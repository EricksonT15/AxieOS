r"""Task136AW: guarded raw cache insert, defaulting to read-only preflight.

From the AxieOS repository root:
    py -B .\scripts\v014_raw_import_apply.py

Production writes require --apply and --confirm-plan-sha256 with the exact
preflight hash. Apply creates and checks a persistent backup outside the repo,
then inserts only the Task136AU raw transaction/transfer rows atomically.
No network, ledger, classification, economics or accounting writers run.
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
from v014_post_apply_reconcile import connect_ro, require
from v014_raw_import_clone import TABLES, by_sha, latest, load, plan


WATCH = ("blockchain_transactions",) + PROTECTED_TABLES + tuple(TABLES)


def fingerprint(conn: sqlite3.Connection) -> dict[str, str]:
    return {table: table_fingerprint(conn, table) for table in WATCH}


def strict_sql(table: str) -> str:
    require(table in TABLES, "unexpected raw table")
    fields = TABLES[table]
    return (f"INSERT INTO {table} (" + ",".join(fields) + ") VALUES (" +
            ",".join("?" for _ in fields) + ")")


def gate(conn: sqlite3.Connection, prepared: dict[str, list[tuple]],
         digest: str, av: dict, av_sha: str,
         shas: dict[str, str]) -> dict:
    require(av.get("task") == "136AV" and av.get("checkpoint96") == "OPEN" and
            av.get("accepted_financial_totals") is None and
            av.get("production_database_writes") == 0 and
            av.get("plan_sha256") == digest and
            av["sources"]["136AU"]["sha256"] == shas["136AU"] and
            av["sources"]["136AR"]["sha256"] == shas["136AR"] and
            av["sources"]["136W"]["sha256"] == shas["136W"] and
            av["coverage"]["clone_integrity"] == "ok" and
            av["coverage"]["clone_deleted"] is True and
            av["coverage"]["production_writes"] == 0,
            "Task136AV clone, source chain or plan differs")
    require(av["coverage"]["proposed_transactions"] ==
            len(prepared["ronin_api_transactions_raw"]) and
            av["coverage"]["proposed_transfers"] ==
            len(prepared["ronin_token_transfers_raw"]) and
            all(av["coverage"]["clone_first_pass"][t] == len(prepared[t]) and
                av["coverage"]["clone_second_pass"][t] == 0 for t in TABLES),
            "Task136AV clone insert coverage differs")
    require(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
            "production database integrity failed")
    before = {}
    for table, fields in TABLES.items():
        actual = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        require(set(fields) <= actual, f"{table}: schema changed")
        before[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        require(before[table] == av["coverage"]["production_raw_before"][table],
                f"{table}: production count differs from clone preflight")
        identity = "tx_hash" if table == "ronin_api_transactions_raw" else "transfer_key"
        keys = {str(row[0]).lower() for row in conn.execute(f"SELECT {identity} FROM {table}")}
        require(not keys & {str(row[0]).lower() for row in prepared[table]},
                f"{table}: proposed source identity already exists")
    return {"task136av_sha256": av_sha, "plan_sha256": digest,
            "transaction_rows": len(prepared["ronin_api_transactions_raw"]),
            "transfer_rows": len(prepared["ronin_token_transfers_raw"]),
            "raw_before": before}


def backup(source: sqlite3.Connection, db: Path, backup_dir: Path,
           baseline: dict[str, str], before: dict[str, int]) -> Path:
    folder = backup_dir.expanduser().resolve()
    repo = Path.cwd().resolve()
    require(not folder.is_relative_to(repo) and not db.is_relative_to(folder),
            "backup directory must be outside repository and production DB folder")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("axieos_before_task136aw_" +
                     datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
                     "_" + uuid4().hex[:6] + ".db")
    require(not path.exists(), "backup path exists")
    with closing(sqlite3.connect(path)) as dest:
        source.backup(dest)
        require(dest.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                fingerprint(dest) == baseline and
                all(dest.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == count
                    for table, count in before.items()),
                "backup integrity or raw source differs; no production insert")
    return path


def old_digest(conn: sqlite3.Connection, table: str, new_keys: list[str]) -> str:
    identity = "tx_hash" if table == "ronin_api_transactions_raw" else "transfer_key"
    conn.execute("CREATE TEMP TABLE _task136aw_new(key TEXT PRIMARY KEY)")
    try:
        conn.executemany("INSERT INTO _task136aw_new VALUES (?)", ((k,) for k in new_keys))
        sha = hashlib.sha256()
        for row in conn.execute(f"SELECT * FROM {table} WHERE {identity} NOT IN "
                                "(SELECT key FROM _task136aw_new) ORDER BY rowid"):
            sha.update(repr(row).encode("utf-8"))
            sha.update(b"\n")
        return sha.hexdigest()
    finally:
        conn.execute("DROP TABLE _task136aw_new")


def apply(db: Path, prepared: dict[str, list[tuple]], digest: str,
          av: dict, av_sha: str, shas: dict[str, str],
          baseline: dict[str, str], backup_path: Path) -> dict:
    require(backup_path.is_file(), "checked backup missing")
    with closing(sqlite3.connect(db, timeout=15)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("BEGIN IMMEDIATE")
        try:
            pre = gate(conn, prepared, digest, av, av_sha, shas)
            require(fingerprint(conn) == baseline,
                    "production changed after backup; no insert")
            inserted = {}
            for table in TABLES:
                count_before = conn.total_changes
                conn.executemany(strict_sql(table), prepared[table])
                inserted[table] = conn.total_changes - count_before
                require(inserted[table] == len(prepared[table]) and
                        conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] ==
                        pre["raw_before"][table] + inserted[table],
                        f"{table}: exact production insert count differs")
                for source in prepared[table]:
                    identity = "tx_hash" if table == "ronin_api_transactions_raw" else "transfer_key"
                    stored = conn.execute(f"SELECT {','.join(TABLES[table])} FROM {table} "
                                          f"WHERE {identity}=?", (source[0],)).fetchone()
                    require(stored == source,
                            f"{table}: stored source row differs after insert")
                require(old_digest(conn, table, [str(row[0]) for row in prepared[table]]) ==
                        baseline[table], f"{table}: prior raw rows changed")
            require(all(table_fingerprint(conn, table) == baseline[table]
                        for table in ("blockchain_transactions",) + PROTECTED_TABLES) and
                    conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                    not conn.execute("PRAGMA foreign_key_check").fetchall(),
                    "protected production tables or SQLite integrity changed")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"inserted": inserted, "raw_before": pre["raw_before"],
            "raw_after": {t: pre["raw_before"][t] + inserted[t] for t in TABLES},
            "backup_path": str(backup_path), "integrity_check": "ok",
            "protected_tables_unchanged": len(PROTECTED_TABLES) + 1}


def markdown(report: dict) -> str:
    p = report["plan"]
    lines = ["# AxieOS V0.14 — Task136AW Guarded raw cache update", "",
             f"Mode: **{report['mode']}**. Plan SHA-256: `{p['plan_sha256']}`.", "",
             f"Raw transaction/transfer rows: **{p['transaction_rows']}/"
             f"{p['transfer_rows']}**.", ""]
    if report["result"]:
        lines += [f"Production raw before: **{report['result']['raw_before']}**; "
                  f"after: **{report['result']['raw_after']}**.", "",
                  f"Persistent backup: `{report['result']['backup_path']}`.", ""]
    else:
        lines += ["Preflight opened production read only; no backup or production write.", ""]
    lines += ["Only raw source tables are in scope. Transaction classification, "
              "ledger materialization, accounting, cost basis, profit and PHP "
              "recovery remain unaccepted. Verified totals: **UNKNOWN**.", "",
              "Network calls: 0 | Checkpoint 96: **OPEN**.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--au", type=Path)
    parser.add_argument("--au-dir", type=Path, default=Path("reports/axieos_v014/task136au"))
    parser.add_argument("--av", type=Path)
    parser.add_argument("--av-dir", type=Path, default=Path("reports/axieos_v014/task136av"))
    parser.add_argument("--ar-dir", type=Path, default=Path("reports/axieos_v014/task136ar"))
    parser.add_argument("--w-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136aw"))
    parser.add_argument("--backup-dir", type=Path, default=Path.home() / "AxieOSBackups")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-plan-sha256")
    args = parser.parse_args()
    require(not args.confirm_plan_sha256 or args.apply,
            "--confirm-plan-sha256 is only valid with --apply")
    ap = args.au or latest(args.au_dir, "136AU")
    vp = args.av or latest(args.av_dir, "136AV")
    au, au_sha = load(ap)
    av, av_sha = load(vp)
    rp = by_sha(args.ar_dir, av["sources"]["136AR"]["sha256"], "136AR")
    wp = by_sha(args.w_dir, av["sources"]["136W"]["sha256"], "136W")
    ar, ar_sha = load(rp)
    w, w_sha = load(wp)
    shas = {"136AU": au_sha, "136AV": av_sha, "136AR": ar_sha, "136W": w_sha}
    prepared, digest = plan(au, ar, w, shas)
    db = args.db.resolve()
    require(db.is_file(), f"production DB missing: {db}")
    with closing(connect_ro(db)) as source:
        source.execute("BEGIN")
        preflight = gate(source, prepared, digest, av, av_sha, shas)
        baseline = fingerprint(source)
        if args.apply:
            require(args.confirm_plan_sha256 == digest,
                    "--apply requires exact SHA-256 printed by preflight")
            backup_path = backup(source, db, args.backup_dir,
                                 baseline, preflight["raw_before"])
        else:
            backup_path = None
    if args.apply:
        try:
            result = apply(db, prepared, digest, av, av_sha, shas, baseline, backup_path)
        except Exception as exc:
            raise RuntimeError(f"STOP: production insert failed or rolled back; "
                               f"backup remains at {backup_path}: {exc}") from exc
    else:
        result = None
    report = {"project": "AxieOS", "version": "0.14", "task": "136AW",
              "mode": "APPLIED" if args.apply else "READ_ONLY_PREFLIGHT",
              "sources": {"136AU": {"filename": ap.name, "sha256": au_sha},
                          "136AV": {"filename": vp.name, "sha256": av_sha},
                          "136AR": {"filename": rp.name, "sha256": ar_sha},
                          "136W": {"filename": wp.name, "sha256": w_sha}},
              "plan": preflight, "result": result,
              "accepted_financial_totals": None,
              "production_database_opened_read_only": not args.apply,
              "production_database_writes": 0 if not args.apply else
                  sum(result["inserted"].values()),
              "network_calls": 0, "checkpoint96": "OPEN",
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AW_Guarded_Raw_" +
            ("Applied_" if args.apply else "Preflight_") +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    print("AXIEOS V0.14 - TASK136AW - GUARDED RAW " +
          ("APPLIED" if args.apply else "READ-ONLY PREFLIGHT"))
    print(f"Plan SHA-256: {digest} | Transactions/transfers: "
          f"{preflight['transaction_rows']}/{preflight['transfer_rows']}")
    if result:
        print(f"Production raw before/after: {result['raw_before']} / "
              f"{result['raw_after']} | Backup: {result['backup_path']}")
    else:
        print(f"Production raw unchanged: {preflight['raw_before']} | No backup created")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("VALIDATION: PASS (guarded raw " +
          ("insert only" if args.apply else "preflight only") + "; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
