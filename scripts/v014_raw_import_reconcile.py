r"""Task136AX: independently reconcile Task136AW raw insert against its backup.

From the AxieOS repository root:
    py -B .\scripts\v014_raw_import_reconcile.py

Reads production, the pre-apply backup, and the SHA-matched Task136AU/AV/AW
reports. Checks exact inserted raw rows, preservation of previous raw rows,
protected tables, integrity and source counts. No writes or network calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from v013_fullrow_materialization_sandbox import PROTECTED_TABLES, table_fingerprint
from v014_post_apply_reconcile import connect_ro, require
from v014_raw_import_clone import TABLES, by_sha, latest, load, plan


def source_gate(aw: dict, av: dict, au: dict, ar: dict, w: dict,
                shas: dict[str, str]) -> dict[str, list[tuple]]:
    require(aw.get("task") == "136AW" and aw.get("mode") == "APPLIED" and
            av.get("task") == "136AV" and au.get("task") == "136AU" and
            all(doc.get("checkpoint96") == "OPEN" and
                doc.get("accepted_financial_totals") is None
                for doc in (aw, av, au, ar, w)),
            "applied report or financial boundary differs")
    require(all(aw["sources"][key]["sha256"] == shas[key]
                for key in ("136AU", "136AV", "136AR", "136W")) and
            aw["production_database_writes"] == sum(
                aw["result"]["inserted"].values()) and
            aw["result"]["integrity_check"] == "ok",
            "Task136AW source digests or applied insert state differ")
    prepared, digest = plan(au, ar, w, shas)
    require(digest == aw["plan"]["plan_sha256"] == av["plan_sha256"] and
            aw["plan"]["task136av_sha256"] == shas["136AV"] and
            aw["result"]["raw_before"] == aw["plan"]["raw_before"] ==
            av["coverage"]["production_raw_before"] and
            all(aw["result"]["inserted"][table] == len(prepared[table]) and
                aw["result"]["raw_after"][table] ==
                    aw["result"]["raw_before"][table] + len(prepared[table])
                for table in TABLES), "Task136AW exact plan or before/after counts differ")
    return prepared


def old_digest(conn, table: str, added: set[str]) -> tuple[str, int]:
    identity = "tx_hash" if table == "ronin_api_transactions_raw" else "transfer_key"
    cursor = conn.execute(f"SELECT * FROM {table} ORDER BY rowid")
    names = [column[0] for column in cursor.description]
    require(identity in names, f"{table}: identity column missing")
    index = names.index(identity)
    digest = hashlib.sha256()
    count = 0
    for row in cursor:
        if str(row[index]).lower() in added:
            continue
        digest.update(repr(row).encode("utf-8"))
        digest.update(b"\n")
        count += 1
    return digest.hexdigest(), count


def compare(prod, backup, prepared: dict[str, list[tuple]], aw: dict) -> dict:
    require(prod.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
            backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
            not prod.execute("PRAGMA foreign_key_check").fetchall() and
            not backup.execute("PRAGMA foreign_key_check").fetchall(),
            "production or backup SQLite integrity differs")
    protected = ("blockchain_transactions",) + PROTECTED_TABLES
    require(all(table_fingerprint(prod, table) == table_fingerprint(backup, table)
                for table in protected),
            "ledger, accounting, classification or gameplay differs from backup")
    for table, fields in TABLES.items():
        before = backup.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        after = prod.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        require(before == aw["result"]["raw_before"][table] and
                after == aw["result"]["raw_after"][table],
                f"{table}: raw counts differ from applied report")
        identity = "tx_hash" if table == "ronin_api_transactions_raw" else "transfer_key"
        added = {str(row[0]).lower() for row in prepared[table]}
        require(len(added) == len(prepared[table]), f"{table}: duplicate proposed key")
        backup_keys = {str(r[0]).lower() for r in backup.execute(
            f"SELECT {identity} FROM {table}")}
        require(not added & backup_keys, f"{table}: proposed row existed before apply")
        current = {str(r[0]).lower(): tuple(r) for r in prod.execute(
            f"SELECT {','.join(fields)} FROM {table}") if str(r[0]).lower() in added}
        expected = {str(r[0]).lower(): tuple(r) for r in prepared[table]}
        require(current == expected and len(current) == len(prepared[table]),
                f"{table}: exact new row value differs")
        remaining_digest, remaining_count = old_digest(prod, table, added)
        require(remaining_count == before and
                remaining_digest == table_fingerprint(backup, table),
                f"{table}: pre-existing raw rows changed")
    tx_hashes = {str(row[0]).lower() for row in prepared["ronin_api_transactions_raw"]}
    transfer_hashes = {str(row[1]).lower() for row in prepared["ronin_token_transfers_raw"]}
    return {"exact_inserted_transactions": len(tx_hashes),
            "exact_inserted_transfers": len(prepared["ronin_token_transfers_raw"]),
            "new_unique_hashes_across_raw_tables": len(tx_hashes | transfer_hashes),
            "new_transfer_hashes_without_new_transaction_row": len(transfer_hashes - tx_hashes),
            "raw_before": aw["result"]["raw_before"],
            "raw_after": aw["result"]["raw_after"],
            "protected_tables_equal_backup": len(protected),
            "preexisting_raw_rows_preserved": True,
            "integrity_check": "ok", "foreign_key_violations": 0}


def markdown(report: dict) -> str:
    c = report["coverage"]
    return "\n".join([
        "# AxieOS V0.14 — Task136AX Post-apply raw-source reconciliation", "",
        f"Exact inserted transaction/transfer rows: "
        f"**{c['exact_inserted_transactions']}/{c['exact_inserted_transfers']}**. "
        f"New unique hashes across those rows: **{c['new_unique_hashes_across_raw_tables']}**.", "",
        f"New transfer hashes without a newly inserted transaction row: "
        f"**{c['new_transfer_hashes_without_new_transaction_row']}**. "
        "These may already have historical transaction evidence and need separate review.", "",
        f"Raw before/after: **{c['raw_before']} / {c['raw_after']}**. "
        f"Protected tables equal backup: **{c['protected_tables_equal_backup']}**.", "",
        "The raw insert does not add ledger classification or accepted economics. "
        "Verified income, expenses, profit and PHP recovery: **UNKNOWN**.", "",
        "Production and backup opened read only | Writes: 0 | Network: 0", "",
        "VALIDATION: PASS (post-apply raw source reconciliation only; Checkpoint 96 OPEN).", ""])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--aw", type=Path)
    parser.add_argument("--aw-dir", type=Path, default=Path("reports/axieos_v014/task136aw"))
    parser.add_argument("--au-dir", type=Path, default=Path("reports/axieos_v014/task136au"))
    parser.add_argument("--av-dir", type=Path, default=Path("reports/axieos_v014/task136av"))
    parser.add_argument("--ar-dir", type=Path, default=Path("reports/axieos_v014/task136ar"))
    parser.add_argument("--w-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136ax"))
    args = parser.parse_args()
    if args.aw is None:
        candidates = []
        for path in args.aw_dir.glob("*.json") if args.aw_dir.is_dir() else []:
            doc, _ = load(path)
            if doc.get("task") == "136AW" and doc.get("mode") == "APPLIED":
                candidates.append((doc.get("created_at_utc", ""), path))
        require(candidates, "no applied Task136AW JSON; pass --aw PATH")
        aw_path = max(candidates)[1]
    else:
        aw_path = args.aw
    aw, aw_sha = load(aw_path)
    paths = {"136AU": by_sha(args.au_dir, aw["sources"]["136AU"]["sha256"], "136AU"),
             "136AV": by_sha(args.av_dir, aw["sources"]["136AV"]["sha256"], "136AV"),
             "136AR": by_sha(args.ar_dir, aw["sources"]["136AR"]["sha256"], "136AR"),
             "136W": by_sha(args.w_dir, aw["sources"]["136W"]["sha256"], "136W")}
    docs, shas = {}, {"136AW": aw_sha}
    for key, path in paths.items():
        docs[key], shas[key] = load(path)
    prepared = source_gate(aw, docs["136AV"], docs["136AU"], docs["136AR"],
                           docs["136W"], shas)
    backup_path = Path(aw["result"]["backup_path"])
    require(backup_path.is_file() and backup_path.resolve() != args.db.resolve(),
            "persistent pre-apply backup missing or points at production")
    with closing(connect_ro(args.db)) as prod, closing(connect_ro(backup_path)) as backup:
        prod.execute("BEGIN")
        backup.execute("BEGIN")
        coverage = compare(prod, backup, prepared, aw)
    report = {"project": "AxieOS", "version": "0.14", "task": "136AX",
              "source_applied_sha256": aw_sha,
              "sources": {"136AW": {"filename": aw_path.name, "sha256": aw_sha},
                          **{k: {"filename": paths[k].name, "sha256": shas[k]}
                             for k in sorted(paths)}},
              "backup_path": str(backup_path), "coverage": coverage,
              "accepted_financial_totals": None,
              "production_and_backup_opened_read_only": True,
              "database_writes": 0, "network_calls": 0,
              "checkpoint96": "OPEN",
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AX_Raw_Post_Apply_Reconciliation_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136AX - RAW POST-APPLY RECONCILIATION")
    print(f"Exact inserted transaction/transfer rows: "
          f"{c['exact_inserted_transactions']}/{c['exact_inserted_transfers']} | "
          f"New unique hashes: {c['new_unique_hashes_across_raw_tables']}")
    print(f"Transfer hashes without new transaction row: "
          f"{c['new_transfer_hashes_without_new_transaction_row']}")
    print(f"Raw before/after: {c['raw_before']} / {c['raw_after']} | "
          f"Protected tables equal backup: {c['protected_tables_equal_backup']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Production and backup read only | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (post-apply raw source reconciliation only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
