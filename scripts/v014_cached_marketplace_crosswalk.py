r"""Task136X: crosswalk cached Axie/WETH transfer pairs without accepting finance totals.

From the AxieOS repository root:
    py -B .\scripts\v014_cached_marketplace_crosswalk.py

Optional: --input reports\axieos_v014\task136w\<schema-1.1-report>.json
Only reads an offline Task136W JSON file. Does not open SQLite or use the network.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("STOP: " + message)


def find_input(directory: Path) -> Path:
    matches = []
    for path in directory.glob("AxieOS_V014_Task136W_Post_Accounting_Cache_Gap_*.json"):
        with path.open(encoding="utf-8") as stream:
            document = json.load(stream)
        if document.get("report_schema_version") == "1.1":
            matches.append((document.get("created_at_utc", ""), path))
    require(bool(matches), f"no Task136W schema 1.1 JSON in {directory}; pass --input PATH")
    return max(matches)[1]


def positive_integer(value: object, label: str) -> int:
    require(isinstance(value, str) and value.isdecimal(), f"{label}: invalid raw integer")
    result = int(value)
    require(result > 0, f"{label}: must be positive")
    return result


def weth_display(raw: str) -> str:
    try:
        amount = Decimal(raw) / Decimal(10) ** 18
    except InvalidOperation as exc:
        raise ValueError("STOP: invalid WETH raw quantity") from exc
    return format(amount, "f")


def candidate(row: dict, owned: set[str]) -> dict | None:
    transfers = row["raw_transfer_rows"]
    weth = [t for t in transfers if t.get("token_symbol") == "WETH"]
    axie = [t for t in transfers if t.get("token_symbol") == "AXIE"]
    if len(transfers) != 2 or len(weth) != 1 or len(axie) != 1:
        return None
    w, a = weth[0], axie[0]
    directions = (w["wallet_relation"], a["wallet_relation"])
    if directions == ("FROM_REGISTERED_OWNED", "TO_REGISTERED_OWNED"):
        shape = "PURCHASE_SHAPED"
    elif directions == ("TO_REGISTERED_OWNED", "FROM_REGISTERED_OWNED"):
        shape = "SALE_SHAPED"
    else:
        return None
    txrows = row["raw_transaction_rows"]
    require(w["token_type"] == "ERC-20" and w["decimals"] == 18,
            f"{row['txhash']}: unexpected WETH token type or decimals")
    require(a["token_type"] == "ERC-721" and a["amount_raw"] == "1",
            f"{row['txhash']}: unexpected Axie transfer type or quantity")
    require(w["block_number"] == a["block_number"] and
            w["timestamp"] == a["timestamp"] and
            w["log_index"] != a["log_index"],
            f"{row['txhash']}: mismatched transfer block/time/log")
    require(a.get("token_id") and str(a["token_id"]).isdecimal(),
            f"{row['txhash']}: missing numeric Axie ID")
    positive_integer(w["amount_raw"], "WETH amount_raw")
    require(all((w["from_address"], w["to_address"], a["from_address"], a["to_address"])),
            f"{row['txhash']}: missing transfer endpoint")
    require((w["from_address"].lower() in owned) == (shape == "PURCHASE_SHAPED") and
            (w["to_address"].lower() in owned) == (shape == "SALE_SHAPED") and
            (a["to_address"].lower() in owned) == (shape == "PURCHASE_SHAPED") and
            (a["from_address"].lower() in owned) == (shape == "SALE_SHAPED"),
            f"{row['txhash']}: wallet direction inconsistent with endpoints")
    require(len(txrows) <= 1, f"{row['txhash']}: multiple raw transaction rows")
    if txrows:
        require(txrows[0]["block_number"] == w["block_number"],
                f"{row['txhash']}: raw transaction block mismatch")
    return {
        "txhash": row["txhash"],
        "timestamp_utc": row["first_cached_timestamp_utc"],
        "block_number": w["block_number"],
        "axie_id": str(a["token_id"]),
        "shape": shape,
        "weth_transfer_raw": w["amount_raw"],
        "weth_transfer_candidate_quantity": weth_display(w["amount_raw"]),
        "weth_contract": w["token_address"],
        "axie_contract": a["token_address"],
        "weth_from": w["from_address"], "weth_to": w["to_address"],
        "axie_from": a["from_address"], "axie_to": a["to_address"],
        "raw_transaction_present": bool(txrows),
        "raw_transaction_status": txrows[0]["status"] if txrows else None,
        "raw_transaction_from": txrows[0]["from_address"] if txrows else None,
        "raw_fee_raw": txrows[0]["fee_raw"] if txrows else None,
        "observed_weth_role": "OUTGOING_TRANSFER" if shape == "PURCHASE_SHAPED"
                              else "INCOMING_TRANSFER_NOT_SALE_GROSS",
        "financial_treatment": "CANDIDATE_ONLY",
    }


def build(source: dict, source_path: Path) -> dict:
    require(source.get("task") == "136W" and source.get("report_schema_version") == "1.1",
            "input must be Task136W schema 1.1 JSON")
    require(source.get("database_writes") == 0 and source.get("network_calls") == 0 and
            source.get("checkpoint96") == "OPEN" and
            source.get("accepted_financial_totals") is None,
            "unexpected source validation status")
    rows = source["candidate_rows"]
    require(len(rows) == source["coverage"]["candidate_hashes"], "source hash count mismatch")
    hashes = [r["txhash"].lower() for r in rows]
    require(len(hashes) == len(set(hashes)), "duplicate source hash")
    require(all(not r["stored_accounting_row_present"] and
                r["stored_ledger_row_count"] == 0 for r in rows),
            "source contains previously stored hash")
    owned = {w["address"].lower() for w in source["registered_owned_wallets"]}
    require(len(owned) >= 1, "missing registered owned wallets")
    pairs = [c for r in rows if (c := candidate(r, owned)) is not None]
    pairs.sort(key=lambda r: (r["timestamp_utc"], r["txhash"]))
    counts = Counter(r["shape"] for r in pairs)
    purchases = defaultdict(list)
    sales = defaultdict(list)
    for pair in pairs:
        (purchases if pair["shape"] == "PURCHASE_SHAPED" else sales)[pair["axie_id"]].append(pair)
    sequences = []
    for axie_id in sorted(purchases.keys() & sales.keys(), key=int):
        for buy in purchases[axie_id]:
            for sale in sales[axie_id]:
                if buy["timestamp_utc"] < sale["timestamp_utc"]:
                    sequences.append({"axie_id": axie_id,
                                      "purchase_hash": buy["txhash"],
                                      "purchase_timestamp_utc": buy["timestamp_utc"],
                                      "sale_hash": sale["txhash"],
                                      "sale_timestamp_utc": sale["timestamp_utc"],
                                      "status": "SAME_AXIE_ID_CHRONOLOGICAL_CANDIDATE"})
    # Multiple acquisitions/disposals of the same ID need a separate ownership timeline.
    ambiguous_ids = sorted((k for k in purchases.keys() & sales.keys()
                            if len(purchases[k]) != 1 or len(sales[k]) != 1), key=int)
    counts_by_id = {"purchase_only_ids": len(purchases.keys() - sales.keys()),
                    "sale_only_ids": len(sales.keys() - purchases.keys()),
                    "both_ids": len(purchases.keys() & sales.keys())}
    pilot = []
    for shape in ("PURCHASE_SHAPED", "SALE_SHAPED"):
        group = [r for r in pairs if r["shape"] == shape]
        pilot.extend(group[:3] + group[-3:] if len(group) > 6 else group)
    return {"project": "AxieOS", "version": "0.14", "task": "136X",
            "source_report": str(source_path),
            "source_created_at_utc": source["created_at_utc"],
            "source_accounting_cutoff_utc": source["cutoff"]["accounting_latest_utc"],
            "source_cache_latest_utc": source["cutoff"]["raw_latest_utc"],
            "coverage": {"cached_hashes": len(rows), "exact_two_transfer_weth_axie_pairs": len(pairs),
                         "purchase_shaped": counts["PURCHASE_SHAPED"],
                         "sale_shaped": counts["SALE_SHAPED"],
                         "purchase_shaped_with_raw_transaction": sum(r["raw_transaction_present"] for r in pairs
                                                                    if r["shape"] == "PURCHASE_SHAPED"),
                         "sale_shaped_with_raw_transaction": sum(r["raw_transaction_present"] for r in pairs
                                                                if r["shape"] == "SALE_SHAPED"),
                         "chronological_same_id_sequences": len(sequences),
                         "ambiguous_repeated_asset_ids": ambiguous_ids, **counts_by_id,
                         "pilot_hashes": len(pilot)},
            "pair_candidates": pairs, "same_id_sequences": sequences,
            "pilot": [{"txhash": r["txhash"], "axie_id": r["axie_id"],
                       "shape": r["shape"], "timestamp_utc": r["timestamp_utc"]} for r in pilot],
            "limitations": ["Incoming WETH is an observed transfer, not verified sale gross.",
                            "The raw transaction record can be absent when the wallet receives a sale.",
                            "A matching Axie ID and chronology do not establish historical cost basis or net profit.",
                            "Activity after the raw cache cutoff is outside this report."],
            "accepted_financial_totals": None, "verified_profit": None,
            "database_opened": False, "database_writes": 0, "network_calls": 0,
            "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136X Cached marketplace flow crosswalk", "",
             f"Source: `{report['source_report']}` (Task136W schema 1.1).", "",
             f"From **{c['cached_hashes']}** cached wallet hashes, **{c['exact_two_transfer_weth_axie_pairs']}** "
             "contain exactly one WETH transfer and one Axie transfer in the same block.", "",
             "| Evidence shape | Hashes | Raw transaction present |",
             "|---|---:|---:|",
             f"| WETH out, Axie in | {c['purchase_shaped']} | {c['purchase_shaped_with_raw_transaction']} |",
             f"| Axie out, WETH in | {c['sale_shaped']} | {c['sale_shaped_with_raw_transaction']} |", "",
             f"Same Axie ID in chronological purchase-shaped then sale-shaped flows: "
             f"**{c['chronological_same_id_sequences']}** candidate sequences. "
             f"Purchase-only IDs: **{c['purchase_only_ids']}**; sale-only IDs: **{c['sale_only_ids']}**. "
             f"Repeated IDs requiring separate timeline review: **{len(c['ambiguous_repeated_asset_ids'])}**.", "",
             "The companion JSON contains every pair, raw WETH transfer quantity, endpoints, "
             "and a bounded 12-hash pilot (earliest and latest three per shape).", "",
             "Sale gross, marketplace fee, cost basis, gas payer for transfer-only rows, "
             "PHP valuation, realized profit, and capital recovery: **UNKNOWN**. "
             "No pair is accepted as a financial event.", "",
             f"Raw cache ends at **{report['source_cache_latest_utc']}**; later activity requires separate evidence.", "",
             "Database opened: NO | Writes: 0 | Network calls: 0", "",
             "VALIDATION: PASS (offline candidate crosswalk only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--input-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136x"))
    args = parser.parse_args()
    source_path = args.input or find_input(args.input_dir)
    require(source_path.is_file(), f"missing source: {source_path}")
    with source_path.open(encoding="utf-8") as stream:
        source = json.load(stream)
    report = build(source, source_path)
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136X_Cached_Marketplace_Crosswalk_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
            + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with mp.open("x", encoding="utf-8") as stream:
        stream.write(markdown(report))
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136X - CACHED MARKETPLACE FLOW CROSSWALK")
    print(f"Cached hashes: {c['cached_hashes']} | Candidate pairs: {c['exact_two_transfer_weth_axie_pairs']}")
    print(f"Purchase-shaped: {c['purchase_shaped']} | Sale-shaped: {c['sale_shaped']} | "
          f"Same-ID sequences: {c['chronological_same_id_sequences']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network calls: 0")
    print("VALIDATION: PASS (offline candidate crosswalk only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
