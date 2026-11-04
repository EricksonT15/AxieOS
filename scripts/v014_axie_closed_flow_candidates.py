r"""Task136AJ: inspect cached purchase-to-sale Axie flows without profit claims.

From the AxieOS repository root:
    py -B .\scripts\v014_axie_closed_flow_candidates.py

Only reads the Task136AI, Task136X and Task136W JSON reports. Per-ID
observed WETH difference is a wallet-flow candidate, never realized profit,
cost basis, a verified expense, or capital recovery.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError("STOP: " + message)


def load(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing report: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def find(directory: Path, task: str, schema: str | None = None) -> Path:
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        item, _ = load(path)
        if item.get("task") == task and (schema is None or
                                          item.get("report_schema_version") == schema):
            matches.append((item.get("created_at_utc", ""), path))
    require(bool(matches), f"missing Task{task} report in {directory}; pass exact path")
    return max(matches)[1]


def weth(raw: str) -> Decimal:
    require(isinstance(raw, str) and raw.isdecimal() and int(raw) > 0,
            "invalid positive raw WETH transfer quantity")
    return Decimal(raw) / Decimal(10) ** 18


def build(ai: dict, x: dict, w: dict, paths: dict[str, Path], shas: dict[str, str]) -> dict:
    require(ai.get("task") == "136AI" and x.get("task") == "136X" and
            w.get("task") == "136W" and w.get("report_schema_version") == "1.1" and
            all(d.get("checkpoint96") == "OPEN" and d.get("accepted_financial_totals") is None
                for d in (ai, x, w)), "unexpected source task or finance state")
    require(ai["sources"]["136W"]["sha256"] == shas["136W"] and
            ai["sources"]["136W"]["filename"] == paths["136W"].name and
            Path(x["source_report"]).name == paths["136W"].name,
            "Task136AI/X cache source differs from Task136W")
    controls = {str(r["txhash"]).lower(): r for r in ai["new_candidates"]}
    require(len(controls) == ai["coverage"]["new_marketplace_shaped_pairs"] and
            len(controls) == len(ai["new_candidates"]), "Task136AI candidate count differs")
    pairs = {str(r["txhash"]).lower(): r for r in x["pair_candidates"]}
    require(len(pairs) == x["coverage"]["exact_two_transfer_weth_axie_pairs"] ==
            len(x["pair_candidates"]), "Task136X Axie pair count differs")
    require(set(pairs) == {h for h, r in controls.items()
                           if r["review_lane"] == "AXIE_PAIR_CANDIDATE"},
            "Axie pair set differs between Task136AI and Task136X")
    require(all(controls[h]["control_status"] == "HISTORICAL_ENDPOINT_MATCH_CANDIDATE"
                for h in pairs), "Axie payment route lacks historical endpoint match")
    raw = {str(r["txhash"]).lower(): r for r in w["candidate_rows"]}
    require(len(raw) == w["coverage"]["candidate_hashes"] and
            len(raw) == len(w["candidate_rows"]), "Task136W cached hash count differs")
    all_axie_transfers = defaultdict(list)
    for h, row in raw.items():
        for transfer in row["raw_transfer_rows"]:
            if transfer.get("token_symbol") == "AXIE":
                all_axie_transfers[str(transfer["token_id"])].append(
                    {"txhash": h, "timestamp": row["first_cached_timestamp_utc"],
                     "transfer_key": transfer["transfer_key"]})
    sequences = x["same_id_sequences"]
    require(len(sequences) == x["coverage"]["chronological_same_id_sequences"] and
            len({str(s["axie_id"]) for s in sequences}) == len(sequences),
            "Task136X chronological sequences overlap or differ")
    details = []
    for sequence in sorted(sequences, key=lambda s: int(s["axie_id"])):
        token_id = str(sequence["axie_id"])
        bh, sh = str(sequence["purchase_hash"]).lower(), str(sequence["sale_hash"]).lower()
        buy, sale = pairs.get(bh), pairs.get(sh)
        require(buy is not None and sale is not None and bh != sh and
                buy["shape"] == "PURCHASE_SHAPED" and sale["shape"] == "SALE_SHAPED" and
                buy["axie_id"] == sale["axie_id"] == token_id,
                f"{token_id}: missing or mismatched purchase/sale pair")
        require(sequence["purchase_timestamp_utc"] == buy["timestamp_utc"] and
                sequence["sale_timestamp_utc"] == sale["timestamp_utc"] and
                buy["timestamp_utc"] < sale["timestamp_utc"],
                f"{token_id}: chronology differs")
        require(buy["axie_contract"].lower() == sale["axie_contract"].lower() and
                buy["weth_contract"].lower() == sale["weth_contract"].lower(),
                f"{token_id}: token contracts differ")
        require(buy["weth_from"].lower() == sale["weth_to"].lower() and
                buy["axie_to"].lower() == sale["axie_from"].lower(),
                f"{token_id}: purchased and sold wallets differ")
        require(buy["raw_transaction_present"] and buy["raw_transaction_status"] == "ok" and
                not sale["raw_transaction_present"],
                f"{token_id}: raw transaction provenance differs")
        between = [t for t in all_axie_transfers[token_id]
                   if buy["timestamp_utc"] <= t["timestamp"] <= sale["timestamp_utc"]]
        require(len(between) == 2 and {t["txhash"] for t in between} == {bh, sh},
                f"{token_id}: additional cached Axie transfer in the purchase/sale interval")
        b, s = weth(buy["weth_transfer_raw"]), weth(sale["weth_transfer_raw"])
        details.append({"axie_id": token_id, "purchase_hash": bh, "sale_hash": sh,
                        "purchase_utc": buy["timestamp_utc"],
                        "sale_utc": sale["timestamp_utc"],
                        "owned_wallet": buy["axie_to"].lower(),
                        "purchase_weth_sent_observed": format(b, "f"),
                        "sale_weth_received_observed": format(s, "f"),
                        "observed_wallet_weth_difference_before_gas": format(s - b, "f"),
                        "difference_interpretation": "CANDIDATE_WALLET_FLOW_NOT_PROFIT",
                        "sale_gross": None, "marketplace_fee": None,
                        "cost_basis_accepted": None, "gas_payer_verified": False,
                        "realized_profit_accepted": None,
                        "cached_transfer_interval_clear": True,
                        "historical_endpoint_pattern_match": True,
                        "sale_raw_transaction_present": False})
    return {"project": "AxieOS", "version": "0.14", "task": "136AJ",
            "sources": {k: {"filename": paths[k].name, "sha256": shas[k]}
                        for k in sorted(paths)},
            "coverage": {"axie_purchase_shaped_hashes": x["coverage"]["purchase_shaped"],
                         "axie_sale_shaped_hashes": x["coverage"]["sale_shaped"],
                         "closed_cached_axie_sequences": len(details),
                         "purchase_only_axie_ids": x["coverage"]["purchase_only_ids"],
                         "sale_only_axie_ids": x["coverage"]["sale_only_ids"],
                         "sale_raw_transaction_missing_for_sequences": len(details),
                         "cached_axie_transfers_between_purchase_and_sale": 0,
                         "observed_weth_difference_signs": dict(sorted(Counter(
                             "POSITIVE" if Decimal(r["observed_wallet_weth_difference_before_gas"]) > 0
                             else "NEGATIVE" if Decimal(r["observed_wallet_weth_difference_before_gas"]) < 0
                             else "ZERO" for r in details).items()))},
            "closed_flow_candidates": details,
            "accepted_financial_totals": None, "accepted_realized_profit": None,
            "database_opened": False, "database_writes": 0, "network_calls": 0,
            "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136AJ Cached Axie purchase/sale flow candidates", "",
             f"Matched same-ID purchase-to-sale sequences: **{c['closed_cached_axie_sequences']}**. "
             f"Purchase-only IDs: **{c['purchase_only_axie_ids']}**; "
             f"sale-only IDs: **{c['sale_only_axie_ids']}**.", "",
             "| Observed WETH difference sign | Candidate IDs |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in c["observed_weth_difference_signs"].items()]
    lines += ["", "| Axie ID | WETH sent | WETH received | Wallet difference before gas |",
              "|---|---:|---:|---:|"]
    lines += [f"| {r['axie_id']} | {r['purchase_weth_sent_observed']} | "
              f"{r['sale_weth_received_observed']} | "
              f"{r['observed_wallet_weth_difference_before_gas']} |"
              for r in report["closed_flow_candidates"]]
    lines += ["", "The difference subtracts observed WETH transfers for a matched Axie ID. "
              "It is not realized profit or an accepted cost basis. All matched sales lack "
              "a cached raw transaction row; the transfer window cannot prove full ownership "
              "history, seller receipt, fees, gas payer, or later wallet activity. "
              "The JSON preserves transaction hashes and evidence flags for review.", "",
              "Verified income, expenses, profit, and PHP recovery: **UNKNOWN**.", "",
              "Database opened: NO | Writes: 0 | Network: 0", "",
              "VALIDATION: PASS (cached per-ID wallet flow only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ai", type=Path)
    parser.add_argument("--ai-dir", type=Path, default=Path("reports/axieos_v014/task136ai"))
    parser.add_argument("--x", type=Path)
    parser.add_argument("--x-dir", type=Path, default=Path("reports/axieos_v014/task136x"))
    parser.add_argument("--w", type=Path)
    parser.add_argument("--w-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136aj"))
    args = parser.parse_args()
    paths = {"136AI": args.ai or find(args.ai_dir, "136AI"),
             "136X": args.x or find(args.x_dir, "136X"),
             "136W": args.w or find(args.w_dir, "136W", "1.1")}
    docs, shas = {}, {}
    for k, p in paths.items():
        docs[k], shas[k] = load(p)
    report = build(docs["136AI"], docs["136X"], docs["136W"], paths, shas)
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AJ_Axie_Closed_Flow_Candidates_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136AJ - AXIE CLOSED FLOW CANDIDATES")
    print(f"Matched same-ID flows: {c['closed_cached_axie_sequences']} | "
          f"Purchase-only: {c['purchase_only_axie_ids']} | Sale-only: {c['sale_only_axie_ids']}")
    print(f"Observed WETH difference signs: {c['observed_weth_difference_signs']}")
    print("Verified income, expenses, profit, and PHP recovery: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (cached per-ID wallet flow only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
