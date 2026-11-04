r"""Task136AZ: read-only preflight for Task136AY recent ledger rows.

Run from the AxieOS repository root:
    py -B .\scripts\v014_recent_ledger_preflight.py

Reads production SQLite in mode=ro/query_only. Reconstructs the Task136AY
proposal from its SHA-matched evidence and compares every proposed row with
the saved clone plan. Does not create a backup or write to production.
"""

from __future__ import annotations

import argparse
import json
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from v013_fullrow_materialization_sandbox import PROTECTED_TABLES, table_fingerprint
from v014_cache_cohort_materialization_sandbox import LEDGER_FIELDS
from v014_post_apply_reconcile import connect_ro, require
from v014_raw_import_clone import by_sha, latest, load
from v014_recent_ledger_clone import plan, validate_sources


def check(conn, ay: dict, ay_sha: str, sources: dict[str, dict],
          shas: dict[str, str]) -> dict:
    require(ay.get("task") == "136AY" and ay.get("checkpoint96") == "OPEN" and
            ay.get("accepted_financial_totals") is None and
            ay.get("production_database_writes") == 0 and
            ay.get("network_calls") == 0 and ay.get("clone_deleted") is True,
            "Task136AY identity or read-only boundary differs")
    require(all(ay.get("sources", {}).get(task, {}).get("sha256") == shas[task]
                for task in ("136AX", "136AU", "136AW", "136AF")),
            "Task136AY source digests differ")
    validate_sources(sources["136AX"], sources["136AU"],
                     sources["136AW"], sources["136AF"], shas)
    reported = ay.get("guarded_ledger_rows")
    cov, sandbox = ay.get("coverage", {}), ay.get("sandbox", {})
    require(isinstance(reported, list) and reported and
            len(reported) == cov.get("guarded_rows") and
            cov.get("quarantined_rows") == 0 and cov.get("quarantined_hashes") == 0 and
            ay.get("quarantined") == [] and
            sandbox.get("clone_rows_first_pass") == len(reported) and
            sandbox.get("clone_rows_second_pass") == 0 and
            sandbox.get("clone_integrity") == "ok" and
            sandbox.get("clone_foreign_key_errors") == 0 and
            sandbox.get("production_ledger_before_after") ==
                [sandbox.get("production_ledger_before_after", [None])[0]] * 2,
            "Task136AY clone or quarantine summary differs")
    require(all(isinstance(row, dict) and set(row) == set(LEDGER_FIELDS) and
                row["txn_fee_ron"] is None and row["status"] in (None, "Success")
                for row in reported), "Task136AY proposed row schema or unknown gas differs")
    selected, quarantine, coverage = plan(
        conn, sources["136AX"], sources["136AU"], sources["136AF"])
    require(coverage == cov and quarantine == [] and
            [dict(zip(LEDGER_FIELDS, row)) for row in selected] == reported,
            "live source differs from Task136AY guarded plan")
    require(len({row[-1] for row in selected}) == len(selected) and
            len({row[0] for row in selected}) == cov["guarded_hashes"],
            "guarded ledger row or hash identity duplicate")
    info = {r[1]: r for r in conn.execute("PRAGMA table_info(blockchain_transactions)")}
    require(set(LEDGER_FIELDS) <= set(info) and
            info["txn_fee_ron"][3] == 0 and info["status"][3] == 0,
            "production ledger schema cannot retain unknown fee/status")
    before = conn.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
    require(before == sandbox["production_ledger_before_after"][0] and
            before == sources["136AF"]["coverage"]["ledger_after"],
            "production ledger count changed since Task136AY")
    require(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
            not conn.execute("PRAGMA foreign_key_check").fetchall(),
            "production SQLite integrity or foreign key check failed")
    watched = ("blockchain_transactions", "ronin_api_transactions_raw",
               "ronin_token_transfers_raw", *PROTECTED_TABLES)
    fingerprints = {table: table_fingerprint(conn, table) for table in watched}
    return {"task136ay_sha256": ay_sha, "guarded_rows": len(selected),
            "guarded_hashes": cov["guarded_hashes"], "ledger_before": before,
            "ledger_if_applied": before + len(selected),
            "transaction_only_hashes_omitted": cov["new_transaction_only_hashes"],
            "unknown_fee_rows": sum(row[10] is None for row in selected),
            "null_status_rows": sum(row[11] is None for row in selected),
            "watched_table_fingerprints": fingerprints,
            "integrity_check": "ok", "foreign_key_violations": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path,
                        default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--ay", type=Path)
    parser.add_argument("--ay-dir", type=Path,
                        default=Path("reports/axieos_v014/task136ay"))
    for task in ("136AX", "136AU", "136AW", "136AF"):
        parser.add_argument(f"--{task.lower()}-dir", type=Path,
                            default=Path(f"reports/axieos_v014/task{task.lower()}"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("reports/axieos_v014/task136az"))
    args = parser.parse_args()
    ay_path = args.ay or latest(args.ay_dir, "136AY")
    ay, ay_sha = load(ay_path)
    paths = {task: by_sha(getattr(args, f"{task.lower()}_dir"),
                          ay["sources"][task]["sha256"], task)
             for task in ("136AX", "136AU", "136AW", "136AF")}
    loaded = {task: load(path) for task, path in paths.items()}
    sources = {task: doc for task, (doc, digest) in loaded.items()}
    shas = {task: digest for task, (doc, digest) in loaded.items()}
    with closing(connect_ro(args.db)) as conn:
        conn.execute("BEGIN")
        result = check(conn, ay, ay_sha, sources, shas)
        require(conn.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
                == result["ledger_before"] and
                all(table_fingerprint(conn, name) == digest
                    for name, digest in result["watched_table_fingerprints"].items()),
                "watched production tables changed during preflight")
    report = {"project": "AxieOS", "version": "0.14", "task": "136AZ",
              "mode": "READ_ONLY_PREFLIGHT",
              "sources": {"136AY": {"filename": ay_path.name, "sha256": ay_sha},
                          **{task: {"filename": paths[task].name, "sha256": shas[task]}
                             for task in paths}},
              "plan": result, "accepted_financial_totals": None,
              "production_database_opened_read_only": True,
              "production_database_writes": 0, "backup_created": False,
              "network_calls": 0, "checkpoint96": "OPEN",
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AZ_Recent_Ledger_Preflight_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
            "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text("\n".join([
        "# AxieOS V0.14 — Task136AZ Recent ledger read-only preflight", "",
        f"Task136AY SHA-256: `{ay_sha}`.", "",
        f"Guarded rows/hashes: **{result['guarded_rows']}/{result['guarded_hashes']}**. "
        f"Ledger before/if applied: **{result['ledger_before']}/"
        f"{result['ledger_if_applied']}**.", "",
        f"Transaction-only hashes omitted: **{result['transaction_only_hashes_omitted']}**. "
        f"NULL gas rows: **{result['unknown_fee_rows']}**; NULL status rows: "
        f"**{result['null_status_rows']}**.", "",
        "No backup created, no production rows inserted, and no accounting or "
        "economic values accepted. Verified totals: **UNKNOWN**. Checkpoint 96: **OPEN**.", "",
        "Database opened read only | Writes: 0 | Network calls: 0", ""]),
        encoding="utf-8")
    print("AXIEOS V0.14 - TASK136AZ - RECENT LEDGER READ-ONLY PREFLIGHT")
    print(f"Plan SHA-256: {ay_sha} | Guarded rows/hashes: "
          f"{result['guarded_rows']}/{result['guarded_hashes']}")
    print(f"Production ledger unchanged: {result['ledger_before']} | No backup created")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: production read only | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (recent ledger preflight only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
