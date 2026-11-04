r"""Task136BA: guarded insert of Task136AY recent full ledger rows.

Run from the AxieOS repository root:
    py -B .\scripts\v014_recent_ledger_apply.py

Default is read-only preflight. Production insertion requires --apply and the
exact Task136AY SHA-256 printed by preflight. Apply first creates and verifies
a persistent SQLite backup outside the repository, then inserts only the
saved 139-row cohort inside one transaction. No network or finance writers.
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

from v013_fullrow_materialization_sandbox import PROTECTED_TABLES, table_fingerprint
from v014_cache_cohort_materialization_sandbox import LEDGER_FIELDS
from v014_post_apply_reconcile import connect_ro, require
from v014_raw_import_clone import by_sha, latest, load
from v014_recent_ledger_preflight import check


INSERT = ("INSERT INTO blockchain_transactions (" + ",".join(LEDGER_FIELDS) +
          ") VALUES (" + ",".join("?" for _ in LEDGER_FIELDS) + ")")
WATCHED = ("blockchain_transactions", "ronin_api_transactions_raw",
           "ronin_token_transfers_raw", *PROTECTED_TABLES)


def fingerprint(conn: sqlite3.Connection) -> dict[str, str]:
    return {table: table_fingerprint(conn, table) for table in WATCHED}


def gate(conn: sqlite3.Connection, az: dict, az_sha: str,
         ay: dict, ay_sha: str, sources: dict[str, dict],
         shas: dict[str, str]) -> tuple[list[tuple], dict]:
    require(az.get("task") == "136AZ" and
            az.get("mode") == "READ_ONLY_PREFLIGHT" and
            az.get("checkpoint96") == "OPEN" and
            az.get("accepted_financial_totals") is None and
            az.get("production_database_writes") == 0 and
            az.get("network_calls") == 0 and
            az.get("backup_created") is False and
            az.get("sources", {}).get("136AY", {}).get("sha256") == ay_sha and
            all(az.get("sources", {}).get(task, {}).get("sha256") == shas[task]
                for task in sources),
            "Task136AZ preflight identity or source chain differs")
    plan = check(conn, ay, ay_sha, sources, shas)
    require(plan == az.get("plan"),
            "live production state differs from Task136AZ preflight; rerun preflight")
    reported = ay["guarded_ledger_rows"]
    selected = [tuple(row[field] for field in LEDGER_FIELDS) for row in reported]
    require(len(selected) == plan["guarded_rows"] and
            len({row[-1] for row in selected}) == len(selected) and
            all(row[10] is None and row[11] in (None, "Success") for row in selected),
            "Task136AY row count, identity, fee or status differs")
    return selected, {"task136az_sha256": az_sha,
                      "task136ay_sha256": ay_sha,
                      "guarded_rows": len(selected),
                      "guarded_hashes": plan["guarded_hashes"],
                      "ledger_before": plan["ledger_before"],
                      "ledger_after_if_applied": plan["ledger_if_applied"],
                      "transaction_only_hashes_omitted":
                          plan["transaction_only_hashes_omitted"],
                      "null_fee_rows": plan["unknown_fee_rows"],
                      "null_status_rows": plan["null_status_rows"]}


def backup(source: sqlite3.Connection, db: Path, backup_dir: Path,
           baseline: dict[str, str], ledger_before: int) -> Path:
    folder = backup_dir.expanduser().resolve()
    require(not folder.is_relative_to(Path.cwd().resolve()) and
            not db.is_relative_to(folder) and folder != db.parent,
            "backup directory must be outside the repository and production DB folder")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / ("axieos_before_task136ba_" +
                       datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
                       "_" + uuid4().hex[:6] + ".db")
    require(not target.exists(), "backup path already exists")
    with closing(sqlite3.connect(target)) as dest:
        source.backup(dest)
        require(dest.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                not dest.execute("PRAGMA foreign_key_check").fetchall() and
                dest.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
                    == ledger_before and fingerprint(dest) == baseline,
                "backup integrity or contents differ; no production insert")
    return target


def prior_ledger_fingerprint(conn: sqlite3.Connection, inserted: set[str]) -> tuple[str, int]:
    sha = hashlib.sha256()
    count = 0
    cursor = conn.execute("SELECT * FROM blockchain_transactions ORDER BY rowid")
    fields = [item[0] for item in cursor.description]
    require("source_row_hash" in fields, "ledger source row identity missing")
    index = fields.index("source_row_hash")
    for row in cursor:
        if row[index] in inserted:
            continue
        sha.update(repr(row).encode("utf-8"))
        sha.update(b"\n")
        count += 1
    return sha.hexdigest(), count


def apply(db: Path, backup_path: Path, baseline: dict[str, str],
          az: dict, az_sha: str, ay: dict, ay_sha: str,
          sources: dict[str, dict], shas: dict[str, str],
          expected: list[tuple], ledger_before: int) -> dict:
    require(backup_path.is_file(), "verified persistent backup missing")
    with closing(sqlite3.connect(db, timeout=15)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("BEGIN IMMEDIATE")
        try:
            live, plan = gate(conn, az, az_sha, ay, ay_sha, sources, shas)
            require(live == expected and plan["ledger_before"] == ledger_before and
                    fingerprint(conn) == baseline,
                    "production changed after backup; no insert")
            initial = conn.total_changes
            conn.executemany(INSERT, expected)
            inserted = conn.total_changes - initial
            require(inserted == len(expected) and
                    conn.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
                        == ledger_before + inserted,
                    "exact insert or ledger count differs")
            for row in expected:
                stored = conn.execute("SELECT " + ",".join(LEDGER_FIELDS) +
                                      " FROM blockchain_transactions WHERE source_row_hash=?",
                                      (row[-1],)).fetchone()
                require(stored == row,
                        f"stored ledger row differs: {row[-1]}")
            old_sha, old_count = prior_ledger_fingerprint(
                conn, {row[-1] for row in expected})
            require(old_count == ledger_before and
                    old_sha == baseline["blockchain_transactions"] and
                    all(table_fingerprint(conn, table) == baseline[table]
                        for table in WATCHED if table != "blockchain_transactions") and
                    conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                    not conn.execute("PRAGMA foreign_key_check").fetchall(),
                    "existing rows, watched tables or SQLite integrity changed")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"inserted_rows": len(expected),
            "inserted_hashes": len({row[0] for row in expected}),
            "ledger_before": ledger_before,
            "ledger_after": ledger_before + len(expected),
            "backup_path": str(backup_path),
            "protected_tables_unchanged": len(WATCHED) - 1,
            "integrity_check": "ok", "foreign_key_violations": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path,
                        default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--az", type=Path)
    parser.add_argument("--az-dir", type=Path,
                        default=Path("reports/axieos_v014/task136az"))
    parser.add_argument("--ay-dir", type=Path,
                        default=Path("reports/axieos_v014/task136ay"))
    for task in ("136AX", "136AU", "136AW", "136AF"):
        parser.add_argument(f"--{task.lower()}-dir", type=Path,
                            default=Path(f"reports/axieos_v014/task{task.lower()}"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("reports/axieos_v014/task136ba"))
    parser.add_argument("--backup-dir", type=Path,
                        default=Path.home() / "AxieOSBackups")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-plan-sha256")
    args = parser.parse_args()
    require(not args.confirm_plan_sha256 or args.apply,
            "--confirm-plan-sha256 is only valid with --apply")
    az_path = args.az or latest(args.az_dir, "136AZ")
    az, az_sha = load(az_path)
    ay_path = by_sha(args.ay_dir, az["sources"]["136AY"]["sha256"], "136AY")
    ay, ay_sha = load(ay_path)
    paths = {task: by_sha(getattr(args, f"{task.lower()}_dir"),
                          az["sources"][task]["sha256"], task)
             for task in ("136AX", "136AU", "136AW", "136AF")}
    loaded = {task: load(path) for task, path in paths.items()}
    sources = {task: doc for task, (doc, digest) in loaded.items()}
    shas = {task: digest for task, (doc, digest) in loaded.items()}
    db = args.db.expanduser().resolve()
    with closing(connect_ro(db)) as source:
        source.execute("BEGIN")
        selected, summary = gate(source, az, az_sha, ay, ay_sha, sources, shas)
        baseline = fingerprint(source)
        require(baseline == az["plan"]["watched_table_fingerprints"],
                "preflight watched production fingerprints differ")
        if args.apply:
            require(args.confirm_plan_sha256 == ay_sha,
                    "--apply requires exact Task136AY SHA-256 printed by preflight")
            backup_path = backup(source, db, args.backup_dir,
                                 baseline, summary["ledger_before"])
        else:
            backup_path = None
    if args.apply:
        try:
            result = apply(db, backup_path, baseline, az, az_sha, ay, ay_sha,
                           sources, shas, selected, summary["ledger_before"])
        except Exception as exc:
            raise RuntimeError("STOP: production insert failed or rolled back; "
                               f"persistent backup remains at {backup_path}: {exc}") from exc
    else:
        result = None
    report = {"project": "AxieOS", "version": "0.14", "task": "136BA",
              "mode": "APPLIED" if args.apply else "READ_ONLY_PREFLIGHT",
              "sources": {"136AZ": {"filename": az_path.name, "sha256": az_sha},
                          "136AY": {"filename": ay_path.name, "sha256": ay_sha},
                          **{task: {"filename": paths[task].name,
                                    "sha256": shas[task]} for task in paths}},
              "plan": summary, "result": result,
              "accepted_financial_totals": None,
              "production_database_opened_read_only": not args.apply,
              "production_database_writes": 0 if result is None else result["inserted_rows"],
              "network_calls": 0, "checkpoint96": "OPEN",
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136BA_Recent_Ledger_" +
            ("Applied_" if args.apply else "Preflight_") +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
            "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    lines = ["# AxieOS V0.14 — Task136BA Guarded recent ledger update", "",
             f"Mode: **{report['mode']}**. Task136AY SHA-256: `{ay_sha}`.", "",
             f"Guarded rows/hashes: **{summary['guarded_rows']}/"
             f"{summary['guarded_hashes']}**. Transaction-only hashes omitted: "
             f"**{summary['transaction_only_hashes_omitted']}**.", ""]
    if result:
        lines += [f"Production ledger before/after: **{result['ledger_before']}/"
                  f"{result['ledger_after']}**. Persistent backup: "
                  f"`{result['backup_path']}`.", ""]
    else:
        lines += [f"Production ledger unchanged: **{summary['ledger_before']}**. "
                  "No backup created.", ""]
    lines += ["Unknown gas is NULL; transfer-only status stays NULL. "
              "No accounting, cost basis, profit, or PHP recovery accepted.", "",
              "Verified financial totals: **UNKNOWN**. Checkpoint 96: **OPEN**.", "",
              "Network calls: 0", ""]
    mp.write_text("\n".join(lines), encoding="utf-8")
    print("AXIEOS V0.14 - TASK136BA - GUARDED RECENT LEDGER " +
          ("APPLIED" if result else "READ-ONLY PREFLIGHT"))
    print(f"Plan SHA-256: {ay_sha} | Guarded rows/hashes: "
          f"{summary['guarded_rows']}/{summary['guarded_hashes']}")
    if result:
        print(f"Production ledger before/after: {result['ledger_before']}/"
              f"{result['ledger_after']} | Backup: {result['backup_path']}")
    else:
        print(f"Production ledger unchanged: {summary['ledger_before']} | No backup created")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("VALIDATION: PASS (guarded ledger " +
          ("insert only" if result else "preflight only") +
          "; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
