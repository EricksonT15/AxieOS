#!/usr/bin/env python3
r"""Reusable, bounded AxieOS source refresh and guarded raw import.

Save as scripts/axieos_operational_sync.py beside the existing V0.15 source
modules and V0.17 gap batch. Run from the AxieOS repository root:
    py -B .\scripts\axieos_operational_sync.py --apply

Without --apply, the command only reviews and rehearses changes. With --apply,
it backs up production outside the repository and inserts only corroborated
raw transaction and token-transfer rows when ownership IDs match. No ledger,
classification, roster, accounting or economic writer runs. No signing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from uuid import uuid4

import AxieOS_V015_Source_Catchup as source
import AxieOS_V015_Source_Reconciliation as prior
import AxieOS_V017_Gap_Batch as guard
import AxieOS_V017_Operational_Refresh as refresh


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data/blockchain/database/axieos.db"
DEFAULT_OUT = ROOT / "reports/axieos/operational_sync"
KINDS = ("transactions", "token-transfers")
COMPLETE = {"REACHED_LOCAL_CUTOFF", "EXPLORER_PAGINATION_END"}


def require(ok, reason):
    if not ok:
        raise ValueError("STOP: " + reason)


def route_pages(client, wallet, kind, cutoff, max_pages):
    """One bounded read per page; retain source items for the guarded plan."""
    result = {"wallet": wallet, "kind": kind, "status": "INCOMPLETE", "pages": 0,
              "cutoff_utc": cutoff.isoformat() if cutoff else None,
              "hashes_at_or_after_cutoff": [], "error": None}
    if cutoff is None:
        result["error"] = "NO_LOCAL_CUTOFF; full-history bootstrap is outside this task"
        return result, []
    selected, hashes, seen, previous_oldest = [], set(), set(), None
    try:
        cursor = None
        for _ in range(max_pages):
            identity = json.dumps(cursor, sort_keys=True)
            require(identity not in seen, "explorer pagination loop")
            seen.add(identity)
            doc = client.page(wallet, kind, cursor)
            result["pages"] += 1
            require(isinstance(doc, dict) and isinstance(doc.get("items"), list) and
                    len(doc["items"]) <= 100, "explorer page shape differs")
            items = doc["items"]
            times = [source.parse_utc(i["timestamp"]) for i in items]
            require(all(a >= b for a, b in zip(times, times[1:])), "explorer page order differs")
            require(previous_oldest is None or not times or times[0] <= previous_oldest,
                    "explorer page sequence differs")
            if times:
                previous_oldest = times[-1]
            for item, at in zip(items, times):
                if at < cutoff:
                    continue
                h = str(item.get("hash" if kind == "transactions" else "transaction_hash", "")).lower()
                require(guard.HASH.fullmatch(h), "explorer transaction hash invalid")
                hashes.add(h)
                selected.append((h, item))
            if any(at < cutoff for at in times):
                result["status"] = "REACHED_LOCAL_CUTOFF"
                break
            cursor = doc.get("next_page_params")
            if cursor is None:
                result["status"] = "EXPLORER_PAGINATION_END"
                break
            require(isinstance(cursor, dict) and items, "explorer cursor or empty page differs")
            time.sleep(0.1)
        else:
            result["error"] = "PAGE_CAP_BEFORE_LOCAL_CUTOFF"
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError, KeyError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"[:260]
    result["hashes_at_or_after_cutoff"] = sorted(hashes)
    return result, selected


def raw_plan(client, selected, tx_missing, tf_missing, row_cap):
    require(len(tx_missing) <= row_cap and len(tf_missing) <= row_cap,
            "raw gap exceeds bounded plan; review before import")
    prepared = {guard.TX: {}, guard.TF: {}}
    for h, item in selected["transactions"]:
        if h not in tx_missing:
            continue
        row = guard.tx_row(item)
        require(row[0] == h and (row[3] in source.WALLETS or row[4] in source.WALLETS),
                f"{h}: transaction wallet relation differs")
        require(h not in prepared[guard.TX] or prepared[guard.TX][h] == row,
                f"{h}: transaction differs across wallet pages")
        prepared[guard.TX][h] = row
    require(set(prepared[guard.TX]) == tx_missing, "transaction gap page rows incomplete")
    for h in sorted(tx_missing):
        detail = guard.tx_row(client.detail(h))
        prepared[guard.TX][h] = guard.reconcile_transaction(prepared[guard.TX][h], detail)
    for h, item in selected["token-transfers"]:
        if h not in tf_missing:
            continue
        row = guard.transfer_row(item)
        require(row[1] == h and (row[5] in source.WALLETS or row[6] in source.WALLETS),
                f"{h}: transfer wallet relation differs")
        key = row[0]
        require(key not in prepared[guard.TF] or prepared[guard.TF][key] == row,
                f"{key}: transfer differs across wallet pages")
        prepared[guard.TF][key] = row
    require({r[1] for r in prepared[guard.TF].values()} == tf_missing and
            len(prepared[guard.TF]) <= row_cap, "transfer gap rows incomplete or exceed cap")
    rows = {t: [prepared[t][k] for k in sorted(prepared[t])] for t in guard.FIELDS}
    sha = hashlib.sha256(json.dumps(rows, separators=(",", ":"), default=str).encode()).hexdigest()
    return rows, sha


def backup_db(db, baseline, folder):
    folder = folder.expanduser().resolve()
    require(folder != db.parent and not folder.is_relative_to(ROOT.resolve()) and
            not db.is_relative_to(folder), "backup folder must be outside the repository")
    folder.mkdir(parents=True, exist_ok=True)
    name = "axieos_before_operational_sync_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    target = folder / (name + "_" + uuid4().hex[:6] + ".db")
    with closing(prior.open_ro(db)) as old, closing(sqlite3.connect(target)) as new:
        old.backup(new)
        require(new.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                guard.fingerprint(new) == baseline, "backup differs from production snapshot")
    return target


def save_report(output, report):
    output.mkdir(parents=True, exist_ok=True)
    name = "AxieOS_Operational_Sync_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    jp, mp = output / (name + ".json"), output / (name + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    own, raw = report["ownership"], report["raw_coverage"]
    lines = ["# AxieOS — Reusable operational source sync", "",
             f"Status: **{report['status']}**. Production raw rows inserted: "
             f"**{report['raw_writes'][guard.TX]}/{report['raw_writes'][guard.TF]}** "
             "(transactions / token transfers).", "",
             f"Saved/pinned Axie IDs: {own['saved_owned_count']}/{own['pinned_chain_owned_count']}; "
             f"chain-only/saved-only: {len(own['chain_only_ids']) if own['chain_only_ids'] is not None else 'UNKNOWN'}/"
             f"{len(own['saved_only_ids']) if own['saved_only_ids'] is not None else 'UNKNOWN'}.",
             f"Routes complete: {sum(r['status'] in COMPLETE for r in raw['routes'])}/4; "
             f"transaction/transfer hash gaps: {len(raw['transaction_hashes_absent_from_raw'])}/"
             f"{len(raw['transfer_hashes_absent_from_raw'])}.", "",
             "| Wallet | Route | Pages | Status | Error |", "| --- | --- | ---: | --- | --- |"]
    lines += [f"| `{r['wallet']}` | {r['kind']} | {r['pages']} | {r['status']} | "
              f"{r['error'] or '—'} |" for r in raw["routes"]]
    lines += ["", f"Plan SHA-256: `{report['plan_sha256'] or 'none'}`. "
              f"Clone first/second: {report['clone_first']}/{report['clone_second']}.",
              f"Backup: `{report['backup'] or 'none'}`. Network calls: {report['network_calls']}.", "",
              "No accounting, roster, ledger, classifier, or financial value is accepted by this command. "
              "Verified income, expenses, profit and PHP recovery: **UNKNOWN**. "
              "Unified Finance: **HOLD**. Checkpoint 96: **OPEN**.", ""]
    mp.write_text("\n".join(lines), encoding="utf-8")
    return jp, mp


def run(args, client):
    db = args.db.resolve()
    require(db.is_file(), f"production DB missing: {db}")
    local = source.local_sources(db)
    saved = set(local["saved_owned_ids"])
    require(len(saved) == len(local["saved_owned_ids"]) and
            all(x.isdecimal() and int(x) > 0 for x in saved), "saved Axie ID scope differs")
    owned = source.ownership(client)
    live = set(owned["axie_ids"]) if owned["status"] == "COMPLETE_AT_PINNED_BLOCK" else None
    require(live is None or len(live) == sum(owned["balances"].values()),
            "pinned ownership enumeration inconsistent")
    differences = {"chain_only_ids": sorted(live - saved, key=int) if live is not None else None,
                   "saved_only_ids": sorted(saved - live, key=int) if live is not None else None}
    cutoffs = {"transactions": local["latest_raw_transaction_utc"],
               "token-transfers": local["latest_raw_transfer_utc"]}
    if live is not None:
        observed_at = source.parse_utc(owned["block_timestamp_utc"])
        require(all(not stamp or source.parse_utc(stamp) <= observed_at
                    for stamp in cutoffs.values()),
                "saved raw UTC cutoff is later than pinned chain block")
    selected = {kind: [] for kind in KINDS}
    routes = []
    if live is not None and live == saved:
        for wallet in source.WALLETS:
            for kind in KINDS:
                route, items = route_pages(client, wallet, kind,
                    source.parse_utc(cutoffs[kind]) if cutoffs[kind] else None, args.max_pages)
                routes.append(route)
                selected[kind].extend(items)
    counts = {kind: {h for r in routes if r["kind"] == kind
                     for h in r["hashes_at_or_after_cutoff"]} for kind in KINDS}
    tx_missing = counts["transactions"] - set(local["raw_tx_hashes"])
    tf_missing = counts["token-transfers"] - set(local["raw_transfer_hashes"])
    ready = len(routes) == 4 and all(r["status"] in COMPLETE for r in routes)
    if live is None:
        status = "OWNERSHIP_SOURCE_INCOMPLETE"
    elif live != saved:
        status = "OWNERSHIP_REVIEW_REQUIRED"
    elif not ready:
        status = "EXPLORER_SOURCE_INCOMPLETE"
    elif len(tx_missing) > args.row_cap or len(tf_missing) > args.row_cap:
        status = "RAW_GAP_EXCEEDS_CAP"
    else:
        status = "READY"
    plan_sha, first, second, backup = None, None, None, None
    changes = {t: 0 for t in guard.FIELDS}
    if status == "READY":
        current = source.local_sources(db)
        require(all(current[k] == local[k] for k in ("saved_owned_ids", "raw_tx_hashes", "raw_transfer_hashes",
                "latest_raw_transaction_utc", "latest_raw_transfer_utc")),
                "production raw or roster changed during network read; rerun")
        rows, plan_sha = raw_plan(client, selected, tx_missing, tf_missing, args.row_cap)
        if not any(rows.values()):
            status = "CURRENT_NO_WRITES"
        else:
            with closing(prior.open_ro(db)) as conn:
                conn.execute("BEGIN")
                baseline = guard.db_guard(conn, rows)
                first, second = guard.clone_rehearsal(conn, rows, baseline)
            if args.apply:
                backup = backup_db(db, baseline, args.backup_dir)
                changes = guard.apply_rows(db, rows, baseline, backup)
                status = "APPLIED_AND_RECONCILED"
            else:
                status = "READ_ONLY_PREFLIGHT_READY"
    report = {"project": "AxieOS", "task": "REUSABLE_OPERATIONAL_SYNC",
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": status,
              "mode": "APPLY_GUARDED" if args.apply else "READ_ONLY",
              "ownership": {"status": owned["status"], "error": owned["error"],
                            "pinned_block": owned["block"], "pinned_block_timestamp_utc": owned["block_timestamp_utc"],
                            "saved_owned_count": len(saved), "pinned_chain_owned_count": len(live) if live is not None else None,
                            **differences},
              "raw_coverage": {"routes": routes, "all_four_complete": ready,
                               "scope": "incremental explorer pages at or after saved raw UTC cutoffs",
                               "local_cutoff_utc": cutoffs,
                               "transaction_hashes_absent_from_raw": sorted(tx_missing),
                               "transfer_hashes_absent_from_raw": sorted(tf_missing)},
              "plan_sha256": plan_sha, "clone_first": first, "clone_second": second,
              "raw_writes": changes, "backup": str(backup) if backup else None,
              "production_database_opened": "READ_ONLY_AND_GUARDED_WRITE" if backup else "READ_ONLY",
              "network_calls": client.calls, "finance_totals": "UNKNOWN",
              "unified_finance": "HOLD", "checkpoint96": "OPEN"}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--backup-dir", type=Path, default=Path.home() / "AxieOSBackups")
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--max-calls", type=int, default=500)
    parser.add_argument("--row-cap", type=int, default=150)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    require(1 <= args.max_pages <= 30 and 100 <= args.max_calls <= 1000 and
            1 <= args.row_cap <= 500 and 1 <= args.timeout <= 30,
            "page, row, network or timeout cap outside allowed bounds")
    client = refresh.BoundedNet(args.timeout, args.max_calls)
    result = run(args, client)
    jp, mp = save_report(args.output_dir, result)
    print("AXIEOS - REUSABLE OPERATIONAL SYNC")
    print("Status:", result["status"], "| Saved/pinned Axies:",
          result["ownership"]["saved_owned_count"], "/", result["ownership"]["pinned_chain_owned_count"])
    print("Routes complete:", sum(r["status"] in COMPLETE for r in result["raw_coverage"]["routes"]), "/4",
          "| Raw transaction/transfer gaps:",
          len(result["raw_coverage"]["transaction_hashes_absent_from_raw"]), "/",
          len(result["raw_coverage"]["transfer_hashes_absent_from_raw"]))
    print("Raw writes:", result["raw_writes"], "| Backup:", result["backup"] or "none")
    print("Reports:", jp, mp, "| Network calls:", result["network_calls"])
    print("Financial totals: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
