r"""Task136BK: guarded production insert of 22 transaction detail raw rows.

From the AxieOS repository root:
    py -B .\scripts\v014_detail_raw_apply.py

Default opens production read only and creates a preflight report. Production
insertion requires --apply plus the exact plan SHA-256 printed by preflight.
Apply creates and verifies a persistent backup outside the repository, then
inserts only raw transaction rows atomically. No ledger or finance writers.
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

from v013_fullrow_materialization_sandbox import table_fingerprint
from v014_detail_raw_clone import TABLE, WATCH, old_raw_digest, plan
from v014_post_apply_reconcile import connect_ro, require
from v014_raw_import_clone import TX_FIELDS, by_sha, latest, load


INSERT = ("INSERT INTO " + TABLE + " (" + ",".join(TX_FIELDS) +
          ") VALUES (" + ",".join("?" for _ in TX_FIELDS) + ")")


def fingerprints(conn: sqlite3.Connection) -> dict[str, str]:
    return {table: table_fingerprint(conn, table) for table in (TABLE, *WATCH)}


def gate(conn: sqlite3.Connection, bj: dict, docs: dict[str, dict],
         shas: dict[str, str]) -> tuple[list[tuple], dict]:
    require(bj.get("task") == "136BJ" and bj.get("checkpoint96") == "OPEN" and
            bj.get("accepted_financial_totals") is None and
            bj.get("production_database_writes") == 0 and
            bj.get("network_calls") == 0 and
            all(bj.get("sources", {}).get(task, {}).get("sha256") == shas[task]
                for task in docs if task != "136BJ"),
            "Task136BJ source chain, finance boundary or read-only scope differs")
    cov = bj["coverage"]
    require(cov["clone_first_pass"] == cov["proposed_raw_transactions"] ==
                len(bj["proposed_raw_transaction_rows"]) and
            cov["clone_second_pass"] == 0 and
            cov["clone_integrity"] == "ok" and
            cov["clone_foreign_key_violations"] == 0 and
            cov["clone_deleted"] is True and
            cov["watched_clone_tables_unchanged"] == len(WATCH) and
            cov["prior_raw_rows_preserved"] == cov["production_raw_transactions"],
            "Task136BJ clone or preservation proof differs")
    rows = plan(docs["136BI"], {k: docs[k] for k in
        ("136BH", "136BF", "136BC", "136AY", "136AU")}, shas)
    digest = hashlib.sha256(json.dumps(rows,
        separators=(",", ":")).encode("utf-8")).hexdigest()
    require(digest == bj["plan_sha256"] and
            [dict(zip(TX_FIELDS, row)) for row in rows] ==
                bj["proposed_raw_transaction_rows"] and
            len(rows) == cov["proposed_raw_transactions"],
            "live Task136BI plan differs from Task136BJ clone")
    require(conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0] ==
                cov["production_raw_transactions"] and
            conn.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0] ==
                cov["production_ledger_rows"] ==
                    docs["136BB"]["coverage"]["ledger_after"] and
            conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
            not conn.execute("PRAGMA foreign_key_check").fetchall(),
            "production raw/ledger counts or integrity changed since clone")
    existing = {str(row[0]).lower() for row in conn.execute(
        f"SELECT tx_hash FROM {TABLE}")}
    hashes = {str(row[0]).lower() for row in rows}
    require(len(hashes) == len(rows) and not existing & hashes,
            "candidate raw transaction identity already in production")
    account = {str(row[0]).lower() for row in conn.execute(
        "SELECT txhash FROM blockchain_accounting_records WHERE txhash IS NOT NULL")}
    classifications = {str(row[0]).lower() for row in conn.execute(
        "SELECT txhash FROM blockchain_transaction_classifications WHERE txhash IS NOT NULL")}
    require(not hashes & (account | classifications),
            "raw detail cohort has new accounting/classification state")
    return rows, {"plan_sha256": digest,
                  "task136bj_sha256": shas["136BJ"],
                  "transaction_rows": len(rows),
                  "raw_before": cov["production_raw_transactions"],
                  "raw_after_if_applied": cov["production_raw_transactions"] + len(rows),
                  "ledger_unchanged": cov["production_ledger_rows"]}


def backup(source: sqlite3.Connection, db: Path, folder: Path,
           baseline: dict[str, str], raw_before: int) -> Path:
    target_dir = folder.expanduser().resolve()
    require(not target_dir.is_relative_to(Path.cwd().resolve()) and
            not db.is_relative_to(target_dir) and target_dir != db.parent,
            "backup directory must be outside repository and production DB folder")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / ("axieos_before_task136bk_" +
                           datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
                           "_" + uuid4().hex[:6] + ".db")
    require(not target.exists(), "backup path already exists")
    with closing(sqlite3.connect(target)) as dest:
        source.backup(dest)
        require(dest.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                not dest.execute("PRAGMA foreign_key_check").fetchall() and
                dest.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0] == raw_before and
                fingerprints(dest) == baseline,
                "backup content or SQLite integrity differs; no production insert")
    return target


def apply(db: Path, backup_path: Path, expected: list[tuple],
          baseline: dict[str, str], bj: dict, docs: dict[str, dict],
          shas: dict[str, str]) -> dict:
    require(backup_path.is_file(), "verified persistent backup missing")
    with closing(sqlite3.connect(db, timeout=15)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("BEGIN IMMEDIATE")
        try:
            actual, summary = gate(conn, bj, docs, shas)
            require(actual == expected and fingerprints(conn) == baseline,
                    "production changed after backup; no insert")
            initial = conn.total_changes
            conn.executemany(INSERT, expected)
            inserted = conn.total_changes - initial
            require(inserted == len(expected) and
                    conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0] ==
                        summary["raw_after_if_applied"],
                    "production raw insert count differs")
            for row in expected:
                stored = conn.execute("SELECT " + ",".join(TX_FIELDS) +
                    f" FROM {TABLE} WHERE tx_hash=?", (row[0],)).fetchone()
                require(stored == row, f"stored raw transaction differs: {row[0]}")
            digest, old_count = old_raw_digest(conn, {str(row[0]).lower()
                                                       for row in expected})
            require(old_count == summary["raw_before"] and
                    digest == baseline[TABLE] and
                    all(table_fingerprint(conn, table) == baseline[table]
                        for table in WATCH) and
                    conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                    not conn.execute("PRAGMA foreign_key_check").fetchall(),
                    "prior raw rows, watched tables, or SQLite integrity changed")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"inserted_rows": len(expected),
            "raw_before": summary["raw_before"],
            "raw_after": summary["raw_after_if_applied"],
            "ledger_unchanged": summary["ledger_unchanged"],
            "backup_path": str(backup_path),
            "watched_tables_unchanged": len(WATCH),
            "integrity_check": "ok", "foreign_key_violations": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path,
                        default=Path("data/blockchain/database/axieos.db"))
    for suffix in ("bj", "bi", "bh", "bf", "bc", "ay", "au", "bb"):
        parser.add_argument(f"--{suffix}-dir", type=Path,
                            default=Path(f"reports/axieos_v014/task136{suffix}"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("reports/axieos_v014/task136bk"))
    parser.add_argument("--backup-dir", type=Path,
                        default=Path.home() / "AxieOSBackups")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-plan-sha256")
    args = parser.parse_args()
    require(not args.confirm_plan_sha256 or args.apply,
            "--confirm-plan-sha256 is only valid with --apply")
    paths = {"136BJ": latest(args.bj_dir, "136BJ")}
    bj, bj_sha = load(paths["136BJ"])
    for task in ("136BI", "136BH", "136BF", "136BC", "136AY", "136AU", "136BB"):
        paths[task] = by_sha(getattr(args, task[3:].lower() + "_dir"),
                              bj["sources"][task]["sha256"], task)
    docs, shas = {}, {}
    for task, path in paths.items():
        docs[task], shas[task] = load(path)
    db = args.db.expanduser().resolve()
    with closing(connect_ro(db)) as source:
        source.execute("BEGIN")
        rows, summary = gate(source, docs["136BJ"], docs, shas)
        baseline = fingerprints(source)
        if args.apply:
            require(args.confirm_plan_sha256 == summary["plan_sha256"],
                    "--apply requires the exact plan SHA-256 printed by preflight")
            backup_path = backup(source, db, args.backup_dir,
                                 baseline, summary["raw_before"])
        else:
            backup_path = None
    if args.apply:
        try:
            result = apply(db, backup_path, rows, baseline, docs["136BJ"], docs, shas)
        except Exception as exc:
            raise RuntimeError("STOP: production raw insert failed or rolled back; "
                               f"persistent backup remains at {backup_path}: {exc}") from exc
    else:
        result = None
    report = {"project": "AxieOS", "version": "0.14", "task": "136BK",
              "mode": "APPLIED" if result else "READ_ONLY_PREFLIGHT",
              "sources": {task: {"filename": path.name, "sha256": shas[task]}
                          for task, path in paths.items()},
              "plan": summary, "result": result,
              "accepted_financial_totals": None,
              "production_database_opened_read_only": not args.apply,
              "production_database_writes": 0 if result is None else result["inserted_rows"],
              "network_calls": 0, "checkpoint96": "OPEN",
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136BK_Detail_Raw_" +
            ("Applied_" if result else "Preflight_") +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
            "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    lines = ["# AxieOS V0.14 — Task136BK Guarded detail raw insert", "",
             f"Mode: **{report['mode']}**. Plan SHA-256: "
             f"`{summary['plan_sha256']}`. Proposed rows: "
             f"**{summary['transaction_rows']}**.", ""]
    if result:
        lines += [f"Production raw transactions before/after: "
                  f"**{result['raw_before']}/{result['raw_after']}**. "
                  f"Backup: `{result['backup_path']}`.", ""]
    else:
        lines += [f"Production raw transactions unchanged: "
                  f"**{summary['raw_before']}**. No backup created.", ""]
    lines += ["Ledger, accounting and economics remain outside this insert. "
              "Raw fee fields do not establish verified gas expense or payer.", "",
              "Verified financial totals: **UNKNOWN**. Checkpoint 96: **OPEN**.", "",
              "Network calls: 0", ""]
    mp.write_text("\n".join(lines), encoding="utf-8")
    print("AXIEOS V0.14 - TASK136BK - GUARDED DETAIL RAW " +
          ("APPLIED" if result else "READ-ONLY PREFLIGHT"))
    print(f"Plan SHA-256: {summary['plan_sha256']} | "
          f"Raw transaction rows: {summary['transaction_rows']}")
    if result:
        print(f"Production raw before/after: {result['raw_before']}/"
              f"{result['raw_after']} | Backup: {result['backup_path']}")
    else:
        print(f"Production raw unchanged: {summary['raw_before']} | No backup created")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("VALIDATION: PASS (guarded raw " +
          ("insert only" if result else "preflight only") +
          "; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
