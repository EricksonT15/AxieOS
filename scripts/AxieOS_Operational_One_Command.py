#!/usr/bin/env python3
r"""Run AxieOS operational sync, current status, and dated dashboard together.

Save as scripts/AxieOS_Operational_One_Command.py; from the repository root:
    py -B .\scripts\AxieOS_Operational_One_Command.py --apply

--apply delegates only to the existing guarded raw-sync procedure. It may
insert new raw source rows after its clone and backup checks. This runner
does not classify events, update finance, or accept profit. Omit --apply for
a read-only preflight (the run stops if there are pending raw rows).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SYNC_DIR = ROOT / "reports/axieos/operational_sync"
STATUS_DIR = ROOT / "reports/axieos/operational_status"
CATCHUP_DIR = ROOT / "reports/axieos_v015/source_catchup"
DASH_DIR = ROOT / "reports/axieos_v016/dashboards"
PHT = timezone(timedelta(hours=8))


def require(ok, message):
    if not ok:
        raise ValueError("STOP: " + message)


def read(path):
    require(path.is_file() and path.stat().st_size <= 25_000_000,
            "missing or oversized saved report: " + str(path))
    return json.loads(path.read_text(encoding="utf-8-sig"))


def new_report(directory, prefix, previous):
    matches = set(directory.glob(prefix + "*.json")) - previous
    require(len(matches) == 1, "expected one new " + prefix + " report; found " + str(len(matches)))
    return matches.pop()


def execute(name, *args):
    script = SCRIPTS / name
    require(script.is_file(), "required script missing: " + str(script))
    command = [sys.executable, "-B", str(script), *args]
    p = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    if p.stdout:
        print(p.stdout.rstrip())
    require(p.returncode == 0, name + " failed: " + p.stderr.strip()[-1200:])


def dashboard_date():
    paths = sorted(CATCHUP_DIR.glob("AxieOS_V015_Source_Catchup_*.json"))
    for path in reversed(paths):
        doc = read(path)
        owned = doc.get("owned_inventory", {})
        if doc.get("task") != "SOURCE_CATCHUP" or owned.get("status") != "COMPLETE_AT_PINNED_BLOCK":
            continue
        stamp = datetime.fromisoformat(owned["block_timestamp_utc"].replace("Z", "+00:00"))
        require(stamp.tzinfo is not None, "catch-up block time has no timezone")
        return stamp.astimezone(PHT).date().isoformat()
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true", help="allow existing guarded raw sync to back up and insert new rows")
    p.add_argument("--skip-dashboard", action="store_true", help="omit historical dated dashboard refresh")
    args = p.parse_args()
    before_sync = set(SYNC_DIR.glob("AxieOS_Operational_Sync_*.json"))
    execute("axieos_operational_sync.py", *(["--apply"] if args.apply else []))
    sync_path = new_report(SYNC_DIR, "AxieOS_Operational_Sync_", before_sync)
    sync = read(sync_path)
    if sync.get("status") == "APPLIED_AND_RECONCILED":
        # The applied report retains its pre-insert gap list for audit. A
        # second, read-only pass proves that the latest raw source is current
        # before the status command consumes its newest report.
        before_sync = set(SYNC_DIR.glob("AxieOS_Operational_Sync_*.json"))
        execute("axieos_operational_sync.py")
        sync_path = new_report(SYNC_DIR, "AxieOS_Operational_Sync_", before_sync)
        sync = read(sync_path)
    raw = sync.get("raw_coverage", {})
    own = sync.get("ownership", {})
    require(sync.get("status") == "CURRENT_NO_WRITES" and
            sync.get("unified_finance") == "HOLD" and sync.get("checkpoint96") == "OPEN" and
            sync.get("finance_totals") == "UNKNOWN" and
            own.get("status") == "COMPLETE_AT_PINNED_BLOCK" and
            own.get("saved_owned_count") == own.get("pinned_chain_owned_count") and
            own.get("chain_only_ids") == own.get("saved_only_ids") == [] and
            raw.get("all_four_complete") is True and len(raw.get("routes", [])) == 4 and
            raw.get("transaction_hashes_absent_from_raw") == [] and
            raw.get("transfer_hashes_absent_from_raw") == [] and
            all(v == 0 for v in sync.get("raw_writes", {}).values()),
            "sync requires review; current status and dashboard not advanced. See " + str(sync_path))
    before_status = set(STATUS_DIR.glob("AxieOS_Operational_Status_*.json"))
    execute("axieos_operational_status.py")
    status_path = new_report(STATUS_DIR, "AxieOS_Operational_Status_", before_status)
    status = read(status_path)
    linked = status.get("last_sync", {})
    require(linked.get("status") in {"SYNC_RECONCILED_AT_DATED_BLOCK", "SYNC_RECONCILED_TODAY"} and
            linked.get("sha256") == hashlib.sha256(sync_path.read_bytes()).hexdigest() and
            Path(linked.get("source_path") or "").resolve() == sync_path.resolve() and
            status.get("unified_finance") == "HOLD" and status.get("checkpoint96") == "OPEN" and
            status.get("verified_financial_totals") == "UNKNOWN", "status report does not match new sync")
    dash_path = None
    if not args.skip_dashboard:
        as_of = dashboard_date()
        if as_of:
            execute("AxieOS_V016_Operational_Dashboard.py", "--period", "all", "--as-of", as_of)
            dash_path = DASH_DIR / f"AxieOS_V016_Operational_Dashboard_{as_of}_all.json"
            dash = read(dash_path)
            require(dash.get("as_of_philippines_date") == as_of and
                    dash.get("verified_financial_totals") == "UNKNOWN" and
                    dash.get("unified_finance") == "HOLD" and dash.get("checkpoint96") == "OPEN" and
                    dash.get("database_writes") == 0 and dash.get("network_calls") == 0 and
                    dash.get("catchup_source", {}).get("status") in
                    {"POST_APPLY_ROSTER_RECONCILED", "PINNED_CHAIN_SNAPSHOT"},
                    "dated dashboard needs review: " + str(dash_path))
        else:
            print("Dated dashboard: no complete saved V0.15 catch-up; skipped")
    print("AXIEOS - ONE-COMMAND OPERATIONAL UPDATE")
    print("Current sync:", sync["status"], "| Saved/pinned Axies:", own["saved_owned_count"], "/", own["pinned_chain_owned_count"])
    print("Sync and status:", sync_path, status_path)
    print("Dashboard:", str(dash_path) + " (historical pinned date)" if dash_path else "SKIPPED")
    print("Financial totals: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
