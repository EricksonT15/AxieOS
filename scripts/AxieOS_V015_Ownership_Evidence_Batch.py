r"""Read-only V0.15 evidence batch for 32 Axie ownership differences.

Save beside AxieOS_V015_Source_Reconciliation.py in scripts/. Run from repo root:
    py -B .\scripts\AxieOS_V015_Ownership_Evidence_Batch.py

Uses the pinned 162-Axie snapshot, saved roster, cached ERC-721 transfers,
and bounded explorer transfer histories for the three saved-only IDs. Produces
JSON, Markdown and CSV. Does not update ownership or finance tables.
"""

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, build_opener

import AxieOS_V015_Source_Reconciliation as prior


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "reports/axieos_v015/source_catchup"
SOURCE = BASE / "AxieOS_V015_Source_Catchup_20261105T030132_927019Z.json"
RECON = BASE / "AxieOS_V015_Source_Reconciliation_20261105T033632_937141Z.json"
RAW_APPLY = BASE / "AxieOS_V015_Guarded_Raw_Import_20261105T034038_489908Z_9ccf82.json"
CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"
API = "https://explorer.roninchain.com/api/v2/tokens/" + CONTRACT + "/instances/"
ZERO = "0x" + "0" * 40


def load_report(path, task):
    prior.require(path.is_file(), f"required {task} report missing: {path}")
    raw = path.read_bytes()
    doc = json.loads(raw.decode("utf-8-sig"))
    prior.require(doc.get("version") == "0.15" and doc.get("task") == task,
                  f"unexpected {task} report")
    return doc, hashlib.sha256(raw).hexdigest()


def addr(value):
    if isinstance(value, dict):
        value = value.get("hash") or value.get("address_hash")
    text = str(value or "").lower()
    if text.startswith("ronin:"):
        text = "0x" + text[6:]
    prior.require(prior.valid_address(text), "transfer address invalid")
    return text


def number(value):
    prior.require(type(value) is int or isinstance(value, str) and value.isascii() and value.isdecimal(),
                  "transfer integer invalid")
    result = int(value)
    prior.require(result >= 0, "negative transfer integer")
    return result


def local_rows(conn, axie_id, pinned_block):
    query = ("SELECT transfer_key,tx_hash,timestamp,block_number,log_index,from_address,to_address "
             "FROM ronin_token_transfers_raw WHERE token_type='ERC-721' "
             "AND lower(token_address)=? AND token_id=? ORDER BY block_number,log_index,transfer_key")
    rows = []
    for key, txhash, at, block, index, sender, recipient in conn.execute(query, (CONTRACT, axie_id)):
        block = number(block)
        if block > pinned_block:
            continue
        sender, recipient = addr(sender), addr(recipient)
        direction = "INTERNAL" if sender in prior.WALLETS and recipient in prior.WALLETS else (
            "IN" if recipient in prior.WALLETS else "OUT" if sender in prior.WALLETS else "UNRELATED")
        rows.append({"transfer_key": key, "txhash": str(txhash).lower(),
                     "timestamp_utc": prior.iso_utc(at).isoformat(), "block_number": block,
                     "log_index": number(index), "from": sender, "to": recipient,
                     "wallet_direction": direction})
    return rows


def fetch_page(opener, axie_id, cursor):
    endpoint = API + axie_id + "/transfers"
    prior.require(cursor is None or isinstance(cursor, dict) and len(cursor) <= 20,
                  "unexpected pagination cursor")
    if cursor:
        prior.require(all(isinstance(k, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", k)
                          and len(k) <= 48 and (v is None or type(v) in (int, str, bool))
                          and len(str(v)) <= 256 for k, v in cursor.items()),
                      "invalid pagination field")
    query = "?" + urlencode(sorted((k, "" if v is None else str(v)) for k, v in cursor.items())) if cursor else ""
    url = endpoint + query
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "AxieOS-V015-Ownership-Evidence/1"})
    with opener.open(request, timeout=20) as response:
        prior.require(response.status == 200 and response.geturl() == url and
                      "json" in response.headers.get("Content-Type", "").lower(),
                      "unexpected explorer response")
        raw = response.read(4_000_001)
    prior.require(len(raw) <= 4_000_000, "explorer page exceeds bound")
    doc = json.loads(raw)
    prior.require(isinstance(doc, dict) and isinstance(doc.get("items"), list) and
                  len(doc["items"]) <= 100 and "next_page_params" in doc,
                  "unexpected explorer page shape")
    return doc, hashlib.sha256(raw).hexdigest()


def normalized_event(item, axie_id):
    prior.require(isinstance(item, dict) and item.get("token_type") == "ERC-721" and
                  addr(item.get("token", {}).get("address_hash")) == CONTRACT and
                  str(item.get("total", {}).get("token_id")) == axie_id,
                  "explorer event is not the target Axie")
    h = str(item.get("transaction_hash", "")).lower()
    prior.require(prior.valid_hash(h), "explorer event hash invalid")
    sender, recipient = addr(item.get("from")), addr(item.get("to"))
    block = number(item.get("block_number"))
    index = number(item.get("log_index"))
    prior.require(block > 0, "explorer event block missing")
    return {"txhash": h, "block_number": block, "log_index": index,
            "timestamp_utc": prior.iso_utc(item.get("timestamp")).isoformat(),
            "from": sender, "to": recipient,
            "wallet_direction": ("INTERNAL" if sender in prior.WALLETS and recipient in prior.WALLETS
                                 else "IN" if recipient in prior.WALLETS
                                 else "OUT" if sender in prior.WALLETS else "UNRELATED"),
            "mint_from_zero": sender == ZERO}


def analyze(db, source, recon, applied, max_pages, fetch_history):
    pin = int(source["owned_inventory"]["block"], 16)
    pin_time = source["owned_inventory"]["block_timestamp_utc"]
    with closing(prior.open_ro(db)) as conn:
        conn.execute("BEGIN")
        review = prior.roster_review(conn, source)
        prior.require(review == recon["roster_review"], "roster differs from source reconciliation")
        required = {"token_type", "token_address", "token_id", "transfer_key", "tx_hash", "timestamp",
                    "block_number", "log_index", "from_address", "to_address"}
        prior.require(required <= prior.table_columns(conn, "ronin_token_transfers_raw"),
                      "cached Axie transfer schema differs")
        prior.require(conn.execute("SELECT count(*) FROM ronin_api_transactions_raw").fetchone()[0] ==
                          applied["raw_after"] == 1196 and
                      conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                      "raw import post-apply state differs")
        cases = []
        for item in review:
            axie_id = item["axie_id"]
            cached = local_rows(conn, axie_id, pin)
            latest = cached[-1] if cached else None
            case = {"axie_id": axie_id, "lane": item["lane"],
                    "saved_status": item["saved_ownership_status"],
                    "saved_class": item["saved_class"], "saved_level": item["saved_level"],
                    "saved_last_seen": item["saved_last_seen"],
                    "cached_transfer_count": len(cached),
                    "latest_cached_transfer": latest,
                    "history_status": "NOT_REQUESTED_FOR_CHAIN_ONLY",
                    "history_pages": 0, "history_events_before_pin": None,
                    "latest_explorer_transfer": None,
                    "evidence_note": "Pinned ownerOf confirms this ID in the checked wallet; acquisition and metadata unresolved"
                        if item["lane"] == "CHAIN_ONLY" else
                        "Absent from both checked wallets at pinned block; lifecycle reason requires evidence",
                    "proposed_saved_status": None, "production_update_approved": False}
            if item["lane"] == "SAVED_ONLY":
                history = fetch_history(axie_id, pin, max_pages)
                case["history_status"] = history["status"]
                case["history_pages"] = history["pages"]
                case["history_events_before_pin"] = len(history["events_at_or_before_pin"])
                case["latest_explorer_transfer"] = history["events_at_or_before_pin"][-1] \
                    if history["events_at_or_before_pin"] else None
                case["history_error"] = history["error"]
                case["history_page_sha256"] = history["page_sha256"]
                case["history_events_after_pin"] = history["events_after_pin"]
                case["explorer_events_at_or_before_pin"] = history["events_at_or_before_pin"]
                if history["status"] == "PAGINATION_END" and case["latest_explorer_transfer"]:
                    last = case["latest_explorer_transfer"]
                    if last["wallet_direction"] == "OUT":
                        case["evidence_note"] = "Latest explorer transfer before pin is outbound; sale, release, or transfer classification unresolved"
                    else:
                        case["evidence_note"] = "Explorer transfer direction does not explain absence at pinned block; investigate"
            cases.append(case)
        prior.require(sum(x["lane"] == "CHAIN_ONLY" for x in cases) == 29 and
                      sum(x["lane"] == "SAVED_ONLY" for x in cases) == 3,
                      "case count changed")
    return {"pinned_block": source["owned_inventory"]["block"],
            "pinned_timestamp_utc": pin_time, "cases": cases,
            "saved_only_complete_histories": sum(x["lane"] == "SAVED_ONLY" and x["history_status"] == "PAGINATION_END"
                                                 for x in cases)}


def markdown(report):
    cases = report["cases"]
    lines = ["# AxieOS V0.15 ownership evidence batch", "",
             f"Pinned block: `{report['pinned_block']}` at {report['pinned_timestamp_utc']}",
             "29 chain-only and 3 saved-only IDs. No ownership or finance status is updated.", "",
             "| Saved-only ID | History | Latest pre-pin direction | Latest hash | Review |",
             "| --- | --- | --- | --- | --- |"]
    for case in cases:
        if case["lane"] == "SAVED_ONLY":
            last = case["latest_explorer_transfer"] or {}
            lines.append(f"| {case['axie_id']} | {case['history_status']} ({case['history_pages']} pages) | "
                         f"{last.get('wallet_direction', 'UNKNOWN')} | {last.get('txhash', 'UNKNOWN')} | "
                         f"{case['evidence_note']} |")
    lines += ["", "The CSV contains all 32 cases and cached transfer counts. A dated ownerOf observation "
              "and transfer direction do not establish a purchase, sale, cost basis, or live ownership now.",
              "Verified income, expenses, profit and PHP recovery: **UNKNOWN**. "
              "Unified Finance: **HOLD**. Checkpoint 96: **OPEN**.", "",
              f"Production database: READ ONLY | Writes: 0 | Explorer calls: {report['network_calls']}", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=prior.DEFAULT_DB)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--reconciliation", type=Path, default=RECON)
    parser.add_argument("--raw-apply", type=Path, default=RAW_APPLY)
    parser.add_argument("--output-dir", type=Path, default=BASE)
    parser.add_argument("--max-pages", type=int, default=12)
    args = parser.parse_args()
    prior.require(1 <= args.max_pages <= 20, "max-pages outside bound")
    source, source_sha = prior.load_source(args.source)
    recon, recon_sha = load_report(args.reconciliation, "SOURCE_RECONCILIATION")
    applied, _ = load_report(args.raw_apply, "GUARDED_RAW_IMPORT")
    prior.require(recon["source"]["sha256"] == source_sha and
                  applied["source_catchup_sha256"] == source_sha and
                  applied["source_reconciliation_sha256"] == recon_sha and
                  applied["status"] == "APPLIED_AND_RECONCILED" and
                  applied["raw_rows_inserted"] == 3 and applied["raw_before"] == 1193 and
                  applied["raw_after"] == 1196 and applied["backup"] and
                  applied["finance_writes"] == applied["ledger_writes"] == applied["axie_roster_writes"] == 0,
                  "guarded raw import evidence differs")
    opener = build_opener(prior.NoRedirect())
    calls = 0

    def fetch(axie_id, pin, pages):
        nonlocal calls
        def counted_page(cursor):
            nonlocal calls
            calls += 1
            return fetch_page(opener, axie_id, cursor)
        return explorer_history_with_fetch(axie_id, pin, pages, counted_page)

    report = analyze(args.db, source, recon, applied, args.max_pages, fetch)
    report.update(version="0.15", task="OWNERSHIP_EVIDENCE_BATCH",
                  created_at_utc=datetime.now(timezone.utc).isoformat(),
                  sources={"catchup_sha256": source_sha, "reconciliation_sha256": recon_sha,
                           "guarded_import": args.raw_apply.name},
                  network_calls=calls, database_writes=0,
                  verified_financial_totals="UNKNOWN", checkpoint96="OPEN")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V015_Ownership_Evidence_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    jp, mp, cp = [args.output_dir / (stem + suffix) for suffix in (".json", ".md", ".csv")]
    with jp.open("x", encoding="utf-8") as out:
        json.dump(report, out, indent=2, ensure_ascii=False)
        out.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    fields = ("axie_id", "lane", "saved_status", "saved_class", "saved_level", "saved_last_seen",
              "cached_transfer_count", "history_status", "history_pages", "history_events_before_pin",
              "evidence_note", "proposed_saved_status", "production_update_approved")
    with cp.open("x", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: case.get(k) for k in fields} for case in report["cases"])
    print("AXIEOS V0.15 - OWNERSHIP EVIDENCE BATCH")
    print(f"Cases: 29 chain-only / 3 saved-only | Complete saved-only histories: "
          f"{report['saved_only_complete_histories']}/3")
    print(f"Reports: {jp} {mp} {cp}")
    print(f"Production read only | Writes: 0 | Explorer calls: {calls}")
    print("Financial totals: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN")


def explorer_history_with_fetch(axie_id, pin, max_pages, fetch):
    """Bounded pagination with injectable page reader for deterministic testing."""
    result = {"status": "INCOMPLETE", "pages": 0, "events_at_or_before_pin": [],
              "events_after_pin": 0, "page_sha256": [], "error": None}
    cursor, cursors, keys = None, set(), set()
    try:
        for _ in range(max_pages):
            marker = json.dumps(cursor, sort_keys=True)
            prior.require(marker not in cursors, "repeated explorer cursor")
            cursors.add(marker)
            doc, digest = fetch(cursor)
            result["pages"] += 1
            result["page_sha256"].append(digest)
            for item in doc["items"]:
                event = normalized_event(item, axie_id)
                key = (event["txhash"], event["log_index"])
                prior.require(key not in keys, "duplicate NFT transfer event")
                keys.add(key)
                if event["block_number"] <= pin:
                    result["events_at_or_before_pin"].append(event)
                else:
                    result["events_after_pin"] += 1
            cursor = doc["next_page_params"]
            if cursor is None or cursor == {}:
                result["status"] = "PAGINATION_END"
                break
        else:
            result["error"] = "PAGE_CAP_BEFORE_END"
        result["events_at_or_before_pin"].sort(key=lambda e: (e["block_number"], e["log_index"], e["txhash"]))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


if __name__ == "__main__":
    main()
