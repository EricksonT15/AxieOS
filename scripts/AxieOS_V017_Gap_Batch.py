#!/usr/bin/env python3
r"""One-batch V0.17 raw gap verification, clone rehearsal and guarded import.

Save in AxieOS/scripts/ beside AxieOS_V017_Operational_Refresh.py,
AxieOS_V015_Source_Catchup.py, AxieOS_V015_Source_Reconciliation.py and
ronin_api_sync.py. Run from the repository root:
    py -B .\scripts\AxieOS_V017_Gap_Batch.py

This default run is read-only for production. If its source and clone checks
pass, rerun the same file with --apply to back up and insert only raw source
rows. No ledger, classifier, economics, accounting or roster writer runs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import tempfile
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import AxieOS_V015_Source_Catchup as source
import AxieOS_V015_Source_Reconciliation as prior
import AxieOS_V017_Operational_Refresh as refresh
import ronin_api_sync as sync


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/axieos_v017/operational_refresh/AxieOS_V017_Operational_Refresh_20261105T093034_504070Z.json"
OUTPUT = ROOT / "reports/axieos_v017/operational_refresh"
DB = ROOT / "data/blockchain/database/axieos.db"
TX = "ronin_api_transactions_raw"
TF = "ronin_token_transfers_raw"
FIELDS = {
    TX: ("tx_hash", "timestamp", "block_number", "from_address", "to_address",
         "method", "status", "value_raw", "fee_raw", "gas_used"),
    TF: ("transfer_key", "tx_hash", "log_index", "timestamp", "block_number",
         "from_address", "to_address", "token_type", "token_symbol", "token_name",
         "token_address", "token_id", "amount_raw", "decimals"),
}
HASH = re.compile(r"0x[0-9a-f]{64}\Z")
ADDRESS = re.compile(r"0x[0-9a-f]{40}\Z")


def require(ok, message):
    if not ok:
        raise ValueError("STOP: " + message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    require(path.is_file(), f"source report missing: {path}")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    require(isinstance(doc, dict), "source report is not an object")
    cov, own = doc.get("raw_coverage", {}), doc.get("ownership", {})
    tx = cov.get("transaction_hashes_absent_from_raw")
    tf = cov.get("transfer_hashes_absent_from_raw")
    require(doc.get("version") == "0.17" and doc.get("task") == "OPERATIONAL_SOURCE_REFRESH" and
            doc.get("status") == "CHANGES_REQUIRE_GUARDED_REVIEW" and
            doc.get("database_writes") == 0 and doc.get("production_database") == "READ_ONLY" and
            doc.get("finance", {}).get("unified_finance") == "HOLD" and
            doc.get("finance", {}).get("checkpoint96") == "OPEN" and
            own.get("status") == "COMPLETE_AT_PINNED_BLOCK" and
            own.get("saved_owned_count") == own.get("pinned_chain_owned_count") == 162 and
            cov.get("all_four_complete") is True and
            isinstance(cov.get("routes"), list) and len(cov["routes"]) == 4 and
            isinstance(tx, list) and len(tx) == len(set(tx)) == 7 and
            isinstance(tf, list) and len(tf) == len(set(tf)) == 6 and
            all(isinstance(h, str) and HASH.fullmatch(h) for h in tx + tf),
            "V0.17 source scope or gap counts differ")
    ids = own.get("chain_only_ids"), own.get("saved_only_ids")
    require(all(isinstance(group, list) for group in ids), "ownership differences unavailable")
    require(len({(r.get("wallet"), r.get("kind")) for r in cov["routes"]}) == 4 and
            {(r["wallet"], r["kind"]) for r in cov["routes"]} ==
            {(w, k) for w in source.WALLETS for k in ("transactions", "token-transfers")} and
            all(r.get("status") in ("REACHED_LOCAL_CUTOFF", "EXPLORER_PAGINATION_END")
                and isinstance(r.get("pages"), int) and 1 <= r["pages"] <= 20
                for r in cov["routes"]), "four explorer route proofs differ")
    return doc, digest(path)


def address(value):
    require(isinstance(value, str), "raw address absent")
    value = value.lower().replace("ronin:", "0x")
    require(ADDRESS.fullmatch(value), "raw address invalid")
    return value


def decimal_text(value, label, optional=False):
    if value is None and optional:
        return None
    require(isinstance(value, (str, int)) and not isinstance(value, bool) and
            str(value).isdecimal(), f"{label}: raw integer invalid")
    return str(value)


def number(value, label):
    require(type(value) is int and value >= 0, f"{label}: integer invalid")
    return value


def tx_row(item):
    r = sync.normalize_transaction(item)
    h = str(r.get("tx_hash", "")).lower()
    require(HASH.fullmatch(h), "transaction hash invalid")
    stamp = source.parse_utc(r["timestamp"]).isoformat()
    block = number(r["block_number"], "transaction block")
    require(block > 0 and isinstance(r.get("status"), str) and r["status"],
            "transaction block/status absent")
    gas = r.get("gas_used")
    gas = int(decimal_text(gas, "transaction gas", optional=True)) if gas is not None else None
    return (h, stamp, block, address(r["from_address"]), address(r["to_address"]),
            r.get("method"), r["status"], decimal_text(r["value"], "transaction value"),
            decimal_text(r["fee"], "transaction fee", optional=True), gas)


def reconcile_transaction(page, detail):
    """Crosscheck independently fetched source views; fill only missing metadata."""
    require(len(page) == len(detail) == len(FIELDS[TX]), "transaction row shape differs")
    combined = []
    for field, from_page, from_detail in zip(FIELDS[TX], page, detail):
        if from_page is not None and from_detail is not None:
            require(from_page == from_detail,
                    f"{page[0]}: transaction {field} conflicts between wallet page and detail")
        if field not in ("method", "fee_raw", "gas_used"):
            require(from_page is not None and from_detail is not None,
                    f"{page[0]}: transaction {field} missing in wallet page or detail")
        combined.append(from_detail if from_detail is not None else from_page)
    return tuple(combined)


def transfer_row(item):
    r = sync.normalize_token_transfer(item)
    h = str(r.get("tx_hash", "")).lower()
    require(HASH.fullmatch(h), "transfer hash invalid")
    log = number(r.get("log_index"), "transfer log index")
    token = address(r["token_address"])
    token_id = str(r["token_id"]) if r.get("token_id") is not None else None
    key = f"{h}:{log}:{token}:{token_id or ''}"
    require(str(r["transfer_key"]).lower() == key, "transfer key differs from source fields")
    kind = r.get("token_type")
    require(kind in ("ERC-20", "ERC-721", "ERC-1155"), "transfer token type differs")
    raw = decimal_text(r.get("amount_raw"), "transfer amount")
    decimals = r.get("decimals")
    decimals = int(decimal_text(decimals, "transfer decimals", optional=True)) if decimals is not None else None
    return (key, h, log, source.parse_utc(r["timestamp"]).isoformat(),
            number(r["block_number"], "transfer block"),
            address(r["from_address"]), address(r["to_address"]), kind,
            r.get("token_symbol"), r.get("token_name"), token, token_id, raw, decimals)


def pages(client, route, cutoff, cap):
    cursor, seen, observed, selected, status, pages_read = None, set(), set(), [], None, 0
    for _ in range(cap):
        identity = json.dumps(cursor, sort_keys=True)
        require(identity not in seen, "explorer cursor loop")
        seen.add(identity)
        doc = client.page(route["wallet"], route["kind"], cursor)
        pages_read += 1
        require(isinstance(doc, dict) and isinstance(doc.get("items"), list) and
                len(doc["items"]) <= 100, "explorer page shape differs")
        stamps = [source.parse_utc(item["timestamp"]) for item in doc["items"]]
        require(all(a >= b for a, b in zip(stamps, stamps[1:])), "explorer order differs")
        for item, at in zip(doc["items"], stamps):
            if at < cutoff:
                continue
            h = str(item.get("hash" if route["kind"] == "transactions" else "transaction_hash", "")).lower()
            require(HASH.fullmatch(h), "explorer hash invalid")
            observed.add(h)
            selected.append((h, item))
        if any(at < cutoff for at in stamps):
            status = "REACHED_LOCAL_CUTOFF"
            break
        cursor = doc.get("next_page_params")
        if cursor is None:
            status = "EXPLORER_PAGINATION_END"
            break
        require(isinstance(cursor, dict) and doc["items"], "explorer continuation differs")
    require(status == route["status"] and pages_read <= cap,
            "explorer route did not reproduce saved cutoff/end; no import")
    return observed, selected, pages_read


def collect(db, src, client):
    cov = src["raw_coverage"]
    local = source.local_sources(db)
    require(len(local["saved_owned_ids"]) == src["ownership"]["saved_owned_count"] and
            len(local["raw_tx_hashes"]) == cov["saved_unique_raw_transaction_hashes"] and
            len(local["raw_transfer_hashes"]) == cov["saved_unique_raw_transfer_hashes"] and
            {"transactions": local["latest_raw_transaction_utc"],
             "token-transfers": local["latest_raw_transfer_utc"]} == cov["local_cutoff_utc"],
            "production source changed since V0.17 refresh; rerun refresh")
    with closing(prior.open_ro(db)) as conn:
        saved = {str(r[0]) for r in conn.execute(
            "SELECT axie_id FROM gameplay_owned_axies WHERE ownership_status='OWNED'")}
    require(saved == set(local["saved_owned_ids"]), "saved roster changed during read")
    tx_expected = set(cov["transaction_hashes_absent_from_raw"])
    tf_expected = set(cov["transfer_hashes_absent_from_raw"])
    all_seen = {"transactions": set(), "token-transfers": set()}
    selected = {"transactions": [], "token-transfers": []}
    pages_count = 0
    for route in cov["routes"]:
        kind = route["kind"]
        seen, rows, count = pages(client, route, source.parse_utc(cov["local_cutoff_utc"][kind]),
                                  min(20, route["pages"] + 2))
        all_seen[kind].update(seen)
        selected[kind].extend(rows)
        pages_count += count
    require(all_seen["transactions"] - set(local["raw_tx_hashes"]) == tx_expected and
            all_seen["token-transfers"] - set(local["raw_transfer_hashes"]) == tf_expected,
            "explorer gap hashes changed since V0.17 refresh; rerun refresh")
    prepared = {TX: {}, TF: {}}
    for h, item in selected["transactions"]:
        if h not in tx_expected:
            continue
        row = tx_row(item)
        require(row[0] == h and (row[3] in source.WALLETS or row[4] in source.WALLETS),
                f"{h}: transaction identity or wallet relation differs")
        require(h not in prepared[TX] or prepared[TX][h] == row,
                f"{h}: conflicting transaction page rows")
        prepared[TX][h] = row
    require(set(prepared[TX]) == tx_expected, "transaction gap pages incomplete")
    for h in sorted(tx_expected):
        detail = tx_row(client.detail(h))
        prepared[TX][h] = reconcile_transaction(prepared[TX][h], detail)
    for h, item in selected["token-transfers"]:
        if h not in tf_expected:
            continue
        row = transfer_row(item)
        require(row[1] == h and (row[5] in source.WALLETS or row[6] in source.WALLETS),
                f"{h}: transfer identity or wallet relation differs")
        key = row[0]
        require(key not in prepared[TF] or prepared[TF][key] == row,
                f"{key}: conflicting transfer page rows")
        prepared[TF][key] = row
    require({r[1] for r in prepared[TF].values()} == tf_expected,
            "transfer gap pages incomplete")
    rows = {t: [prepared[t][key] for key in sorted(prepared[t])] for t in FIELDS}
    require(len(rows[TX]) == 7 and len(rows[TF]) >= 6 and len(rows[TF]) <= 100,
            "raw row count outside bounded source scope")
    plan_sha = hashlib.sha256(json.dumps(rows, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
    return rows, plan_sha, pages_count


def fingerprint(conn):
    return {t: prior.snapshot_table(conn, t) for t in prior.WATCHED}


def sql(table, ignore=False):
    require(table in FIELDS, "table outside raw scope")
    prefix = "INSERT OR IGNORE" if ignore else "INSERT"
    return (prefix + " INTO " + table + " (" + ",".join(FIELDS[table]) + ") VALUES (" +
            ",".join("?" for _ in FIELDS[table]) + ")")


def db_guard(conn, rows):
    require(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
            not conn.execute("PRAGMA foreign_key_check").fetchall(), "production DB integrity differs")
    for table, fields in FIELDS.items():
        cols = prior.table_columns(conn, table)
        require(set(fields) <= cols, f"{table}: raw schema differs")
        key = "tx_hash" if table == TX else "transfer_key"
        new = {str(r[0]).lower() for r in rows[table]}
        existing = {str(r[0]).lower() for r in conn.execute("SELECT " + key + " FROM " + table)}
        require(not new & existing, f"{table}: source identity already present")
    return fingerprint(conn)


def clone_rehearsal(source_conn, rows, baseline):
    with tempfile.TemporaryDirectory(prefix="axieos_v017_raw_clone_") as folder:
        with closing(sqlite3.connect(Path(folder) / "clone.db")) as clone:
            source_conn.backup(clone)
            require(fingerprint(clone) == baseline, "clone differs from production")
            clone.execute("PRAGMA foreign_keys=ON")
            first, second = {}, {}
            for table in FIELDS:
                before = clone.total_changes
                clone.executemany(sql(table), rows[table])
                first[table] = clone.total_changes - before
            clone.commit()
            for table in FIELDS:
                before = clone.total_changes
                clone.executemany(sql(table, ignore=True), rows[table])
                second[table] = clone.total_changes - before
            clone.commit()
            require(all(first[t] == len(rows[t]) and second[t] == 0 for t in FIELDS) and
                    clone.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                    not clone.execute("PRAGMA foreign_key_check").fetchall(),
                    "clone insertion or idempotence differs")
            for table in FIELDS:
                for row in rows[table]:
                    identity = FIELDS[table][0]
                    got = clone.execute("SELECT " + ",".join(FIELDS[table]) + " FROM " + table +
                                        " WHERE " + identity + "=?", (row[0],)).fetchone()
                    require(got == row, f"{table}: clone row differs")
            require(all(prior.snapshot_table(clone, t) == baseline[t]
                        for t in prior.WATCHED if t not in FIELDS),
                    "clone protected tables differ")
    require(fingerprint(source_conn) == baseline, "production changed during clone")
    return first, second


def backup_db(db, baseline, folder):
    folder = folder.expanduser().resolve()
    require(not folder.is_relative_to(ROOT.resolve()) and not db.is_relative_to(folder),
            "backup directory must be outside repository and DB folder")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / ("axieos_before_v017_raw_" +
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6] + ".db")
    with closing(prior.open_ro(db)) as conn, closing(sqlite3.connect(target)) as dest:
        conn.backup(dest)
        require(dest.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                fingerprint(dest) == baseline, "persistent backup differs")
    return target


def apply_rows(db, rows, baseline, backup):
    require(backup.is_file(), "persistent backup missing")
    with closing(sqlite3.connect(db, timeout=15)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("BEGIN IMMEDIATE")
        try:
            require(fingerprint(conn) == baseline, "production changed after backup")
            counts = {}
            for table in FIELDS:
                before = conn.total_changes
                conn.executemany(sql(table), rows[table])
                counts[table] = conn.total_changes - before
                require(counts[table] == len(rows[table]), f"{table}: insert count differs")
                for row in rows[table]:
                    got = conn.execute("SELECT " + ",".join(FIELDS[table]) + " FROM " + table +
                                       " WHERE " + FIELDS[table][0] + "=?", (row[0],)).fetchone()
                    require(got == row, f"{table}: production row differs")
                new_hashes = {r[0] if table == TX else r[1] for r in rows[table]}
                require(prior.snapshot_table(conn, table, new_hashes) == baseline[table],
                        f"{table}: prior raw rows differ")
            require(all(prior.snapshot_table(conn, t) == baseline[t]
                        for t in prior.WATCHED if t not in FIELDS) and
                    conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                    not conn.execute("PRAGMA foreign_key_check").fetchall(),
                    "protected tables or integrity differ")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    with closing(prior.open_ro(db)) as conn:
        require(all(prior.snapshot_table(conn, t) == baseline[t]
                    for t in prior.WATCHED if t not in FIELDS) and
                all(prior.snapshot_table(conn, t, {r[0] if t == TX else r[1] for r in rows[t]}) == baseline[t]
                    for t in FIELDS), "post-commit reconciliation differs; review backup")
    return counts


def markdown(doc):
    lines = ["# AxieOS V0.17 — Guarded raw gap batch", "",
             f"Status: **{doc['status']}**. Source SHA-256: `{doc['source_sha256']}`. "
             f"Plan SHA-256: `{doc['plan_sha256']}`.", "",
             f"Exact raw transaction/transfer rows: **{doc['rows'][TX]}/{doc['rows'][TF]}**; "
             f"clone first pass: {doc['clone_first']}; second pass: {doc['clone_second']}.", "",
             f"Ownership differences (chain only / saved only): "
             f"**{doc['ownership_differences']['chain_only']}/"
             f"{doc['ownership_differences']['saved_only']}**. "
             "A count match does not establish ID match.", "",
             f"Production writes: **{doc['production_writes']}**; "
             f"backup: `{doc['backup'] or 'none'}`; network calls: {doc['network_calls']}.", "",
             "Only raw source rows are in scope. Ledger, roster, classification, "
             "accounting, verified income, expenses, profit and PHP recovery remain unchanged or UNKNOWN. "
             "Unified Finance: **HOLD**. Checkpoint 96: **OPEN**.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=REPORT)
    parser.add_argument("--db", type=Path, default=DB)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--backup-dir", type=Path, default=Path.home() / "AxieOSBackups")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    db = args.db.resolve()
    require(db.is_file(), f"production DB missing: {db}")
    source_report, source_sha = load(args.source)
    own = source_report["ownership"]
    net = refresh.BoundedNet(timeout=15, max_calls=100)
    rows, plan_sha, pages_count = collect(db, source_report, net)
    with closing(prior.open_ro(db)) as conn:
        conn.execute("BEGIN")
        baseline = db_guard(conn, rows)
        first, second = clone_rehearsal(conn, rows, baseline)
    ownership_changed = bool(own["chain_only_ids"] or own["saved_only_ids"])
    if args.apply and ownership_changed:
        backup, changes = None, {t: 0 for t in FIELDS}
        status = "OWNERSHIP_REVIEW_REQUIRED"
    elif args.apply:
        backup = backup_db(db, baseline, args.backup_dir)
        changes = apply_rows(db, rows, baseline, backup)
        status = "APPLIED_AND_RECONCILED"
    else:
        backup, changes = None, {t: 0 for t in FIELDS}
        status = "OWNERSHIP_REVIEW_REQUIRED" if ownership_changed else "READ_ONLY_PREFLIGHT_READY"
    report = {"project": "AxieOS", "version": "0.17", "task": "GUARDED_RAW_GAP_BATCH",
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": status,
              "source": {"filename": args.source.name, "sha256": source_sha},
              "source_sha256": source_sha, "plan_sha256": plan_sha,
              "rows": {t: len(rows[t]) for t in FIELDS},
              "clone_first": first, "clone_second": second,
              "ownership_differences": {"chain_only": len(own["chain_only_ids"]),
                                        "saved_only": len(own["saved_only_ids"]),
                                        "chain_only_ids": own["chain_only_ids"],
                                        "saved_only_ids": own["saved_only_ids"]},
              "backup": str(backup) if backup else None,
              "production_writes": sum(changes.values()), "raw_writes": changes,
              "ledger_writes": 0, "roster_writes": 0, "finance_writes": 0,
              "network_calls": net.calls, "pages_read": pages_count,
              "verified_financial_totals": "UNKNOWN", "unified_finance": "HOLD",
              "checkpoint96": "OPEN"}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V017_Gap_Batch_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    print("AXIEOS V0.17 - GUARDED RAW GAP BATCH")
    print("Status:", status, "| Exact raw transaction/transfer rows:", len(rows[TX]), "/", len(rows[TF]))
    print("Ownership chain-only/saved-only:", len(own["chain_only_ids"]), "/", len(own["saved_only_ids"]))
    print("Clone first/second:", first, "/", second, "| Plan SHA-256:", plan_sha)
    print("Production raw writes:", sum(changes.values()), "| Backup:", backup or "none")
    print("Reports:", jp, mp, "| Network calls:", net.calls)
    print("Financial totals: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
