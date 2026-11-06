#!/usr/bin/env python3
r"""Crosswalk all 24 consumable sale-basis conflicts without assigning cost.

Save as scripts/AxieOS_V100_Consumable_Basis_Crosswalk.py. From the repo root:
    py -B .\scripts\AxieOS_V100_Consumable_Basis_Crosswalk.py

Reads saved Task96BV, 136F, 136BO, 136BM and 136BS JSON reports only.
No database, network, wallet operations, or accepted financial totals.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V013 = ROOT / "reports/axieos_v013/checkpoint96"
V014 = ROOT / "reports/axieos_v014"
OUT = ROOT / "reports/axieos_v100/finance_basis_review"
SOURCES = {
    "96BV": (V013, "AxieOS_Checkpoint96BV_Finance_Source_Rows_*.json"),
    "136F": (V014 / "task136f", "AxieOS_V014_Task136F_Consumable_Transfer_Evidence_*.json"),
    "136BO": (V014 / "task136bo", "AxieOS_V014_Task136BO_Consumable_Purchase_History_*.json"),
    "136BM": (V014 / "task136bm", "AxieOS_V014_Task136BM_Finance_Resolution_Batch_*.json"),
    "136BS": (V014 / "task136bs", "AxieOS_V014_Task136BS_Legacy_Consumable_Crosswalk_*.json"),
}


def require(ok, message):
    if not ok:
        raise ValueError("STOP: " + message)


def source_path(explicit, directory, pattern, label):
    if explicit:
        path = explicit
    else:
        matches = sorted(directory.glob(pattern))
        require(matches, f"{label} source JSON missing in {directory}")
        path = matches[-1]
    require(path.is_file(), f"{label} source file missing: {path}")
    return path


def load(path, label):
    raw = path.read_bytes()
    require(len(raw) <= 25_000_000, f"{label} source too large")
    doc = json.loads(raw.decode("utf-8-sig"))
    require(isinstance(doc, dict), f"{label} source schema differs")
    return doc, {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}


def when(value):
    require(isinstance(value, str) and value, "transaction timestamp missing")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None, "transaction timestamp lacks timezone")
    return result.astimezone(timezone.utc)


def crosswalk(docs):
    bv, f, bo, bm, bs = (docs[k] for k in ("96BV", "136F", "136BO", "136BM", "136BS"))
    require(bv.get("checkpoint") == "96BV" and f.get("task") == "136F" and
            bo.get("task") == "136BO" and bm.get("task") == "136BM" and
            bs.get("task") == "136BS", "source task identity differs")
    accounting = bv["tables"]["blockchain_accounting_records"]["rows"]
    economics = bv["tables"]["blockchain_economic_events"]["rows"]
    econ = {r["txhash"].lower(): r for r in economics}
    require(len(econ) == len(economics), "duplicate economic hash")
    sales = [r for r in accounting if r.get("event_type") == "ASSET_SALE" and
             r.get("asset_category") == "CONSUMABLE" and
             (r["cost_basis"] != econ[r["txhash"].lower()]["cost_basis"] or
              r["realized_pl"] != econ[r["txhash"].lower()]["realized_pl"])]
    require(len(sales) == 24 and len({r["txhash"].lower() for r in sales}) == 24,
            "24 distinct consumable sale conflicts expected")
    bm_hashes = {r["sale_hash"].lower() for r in bm["review_queue"]
                 if r["review_lane"] == "SALE_BASIS_CONFLICT"}
    require(bm_hashes == {r["txhash"].lower() for r in sales},
            "Task136BM conflicts differ from Task96BV")
    require(bo["coverage"]["corroborated"] == len(bo["purchase_checks"]) == 26 and
            bo["coverage"]["unattempted"] == 0, "Task136BO purchase coverage differs")
    purchases = defaultdict(list)
    for p in bo["purchase_checks"]:
        require(p["status"] == "EXPLORER_PURCHASE_CORROBORATED" and
                p["accepted_basis"] is None and p["accepted_financial_value"] is None and
                str(p["token_id"]) in {"1", "2"}, "purchase source acceptance or token differs")
        purchases[str(p["token_id"])].append(p)
    require(len({p["txhash"].lower() for group in purchases.values() for p in group}) == 26,
            "duplicate purchase hash")
    legacy = bs["summary"]["candidates"]
    require(len(legacy) == 116 and all(p.get("token_id") is None and
            p.get("accepted_basis") is None for p in legacy),
            "legacy token identity or acceptance differs")
    raw = defaultdict(list)
    for r in f["evidence"]["raw_transfers"]:
        raw[str(r["tx_hash"]).lower()].append(r)
    cases = []
    for sale in sorted(sales, key=lambda r: r["txhash"]):
        h, token = sale["txhash"].lower(), str(sale["asset_token_id"])
        require(token in {"1", "2"}, f"{h}: unexpected consumable token ID")
        outgoing = [r for r in raw[h] if r["token_symbol"] == "ACI" and
                    str(r["token_id"]) == token and
                    str(r["amount_raw"]) == str(sale["quantity"]) and
                    r["from_address"].lower() == bo["owned_wallet"].lower()]
        require(len(outgoing) == 1, f"{h}: exactly one matching saved sale transfer required")
        sale_time = when(outgoing[0]["timestamp"])
        candidates = []
        for p in purchases[token]:
            purchase_time = when(p["normalized_transaction"]["timestamp"])
            if purchase_time < sale_time:
                candidates.append({"purchase_hash": p["txhash"].lower(),
                                   "purchase_utc": purchase_time.isoformat(),
                                   "observed_quantity_in": p["observed_quantity_in"],
                                   "observed_weth_out": p["observed_weth_out"],
                                   "basis_assigned": False})
        candidates.sort(key=lambda p: (p["purchase_utc"], p["purchase_hash"]))
        other = econ[h]
        cases.append({"sale_hash": h, "sale_utc": sale_time.isoformat(),
                      "token_id": token, "sale_quantity_as_stored": sale["quantity"],
                      "sale_transfer_key": outgoing[0]["transfer_key"],
                      "accounting_status": sale["accounting_status"],
                      "stored_cost_basis_conflict": sale["cost_basis"] != other["cost_basis"],
                      "stored_profit_conflict": sale["realized_pl"] != other["realized_pl"],
                      "corroborated_prior_purchase_candidates": candidates,
                      "prior_purchase_candidate_count": len(candidates),
                      "legacy_unidentified_purchase_candidates_available": len(legacy),
                      "accepted_cost_basis": None, "accepted_profit": None,
                      "resolution": "OPEN: lot assignment, opening balance and intervening consumption unverified"})
    require(len(cases) == 24, "case count differs")
    return cases, {"conflicts": len(cases),
                   "by_token_id": dict(sorted(Counter(c["token_id"] for c in cases).items())),
                   "sales_with_saved_outgoing_transfer": len(cases),
                   "corroborated_purchase_hashes": 26,
                   "legacy_purchase_candidates_without_token_id": len(legacy),
                   "cases_with_prior_purchase_candidates": sum(c["prior_purchase_candidate_count"] > 0 for c in cases)}


def write(folder, report):
    folder.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V100_Consumable_Basis_Crosswalk_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    jp, mp, cp = (folder / (stem + ext) for ext in (".json", ".md", ".csv"))
    with jp.open("x", encoding="utf-8") as out:
        json.dump(report, out, indent=2)
        out.write("\n")
    with cp.open("x", encoding="utf-8-sig", newline="") as out:
        fields = ("sale_hash", "sale_utc", "token_id", "sale_quantity_as_stored",
                  "prior_purchase_candidate_count", "accounting_status", "resolution")
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for case in report["cases"]:
            writer.writerow({k: case[k] for k in fields})
    summary = report["summary"]
    lines = ["# AxieOS V1.0 — Consumable sale basis crosswalk", "",
             f"Sale conflicts: **{summary['conflicts']}**; saved outgoing transfers: "
             f"**{summary['sales_with_saved_outgoing_transfer']}**.",
             f"By token ID: **{summary['by_token_id']}**. "
             f"Cases with a prior corroborated purchase candidate: "
             f"**{summary['cases_with_prior_purchase_candidates']}**.", "",
             "Prior purchase candidates are grouped by token ID and UTC order only. "
             "They are not assigned lots; intervening purchases, consumption, sales and "
             "opening inventory can change the actual basis. The 116 legacy purchase-shaped "
             "hashes have no accepted token ID and cannot be allocated here.", "",
             "The CSV lists the 24 unresolved cases; JSON includes candidate purchase hashes. "
             "No cost basis, realized profit, expense or PHP recovery is accepted.", "",
             "Bounty Board: PAUSED | Unified Finance: HOLD | Checkpoint 96: OPEN", "",
             "Database opened: NO | Writes: 0 | Network calls: 0", ""]
    mp.write_text("\n".join(lines), encoding="utf-8")
    return jp, mp, cp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for label, (directory, _) in SOURCES.items():
        parser.add_argument("--" + label.lower(), type=Path, default=None,
                            help=f"exact {label} JSON path (default: latest in {directory})")
    parser.add_argument("--output-dir", type=Path, default=OUT)
    args = parser.parse_args()
    docs, sources = {}, {}
    for label, (folder, pattern) in SOURCES.items():
        path = source_path(getattr(args, label.lower()), folder, pattern, label)
        docs[label], sources[label] = load(path, label)
    cases, summary = crosswalk(docs)
    report = {"project": "AxieOS", "version": "1.0-pilot", "task": "CONSUMABLE_BASIS_CROSSWALK",
              "created_utc": datetime.now(timezone.utc).isoformat(), "sources": sources,
              "summary": summary, "cases": cases, "accepted_cost_basis": None,
              "accepted_realized_profit": None, "financial_totals": "UNKNOWN",
              "unified_finance": "HOLD", "checkpoint96": "OPEN",
              "database_opened": False, "database_writes": 0, "network_calls": 0}
    paths = write(args.output_dir, report)
    print("AXIEOS V1.0 - CONSUMABLE BASIS CROSSWALK")
    print("Sale conflicts:", summary["conflicts"], "| By token:", summary["by_token_id"])
    print("Cases with prior purchase candidates:", summary["cases_with_prior_purchase_candidates"],
          "| Accepted basis/profit: UNKNOWN")
    print("Reports:", *paths)
    print("Database opened: NO | Writes: 0 | Network: 0 | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
