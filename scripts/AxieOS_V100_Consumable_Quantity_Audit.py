#!/usr/bin/env python3
r"""Audit saved consumable token movements and the 24 sale conflicts.

Save in scripts/AxieOS_V100_Consumable_Quantity_Audit.py, then run from repo root:
    py -B .\scripts\AxieOS_V100_Consumable_Quantity_Audit.py

Uses saved JSON only. No SQLite, network, financial valuation, or wallet action.
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
F_DIR = ROOT / "reports/axieos_v014/task136f"
C_DIR = ROOT / "reports/axieos_v100/finance_basis_review"
OUTPUT = C_DIR
F_PATTERN = "AxieOS_V014_Task136F_Consumable_Transfer_Evidence_*.json"
C_PATTERN = "AxieOS_V100_Consumable_Basis_Crosswalk_*.json"
ZERO = "0x" + "0" * 40


def require(condition, reason):
    if not condition:
        raise ValueError("STOP: " + reason)


def selected(explicit, folder, pattern):
    matches = [explicit] if explicit else sorted(folder.glob(pattern))
    require(bool(matches), f"missing source in {folder}; pass its exact path explicitly")
    path = matches[-1]
    require(path.is_file(), f"source missing: {path}")
    return path


def load(path):
    data = path.read_bytes()
    require(len(data) <= 30_000_000, f"source too large: {path}")
    doc = json.loads(data.decode("utf-8-sig"))
    require(isinstance(doc, dict), f"expected JSON object: {path}")
    return doc, {"path": str(path), "sha256": hashlib.sha256(data).hexdigest()}


def utc(value):
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(timestamp.tzinfo is not None, "transfer has no UTC timezone")
    return timestamp.astimezone(timezone.utc)


def audit(f, crosswalk):
    require(f.get("task") == "136F" and crosswalk.get("task") == "CONSUMABLE_BASIS_CROSSWALK",
            "wrong source task")
    require(crosswalk.get("summary", {}).get("conflicts") == 24 and
            crosswalk.get("accepted_cost_basis") is None, "basis crosswalk differs")
    rows = f["evidence"]["raw_transfers"]
    require(len(rows) == 691, "saved transfer snapshot changed; review new coverage first")
    cases = crosswalk["cases"]
    require(len(cases) == 24 and len({c["sale_hash"] for c in cases}) == 24,
            "expected 24 distinct conflict hashes")
    sale_keys = {c["sale_transfer_key"]: c for c in cases}
    require(len(sale_keys) == 24, "sale transfer keys not unique")
    wallet = None
    observations = []
    seen = set()
    for row in rows:
        key = row["transfer_key"]
        require(key not in seen, f"duplicate transfer key {key}")
        seen.add(key)
        require(row["token_symbol"] == "ACI" and row["token_type"] == "ERC-1155" and
                str(row["token_id"]) in ("1", "2"), f"unexpected token: {key}")
        quantity = int(row["amount_raw"])
        require(quantity > 0 and str(quantity) == str(row["amount_raw"]),
                f"non-integer or nonpositive quantity: {key}")
        from_addr, to_addr = row["from_address"].lower(), row["to_address"].lower()
        if key in sale_keys:
            candidate = from_addr
            wallet = wallet or candidate
            require(wallet == candidate and sale_keys[key]["sale_hash"] == row["tx_hash"].lower() and
                    sale_keys[key]["token_id"] == str(row["token_id"]),
                    f"sale crosswalk differs from raw transfer: {key}")
        observations.append((row, quantity, from_addr, to_addr, utc(row["timestamp"])))
    require(wallet is not None, "no wallet established from sale crosswalk")
    movements = defaultdict(list)
    for row, quantity, from_addr, to_addr, stamp in observations:
        require((from_addr == wallet) != (to_addr == wallet),
                f"transfer does not touch exactly one wallet side: {row['transfer_key']}")
        incoming = to_addr == wallet
        peer = from_addr if incoming else to_addr
        kind = ("MINT_IN" if peer == ZERO else "TRANSFER_IN") if incoming else (
            "BURN_OUT" if peer == ZERO else "TRANSFER_OUT")
        movements[str(row["token_id"])].append({
            "transfer_key": row["transfer_key"], "tx_hash": row["tx_hash"].lower(),
            "timestamp_utc": stamp.isoformat(), "block_number": int(row["block_number"]),
            "log_index": int(row["log_index"]), "token_id": str(row["token_id"]),
            "kind": kind, "quantity": quantity, "delta": quantity if incoming else -quantity,
            "peer": peer, "is_sale_conflict": row["transfer_key"] in sale_keys})
    require(set(movements) == {"1", "2"}, "both token IDs expected")
    by_token = {}
    sale_results = []
    for token, flow in sorted(movements.items()):
        flow.sort(key=lambda r: (r["block_number"], r["log_index"], r["transfer_key"]))
        running = 0
        minimum = 0
        minimum_key = None
        counts, totals = Counter(), Counter()
        for item in flow:
            before = running
            running += item["delta"]
            counts[item["kind"]] += 1
            totals[item["kind"]] += item["quantity"]
            if running < minimum:
                minimum = running
                minimum_key = item["transfer_key"]
            if item["is_sale_conflict"]:
                sale_results.append({"sale_hash": item["tx_hash"], "token_id": token,
                                     "sale_transfer_key": item["transfer_key"],
                                     "sale_utc": item["timestamp_utc"],
                                     "observed_quantity": item["quantity"],
                                     "net_flow_before_sale_from_zero": before,
                                     "net_flow_after_sale_from_zero": running,
                                     "opening_inventory": "UNKNOWN",
                                     "assigned_purchase_lot": None,
                                     "accepted_cost_basis": None, "accepted_profit": None})
        by_token[token] = {
            "first_observed_utc": flow[0]["timestamp_utc"],
            "last_observed_utc": flow[-1]["timestamp_utc"],
            "movement_rows": len(flow), "counts_by_shape": dict(sorted(counts.items())),
            "quantities_by_shape": dict(sorted(totals.items())),
            "net_observed_change": running,
            "minimum_observed_prefix_from_zero": minimum,
            "minimum_opening_units_needed_to_avoid_negative_observed_path": -minimum,
            "first_key_reaching_minimum": minimum_key,
            "actual_opening_inventory": None, "actual_closing_inventory": None}
    require(len(sale_results) == 24 and {s["sale_transfer_key"] for s in sale_results} == set(sale_keys),
            "sale transfer coverage mismatch")
    require(Counter(s["token_id"] for s in sale_results) == Counter({"1": 6, "2": 18}),
            "sale token counts changed")
    sale_results.sort(key=lambda s: (s["sale_utc"], s["sale_hash"]))
    return wallet, by_token, sale_results


def save(folder, report):
    folder.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V100_Consumable_Quantity_Audit_" + datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S_%fZ")
    jp, mp, cp = (folder / (stem + ext) for ext in (".json", ".md", ".csv"))
    with jp.open("x", encoding="utf-8") as dest:
        json.dump(report, dest, indent=2)
        dest.write("\n")
    fields = ("sale_hash", "token_id", "sale_utc", "observed_quantity",
              "net_flow_before_sale_from_zero", "net_flow_after_sale_from_zero",
              "opening_inventory", "accepted_cost_basis", "accepted_profit")
    with cp.open("x", encoding="utf-8-sig", newline="") as dest:
        writer = csv.DictWriter(dest, fieldnames=fields)
        writer.writeheader()
        for sale in report["sale_cases"]:
            writer.writerow({key: sale[key] for key in fields})
    lines = ["# AxieOS V1.0 — Consumable quantity audit", "",
             "Saved ERC-1155 transfer movements only. The observed path begins on "
             "2026-05-13 and does not establish actual opening inventory.", "",
             "| Token | Rows | Net change | Minimum opening units needed | Actual opening |",
             "| --- | ---: | ---: | ---: | --- |"]
    for token, item in report["by_token_id"].items():
        lines.append(f"| {token} | {item['movement_rows']} | {item['net_observed_change']} | "
                     f"{item['minimum_opening_units_needed_to_avoid_negative_observed_path']} | UNKNOWN |")
    lines += ["", "The minimum is a lower bound for this saved transfer path, not an accepted "
              "opening balance. Movements may have missing earlier sources. Mint and burn "
              "shapes do not by themselves establish a zero-cost acquisition or expense. "
              "The 24 sales have no assigned purchase lots; purchase candidates are not "
              "evidence of remaining quantity after intervening use.", "",
              "Accepted cost basis and profit: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN", "",
              "Database opened: NO | Writes: 0 | Network: 0", ""]
    mp.write_text("\n".join(lines), encoding="utf-8")
    return jp, mp, cp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transfers", type=Path, help="exact Task136F JSON path")
    parser.add_argument("--crosswalk", type=Path, help="exact V1.0 basis crosswalk JSON path")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    fp = selected(args.transfers, F_DIR, F_PATTERN)
    cp = selected(args.crosswalk, C_DIR, C_PATTERN)
    f, f_src = load(fp)
    c, c_src = load(cp)
    wallet, by_token, sales = audit(f, c)
    report = {"project": "AxieOS", "version": "1.0-pilot",
              "task": "CONSUMABLE_QUANTITY_AUDIT",
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "sources": {"136F": f_src, "basis_crosswalk": c_src},
              "wallet": wallet, "by_token_id": by_token, "sale_cases": sales,
              "sale_conflicts": len(sales), "accepted_opening_inventory": None,
              "accepted_cost_basis": None, "accepted_profit": None,
              "unified_finance": "HOLD", "checkpoint96": "OPEN",
              "database_opened": False, "database_writes": 0, "network_calls": 0}
    paths = save(args.output_dir, report)
    print("AXIEOS V1.0 - CONSUMABLE QUANTITY AUDIT")
    print("Transfer rows:", sum(x["movement_rows"] for x in by_token.values()),
          "| Sale conflicts:", len(sales))
    print("Minimum opening units for saved path:",
          {key: val["minimum_opening_units_needed_to_avoid_negative_observed_path"]
           for key, val in by_token.items()})
    print("Accepted opening inventory, cost basis and profit: UNKNOWN")
    print("Reports:", *paths)
    print("Database opened: NO | Writes: 0 | Network: 0 | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
