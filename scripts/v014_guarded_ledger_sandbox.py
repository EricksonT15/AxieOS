r"""Task136AD: rehearse provenance-corrected cached ledger rows in a clone.

Run from the AxieOS repository root:
    py -B .\scripts\v014_guarded_ledger_sandbox.py

Requires Task136AC and Task136W JSON, plus the previously saved Task136AC
and V0.13 full-row sandbox helpers. Production SQLite is read-only. Writes
only to a disposable copy; does not classify, import into production, or
access the network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

from v014_cache_cohort_materialization_sandbox import (
    LEDGER_FIELDS, plan, readonly_connect, rehearse, require,
)


def find_report(directory: Path, task: str) -> Path:
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
        if data.get("task") == task and (task != "136W" or
                                        data.get("report_schema_version") == "1.1"):
            matches.append((data.get("created_at_utc", ""), path))
    require(bool(matches), f"no Task{task} JSON in {directory}; pass --ac/--cache PATH")
    return max(matches)[1]


def read(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing report: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def assess_group(rows: list[dict], raw: dict) -> list[str]:
    reasons = []
    if any(not row["token_collectibles"] for row in rows):
        reasons.append("MISSING_ASSET_NAME")
    for row in rows:
        try:
            inbound, outbound = Decimal(str(row["value_in"])), Decimal(str(row["value_out"]))
        except InvalidOperation:
            reasons.append("INVALID_LEDGER_VALUE")
            continue
        if not inbound.is_finite() or not outbound.is_finite() or inbound < 0 or outbound < 0:
            reasons.append("INVALID_LEDGER_VALUE")
        elif inbound == 0 and outbound == 0:
            reasons.append("ZERO_VALUE_TRANSFER")
        elif inbound > 0 and outbound > 0:
            reasons.append("BOTH_DIRECTIONS_ON_ONE_ROW")
    txrows = raw["raw_transaction_rows"]
    if len(txrows) > 1:
        reasons.append("MULTIPLE_RAW_TRANSACTIONS")
    elif txrows and str(txrows[0]["status"]).lower() != "ok":
        reasons.append("RAW_TRANSACTION_NOT_OK")
    return sorted(set(reasons))


def build(ac: dict, cache: dict, ac_sha: str, cache_sha: str,
          conn) -> tuple[dict, list[tuple]]:
    require(ac.get("task") == "136AC" and ac.get("checkpoint96") == "OPEN" and
            ac.get("production_database_writes") == 0 and
            ac.get("temporary_clone_deleted") is True and
            ac.get("accepted_financial_totals") is None,
            "Task136AC result changed")
    require(ac.get("source_task136w", {}).get("sha256") == cache_sha,
            "Task136AC was built from a different Task136W snapshot")
    s, p = ac["sandbox"], ac["plan"]
    require(s["clone_rows_first_pass"] == p["selected_full_ledger_rows"] and
            s["clone_rows_second_pass"] == 0 and
            s["clone_integrity"] == "ok" and s["clone_foreign_key_errors"] == 0 and
            s["production_ledger_before_after"][0] == s["production_ledger_before_after"][1],
            "Task136AC sandbox validation differs")
    previous = ac["proposed_ledger_rows"]
    require(len(previous) == p["selected_full_ledger_rows"] and
            all(set(r) == set(LEDGER_FIELDS) for r in previous),
            "Task136AC proposed rows changed")
    current, current_counts = plan(conn, cache)
    require(current_counts == p, "live source scope changed since Task136AC")
    previous_by_source = {r["source_row_hash"]: tuple(r[f] for f in LEDGER_FIELDS)
                          for r in previous}
    current_by_source = {r[-1]: r for r in current}
    require(len(previous_by_source) == len(previous) and
            previous_by_source == current_by_source,
            "live proposed rows differ from Task136AC; rerun 136AC")
    raw_by_hash = {str(r["txhash"]).lower(): r for r in cache["candidate_rows"]}
    by_hash = defaultdict(list)
    for row in previous:
        by_hash[str(row["txhash"]).lower()].append(row)
    quarantine = []
    safe = []
    status_counts = Counter()
    for h, rows in by_hash.items():
        raw = raw_by_hash[h]
        reasons = assess_group(rows, raw)
        if reasons:
            quarantine.append({"txhash": h, "row_count": len(rows),
                               "reasons": reasons})
            continue
        txrows = raw["raw_transaction_rows"]
        observed_status = "Success" if txrows and str(txrows[0]["status"]).lower() == "ok" else None
        for row in rows:
            modified = dict(row)
            # The old adapter's 0.0 is a placeholder, not verified user-paid gas.
            modified["txn_fee_ron"] = None
            # Transfer-only hashes have no matching raw transaction status.
            modified["status"] = observed_status
            safe.append(tuple(modified[f] for f in LEDGER_FIELDS))
            status_counts["RAW_OK" if observed_status == "Success" else "NO_RAW_TRANSACTION"] += 1
    require(len(safe) + sum(x["row_count"] for x in quarantine) == len(previous),
            "guarded and quarantined rows do not partition Task136AC")
    require(len({r[-1] for r in safe}) == len(safe), "guarded source hashes not unique")
    require(all(r[10] is None for r in safe), "unverified gas placeholder remains")
    return {"project": "AxieOS", "version": "0.14", "task": "136AD",
            "source_task136ac_sha256": ac_sha, "source_task136w_sha256": cache_sha,
            "coverage": {"original_proposed_rows": len(previous),
                         "original_transfer_hashes": len(by_hash),
                         "guarded_rows": len(safe),
                         "guarded_hashes": len({r[0] for r in safe}),
                         "quarantined_hashes": len(quarantine),
                         "quarantined_rows": sum(x["row_count"] for x in quarantine),
                         "status_provenance_rows": dict(sorted(status_counts.items())),
                         "ledger_fee_unknown_rows": len(safe),
                         "transaction_only_hashes_still_omitted": p["transaction_only_hashes"]},
            "quarantined": quarantine,
            "guarded_ledger_rows": [dict(zip(LEDGER_FIELDS, row)) for row in safe],
            "accepted_financial_totals": None, "production_database_writes": 0,
            "network_calls": 0, "checkpoint96": "OPEN"}, safe


def markdown(report: dict) -> str:
    c, sandbox = report["coverage"], report["sandbox"]
    lines = ["# AxieOS V0.14 — Task136AD Guarded ledger sandbox", "",
             f"Original proposed transfer rows: **{c['original_proposed_rows']}**. "
             f"Guarded rows: **{c['guarded_rows']}** across **{c['guarded_hashes']}** hashes. "
             f"Quarantined: **{c['quarantined_rows']}** rows across "
             f"**{c['quarantined_hashes']}** whole hashes.", "",
             "| Status provenance in guarded rows | Rows |", "|---|---:|"]
    for label, count in c["status_provenance_rows"].items():
        lines.append(f"| {label} | {count} |")
    lines += ["", f"All **{c['ledger_fee_unknown_rows']}** guarded rows keep ledger fee NULL "
              "because user-paid gas is not verified. Rows without raw transaction evidence "
              "keep status NULL rather than synthetic Success.", "",
              "| Quarantined transaction hash | Rows | Reasons |", "|---|---:|---|"]
    for item in report["quarantined"]:
        lines.append(f"| `{item['txhash']}` | {item['row_count']} | {', '.join(item['reasons'])} |")
    lines += ["", f"Temporary clone first/second inserts: "
              f"**{sandbox['clone_rows_first_pass']}/{sandbox['clone_rows_second_pass']}**. "
              f"Integrity: **{sandbox['clone_integrity']}**; foreign key errors: "
              f"**{sandbox['clone_foreign_key_errors']}**.", "",
              f"The **{c['transaction_only_hashes_still_omitted']}** transaction-only hashes "
              "and activity after the cache cutoff remain out of scope. No accounting or "
              "economics has been run.", "",
              "Production DB opened: read only | Production writes: 0 | Temporary clone: deleted | Network: 0", "",
              "VALIDATION: PASS (guarded sandbox only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--ac", type=Path)
    parser.add_argument("--ac-dir", type=Path, default=Path("reports/axieos_v014/task136ac"))
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136ad"))
    args = parser.parse_args()
    ac_path = args.ac or find_report(args.ac_dir, "136AC")
    cache_path = args.cache or find_report(args.cache_dir, "136W")
    ac, ac_sha = read(ac_path)
    cache, cache_sha = read(cache_path)
    db = args.db.resolve()
    require(db.is_file(), f"database missing: {db}")
    with closing(readonly_connect(db)) as prod:
        prod.execute("PRAGMA query_only=ON")
        report, safe = build(ac, cache, ac_sha, cache_sha, prod)
        cols = {r[1]: r for r in prod.execute('PRAGMA table_info("blockchain_transactions")')}
        require(cols["txn_fee_ron"][3] == 0 and cols["status"][3] == 0,
                "ledger schema forbids NULL fee/status; requires schema review")
        report["sandbox"] = rehearse(prod, safe)
    report["source_task136ac_filename"] = ac_path.name
    report["source_task136w_filename"] = cache_path.name
    report["source_database"] = str(args.db)
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AD_Guarded_Ledger_Sandbox_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
            + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with mp.open("x", encoding="utf-8") as stream:
        stream.write(markdown(report))
    c, s = report["coverage"], report["sandbox"]
    print("AXIEOS V0.14 - TASK136AD - GUARDED LEDGER SANDBOX")
    print(f"Guarded rows: {c['guarded_rows']} | Hashes: {c['guarded_hashes']} | "
          f"Quarantined rows/hashes: {c['quarantined_rows']}/{c['quarantined_hashes']}")
    print(f"NULL fee rows: {c['ledger_fee_unknown_rows']} | "
          f"Clone first/second: {s['clone_rows_first_pass']}/{s['clone_rows_second_pass']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Production DB opened: read only | Production writes: 0 | Temporary clone: deleted | Network: 0")
    print("VALIDATION: PASS (guarded sandbox only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
