#!/usr/bin/env python3
r"""One-run, read-only V0.17 operational source refresh.

Save as scripts/AxieOS_V017_Operational_Refresh.py. From the repo root:
    py -B .\scripts\AxieOS_V017_Operational_Refresh.py

Compares a fresh pinned two-wallet Axie ownership snapshot and four bounded
explorer routes with the saved roster and raw source hashes. No importer,
classifier, transaction signing, production writes, finance totals, or Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

import AxieOS_V015_Source_Catchup as source


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data/blockchain/database/axieos.db"
DEFAULT_OUT = ROOT / "reports/axieos_v017/operational_refresh"
BASELINE = ROOT / "reports/axieos_v016/dashboards/AxieOS_V016_Operational_Dashboard_2026-11-05_all.json"
HASH = re.compile(r"0x[0-9a-f]{64}\Z")


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError("STOP: " + message)


class BoundedNet(source.Net):
    def __init__(self, timeout: int, max_calls: int):
        super().__init__(timeout)
        self.max_calls = max_calls

    def fetch(self, request):
        for attempt in range(3):
            require(self.calls < self.max_calls, "network call cap reached")
            self.calls += 1
            try:
                doc = source.read_json(self.opener, request, self.timeout)
                time.sleep(0.2)
                return doc
            except HTTPError as exc:
                if exc.code not in (429, 502, 503, 504) or attempt == 2:
                    raise
            except (URLError, TimeoutError, OSError):
                if attempt == 2:
                    raise
            time.sleep(1 + attempt)


def baseline(path: Path) -> dict:
    require(path.is_file(), f"V0.16 dashboard missing: {path}")
    raw = path.read_bytes()
    doc = json.loads(raw.decode("utf-8-sig"))
    roster = doc.get("catchup_source", {})
    klass = doc.get("new_axie_class_coverage", {})
    trades = doc.get("scoped_closed_trades", {})
    require(doc.get("version") == "0.16" and
            doc.get("as_of_philippines_date") == "2026-11-05" and
            roster.get("status") == "POST_APPLY_ROSTER_RECONCILED" and
            roster.get("chain_owned_count") == 162 and
            klass.get("status") == "APPLIED_CLASS_RECONCILED" and
            klass.get("class_known") == 29 and klass.get("level_unknown") == 29 and
            trades.get("status") == "CORROBORATED_SCOPED_WALLET_FLOW" and
            trades.get("pairs_through_as_of") == 26 and
            doc.get("verified_financial_totals") == "UNKNOWN" and
            doc.get("unified_finance") == "HOLD" and doc.get("checkpoint96") == "OPEN" and
            doc.get("database_writes") == 0,
            "V0.16 baseline is not the released scoped dashboard")
    return {"filename": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
            "as_of_philippines_date": doc["as_of_philippines_date"],
            "pinned_owned_count": roster["chain_owned_count"],
            "closed_trade_pairs_at_baseline": trades["pairs_through_as_of"]}


def saved_metadata(db: Path, saved_ids: list[str]) -> dict:
    uri = db.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        conn.execute("PRAGMA query_only=ON")
        require(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='gameplay_owned_axies'").fetchone(),
                "saved Axie roster table missing")
        cols = {r[1] for r in conn.execute("PRAGMA table_info(gameplay_owned_axies)")}
        require({"axie_id", "ownership_status", "axie_class", "level", "breed_count", "wallet_address"} <= cols,
                "saved Axie roster columns differ")
        rows = conn.execute("SELECT axie_id,axie_class,level,breed_count,wallet_address "
                            "FROM gameplay_owned_axies WHERE ownership_status='OWNED'").fetchall()
    require(len(rows) == len(saved_ids) and len({str(r[0]) for r in rows}) == len(rows) and
            {str(r[0]) for r in rows} == set(saved_ids), "saved OWNED roster changed during read")
    return {"class_unknown_ids": sorted((str(r[0]) for r in rows if r[1] is None), key=int),
            "level_unknown_ids": sorted((str(r[0]) for r in rows if r[2] is None), key=int),
            "breed_unknown_ids": sorted((str(r[0]) for r in rows if r[3] is None), key=int),
            "wallet_not_in_scope_ids": sorted((str(r[0]) for r in rows
                                               if str(r[4]).lower() not in source.WALLETS), key=int)}


def review(db: Path, client: BoundedNet, max_pages: int, baseline_path: Path) -> dict:
    ref = baseline(baseline_path)
    local = source.local_sources(db)
    saved = local["saved_owned_ids"]
    require(len(saved) == len(set(saved)) and all(x.isdecimal() and int(x) > 0 for x in saved),
            "saved Axie IDs invalid")
    metadata = saved_metadata(db, saved)
    owned = source.ownership(client)
    cutoffs = {"transactions": local["latest_raw_transaction_utc"],
               "token-transfers": local["latest_raw_transfer_utc"]}
    routes = [source.collect_route(client, wallet, kind,
              source.parse_utc(cutoffs[kind]) if cutoffs[kind] else None, max_pages)
              for wallet in source.WALLETS for kind in ("transactions", "token-transfers")]
    route_ok = all(r["status"] in ("REACHED_LOCAL_CUTOFF", "EXPLORER_PAGINATION_END") for r in routes)
    live = set(owned["axie_ids"]) if owned["status"] == "COMPLETE_AT_PINNED_BLOCK" else None
    if live is not None:
        require(len(live) == sum(owned["balances"].values()) and
                all(x.isdecimal() and int(x) > 0 for x in live), "pinned ownership inconsistent")
    tx_hashes = {h for r in routes if r["kind"] == "transactions" for h in r["hashes_at_or_after_cutoff"]}
    transfers = {h for r in routes if r["kind"] == "token-transfers" for h in r["hashes_at_or_after_cutoff"]}
    require(all(HASH.fullmatch(h) for h in tx_hashes | transfers), "explorer hash invalid")
    tx_gaps = sorted(tx_hashes - set(local["raw_tx_hashes"]))
    transfer_gaps = sorted(transfers - set(local["raw_transfer_hashes"]))
    complete = live is not None and route_ok
    status = "INCOMPLETE_SOURCE_REVIEW" if not complete else (
        "CHANGES_REQUIRE_GUARDED_REVIEW" if tx_gaps or transfer_gaps or live != set(saved) else
        "CURRENT_AT_PINNED_BLOCK_AND_CUTOFFS")
    return {"project": "AxieOS", "version": "0.17", "task": "OPERATIONAL_SOURCE_REFRESH",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "status": status, "baseline_v016": ref,
            "ownership": {"status": owned["status"], "error": owned["error"],
                          "block": owned["block"], "block_timestamp_utc": owned["block_timestamp_utc"],
                          "wallet_balances": owned["balances"], "saved_owned_count": len(saved),
                          "pinned_chain_owned_count": len(live) if live is not None else None,
                          "chain_only_ids": sorted(live - set(saved), key=int) if live is not None else None,
                          "saved_only_ids": sorted(set(saved) - live, key=int) if live is not None else None},
            "raw_coverage": {"routes": routes, "all_four_complete": route_ok,
                             "local_cutoff_utc": cutoffs,
                             "saved_unique_raw_transaction_hashes": len(local["raw_tx_hashes"]),
                             "saved_unique_raw_transfer_hashes": len(local["raw_transfer_hashes"]),
                             "transaction_hashes_absent_from_raw": tx_gaps,
                             "transfer_hashes_absent_from_raw": transfer_gaps,
                             "interpretation": "Hash gaps are candidates, not verified economics. An incomplete route cannot establish zero gaps."},
            "metadata": metadata, "latest_saved_gameplay_dates": local["gameplay_latest_dates"],
            "finance": {"verified_income": "UNKNOWN", "verified_expenses": "UNKNOWN",
                        "verified_profit": "UNKNOWN", "verified_php_recovery": "UNKNOWN",
                        "unified_finance": "HOLD", "checkpoint96": "OPEN"},
            "production_database": "READ_ONLY", "database_writes": 0,
            "network_calls_attempted": client.calls,
            "network_call_cap": client.max_calls,
            "rpc_http_400_batch_fallbacks": client.batch_400_fallbacks}


def markdown(report: dict) -> str:
    o, raw, m = report["ownership"], report["raw_coverage"], report["metadata"]
    lines = ["# AxieOS V0.17 — Operational source refresh", "",
             f"Generated UTC: {report['generated_utc']}",
             f"**Status: {report['status']}**. Source baseline: "
             f"`{report['baseline_v016']['filename']}` (SHA-256 "
             f"`{report['baseline_v016']['sha256']}`).", "",
             "## Pinned ownership", "",
             f"Saved OWNED: **{o['saved_owned_count']}**; pinned chain: "
             f"**{o['pinned_chain_owned_count'] if o['pinned_chain_owned_count'] is not None else 'UNKNOWN'}**. "
             f"Status: **{o['status']}**; block `{o['block'] or 'UNKNOWN'}` "
             f"at {o['block_timestamp_utc'] or 'UNKNOWN'}.",
             f"Chain only IDs: {', '.join(o['chain_only_ids']) if o['chain_only_ids'] else 'none or UNKNOWN'}.",
             f"Saved only IDs: {', '.join(o['saved_only_ids']) if o['saved_only_ids'] else 'none or UNKNOWN'}.",
             f"Ownership error: {o['error'] or 'none'}.", "",
             "## Raw source coverage", "",
             f"Routes complete: **{sum(r['status'] in ('REACHED_LOCAL_CUTOFF', 'EXPLORER_PAGINATION_END') for r in raw['routes'])}/4**. "
             f"Transaction/transfer hash gaps: **{len(raw['transaction_hashes_absent_from_raw'])}/"
             f"{len(raw['transfer_hashes_absent_from_raw'])}** (candidate gaps when any route is incomplete).", "",
             "| Wallet | Route | Pages | Status | Error |", "| --- | --- | ---: | --- | --- |"]
    for route in raw["routes"]:
        lines.append(f"| `{route['wallet']}` | {route['kind']} | {route['pages']} | "
                     f"{route['status']} | {route['error'] or '—'} |")
    lines += ["", "Missing transaction hashes:", "", *[f"- `{h}`" for h in raw["transaction_hashes_absent_from_raw"]],
              "", "Missing transfer hashes:", "", *[f"- `{h}`" for h in raw["transfer_hashes_absent_from_raw"]],
              "", "## Saved metadata gaps", "",
              f"Class/level/breed unknown: **{len(m['class_unknown_ids'])}/"
              f"{len(m['level_unknown_ids'])}/{len(m['breed_unknown_ids'])}**. "
              "Unknown values remain unknown; a class recovered in V0.16 is not evidence of level.", "",
              "The V0.16 closed-trade cohort is historical and is not recomputed here. "
              "No Axie ownership, raw hash or financial candidate is imported or classified by this review.", "",
              "Verified income, expenses, profit and PHP recovery: **UNKNOWN**. "
              "Unified Finance: **HOLD**. Checkpoint 96: **OPEN**.", "",
              f"Production database: **READ ONLY** | Writes: **0** | "
              f"Network calls: **{report['network_calls_attempted']}** "
              f"(cap {report['network_call_cap']}; RPC HTTP 400 batch fallbacks "
              f"{report['rpc_http_400_batch_fallbacks']}).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-pages", type=int, default=8)
    parser.add_argument("--max-calls", type=int, default=400)
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()
    require(1 <= args.max_pages <= 20 and 50 <= args.max_calls <= 600 and
            1 <= args.timeout <= 30, "network bounds outside allowed range")
    require(args.db.is_file(), f"database missing: {args.db}")
    client = BoundedNet(args.timeout, args.max_calls)
    report = review(args.db, client, args.max_pages, args.baseline)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V017_Operational_Refresh_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    with mp.open("x", encoding="utf-8") as handle:
        handle.write(markdown(report))
    own, raw = report["ownership"], report["raw_coverage"]
    print("AXIEOS V0.17 - BOUNDED OPERATIONAL SOURCE REFRESH")
    print("Status:", report["status"], "| Saved/pinned Axies:",
          own["saved_owned_count"], "/", own["pinned_chain_owned_count"] or "UNKNOWN")
    print("Routes complete:", sum(r["status"] in ("REACHED_LOCAL_CUTOFF", "EXPLORER_PAGINATION_END")
                                   for r in raw["routes"]), "/4 | Raw transaction/transfer gaps:",
          len(raw["transaction_hashes_absent_from_raw"]), "/", len(raw["transfer_hashes_absent_from_raw"]))
    print("Saved class/level/breed unknown:", *(len(report["metadata"][k]) for k in
          ("class_unknown_ids", "level_unknown_ids", "breed_unknown_ids")))
    print("Reports:", jp, mp)
    print("Production database: READ ONLY | Writes: 0 | Network calls:", client.calls)
    print("Financial totals: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
