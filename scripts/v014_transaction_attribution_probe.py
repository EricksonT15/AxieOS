r"""Task136P: read-only candidate transaction attribution for gameplay events.

From the AxieOS repository root:
    py -B .\scripts\v014_transaction_attribution_probe.py

Candidate hashes are clues only. This script neither accepts payments or fees
nor computes finance totals. It makes no network calls or database writes.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4


UTC = timezone.utc
LOCAL_OFFSET = timedelta(hours=8)  # candidate display-time comparison only
MAX_TABLE_ROWS = 100000
MAX_CANDIDATES = 40
REQUIRED = {
    "marketplace_events": {"id", "event_datetime", "event_type", "asset_type", "asset_id", "quantity", "amount", "currency"},
    "pouch_opening_events": {"id", "event_datetime", "request_tx_hash", "fulfillment_tx_hash", "net_ron_cost"},
    "blockchain_accounting_records": {"txhash", "datetime", "classification", "asset_category", "asset_token_id", "quantity", "gross_amount"},
    "blockchain_transactions": {"txhash", "datetime", "method", "status", "txn_fee_ron"},
    "ronin_api_transactions_raw": {"tx_hash", "timestamp", "method", "status", "fee_raw", "gas_used"},
    "ronin_token_transfers_raw": {"tx_hash", "timestamp", "token_type", "token_id", "amount_raw"},
}


def quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def read_sources(conn: sqlite3.Connection) -> dict:
    tables = {}
    for table, required in REQUIRED.items():
        fields = {r[1] for r in conn.execute(f"PRAGMA table_info({quote(table)})")}
        if missing := required - fields:
            raise ValueError(f"STOP: {table} missing columns {sorted(missing)}")
        count = conn.execute(f"SELECT COUNT(*) FROM {quote(table)}").fetchone()[0]
        if count > MAX_TABLE_ROWS:
            raise ValueError(f"STOP: {table} has {count} rows; narrow the probe")
        cursor = conn.execute(f"SELECT * FROM {quote(table)}")
        names = [col[0] for col in cursor.description]
        tables[table] = [dict(zip(names, row)) for row in cursor]
        if len(tables[table]) != count:
            raise ValueError(f"STOP: {table} changed during extraction")
    return tables


def moment(value: object) -> datetime | None:
    if value is None or str(value).strip() == "":
        return None
    s = str(value).strip()
    try:
        if s.isdecimal():
            return datetime.fromtimestamp(int(s), UTC).replace(tzinfo=None)
        parsed = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return parsed.astimezone(UTC).replace(tzinfo=None) if parsed.tzinfo else parsed
    except (ValueError, OverflowError):
        return None


def normalized_id(value: object) -> str | None:
    if value in (None, ""):
        return None
    try:
        return str(int(str(value)))
    except ValueError:
        return str(value)


def same_amount(a: object, b: object) -> bool:
    if a is None or b is None:
        return False
    try:
        return Decimal(str(a)) == Decimal(str(b))
    except InvalidOperation:
        return False


def public_tx(tx: dict) -> dict:
    return {k: tx.get(k) for k in ("txhash", "datetime", "method", "status", "txn_fee_ron")}


def raw_tx(tx: dict) -> dict:
    return {k: tx.get(k) for k in ("tx_hash", "timestamp", "method", "status", "fee_raw", "gas_used")}


def build_report(tables: dict) -> dict:
    accounts = tables["blockchain_accounting_records"]
    transfers = tables["ronin_token_transfers_raw"]
    transactions = {}
    raw_transactions = {}
    for row in tables["blockchain_transactions"]:
        if row["txhash"]:
            transactions.setdefault(str(row["txhash"]).lower(), []).append(row)
    for row in tables["ronin_api_transactions_raw"]:
        if row["tx_hash"]:
            raw_transactions.setdefault(str(row["tx_hash"]).lower(), []).append(row)

    events = []
    for event in tables["marketplace_events"]:
        if event["event_type"] not in ("buy", "sale"):
            continue
        local = moment(event["event_datetime"])
        if local is None:
            raise ValueError(f"STOP: unparseable marketplace datetime for ID {event['id']}")
        day_only = len(str(event["event_datetime"]).strip()) == 10
        classification = "MARKETPLACE_BUY" if event["event_type"] == "buy" else "MARKETPLACE_SALE"
        category = "AXIE_NFT" if str(event["asset_type"]).lower() == "axie" else "CONSUMABLE"
        asset_id = normalized_id(event["asset_id"])
        comparable = []
        cross_id_leads = []
        for row in accounts:
            if row["classification"] != classification or row["asset_category"] != category:
                continue
            if not same_amount(row["quantity"], event["quantity"]):
                continue
            utc_time = moment(row["datetime"])
            if utc_time is None:
                continue
            local_time = utc_time + LOCAL_OFFSET
            if abs((local_time.date() - local.date()).days) > 1:
                continue
            amount_equal = (str(event["currency"]).upper() in ("ETH", "WETH")
                            and same_amount(row["gross_amount"], event["amount"]))
            seconds = None if day_only else abs(int((local_time - local).total_seconds()))
            same_id = asset_id is None or normalized_id(row["asset_token_id"]) == asset_id
            if not same_id:
                if (category == "AXIE_NFT" and amount_equal and not day_only and seconds <= 60):
                    cross_id_leads.append({"accounting_hash": row["txhash"],
                                           "onchain_asset_token_id": row["asset_token_id"],
                                           "accounting_utc": row["datetime"],
                                           "seconds_apart_after_utc_plus_8": seconds,
                                           "gross_amount": row["gross_amount"],
                                           "interpretation": "time-and-amount lead; local asset_id meaning unverified"})
                continue
            tier = "SAME_GROSS_AND_TIME_CANDIDATE" if amount_equal and (
                local_time.date() == local.date() if day_only else seconds <= 60
            ) else "CONTEXT_ONLY"
            h = str(row["txhash"]).lower() if row["txhash"] else ""
            comparable.append({"tier": tier, "accounting_hash": row["txhash"],
                               "accounting_utc": row["datetime"], "candidate_local": str(local_time),
                               "seconds_apart": seconds, "accounting_asset_id": row["asset_token_id"],
                               "accounting_gross": row["gross_amount"], "same_gross": amount_equal,
                               "transaction_rows": [public_tx(x) for x in transactions.get(h, [])],
                               "raw_transaction_rows": [raw_tx(x) for x in raw_transactions.get(h, [])]})
        comparable.sort(key=lambda c: (c["tier"] != "SAME_GROSS_AND_TIME_CANDIDATE",
                                       c["seconds_apart"] if c["seconds_apart"] is not None else 999999,
                                       str(c["accounting_hash"])))
        nearby = []
        if category == "AXIE_NFT" and asset_id is not None:
            for row in transfers:
                if normalized_id(row["token_id"]) != asset_id:
                    continue
                at = moment(row["timestamp"])
                if at is None:
                    continue
                shifted = at + LOCAL_OFFSET
                if ((shifted.date() == local.date()) if day_only
                        else abs((shifted - local).total_seconds()) <= 900):
                    nearby.append({"tx_hash": row["tx_hash"], "timestamp": row["timestamp"],
                                   "token_type": row["token_type"], "token_id": row["token_id"],
                                   "amount_raw": row["amount_raw"],
                                   "transaction_rows": [public_tx(x) for x in transactions.get(str(row["tx_hash"]).lower(), [])],
                                   "raw_transaction_rows": [raw_tx(x) for x in raw_transactions.get(str(row["tx_hash"]).lower(), [])]})
        matched = [x for x in comparable if x["tier"] == "SAME_GROSS_AND_TIME_CANDIDATE"]
        events.append({"manual_id": event["id"], "action": event["event_type"],
                       "asset_type": event["asset_type"], "asset_id": event["asset_id"],
                       "asset_id_semantics": "UNVERIFIED_LOCAL_LABEL_OR_TOKEN_ID",
                       "datetime_as_stored": event["event_datetime"], "amount_as_stored": event["amount"],
                       "currency_as_stored": event["currency"], "quantity": event["quantity"],
                       "exact_amount_time_candidate_count": len(matched),
                       "accounting_candidate_count": len(comparable),
                       "accounting_candidates": comparable[:MAX_CANDIDATES],
                       "accounting_candidates_truncated": len(comparable) > MAX_CANDIDATES,
                       "cross_id_time_amount_leads": cross_id_leads[:MAX_CANDIDATES],
                       "cross_id_leads_truncated": len(cross_id_leads) > MAX_CANDIDATES,
                       "nearby_asset_transfer_count": len(nearby),
                       "nearby_asset_transfers": nearby[:MAX_CANDIDATES],
                       "nearby_asset_transfers_truncated": len(nearby) > MAX_CANDIDATES})

    pouches = []
    for pouch in tables["pouch_opening_events"]:
        if pouch["net_ron_cost"] is None and not pouch["request_tx_hash"] and not pouch["fulfillment_tx_hash"]:
            continue
        local = moment(pouch["event_datetime"])
        if local is None:
            raise ValueError(f"STOP: unparseable pouch datetime for ID {pouch['id']}")
        day_only = len(str(pouch["event_datetime"]).strip()) == 10
        explicit = {}
        for kind in ("request", "fulfillment"):
            h = pouch[kind + "_tx_hash"]
            if h:
                explicit[kind] = {"hash": h, "transaction_rows": [public_tx(x) for x in transactions.get(str(h).lower(), [])],
                                  "raw_transaction_rows": [raw_tx(x) for x in raw_transactions.get(str(h).lower(), [])]}
        nearby = []
        if not day_only:
            for row in tables["ronin_api_transactions_raw"]:
                at = moment(row["timestamp"])
                if at is not None and abs(((at + LOCAL_OFFSET) - local).total_seconds()) <= 900:
                    nearby.append(raw_tx(row))
        pouches.append({"id": pouch["id"], "datetime_as_stored": pouch["event_datetime"],
                        "net_ron_cost_as_stored": pouch["net_ron_cost"],
                        "explicit_hash_lookups": explicit, "nearby_raw_count": len(nearby),
                        "nearby_raw_rows": nearby[:MAX_CANDIDATES],
                        "nearby_raw_truncated": len(nearby) > MAX_CANDIDATES,
                        "attribution_status": "UNVERIFIED_CANDIDATES_ONLY"})
    return {"marketplace_rows": events, "pouch_rows": pouches,
            "coverage": {"marketplace_action_rows": len(events),
                         "rows_with_one_exact_amount_time_candidate": sum(x["exact_amount_time_candidate_count"] == 1 for x in events),
                         "rows_with_no_exact_amount_time_candidate": sum(x["exact_amount_time_candidate_count"] == 0 for x in events),
                         "pouch_cost_or_hash_rows": len(pouches)},
            "interpretation": "No manual row or nearby raw hash is accepted as a new finance event by this probe."}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136P transaction attribution probe", "",
             "**Mode:** Read-only local candidate links. UTC+8 is a comparison hypothesis, not a verified timezone declaration. Manual asset_id can be a local label, so cross-ID time-and-amount leads are shown separately and never accepted as identity proof.", "",
             f"Marketplace buy/sale rows: {c['marketplace_action_rows']}; one same-gross, close-time candidate: "
             f"{c['rows_with_one_exact_amount_time_candidate']}; none: {c['rows_with_no_exact_amount_time_candidate']}.", "",
             "| Manual ID | Action | Stored asset ID or label | Same-ID gross/time candidates | Cross-ID leads | Nearby asset transfers |",
             "|---:|---|---|---:|---:|---:|"]
    for row in report["marketplace_rows"]:
        lines.append(f"| {row['manual_id']} | {row['action']} | {row['asset_id'] or '—'} | "
                     f"{row['exact_amount_time_candidate_count']} | {len(row['cross_id_time_amount_leads'])} | "
                     f"{row['nearby_asset_transfer_count']} |")
    lines += ["", f"Pouch rows with stored cost or hashes: {c['pouch_cost_or_hash_rows']}. "
              "The companion JSON contains the nearby raw candidates and any exact-hash lookups. "
              "Nearby timestamps alone do not prove the transaction, payer, fee unit, or expense.", "",
              "Additional accepted finance events: **0**. Verified income, expenses, profit and recovery: **UNKNOWN**.", "",
              "Database opened: YES (read only) | Database writes: 0 | Network calls: 0", "",
              "VALIDATION: PASS (candidate attribution only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136p"))
    args = parser.parse_args()
    db = args.db.resolve()
    if not db.is_file():
        raise SystemExit(f"STOP: database not found: {db}. Pass --db PATH.")
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=10)) as conn:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        tables = read_sources(conn)
    report = build_report(tables)
    report.update({"project": "AxieOS", "version": "0.14", "task": "136P",
                   "created_at_utc": datetime.now(UTC).isoformat(),
                   "source_database": str(args.db), "accepted_financial_totals": None,
                   "database_writes": 0, "network_calls": 0, "checkpoint96": "OPEN"})
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136P_Transaction_Attribution_"
            + datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with mp.open("x", encoding="utf-8") as f:
        f.write(markdown(report))
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136P - TRANSACTION ATTRIBUTION PROBE")
    print(f"Marketplace rows: {c['marketplace_action_rows']} | One close candidate: "
          f"{c['rows_with_one_exact_amount_time_candidate']} | No close candidate: "
          f"{c['rows_with_no_exact_amount_time_candidate']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: YES (read only) | Database writes: 0 | Network calls: 0")
    print("VALIDATION: PASS (candidate attribution only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
