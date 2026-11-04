r"""Task136W: find cached wallet activity after the stored accounting cutoff.

Run from the AxieOS repository root:
    py -B .\scripts\v014_post_accounting_cache_gap.py

Reads SQLite with mode=ro/query_only. Does not run importers, classify activity,
compute financial totals, write to the database, or access the network.
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


REQUIRED = {
    "ronin_wallet_registry": {"address", "ownership_type", "wallet_role"},
    "blockchain_accounting_records": {"txhash", "datetime"},
    "blockchain_transactions": {"txhash", "datetime"},
    "ronin_api_transactions_raw": {"tx_hash", "timestamp", "block_number", "from_address", "to_address", "method", "status", "value_raw", "fee_raw", "gas_used"},
    "ronin_token_transfers_raw": {"transfer_key", "tx_hash", "log_index", "timestamp", "block_number", "from_address", "to_address", "token_type", "token_address", "token_id", "token_symbol", "amount_raw", "decimals"},
}
MAX_RAW_ROWS = 100000


def q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError("STOP: " + reason)


def parse_time(value: object, label: str) -> datetime:
    require(value is not None and str(value).strip() != "", f"{label}: missing timestamp")
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"STOP: {label}: invalid timestamp {value!r}") from exc
    if dt.tzinfo is None:
        # Existing ledger datetimes are stored as UTC, per the cached source schema.
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fetch(conn: sqlite3.Connection, table: str) -> list[dict]:
    cursor = conn.execute(f"SELECT * FROM {q(table)}")
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor]


def direction(row: dict, owned: set[str]) -> str | None:
    sender = str(row.get("from_address") or "").lower() in owned
    receiver = str(row.get("to_address") or "").lower() in owned
    if sender and receiver:
        return "BOTH_REGISTERED_OWNED"
    if sender:
        return "FROM_REGISTERED_OWNED"
    if receiver:
        return "TO_REGISTERED_OWNED"
    return None


def build(conn: sqlite3.Connection) -> dict:
    for name, fields in REQUIRED.items():
        actual = {r[1] for r in conn.execute(f"PRAGMA table_info({q(name)})")}
        require(fields <= actual, f"{name}: missing {sorted(fields - actual)}")
    wallets = fetch(conn, "ronin_wallet_registry")
    owned_rows = [w for w in wallets if str(w["ownership_type"]).upper() == "USER_OWNED"]
    owned = {str(w["address"]).lower() for w in owned_rows if w["address"]}
    require(bool(owned), "no registered USER_OWNED wallet")
    require(len(owned) == len(owned_rows), "duplicate or empty registered owned address")

    account = fetch(conn, "blockchain_accounting_records")
    ledger = fetch(conn, "blockchain_transactions")
    require(account and ledger, "accounting or ledger is empty")
    cutoff = max(parse_time(r["datetime"], "accounting.datetime") for r in account)
    ledger_latest = max(parse_time(r["datetime"], "ledger.datetime") for r in ledger)
    account_hashes = {str(r["txhash"]).lower() for r in account if r["txhash"]}
    ledger_counts = Counter(str(r["txhash"]).lower() for r in ledger if r["txhash"])
    require(len(account_hashes) == sum(bool(r["txhash"]) for r in account), "duplicate/empty accounting hash")

    raw_transactions = fetch(conn, "ronin_api_transactions_raw")
    raw_transfers = fetch(conn, "ronin_token_transfers_raw")
    require(len(raw_transactions) <= MAX_RAW_ROWS and len(raw_transfers) <= MAX_RAW_ROWS,
            "raw source too large for this bounded report")
    groups = defaultdict(lambda: {"transaction_rows": [], "transfer_rows": [], "times": []})
    selected_raw_tx = 0
    selected_raw_transfer = 0
    latest_raw = None
    for table, rows, kind in (("transaction", raw_transactions, "transaction_rows"),
                              ("transfer", raw_transfers, "transfer_rows")):
        for row in rows:
            at = parse_time(row["timestamp"], f"{table}.timestamp")
            if latest_raw is None or at > latest_raw:
                latest_raw = at
            if at <= cutoff:
                continue
            role = direction(row, owned)
            if role is None:
                continue
            h = row.get("tx_hash")
            require(isinstance(h, str) and h.strip(), f"{table}: missing selected hash")
            group = groups[h.lower()]
            group["times"].append(at)
            if kind == "transaction_rows":
                selected_raw_tx += 1
                group[kind].append({"timestamp": row["timestamp"],
                                    "block_number": row["block_number"],
                                    "from_address": row["from_address"], "to_address": row["to_address"],
                                    "method": row["method"], "status": row["status"],
                                    "value_raw": row["value_raw"], "fee_raw": row["fee_raw"],
                                    "gas_used": row["gas_used"], "wallet_relation": role})
            else:
                selected_raw_transfer += 1
                group[kind].append({"transfer_key": row["transfer_key"],
                                    "log_index": row["log_index"],
                                    "timestamp": row["timestamp"],
                                    "block_number": row["block_number"],
                                    "from_address": row["from_address"], "to_address": row["to_address"],
                                    "token_type": row["token_type"],
                                    "token_address": row["token_address"],
                                    "token_id": row["token_id"], "token_symbol": row["token_symbol"],
                                    "amount_raw": row["amount_raw"], "decimals": row["decimals"],
                                    "wallet_relation": role})
    candidate_rows = []
    for h, group in groups.items():
        candidate_rows.append({"txhash": h,
                               "first_cached_timestamp_utc": min(group["times"]).isoformat(),
                               "last_cached_timestamp_utc": max(group["times"]).isoformat(),
                               "stored_accounting_row_present": h in account_hashes,
                               "stored_ledger_row_count": ledger_counts[h],
                               "raw_transaction_rows": group["transaction_rows"],
                               "raw_transfer_rows": group["transfer_rows"],
                               "finance_treatment": "UNCLASSIFIED_CACHED_WALLET_ACTIVITY"})
    candidate_rows.sort(key=lambda x: (x["first_cached_timestamp_utc"], x["txhash"]))
    mix = Counter((bool(x["raw_transaction_rows"]), bool(x["raw_transfer_rows"]))
                  for x in candidate_rows)
    return {"project": "AxieOS", "version": "0.14", "task": "136W",
            "report_schema_version": "1.1",
            "scope": "Wallet-involved cached raw activity strictly after the accounting cutoff; no finance acceptance",
            "cutoff": {"accounting_latest_utc": cutoff.isoformat(),
                       "ledger_latest_utc": ledger_latest.isoformat(),
                       "raw_latest_utc": latest_raw.isoformat() if latest_raw else None},
            "registered_owned_wallets": [{"address": str(w["address"]).lower(),
                                          "wallet_role": w["wallet_role"]} for w in owned_rows],
            "source_rows": {"accounting": len(account), "ledger": len(ledger),
                            "raw_transactions": len(raw_transactions), "raw_transfers": len(raw_transfers)},
            "coverage": {"candidate_hashes": len(candidate_rows),
                         "wallet_raw_transaction_rows_after_cutoff": selected_raw_tx,
                         "wallet_raw_transfer_rows_after_cutoff": selected_raw_transfer,
                         "hashes_absent_from_ledger": sum(x["stored_ledger_row_count"] == 0 for x in candidate_rows),
                         "hashes_absent_from_accounting": sum(not x["stored_accounting_row_present"] for x in candidate_rows),
                         "hash_source_mix": {"both": mix[(True, True)],
                                             "transaction_only": mix[(True, False)],
                                             "transfer_only": mix[(False, True)]},
                         "raw_transaction_status_counts": dict(sorted(Counter(
                             str(x["status"]) for item in candidate_rows
                             for x in item["raw_transaction_rows"]).items())),
                         "candidate_months": dict(sorted(Counter(
                             x["first_cached_timestamp_utc"][:7] for x in candidate_rows).items()))},
            "candidate_rows": candidate_rows,
            "accepted_financial_totals": None,
            "database_writes": 0, "network_calls": 0, "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c, cutoff = report["coverage"], report["cutoff"]
    lines = ["# AxieOS V0.14 — Task136W Post-accounting cache gap", "",
             f"Accounting latest UTC: **{cutoff['accounting_latest_utc']}**. "
             f"Raw cache latest UTC: **{cutoff['raw_latest_utc']}**.", "",
             f"Wallet-involved cached hashes after accounting cutoff: **{c['candidate_hashes']}**; "
             f"without ledger rows: **{c['hashes_absent_from_ledger']}**; "
             f"without accounting rows: **{c['hashes_absent_from_accounting']}**.", "",
             "| Month (UTC) | Candidate hashes |", "|---|---:|"]
    for month, count in c["candidate_months"].items():
        lines.append(f"| {month} | {count} |")
    lines += ["", "The companion JSON preserves endpoints, raw value/fee fields, token identifiers and log ordering "
              "for cached transactions and transfers involving a registered "
              "owned wallet. A hash can contain several token transfers; it is counted once. "
              "Presence in raw cache does not establish purchase, sale, fee payer, cost basis, "
              "income, expense, or economic status. No token quantities or fees are added.", "",
              "Activity later than the raw-cache latest timestamp is outside this report and must be "
              "collected separately. The production ledger and accounting tables were not changed.", "",
              "Verified financial totals: **UNKNOWN**.", "",
              "Database opened: YES (read only) | Database writes: 0 | Network calls: 0", "",
              "VALIDATION: PASS (cached gap extraction only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    args = parser.parse_args()
    db = args.db.resolve()
    require(db.is_file(), f"database not found: {db}")
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=10)) as conn:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("BEGIN")
        report = build(conn)
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["source_database"] = str(args.db)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136W_Post_Accounting_Cache_Gap_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as out:
        json.dump(report, out, ensure_ascii=False, indent=2)
        out.write("\n")
    with mp.open("x", encoding="utf-8") as out:
        out.write(markdown(report))
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136W - POST ACCOUNTING CACHE GAP")
    print(f"Cached wallet hashes: {c['candidate_hashes']} | No ledger: "
          f"{c['hashes_absent_from_ledger']} | No accounting: "
          f"{c['hashes_absent_from_accounting']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: YES (read only) | Database writes: 0 | Network calls: 0")
    print("VALIDATION: PASS (cached gap extraction only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
