r"""Task136AH: cross-check shadow marketplace shapes against cached raw transfers.

Run from the AxieOS repository root:
    py -B .\scripts\v014_marketplace_candidate_review.py

Reads only Task136AG, Task136W schema 1.1, and Task136X JSON snapshots.
No SQLite, network, financial totals, or accounting writes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
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
    require(bool(matches), f"no Task{task} report in {directory}; pass its exact path")
    return max(matches)[1]


def direction(transfer: dict, owned: set[str]) -> str:
    a = str(transfer.get("from_address") or "").lower()
    b = str(transfer.get("to_address") or "").lower()
    require(a and b and a != b, "missing or identical transfer endpoints")
    inbound = b in owned and a not in owned
    outbound = a in owned and b not in owned
    require(inbound != outbound, "raw transfer wallet direction ambiguous")
    label = "TO_REGISTERED_OWNED" if inbound else "FROM_REGISTERED_OWNED"
    require(transfer.get("wallet_relation") == label, "raw wallet relation differs from endpoints")
    return "IN" if inbound else "OUT"


def analyze(ag: dict, w: dict, x: dict, digests: dict[str, str],
            filenames: dict[str, str]) -> dict:
    require(ag.get("task") == "136AG" and w.get("task") == "136W" and
            w.get("report_schema_version") == "1.1" and x.get("task") == "136X" and
            all(r.get("checkpoint96") == "OPEN" and
                r.get("accepted_financial_totals") is None for r in (ag, w, x)),
            "wrong source task, schema, or financial state")
    require(Path(x["source_report"]).name == filenames["136W"],
            "Task136X was built from a different Task136W report")
    candidates = ag["candidates"]
    require(len(candidates) == ag["coverage"]["guarded_hashes"] and
            sum(ag["coverage"]["legacy_labels"].values()) == len(candidates),
            "Task136AG candidate count differs")
    by_hash = {str(r["txhash"]).lower(): r for r in candidates}
    require(len(by_hash) == len(candidates), "duplicate Task136AG hash")
    raw = w["candidate_rows"]
    raw_by_hash = {str(r["txhash"]).lower(): r for r in raw}
    require(len(raw_by_hash) == len(raw) == w["coverage"]["candidate_hashes"] and
            set(by_hash).issubset(raw_by_hash), "Task136AG hashes not covered by Task136W")
    owned = {str(r["address"]).lower() for r in w["registered_owned_wallets"]}
    require(owned, "no registered owned wallets")
    exact_x = {str(r["txhash"]).lower(): r for r in x["pair_candidates"]}
    require(len(exact_x) == len(x["pair_candidates"]) ==
            x["coverage"]["exact_two_transfer_weth_axie_pairs"],
            "Task136X pair count or uniqueness differs")
    selected = [r for r in candidates if r["legacy_label"] in
                ("MARKETPLACE_BUY", "MARKETPLACE_SALE")]
    require(len(selected) == sum(ag["coverage"]["legacy_labels"].get(label, 0)
                                 for label in ("MARKETPLACE_BUY", "MARKETPLACE_SALE")),
            "Task136AG marketplace label counts differ")
    out = []
    for agrow in sorted(selected, key=lambda r: str(r["txhash"]).lower()):
        h = str(agrow["txhash"]).lower()
        source = raw_by_hash[h]
        transfers, transactions = source["raw_transfer_rows"], source["raw_transaction_rows"]
        require(len(transfers) == agrow["ledger_rows"],
                f"{h}: raw transfers differ from guarded ledger row count")
        require(len(transfers) == 2 and len(transactions) <= 1,
                f"{h}: marketplace-shaped group is not an exact two-transfer pair")
        weth = [t for t in transfers if t.get("token_symbol") == "WETH"]
        assets = [t for t in transfers if t.get("token_symbol") != "WETH"]
        require(len(weth) == len(assets) == 1, f"{h}: expected one WETH and one asset")
        pay, asset = weth[0], assets[0]
        require(pay.get("token_type") == "ERC-20" and pay.get("decimals") == 18 and
                str(pay.get("amount_raw") or "").isdecimal() and int(pay["amount_raw"]) > 0,
                f"{h}: invalid WETH provenance or raw quantity")
        require(str(asset.get("amount_raw") or "").isdecimal() and
                int(asset["amount_raw"]) > 0,
                f"{h}: invalid asset raw quantity")
        require(pay.get("timestamp") == asset.get("timestamp") and
                pay.get("block_number") == asset.get("block_number") and
                pay.get("log_index") != asset.get("log_index"),
                f"{h}: raw transfer block/time/log differs")
        pd, ad = direction(pay, owned), direction(asset, owned)
        expected_label = "MARKETPLACE_BUY" if pd == "OUT" and ad == "IN" else (
            "MARKETPLACE_SALE" if pd == "IN" and ad == "OUT" else None)
        require(expected_label == agrow["legacy_label"] and
                agrow["shape"] == ("BUY_CANDIDATE" if pd == "OUT" else "SALE_CANDIDATE"),
                f"{h}: raw wallet flow differs from shadow classifier")
        if transactions:
            tx = transactions[0]
            require(tx.get("block_number") == pay["block_number"] and
                    tx.get("status") == "ok" and
                    agrow["status"] == "Success" and agrow["method"] == tx["method"],
                    f"{h}: raw transaction block, method, or status differs")
        else:
            require(agrow["status"] is None and agrow["method"] is None,
                    f"{h}: transfer-only provenance differs")
        symbol = str(asset.get("token_symbol") or "UNKNOWN")
        token_type = asset.get("token_type")
        if symbol == "AXIE":
            require(token_type == "ERC-721" and asset["amount_raw"] == "1" and
                    str(asset.get("token_id") or "").isdecimal(),
                    f"{h}: AXIE type, quantity, or token ID differs")
            earlier = exact_x.get(h)
            require(earlier is not None and earlier["axie_id"] == str(asset["token_id"]) and
                    earlier["weth_transfer_raw"] == pay["amount_raw"] and
                    earlier["shape"] == ("PURCHASE_SHAPED" if pd == "OUT" else "SALE_SHAPED"),
                    f"{h}: Task136X Axie pair differs")
            lane = "AXIE_PAIR_CANDIDATE"
        elif token_type == "ERC-20":
            require(h not in exact_x, f"{h}: fungible pair is incorrectly in Axie crosswalk")
            lane = "FUNGIBLE_EXCHANGE_REVIEW"
        else:
            require(h not in exact_x, f"{h}: other asset is incorrectly in Axie crosswalk")
            lane = "OTHER_ASSET_PAIR_CANDIDATE"
        out.append({"txhash": h, "asset_symbol": symbol, "asset_token_type": token_type,
                    "asset_token_id": asset.get("token_id"),
                    "shape": "BUY_CANDIDATE" if pd == "OUT" else "SALE_CANDIDATE",
                    "review_lane": lane, "raw_transaction_present": bool(transactions),
                    "raw_transaction_method": transactions[0]["method"] if transactions else None,
                    "raw_transaction_status": transactions[0]["status"] if transactions else None,
                    "asset_transfer_key": asset["transfer_key"],
                    "weth_transfer_key": pay["transfer_key"],
                    "weth_transfer_raw": pay["amount_raw"],
                    "sale_gross_status": "UNKNOWN",
                    "financial_treatment": "UNREVIEWED_CANDIDATE"})
    axie_hashes = {r["txhash"] for r in out if r["review_lane"] == "AXIE_PAIR_CANDIDATE"}
    require(axie_hashes == set(exact_x), "Task136X Axie pair set differs from new shadow")
    require(sum(r["shape"] == "BUY_CANDIDATE" for r in out) ==
            ag["coverage"]["legacy_labels"].get("MARKETPLACE_BUY", 0) and
            sum(r["shape"] == "SALE_CANDIDATE" for r in out) ==
            ag["coverage"]["legacy_labels"].get("MARKETPLACE_SALE", 0),
            "shadow marketplace totals differ")
    return {"project": "AxieOS", "version": "0.14", "task": "136AH",
            "sources": {k: {"filename": filenames[k], "sha256": digests[k]}
                        for k in sorted(digests)},
            "coverage": {"shadow_hashes": len(by_hash), "raw_cached_hashes": len(raw),
                         "marketplace_labeled_hashes": len(out),
                         "exact_two_transfer_pairs": len(out),
                         "by_asset_and_shape": dict(sorted(Counter(
                             r["asset_symbol"] + "/" + r["shape"] for r in out).items())),
                         "by_review_lane": dict(sorted(Counter(r["review_lane"] for r in out).items())),
                         "raw_transaction_present": sum(r["raw_transaction_present"] for r in out),
                         "raw_transaction_absent": sum(not r["raw_transaction_present"] for r in out),
                         "axie_pairs_crosschecked_with_136X": len(axie_hashes)},
            "candidate_pairs": out, "accepted_financial_totals": None,
            "database_opened": False, "database_writes": 0, "network_calls": 0,
            "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136AH Marketplace candidate review", "",
             f"Shadow marketplace labels: **{c['marketplace_labeled_hashes']}**; "
             f"all **{c['exact_two_transfer_pairs']}** match one raw WETH and one raw asset transfer. "
             f"**{c['axie_pairs_crosschecked_with_136X']}** Axie pairs match Task136X exactly.", "",
             "| Raw asset and movement | Candidate hashes |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in c["by_asset_and_shape"].items()]
    lines += ["", "| Review lane | Hashes |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in c["by_review_lane"].items()]
    lines += ["", f"Raw transaction present: **{c['raw_transaction_present']}**; "
              f"transfer-only: **{c['raw_transaction_absent']}**. "
              "Fungible WETH/asset pairs require exchange review before any marketplace label. "
              "Incoming WETH is a raw transfer, not verified sale gross. "
              "Asset IDs for ACI/AM/ITEM are raw token IDs, not Axie IDs.", "",
              "Verified income, expenses, marketplace fees, cost basis, profit, "
              "and PHP recovery: **UNKNOWN**. No financial events are accepted.", "",
              "Database opened: NO | Writes: 0 | Network: 0", "",
              "VALIDATION: PASS (offline candidate crosswalk only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ag", type=Path)
    parser.add_argument("--ag-dir", type=Path, default=Path("reports/axieos_v014/task136ag"))
    parser.add_argument("--w", type=Path)
    parser.add_argument("--w-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--x", type=Path)
    parser.add_argument("--x-dir", type=Path, default=Path("reports/axieos_v014/task136x"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136ah"))
    args = parser.parse_args()
    paths = {"136AG": args.ag or find(args.ag_dir, "136AG"),
             "136W": args.w or find(args.w_dir, "136W", "1.1"),
             "136X": args.x or find(args.x_dir, "136X")}
    docs, shas = {}, {}
    for k, path in paths.items():
        docs[k], shas[k] = load(path)
    report = analyze(docs["136AG"], docs["136W"], docs["136X"], shas,
                     {k: p.name for k, p in paths.items()})
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AH_Marketplace_Candidate_Review_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136AH - MARKETPLACE CANDIDATE REVIEW")
    print(f"Marketplace-shaped: {c['marketplace_labeled_hashes']} | "
          f"Exact raw pairs: {c['exact_two_transfer_pairs']} | "
          f"Axie crosschecked: {c['axie_pairs_crosschecked_with_136X']}")
    print(f"Asset/shape: {c['by_asset_and_shape']}")
    print("Verified income, expenses, profit, and PHP recovery: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (offline candidate crosswalk only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
