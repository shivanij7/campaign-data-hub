import pytest

from app import db


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "test.db")
    db.init_db(c)
    yield c
    c.close()


def snapshot(conn):
    """Everything an ingestion produces, minus timestamps/ids -- for equality comparisons."""
    q = lambda sql: [tuple(r) for r in conn.execute(sql)]
    return {
        "deliveries": q("SELECT filename, health, rows_read, rows_loaded, rows_quarantined FROM deliveries ORDER BY filename"),
        "metrics": q("SELECT platform, campaign, date, spend_usd, impressions, clicks, transforms FROM metrics ORDER BY platform, campaign, date"),
        "quarantine": q("SELECT d.filename, source_row, code, message FROM quarantined_rows r JOIN deliveries d ON d.id=r.delivery_id ORDER BY d.filename, source_row, code"),
        "checks": q("SELECT d.filename, check_name, status, summary, details FROM quality_checks c JOIN deliveries d ON d.id=c.delivery_id ORDER BY d.filename, check_name"),
    }
