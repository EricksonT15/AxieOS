r"""Task136BB: independently reconcile the Task136BA ledger insert with backup.

Run from the AxieOS repository root:
    py -B .\scripts\v014_recent_ledger_reconcile.py

Reads the production database and the persistent pre-apply backup in mode=ro.
Checks the exact 139 inserted ledger rows, all prior ledger rows, raw tables,
and protected accounting/gameplay tables. No writes or network calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from v013_fullrow_materialization_sandbox import PROTECTED_TABLES, table_fingerprint
from v014_cache_cohort_materialization_sandbox import LEDGER_FIELDS
from v014_post_apply_reconcile import connect_ro, require
from v014_raw_import_clone import by_sha, load


UNCHANGED = ("ronin_api_transactions_raw", "ronin_token_transfers_raw",
             *PROTECTED_TABLES)


def select_applied(path: Path | None, directory: Path) -> Path:
    if path is not None:
        return path
    candidates = []
    for candidate in directory.glob("*.json") if directory.is_dir() else []:
        document, _ = load(candidate)
        if document.get("task") == "136BA" and document.get("mode") == "APPLIED":
            candidates.append((document.get("created_at_utc", ""), candidate))
    require(bool(candidates),
            f"no applied Task136BA report found in {directory}; pass --applied PATH")
    return max(candidates)[1]


def unchanged_ledger_digest(conn, inserted: set[str]) -> tuple[str, int]:
    digest = hashlib.sha256()
    kept = 0
    cursor = conn.execute("SELECT * FROM blockchain_transactions ORDER BY rowid")
    fields = [item[0] for item in cursor.description]
    require("source_row_hash" in fields, "ledger source identity column missing")
    index = fields.index("source_row_hash")
    for row in cursor:
        if row[index] in inserted:
            continue
        digest.update(repr(row).encode("utf-8"))
        digest.update(b"\n")
        kept += 1
    return digest.hexdigest(), kept


def reconcile(current, backup, ba: dict, ba_sha: str,
              ay: dict, ay_sha: str, az: dict, az_sha: str,
              au: dict, au_sha: str) -> dict:
    require(ba.get("task") == "136BA" and ba.get("mode") == "APPLIED" and
            ba.get("checkpoint96") == "OPEN" and
            ba.get("accepted_financial_totals") is None and
            ba.get("network_calls") == 0 and
            ba.get("sources", {}).get("136AY", {}).get("sha256") == ay_sha and
            ba.get("sources", {}).get("136AZ", {}).get("sha256") == az_sha and
            ay.get("task") == "136AY" and ay.get("checkpoint96") == "OPEN" and
            ay.get("accepted_financial_totals") is None and
            az.get("task") == "136AZ" and
            az.get("mode") == "READ_ONLY_PREFLIGHT" and
            az.get("sources", {}).get("136AY", {}).get("sha256") == ay_sha and
            az.get("accepted_financial_totals") is None and
            ay.get("sources", {}).get("136AU", {}).get("sha256") == au_sha and
            au.get("task") == "136AU" and au.get("checkpoint96") == "OPEN" and
            au.get("accepted_financial_totals") is None,
            "applied report, source chain, or finance boundary differs")
    result, plan, pre = ba.get("result") or {}, ba.get("plan") or {}, az.get("plan") or {}
    rows = ay.get("guarded_ledger_rows")
    require(isinstance(rows, list) and bool(rows) and
            len(rows) == result.get("inserted_rows") == plan.get("guarded_rows") ==
                pre.get("guarded_rows") == ay.get("coverage", {}).get("guarded_rows") and
            result.get("inserted_hashes") == plan.get("guarded_hashes") ==
                pre.get("guarded_hashes") and
            plan.get("task136ay_sha256") == ay_sha and
            plan.get("task136az_sha256") == az_sha and
            pre.get("task136ay_sha256") == ay_sha,
            "saved plan, row counts, or source digests differ")
    require(all(isinstance(row, dict) and set(row) == set(LEDGER_FIELDS) and
                row["txn_fee_ron"] is None and row["status"] in (None, "Success")
                for row in rows), "guarded row schema, gas or status differs")
    identity = {row["source_row_hash"] for row in rows}
    hashes = {str(row["txhash"]).lower() for row in rows}
    require(len(identity) == len(rows) and len(hashes) == result["inserted_hashes"],
            "duplicate source-row identities or hash count differs")
    before, after = result.get("ledger_before"), result.get("ledger_after")
    require(isinstance(before, int) and after == before + len(rows) and
            before == plan.get("ledger_before") == pre.get("ledger_before") and
            after == plan.get("ledger_after_if_applied") ==
                pre.get("ledger_if_applied") and
            ba.get("production_database_writes") == len(rows),
            "production row arithmetic or write scope differs")
    require(backup.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
                == before and
            current.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
                == after,
            "backup/current ledger counts differ from applied report")
    require(backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
            current.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
            not backup.execute("PRAGMA foreign_key_check").fetchall() and
            not current.execute("PRAGMA foreign_key_check").fetchall(),
            "backup/current SQLite integrity or foreign key check failed")
    require(table_fingerprint(backup, "blockchain_transactions") ==
                pre["watched_table_fingerprints"]["blockchain_transactions"],
            "backup ledger differs from Task136AZ preflight")
    for row in rows:
        key = row["source_row_hash"]
        expected = tuple(row[field] for field in LEDGER_FIELDS)
        stored = current.execute(
            "SELECT " + ",".join(LEDGER_FIELDS) +
            " FROM blockchain_transactions WHERE source_row_hash=?", (key,)).fetchall()
        require(stored == [expected], f"inserted ledger row differs: {key}")
        require(backup.execute(
            "SELECT COUNT(*) FROM blockchain_transactions WHERE source_row_hash=?",
            (key,)).fetchone()[0] == 0,
            f"planned source row already existed in backup: {key}")
    preserved_digest, preserved = unchanged_ledger_digest(current, identity)
    require(preserved == before and preserved_digest ==
                table_fingerprint(backup, "blockchain_transactions"),
            "prior ledger rows changed after Task136BA")
    for table in UNCHANGED:
        saved = pre["watched_table_fingerprints"][table]
        require(table_fingerprint(backup, table) == saved and
                table_fingerprint(current, table) == saved,
                f"raw or protected table changed since preflight: {table}")
    tx_only = ({str(row["tx_hash"]).lower()
                for row in au["normalized_new_transactions"]} -
               {str(row["tx_hash"]).lower()
                for row in au["normalized_new_transfers"]})
    require(plan.get("transaction_only_hashes_omitted") ==
                pre.get("transaction_only_hashes_omitted") ==
                ay["coverage"]["new_transaction_only_hashes"] == len(tx_only) and
            len(hashes | tx_only) == ay["coverage"]["new_unique_raw_hashes"] and
            all(current.execute(
                "SELECT COUNT(*) FROM blockchain_transactions WHERE lower(txhash)=?",
                (h,)).fetchone()[0] == 0 for h in tx_only),
            "new transaction-only hash coverage or omission differs")
    return {"task136ba_applied_sha256": ba_sha,
            "ledger_before": before, "ledger_after": after,
            "inserted_rows_exact": len(rows), "inserted_hashes_exact": len(hashes),
            "prior_ledger_rows_preserved": preserved,
            "raw_tables_unchanged": 2,
            "protected_tables_unchanged": len(PROTECTED_TABLES),
            "transaction_only_hashes_still_omitted":
                plan["transaction_only_hashes_omitted"],
            "new_raw_hashes_without_new_ledger":
                ay["coverage"]["new_unique_raw_hashes"] - len(hashes),
            "integrity_check": "ok", "foreign_key_violations": 0,
            "verified_financial_totals": None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path,
                        default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--applied", type=Path)
    parser.add_argument("--applied-dir", type=Path,
                        default=Path("reports/axieos_v014/task136ba"))
    parser.add_argument("--ay-dir", type=Path,
                        default=Path("reports/axieos_v014/task136ay"))
    parser.add_argument("--az-dir", type=Path,
                        default=Path("reports/axieos_v014/task136az"))
    parser.add_argument("--au-dir", type=Path,
                        default=Path("reports/axieos_v014/task136au"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("reports/axieos_v014/task136bb"))
    args = parser.parse_args()
    ba_path = select_applied(args.applied, args.applied_dir)
    ba, ba_sha = load(ba_path)
    ay_path = by_sha(args.ay_dir, ba["sources"]["136AY"]["sha256"], "136AY")
    az_path = by_sha(args.az_dir, ba["sources"]["136AZ"]["sha256"], "136AZ")
    ay, ay_sha = load(ay_path)
    az, az_sha = load(az_path)
    au_path = by_sha(args.au_dir, ay["sources"]["136AU"]["sha256"], "136AU")
    au, au_sha = load(au_path)
    backup_path = Path(ba["result"]["backup_path"])
    require(backup_path.expanduser().resolve() != args.db.expanduser().resolve(),
            "backup path equals production database")
    with closing(connect_ro(args.db)) as current, closing(connect_ro(backup_path)) as backup:
        current.execute("BEGIN")
        backup.execute("BEGIN")
        coverage = reconcile(current, backup, ba, ba_sha, ay, ay_sha,
                             az, az_sha, au, au_sha)
    report = {"project": "AxieOS", "version": "0.14", "task": "136BB",
              "sources": {"136BA": {"filename": ba_path.name, "sha256": ba_sha},
                          "136AY": {"filename": ay_path.name, "sha256": ay_sha},
                          "136AZ": {"filename": az_path.name, "sha256": az_sha},
                          "136AU": {"filename": au_path.name, "sha256": au_sha}},
              "backup_path": str(backup_path), "coverage": coverage,
              "accepted_financial_totals": None,
              "production_database_opened_read_only": True,
              "backup_database_opened_read_only": True,
              "database_writes": 0, "network_calls": 0,
              "checkpoint96": "OPEN",
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136BB_Recent_Ledger_Reconciliation_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
            "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text("\n".join([
        "# AxieOS V0.14 — Task136BB Recent ledger reconciliation", "",
        f"Production ledger before/after: **{coverage['ledger_before']}/"
        f"{coverage['ledger_after']}**. Exact inserted rows/hashes: "
        f"**{coverage['inserted_rows_exact']}/{coverage['inserted_hashes_exact']}**.", "",
        f"Preserved prior ledger rows: **{coverage['prior_ledger_rows_preserved']}**. "
        f"Unchanged raw/protected tables: **{coverage['raw_tables_unchanged']}/"
        f"{coverage['protected_tables_unchanged']}**.", "",
        f"New raw hashes without a new ledger row: "
        f"**{coverage['new_raw_hashes_without_new_ledger']}** "
        "(transaction-only).", "",
        "Gas, classification and financial totals remain unaccepted. "
        "Verified financial totals: **UNKNOWN**. Checkpoint 96: **OPEN**.", "",
        "Production and backup opened read only | Writes: 0 | Network: 0", ""]),
        encoding="utf-8")
    print("AXIEOS V0.14 - TASK136BB - RECENT LEDGER POST-APPLY RECONCILIATION")
    print(f"Ledger: {coverage['ledger_before']}/{coverage['ledger_after']} | "
          f"Exact inserted rows/hashes: {coverage['inserted_rows_exact']}/"
          f"{coverage['inserted_hashes_exact']}")
    print(f"Prior ledger rows preserved: {coverage['prior_ledger_rows_preserved']} | "
          f"Raw/protected tables unchanged: {coverage['raw_tables_unchanged']}/"
          f"{coverage['protected_tables_unchanged']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: production and backup read only | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (post-apply ledger reconciliation only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
