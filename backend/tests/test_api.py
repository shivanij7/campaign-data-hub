import pytest
from fastapi.testclient import TestClient

from app import db, pipeline
from app.main import create_app
from app.routes import ingestions

API = "/api/v1"


@pytest.fixture
def client(tmp_path):
    path = tmp_path / "api.db"
    conn = db.connect(path)
    db.init_db(conn)
    pipeline.ingest(conn)
    conn.close()
    with TestClient(create_app(path)) as c:
        c.db_path = path
        yield c


def test_metrics_filters_and_pagination(client):
    r = client.get(f"{API}/metrics", params={"platform": "google_ads", "limit": 10})
    body = r.json()
    assert r.status_code == 200 and body["total"] == 150 and len(body["items"]) == 10
    assert all(i["platform"] == "google_ads" for i in body["items"])
    r = client.get(f"{API}/metrics", params={"date_from": "2026-06-29", "date_to": "2026-06-30", "limit": 1000})
    assert r.json()["total"] == 5 * 2 * 2 + 3 * 2          # google+meta (5 campaigns) + linkedin (3), 2 days


def test_summary_totals_follow_filters_and_match_groups(client):
    r = client.get(f"{API}/metrics/summary", params={"group_by": "platform"}).json()
    by = {g["platform"]: g for g in r["groups"]}
    assert by["google_ads"]["spend_usd"] == pytest.approx(27954.50, abs=0.01)
    assert by["linkedin_ads"]["spend_usd"] == pytest.approx(5869.97, abs=0.01)
    assert by["meta_ads"]["spend_usd"] == pytest.approx(19685.25, abs=0.01)
    assert r["totals"]["spend_usd"] == pytest.approx(sum(g["spend_usd"] for g in r["groups"]), abs=0.01)
    assert r["totals"]["ctr"] == pytest.approx(r["totals"]["clicks"] / r["totals"]["impressions"], abs=1e-6)  # API rounds to 6 dp

    f = client.get(f"{API}/metrics/summary", params={"platform": "meta_ads", "date_from": "2026-06-08",
                                                     "date_to": "2026-06-14"}).json()
    assert f["filters"]["platform"] == "meta_ads"
    assert f["totals"]["spend_usd"] == pytest.approx(sum(g["spend_usd"] for g in f["groups"]), abs=0.01)
    assert all(g["platform"] == "meta_ads" for g in f["groups"])


def test_summary_sorting(client):
    spend = [g["spend_usd"] for g in client.get(f"{API}/metrics/summary").json()["groups"]]
    assert spend == sorted(spend, reverse=True)
    ctr = [g["ctr"] for g in client.get(f"{API}/metrics/summary", params={"sort_by": "ctr", "order": "asc"}).json()["groups"]]
    assert ctr == sorted(ctr)


def test_cpc_and_ctr_are_null_not_errors_when_denominator_is_zero(client):
    conn = db.connect(client.db_path)
    did = conn.execute("SELECT id FROM deliveries LIMIT 1").fetchone()[0]
    conn.execute("INSERT INTO metrics (delivery_id, source_row, platform, campaign, date, spend_usd, impressions, clicks)"
                 " VALUES (?, 1, 'meta_ads', 'Zero Clicks', '2026-06-10', 12.5, 1000, 0)", (did,))
    conn.execute("INSERT INTO metrics (delivery_id, source_row, platform, campaign, date, spend_usd, impressions, clicks)"
                 " VALUES (?, 2, 'meta_ads', 'Zero Everything', '2026-06-10', 0, 0, 0)", (did,))
    conn.commit(); conn.close()
    groups = {g["campaign"]: g for g in client.get(f"{API}/metrics/summary", params={"platform": "meta_ads"}).json()["groups"]}
    assert groups["Zero Clicks"]["cpc"] is None and groups["Zero Clicks"]["ctr"] == 0.0
    assert groups["Zero Everything"]["ctr"] is None and groups["Zero Everything"]["cpc"] is None
    # nulls sort last in both directions
    for order in ("asc", "desc"):
        names = [g["campaign"] for g in client.get(f"{API}/metrics/summary",
                 params={"platform": "meta_ads", "sort_by": "cpc", "order": order}).json()["groups"]]
        assert names[-1] in ("Zero Clicks", "Zero Everything") and names[-2] in ("Zero Clicks", "Zero Everything")


def test_lineage_explains_the_numbers(client):
    r = client.get(f"{API}/metrics/summary", params={"platform": "meta_ads", "date_from": "2026-06-08",
                                                     "date_to": "2026-06-14"}).json()
    assert [d["filename"] for d in r["lineage"]["deliveries"]] == ["meta_ads_2026-06-08.csv"]
    assert r["lineage"]["deliveries"][0]["health"] == "fail"
    assert r["lineage"]["transforms"]["unit_scale"] == 35


def test_validation_errors_use_the_standard_error_body(client):
    r = client.get(f"{API}/metrics", params={"platform": "tiktok"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
    r = client.get(f"{API}/metrics", params={"date_from": "2026-06-20", "date_to": "2026-06-01"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_date_range"
    assert client.get(f"{API}/metrics", params={"limit": 0}).status_code == 422
    assert client.get(f"{API}/nope").json()["error"]["code"] == "not_found"


def test_deliveries_list_and_filter(client):
    items = client.get(f"{API}/deliveries").json()
    assert len(items) == 16
    failing = client.get(f"{API}/deliveries", params={"health": "fail"}).json()
    assert {d["filename"] for d in failing} == {
        "linkedin_ads_2026-06-08.json", "meta_ads_2026-06-08.csv", "meta_ads_2026-06-15.csv",
        "google_ads_2026-06-15_resend.csv", "linkedin_ads_2026-06-22 (missing)"}
    assert all(d["problems"] for d in failing)


def test_delivery_detail_and_404(client):
    d = next(x for x in client.get(f"{API}/deliveries").json() if x["filename"] == "meta_ads_2026-06-15.csv")
    detail = client.get(f"{API}/deliveries/{d['id']}").json()
    comp = next(c for c in detail["checks"] if c["name"] == "completeness")
    assert comp["status"] == "fail" and comp["details"]["affected_rows"] == 3
    assert len(detail["quarantined_rows"]) == 3 and detail["quarantined_rows"][0]["raw"] is not None
    r = client.get(f"{API}/deliveries/99999")
    assert r.status_code == 404 and r.json()["error"]["code"] == "delivery_not_found"


def test_ingestion_is_idempotent_through_the_api(client):
    before = client.get(f"{API}/metrics/summary").json()
    for body in (None, {}, {"filename": "meta_ads_2026-06-08.csv"}):
        r = client.post(f"{API}/ingestions", json=body) if body is not None else client.post(f"{API}/ingestions")
        assert r.status_code == 200 and r.json()["errors"] == []
    assert client.post(f"{API}/ingestions").json()["health_counts"] == {"warn": 3, "pass": 8, "fail": 5}
    after = client.get(f"{API}/metrics/summary").json()
    assert before == after


def test_ingestion_errors(client):
    r = client.post(f"{API}/ingestions", json={"filename": "nope.csv"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "delivery_not_found"
    ingestions._running.acquire()
    try:
        r = client.post(f"{API}/ingestions")
        assert r.status_code == 409 and r.json()["error"]["code"] == "ingestion_in_progress"
    finally:
        ingestions._running.release()


# ---------------- the prebuilt UI is served by the API when it exists ---------------------------

def test_prebuilt_ui_is_served_without_hiding_the_api(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>the ui</h1>")
    with TestClient(create_app(tmp_path / "x.db", frontend_dist=dist)) as c:
        assert "the ui" in c.get("/").text
        assert c.get(f"{API}/deliveries").status_code == 200
        assert c.get("/docs").status_code == 200


def test_without_a_built_ui_the_api_still_works(tmp_path):
    with TestClient(create_app(tmp_path / "x.db", frontend_dist=tmp_path / "missing")) as c:
        r = c.get("/")
        assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
        assert c.get(f"{API}/deliveries").status_code == 200
