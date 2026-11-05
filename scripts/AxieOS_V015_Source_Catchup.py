r"""One-run, read-only AxieOS V0.15 source catch-up review.

Save in scripts/AxieOS_V015_Source_Catchup.py and run from repository root:
    py -B .\scripts\AxieOS_V015_Source_Catchup.py

Reads the local database and public Ronin chain/explorer. Produces one JSON and
one Markdown report. Never inserts rows, signs, broadcasts, or calculates P/L.
"""

import argparse
import json
import re
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "blockchain" / "database" / "axieos.db"
OUT = ROOT / "reports" / "axieos_v015" / "source_catchup"
RPC_URL = "https://api.roninchain.com/rpc"
EXPLORER = "https://explorer.roninchain.com/api/v2/addresses/"
AXIE = "0x32950db2a7164ae833121501c797d79e7b79d74c"
WALLETS = (
    "0x1ed8b3f3bd6a624de47f81beea101f0d15cdfbc8",
    "0x5c32ce3b21e786dcaf11d9c64dec31b21a2c6610",
)
PHT = timezone(timedelta(hours=8))
SELECTORS = {"balance": "70a08231", "index": "2f745c59", "owner": "6352211e"}
MAX_RESPONSE = 2_000_000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "redirect refused", headers, fp)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def parse_utc(value):
    require(isinstance(value, str), "timestamp missing")
    dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    require(dt.tzinfo is not None, "timestamp lacks timezone")
    return dt.astimezone(timezone.utc)


def read_json(opener, request, timeout):
    with opener.open(request, timeout=timeout) as response:
        require(response.status == 200, "HTTP status is not 200")
        require("json" in response.headers.get("Content-Type", "").lower(), "response is not JSON")
        require(response.geturl() == request.full_url, "redirected response")
        raw = response.read(MAX_RESPONSE + 1)
    require(len(raw) <= MAX_RESPONSE, "response exceeds byte cap")
    return json.loads(raw.decode("utf-8"))


class Net:
    def __init__(self, timeout=15):
        self.opener = build_opener(NoRedirect())
        self.timeout = timeout
        self.calls = 0
        self.batch_400_fallbacks = 0

    def fetch(self, request):
        for attempt in range(3):
            self.calls += 1
            try:
                result = read_json(self.opener, request, self.timeout)
                time.sleep(0.2)
                return result
            except HTTPError as exc:
                if exc.code not in (429, 502, 503, 504) or attempt == 2:
                    raise
            except (URLError, TimeoutError, OSError):
                if attempt == 2:
                    raise
            time.sleep(1 + attempt)

    def rpc(self, requests):
        require(1 <= len(requests) <= 10, "RPC batch outside bound")
        envelopes = [{"jsonrpc": "2.0", "id": i + 1, "method": method, "params": params}
                     for i, (method, params) in enumerate(requests)]
        payload = envelopes if len(envelopes) > 1 else envelopes[0]
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request = Request(RPC_URL, data=body, method="POST", headers={
            "Content-Type": "application/json", "Accept": "application/json",
            "User-Agent": "AxieOS-Source-Catchup/0.15"})
        try:
            doc = self.fetch(request)
        except HTTPError as exc:
            if exc.code != 400 or len(requests) == 1:
                raise
            self.batch_400_fallbacks += 1
            middle = len(requests) // 2
            return self.rpc(requests[:middle]) + self.rpc(requests[middle:])
        if len(envelopes) > 1 and isinstance(doc, dict) and isinstance(doc.get("error"), dict) and doc["error"].get("code") == -32600:
            return [self.rpc([spec])[0] for spec in requests]
        responses = doc if isinstance(doc, list) else [doc]
        require(len(responses) == len(envelopes), "RPC reply count mismatch")
        require(all(isinstance(r, dict) and type(r.get("id")) is int and r.get("jsonrpc") == "2.0" for r in responses), "invalid RPC envelopes")
        by_id = {r["id"]: r for r in responses}
        require(len(by_id) == len(envelopes) and set(by_id) == {e["id"] for e in envelopes}, "RPC ID mismatch")
        result = []
        for e in envelopes:
            reply = by_id[e["id"]]
            require(reply.get("error") is None and "result" in reply, f"RPC error: {reply.get('error')}")
            result.append(reply["result"])
        return result

    def page(self, wallet, kind, cursor):
        require(wallet in WALLETS and kind in ("transactions", "token-transfers"), "route not allowed")
        if cursor is not None:
            require(isinstance(cursor, dict) and len(cursor) <= 20, "invalid cursor")
            for key, value in cursor.items():
                require(isinstance(key, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key) and len(key) <= 48,
                        "invalid cursor key")
                require(value is None or isinstance(value, (str, int, bool)) and len(str(value)) <= 256,
                        "invalid cursor value")
        query = "?" + urlencode(sorted((k, "" if v is None else str(v)) for k, v in cursor.items())) if cursor else ""
        url = EXPLORER + wallet + "/" + kind + query
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "AxieOS-Source-Catchup/0.15"})
        return self.fetch(request)

    def detail(self, txhash):
        require(re.fullmatch(r"0x[0-9a-f]{64}", txhash), "invalid detail transaction hash")
        url = "https://explorer.roninchain.com/api/v2/transactions/" + txhash
        req = Request(url, headers={"Accept": "application/json", "User-Agent": "AxieOS-Source-Catchup/0.15"})
        return self.fetch(req)


def uint_abi(reply):
    require(isinstance(reply, str) and re.fullmatch(r"0x[0-9a-fA-F]{64}", reply), "invalid ABI word")
    return int(reply, 16)


def rpc_hex(reply):
    require(isinstance(reply, str) and re.fullmatch(r"0x[0-9a-fA-F]+", reply), "invalid RPC quantity")
    return int(reply, 16)


def eth_call(selector, words, block):
    require(selector in SELECTORS.values() and all(re.fullmatch(r"[0-9a-f]{64}", w) for w in words), "invalid view call")
    return ("eth_call", [{"to": AXIE, "data": "0x" + selector + "".join(words)}, block])


def grouped(client, specs):
    return [result for i in range(0, len(specs), 10) for result in client.rpc(specs[i:i + 10])]


def ownership(client):
    result = {"status": "INCOMPLETE", "wallets": list(WALLETS), "block": None,
              "block_timestamp_utc": None, "balances": {}, "axie_ids": [], "error": None}
    try:
        chain, head = client.rpc([("eth_chainId", []), ("eth_getBlockByNumber", ["latest", False])])
        require(rpc_hex(chain) == 2020, "wrong chain ID")
        require(isinstance(head, dict) and re.fullmatch(r"0x[0-9a-fA-F]{64}", head.get("hash", "")), "invalid block header")
        block, block_hash = head["number"], head["hash"]
        result["block"] = block
        result["block_timestamp_utc"] = datetime.fromtimestamp(rpc_hex(head["timestamp"]), timezone.utc).isoformat()
        age = datetime.now(timezone.utc) - parse_utc(result["block_timestamp_utc"])
        require(timedelta(minutes=-5) <= age <= timedelta(hours=1), "RPC block is not recent")
        words = [w[2:].rjust(64, "0") for w in WALLETS]
        balances = grouped(client, [eth_call(SELECTORS["balance"], [w], block) for w in words])
        owned = []
        for wallet, encoded, balance_reply in zip(WALLETS, words, balances):
            count = uint_abi(balance_reply)
            require(count <= 500, "wallet Axie count exceeds bounded enumeration")
            result["balances"][wallet] = count
            specs = [eth_call(SELECTORS["index"], [encoded, format(i, "064x")], block)
                     for i in range(count)]
            ids = [uint_abi(raw) for raw in grouped(client, specs)]
            require(len(set(ids)) == count and all(i > 0 for i in ids), "duplicate or zero token ID")
            owner_specs = [eth_call(SELECTORS["owner"], [format(i, "064x")], block) for i in ids]
            actual_owners = ["0x" + format(uint_abi(raw), "040x") for raw in grouped(client, owner_specs)]
            require(all(o == wallet for o in actual_owners), "ownerOf differs from enumeration")
            owned.extend(ids)
        require(len(set(owned)) == len(owned), "token appears in both wallets")
        recheck = client.rpc([("eth_getBlockByNumber", [block, False])])[0]
        require(isinstance(recheck, dict) and recheck.get("hash", "").lower() == block_hash.lower(), "pinned block changed")
        result.update(status="COMPLETE_AT_PINNED_BLOCK", axie_ids=sorted(map(str, owned), key=int))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError, KeyError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def collect_route(client, wallet, kind, cutoff, max_pages):
    result = {"wallet": wallet, "kind": kind, "cutoff_utc": cutoff.isoformat() if cutoff else None,
              "status": "INCOMPLETE", "pages": 0, "hashes_at_or_after_cutoff": [], "latest_utc": None, "error": None}
    if cutoff is None:
        result["error"] = "NO_LOCAL_CUTOFF; full history requires a separate bounded plan"
        return result
    cursor, seen, hashes, previous_oldest = None, set(), set(), None
    try:
        for _ in range(max_pages):
            cursor_key = json.dumps(cursor, sort_keys=True)
            require(cursor_key not in seen, "pagination cursor repeated")
            seen.add(cursor_key)
            doc = client.page(wallet, kind, cursor)
            result["pages"] += 1
            require(isinstance(doc, dict) and isinstance(doc.get("items"), list) and len(doc["items"]) <= 100,
                    "unexpected page shape")
            items = doc["items"]
            dates = [parse_utc(item["timestamp"]) for item in items]
            require(all(a >= b for a, b in zip(dates, dates[1:])), "unordered page")
            require(previous_oldest is None or not dates or dates[0] <= previous_oldest,
                    "pages out of descending order")
            if dates:
                top = dates[0].isoformat()
                if result["latest_utc"] is None:
                    result["latest_utc"] = top
                previous_oldest = dates[-1]
            for item, at in zip(items, dates):
                if at >= cutoff:
                    h = str(item.get("hash" if kind == "transactions" else "transaction_hash", "")).lower()
                    require(re.fullmatch(r"0x[0-9a-f]{64}", h), "invalid transaction hash at or after cutoff")
                    hashes.add(h)
            if any(at < cutoff for at in dates):
                result["status"] = "REACHED_LOCAL_CUTOFF"
                break
            cursor = doc.get("next_page_params")
            if cursor is None:
                result["status"] = "EXPLORER_PAGINATION_END"
                break
            require(isinstance(cursor, dict) and items, "invalid pagination continuation")
            time.sleep(0.15)
        else:
            result["error"] = "PAGE_CAP_BEFORE_LOCAL_CUTOFF"
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError, KeyError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["hashes_at_or_after_cutoff"] = sorted(hashes)
    return result


def table_columns(conn, table, required):
    present = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    if not present:
        return False
    return required <= {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def local_sources(db):
    require(db.is_file(), f"database missing: {db}")
    result = {"saved_owned_ids": [], "raw_tx_hashes": [], "raw_transfer_hashes": [],
              "latest_raw_transaction_utc": None, "latest_raw_transfer_utc": None,
              "gameplay_latest_dates": {}, "missing_tables_or_columns": []}
    with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.execute("PRAGMA query_only=ON")
        required = {
            "gameplay_owned_axies": {"axie_id", "ownership_status"},
            "ronin_api_transactions_raw": {"tx_hash", "timestamp"},
            "ronin_token_transfers_raw": {"tx_hash", "timestamp"},
        }
        for table, fields in required.items():
            if not table_columns(conn, table, fields):
                result["missing_tables_or_columns"].append(table)
        require(not result["missing_tables_or_columns"], "required source tables missing: " + ", ".join(result["missing_tables_or_columns"]))
        result["saved_owned_ids"] = sorted({str(row[0]) for row in conn.execute(
            "SELECT axie_id FROM gameplay_owned_axies WHERE ownership_status='OWNED' AND axie_id IS NOT NULL")}, key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else x))
        for table, key, cutoff_key in (("ronin_api_transactions_raw", "raw_tx_hashes", "latest_raw_transaction_utc"),
                                       ("ronin_token_transfers_raw", "raw_transfer_hashes", "latest_raw_transfer_utc")):
            rows = conn.execute(f"SELECT tx_hash,timestamp FROM {table} WHERE tx_hash IS NOT NULL").fetchall()
            result[key] = sorted({str(h).lower() for h, _ in rows})
            timestamps = []
            for _, at in rows:
                try:
                    timestamps.append(parse_utc(at))
                except (ValueError, TypeError):
                    pass
            result[cutoff_key] = max(timestamps).isoformat() if timestamps else None
        gameplay = {
            "gameplay_daily_sessions": "session_date",
            "terrarium_snapshots": "snapshot_datetime",
            "marketplace_events": "event_datetime",
            "inventory_events": "event_datetime",
            "staking_reward_events": "event_datetime",
        }
        for table, column in gameplay.items():
            result["gameplay_latest_dates"][table] = (conn.execute(f"SELECT max({column}) FROM {table}").fetchone()[0]
                 if table_columns(conn, table, {column}) else None)
    return result


def transaction_details(client, hashes):
    rows = []
    for h in hashes:
        item = {"txhash": h, "status": "UNAVAILABLE", "error": None,
                "timestamp": None, "block_number": None, "method": None,
                "chain_status": None, "fee_raw": None, "gas_used": None}
        try:
            doc = client.detail(h)
            require(isinstance(doc, dict) and str(doc.get("hash", "")).lower() == h,
                    "detail hash differs from route")
            item.update(status="CORROBORATED_DETAIL", timestamp=parse_utc(doc["timestamp"]).isoformat(),
                        block_number=doc.get("block_number"), method=doc.get("method"),
                        chain_status=doc.get("status"), fee_raw=doc.get("fee"), gas_used=doc.get("gas_used"))
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError, KeyError) as exc:
            item["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(item)
    return rows


def build_report(local, client, max_pages):
    owned = ownership(client)
    cutoffs = {"transactions": local["latest_raw_transaction_utc"],
               "token-transfers": local["latest_raw_transfer_utc"]}
    routes = [collect_route(client, w, kind, parse_utc(cutoffs[kind]) if cutoffs[kind] else None, max_pages)
              for w in WALLETS for kind in ("transactions", "token-transfers")]
    saved = set(local["saved_owned_ids"])
    live = set(owned["axie_ids"]) if owned["status"] == "COMPLETE_AT_PINNED_BLOCK" else None
    new_tx = set().union(*(set(r["hashes_at_or_after_cutoff"]) for r in routes if r["kind"] == "transactions"))
    new_transfer = set().union(*(set(r["hashes_at_or_after_cutoff"]) for r in routes if r["kind"] == "token-transfers"))
    known_tx = set(local["raw_tx_hashes"])
    known_transfer = set(local["raw_transfer_hashes"])
    tx_gaps = sorted(new_tx - known_tx)
    details = transaction_details(client, tx_gaps)
    return {"version": "0.15", "task": "SOURCE_CATCHUP", "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "owned_inventory": {"status": owned["status"], "error": owned["error"], "block": owned["block"],
                "block_timestamp_utc": owned["block_timestamp_utc"], "wallet_balances": owned["balances"],
                "saved_owned_rows": len(saved), "chain_owned_count": len(live) if live is not None else None,
                "chain_only_ids": sorted(live - saved, key=int) if live is not None else None,
                "saved_only_ids": sorted(saved - live, key=int) if live is not None else None},
            "wallet_coverage": {"routes": routes, "all_routes_reached_cutoff_or_end": all(r["status"] in ("REACHED_LOCAL_CUTOFF", "EXPLORER_PAGINATION_END") for r in routes),
                "transaction_hashes_at_or_after_cutoff_absent_from_raw": tx_gaps,
                "transfer_hashes_at_or_after_cutoff_absent_from_raw": sorted(new_transfer - known_transfer),
                "raw_transaction_cutoff_utc": cutoffs["transactions"], "raw_transfer_cutoff_utc": cutoffs["token-transfers"],
                "transaction_gap_details": details},
            "gameplay_restart": {"suggested_new_observation_date_philippines": datetime.now(PHT).date().isoformat(),
                "latest_saved_dates": local["gameplay_latest_dates"],
                "instruction": "Begin new manual gameplay and Terrarium observations at the stated date. Earlier missing days remain unobserved; do not backfill by assumption."},
            "finance": {"verified_totals": "UNKNOWN", "unified_finance": "HOLD", "checkpoint96": "OPEN"},
            "production_database": "READ_ONLY", "database_writes": 0,
            "rpc_batch_400_fallbacks": getattr(client, "batch_400_fallbacks", 0),
            "network_calls_attempted": client.calls}


def markdown(r):
    inv, cov, game = r["owned_inventory"], r["wallet_coverage"], r["gameplay_restart"]
    lines = ["# AxieOS V0.15 source catch-up review", "", f"Generated UTC: {r['created_at_utc']}", "",
             f"## Owned Axies — {inv['status']}", "", f"Saved OWNED rows: **{inv['saved_owned_rows']}**. Chain snapshot: **{inv['chain_owned_count'] if inv['chain_owned_count'] is not None else 'UNKNOWN'}**.",
             f"Pinned block: {inv['block'] or 'UNKNOWN'} at {inv['block_timestamp_utc'] or 'UNKNOWN'}. Error: {inv['error'] or 'none'}.", "",
             f"Chain only IDs: {', '.join(inv['chain_only_ids']) if inv['chain_only_ids'] else 'none or unavailable'}.  Saved only IDs: {', '.join(inv['saved_only_ids']) if inv['saved_only_ids'] else 'none or unavailable'}.", "",
             "Differences need lifecycle review; they do not prove purchase, sale, or release.", "",
             "## Wallet raw coverage", "", f"All four routes reached their local cutoff or source end: **{cov['all_routes_reached_cutoff_or_end']}**.",
             f"Transaction hashes absent from raw: **{len(cov['transaction_hashes_at_or_after_cutoff_absent_from_raw'])}**. Transfer hashes absent from raw: **{len(cov['transfer_hashes_at_or_after_cutoff_absent_from_raw'])}**.", "",
             "| Wallet | Route | Pages | Hashes at/after cutoff | Status | Error |", "| --- | --- | ---: | ---: | --- | --- |"]
    for route in cov["routes"]:
        lines.append(f"| {route['wallet'][:10]}… | {route['kind']} | {route['pages']} | {len(route['hashes_at_or_after_cutoff'])} | {route['status']} | {route['error'] or '-'} |")
    lines += ["", "| Raw transaction gap | Detail | Method | Error |", "| --- | --- | --- | --- |"]
    for detail in cov["transaction_gap_details"]:
        lines.append(f"| {detail['txhash']} | {detail['status']} | {detail['method'] or '-'} | {detail['error'] or '-'} |")
    lines += ["", "## Gameplay observation restart", "", f"Suggested date: **{game['suggested_new_observation_date_philippines']}**.", "",
              "| Saved source | Latest date |", "| --- | --- |"]
    for table, value in game["latest_saved_dates"].items():
        lines.append(f"| {table} | {value or 'UNKNOWN'} |")
    lines += ["", game["instruction"], "", "Chain/explorer evidence is a read-only review. No candidate hashes or ownership changes were imported or classified.",
              "Verified finance totals: **UNKNOWN**. Unified Finance: **HOLD**. Checkpoint 96: **OPEN**.", "",
              f"Production database: READ ONLY | Writes: 0 | RPC HTTP 400 batch fallbacks: {r['rpc_batch_400_fallbacks']} | Network calls attempted: {r['network_calls_attempted']}", ""]
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=DB)
    p.add_argument("--output-dir", type=Path, default=OUT)
    p.add_argument("--max-pages", type=int, default=8)
    p.add_argument("--timeout", type=int, default=15)
    args = p.parse_args()
    require(1 <= args.max_pages <= 20 and 1 <= args.timeout <= 30, "limits outside bounded range")
    local = local_sources(args.db)
    client = Net(args.timeout)
    report = build_report(local, client, args.max_pages)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V015_Source_Catchup_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    jp.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    mp.write_text(markdown(report), encoding="utf-8")
    inv, cov = report["owned_inventory"], report["wallet_coverage"]
    print("AXIEOS V0.15 - SOURCE CATCH-UP REVIEW")
    print(f"Saved/chain Axies: {inv['saved_owned_rows']}/{inv['chain_owned_count'] if inv['chain_owned_count'] is not None else 'UNKNOWN'} | Ownership: {inv['status']}")
    print(f"Wallet routes complete: {sum(r['status'] in ('REACHED_LOCAL_CUTOFF', 'EXPLORER_PAGINATION_END') for r in cov['routes'])}/4 | Raw transaction/transfer hash gaps: {len(cov['transaction_hashes_at_or_after_cutoff_absent_from_raw'])}/{len(cov['transfer_hashes_at_or_after_cutoff_absent_from_raw'])}")
    print(f"Reports: {jp} {mp}")
    print(f"Production database: READ ONLY | Writes: 0 | Network calls attempted: {client.calls}")
    print(f"RPC HTTP 400 batch fallbacks: {client.batch_400_fallbacks}")
    print("Finance totals: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
