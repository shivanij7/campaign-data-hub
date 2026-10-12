"""Quick look at what the parsers make of every delivery (no DB involved)."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import config                                  # noqa: E402
from app.deliveries import discover, expected_window    # noqa: E402
from app.parsers import parse_file                      # noqa: E402

rates = config.load_rates()
files, unknown = discover(config.DELIVERIES_DIR)
print("unrecognized:", unknown)
for f in files:
    r = parse_file(f.platform, f.path, rates)
    codes = Counter((i.severity, i.code) for i in r.issues)
    lo, hi = expected_window(f.week_start)
    print(f"{f.filename:34} window {lo}..{hi}  read={r.rows_read:3} ok={len(r.metrics):3} "
          f"fatal={r.fatal} issues={dict(codes)}")
