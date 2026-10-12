"""Usage (from the backend/ folder):
    python -m app.cli ingest                 # (re)ingest every delivery
    python -m app.cli ingest --file NAME     # re-ingest one delivery
"""
import argparse
import sys

from . import config, db, pipeline


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="app.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    ing = sub.add_parser("ingest", help="ingest delivery files")
    ing.add_argument("--file", help="re-ingest only this delivery filename")
    args = p.parse_args(argv)

    conn = db.connect()
    db.init_db(conn)
    try:
        result = pipeline.ingest(conn, only=args.file)
    except pipeline.DeliveryNotFound as exc:
        print(f"no such delivery: {exc}", file=sys.stderr)
        return 1
    print(f"database: {config.DB_PATH}")
    for d in result["deliveries"]:
        print(f"  {d['health']:4}  {d['filename']:36} read={d['rows_read']:3} loaded={d['rows_loaded']:3}")
    for e in result["errors"]:
        print(f"  ERROR {e['filename']}: {e['error']}")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
