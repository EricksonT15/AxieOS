r"""Task136BD: offline raw-transfer review of recent marketplace candidates.

Run from the AxieOS repository root:
    py -B .\scripts\v014_recent_marketplace_review.py

Uses only SHA-linked Task136BC/BB/AY/AU JSON. Checks each candidate against
the exact imported raw transfers and separates NFT pairs from fungible routes.
Does not open SQLite, call a network, or accept financial treatment.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from v013_fullrow_materialization_sandbox import human_amount, source_hash, utc_datetime
from v014_post_apply_reconcile import require
from v014_raw_import_clone import by_sha, latest, load


def analyze(bc: dict, bb: dict, ay: dict, au: dict,
            shas: dict[str, str]) -> dict:
    require(all(doc.get("task") == task and doc.get("checkpoint96") == "OPEN"
                and doc.get("accepted_financial_totals") is None
                for task, doc in (("136BC", bc), ("136BB", bb),
                                  ("136AY", ay), ("136AU", au))) and
            all(bc["sources"][t]["sha256"] == shas[t]
                for t in ("136BB", "136AY")) and
            bb["sources"]["136AY"]["sha256"] == shas["136AY"] and
            ay["sources"]["136AU"]["sha256"] == shas["136AU"],
            "Task136BC/BB/AY/AU source chain or financial boundary differs")
    candidates = bc["candidates"]
    by_hash = {str(row["txhash"]).lower(): row for row in candidates}
    ledger = ay["guarded_ledger_rows"]
    raw = au["normalized_new_transfers"]
    require(len(by_hash) == len(candidates) == bc["coverage"]["recent_hashes"] ==
            bb["coverage"]["inserted_hashes_exact"] and
            len(ledger) == bc["coverage"]["recent_ledger_rows"] ==
                bb["coverage"]["inserted_rows_exact"] and
            len(raw) == au["coverage"]["unique_transfer_rows"] == len(ledger),
            "recent candidate, raw transfer or ledger counts differ")
    raw_by_source = {source_hash(t["transfer_key"]): t for t in raw}
    require(len(raw_by_source) == len(raw) and
            {r["source_row_hash"] for r in ledger} == set(raw_by_source),
            "new ledger source keys do not match raw transfer snapshot")
    grouped_ledger, grouped_raw = defaultdict(list), defaultdict(list)
    for row in ledger:
        h, t = str(row["txhash"]).lower(), raw_by_source[row["source_row_hash"]]
        require(h == str(t["tx_hash"]).lower() and
                row["blockno"] == t["block_number"] and
                row["unixtimestamp"] == utc_datetime(t["timestamp"])[0] and
                str(row["from_address"]).lower() == str(t["from_address"]).lower() and
                str(row["to_address"]).lower() == str(t["to_address"]).lower() and
                row["token_collectibles"] == t["token_name"] and
                row["txn_fee_ron"] is None,
                f"{h}: raw provenance differs from guarded ledger row")
        value_in, value_out = Decimal(str(row["value_in"])), Decimal(str(row["value_out"]))
        amount = Decimal(human_amount(t["amount_raw"], t["decimals"]))
        require(amount > 0 and
                ((value_in == amount and value_out == 0) or
                 (value_out == amount and value_in == 0)),
                f"{h}: raw transfer amount/direction differs from ledger")
        grouped_ledger[h].append(row)
        grouped_raw[h].append(t)
    require(set(grouped_ledger) == set(by_hash) and
            all(len(grouped_ledger[h]) == by_hash[h]["ledger_rows"]
                for h in by_hash),
            "Task136BC grouped ledger coverage differs")
    txs = {str(row["tx_hash"]).lower(): row
           for row in au["normalized_new_transactions"]}
    require(len(txs) == au["coverage"]["unique_transaction_rows"],
            "Task136AU new transaction identities duplicate")
    selected = [r for r in candidates if r["legacy_label"] in
                ("MARKETPLACE_BUY", "MARKETPLACE_SALE")]
    require(len(selected) == sum(bc["coverage"]["legacy_labels"].get(label, 0)
                                 for label in ("MARKETPLACE_BUY", "MARKETPLACE_SALE")) and
            len(selected) == sum(bc["coverage"]["movement_shapes"].get(shape, 0)
                                 for shape in ("BUY_CANDIDATE", "SALE_CANDIDATE")),
            "legacy labels and marketplace-shaped counts differ")
    out = []
    for item in sorted(selected, key=lambda r: r["txhash"].lower()):
        h = str(item["txhash"]).lower()
        transfers = grouped_raw[h]
        paired = len(transfers) == 2
        weth = [t for t in transfers if t.get("token_symbol") == "WETH"]
        others = [t for t in transfers if t.get("token_symbol") != "WETH"]
        exact = paired and len(weth) == len(others) == 1
        expected_shape = ("BUY_CANDIDATE" if item["legacy_label"] == "MARKETPLACE_BUY"
                          else "SALE_CANDIDATE")
        require(item["shape"] == expected_shape,
                f"{h}: candidate label and wallet movement shape differ")
        tx = txs.get(h)
        if tx is not None:
            require(tx["status"] == "ok" and
                    tx["method"] == item["method"] and item["status"] == "Success",
                    f"{h}: raw transaction method/status differ from shadow")
            tx_source = "NEW_RAW_TRANSACTION"
        elif item["method"] is not None and item["status"] == "Success":
            tx_source = "PRIOR_RAW_TRANSACTION"
        else:
            require(item["method"] is None and item["status"] is None,
                    f"{h}: missing raw transaction state differs")
            tx_source = "TRANSFER_ONLY"
        review = "NONEXACT_PAIR_REVIEW"
        asset_symbol = asset_type = token_id = None
        if exact:
            w, asset = weth[0], others[0]
            wr, ar = (raw_by_source[r["source_row_hash"]]
                      for r in grouped_ledger[h])
            require({wr["transfer_key"], ar["transfer_key"]} ==
                    {w["transfer_key"], asset["transfer_key"]} and
                    w["token_type"] == "ERC-20" and int(w["decimals"]) == 18 and
                    w["block_number"] == asset["block_number"] and
                    w["timestamp"] == asset["timestamp"] and
                    w["log_index"] != asset["log_index"],
                    f"{h}: paired raw transfer identity, block or WETH metadata differs")
            pay_ledger = next(r for r in grouped_ledger[h]
                              if r["source_row_hash"] == source_hash(w["transfer_key"]))
            asset_ledger = next(r for r in grouped_ledger[h]
                                if r["source_row_hash"] == source_hash(asset["transfer_key"]))
            weth_in = Decimal(str(pay_ledger["value_in"])) > 0
            asset_in = Decimal(str(asset_ledger["value_in"])) > 0
            require((not weth_in and asset_in) if expected_shape == "BUY_CANDIDATE"
                    else (weth_in and not asset_in),
                    f"{h}: paired raw wallet flow differs from shadow")
            asset_symbol, asset_type, token_id = (
                asset["token_symbol"], asset["token_type"], asset.get("token_id"))
            if asset_type == "ERC-20":
                review = "FUNGIBLE_EXCHANGE_REVIEW"
            elif asset_type in ("ERC-721", "ERC-1155"):
                review = "NFT_PAIR_CANDIDATE"
            else:
                review = "OTHER_ASSET_REVIEW"
            if asset_symbol == "AXIE":
                require(asset_type == "ERC-721" and
                        str(asset["amount_raw"]) == "1" and
                        str(token_id or "").isdecimal(),
                        f"{h}: AXIE token identity or quantity differs")
        out.append({"txhash": h, "legacy_label": item["legacy_label"],
                    "shape": expected_shape, "ledger_rows": item["ledger_rows"],
                    "raw_transfer_rows": len(transfers),
                    "exact_weth_asset_pair": exact,
                    "asset_symbol": asset_symbol, "asset_type": asset_type,
                    "asset_token_id": token_id,
                    "raw_transaction_source": tx_source,
                    "review_lane": review,
                    "accepted_marketplace_transaction": False,
                    "financial_treatment": "UNREVIEWED_CANDIDATE"})
    require(len(out) == len(selected) and
            sum(r["shape"] == "BUY_CANDIDATE" for r in out) ==
                bc["coverage"]["legacy_labels"].get("MARKETPLACE_BUY", 0) and
            sum(r["shape"] == "SALE_CANDIDATE" for r in out) ==
                bc["coverage"]["legacy_labels"].get("MARKETPLACE_SALE", 0),
            "candidate marketplace partition differs")
    return {"project": "AxieOS", "version": "0.14", "task": "136BD",
            "sources": {task: {"sha256": shas[task]} for task in shas},
            "coverage": {"recent_hashes": len(by_hash),
                         "marketplace_shaped": len(out),
                         "exact_weth_asset_pairs": sum(r["exact_weth_asset_pair"] for r in out),
                         "by_review_lane": dict(sorted(Counter(r["review_lane"] for r in out).items())),
                         "by_asset_and_shape": dict(sorted(Counter(
                             str(r["asset_symbol"]) + "/" + r["shape"] for r in out).items())),
                         "raw_transaction_source": dict(sorted(Counter(
                             r["raw_transaction_source"] for r in out).items()))},
            "candidate_pairs": out, "accepted_financial_totals": None,
            "database_opened": False, "database_writes": 0,
            "network_calls": 0, "checkpoint96": "OPEN"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bc", type=Path)
    for suffix in ("bc", "bb", "ay", "au"):
        parser.add_argument(f"--{suffix}-dir", type=Path,
                            default=Path(f"reports/axieos_v014/task136{suffix}"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("reports/axieos_v014/task136bd"))
    args = parser.parse_args()
    bp = args.bc or latest(args.bc_dir, "136BC")
    bc, bc_sha = load(bp)
    paths = {"136BC": bp,
             "136BB": by_sha(args.bb_dir, bc["sources"]["136BB"]["sha256"], "136BB"),
             "136AY": by_sha(args.ay_dir, bc["sources"]["136AY"]["sha256"], "136AY")}
    bb, bb_sha = load(paths["136BB"])
    ay, ay_sha = load(paths["136AY"])
    paths["136AU"] = by_sha(args.au_dir, ay["sources"]["136AU"]["sha256"], "136AU")
    au, au_sha = load(paths["136AU"])
    shas = {"136BC": bc_sha, "136BB": bb_sha,
            "136AY": ay_sha, "136AU": au_sha}
    report = analyze(bc, bb, ay, au, shas)
    for task, path in paths.items():
        report["sources"][task]["filename"] = path.name
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136BD_Recent_Marketplace_Review_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
            "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    c = report["coverage"]
    mp.write_text("\n".join([
        "# AxieOS V0.14 — Task136BD Recent marketplace candidate review", "",
        f"Marketplace-shaped hashes: **{c['marketplace_shaped']}**; "
        f"exact WETH/asset raw pairs: **{c['exact_weth_asset_pairs']}**.", "",
        "| Review lane | Hashes |", "|---|---:|",
        *[f"| {lane} | {count} |" for lane, count in c["by_review_lane"].items()],
        "", "Fungible pairs and incomplete raw routes remain in review. "
        "A raw paired flow is not a verified purchase, sale or profit. "
        "Non-Axie NFT token IDs are not Axie numbers.", "",
        "Verified income, expenses, profit and PHP recovery: **UNKNOWN**. "
        "Checkpoint 96: **OPEN**.", "",
        "Database opened: NO | Writes: 0 | Network: 0", ""]), encoding="utf-8")
    print("AXIEOS V0.14 - TASK136BD - RECENT MARKETPLACE CANDIDATE REVIEW")
    print(f"Marketplace-shaped: {c['marketplace_shaped']} | "
          f"Exact raw pairs: {c['exact_weth_asset_pairs']}")
    print(f"Review lanes: {c['by_review_lane']}")
    print(f"Asset/shape: {c['by_asset_and_shape']}")
    print("Verified income, expenses, profit and PHP recovery: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (offline candidate crosswalk only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
