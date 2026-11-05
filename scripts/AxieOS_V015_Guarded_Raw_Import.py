r"""Guarded V0.15 import for the three reconciled raw transaction details.

Save beside AxieOS_V015_Source_Reconciliation.py in scripts/. From repo root:
    py -B .\scripts\AxieOS_V015_Guarded_Raw_Import.py --apply

Rechecks the pinned source, the reconciliation report, the live database and
three explorer details. A disposable clone must pass before any production
write. Creates a verified persistent backup outside the repo, then inserts
only missing ronin_api_transactions_raw rows in one transaction. Does not
change ledger, Axie ownership, classifications, accounting, or finance totals.
Without --apply it performs the same checks and writes only a preflight report.
"""

import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from urllib.request import build_opener

import AxieOS_V015_Source_Reconciliation as prior


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "reports/axieos_v015/source_catchup"
SOURCE_NAME = "AxieOS_V015_Source_Catchup_20261105T030132_927019Z.json"
RECON_NAME = "AxieOS_V015_Source_Reconciliation_20261105T033632_937141Z.json"
BACKUP_DIR = Path.home() / "AxieOSBackups"
TABLE = "ronin_api_transactions_raw"
INSERT = ("INSERT INTO " + TABLE + " (" + ",".join(prior.TX_FIELDS) + ") VALUES (" +
          ",".join("?" for _ in prior.TX_FIELDS) + ")")


def load_reconciliation(path, source_digest):
    prior.require(path.is_file(), f"source reconciliation report missing: {path}")
    content = path.read_bytes()
    report = json.loads(content.decode("utf-8-sig"))
    raw = report["raw_transaction_rehearsal"]
    review = report["roster_review"]
    prior.require(report.get("version") == "0.15" and report.get("task") == "SOURCE_RECONCILIATION"
                  and report["source"]["sha256"] == source_digest
                  and report["source"]["block"] == "0x3c43185"
                  and report["production_database"] == "READ_ONLY" and report["database_writes"] == 0
                  and report["verified_financial_totals"] == "UNKNOWN"
                  and report["checkpoint96"] == "OPEN" and report["unified_finance"] == "HOLD",
                  "reconciliation source or scope differs")
    prior.require(len(review) == 32 and len({r["axie_id"] for r in review}) == 32 and
                  sum(r["lane"] == "CHAIN_ONLY" for r in review) == 29 and
                  sum(r["lane"] == "SAVED_ONLY" for r in review) == 3 and
                  all(r["production_update_approved"] is False for r in review),
                  "roster review differs")
    rows = raw["candidate_raw_transaction_rows"]
    prior.require(raw["missing_rehearsed"] == raw["clone_first_pass"] == len(rows) == 3 and
                  raw["already_present_exact"] == raw["clone_second_pass"] == raw["production_writes"] == 0 and
                  raw["clone_deleted"] is True and report["network_calls"] == 3 and
                  len({r["tx_hash"] for r in rows}) == 3 and
                  all(set(r) == set(prior.TX_FIELDS) for r in rows),
                  "three-row raw clone proof differs")
    calculated = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":"))
                                .encode("utf-8")).hexdigest()
    prior.require(calculated == raw["plan_sha256"], "candidate plan SHA-256 differs")
    return report, hashlib.sha256(content).hexdigest()


def fingerprint(conn):
    return {table: prior.snapshot_table(conn, table) for table in prior.WATCHED}


def checked_plan(db, source, report):
    opener = build_opener(prior.NoRedirect())
    calls = 0

    def fetch(txhash):
        nonlocal calls
        calls += 1
        return prior.explorer_detail(opener, txhash)

    with closing(prior.open_ro(db)) as conn:
        conn.execute("BEGIN")
        prior.require(prior.roster_review(conn, source) == report["roster_review"],
                      "saved Axie roster or metadata changed since reconciliation")
        rehearsal = prior.rehearse(conn, source, fetch)
        baseline = fingerprint(conn)
    expected = report["raw_transaction_rehearsal"]["candidate_raw_transaction_rows"]
    rows = [tuple(row[field] for field in prior.TX_FIELDS) for row in expected]
    now = rehearsal["candidate_raw_transaction_rows"]
    if rehearsal["missing_rehearsed"] == 0 and rehearsal["already_present_exact"] == 3:
        state = "ALREADY_PRESENT_EXACT"
    else:
        prior.require(rehearsal["missing_rehearsed"] == 3 and rehearsal["already_present_exact"] == 0
                      and now == expected and
                      baseline[TABLE]["rows"] == report["raw_transaction_rehearsal"]["production_raw_rows"]
                      and baseline["blockchain_transactions"]["rows"] ==
                          report["raw_transaction_rehearsal"]["production_ledger_rows"],
                      "current raw rows, ledger, or re-fetched detail differs from clone plan")
        state = "READY"
    return rows, baseline, state, calls


def make_backup(db, directory, baseline):
    directory = directory.expanduser().resolve()
    prior.require(not directory.is_relative_to(ROOT.resolve()) and directory != db.parent and
                  not db.is_relative_to(directory), "backup directory must be outside repository and DB folder")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ("axieos_before_v015_raw_" +
                        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
                        "_" + uuid4().hex[:6] + ".db")
    prior.require(not path.exists(), "backup target already exists")
    with closing(prior.open_ro(db)) as source, closing(sqlite3.connect(path)) as backup:
        source.backup(backup)
        prior.require(backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                      not backup.execute("PRAGMA foreign_key_check").fetchall() and
                      fingerprint(backup) == baseline,
                      "backup differs from preflight; production unchanged")
    return path


def apply(db, rows, baseline, backup):
    prior.require(backup.is_file(), "verified backup missing")
    hashes = {row[0] for row in rows}
    with closing(sqlite3.connect(db, timeout=15)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("BEGIN IMMEDIATE")
        try:
            prior.require(fingerprint(conn) == baseline, "production changed after backup")
            prior.require(not conn.execute("SELECT 1 FROM " + TABLE + " WHERE lower(tx_hash) IN (?,?,?) LIMIT 1",
                                           tuple(sorted(hashes))).fetchone(), "candidate now present")
            before = conn.total_changes
            conn.executemany(INSERT, rows)
            prior.require(conn.total_changes - before == 3 and
                          conn.execute("SELECT count(*) FROM " + TABLE).fetchone()[0] ==
                              baseline[TABLE]["rows"] + 3,
                          "unexpected production insert count")
            for row in rows:
                stored = conn.execute("SELECT " + ",".join(prior.TX_FIELDS) + " FROM " + TABLE +
                                      " WHERE tx_hash=?", (row[0],)).fetchone()
                prior.require(stored == row, f"stored raw row differs: {row[0]}")
            prior.require(prior.snapshot_table(conn, TABLE, hashes) == baseline[TABLE] and
                          all(prior.snapshot_table(conn, t) == baseline[t] for t in prior.WATCHED[1:]) and
                          conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                          not conn.execute("PRAGMA foreign_key_check").fetchall(),
                          "prior raw rows, protected tables, or integrity changed")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    with closing(prior.open_ro(db)) as conn:
        prior.require(prior.snapshot_table(conn, TABLE, hashes) == baseline[TABLE] and
                      all(prior.snapshot_table(conn, t) == baseline[t] for t in prior.WATCHED[1:]) and
                      conn.execute("SELECT count(*) FROM " + TABLE).fetchone()[0] ==
                          baseline[TABLE]["rows"] + 3,
                      "post-commit verification differs; use the backup for review")


def markdown(report):
    return "\n".join([
        "# AxieOS V0.15 guarded raw import", "",
        f"Status: **{report['status']}** | Exact rows: **{report['raw_rows_inserted']}**.",
        f"Raw transactions before/after: **{report['raw_before']}/{report['raw_after']}**.",
        f"Source reconciliation SHA-256: `{report['source_reconciliation_sha256']}`.",
        f"Plan SHA-256: `{report['plan_sha256']}`.",
        f"Backup: `{report['backup'] or 'none (read-only or already present)'}`.", "",
        "The 29 chain-only and 3 saved-only Axie cases remain review items. No Axie status, "
        "ledger, accounting, or finance row was changed.",
        "Verified income, expenses, profit, and PHP recovery: **UNKNOWN**. "
        "Unified Finance: **HOLD**. Checkpoint 96: **OPEN**.", "",
        f"Network detail calls: {report['network_calls']} | Database writes: {report['database_writes']}", ""])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=prior.DEFAULT_DB)
    parser.add_argument("--source", type=Path, default=SOURCE_DIR / SOURCE_NAME)
    parser.add_argument("--reconciliation", type=Path, default=SOURCE_DIR / RECON_NAME)
    parser.add_argument("--output-dir", type=Path, default=SOURCE_DIR)
    parser.add_argument("--backup-dir", type=Path, default=BACKUP_DIR)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    db = args.db.expanduser().resolve()
    source, digest = prior.load_source(args.source)
    previous, previous_sha = load_reconciliation(args.reconciliation, digest)
    rows, baseline, state, calls = checked_plan(db, source, previous)
    backup = None
    inserted = 0
    if args.apply and state == "READY":
        backup = make_backup(db, args.backup_dir, baseline)
        apply(db, rows, baseline, backup)
        inserted = 3
        state = "APPLIED_AND_RECONCILED"
    elif state == "READY":
        state = "READ_ONLY_PREFLIGHT_READY"
    raw_after = baseline[TABLE]["rows"] + inserted
    report = {"version": "0.15", "task": "GUARDED_RAW_IMPORT",
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": state,
              "source_catchup_sha256": digest, "source_reconciliation_sha256": previous_sha,
              "plan_sha256": previous["raw_transaction_rehearsal"]["plan_sha256"],
              "raw_rows_inserted": inserted, "raw_before": baseline[TABLE]["rows"],
              "raw_after": raw_after, "backup": str(backup) if backup else None,
              "network_calls": calls, "database_writes": inserted,
              "axie_roster_writes": 0, "ledger_writes": 0, "finance_writes": 0,
              "verified_financial_totals": "UNKNOWN", "unified_finance": "HOLD",
              "checkpoint96": "OPEN"}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V015_Guarded_Raw_Import_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    print("AXIEOS V0.15 - GUARDED RAW IMPORT")
    print(f"Status: {state} | Exact raw rows inserted: {inserted} | Raw: "
          f"{baseline[TABLE]['rows']}/{raw_after}")
    print(f"Backup: {backup or 'none'}")
    print(f"Reports: {jp} {mp}")
    print("Axie roster/ledger/finance writes: 0 | Financial totals: UNKNOWN | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
