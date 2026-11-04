r"""Task136AG: read-only candidate classification of the guarded ledger cohort.

Run from the AxieOS repository root:
    py -B .\scripts\v014_post_apply_accounting_shadow.py

Requires the Task136AF reconciliation, Task136AE applied, and Task136AD
guarded-plan JSON files.
Reads production SQLite with mode=ro/query_only. Calls only the legacy pure
grouped-transaction classifier, never its sync, accounting, or economic writers.
The legacy HIGH confidence label is a pattern label, not verified finance.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ronin_api_sync import classify_grouped_transaction, get_movement_direction
from v014_post_apply_reconcile import connect_ro, read, require


FIELDS = ("txhash", "blockno", "unixtimestamp", "datetime", "from_address",
          "to_address", "method", "token_collectibles", "value_in",
          "value_out", "txn_fee_ron", "status", "source_row_hash")


def select_af(explicit: Path | None, directory: Path) -> Path:
    if explicit is not None:
        return explicit
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        item, _ = read(path)
        if item.get("task") == "136AF" and item.get("checkpoint96") == "OPEN":
            matches.append((item.get("created_at_utc", ""), path))
    require(bool(matches), f"no Task136AF report in {directory}; pass --af PATH")
    return max(matches)[1]


def analyze(af: dict, ae: dict, ad: dict, af_sha: str, ae_sha: str,
            ad_sha: str, conn) -> dict:
    c = af.get("coverage", {})
    a = ad.get("coverage", {})
    require(af.get("task") == "136AF" and ae.get("task") == "136AE" and
            ae.get("mode") == "APPLIED" and ad.get("task") == "136AD" and
            af.get("checkpoint96") == ae.get("checkpoint96") == ad.get("checkpoint96") == "OPEN" and
            af.get("accepted_financial_totals") is None and
            ae.get("accepted_financial_totals") is None and
            ad.get("accepted_financial_totals") is None and
            c.get("source_applied_sha256") == ae_sha and
            ae.get("source_files", {}).get("136AD", {}).get("sha256") == ad_sha and
            c.get("inserted_rows_exact") == a.get("guarded_rows") and
            c.get("inserted_hashes_exact") == a.get("guarded_hashes"),
            "Task136AF/AD scope or finance status differs")
    proposed = ad["guarded_ledger_rows"]
    require(len(proposed) == c["inserted_rows_exact"] and
            all(set(row) == set(FIELDS) for row in proposed),
            "guarded row plan is missing or changed")
    by_source = {row["source_row_hash"]: row for row in proposed}
    require(len(by_source) == len(proposed), "duplicate guarded source hash")
    hashes = {str(row["txhash"]).lower() for row in proposed}
    require(len(hashes) == c["inserted_hashes_exact"], "guarded hash count differs")
    require(conn.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0] ==
            c["ledger_after"], "production ledger changed since Task136AF; reconcile again")
    require(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity check failed")
    cursor = conn.execute(
        "SELECT " + ",".join(FIELDS) +
        " FROM blockchain_transactions ORDER BY blockno,id")
    rows = [dict(zip(FIELDS, row)) for row in cursor
            if row[-1] in by_source]
    require(len(rows) == len(proposed) and
            {r["source_row_hash"] for r in rows} == set(by_source),
            "guarded ledger source rows missing or duplicated")
    for row in rows:
        expected = by_source[row["source_row_hash"]]
        require(row == expected, f"guarded ledger row changed: {row['source_row_hash']}")
    account_hashes = {str(h).lower() for (h,) in conn.execute(
        "SELECT txhash FROM blockchain_accounting_records WHERE txhash IS NOT NULL")}
    require(not hashes & account_hashes, "cohort accounting changed; reconcile before shadow")
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row["txhash"]).lower()].append(row)
    require(set(grouped) == hashes, "grouped ledger coverage differs")
    details = []
    labels = Counter()
    flags = Counter()
    for h, members in sorted(grouped.items()):
        methods = {r["method"] for r in members}
        statuses = {r["status"] for r in members}
        movements = [{"from_address": r["from_address"], "to_address": r["to_address"],
                      "asset": r["token_collectibles"], "value_in": r["value_in"],
                      "value_out": r["value_out"]} for r in members]
        directions = [(m["asset"], get_movement_direction(m)) for m in movements]
        weth = "Ronin Wrapped Ether"
        wi = sum(asset == weth and d == "IN" for asset, d in directions)
        wo = sum(asset == weth and d == "OUT" for asset, d in directions)
        ai = sum(asset != weth and d == "IN" for asset, d in directions)
        ao = sum(asset != weth and d == "OUT" for asset, d in directions)
        local_flags = []
        if len(methods) != 1 or len(statuses) != 1:
            local_flags.append("MIXED_METHOD_OR_STATUS")
        if None in methods:
            local_flags.append("METHOD_MISSING")
        if None in statuses:
            local_flags.append("STATUS_MISSING")
        if any(r["txn_fee_ron"] is not None for r in members):
            local_flags.append("UNEXPECTED_FEE_VALUE")
        if any(d == "NONE" for _, d in directions):
            local_flags.append("NO_DIRECTION")
        if wi and wo or ai and ao:
            local_flags.append("BIDIRECTIONAL_ASSET_FLOW")
        if (wo and ai) and (wi and ao):
            local_flags.append("BUY_AND_SALE_SHAPE")
        tx = {"txhash": h, "method": next(iter(methods)) if len(methods) == 1 else None,
              "movements": movements}
        result = (classify_grouped_transaction(tx) if len(methods) == 1 and
                  len(statuses) == 1 else {"classification": "REVIEW_MIXED_GROUP",
                                           "confidence": "LOW", "reason": "mixed method/status"})
        label = result["classification"]
        labels[label] += 1
        flags.update(local_flags)
        paired = ("BUY_CANDIDATE" if wo and ai and not wi and not ao else
                  "SALE_CANDIDATE" if wi and ao and not wo and not ai else
                  "OTHER_OR_AMBIGUOUS")
        details.append({"txhash": h, "ledger_rows": len(members),
                        "legacy_label": label, "legacy_confidence": result["confidence"],
                        "legacy_reason": result["reason"], "shape": paired,
                        "method": tx["method"], "status": next(iter(statuses)) if len(statuses) == 1 else None,
                        "assets": sorted({str(x) for x, _ in directions}),
                        "flags": sorted(local_flags),
                        "accounting_treatment": "UNREVIEWED_CANDIDATE"})
    return {"project": "AxieOS", "version": "0.14", "task": "136AG",
            "source_task136af_sha256": af_sha, "source_task136ae_sha256": ae_sha,
            "source_task136ad_sha256": ad_sha,
            "coverage": {"guarded_hashes": len(hashes), "guarded_rows": len(rows),
                         "stored_accounting_for_cohort": 0,
                         "legacy_labels": dict(sorted(labels.items())),
                         "movement_shapes": dict(sorted(Counter(d["shape"] for d in details).items())),
                         "review_flags": dict(sorted(flags.items())),
                         "fee_unverified_rows": len(rows)},
            "candidates": details, "accepted_financial_totals": None,
            "database_writes": 0, "network_calls": 0, "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136AG Accounting shadow", "",
             f"Guarded cohort: **{c['guarded_rows']}** exact ledger rows, "
             f"**{c['guarded_hashes']}** transaction hashes; stored accounting: **0**.", "",
             "| Legacy classifier candidate | Hashes |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in c["legacy_labels"].items()]
    lines += ["", "| Movement shape | Hashes |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in c["movement_shapes"].items()]
    lines += ["", "| Review flag | Hashes |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in c["review_flags"].items()]
    lines += ["", "The legacy classifier's HIGH confidence is structural only. "
             "A paired WETH and asset movement is a candidate; marketplace attribution, "
             "cost basis, gas payer, and accounting treatment remain unverified. "
             "All ledger fee fields in this cohort are NULL.", "",
             "Verified income, expenses, profit, and PHP recovery: **UNKNOWN**.", "",
             "Production database opened read only | Database writes: 0 | Network: 0", "",
             "VALIDATION: PASS (candidate classification only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--af", type=Path)
    parser.add_argument("--af-dir", type=Path, default=Path("reports/axieos_v014/task136af"))
    parser.add_argument("--ae", type=Path)
    parser.add_argument("--ae-dir", type=Path, default=Path("reports/axieos_v014/task136ae"))
    parser.add_argument("--ad", type=Path)
    parser.add_argument("--ad-dir", type=Path, default=Path("reports/axieos_v014/task136ad"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136ag"))
    args = parser.parse_args()
    af_path = select_af(args.af, args.af_dir)
    af, af_sha = read(af_path)
    ae_path = args.ae or args.ae_dir / af["source_applied"]
    ae, ae_sha = read(ae_path)
    require(ae_path.name == af["source_applied"], "Task136AE filename differs from reconciliation")
    ad_path = args.ad or args.ad_dir / af["source_ad"]
    ad, ad_sha = read(ad_path)
    require(ad_path.name == af["source_ad"], "Task136AD filename differs from reconciliation")
    with closing(connect_ro(args.db)) as conn:
        report = analyze(af, ae, ad, af_sha, ae_sha, ad_sha, conn)
    report["source_task136af_filename"] = af_path.name
    report["source_task136ae_filename"] = ae_path.name
    report["source_task136ad_filename"] = ad_path.name
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AG_Accounting_Shadow_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136AG - ACCOUNTING SHADOW")
    print(f"Guarded rows/hashes: {c['guarded_rows']}/{c['guarded_hashes']} | Stored accounting: 0")
    print(f"Legacy labels: {c['legacy_labels']} | Movement shapes: {c['movement_shapes']}")
    print("Verified income, expenses, profit, and PHP recovery: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: production read only | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (candidate classification only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
