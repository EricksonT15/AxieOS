r"""Task136F: extract saved CocoChoco transfer and gameplay evidence, read only.

From the AxieOS repository root:
    py -B .\scripts\v014_consumable_transfer_evidence.py

The database is opened in SQLite read-only mode. Only timestamped reports are
written under reports/axieos_v014/task136f/. No network calls are made.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


DB_DEFAULT = Path("data/blockchain/database/axieos.db")
OUT_DEFAULT = Path("reports/axieos_v014/task136f")
RAW_COLUMNS = ("transfer_key", "tx_hash", "log_index", "timestamp", "block_number",
               "from_address", "to_address", "token_type", "token_symbol", "token_name",
               "token_address", "token_id", "amount_raw", "decimals", "imported_at")
ACCOUNTING_COLUMNS = ("accounting_key", "txhash", "datetime", "event_type", "asset_token_id",
                      "asset_category", "quantity", "direction", "accounting_status")
OTHER_TABLES = ("inventory_events", "pouch_opening_events", "pouch_reward_items",
                "gameplay_inventory_snapshots")


def ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({ident(table)})")}


def rows_as_dicts(cursor: sqlite3.Cursor) -> list[dict]:
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def extract(conn: sqlite3.Connection) -> dict:
    available = {name for (name,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )}
    for table, required in (("ronin_token_transfers_raw", RAW_COLUMNS),
                            ("blockchain_accounting_records", ACCOUNTING_COLUMNS)):
        missing = set(required) - table_columns(conn, table)
        if table not in available or missing:
            raise ValueError(f"STOP: {table} unavailable or missing columns {sorted(missing)}")
    raw = rows_as_dicts(conn.execute(
        "SELECT " + ", ".join(map(ident, RAW_COLUMNS)) + " FROM ronin_token_transfers_raw "
        "WHERE CAST(token_id AS TEXT) IN ('1','2') "
        "ORDER BY timestamp, block_number, log_index, transfer_key"
    ))
    accounting = rows_as_dicts(conn.execute(
        "SELECT " + ", ".join(map(ident, ACCOUNTING_COLUMNS)) + " FROM blockchain_accounting_records "
        "WHERE asset_category='CONSUMABLE' AND CAST(asset_token_id AS TEXT) IN ('1','2') "
        "ORDER BY datetime, accounting_key"
    ))
    other = {}
    for table in OTHER_TABLES:
        if table in available:
            # All four tables are small in the Task136E schema; preserve rows as
            # separate evidence, never add them to blockchain movement totals.
            count = conn.execute(f"SELECT COUNT(*) FROM {ident(table)}").fetchone()[0]
            if count > 10000:
                raise ValueError(f"STOP: {table} has {count} rows; narrow the extraction first")
            other[table] = rows_as_dicts(conn.execute(f"SELECT * FROM {ident(table)}"))
        else:
            other[table] = None
    return {"raw_transfers": raw, "accounting_rows": accounting, "gameplay_tables": other}


def summarize(evidence: dict) -> dict:
    raw = evidence["raw_transfers"]
    accounting = evidence["accounting_rows"]
    keys = [str(r["transfer_key"]) for r in raw]
    if len(set(keys)) != len(keys):
        raise ValueError("STOP: raw transfer_key is not unique in the extracted set")
    account_hashes = {str(r["txhash"]).lower() for r in accounting if r["txhash"]}
    first_accounting_date = {
        token: min((str(r["datetime"])[:10] for r in accounting
                    if str(r["asset_token_id"]) == token), default=None)
        for token in ("1", "2")
    }
    groups = defaultdict(list)
    for row in raw:
        group_key = (str(row["token_address"] or "").lower(), str(row["token_id"]),
                     str(row["token_type"] or ""), str(row["decimals"]))
        groups[group_key].append(row)
    contracts = []
    for (address, token, kind, decimals), members in sorted(groups.items()):
        hashes = {str(r["tx_hash"]).lower() for r in members if r["tx_hash"]}
        cutoff = first_accounting_date[token]
        prior = sum(bool(cutoff and r["timestamp"] and str(r["timestamp"])[:10] < cutoff)
                    for r in members)
        participants = Counter()
        for r in members:
            for field in ("from_address", "to_address"):
                if r[field]:
                    participants[str(r[field]).lower()] += 1
        dates = [str(r["timestamp"]) for r in members if r["timestamp"]]
        contracts.append({
            "token_address": address, "token_id": token, "token_type": kind,
            "decimals": decimals,
            "token_names": sorted({str(r["token_name"]) for r in members if r["token_name"]}),
            "token_symbols": sorted({str(r["token_symbol"]) for r in members if r["token_symbol"]}),
            "raw_rows": len(members), "distinct_transaction_hashes": len(hashes),
            "hashes_matching_accounting": len(hashes & account_hashes),
            "prior_to_first_accounting_calendar_date_rows": prior,
            "first_raw_timestamp": min(dates, default=None),
            "last_raw_timestamp": max(dates, default=None),
            "participant_row_appearances": dict(sorted(participants.items())),
        })
    return {
        "raw_rows": len(raw), "accounting_rows": len(accounting),
        "distinct_accounting_hashes": len(account_hashes),
        "raw_hashes_matching_accounting": len({str(r["tx_hash"]).lower() for r in raw if r["tx_hash"]} & account_hashes),
        "first_accounting_calendar_date": first_accounting_date,
        "contract_token_groups": contracts,
        "gameplay_table_rows": {name: None if rows is None else len(rows)
                                for name, rows in evidence["gameplay_tables"].items()},
    }


def markdown(report: dict) -> str:
    s = report["summary"]
    out = ["# AxieOS V0.14 — Task136F: Consumable transfer evidence", "",
           "**Decision:** Source extraction only. No opening inventory, unit cost, FIFO allocation, or realized profit is accepted.", "",
           f"Raw token-ID 1/2 rows: **{s['raw_rows']}**; accounting rows: **{s['accounting_rows']}**; "
           f"raw transaction hashes overlapping accounting: **{s['raw_hashes_matching_accounting']}**.", "",
           "| Contract | Token ID | Type | Decimals | Raw rows | Prior calendar date | Accounting hash overlap | First → last stored timestamp |",
           "|---|---:|---|---:|---:|---:|---:|---|"]
    for g in s["contract_token_groups"]:
        out.append(f"| `{g['token_address']}` | {g['token_id']} | {g['token_type']} | {g['decimals']} | "
                   f"{g['raw_rows']} | {g['prior_to_first_accounting_calendar_date_rows']} | "
                   f"{g['hashes_matching_accounting']} | {g['first_raw_timestamp']} → {g['last_raw_timestamp']} |")
    out += ["", "The 'prior calendar date' column counts raw rows dated before the first accounting calendar date for that token ID. It does not calculate an opening quantity. Contract and wallet identity require review before interpreting amounts or directions.", "",
            "## Other local evidence rows", ""]
    for name, count in s["gameplay_table_rows"].items():
        out.append(f"- `{name}`: {count if count is not None else 'table absent'}")
    out += ["", "Gameplay events and pouch rewards are preserved separately in the JSON. They may describe the same underlying movement as blockchain transfers; do not sum them together. Raw `amount_raw` units and wallet ownership are not assumed by this report.", "",
            "**Validation:** PASS for read-only extraction and unique raw transfer keys. Financial verification UNKNOWN; Checkpoint 96 OPEN.", ""]
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_DEFAULT)
    parser.add_argument("--output-dir", type=Path, default=OUT_DEFAULT)
    args = parser.parse_args()
    db = args.db.resolve()
    if not db.is_file():
        raise SystemExit(f"STOP: database not found: {db}. Pass --db PATH.")
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=10)) as conn:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        evidence = extract(conn)
    report = {
        "project": "AxieOS", "version": "0.14", "task": "136F",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_database": str(args.db), "summary": summarize(evidence), "evidence": evidence,
        "accepted_opening_balance": None, "accepted_cost_basis": None,
        "accepted_realized_profit": None, "checkpoint96": "OPEN",
        "database_writes": 0, "network_calls": 0,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V014_Task136F_Consumable_Transfer_Evidence_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6]
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    jp.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    mp.write_text(markdown(report), encoding="utf-8")
    print("AXIEOS V0.14 - TASK136F - CONSUMABLE TRANSFER EVIDENCE")
    print(f"Raw rows: {report['summary']['raw_rows']} | Contract/token groups: {len(report['summary']['contract_token_groups'])}")
    print("Opening balance, cost basis and profit: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: YES (read only) | Database writes: 0 | Network calls: 0")
    print("VALIDATION: PASS (extraction only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
