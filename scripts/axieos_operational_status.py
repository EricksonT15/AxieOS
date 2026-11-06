#!/usr/bin/env python3
r"""Read-only AxieOS status after a completed operational sync.

Save as scripts/axieos_operational_status.py, then run from the repository root:
    py -B .\scripts\axieos_operational_status.py

This reads the saved database and latest operational-sync evidence. It never
relabels a dated chain snapshot as live, never edits the database, and never
accepts financial totals. Run axieos_operational_sync.py separately whenever
a new chain snapshot is wanted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/blockchain/database/axieos.db"
SYNC_DIR = ROOT / "reports/axieos/operational_sync"
LEVEL_DIR = ROOT / "reports/axieos/level_recovery"
TRADE_DIR = ROOT / "reports/axieos_v016/scoped_closeout"
OUT = ROOT / "reports/axieos/operational_status"
PHT = timezone(timedelta(hours=8))
SYNC_PREFIX = "AxieOS_Operational_Sync_"
LEVEL_PREFIX = "AxieOS_AXP_Level_Recovery_"
TRADE_PREFIX = "AxieOS_V016_Scoped_Closeout_"


def require(ok, message):
    if not ok:
        raise ValueError("STOP: " + message)


def latest(directory, prefix):
    matches = sorted(directory.glob(prefix + "*.json")) if directory.is_dir() else []
    return matches[-1] if matches else None


def load(path):
    if path is None:
        return None, None
    raw = path.read_bytes()
    require(len(raw) <= 20_000_000, "saved report exceeds size cap")
    doc = json.loads(raw.decode("utf-8-sig"))
    require(isinstance(doc, dict), "saved report is not a JSON object")
    return doc, hashlib.sha256(raw).hexdigest()


def roster(db):
    require(db.is_file(), f"database missing: {db}")
    with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.execute("PRAGMA query_only=ON")
        require(conn.execute("SELECT 1 FROM sqlite_master WHERE name='gameplay_owned_axies' AND type='table'").fetchone(),
                "gameplay_owned_axies table missing")
        cols = {r[1] for r in conn.execute("PRAGMA table_info(gameplay_owned_axies)")}
        require({"axie_id", "ownership_status", "axie_class", "level", "breed_count"} <= cols,
                "owned Axie schema changed")
        rows = conn.execute("SELECT axie_id,axie_class,level,breed_count FROM gameplay_owned_axies "
                            "WHERE ownership_status='OWNED'").fetchall()
        ids = [str(r[0]) for r in rows]
        require(len(ids) == len(set(ids)) and all(i.isdecimal() and int(i) > 0 for i in ids),
                "owned Axie IDs missing or duplicated")
        raw_counts = {}
        for table in ("ronin_api_transactions_raw", "ronin_token_transfers_raw", "blockchain_transactions"):
            present = conn.execute("SELECT 1 FROM sqlite_master WHERE name=? AND type='table'", (table,)).fetchone()
            raw_counts[table] = conn.execute("SELECT count(*) FROM " + table).fetchone()[0] if present else None
        return {"saved_owned_count": len(rows),
                "unknown_class": sum(r[1] is None for r in rows),
                "unknown_level": sum(r[2] is None for r in rows),
                "unknown_breed": sum(r[3] is None for r in rows),
                "source_row_counts": raw_counts}


def sync_status(path, saved, today):
    doc, sha = load(path)
    result = {"status": "NO_SYNC_REPORT", "source_path": str(path) if path else None,
              "sha256": sha, "reported_status": None, "pinned_utc": None,
              "pinned_local_date": None, "age_days": None, "network_calls": None,
              "raw_writes": None, "reason": None}
    if doc is None:
        return result
    result["reported_status"] = doc.get("status")
    result["network_calls"] = doc.get("network_calls")
    result["raw_writes"] = doc.get("raw_writes")
    try:
        own, coverage = doc["ownership"], doc["raw_coverage"]
        when = datetime.fromisoformat(own["pinned_block_timestamp_utc"].replace("Z", "+00:00"))
        require(when.tzinfo is not None, "sync block timestamp has no timezone")
        local = when.astimezone(PHT).date()
        result.update(pinned_utc=when.astimezone(timezone.utc).isoformat(),
                      pinned_local_date=local.isoformat(), age_days=(today - local).days)
        require(local <= today, "sync block later than report date")
        require(doc.get("task") == "REUSABLE_OPERATIONAL_SYNC" and
                doc.get("status") in {"CURRENT_NO_WRITES", "APPLIED_AND_RECONCILED"} and
                doc.get("finance_totals") == "UNKNOWN" and doc.get("unified_finance") == "HOLD" and
                doc.get("checkpoint96") == "OPEN" and own["status"] == "COMPLETE_AT_PINNED_BLOCK" and
                own["saved_owned_count"] == own["pinned_chain_owned_count"] == saved["saved_owned_count"] and
                own["chain_only_ids"] == own["saved_only_ids"] == [] and
                coverage["all_four_complete"] is True and len(coverage["routes"]) == 4 and
                coverage["transaction_hashes_absent_from_raw"] == [] and
                coverage["transfer_hashes_absent_from_raw"] == [],
                "saved roster or source coverage differs from sync report")
        require(set(doc["raw_writes"]) == {"ronin_api_transactions_raw", "ronin_token_transfers_raw"} and
                all(type(v) is int and v >= 0 for v in doc["raw_writes"].values()),
                "raw write summary incomplete")
        if doc["status"] == "CURRENT_NO_WRITES":
            require(all(v == 0 for v in doc["raw_writes"].values()) and doc.get("backup") is None,
                    "no-write status conflicts with write summary")
        else:
            require(doc.get("backup"), "applied sync backup absent from report")
        result["status"] = "SYNC_RECONCILED_AT_DATED_BLOCK" if result["age_days"] else "SYNC_RECONCILED_TODAY"
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        result["status"] = "SYNC_REVIEW_REQUIRED"
        result["reason"] = str(exc)[:260]
    return result


def trade_status(path):
    doc, sha = load(path)
    result = {"status": "NO_SCOPED_TRADE_REPORT", "source_path": str(path) if path else None,
              "sha256": sha, "pairs": None, "observed_weth_difference_before_gas": None,
              "candidate_purchase_gas_ron": None}
    if doc is None:
        return result
    coverage = doc.get("coverage", {})
    if (doc.get("task") == "SCOPED_CLOSED_TRADE_CLOSEOUT" and
            doc.get("scope_status") == "COMPLETE_FOR_REPOSITORY_REVIEW" and
            doc.get("unified_finance") == "HOLD" and doc.get("checkpoint96") == "OPEN" and
            doc.get("database_writes") == 0 and coverage.get("pair_count") == 26 and
            len(doc.get("closed_trade_cases", [])) == 26 and
            all(doc.get(k) is None for k in
                ("accepted_income", "accepted_expenses", "accepted_profit", "verified_php_recovery"))):
        result.update(status="HISTORICAL_SCOPED_WALLET_FLOW", pairs=26,
                      observed_weth_difference_before_gas=coverage.get("observed_weth_difference_before_gas"),
                      candidate_purchase_gas_ron=coverage.get("purchase_gas_ron_candidate"))
    else:
        result["status"] = "SCOPED_TRADE_SOURCE_REVIEW_REQUIRED"
    return result


def level_status(path):
    doc, sha = load(path)
    if doc is None:
        return {"status": "NO_LEVEL_PROBE", "source_path": None}
    return {"status": doc.get("status"), "source_path": str(path), "sha256": sha,
            "api_error": doc.get("api_error"), "roster_updates": doc.get("roster_updates"),
            "accepted_as_level_source": doc.get("status") == "APPLIED_AND_RECONCILED"}


def write_report(output, doc):
    output.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_Operational_Status_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    jp, mp = output / (stem + ".json"), output / (stem + ".md")
    jp.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    saved, sync, trades = doc["saved_roster"], doc["last_sync"], doc["closed_trades"]
    md = ["# AxieOS operational status", "",
          f"Generated: {doc['generated_utc']}. Last chain sync: **{sync['status']}**.",
          f"Pinned chain block UTC: {sync['pinned_utc'] or 'UNKNOWN'}; "
          f"age at report date: {sync['age_days'] if sync['age_days'] is not None else 'UNKNOWN'} days.", "",
          f"Saved owned Axies: **{saved['saved_owned_count']}**. Unknown class/level/breed: "
          f"**{saved['unknown_class']}/{saved['unknown_level']}/{saved['unknown_breed']}**.",
          f"Raw transaction/transfer rows: **{saved['source_row_counts']['ronin_api_transactions_raw']}"
          f"/{saved['source_row_counts']['ronin_token_transfers_raw']}**. "
          f"Ledger rows: **{saved['source_row_counts']['blockchain_transactions']}**.", "",
          f"Saved sync evidence: `{sync['source_path'] or 'none'}` (SHA-256 {sync['sha256'] or 'none'}).",
          f"Level source: **{doc['level_source']['status']}**. "
          f"No level is inferred from AXP; unknown values stay unknown.", "",
          f"Closed trades: **{trades['status']}**; historical scoped pairs: "
          f"**{trades['pairs'] if trades['pairs'] is not None else 'UNKNOWN'}**.",
          f"Observed WETH difference before gas: **{trades['observed_weth_difference_before_gas'] or 'UNKNOWN'}**; "
          f"candidate purchase gas RON: **{trades['candidate_purchase_gas_ron'] or 'UNKNOWN'}**.", "",
          "This report does not refresh the chain. Observed wallet differences are not verified profit. "
          "Verified financial totals: **UNKNOWN**; Unified Finance: **HOLD**; Checkpoint 96: **OPEN**.",
          "Database read only; writes: 0; network calls: 0.", ""]
    mp.write_text("\n".join(md), encoding="utf-8")
    return jp, mp


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=DB)
    p.add_argument("--sync-dir", type=Path, default=SYNC_DIR)
    p.add_argument("--level-dir", type=Path, default=LEVEL_DIR)
    p.add_argument("--trade-dir", type=Path, default=TRADE_DIR)
    p.add_argument("--output-dir", type=Path, default=OUT)
    args = p.parse_args()
    now = datetime.now(timezone.utc)
    saved = roster(args.db)
    sync = sync_status(latest(args.sync_dir, SYNC_PREFIX), saved, now.astimezone(PHT).date())
    trade = trade_status(latest(args.trade_dir, TRADE_PREFIX))
    level = level_status(latest(args.level_dir, LEVEL_PREFIX))
    report = {"project": "AxieOS", "task": "OPERATIONAL_STATUS", "generated_utc": now.isoformat(),
              "as_of_philippines_date": now.astimezone(PHT).date().isoformat(),
              "saved_roster": saved, "last_sync": sync, "closed_trades": trade,
              "level_source": level, "verified_financial_totals": "UNKNOWN",
              "unified_finance": "HOLD", "checkpoint96": "OPEN",
              "database_opened": "READ_ONLY", "database_writes": 0, "network_calls": 0}
    jp, mp = write_report(args.output_dir, report)
    print("AXIEOS - OPERATIONAL STATUS")
    print("Saved Axies:", saved["saved_owned_count"], "| Unknown class/level/breed:",
          saved["unknown_class"], "/", saved["unknown_level"], "/", saved["unknown_breed"])
    print("Last chain sync:", sync["status"], "| Pinned block UTC:", sync["pinned_utc"] or "UNKNOWN")
    print("Scoped trade pairs:", trade["pairs"] if trade["pairs"] is not None else "UNKNOWN")
    print("Reports:", jp, mp)
    print("Financial totals: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN")
    print("Database: read only | Writes: 0 | Network calls: 0")


if __name__ == "__main__":
    main()
