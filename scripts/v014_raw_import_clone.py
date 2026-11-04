r"""Task136AV: rehearse the Task136AU raw-source insert in a disposable clone.

From the AxieOS repository root:
    py -B .\scripts\v014_raw_import_clone.py

Reads production SQLite in mode=ro. Copies it to a temporary database and
inserts only the 93/139 normalized raw transaction/transfer candidates from
Task136AU. Runs twice for idempotence, verifies protected tables, then deletes
the clone. No production writes, network, ledger or accounting materialization.
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
from v014_explorer_readonly_probe import utc
from v014_post_apply_reconcile import connect_ro, require


TX_FIELDS = ("tx_hash", "timestamp", "block_number", "from_address", "to_address",
             "method", "status", "value_raw", "fee_raw", "gas_used")
TRANSFER_FIELDS = ("transfer_key", "tx_hash", "log_index", "timestamp", "block_number",
                   "from_address", "to_address", "token_type", "token_symbol",
                   "token_name", "token_address", "token_id", "amount_raw", "decimals")
TABLES = {"ronin_api_transactions_raw": TX_FIELDS,
          "ronin_token_transfers_raw": TRANSFER_FIELDS}


def load(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing report: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def latest(directory: Path, task: str) -> Path:
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        doc, _ = load(path)
        if doc.get("task") == task:
            matches.append((doc.get("created_at_utc", ""), path))
    require(matches, f"missing Task{task} JSON in {directory}")
    return max(matches)[1]


def by_sha(directory: Path, digest: str, task: str) -> Path:
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        if hashlib.sha256(path.read_bytes()).hexdigest() == digest:
            doc, _ = load(path)
            if doc.get("task") == task:
                matches.append(path)
    require(len(matches) == 1, f"expected one SHA-matched Task{task} in {directory}")
    return matches[0]


def address(value: object) -> bool:
    return isinstance(value, str) and len(value) == 42 and value.lower().startswith("0x") and all(
        x in "0123456789abcdef" for x in value[2:].lower())


def txhash(value: object) -> bool:
    return isinstance(value, str) and len(value) == 66 and value.lower().startswith("0x") and all(
        x in "0123456789abcdef" for x in value[2:].lower())


def plan(au: dict, ar: dict, w: dict, shas: dict) -> tuple[dict[str, list[tuple]], str]:
    require(au.get("task") == "136AU" and ar.get("task") == "136AR" and
            w.get("task") == "136W" and w.get("report_schema_version") == "1.1" and
            all(doc.get("checkpoint96") == "OPEN" and
                doc.get("accepted_financial_totals") is None for doc in (au, ar, w)),
            "source task, checkpoint or financial boundary differs")
    require(au["sources"]["136W"]["sha256"] == shas["136W"] and
            ar["sources"]["136W"]["sha256"] == shas["136W"] and
            ar["coverage"]["new_wallet_hashes_after_snapshot"] == 0 and
            ar["coverage"]["existing_wallet_hashes_with_later_rows"] == 0 and
            ar["snapshot_latest_raw_utc"] == ar["current_latest_raw_utc"] and
            au["coverage"]["ready_for_guarded_raw_import_plan"] is True and
            all(au["coverage"][key] == 0 for key in (
                "invalid_items", "conflicting_identities", "hash_overlap_with_prior_snapshot",
                "transfer_key_overlap_with_prior_snapshot")),
            "Task136AR/AU source chain or import readiness differs")
    cutoff = utc(w["cutoff"]["raw_latest_utc"])
    require(cutoff is not None and
            au["snapshot_raw_latest_utc"] == ar["snapshot_latest_raw_utc"] ==
            cutoff.isoformat(), "raw snapshot cutoff differs")
    transactions = au["normalized_new_transactions"]
    transfers = au["normalized_new_transfers"]
    require(len(transactions) == au["coverage"]["unique_transaction_rows"] and
            len(transfers) == au["coverage"]["unique_transfer_rows"] and
            transactions and transfers, "Task136AU candidate counts differ")
    result = {table: [] for table in TABLES}
    hashes, keys = set(), set()
    for row in transactions:
        h = row["tx_hash"]
        require(txhash(h) and h == h.lower() and h not in hashes and
                utc(row["timestamp"]) is not None and utc(row["timestamp"]) > cutoff and
                address(row["from_address"]) and address(row["to_address"]) and
                isinstance(row["block_number"], int) and row["block_number"] > 0 and
                isinstance(row["source_routes_seen"], int) and row["source_routes_seen"] > 0,
                "transaction identity or source timestamp differs")
        hashes.add(h)
        gas = row.get("gas_used")
        require(gas is None or str(gas).isdecimal(), "transaction gas_used invalid")
        result["ronin_api_transactions_raw"].append((
            h, row["timestamp"], row["block_number"], row["from_address"],
            row["to_address"], row.get("method"), row.get("status"),
            str(row["value"]) if row.get("value") is not None else None,
            str(row["fee"]) if row.get("fee") is not None else None,
            int(gas) if gas is not None else None))
    for row in transfers:
        h, key = row["tx_hash"], row["transfer_key"]
        require(txhash(h) and h == h.lower() and isinstance(key, str) and
                key.lower().startswith(h + ":") and key.lower() not in keys and
                utc(row["timestamp"]) is not None and utc(row["timestamp"]) > cutoff and
                address(row["from_address"]) and address(row["to_address"]) and
                address(row["token_address"]) and
                isinstance(row["log_index"], int) and
                isinstance(row["block_number"], int) and row["block_number"] > 0 and
                str(row["amount_raw"]).isdecimal() and
                isinstance(row["source_routes_seen"], int) and row["source_routes_seen"] > 0,
                "transfer identity or source timestamp differs")
        keys.add(key.lower())
        decimals = row.get("decimals")
        require(decimals is None or str(decimals).isdecimal(),
                "transfer decimals invalid")
        result["ronin_token_transfers_raw"].append((
            key, h, row["log_index"], row["timestamp"], row["block_number"],
            row["from_address"], row["to_address"], row.get("token_type"),
            row.get("token_symbol"), row.get("token_name"), row["token_address"],
            str(row["token_id"]) if row.get("token_id") is not None else None,
            str(row["amount_raw"]), int(decimals) if decimals is not None else None))
    for table, key_index in (("ronin_api_transactions_raw", 0),
                             ("ronin_token_transfers_raw", 0)):
        result[table].sort(key=lambda row: str(row[key_index]).lower())
    fingerprint = hashlib.sha256(json.dumps(result, sort_keys=True, default=str,
                    separators=(",", ":")).encode("utf-8")).hexdigest()
    return result, fingerprint


def insert_sql(table: str, fields: tuple[str, ...]) -> str:
    require(table in TABLES and fields == TABLES[table], "unexpected raw import table")
    return (f"INSERT OR IGNORE INTO {table} (" + ",".join(fields) + ") VALUES (" +
            ",".join("?" for _ in fields) + ")")


def rehearse(db: Path, rows: dict[str, list[tuple]], w: dict) -> dict:
    with closing(connect_ro(db)) as production:
        production.execute("BEGIN")
        require(production.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                "production integrity check failed")
        owned = {str(addr).lower() for addr, typ in production.execute(
            "SELECT address,ownership_type FROM ronin_wallet_registry")
            if addr and str(typ).upper() == "USER_OWNED"}
        require(owned == {str(r["address"]).lower() for r in w["registered_owned_wallets"]},
                "owned wallet registry changed since Task136W")
        baselines = {t: table_fingerprint(production, t) for t in
                     ("blockchain_transactions",) + PROTECTED_TABLES + tuple(TABLES)}
        before = {}
        for table, fields in TABLES.items():
            actual = {r[1] for r in production.execute(f"PRAGMA table_info({table})")}
            require(set(fields) <= actual, f"{table}: raw table schema differs")
            before[table] = production.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        existing_hashes = {str(x[0]).lower() for x in production.execute(
            "SELECT tx_hash FROM ronin_api_transactions_raw")}
        existing_keys = {str(x[0]).lower() for x in production.execute(
            "SELECT transfer_key FROM ronin_token_transfers_raw")}
        require(not existing_hashes & {r[0] for r in rows["ronin_api_transactions_raw"]} and
                not existing_keys & {str(r[0]).lower() for r in rows["ronin_token_transfers_raw"]},
                "raw catch-up rows already present in production; reconcile before import")
        with TemporaryDirectory(prefix="axieos_v014_raw_clone_") as temp:
            clone_path = Path(temp) / "raw_clone.db"
            with closing(sqlite3.connect(clone_path)) as clone:
                production.backup(clone)
                require(all(table_fingerprint(clone, t) == digest
                            for t, digest in baselines.items()),
                        "clone differs from production baseline")
                clone.execute("PRAGMA foreign_keys=ON")
                first, second = {}, {}
                for table, fields in TABLES.items():
                    query = insert_sql(table, fields)
                    start = clone.total_changes
                    clone.executemany(query, rows[table])
                    first[table] = clone.total_changes - start
                clone.commit()
                for table, fields in TABLES.items():
                    start = clone.total_changes
                    clone.executemany(insert_sql(table, fields), rows[table])
                    second[table] = clone.total_changes - start
                clone.commit()
                require(all(first[t] == len(rows[t]) and second[t] == 0 and
                            clone.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] ==
                            before[t] + len(rows[t]) for t in TABLES),
                        "clone insert or second-pass idempotence differs")
                for table, fields in TABLES.items():
                    source = {str(r[0]).lower(): tuple(r) for r in rows[table]}
                    selected = {str(r[0]).lower(): tuple(r) for r in clone.execute(
                        f"SELECT {','.join(fields)} FROM {table}")
                        if str(r[0]).lower() in source}
                    require(selected == source, f"{table}: inserted source rows differ")
                require(clone.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                        not clone.execute("PRAGMA foreign_key_check").fetchall() and
                        all(table_fingerprint(clone, t) == baselines[t]
                            for t in ("blockchain_transactions",) + PROTECTED_TABLES),
                        "clone integrity or protected table changed")
        require(all(table_fingerprint(production, t) == digest
                    for t, digest in baselines.items()),
                "production changed during clone rehearsal")
    return {"clone_first_pass": first, "clone_second_pass": second,
            "production_raw_before": before, "clone_integrity": "ok",
            "protected_tables_unchanged": len(PROTECTED_TABLES) + 1,
            "clone_deleted": True, "production_writes": 0}


def markdown(report: dict) -> str:
    c = report["coverage"]
    return "\n".join([
        "# AxieOS V0.14 — Task136AV Raw import clone rehearsal", "",
        f"Proposed transaction/transfer rows: **{c['proposed_transactions']}/"
        f"{c['proposed_transfers']}**. Clone first pass: **{c['clone_first_pass']}**; "
        f"second pass: **{c['clone_second_pass']}**.", "",
        f"Plan SHA-256: `{report['plan_sha256']}`. No raw rows, ledger, "
        "economic events, or accounting rows were added to production.", "",
        "This rehearsal does not classify transactions or verify fee payer, basis, "
        "profit, portfolio value, or PHP recovery. Verified totals: **UNKNOWN**.", "",
        "Production opened read only | Production writes: 0 | Clone deleted | Network: 0", "",
        "VALIDATION: PASS (raw-source clone rehearsal only; Checkpoint 96 OPEN).", ""])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--au", type=Path)
    parser.add_argument("--au-dir", type=Path, default=Path("reports/axieos_v014/task136au"))
    parser.add_argument("--ar-dir", type=Path, default=Path("reports/axieos_v014/task136ar"))
    parser.add_argument("--w-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136av"))
    args = parser.parse_args()
    ap = args.au or latest(args.au_dir, "136AU")
    au, au_sha = load(ap)
    rp = latest(args.ar_dir, "136AR")
    ar, ar_sha = load(rp)
    wp = by_sha(args.w_dir, au["sources"]["136W"]["sha256"], "136W")
    w, w_sha = load(wp)
    prepared, digest = plan(au, ar, w, {"136AU": au_sha, "136AR": ar_sha,
                                         "136W": w_sha})
    result = rehearse(args.db, prepared, w)
    coverage = {"proposed_transactions": len(prepared["ronin_api_transactions_raw"]),
                "proposed_transfers": len(prepared["ronin_token_transfers_raw"]), **result}
    report = {"project": "AxieOS", "version": "0.14", "task": "136AV",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "sources": {"136AU": {"filename": ap.name, "sha256": au_sha},
                          "136AR": {"filename": rp.name, "sha256": ar_sha},
                          "136W": {"filename": wp.name, "sha256": w_sha}},
              "plan_sha256": digest, "coverage": coverage,
              "accepted_financial_totals": None,
              "production_database_opened_read_only": True,
              "production_database_writes": 0, "network_calls": 0,
              "checkpoint96": "OPEN"}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AV_Raw_Import_Clone_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136AV - RAW IMPORT CLONE REHEARSAL")
    print(f"Proposed transactions/transfers: {c['proposed_transactions']}/"
          f"{c['proposed_transfers']} | Clone first: {c['clone_first_pass']} | "
          f"second: {c['clone_second_pass']}")
    print(f"Plan SHA-256: {digest}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Production read only | Writes: 0 | Clone: deleted | Network: 0")
    print("VALIDATION: PASS (raw-source clone rehearsal only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
