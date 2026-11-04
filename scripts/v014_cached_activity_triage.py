r"""Task136Z: offline structural inventory of all post-accounting cached hashes.

Run at the AxieOS repository root:
    py -B .\scripts\v014_cached_activity_triage.py

Reads Task136W schema 1.1 JSON. No database or network access, and no finance
event acceptance or monetary totals. Every source hash receives one bucket.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError("STOP: " + reason)


def find_source(directory: Path) -> Path:
    matches = []
    for path in directory.glob("AxieOS_V014_Task136W_Post_Accounting_Cache_Gap_*.json"):
        with path.open(encoding="utf-8") as stream:
            d = json.load(stream)
        if d.get("report_schema_version") == "1.1":
            matches.append((d.get("created_at_utc", ""), path))
    require(bool(matches), f"no Task136W schema 1.1 JSON in {directory}; pass --input PATH")
    return max(matches)[1]


def pair_shape(transfers: list[dict]) -> tuple[str, dict, dict] | None:
    if len(transfers) != 2:
        return None
    weth = [t for t in transfers if t.get("token_symbol") == "WETH"]
    if len(weth) != 1:
        return None
    w = weth[0]
    a = next(t for t in transfers if t is not w)
    if w["wallet_relation"] == "FROM_REGISTERED_OWNED" and \
            a["wallet_relation"] == "TO_REGISTERED_OWNED":
        shape = "WETH_OUT_ASSET_IN"
    elif w["wallet_relation"] == "TO_REGISTERED_OWNED" and \
            a["wallet_relation"] == "FROM_REGISTERED_OWNED":
        shape = "ASSET_OUT_WETH_IN"
    else:
        return None
    require(w["token_type"] == "ERC-20" and w["decimals"] == 18,
            "unexpected WETH type or decimals in opposing pair")
    require(w["block_number"] == a["block_number"] and w["timestamp"] == a["timestamp"],
            "opposing pair has inconsistent block or timestamp")
    return shape, w, a


def build(source: dict, source_path: Path) -> dict:
    require(source.get("task") == "136W" and source.get("report_schema_version") == "1.1",
            "input must be Task136W schema 1.1")
    require(source.get("accepted_financial_totals") is None and
            source.get("checkpoint96") == "OPEN", "unexpected source finance state")
    rows = source["candidate_rows"]
    require(len(rows) == source["coverage"]["candidate_hashes"], "candidate count mismatch")
    hashes = [str(r["txhash"]).lower() for r in rows]
    require(len(hashes) == len(set(hashes)), "duplicate cached hash")
    require(all(not r["stored_accounting_row_present"] and
                r["stored_ledger_row_count"] == 0 for r in rows),
            "cached hash already present in ledger or accounting")
    inventory = []
    for row in rows:
        transfers, txrows = row["raw_transfer_rows"], row["raw_transaction_rows"]
        require(bool(transfers or txrows), f"{row['txhash']}: empty raw evidence")
        pair = pair_shape(transfers)
        if pair:
            shape, weth, asset = pair
            bucket = "OPPOSING_WETH_ASSET_PAIR"
            asset_symbol = asset["token_symbol"] or asset["token_type"]
            paired_detail = {"shape": shape, "asset_symbol": asset_symbol,
                             "asset_type": asset["token_type"],
                             "asset_contract": asset["token_address"],
                             "asset_token_id": asset["token_id"],
                             "asset_amount_raw": asset["amount_raw"],
                             "asset_decimals": asset["decimals"],
                             "weth_amount_raw": weth["amount_raw"],
                             "weth_contract": weth["token_address"]}
        elif transfers:
            bucket = "OTHER_TOKEN_TRANSFER_ACTIVITY"
            paired_detail = None
        else:
            bucket = "RAW_TRANSACTION_WITHOUT_WALLET_TOKEN_TRANSFER"
            paired_detail = None
        inventory.append({"txhash": row["txhash"],
                          "first_cached_timestamp_utc": row["first_cached_timestamp_utc"],
                          "bucket": bucket, "pair": paired_detail,
                          "raw_transaction_count": len(txrows),
                          "raw_transfer_count": len(transfers),
                          "methods": sorted({str(t["method"] or "UNSPECIFIED") for t in txrows}),
                          "transaction_statuses": sorted({str(t["status"] or "UNSPECIFIED") for t in txrows}),
                          "token_symbols": sorted({str(t["token_symbol"] or t["token_type"])
                                                   for t in transfers}),
                          "transfer_directions": sorted({t["wallet_relation"] for t in transfers}),
                          "source_fee_raw_present": any(t["fee_raw"] not in (None, "") for t in txrows),
                          "financial_treatment": "UNCLASSIFIED_CANDIDATE"})
    bucket_counts = Counter(r["bucket"] for r in inventory)
    pair_counts = Counter((r["pair"]["asset_symbol"], r["pair"]["shape"])
                          for r in inventory if r["pair"])
    method_counts = Counter(method for row in inventory for method in row["methods"])
    require(sum(bucket_counts.values()) == len(rows), "not all hashes assigned one bucket")
    return {"project": "AxieOS", "version": "0.14", "task": "136Z",
            "source_report": str(source_path),
            "source_created_at_utc": source["created_at_utc"],
            "source_cache_latest_utc": source["cutoff"]["raw_latest_utc"],
            "coverage": {"cached_hashes": len(rows),
                         "bucket_counts": dict(sorted(bucket_counts.items())),
                         "opposing_pair_asset_shape_counts": [
                             {"asset_symbol": asset, "shape": shape, "hashes": n}
                             for (asset, shape), n in sorted(pair_counts.items())],
                         "method_counts": dict(sorted(method_counts.items())),
                         "raw_transaction_status_counts": source["coverage"]["raw_transaction_status_counts"]},
            "inventory_rows": inventory,
            "interpretation": ["Buckets describe raw transfer structure, not income or expense.",
                               "An incoming WETH transfer does not establish a sale gross or fee.",
                               "A raw transaction fee does not establish its accounting treatment.",
                               "Cached activity ends at the source cache cutoff."],
            "accepted_financial_totals": None, "accepted_new_events": 0,
            "database_opened": False, "database_writes": 0, "network_calls": 0,
            "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136Z Cached activity triage", "",
             f"Source: `{report['source_report']}` (Task136W schema 1.1).", "",
             f"All **{c['cached_hashes']}** post-accounting cached hashes have one structural bucket.", "",
             "| Bucket | Hashes |", "|---|---:|"]
    for bucket, n in c["bucket_counts"].items():
        lines.append(f"| {bucket} | {n} |")
    lines += ["", "## Two-transfer WETH and asset pairs", "",
              "| Asset symbol | WETH out, asset in | Asset out, WETH in |", "|---|---:|---:|"]
    table = {(r["asset_symbol"], r["shape"]): r["hashes"]
             for r in c["opposing_pair_asset_shape_counts"]}
    for asset in sorted({asset for asset, _ in table}):
        lines.append(f"| {asset} | {table.get((asset, 'WETH_OUT_ASSET_IN'), 0)} | "
                     f"{table.get((asset, 'ASSET_OUT_WETH_IN'), 0)} |")
    lines += ["", "These pair shapes include consumables and swaps. The companion JSON preserves "
              "every hash, token ID, raw quantity, method and direction for later source-specific review. "
              "No pair is accepted as a marketplace trade by this report.", "",
              f"The raw cache ends at **{report['source_cache_latest_utc']}**; later activity is outside scope.", "",
              "Verified income, expenses, basis, profit and PHP recovery: **UNKNOWN**.", "",
              "Database opened: NO | Writes: 0 | Network calls: 0", "",
              "VALIDATION: PASS (structural inventory only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--input-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136z"))
    args = parser.parse_args()
    source_path = args.input or find_source(args.input_dir)
    require(source_path.is_file(), f"missing source: {source_path}")
    with source_path.open(encoding="utf-8") as stream:
        source = json.load(stream)
    report = build(source, source_path)
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136Z_Cached_Activity_Triage_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
            + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with mp.open("x", encoding="utf-8") as stream:
        stream.write(markdown(report))
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136Z - CACHED ACTIVITY TRIAGE")
    print(f"Cached hashes: {c['cached_hashes']} | Buckets: {c['bucket_counts']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network calls: 0")
    print("VALIDATION: PASS (structural inventory only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
