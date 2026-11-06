#!/usr/bin/env python3
r"""Refresh the V1.0 no-spend watchlist and local dashboard in one command.

Save as scripts/AxieOS_V100_Refresh_NoSpend_Dashboard.py. From repo root:
    py -B .\scripts\AxieOS_V100_Refresh_NoSpend_Dashboard.py

Default: reuse the latest reconciled saved operational sync, read the roster,
and regenerate the watchlist and local HTML. Use --sync to first run the
existing read-only network sync/status preflight. Neither mode applies raw
rows, changes the roster, accepts finance values, or executes gameplay.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
WATCH = ROOT / "reports/axieos_v100/no_spend_watchlist"
FINANCE = ROOT / "reports/axieos_v100/finance_basis_review"
PHT = timezone(timedelta(hours=8))


def require(ok, reason):
    if not ok:
        raise ValueError("STOP: " + reason)


def run_script(filename, *args):
    path = SCRIPTS / filename
    require(path.is_file(), f"required script missing: {path}")
    proc = subprocess.run([sys.executable, "-B", str(path), *args], cwd=ROOT,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, check=False)
    if proc.stdout:
        print(proc.stdout.rstrip())
    require(proc.returncode == 0,
            f"{filename} failed: {proc.stderr.strip()[-1800:]}")


def new_watchlist(before):
    found = set(WATCH.glob("AxieOS_V100_NoSpend_Portfolio_Watchlist_*.json")) - before
    require(len(found) == 1, f"expected one new watchlist JSON; found {len(found)}")
    path = found.pop()
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    require(doc.get("task") == "NO_SPEND_PORTFOLIO_WATCHLIST" and
            doc.get("financial_totals") == "UNKNOWN" and
            doc.get("bounty_board") == "PAUSED_NO_OPERATING_FUNDS" and
            doc.get("unified_finance") == "HOLD" and
            doc.get("checkpoint96") == "OPEN" and
            doc.get("database_writes") == doc.get("network_calls") == 0 and
            doc.get("automatic_execution") is False and
            len(doc.get("axies", [])) == doc.get("owned_axies"),
            "new watchlist crossed the no-spend or finance boundary")
    return path, doc


def validate_dashboard(watch_path, doc):
    path = WATCH / "AxieOS_V100_NoSpend_Portfolio_Watchlist_Latest.html"
    require(path.is_file(), "HTML watchlist missing")
    page = path.read_text(encoding="utf-8")
    require(watch_path.name in page and
            f"Showing ${{n}} of ${{rows.length}} saved owned Axies" in page and
            "Finance remains on hold" in page and
            "Bounty Board<strong>Paused</strong>" in page,
            "HTML does not match new no-spend watchlist")
    files = sorted(FINANCE.glob("AxieOS_V100_Finance_Source_Exceptions_*.json"))
    if files:
        require(page.count("Consumable sale exceptions<strong>24 open</strong>") == 1 and
                files[-1].name in page, "finance exceptions missing or repeated in HTML")
    else:
        require("Consumable sale exceptions<strong>" not in page,
                "HTML refers to missing finance source exceptions")
    return path, bool(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync", action="store_true",
                        help="run the existing read-only network sync/status preflight first")
    parser.add_argument("--as-of", default=datetime.now(PHT).date().isoformat(),
                        help="Philippine report date (YYYY-MM-DD)")
    args = parser.parse_args()
    as_of = datetime.fromisoformat(args.as_of).date().isoformat()
    if args.sync:
        run_script("AxieOS_Operational_One_Command.py", "--skip-dashboard")
    before = set(WATCH.glob("AxieOS_V100_NoSpend_Portfolio_Watchlist_*.json"))
    run_script("AxieOS_V100_NoSpend_Portfolio_Watchlist.py", "--as-of", as_of)
    report_path, doc = new_watchlist(before)
    run_script("AxieOS_V100_Watchlist_App.py")
    dashboard_path, has_exceptions = validate_dashboard(report_path, doc)
    print("AXIEOS V1.0 - ONE-COMMAND NO-SPEND DASHBOARD REFRESH")
    print("Owned:", doc["owned_axies"], "| Unknown levels:", doc["unknown_levels"],
          "| Pinned sync age:", doc["sync_age_days"], "day(s)")
    print("Finance source exceptions:", "24 OPEN" if has_exceptions else "no saved report")
    print("Watchlist:", report_path, "| Dashboard:", dashboard_path)
    print("Database: READ ONLY | Database writes: 0 | Network:",
          "read-only sync preflight" if args.sync else "0 calls")
    print("Bounty Board: PAUSED | Unified Finance: HOLD | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
