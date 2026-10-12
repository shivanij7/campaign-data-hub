"""Checks that this machine is ready to run the project.   Usage:  python scripts/doctor.py

Only Python is required to run everything (the API serves the prebuilt UI).
Node is only needed to edit or rebuild the UI.
"""
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
problems = 0


def ok(msg):
    print(f"  ok    {msg}")


def fix(msg):
    global problems
    problems += 1
    print(f"  FIX   {msg}")


def note(msg):
    print(f"  note  {msg}")


print("Python")
v = sys.version_info
(ok if v >= (3, 10) else fix)(f"Python {v.major}.{v.minor}.{v.micro}" + ("" if v >= (3, 10) else "  -> need 3.10 or newer"))
missing = [m for m in ("fastapi", "uvicorn", "httpx", "pytest") if importlib.util.find_spec(m) is None]
if missing:
    fix(f"missing packages {missing}: activate your virtual environment, then  pip install -r backend/requirements.txt")
else:
    ok("backend packages installed")

print("Data")
files = [p for p in (ROOT / "data" / "deliveries").glob("*") if p.is_file()]
(ok if files else fix)(f"{len(files)} delivery files in data/deliveries")
(ok if (ROOT / "data" / "exchange_rates.json").is_file() else fix)("data/exchange_rates.json")

print("Frontend")
(ok if (ROOT / "frontend" / "dist" / "index.html").is_file() else note)(
    "prebuilt UI found (the API will serve it)" if (ROOT / "frontend" / "dist" / "index.html").is_file()
    else "no prebuilt UI: run  npm run build  in frontend/ (needs Node), or use the API at /docs")
node = shutil.which("node")
if node:
    out = subprocess.run([node, "-v"], capture_output=True, text=True).stdout.strip()
    major, minor = (int(x) for x in out.lstrip("v").split(".")[:2])
    good = (major == 20 and minor >= 19) or (major == 22 and minor >= 12) or major >= 23
    (ok if good else note)(f"Node {out}" + ("" if good else "  -> the UI toolchain needs 20.19+ or 22.12+ (only for editing the UI)"))
else:
    note("Node not installed (only needed to edit/rebuild the UI)")

print("\nAll good." if not problems else f"\n{problems} thing(s) to fix before running.")
sys.exit(1 if problems else 0)
