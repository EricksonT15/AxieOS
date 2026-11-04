r"""Task136BJ: disposable clone rehearsal for 22 transaction detail rows.

From the AxieOS repository root:
    py -B .\scripts\v014_detail_raw_clone.py

Reproduces the SHA-linked Task136BI plan from saved evidence, opens production
read only, and inserts proposed rows only into a temporary SQLite clone.
No ledger, accounting or economics writer and no network calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from v013_fullrow_materialization_sandbox import PROTECTED_TABLES, table_fingerprint
from v014_post_apply_reconcile import connect_ro, require
from v014_raw_import_clone import TX_FIELDS, by_sha, latest, load
from v014_transaction_detail_crosswalk import build as reproduce


TABLE = "ronin_api_transactions_raw"
WATCH = ("blockchain_transactions", "ronin_token_transfers_raw", *PROTECTED_TABLES)
INSERT = ("INSERT OR IGNORE INTO " + TABLE + " (" + ",".join(TX_FIELDS) +
          ") VALUES (" + ",".join("?" for _ in TX_FIELDS) + ")")


def plan(bi: dict, docs: dict[str, dict], shas: dict[str, str]) -> list[tuple]:
    require(bi.get("task") == "136BI" and bi.get("checkpoint96") == "OPEN" and
            bi.get("accepted_financial_totals") is None and
            bi.get("database_opened") is False and bi.get("database_writes") == 0 and
            bi.get("network_calls") == 0 and
            all(bi.get("sources", {}).get(t, {}).get("sha256") == shas[t]
                for t in docs),
            "Task136BI identity, source chain or financial boundary differs")
    rebuilt = reproduce(docs["136BH"], docs["136BF"], docs["136BC"],
                        docs["136AY"], docs["136AU"], shas)
    require(rebuilt["coverage"] == bi["coverage"] and
            rebuilt["candidate_raw_transaction_rows"] ==
                bi["candidate_raw_transaction_rows"] and
            rebuilt["evidence_rows"] == bi["evidence_rows"],
            "Task136BI raw transaction plan differs from saved explorer bodies")
    rows = bi["candidate_raw_transaction_rows"]
    require(len(rows) == bi["coverage"]["candidate_raw_transactions"] ==
                bi["coverage"]["lookup_hashes"] and
            len({r["tx_hash"] for r in rows}) == len(rows) and
            all(set(row) == set(TX_FIELDS) and row["status"] == "ok" and
                row["fee_raw"] is not None and row["method"] is not None
                for row in rows),
            "transaction identity, status, method or raw fee coverage differs")
    return [tuple(row[field] for field in TX_FIELDS)
            for row in sorted(rows, key=lambda r: r["tx_hash"])]


def old_raw_digest(conn, newly_inserted: set[str]) -> tuple[str, int]:
    sha = hashlib.sha256()
    count = 0
    cursor = conn.execute("SELECT * FROM " + TABLE + " ORDER BY rowid")
    index = [field[0] for field in cursor.description].index("tx_hash")
    for row in cursor:
        if str(row[index]).lower() in newly_inserted:
            continue
        sha.update(repr(row).encode("utf-8"))
        sha.update(b"\n")
        count += 1
    return sha.hexdigest(), count


def rehearse(prod: sqlite3.Connection, rows: list[tuple], bb: dict,
             ay: dict) -> dict:
    before = prod.execute("SELECT COUNT(*) FROM " + TABLE).fetchone()[0]
    ledger_before = prod.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
    require(ledger_before == bb["coverage"]["ledger_after"] and
            bb["coverage"]["inserted_hashes_exact"] ==
                ay["coverage"]["guarded_hashes"] and
            prod.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
            not prod.execute("PRAGMA foreign_key_check").fetchall(),
            "production ledger or SQLite integrity differs from Task136BB")
    columns = {item[1] for item in prod.execute(f"PRAGMA table_info({TABLE})")}
    require(set(TX_FIELDS) <= columns, "production raw transaction schema changed")
    hashes = {row[0] for row in rows}
    prior = {str(r[0]).lower() for r in prod.execute(f"SELECT tx_hash FROM {TABLE}")}
    require(not prior & hashes, "proposed transaction detail already in production raw")
    cohort = {str(r["txhash"]).lower() for r in ay["guarded_ledger_rows"]}
    require(hashes.issubset(cohort), "raw transaction proposal outside guarded ledger")
    account = {str(r[0]).lower() for r in prod.execute(
        "SELECT txhash FROM blockchain_accounting_records WHERE txhash IS NOT NULL")}
    classified = {str(r[0]).lower() for r in prod.execute(
        "SELECT txhash FROM blockchain_transaction_classifications WHERE txhash IS NOT NULL")}
    require(not hashes & (account | classified),
            "new detail cohort already has accounting or classification")
    raw_digest = table_fingerprint(prod, TABLE)
    protected = {table: table_fingerprint(prod, table) for table in WATCH}
    with TemporaryDirectory(prefix="axieos_v014_detail_raw_clone_") as temp:
        with closing(sqlite3.connect(Path(temp) / "detail.db")) as clone:
            prod.backup(clone)
            clone.execute("PRAGMA foreign_keys=ON")
            require(table_fingerprint(clone, TABLE) == raw_digest and
                    all(table_fingerprint(clone, table) == digest
                        for table, digest in protected.items()),
                    "temporary clone differs from production")
            initial = clone.total_changes
            clone.executemany(INSERT, rows)
            first = clone.total_changes - initial
            clone.commit()
            initial = clone.total_changes
            clone.executemany(INSERT, rows)
            second = clone.total_changes - initial
            clone.commit()
            require(first == len(rows) and second == 0 and
                    clone.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0] ==
                        before + len(rows),
                    "clone insert count or idempotence differs")
            for row in rows:
                stored = clone.execute("SELECT " + ",".join(TX_FIELDS) +
                    f" FROM {TABLE} WHERE tx_hash=?", (row[0],)).fetchone()
                require(stored == row, f"clone raw transaction differs: {row[0]}")
            digest, preserved = old_raw_digest(clone, hashes)
            require(preserved == before and digest == raw_digest and
                    all(table_fingerprint(clone, table) == expected
                        for table, expected in protected.items()) and
                    clone.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                    not clone.execute("PRAGMA foreign_key_check").fetchall(),
                    "clone prior raw, watched tables or SQLite integrity differ")
    require(table_fingerprint(prod, TABLE) == raw_digest and
            all(table_fingerprint(prod, table) == expected
                for table, expected in protected.items()),
            "production changed during clone rehearsal")
    return {"production_raw_transactions": before,
            "production_ledger_rows": ledger_before,
            "clone_first_pass": first, "clone_second_pass": second,
            "clone_raw_transactions_after": before + first,
            "prior_raw_rows_preserved": preserved,
            "watched_clone_tables_unchanged": len(WATCH),
            "clone_integrity": "ok", "clone_foreign_key_violations": 0,
            "clone_deleted": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path,
                        default=Path("data/blockchain/database/axieos.db"))
    for suffix in ("bi", "bh", "bf", "bc", "ay", "au", "bb"):
        parser.add_argument(f"--{suffix}-dir", type=Path,
                            default=Path(f"reports/axieos_v014/task136{suffix}"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("reports/axieos_v014/task136bj"))
    args = parser.parse_args()
    paths = {"136BI": latest(args.bi_dir, "136BI")}
    bi, bi_sha = load(paths["136BI"])
    for task in ("136BH", "136BF", "136BC", "136AY", "136AU"):
        paths[task] = by_sha(getattr(args, task[3:].lower() + "_dir"),
                              bi["sources"][task]["sha256"], task)
    bf_source, _ = load(paths["136BF"])
    paths["136BB"] = by_sha(args.bb_dir,
                             bf_source["sources"]["136BB"]["sha256"], "136BB")
    docs, shas = {}, {}
    for task, path in paths.items():
        docs[task], shas[task] = load(path)
    rows = plan(docs["136BI"], {k: docs[k] for k in
        ("136BH", "136BF", "136BC", "136AY", "136AU")}, shas)
    with closing(connect_ro(args.db)) as prod:
        prod.execute("BEGIN")
        result = rehearse(prod, rows, docs["136BB"], docs["136AY"])
    report = {"project": "AxieOS", "version": "0.14", "task": "136BJ",
              "sources": {task: {"filename": path.name, "sha256": shas[task]}
                          for task, path in paths.items()},
              "plan_sha256": hashlib.sha256(json.dumps(rows,
                  separators=(",", ":")).encode("utf-8")).hexdigest(),
              "coverage": {"proposed_raw_transactions": len(rows),
                           **result},
              "proposed_raw_transaction_rows": [dict(zip(TX_FIELDS, row))
                                                 for row in rows],
              "accepted_financial_totals": None,
              "production_database_opened_read_only": True,
              "production_database_writes": 0,
              "network_calls": 0, "checkpoint96": "OPEN",
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136BJ_Detail_Raw_Clone_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
            "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    c = report["coverage"]
    mp.write_text("\n".join([
        "# AxieOS V0.14 — Task136BJ Transaction detail raw clone", "",
        f"Proposed raw transactions: **{c['proposed_raw_transactions']}**. "
        f"Clone first/second inserts: **{c['clone_first_pass']}/"
        f"{c['clone_second_pass']}**. Production raw rows: "
        f"**{c['production_raw_transactions']}**.", "",
        "All other tables in the disposable clone are preserved. "
        "Raw fees are source evidence only; ledger fee and financial totals "
        "remain unverified.", "",
        "Verified financial totals: **UNKNOWN**. Checkpoint 96: **OPEN**.", "",
        "Production opened read only | Writes: 0 | Clone deleted | Network: 0", ""]),
        encoding="utf-8")
    print("AXIEOS V0.14 - TASK136BJ - DETAIL RAW CLONE")
    print(f"Proposed transactions: {c['proposed_raw_transactions']} | "
          f"Clone first/second: {c['clone_first_pass']}/{c['clone_second_pass']}")
    print(f"Production raw transactions unchanged: {c['production_raw_transactions']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Production read only | Writes: 0 | Clone: deleted | Network: 0")
    print("VALIDATION: PASS (raw transaction clone only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
