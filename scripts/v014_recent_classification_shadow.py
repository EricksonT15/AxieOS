r"""Task136BC: read-only candidate classification for Task136BB recent rows.

Run from the AxieOS repository root:
    py -B .\scripts\v014_recent_classification_shadow.py

Reads production in SQLite mode=ro/query_only. Calls only the existing pure
legacy classifier on the 92 newly materialized hashes. Does not run sync,
accounting, economic writers, or any network request. Labels are candidates.
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
from v014_cache_cohort_materialization_sandbox import LEDGER_FIELDS
from v014_post_apply_reconcile import connect_ro, require
from v014_raw_import_clone import by_sha, latest, load


def analyze(conn, bb: dict, ba: dict, ay: dict,
            bb_sha: str, ba_sha: str, ay_sha: str) -> dict:
    require(bb.get("task") == "136BB" and ba.get("task") == "136BA" and
            ba.get("mode") == "APPLIED" and ay.get("task") == "136AY" and
            all(doc.get("checkpoint96") == "OPEN" and
                doc.get("accepted_financial_totals") is None
                for doc in (bb, ba, ay)) and
            bb.get("sources", {}).get("136BA", {}).get("sha256") == ba_sha and
            bb.get("sources", {}).get("136AY", {}).get("sha256") == ay_sha and
            ba.get("sources", {}).get("136AY", {}).get("sha256") == ay_sha,
            "Task136BB/BA/AY source chain or financial boundary differs")
    cov, applied, proposed = (bb.get("coverage") or {},
                              ba.get("result") or {},
                              ay.get("guarded_ledger_rows"))
    require(isinstance(proposed, list) and len(proposed) ==
            cov.get("inserted_rows_exact") == applied.get("inserted_rows") and
            cov.get("inserted_hashes_exact") == applied.get("inserted_hashes") and
            cov.get("ledger_after") == applied.get("ledger_after") and
            cov.get("prior_ledger_rows_preserved") == applied.get("ledger_before"),
            "reconciled recent ledger cohort differs")
    by_source = {row["source_row_hash"]: row for row in proposed}
    hashes = {str(row["txhash"]).lower() for row in proposed}
    require(len(by_source) == len(proposed) and
            len(hashes) == cov["inserted_hashes_exact"] and
            all(set(row) == set(LEDGER_FIELDS) for row in proposed),
            "duplicate or malformed proposed ledger rows")
    require(conn.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0] ==
            cov["ledger_after"] and
            conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
            "production ledger changed or SQLite integrity failed")
    cursor = conn.execute("SELECT " + ",".join(LEDGER_FIELDS) +
                          " FROM blockchain_transactions ORDER BY blockno,id")
    rows = [dict(zip(LEDGER_FIELDS, row)) for row in cursor
            if row[-1] in by_source]
    require(len(rows) == len(proposed) and
            {row["source_row_hash"] for row in rows} == set(by_source),
            "guarded source rows missing or duplicated")
    for row in rows:
        require(row == by_source[row["source_row_hash"]],
                f"ledger row differs since Task136BB: {row['source_row_hash']}")
    accounting = {str(h).lower() for (h,) in conn.execute(
        "SELECT txhash FROM blockchain_accounting_records WHERE txhash IS NOT NULL")}
    classified = {str(h).lower() for (h,) in conn.execute(
        "SELECT txhash FROM blockchain_transaction_classifications WHERE txhash IS NOT NULL")}
    require(not hashes & accounting and not hashes & classified,
            "recent cohort already has accounting/classification; reconcile before shadow")
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row["txhash"]).lower()].append(row)
    require(set(grouped) == hashes, "grouped source hash coverage differs")
    details, labels, flags = [], Counter(), Counter()
    weth = "Ronin Wrapped Ether"
    for h, members in sorted(grouped.items()):
        methods = {r["method"] for r in members}
        statuses = {r["status"] for r in members}
        movements = [{"from_address": r["from_address"],
                      "to_address": r["to_address"],
                      "asset": r["token_collectibles"],
                      "value_in": r["value_in"],
                      "value_out": r["value_out"]} for r in members]
        directions = [(m["asset"], get_movement_direction(m)) for m in movements]
        wi = sum(asset == weth and d == "IN" for asset, d in directions)
        wo = sum(asset == weth and d == "OUT" for asset, d in directions)
        ai = sum(asset != weth and d == "IN" for asset, d in directions)
        ao = sum(asset != weth and d == "OUT" for asset, d in directions)
        review = []
        if len(methods) != 1 or len(statuses) != 1:
            review.append("MIXED_METHOD_OR_STATUS")
        if None in methods:
            review.append("METHOD_MISSING")
        if None in statuses:
            review.append("STATUS_MISSING")
        if any(r["txn_fee_ron"] is not None for r in members):
            review.append("UNEXPECTED_FEE_VALUE")
        if any(direction == "NONE" for _, direction in directions):
            review.append("NO_DIRECTION")
        if (wi and wo) or (ai and ao):
            review.append("BIDIRECTIONAL_ASSET_FLOW")
        if (wo and ai) and (wi and ao):
            review.append("BUY_AND_SALE_SHAPE")
        tx = {"txhash": h, "method": next(iter(methods)) if len(methods) == 1 else None,
              "movements": movements}
        result = (classify_grouped_transaction(tx)
                  if len(methods) == 1 and len(statuses) == 1 else
                  {"classification": "REVIEW_MIXED_GROUP", "confidence": "LOW",
                   "reason": "mixed method/status"})
        label = result["classification"]
        shape = ("BUY_CANDIDATE" if wo and ai and not wi and not ao else
                 "SALE_CANDIDATE" if wi and ao and not wo and not ai else
                 "OTHER_OR_AMBIGUOUS")
        labels[label] += 1
        flags.update(review)
        details.append({"txhash": h, "ledger_rows": len(members),
                        "legacy_label": label,
                        "legacy_confidence": result["confidence"],
                        "legacy_reason": result["reason"],
                        "shape": shape, "method": tx["method"],
                        "status": next(iter(statuses)) if len(statuses) == 1 else None,
                        "assets": sorted({str(asset) for asset, _ in directions}),
                        "flags": sorted(review),
                        "accounting_treatment": "UNREVIEWED_CANDIDATE"})
    return {"project": "AxieOS", "version": "0.14", "task": "136BC",
            "sources": {"136BB": {"sha256": bb_sha},
                        "136BA": {"sha256": ba_sha},
                        "136AY": {"sha256": ay_sha}},
            "coverage": {"recent_hashes": len(hashes),
                         "recent_ledger_rows": len(rows),
                         "stored_accounting_for_cohort": 0,
                         "stored_classification_for_cohort": 0,
                         "legacy_labels": dict(sorted(labels.items())),
                         "movement_shapes": dict(sorted(Counter(
                             row["shape"] for row in details).items())),
                         "review_flags": dict(sorted(flags.items())),
                         "fee_unverified_rows": len(rows)},
            "candidates": details,
            "accepted_financial_totals": None,
            "production_database_opened_read_only": True,
            "database_writes": 0, "network_calls": 0, "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136BC Recent classification shadow", "",
             f"Exact recent ledger rows/hashes: **{c['recent_ledger_rows']}/"
             f"{c['recent_hashes']}**. Stored accounting/classification: **0/0**.", "",
             "| Legacy candidate label | Hashes |", "|---|---:|"]
    lines.extend(f"| {label} | {count} |" for label, count in c["legacy_labels"].items())
    lines += ["", "| Movement shape | Hashes |", "|---|---:|"]
    lines.extend(f"| {label} | {count} |" for label, count in c["movement_shapes"].items())
    lines += ["", "| Review flag | Hashes |", "|---|---:|"]
    lines.extend(f"| {label} | {count} |" for label, count in c["review_flags"].items())
    lines += ["", "Legacy confidence describes pattern matching only. Route, "
              "counterparty, basis, payer, and financial treatment require separate "
              "review. Fee fields in all recent ledger rows remain NULL.", "",
              "Verified income, expenses, profit, and PHP recovery: **UNKNOWN**.", "",
              "Production opened read only | Writes: 0 | Network: 0", "",
              "VALIDATION: PASS (candidate classification only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path,
                        default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--bb", type=Path)
    parser.add_argument("--bb-dir", type=Path,
                        default=Path("reports/axieos_v014/task136bb"))
    parser.add_argument("--ba-dir", type=Path,
                        default=Path("reports/axieos_v014/task136ba"))
    parser.add_argument("--ay-dir", type=Path,
                        default=Path("reports/axieos_v014/task136ay"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("reports/axieos_v014/task136bc"))
    args = parser.parse_args()
    bb_path = args.bb or latest(args.bb_dir, "136BB")
    bb, bb_sha = load(bb_path)
    ba_path = by_sha(args.ba_dir, bb["sources"]["136BA"]["sha256"], "136BA")
    ay_path = by_sha(args.ay_dir, bb["sources"]["136AY"]["sha256"], "136AY")
    ba, ba_sha = load(ba_path)
    ay, ay_sha = load(ay_path)
    with closing(connect_ro(args.db)) as conn:
        conn.execute("BEGIN")
        report = analyze(conn, bb, ba, ay, bb_sha, ba_sha, ay_sha)
    for task, path in (("136BB", bb_path), ("136BA", ba_path), ("136AY", ay_path)):
        report["sources"][task]["filename"] = path.name
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136BC_Recent_Classification_Shadow_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
            "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136BC - RECENT CLASSIFICATION SHADOW")
    print(f"Recent ledger rows/hashes: {c['recent_ledger_rows']}/"
          f"{c['recent_hashes']} | Stored accounting/classification: 0/0")
    print(f"Legacy labels: {c['legacy_labels']} | Movement shapes: {c['movement_shapes']}")
    print(f"Review flags: {c['review_flags']}")
    print("Verified income, expenses, profit, and PHP recovery: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Production read only | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (recent candidate classification only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
