r"""Task136AF: independently reconcile the Task136AE ledger insert with backup.

Run from the AxieOS repository root:
    py -B .\scripts\v014_post_apply_reconcile.py

Reads production and the persistent pre-apply backup with SQLite mode=ro and
query_only. No database writes or network calls. Does not run accounting or
assign financial treatment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from v013_fullrow_materialization_sandbox import PROTECTED_TABLES, table_fingerprint


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError("STOP: " + reason)


def read(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing report: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def select_applied(explicit: Path | None, directory: Path) -> Path:
    if explicit is not None:
        return explicit
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        item, _ = read(path)
        if item.get("task") == "136AE" and item.get("mode") == "APPLIED":
            matches.append((item.get("created_at_utc", ""), path))
    require(bool(matches), f"no applied Task136AE report in {directory}; pass --applied PATH")
    return max(matches)[1]


def source_path(explicit: Path | None, directory: Path, digest: str) -> Path:
    if explicit is not None:
        return explicit
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        if hashlib.sha256(path.read_bytes()).hexdigest() == digest:
            matches.append(path)
    require(len(matches) == 1, f"expected one SHA-matched report in {directory}; pass explicit path")
    return matches[0]


def connect_ro(path: Path) -> sqlite3.Connection:
    db = path.expanduser().resolve()
    require(db.is_file(), f"database not found: {db}")
    conn = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=10)
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA trusted_schema=OFF")
    return conn


def original_digest_excluding(conn: sqlite3.Connection, new_hashes: set[str]) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    cursor = conn.execute("SELECT * FROM blockchain_transactions ORDER BY rowid")
    columns = [field[0] for field in cursor.description]
    require("source_row_hash" in columns, "ledger source_row_hash missing")
    source_index = columns.index("source_row_hash")
    for row in cursor:
        if row[source_index] in new_hashes:
            continue
        digest.update(repr(row).encode("utf-8"))
        digest.update(b"\n")
        count += 1
    return digest.hexdigest(), count


def compare(applied: dict, ad: dict, cache: dict,
            applied_sha: str, ad_sha: str, cache_sha: str,
            current: sqlite3.Connection, backup: sqlite3.Connection) -> dict:
    require(applied.get("task") == "136AE" and applied.get("mode") == "APPLIED" and
            applied.get("checkpoint96") == "OPEN" and applied.get("accepted_financial_totals") is None,
            "wrong applied report or finance state")
    require(applied.get("source_files", {}).get("136AD", {}).get("sha256") == ad_sha and
            applied.get("source_files", {}).get("136W", {}).get("sha256") == cache_sha,
            "applied report source digests differ")
    require(applied.get("plan", {}).get("task136ad_sha256") == ad_sha,
            "applied plan digest differs")
    require(ad.get("task") == "136AD" and ad.get("checkpoint96") == "OPEN" and
            ad.get("source_task136w_sha256") == cache_sha and
            ad.get("accepted_financial_totals") is None,
            "wrong Task136AD source")
    require(cache.get("task") == "136W" and cache.get("report_schema_version") == "1.1",
            "wrong Task136W source")
    rows = ad["guarded_ledger_rows"]
    result = applied.get("result") or {}
    before = result.get("ledger_before")
    after = result.get("ledger_after")
    require(len(rows) == result.get("inserted_rows") == applied["plan"]["source_rows"] and
            isinstance(before, int) and after == before + len(rows),
            "applied row count or ledger arithmetic differs")
    require(len(rows) == ad["coverage"]["guarded_rows"] and
            len({r["source_row_hash"] for r in rows}) == len(rows),
            "guarded rows changed or duplicate")
    new_hashes = {r["source_row_hash"] for r in rows}
    backup_count = backup.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
    current_count = current.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
    require(backup_count == before and current_count == after,
            "backup/current ledger count differs from applied report")
    require(backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
            current.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
            not current.execute("PRAGMA foreign_key_check").fetchall(),
            "SQLite integrity or foreign key check failed")
    require(all(table_fingerprint(backup, t) == table_fingerprint(current, t)
                for t in PROTECTED_TABLES), "protected accounting/gameplay table changed")
    backup_digest = table_fingerprint(backup, "blockchain_transactions")
    current_old_digest, old_count = original_digest_excluding(current, new_hashes)
    require(old_count == before and current_old_digest == backup_digest,
            "original ledger rows differ from pre-apply backup")
    for row in rows:
        columns = tuple(row)
        require(row["txn_fee_ron"] is None and row["status"] in (None, "Success"),
                "guarded fee/status changed")
        stored = current.execute(
            "SELECT " + ",".join(columns) +
            " FROM blockchain_transactions WHERE source_row_hash=?",
            (row["source_row_hash"],)).fetchall()
        require(len(stored) == 1 and stored[0] == tuple(row[k] for k in columns),
                f"inserted row differs: {row['source_row_hash']}")
        require(backup.execute("SELECT COUNT(*) FROM blockchain_transactions WHERE source_row_hash=?",
                               (row["source_row_hash"],)).fetchone()[0] == 0,
                "new source row already existed in backup")
    cache_rows = cache["candidate_rows"]
    require(len(cache_rows) == cache["coverage"]["candidate_hashes"],
            "Task136W cache count differs")
    cache_hashes = {str(r["txhash"]).lower() for r in cache_rows}
    inserted_hashes = {str(r["txhash"]).lower() for r in rows}
    require(len(cache_hashes) == len(cache_rows) and
            len(inserted_hashes) == ad["coverage"]["guarded_hashes"],
            "cached or inserted transaction hash coverage differs")
    found = Counter()
    for h, n in current.execute("SELECT LOWER(txhash),COUNT(*) FROM blockchain_transactions "
                                "WHERE txhash IS NOT NULL GROUP BY LOWER(txhash)"):
        if h in cache_hashes:
            found[h] = n
    require(set(found) == inserted_hashes and sum(found.values()) == len(rows),
            "post-apply cached ledger hash coverage differs")
    accounted = {str(h).lower() for (h,) in current.execute(
        "SELECT txhash FROM blockchain_accounting_records WHERE txhash IS NOT NULL")}
    require(not cache_hashes & accounted, "accounting unexpectedly changed for cached cohort")
    remaining = cache_hashes - inserted_hashes
    tx_only = {str(r["txhash"]).lower() for r in cache_rows if not r["raw_transfer_rows"]}
    quarantine = {str(r["txhash"]).lower() for r in ad["quarantined"]}
    require(remaining == tx_only | quarantine and not tx_only & quarantine,
            "remaining cache gap is not exactly transaction-only plus quarantine")
    return {"source_applied_sha256": applied_sha,
            "ledger_before": before, "ledger_after": after,
            "inserted_rows_exact": len(rows), "inserted_hashes_exact": len(inserted_hashes),
            "original_ledger_rows_preserved": old_count,
            "protected_tables_unchanged": len(PROTECTED_TABLES),
            "cached_hashes": len(cache_hashes),
            "remaining_without_ledger": len(remaining),
            "transaction_only_remaining": len(tx_only),
            "quarantined_remaining": len(quarantine),
            "cached_hashes_without_accounting": len(cache_hashes),
            "backup_integrity": "ok", "production_integrity": "ok"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    return "\n".join([
        "# AxieOS V0.14 — Task136AF Post-apply reconciliation", "",
        f"Production ledger: **{c['ledger_before']} → {c['ledger_after']}**. "
        f"Exactly **{c['inserted_rows_exact']}** new rows across **{c['inserted_hashes_exact']}** hashes "
        "match the guarded plan.", "",
        f"Original ledger rows preserved: **{c['original_ledger_rows_preserved']}**. "
        f"Protected tables unchanged: **{c['protected_tables_unchanged']}**. "
        "Backup and production integrity: **ok**.", "",
        f"Of **{c['cached_hashes']}** cached hashes, **{c['remaining_without_ledger']}** remain "
        f"without ledger rows: **{c['transaction_only_remaining']}** transaction-only and "
        f"**{c['quarantined_remaining']}** quarantined. All **{c['cached_hashes_without_accounting']}** "
        "still lack accounting rows.", "",
        "Ledger insertion does not verify income, expense, basis, profit, gas payer or PHP recovery. "
        "The old Task136W absence report is now a historical snapshot.", "",
        "Database opened: production and backup read only | Writes: 0 | Network: 0", "",
        "VALIDATION: PASS (post-apply source reconciliation only; Checkpoint 96 OPEN).", ""])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--applied", type=Path)
    parser.add_argument("--applied-dir", type=Path, default=Path("reports/axieos_v014/task136ae"))
    parser.add_argument("--ad", type=Path)
    parser.add_argument("--ad-dir", type=Path, default=Path("reports/axieos_v014/task136ad"))
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136af"))
    args = parser.parse_args()
    applied_path = select_applied(args.applied, args.applied_dir)
    applied, applied_sha = read(applied_path)
    ad_path = source_path(args.ad, args.ad_dir, applied["source_files"]["136AD"]["sha256"])
    cache_path = source_path(args.cache, args.cache_dir, applied["source_files"]["136W"]["sha256"])
    ad, ad_sha = read(ad_path)
    cache, cache_sha = read(cache_path)
    backup_path = Path(applied["result"]["backup_path"])
    with closing(connect_ro(args.db)) as current, closing(connect_ro(backup_path)) as backup:
        coverage = compare(applied, ad, cache, applied_sha, ad_sha, cache_sha,
                           current, backup)
    report = {"project": "AxieOS", "version": "0.14", "task": "136AF",
              "source_applied": applied_path.name, "source_ad": ad_path.name,
              "source_w": cache_path.name, "backup_path": str(backup_path),
              "coverage": coverage, "accepted_financial_totals": None,
              "database_writes": 0, "network_calls": 0, "checkpoint96": "OPEN",
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AF_Post_Apply_Reconciliation_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
            + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with mp.open("x", encoding="utf-8") as stream:
        stream.write(markdown(report))
    print("AXIEOS V0.14 - TASK136AF - POST-APPLY RECONCILIATION")
    print(f"Ledger: {coverage['ledger_before']}/{coverage['ledger_after']} | "
          f"Exact inserted rows/hashes: {coverage['inserted_rows_exact']}/{coverage['inserted_hashes_exact']}")
    print(f"Cached hashes still without ledger: {coverage['remaining_without_ledger']} "
          f"({coverage['transaction_only_remaining']} transaction-only + "
          f"{coverage['quarantined_remaining']} quarantined)")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: production and backup read only | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (post-apply source reconciliation only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
