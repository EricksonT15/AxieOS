r"""Task136AE: gated production insert of the Task136AD guarded ledger rows.

From the AxieOS repository root:
    py -B .\scripts\v014_guarded_ledger_apply.py

Default is a read-only preflight. An explicit --apply with the Task136AD file's
SHA-256 is required for a production write. Apply makes a durable SQLite backup
outside the repository, then inserts only the guarded ledger rows in one
transaction. No accounting/economics materialization or network access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from v014_guarded_ledger_sandbox import build, find_report, read
from v014_cache_cohort_materialization_sandbox import (
    LEDGER_FIELDS, PROTECTED_TABLES, readonly_connect, require, table_fingerprint,
)


STRICT_INSERT = ("INSERT INTO blockchain_transactions (" + ",".join(LEDGER_FIELDS)
                 + ") VALUES (" + ",".join("?" for _ in LEDGER_FIELDS) + ")")


def source_gate(conn: sqlite3.Connection, ac: dict, cache: dict, ad: dict,
                ac_sha: str, cache_sha: str, ad_sha: str) -> tuple[list[tuple], dict]:
    require(ad.get("task") == "136AD" and ad.get("checkpoint96") == "OPEN" and
            ad.get("production_database_writes") == 0 and
            ad.get("accepted_financial_totals") is None and
            ad.get("network_calls") == 0,
            "Task136AD validation state changed")
    require(ad.get("source_task136ac_sha256") == ac_sha and
            ad.get("source_task136w_sha256") == cache_sha,
            "Task136AD source snapshot digests differ")
    reported = ad.get("guarded_ledger_rows")
    cov, sandbox = ad.get("coverage", {}), ad.get("sandbox", {})
    require(isinstance(reported, list) and len(reported) == cov.get("guarded_rows") and
            sandbox.get("clone_rows_first_pass") == len(reported) and
            sandbox.get("clone_rows_second_pass") == 0 and
            sandbox.get("clone_integrity") == "ok" and
            sandbox.get("clone_foreign_key_errors") == 0 and
            sandbox.get("production_ledger_before_after", [None])[0] ==
            sandbox.get("production_ledger_before_after", [None, None])[-1],
            "Task136AD clone or proposed row validation differs")
    require(all(set(r) == set(LEDGER_FIELDS) and r["txn_fee_ron"] is None
                and r["status"] in (None, "Success") for r in reported),
            "Task136AD row schema or unknown fee/status changed")
    require(len({r["source_row_hash"] for r in reported}) == len(reported),
            "Task136AD source-row hashes duplicate")
    reproduced, safe = build(ac, cache, ac_sha, cache_sha, conn)
    require(reproduced["coverage"] == cov and
            reproduced["quarantined"] == ad.get("quarantined") and
            reproduced["guarded_ledger_rows"] == reported,
            "Task136AD plan differs from live source; rerun guarded sandbox")
    require(len(safe) == len(reported) and cov.get("guarded_hashes") == len({r[0] for r in safe}),
            "Task136AD guarded hash count differs")
    fields = {r[1]: r for r in conn.execute('PRAGMA table_info("blockchain_transactions")')}
    require("txn_fee_ron" in fields and "status" in fields and
            fields["txn_fee_ron"][3] == 0 and fields["status"][3] == 0,
            "ledger cannot store unknown fee/status as NULL")
    ledger_before = conn.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
    require(ledger_before == sandbox["production_ledger_before_after"][0],
            "production ledger count changed since guarded rehearsal")
    return safe, {"task136ad_sha256": ad_sha, "source_rows": len(safe),
                  "source_hashes": cov["guarded_hashes"],
                  "quarantined_rows": cov["quarantined_rows"],
                  "transaction_only_hashes_still_omitted": cov["transaction_only_hashes_still_omitted"],
                  "ledger_before": ledger_before}


def fingerprint(conn: sqlite3.Connection) -> dict[str, str]:
    return {table: table_fingerprint(conn, table)
            for table in ("blockchain_transactions", *PROTECTED_TABLES)}


def save_backup(source: sqlite3.Connection, backup_dir: Path,
                baseline: dict[str, str], ledger_before: int) -> Path:
    folder = backup_dir.expanduser().resolve()
    repo = Path.cwd().resolve()
    require(not folder.is_relative_to(repo),
            "backup directory must be outside the Git repository")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("axieos_before_task136ae_"
                     + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
                     + "_" + uuid4().hex[:6] + ".db")
    require(not path.exists(), "backup path already exists")
    with closing(sqlite3.connect(path)) as backup:
        source.backup(backup)
        require(backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                backup.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0] == ledger_before and
                fingerprint(backup) == baseline,
                "backup integrity or content differs; no production insert")
    return path


def apply(db: Path, ac: dict, cache: dict, ad: dict, ac_sha: str, cache_sha: str,
          ad_sha: str, safe: list[tuple], backup_path: Path,
          baseline: dict[str, str], ledger_before: int) -> dict:
    require(backup_path.is_file(), "backup missing; no production insert")
    with closing(sqlite3.connect(db, timeout=10)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("BEGIN IMMEDIATE")
        try:
            live_safe, _ = source_gate(conn, ac, cache, ad, ac_sha, cache_sha, ad_sha)
            require(live_safe == safe and fingerprint(conn) == baseline,
                    "database changed after backup; no production insert")
            before = conn.total_changes
            conn.executemany(STRICT_INSERT, safe)
            inserted = conn.total_changes - before
            require(inserted == len(safe), "production insert count differs")
            after = conn.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
            require(after == ledger_before + len(safe), "production ledger count differs")
            require(all(table_fingerprint(conn, t) == baseline[t] for t in PROTECTED_TABLES),
                    "protected production table changed")
            require(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                    not conn.execute("PRAGMA foreign_key_check").fetchall(),
                    "post-insert SQLite integrity or foreign key check failed")
            for row in safe:
                stored = conn.execute(
                    "SELECT " + ",".join(LEDGER_FIELDS) +
                    " FROM blockchain_transactions WHERE source_row_hash=?", (row[-1],)).fetchone()
                require(stored == row, f"inserted ledger row differs: {row[-1]}")
            conn.execute("CREATE TEMP TABLE _task136ae_new (h TEXT PRIMARY KEY)")
            conn.executemany("INSERT INTO _task136ae_new VALUES (?)", ((r[-1],) for r in safe))
            old_digest = hashlib.sha256()
            old_count = 0
            for old_row in conn.execute(
                    "SELECT * FROM blockchain_transactions WHERE source_row_hash IS NULL "
                    "OR source_row_hash NOT IN (SELECT h FROM _task136ae_new) ORDER BY rowid"):
                old_digest.update(repr(old_row).encode("utf-8"))
                old_digest.update(b"\n")
                old_count += 1
            require(old_count == ledger_before and
                    old_digest.hexdigest() == baseline["blockchain_transactions"],
                    "existing production ledger rows changed")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"inserted_rows": len(safe), "ledger_before": ledger_before,
            "ledger_after": ledger_before + len(safe), "backup_path": str(backup_path),
            "protected_tables_unchanged": len(PROTECTED_TABLES),
            "integrity_check": "ok", "foreign_key_errors": 0}


def markdown(report: dict) -> str:
    c = report["plan"]
    lines = ["# AxieOS V0.14 — Task136AE Guarded ledger update", "",
             f"Mode: **{report['mode']}**. Task136AD SHA-256: `{c['task136ad_sha256']}`.", "",
             f"Guarded ledger rows: **{c['source_rows']}** across **{c['source_hashes']}** hashes; "
             f"quarantined rows: **{c['quarantined_rows']}**. "
             f"Transaction-only hashes still omitted: **{c['transaction_only_hashes_still_omitted']}**.", ""]
    if report["mode"] == "APPLIED":
        r = report["result"]
        lines += [f"Production ledger before/after: **{r['ledger_before']}/{r['ledger_after']}**. "
                  f"Inserted rows: **{r['inserted_rows']}**.", "",
                  f"Backup outside repository: `{r['backup_path']}`.", ""]
    else:
        lines += ["This preflight did not create a backup or write to production.", ""]
    lines += ["Unknown gas remains NULL. A raw transfer without a matching transaction "
              "keeps status NULL. No accounting, cost basis, profit or PHP valuation is accepted.", "",
              "Checkpoint 96: **OPEN**. Verified financial totals: **UNKNOWN**.", "",
              "Network calls: 0", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--ac", type=Path)
    parser.add_argument("--ac-dir", type=Path, default=Path("reports/axieos_v014/task136ac"))
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--ad", type=Path)
    parser.add_argument("--ad-dir", type=Path, default=Path("reports/axieos_v014/task136ad"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136ae"))
    parser.add_argument("--backup-dir", type=Path, default=Path.home() / "AxieOSBackups")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-plan-sha256", help="Exact SHA-256 printed by preflight")
    args = parser.parse_args()
    require(not args.confirm_plan_sha256 or args.apply,
            "--confirm-plan-sha256 is only for --apply")
    ac_path = args.ac or find_report(args.ac_dir, "136AC")
    cache_path = args.cache or find_report(args.cache_dir, "136W")
    ad_path = args.ad or find_report(args.ad_dir, "136AD")
    ac, ac_sha = read(ac_path)
    cache, cache_sha = read(cache_path)
    ad, ad_sha = read(ad_path)
    db = args.db.resolve()
    require(db.is_file(), f"database missing: {db}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with closing(readonly_connect(db)) as source:
        source.execute("PRAGMA query_only=ON")
        safe, plan_summary = source_gate(source, ac, cache, ad, ac_sha, cache_sha, ad_sha)
        baseline = fingerprint(source)
        if args.apply:
            require(args.confirm_plan_sha256 == ad_sha,
                    "--apply requires exact Task136AD SHA-256 from preflight")
            backup_path = save_backup(source, args.backup_dir,
                                      baseline, plan_summary["ledger_before"])
        else:
            backup_path = None
    if args.apply:
        try:
            result = apply(db, ac, cache, ad, ac_sha, cache_sha, ad_sha, safe,
                           backup_path, baseline, plan_summary["ledger_before"])
        except Exception as exc:
            raise RuntimeError(f"STOP: production update failed or rolled back; "
                               f"persistent backup remains at {backup_path}: {exc}") from exc
    else:
        result = None
    report = {"project": "AxieOS", "version": "0.14", "task": "136AE",
              "mode": "APPLIED" if args.apply else "READ_ONLY_PREFLIGHT",
              "source_files": {"136W": {"name": cache_path.name, "sha256": cache_sha},
                               "136AC": {"name": ac_path.name, "sha256": ac_sha},
                               "136AD": {"name": ad_path.name, "sha256": ad_sha}},
              "plan": plan_summary, "result": result,
              "source_database": str(args.db),
              "accepted_financial_totals": None, "network_calls": 0,
              "checkpoint96": "OPEN", "created_at_utc": datetime.now(timezone.utc).isoformat()}
    stem = ("AxieOS_V014_Task136AE_Guarded_Ledger_"
            + ("Applied_" if args.apply else "Preflight_")
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
            + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with mp.open("x", encoding="utf-8") as stream:
        stream.write(markdown(report))
    print("AXIEOS V0.14 - TASK136AE - GUARDED LEDGER "
          + ("APPLIED" if args.apply else "READ-ONLY PREFLIGHT"))
    print(f"Plan SHA-256: {ad_sha} | Guarded rows: {len(safe)} | "
          f"Transfer hashes: {plan_summary['source_hashes']}")
    if result:
        print(f"Production ledger before/after: {result['ledger_before']}/{result['ledger_after']} | "
              f"Backup: {result['backup_path']}")
    else:
        print(f"Production ledger unchanged: {plan_summary['ledger_before']} | No backup created")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("VALIDATION: PASS (guarded ledger "
          + ("insert only" if args.apply else "preflight only")
          + "; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
