r"""Task136Y: read-only historical control for cached Axie/WETH transfer patterns.

Run from the AxieOS repository root:
    py -B .\scripts\v014_marketplace_pattern_control.py

Reads the local database in SQLite mode=ro and the latest Task136W schema 1.1
report. Does not insert, import, accept new finance events, or access the network.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4


REQUIRED = {
    "ronin_wallet_registry": {"address", "ownership_type"},
    "blockchain_accounting_records": {"txhash", "classification", "asset_token_id",
                                      "gross_amount", "net_amount"},
    "ronin_token_transfers_raw": {"tx_hash", "token_type", "token_symbol", "token_id",
                                  "amount_raw", "decimals", "from_address", "to_address"},
}
MAX_ROWS = 100000


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError("STOP: " + message)


def find_w(directory: Path) -> Path:
    matches = []
    for path in directory.glob("AxieOS_V014_Task136W_Post_Accounting_Cache_Gap_*.json"):
        with path.open(encoding="utf-8") as stream:
            d = json.load(stream)
        if d.get("report_schema_version") == "1.1":
            matches.append((d.get("created_at_utc", ""), path))
    require(bool(matches), f"no Task136W schema 1.1 report in {directory}; pass --cache PATH")
    return max(matches)[1]


def fetch(conn: sqlite3.Connection, name: str) -> list[dict]:
    actual = {row[1] for row in conn.execute(f'PRAGMA table_info("{name}")')}
    require(REQUIRED[name] <= actual, f"{name}: missing {sorted(REQUIRED[name] - actual)}")
    count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
    require(count <= MAX_ROWS, f"{name}: {count} rows exceeds bounded report")
    cursor = conn.execute(f'SELECT * FROM "{name}"')
    columns = [d[0] for d in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor]
    require(len(rows) == count, f"{name}: count changed during snapshot")
    return rows


def amount(value: object) -> Decimal | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def asset_id(value: object) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    raw = str(value).strip()
    return str(int(raw)) if raw.isdecimal() else raw


def signature(transfers: list[dict], owned: set[str]) -> dict | None:
    involved = [t for t in transfers if str(t["from_address"] or "").lower() in owned
                or str(t["to_address"] or "").lower() in owned]
    if len(involved) != 2 or len(transfers) != 2:
        return None
    weth = [t for t in involved if t["token_symbol"] == "WETH"]
    axie = [t for t in involved if t["token_symbol"] == "AXIE"]
    if len(weth) != 1 or len(axie) != 1:
        return None
    w, a = weth[0], axie[0]
    if w["token_type"] != "ERC-20" or w["decimals"] != 18 or \
            a["token_type"] != "ERC-721" or str(a["amount_raw"]) != "1":
        return None
    w_out = str(w["from_address"] or "").lower() in owned
    w_in = str(w["to_address"] or "").lower() in owned
    a_out = str(a["from_address"] or "").lower() in owned
    a_in = str(a["to_address"] or "").lower() in owned
    if (w_out, w_in, a_out, a_in) == (True, False, False, True):
        shape = "PURCHASE_SHAPED"
    elif (w_out, w_in, a_out, a_in) == (False, True, True, False):
        shape = "SALE_SHAPED"
    else:
        return None
    raw = str(w["amount_raw"] or "")
    if not raw.isdecimal() or int(raw) <= 0 or asset_id(a["token_id"]) is None:
        return None
    return {"shape": shape, "axie_id": asset_id(a["token_id"]),
            "weth_transfer_quantity": str(Decimal(raw) / (Decimal(10) ** 18))}


def build(cache: dict, cache_path: Path, tables: dict) -> dict:
    require(cache.get("task") == "136W" and cache.get("report_schema_version") == "1.1",
            "cache must be Task136W schema 1.1")
    require(cache.get("accepted_financial_totals") is None and cache.get("checkpoint96") == "OPEN",
            "unexpected cache finance state")
    cache_rows = cache["candidate_rows"]
    require(len(cache_rows) == cache["coverage"]["candidate_hashes"], "cache count mismatch")
    account = tables["blockchain_accounting_records"]
    account_hashes = [str(r["txhash"] or "").lower() for r in account]
    require(all(account_hashes) and len(account_hashes) == len(set(account_hashes)),
            "duplicate or missing accounting hash")
    owned = {str(r["address"]).lower() for r in tables["ronin_wallet_registry"]
             if str(r["ownership_type"]).upper() == "USER_OWNED" and r["address"]}
    require(bool(owned), "no registered owned wallet")
    cache_owned = {str(w["address"]).lower() for w in cache["registered_owned_wallets"]}
    require(owned == cache_owned, "wallet registry changed since Task136W; rerun 136W first")
    cache_hashes = {str(r["txhash"]).lower() for r in cache_rows}
    require(len(cache_hashes) == len(cache_rows) and not cache_hashes.intersection(account_hashes),
            "cached candidates overlap stored accounting hashes")
    transfers = defaultdict(list)
    for t in tables["ronin_token_transfers_raw"]:
        h = str(t["tx_hash"] or "").lower()
        if h:
            transfers[h].append(t)
    results = []
    for row in account:
        h = str(row["txhash"]).lower()
        sig = signature(transfers[h], owned)
        if sig is None:
            continue
        expected = "MARKETPLACE_BUY" if sig["shape"] == "PURCHASE_SHAPED" else "MARKETPLACE_SALE"
        stored = amount(row["gross_amount"] if sig["shape"] == "PURCHASE_SHAPED" else row["net_amount"])
        observed = amount(sig["weth_transfer_quantity"])
        stored_id = asset_id(row["asset_token_id"])
        checks = {"classification": row["classification"] == expected,
                  "weth_quantity": stored == observed if stored is not None else None,
                  "axie_id": stored_id == sig["axie_id"] if stored_id is not None else None}
        status = ("CONFLICT" if False in checks.values() else
                  "INCOMPLETE_CONTROL" if None in checks.values() else "ALIGNED_CONTROL")
        results.append({"txhash": h, **sig, "expected_classification": expected,
                        "stored_classification": row["classification"],
                        "stored_comparable_quantity": str(stored) if stored is not None else None,
                        "stored_asset_token_id": stored_id, "checks": checks,
                        "control_status": status})
    results.sort(key=lambda r: (r["control_status"], r["txhash"]))
    statuses = Counter(r["control_status"] for r in results)
    shapes = Counter(r["shape"] for r in results)
    return {"project": "AxieOS", "version": "0.14", "task": "136Y",
            "source_cache_report": str(cache_path),
            "scope": "Historical accounting-backed Axie/WETH signatures used as controls; no acceptance of new candidates",
            "coverage": {"historical_accounting_hashes": len(account),
                         "historical_hashes_with_any_raw_transfer": sum(h in transfers for h in account_hashes),
                         "historical_exact_pair_controls": len(results),
                         "historical_purchase_shaped": shapes["PURCHASE_SHAPED"],
                         "historical_sale_shaped": shapes["SALE_SHAPED"],
                         "aligned_controls": statuses["ALIGNED_CONTROL"],
                         "incomplete_controls": statuses["INCOMPLETE_CONTROL"],
                         "conflicting_controls": statuses["CONFLICT"],
                         "new_cached_hashes_held_out": len(cache_rows)},
            "historical_control_rows": results,
            "interpretation": "Structural control evidence only; even aligned controls do not verify new trades, fee assumptions or cost basis.",
            "accepted_new_events": 0, "accepted_financial_totals": None,
            "database_opened": True, "database_writes": 0, "network_calls": 0,
            "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136Y Marketplace pattern control", "",
             f"Historical accounting hashes: **{c['historical_accounting_hashes']}**; "
             f"with any raw transfer: **{c['historical_hashes_with_any_raw_transfer']}**.", "",
             f"Exact Axie/WETH structural controls: **{c['historical_exact_pair_controls']}** "
             f"({c['historical_purchase_shaped']} purchase-shaped, "
             f"{c['historical_sale_shaped']} sale-shaped).", "",
             "| Comparison with stored accounting | Hashes |", "|---|---:|",
             f"| Aligned class, asset ID, comparable WETH quantity | {c['aligned_controls']} |",
             f"| Incomplete stored comparison | {c['incomplete_controls']} |",
             f"| Conflict in at least one field | {c['conflicting_controls']} |", "",
             f"The **{c['new_cached_hashes_held_out']}** newer cached hashes remain held out "
             "from accounting. The companion JSON identifies each historical control and discrepancy.", "",
             "A sale-side WETH transfer is a candidate net receipt; this control cannot verify "
             "sale gross, fee model, gas payer, basis, profit or PHP recovery.", "",
             "Accepted new events: **0**. Verified financial totals: **UNKNOWN**.", "",
             "Database opened: YES (read only) | Writes: 0 | Network calls: 0", "",
             "VALIDATION: PASS (historical pattern comparison only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--cache-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136y"))
    args = parser.parse_args()
    cache_path = args.cache or find_w(args.cache_dir)
    require(cache_path.is_file(), f"cache report missing: {cache_path}")
    with cache_path.open(encoding="utf-8") as stream:
        cache = json.load(stream)
    db = args.db.resolve()
    require(db.is_file(), f"database missing: {db}")
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=10)) as conn:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("BEGIN")
        tables = {name: fetch(conn, name) for name in REQUIRED}
        report = build(cache, cache_path, tables)
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["source_database"] = str(args.db)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136Y_Marketplace_Pattern_Control_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
            + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with mp.open("x", encoding="utf-8") as stream:
        stream.write(markdown(report))
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136Y - MARKETPLACE PATTERN CONTROL")
    print(f"Historical controls: {c['historical_exact_pair_controls']} | "
          f"Aligned: {c['aligned_controls']} | Incomplete: {c['incomplete_controls']} | "
          f"Conflicting: {c['conflicting_controls']}")
    print(f"New cached hashes held out: {c['new_cached_hashes_held_out']} | Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: YES (read only) | Writes: 0 | Network calls: 0")
    print("VALIDATION: PASS (historical pattern comparison only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
