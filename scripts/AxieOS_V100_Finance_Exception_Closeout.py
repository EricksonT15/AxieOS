#!/usr/bin/env python3
r"""Record unresolved consumable sale basis exceptions on the no-spend dashboard.

Save as scripts/AxieOS_V100_Finance_Exception_Closeout.py. From repo root:
    py -B .\scripts\AxieOS_V100_Finance_Exception_Closeout.py

Reads saved V1.0 basis, quantity and watchlist reports; writes exception reports
and a local HTML dashboard. No database, network, accounting or wallet action.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import webbrowser
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from AxieOS_V100_Watchlist_App import load_latest as load_watchlist, render as render_watchlist


ROOT = Path(__file__).resolve().parents[1]
FINANCE = ROOT / "reports/axieos_v100/finance_basis_review"
WATCHLIST = ROOT / "reports/axieos_v100/no_spend_watchlist"


def require(condition, reason):
    if not condition:
        raise ValueError("STOP: " + reason)


def choose(explicit, pattern):
    paths = [explicit] if explicit else sorted(FINANCE.glob(pattern))
    require(bool(paths), f"source missing in {FINANCE}: {pattern}")
    path = paths[-1]
    require(path.is_file(), f"source file missing: {path}")
    return path


def load(path):
    raw = path.read_bytes()
    require(len(raw) <= 25_000_000, f"source too large: {path}")
    doc = json.loads(raw.decode("utf-8-sig"))
    require(isinstance(doc, dict), f"source schema differs: {path}")
    return doc, {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}


def build(basis, quantity, basis_source, quantity_source, watch_path, watch):
    require(basis.get("task") == "CONSUMABLE_BASIS_CROSSWALK" and
            quantity.get("task") == "CONSUMABLE_QUANTITY_AUDIT", "source task differs")
    require(quantity["sources"]["basis_crosswalk"]["sha256"] == basis_source["sha256"],
            "quantity audit was built from a different basis crosswalk")
    require(basis.get("accepted_cost_basis") is None and
            basis.get("accepted_realized_profit") is None and
            quantity.get("accepted_opening_inventory") is None and
            quantity.get("accepted_cost_basis") is None and
            quantity.get("accepted_profit") is None, "source financial acceptance differs")
    by_token = quantity["by_token_id"]
    require(set(by_token) == {"1", "2"} and
            all(type(v["minimum_opening_units_needed_to_avoid_negative_observed_path"]) is int
                and v["minimum_opening_units_needed_to_avoid_negative_observed_path"] >= 0
                and v["actual_opening_inventory"] is None for v in by_token.values()),
            "opening inventory source differs")
    basis_cases = {c["sale_hash"]: c for c in basis["cases"]}
    quantity_cases = {c["sale_hash"]: c for c in quantity["sale_cases"]}
    require(len(basis_cases) == len(quantity_cases) == 24 and
            basis_cases.keys() == quantity_cases.keys(), "sale case sets differ")
    exceptions = []
    for sale_hash in sorted(basis_cases):
        b, q = basis_cases[sale_hash], quantity_cases[sale_hash]
        require(b["sale_transfer_key"] == q["sale_transfer_key"] and
                b["token_id"] == q["token_id"] and
                b["prior_purchase_candidate_count"] > 0 and
                q["accepted_cost_basis"] is None and q["accepted_profit"] is None,
                f"case reconciliation differs: {sale_hash}")
        exceptions.append({
            "sale_hash": sale_hash, "token_id": b["token_id"],
            "sale_utc": q["sale_utc"], "sale_quantity": q["observed_quantity"],
            "candidate_prior_purchases": b["prior_purchase_candidate_count"],
            "exception_status": "OPEN_SOURCE_GAP", "decision": "DEFER_COST_AND_PROFIT",
            "reason": "Opening inventory, complete lot identity and intervening consumption are unverified",
            "accepted_cost_basis": None, "accepted_profit": None})
    counts = Counter(e["token_id"] for e in exceptions)
    require(counts == Counter({"1": 6, "2": 18}) and
            watch["financial_totals"] == "UNKNOWN" and watch["unified_finance"] == "HOLD" and
            watch["checkpoint96"] == "OPEN", "exception count or watchlist boundary differs")
    return {
        "project": "AxieOS", "version": "1.0-pilot", "task": "FINANCE_SOURCE_EXCEPTION_CLOSEOUT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {"basis_crosswalk": basis_source, "quantity_audit": quantity_source,
                    "watchlist": {"path": str(watch_path),
                                  "sha256": hashlib.sha256(watch_path.read_bytes()).hexdigest()}},
        "scope": "saved consumable transfers and 24 stored sale conflicts only",
        "sale_conflicts": 24, "by_token_id": dict(sorted(counts.items())),
        "minimum_starting_units_for_observed_path_only": {
            k: v["minimum_opening_units_needed_to_avoid_negative_observed_path"]
            for k, v in sorted(by_token.items())},
        "actual_opening_inventory": None, "accepted_cost_basis": None, "accepted_profit": None,
        "exceptions": exceptions, "next_trigger":
            "Reopen only when token-specific opening inventory, complete lot provenance and intervening consumption are supported by new evidence",
        "bounty_board": "PAUSED", "unified_finance": "HOLD", "checkpoint96": "OPEN",
        "database_opened": False, "database_writes": 0, "network_calls": 0}


def write_reports(report):
    FINANCE.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V100_Finance_Source_Exceptions_" + datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S_%fZ")
    jp, mp, cp = (FINANCE / (stem + ext) for ext in (".json", ".md", ".csv"))
    with jp.open("x", encoding="utf-8") as dest:
        json.dump(report, dest, indent=2)
        dest.write("\n")
    fields = ("sale_hash", "token_id", "sale_utc", "sale_quantity", "candidate_prior_purchases",
              "exception_status", "decision", "reason", "accepted_cost_basis", "accepted_profit")
    with cp.open("x", encoding="utf-8-sig", newline="") as dest:
        writer = csv.DictWriter(dest, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row[key] for key in fields} for row in report["exceptions"])
    lines = ["# AxieOS V1.0 — Finance source exceptions", "",
             "The 24 consumable sale conflicts remain OPEN_SOURCE_GAP: 6 regular token #1 and "
             "18 premium token #2. Earlier purchase candidates are present in every case but "
             "no purchase lot has been assigned.", "",
             "The observed transfer path requires at least "
             f"{report['minimum_starting_units_for_observed_path_only']['1']} regular and "
             f"{report['minimum_starting_units_for_observed_path_only']['2']} premium units "
             "at the saved May 13 start. These are lower bounds, not actual opening inventory.", "",
             "Accepted cost basis, realized profit and verified financial totals: UNKNOWN. "
             "Reopen only with new token-specific opening inventory, lot provenance and "
             "intervening consumption evidence. The CSV lists each exception.", "",
             "Bounty Board: PAUSED | Unified Finance: HOLD | Checkpoint 96: OPEN", "",
             "Database opened: NO | Writes: 0 | Network: 0", ""]
    mp.write_text("\n".join(lines), encoding="utf-8")
    return jp, mp, cp


def write_dashboard(watch_path, watch, report, report_path):
    page = render_watchlist(watch_path, watch, report, report_path.name)
    path = WATCHLIST / "AxieOS_V100_NoSpend_Portfolio_Watchlist_Latest.html"
    path.write_text(page, encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--basis", type=Path, help="exact basis crosswalk JSON path")
    parser.add_argument("--quantity", type=Path, help="exact quantity audit JSON path")
    parser.add_argument("--no-open", action="store_true", help="do not open the local HTML page")
    args = parser.parse_args()
    bp = choose(args.basis, "AxieOS_V100_Consumable_Basis_Crosswalk_*.json")
    qp = choose(args.quantity, "AxieOS_V100_Consumable_Quantity_Audit_*.json")
    basis, basis_source = load(bp)
    quantity, quantity_source = load(qp)
    watch_path, watch = load_watchlist(WATCHLIST)
    report = build(basis, quantity, basis_source, quantity_source, watch_path, watch)
    paths = write_reports(report)
    html_path = write_dashboard(watch_path, watch, report, paths[0])
    print("AXIEOS V1.0 - FINANCE EXCEPTION AND NO-SPEND DASHBOARD")
    print("Sale conflicts:", report["sale_conflicts"], "| Starting floors:",
          report["minimum_starting_units_for_observed_path_only"])
    print("Exceptions: OPEN_SOURCE_GAP | Accepted basis/profit: UNKNOWN")
    print("Reports:", *paths)
    print("Dashboard:", html_path)
    print("Database opened: NO | Writes: 0 | Network: 0 | Checkpoint 96: OPEN")
    if not args.no_open and not webbrowser.open(html_path.resolve().as_uri()):
        print("Open the dashboard HTML path above in your browser.")


if __name__ == "__main__":
    main()
