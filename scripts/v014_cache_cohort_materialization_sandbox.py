r"""Task136AC: rehearse only Task136W cached transfer rows in a disposable DB.

Run at the AxieOS repository root:
    py -B .\scripts\v014_cache_cohort_materialization_sandbox.py

Reads production SQLite mode=ro/query_only. Writes proposed full ledger rows
only to a temporary clone, then deletes the clone. No accounting/classification,
production database writes, or network access. Requires the existing
v013_fullrow_materialization_sandbox.py helper beside this script.
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

from v013_fullrow_materialization_sandbox import (
    PROTECTED_TABLES, get_transfers, proposed_rows, readonly_connect,
    source_hash, table_fingerprint,
)


LEDGER_FIELDS = ("txhash", "blockno", "unixtimestamp", "datetime", "from_address",
                 "to_address", "method", "token_collectibles", "value_in",
                 "value_out", "txn_fee_ron", "status", "source_row_hash")
INSERT = ("INSERT OR IGNORE INTO blockchain_transactions (" + ",".join(LEDGER_FIELDS)
          + ") VALUES (" + ",".join("?" for _ in LEDGER_FIELDS) + ")")


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError("STOP: " + message)


def find_w(directory: Path) -> Path:
    matches = []
    for path in directory.glob("AxieOS_V014_Task136W_Post_Accounting_Cache_Gap_*.json"):
        with path.open(encoding="utf-8") as stream:
            report = json.load(stream)
        if report.get("report_schema_version") == "1.1":
            matches.append((report.get("created_at_utc", ""), path))
    require(bool(matches), f"no Task136W schema 1.1 JSON in {directory}; pass --cache PATH")
    return max(matches)[1]


def plan(conn: sqlite3.Connection, cache: dict) -> tuple[list[tuple], dict]:
    require(cache.get("task") == "136W" and cache.get("report_schema_version") == "1.1" and
            cache.get("accepted_financial_totals") is None and cache.get("checkpoint96") == "OPEN",
            "wrong or changed Task136W source")
    candidates = cache["candidate_rows"]
    require(len(candidates) == cache["coverage"]["candidate_hashes"], "cache count mismatch")
    hashes = {str(r["txhash"]).lower() for r in candidates}
    require(len(hashes) == len(candidates), "duplicate cache hash")
    require(all(not r["stored_accounting_row_present"] and
                r["stored_ledger_row_count"] == 0 for r in candidates),
            "source cache contains previously stored hash")
    expected_keys = [str(t["transfer_key"]) for r in candidates
                     for t in r["raw_transfer_rows"]]
    require(all(expected_keys) and len(expected_keys) == len(set(expected_keys)),
            "duplicate or missing source transfer key")
    expected_source_hashes = {source_hash(k) for k in expected_keys}
    require(len(expected_source_hashes) == len(expected_keys), "source hash collision")
    ledger_hashes = {str(r[0]).lower() for r in conn.execute(
        "SELECT DISTINCT txhash FROM blockchain_transactions WHERE txhash IS NOT NULL")}
    accounting_hashes = {str(r[0]).lower() for r in conn.execute(
        "SELECT DISTINCT txhash FROM blockchain_accounting_records WHERE txhash IS NOT NULL")}
    require(not hashes & (ledger_hashes | accounting_hashes),
            "cached cohort is no longer absent from ledger/accounting; refresh Task136W")
    live_selected = [row for row in get_transfers(conn)
                     if str(row[1] or "").lower() in hashes]
    live_keys = [str(row[0]) for row in live_selected]
    require(len(live_keys) == len(set(live_keys)) and set(live_keys) == set(expected_keys),
            "raw source transfer keys changed since Task136W; refresh source")
    live_by_key = {str(row[0]): row for row in live_selected}
    for candidate in candidates:
        for t in candidate["raw_transfer_rows"]:
            live = live_by_key[str(t["transfer_key"])]
            expected = (str(candidate["txhash"]).lower(), str(t["log_index"]),
                        str(t["timestamp"]), str(t["block_number"]),
                        str(t["from_address"]).lower(), str(t["to_address"]).lower(),
                        t["token_type"], t["token_symbol"],
                        str(t["token_address"] or "").lower(), str(t["token_id"]),
                        str(t["amount_raw"]), str(t["decimals"]))
            actual = (str(live[1]).lower(), str(live[2]), str(live[3]), str(live[4]),
                      str(live[5]).lower(), str(live[6]).lower(), live[7], live[8],
                      str(live[10] or "").lower(), str(live[11]), str(live[12]), str(live[13]))
            require(expected == actual,
                    f"raw source transfer {t['transfer_key']} changed since Task136W")
    all_prepared, _, _ = proposed_rows(conn)
    selected = [r for r in all_prepared if str(r[0]).lower() in hashes]
    require(len(selected) == len(expected_keys) and
            {r[-1] for r in selected} == expected_source_hashes,
            "legacy PRIMARY wallet materializer does not cover all cached transfers")
    existing_source_hashes = {r[0] for r in conn.execute(
        "SELECT source_row_hash FROM blockchain_transactions WHERE source_row_hash IS NOT NULL")}
    require(not existing_source_hashes & expected_source_hashes,
            "proposed row source hash is already present; refresh Task136W")
    selected_hashes = {str(r[0]).lower() for r in selected}
    require(selected_hashes == {str(r["txhash"]).lower() for r in candidates
                                if r["raw_transfer_rows"]},
            "cached transfer hash coverage differs")
    txn_only = hashes - selected_hashes
    require(len(txn_only) == sum(not r["raw_transfer_rows"] for r in candidates),
            "cached transaction-only cohort differs")
    return selected, {"cache_hashes": len(hashes),
                      "selected_transfer_hashes": len(selected_hashes),
                      "selected_full_ledger_rows": len(selected),
                      "transaction_only_hashes": len(txn_only),
                      "all_raw_eligible_transfer_rows": len(all_prepared),
                      "outside_cohort_eligible_transfer_rows": len(all_prepared) - len(selected)}


def rehearse(prod: sqlite3.Connection, selected: list[tuple]) -> dict:
    before = prod.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
    original_ledger_digest = table_fingerprint(prod, "blockchain_transactions")
    protected = {name: table_fingerprint(prod, name) for name in PROTECTED_TABLES}
    with TemporaryDirectory(prefix="axieos_v014_cache_cohort_") as temp:
        clone = sqlite3.connect(Path(temp) / "cohort_only.db")
        try:
            prod.backup(clone)
            clone.execute("PRAGMA foreign_keys=ON")
            require(clone.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0] == before,
                    "clone ledger count differs")
            initial = clone.total_changes
            clone.executemany(INSERT, selected)
            added = clone.total_changes - initial
            clone.commit()
            initial = clone.total_changes
            clone.executemany(INSERT, selected)
            repeated = clone.total_changes - initial
            clone.commit()
            after = clone.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
            require(added == len(selected) and repeated == 0 and after == before + len(selected),
                    "clone insertion or idempotence differs")
            require(all(table_fingerprint(clone, name) == digest for name, digest in protected.items()),
                    "protected clone table changed")
            clone.execute("CREATE TEMP TABLE _new_source (h TEXT PRIMARY KEY)")
            clone.executemany("INSERT INTO _new_source VALUES (?)", ((r[-1],) for r in selected))
            existing_digest = hashlib.sha256()
            preserved = 0
            for row in clone.execute(
                    "SELECT * FROM blockchain_transactions WHERE source_row_hash IS NULL OR source_row_hash NOT IN "
                    "(SELECT h FROM _new_source) ORDER BY rowid"):
                existing_digest.update(repr(row).encode("utf-8"))
                existing_digest.update(b"\n")
                preserved += 1
            require(preserved == before and existing_digest.hexdigest() == original_ledger_digest,
                    "original clone ledger rows changed")
            integrity = clone.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_errors = clone.execute("PRAGMA foreign_key_check").fetchall()
            require(integrity == "ok" and not foreign_errors,
                    "clone integrity or foreign key check failed")
        finally:
            clone.close()
    require(prod.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0] == before and
            table_fingerprint(prod, "blockchain_transactions") == original_ledger_digest and
            all(table_fingerprint(prod, name) == digest for name, digest in protected.items()),
            "production ledger or protected tables changed")
    return {"production_ledger_before_after": [before, before],
            "clone_rows_first_pass": added, "clone_rows_second_pass": repeated,
            "clone_ledger_rows_after": after, "original_clone_rows_preserved": preserved,
            "protected_clone_tables_unchanged": len(PROTECTED_TABLES),
            "clone_integrity": integrity, "clone_foreign_key_errors": len(foreign_errors)}


def markdown(report: dict) -> str:
    p, s = report["plan"], report["sandbox"]
    lines = ["# AxieOS V0.14 — Task136AC Cohort-only materialization sandbox", "",
             f"Task136W cached hashes: **{p['cache_hashes']}**. "
             f"Transfer-backed hashes: **{p['selected_transfer_hashes']}**; "
             f"transaction-only hashes: **{p['transaction_only_hashes']}**.", "",
             f"Prepared full ledger rows for this cohort: **{p['selected_full_ledger_rows']}**. "
             f"Other raw eligible transfer rows excluded: **{p['outside_cohort_eligible_transfer_rows']}**.", "",
             f"Temporary clone inserted **{s['clone_rows_first_pass']}** rows on the first pass "
             f"and **{s['clone_rows_second_pass']}** on the second. "
             f"Original rows preserved: **{s['original_clone_rows_preserved']}**. "
             f"Integrity: **{s['clone_integrity']}**; foreign key errors: "
             f"**{s['clone_foreign_key_errors']}**.", "",
             "The companion JSON includes every proposed full ledger row and its source hash "
             "for review. This does not classify the 707 hashes or resolve the 141 transaction-only cases. "
             "Marketplace economics, costs, profit, gas payer and PHP recovery remain UNKNOWN.", "",
             "Production DB opened: read only | Production writes: 0 | Temporary clone: deleted | Network: 0", "",
             "VALIDATION: PASS (scoped sandbox rehearsal only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136ac"))
    args = parser.parse_args()
    cache_path = args.cache or find_w(args.cache_dir)
    require(cache_path.is_file(), f"cache JSON missing: {cache_path}")
    raw = cache_path.read_bytes()
    cache = json.loads(raw.decode("utf-8-sig"))
    db = args.db.resolve()
    require(db.is_file(), f"database missing: {db}")
    with closing(readonly_connect(db)) as prod:
        prod.execute("PRAGMA query_only=ON")
        selected, counts = plan(prod, cache)
        sandbox = rehearse(prod, selected)
    report = {"project": "AxieOS", "version": "0.14", "task": "136AC",
              "source_task136w": {"filename": cache_path.name,
                                  "sha256": hashlib.sha256(raw).hexdigest()},
              "source_database": str(args.db), "plan": counts, "sandbox": sandbox,
              "proposed_ledger_rows": [dict(zip(LEDGER_FIELDS, row)) for row in selected],
              "accepted_financial_totals": None, "production_database_writes": 0,
              "temporary_clone_deleted": True, "network_calls": 0,
              "checkpoint96": "OPEN", "created_at_utc": datetime.now(timezone.utc).isoformat()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AC_Cohort_Materialization_Sandbox_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
            + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with mp.open("x", encoding="utf-8") as stream:
        stream.write(markdown(report))
    print("AXIEOS V0.14 - TASK136AC - COHORT-ONLY MATERIALIZATION SANDBOX")
    print(f"Cached hashes: {counts['cache_hashes']} | Transfer-backed: "
          f"{counts['selected_transfer_hashes']} | Transaction-only: "
          f"{counts['transaction_only_hashes']}")
    print(f"Proposed full rows: {counts['selected_full_ledger_rows']} | "
          f"Clone first/second: {sandbox['clone_rows_first_pass']}/{sandbox['clone_rows_second_pass']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Production DB opened: read only | Production writes: 0 | Temporary clone: deleted | Network: 0")
    print("VALIDATION: PASS (scoped sandbox rehearsal only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
