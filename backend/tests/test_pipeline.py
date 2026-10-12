import json
import re
import shutil

from app import config, pipeline
from app.models import DeliveryContext
from app.quality import Check, run_checks
from tests.conftest import snapshot

D = config.DELIVERIES_DIR


def health(conn):
    return {r["filename"]: r["health"] for r in conn.execute("SELECT filename, health FROM deliveries")}


def check_status(conn, filename, check):
    row = conn.execute("SELECT status FROM quality_checks c JOIN deliveries d ON d.id=c.delivery_id "
                       "WHERE d.filename=? AND check_name=?", (filename, check)).fetchone()
    return row["status"] if row else None


# ---------------- NFR-1 idempotency ----------------------------------------------------

def test_full_reingest_changes_nothing(conn):
    pipeline.ingest(conn)
    first = snapshot(conn)
    pipeline.ingest(conn)
    assert snapshot(conn) == first
    assert len(first["metrics"]) == 359


def test_single_delivery_reingest_changes_nothing(conn):
    pipeline.ingest(conn)
    first = snapshot(conn)
    pipeline.ingest(conn, only="meta_ads_2026-06-08.csv")
    pipeline.ingest(conn, only="google_ads_2026-06-01.csv")
    assert snapshot(conn) == first


# ---------------- planted defects are caught ---------------------------------------------

def test_health_of_every_delivery(conn):
    pipeline.ingest(conn)
    h = health(conn)
    assert h["google_ads_2026-06-01.csv"] == "warn"           # 8 exact duplicate rows
    assert h["google_ads_2026-06-15_resend.csv"] == "fail"    # byte-identical re-delivery
    assert h["linkedin_ads_2026-06-22 (missing)"] == "fail"   # whole week never arrived
    assert h["meta_ads_2026-06-08.csv"] == "fail"             # spend 100x too large
    assert h["meta_ads_2026-06-15.csv"] == "fail"             # 8.6% rows missing clicks
    assert h["linkedin_ads_2026-06-08.json"] == "fail"        # 24% rows missing clicks
    assert h["meta_ads_2026-06-01.csv"] == "warn" and h["meta_ads_2026-06-22.csv"] == "warn"
    clean = [f for f in h if f in ("google_ads_2026-06-08.csv", "google_ads_2026-06-22.csv", "google_ads_2026-06-29.csv",
                                    "linkedin_ads_2026-06-01.json", "linkedin_ads_2026-06-15.json",
                                    "linkedin_ads_2026-06-29.json", "meta_ads_2026-06-29.csv", "google_ads_2026-06-15.csv")]
    assert len(clean) == 8 and all(h[f] == "pass" for f in clean)


def test_specific_checks_fire(conn):
    pipeline.ingest(conn)
    assert check_status(conn, "google_ads_2026-06-01.csv", "duplicate_rows") == "warn"
    assert check_status(conn, "meta_ads_2026-06-01.csv", "validity") == "warn"           # 06/31
    assert check_status(conn, "meta_ads_2026-06-22.csv", "validity") == "warn"           # negative spend
    assert check_status(conn, "meta_ads_2026-06-15.csv", "completeness") == "fail"
    assert check_status(conn, "meta_ads_2026-06-08.csv", "unit_scale") == "fail"
    assert check_status(conn, "google_ads_2026-06-15_resend.csv", "duplicate_delivery") == "fail"


# ---------------- numbers ---------------------------------------------------------------

def test_resend_is_not_double_counted(conn):
    pipeline.ingest(conn)
    n = conn.execute("SELECT COUNT(*) FROM metrics WHERE platform='google_ads' AND date BETWEEN '2026-06-15' AND '2026-06-21'").fetchone()[0]
    assert n == 35
    assert conn.execute("SELECT rows_loaded FROM deliveries WHERE filename='google_ads_2026-06-15_resend.csv'").fetchone()[0] == 0


def test_units_are_normalized(conn):
    pipeline.ingest(conn)
    # Meta 06-08 arrived in cents: after correction it must look like every other week
    assert conn.execute("SELECT MAX(spend_usd) FROM metrics WHERE platform='meta_ads' AND date BETWEEN '2026-06-08' AND '2026-06-14'").fetchone()[0] < 300
    # Google micros: 117410000 micros -> 117.41 USD
    assert conn.execute("SELECT spend_usd FROM metrics WHERE platform='google_ads' AND campaign='Search - Brand' AND date='2026-06-07'").fetchone()[0] == 117.41
    # LinkedIn EUR 92.37 -> USD at 1.08
    assert round(conn.execute("SELECT spend_usd FROM metrics WHERE platform='linkedin_ads' AND campaign='ABM Tier 1' AND date='2026-06-01'").fetchone()[0], 4) == round(92.37 * 1.08, 4)


def test_campaign_names_are_canonicalized(conn):
    pipeline.ingest(conn)
    names = {r[0] for r in conn.execute("SELECT DISTINCT campaign FROM metrics WHERE platform='meta_ads'")}
    assert names == {"Summer Sale", "Lead Gen Webinar", "Brand Awareness Q2", "Retargeting - US", "App Install Push"}


# ---------------- NFR-2 error isolation ----------------------------------------------------

def test_broken_files_do_not_abort_the_run(conn, tmp_path):
    src = tmp_path / "deliveries"
    src.mkdir()
    shutil.copy(D / "meta_ads_2026-06-29.csv", src)
    shutil.copy(D / "linkedin_ads_2026-06-29.json", src)
    (src / "linkedin_ads_2026-06-01.json").write_text("{ this is not json")                 # malformed JSON
    (src / "google_ads_2026-06-01.csv").write_text("foo,bar\n1,2\n")                        # wrong columns
    (src / "meta_ads_2026-06-08.csv").write_bytes(b"\xff\xfe\x00garbage\x80\x81")           # binary junk
    (src / "random_notes.txt").write_text("not a delivery")                                  # unrecognized name
    (src / "linkedin_ads_2026-06-08.json").write_text(json.dumps(["oops", {"campaign": "X"}]))  # bad records

    result = pipeline.ingest(conn, directory=src)
    assert result["errors"] == []
    h = health(conn)
    assert h["meta_ads_2026-06-29.csv"] == "pass" and h["linkedin_ads_2026-06-29.json"] == "pass"
    for bad in ("linkedin_ads_2026-06-01.json", "google_ads_2026-06-01.csv", "meta_ads_2026-06-08.csv",
                "random_notes.txt", "linkedin_ads_2026-06-08.json"):
        assert h[bad] == "fail", bad
    assert check_status(conn, "linkedin_ads_2026-06-01.json", "file_readable") == "fail"
    assert check_status(conn, "random_notes.txt", "filename_recognized") == "fail"


def test_a_crashing_check_is_reported_not_raised():
    class Boom(Check):
        name, level = "boom", "row"
        def run(self, ctx): raise RuntimeError("kaboom")

    ctx = DeliveryContext(filename="x.csv", platform="meta_ads", week_start=None)
    [res] = run_checks(ctx, [Boom()])
    assert res.status == "fail" and "kaboom" in res.summary


# ---------------- portability: files as Windows tools write them ----------------------------

def test_windows_style_files_give_identical_results(conn, tmp_path):
    """CRLF line endings everywhere, plus the UTF-8 BOM that Excel adds, must not change a single number."""
    pipeline.ingest(conn)
    baseline = snapshot(conn)

    src = tmp_path / "deliveries"
    src.mkdir()
    for f in D.iterdir():
        data = f.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        if f.name.startswith(("meta", "linkedin")):
            data = b"\xef\xbb\xbf" + data
        (src / f.name).write_bytes(data)

    from app import db
    other = db.connect(tmp_path / "win.db")
    db.init_db(other)
    assert pipeline.ingest(other, directory=src)["errors"] == []

    def without_hashes(snap):  # the byte hash is evidence in a check and *should* differ for different bytes
        snap = dict(snap)
        snap["checks"] = [(*row[:4], re.sub(r'"content_hash": "[0-9a-f]{64}"', '"content_hash": "-"', row[4]))
                          for row in snap["checks"]]
        return snap

    assert without_hashes(snapshot(other)) == without_hashes(baseline)
    other.close()
