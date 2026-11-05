r"""AxieOS V0.15: one-run ownership review and raw transaction clone rehearsal.

Save as scripts/AxieOS_V015_Source_Reconciliation.py. From the repository root:
    py -B .\scripts\AxieOS_V015_Source_Reconciliation.py

Uses the exact November 5 pinned source report, local SQLite in read-only mode,
and three public explorer transaction details. Produces JSON, Markdown and a
32-row Axie review CSV. Raw transactions are inserted twice into a disposable
clone only. No production writes, accounting, or financial totals.
"""

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import HTTPRedirectHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data/blockchain/database/axieos.db"
DEFAULT_SOURCE_DIR = ROOT / "reports/axieos_v015/source_catchup"
DEFAULT_OUTPUT = DEFAULT_SOURCE_DIR
SOURCE_SHA256 = "32260f4e5b7472a3b2c5c8d3c07ebe5664cf051cd70d8126d8fdd893551550fa"
TX_FIELDS = ("tx_hash", "timestamp", "block_number", "from_address", "to_address",
             "method", "status", "value_raw", "fee_raw", "gas_used")
WATCHED = ("ronin_api_transactions_raw", "ronin_token_transfers_raw",
           "blockchain_transactions", "blockchain_accounting_records",
           "blockchain_economic_events", "blockchain_transaction_classifications",
           "blockchain_transaction_intelligence", "staking_reward_events",
           "gameplay_owned_axies")
WALLETS = {"0x1ed8b3f3bd6a624de47f81beea101f0d15cdfbc8",
           "0x5c32ce3b21e786dcaf11d9c64dec31b21a2c6610"}


def require(condition, message):
    if not condition:
        raise ValueError("STOP: " + message)


def valid_hash(value):
    return isinstance(value, str) and re.fullmatch(r"0x[0-9a-f]{64}", value) is not None


def valid_address(value):
    return isinstance(value, str) and re.fullmatch(r"0x[0-9a-f]{40}", value) is not None


def iso_utc(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "timezone missing")
    return parsed.astimezone(timezone.utc)


def load_source(path):
    require(path.is_file(), f"catch-up report missing: {path}")
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    require(digest == SOURCE_SHA256, "catch-up report SHA-256 differs from pinned November 5 report")
    source = json.loads(content.decode("utf-8-sig"))
    inv, cov = source["owned_inventory"], source["wallet_coverage"]
    require(source.get("version") == "0.15" and source.get("task") == "SOURCE_CATCHUP"
            and inv["status"] == "COMPLETE_AT_PINNED_BLOCK"
            and cov["all_routes_reached_cutoff_or_end"] is True
            and source["database_writes"] == 0 and source["finance"]["verified_totals"] == "UNKNOWN",
            "source coverage or financial boundary differs")
    require(inv["block"] == "0x3c43185" and
            iso_utc(inv["block_timestamp_utc"]).isoformat() == "2026-11-05T02:59:09+00:00" and
            set(inv["wallet_balances"]) == WALLETS and sum(inv["wallet_balances"].values()) == 162,
            "pinned block or wallet counts differ")
    require(len(inv["chain_only_ids"]) == 29 and len(inv["saved_only_ids"]) == 3 and
            inv["saved_owned_rows"] == 136 and inv["chain_owned_count"] == 162 and
            len(cov["transaction_gap_details"]) == 3 and
            not cov["transfer_hashes_at_or_after_cutoff_absent_from_raw"],
            "snapshot inventory or raw gap counts differ")
    gaps = cov["transaction_hashes_at_or_after_cutoff_absent_from_raw"]
    require(set(gaps) == {d["txhash"] for d in cov["transaction_gap_details"]} and
            all(valid_hash(h) for h in gaps), "source transaction identities differ")
    return source, digest


def open_ro(db):
    require(db.is_file(), f"database missing: {db}")
    conn = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    conn.execute("PRAGMA query_only=ON")
    return conn


def table_columns(conn, name):
    require(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone(),
            f"required table absent: {name}")
    return {r[1] for r in conn.execute(f"PRAGMA table_info({name})")}


def snapshot_table(conn, table, omit_hashes=()):
    sha, count = hashlib.sha256(), 0
    cursor = conn.execute("SELECT * FROM " + table + " ORDER BY rowid")
    index = [field[0] for field in cursor.description].index("tx_hash") if omit_hashes else None
    for row in cursor:
        if index is not None and str(row[index]).lower() in omit_hashes:
            continue
        sha.update(repr(row).encode("utf-8"))
        sha.update(b"\n")
        count += 1
    return {"rows": count, "sha256": sha.hexdigest()}


def roster_review(conn, source):
    inv = source["owned_inventory"]
    require({"axie_id", "ownership_status", "wallet_address"} <= table_columns(conn, "gameplay_owned_axies"),
            "saved Axie schema differs")
    ids = set(inv["chain_only_ids"] + inv["saved_only_ids"])
    require(len(ids) == 32 and all(x.isdecimal() and int(x) > 0 for x in ids),
            "Axie ID set differs")
    saved = {str(r[0]) for r in conn.execute(
        "SELECT axie_id FROM gameplay_owned_axies WHERE ownership_status='OWNED' AND axie_id IS NOT NULL")}
    require(len(saved) == inv["saved_owned_rows"] and
            set(inv["saved_only_ids"]) <= saved and not set(inv["chain_only_ids"]) & saved and
            len(saved) - len(inv["saved_only_ids"]) + len(inv["chain_only_ids"]) == inv["chain_owned_count"],
            "live saved OWNED roster differs from pinned snapshot")
    rows = []
    for axie_id in sorted(ids, key=int):
        saved_row = conn.execute("SELECT ownership_status,wallet_address,axie_class,level,breed_count,"
                                 "acquisition_txhash,acquisition_datetime,acquisition_cost_weth,"
                                 "last_seen_datetime,data_source FROM gameplay_owned_axies WHERE axie_id=?",
                                 (axie_id,)).fetchone()
        lane = "CHAIN_ONLY" if axie_id in inv["chain_only_ids"] else "SAVED_ONLY"
        rows.append({"axie_id": axie_id, "lane": lane,
                     "pinned_chain_owner": next((w for w, n in inv["wallet_balances"].items() if n > 0), "UNKNOWN")
                         if lane == "CHAIN_ONLY" else "NOT_IN_TWO_CHECKED_WALLETS",
                     "saved_ownership_status": saved_row[0] if saved_row else None,
                     "saved_wallet": saved_row[1] if saved_row else None,
                     "saved_class": saved_row[2] if saved_row else None,
                     "saved_level": saved_row[3] if saved_row else None,
                     "saved_breed_count": saved_row[4] if saved_row else None,
                     "saved_acquisition_txhash": saved_row[5] if saved_row else None,
                     "saved_acquisition_datetime": saved_row[6] if saved_row else None,
                     "saved_acquisition_cost_weth": saved_row[7] if saved_row else None,
                     "saved_last_seen": saved_row[8] if saved_row else None,
                     "saved_data_source": saved_row[9] if saved_row else None,
                     "review_status": "METADATA_AND_LIFECYCLE_REVIEW" if lane == "CHAIN_ONLY"
                         else "LIFECYCLE_REASON_UNRESOLVED",
                     "production_update_approved": False})
    return rows


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("STOP: explorer redirected")


def explorer_detail(opener, txhash):
    url = "https://explorer.roninchain.com/api/v2/transactions/" + txhash
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "AxieOS-V015-Source-Reconciliation/1"})
    with opener.open(request, timeout=20) as response:
        require(response.status == 200 and response.geturl() == url and
                "json" in response.headers.get("Content-Type", "").lower(), "explorer response invalid")
        body = response.read(2_000_001)
    require(len(body) <= 2_000_000, "explorer response too large")
    return json.loads(body)


def raw_candidate(detail, doc):
    h = detail["txhash"]
    require(isinstance(doc, dict) and str(doc.get("hash", "")).lower() == h,
            f"{h}: explorer hash differs")
    at = iso_utc(doc.get("timestamp"))
    require(at == iso_utc(detail["timestamp"]) and
            type(doc.get("block_number")) is int and doc["block_number"] == detail["block_number"] and
            doc.get("method") == detail["method"] and doc.get("status") == detail["chain_status"],
            f"{h}: explorer time, block, method, or status differs")
    fee = doc.get("fee")
    fee = fee.get("value") if isinstance(fee, dict) else fee
    gas = doc.get("gas_used")
    require(str(fee) == str(detail["fee_raw"]["value"]) and
            str(gas) == str(detail["gas_used"]) and str(fee).isdecimal() and str(gas).isdecimal(),
            f"{h}: explorer raw fee or gas differs")
    sender, recipient = doc.get("from"), doc.get("to")
    sender = sender.get("hash") if isinstance(sender, dict) else sender
    recipient = recipient.get("hash") if isinstance(recipient, dict) else recipient
    sender, recipient = str(sender).lower(), str(recipient).lower()
    value = doc.get("value")
    require(valid_address(sender) and valid_address(recipient) and
            sender in WALLETS and str(value).isdecimal(),
            f"{h}: sender, recipient, or raw value invalid")
    return (h, doc["timestamp"], doc["block_number"], sender, recipient,
            doc["method"], doc["status"], str(value), str(fee), int(gas))


def rehearse(conn, source, fetch):
    require(set(TX_FIELDS) <= table_columns(conn, "ronin_api_transactions_raw"), "raw transaction schema differs")
    for table in WATCHED:
        table_columns(conn, table)
    require(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
            not conn.execute("PRAGMA foreign_key_check").fetchall(), "production SQLite integrity failed")
    details = source["wallet_coverage"]["transaction_gap_details"]
    candidate_rows = []
    for detail in details:
        require(detail["status"] == "CORROBORATED_DETAIL" and detail["chain_status"] == "ok",
                "saved transaction detail incomplete")
        candidate_rows.append(raw_candidate(detail, fetch(detail["txhash"])))
    hashes = {r[0] for r in candidate_rows}
    require(len(hashes) == 3, "transaction detail duplicates")
    watched_before = {t: snapshot_table(conn, t) for t in WATCHED}
    present = []
    missing = []
    for row in candidate_rows:
        stored = conn.execute("SELECT " + ",".join(TX_FIELDS) +
                              " FROM ronin_api_transactions_raw WHERE lower(tx_hash)=?", (row[0],)).fetchall()
        require(len(stored) <= 1, f"{row[0]}: multiple stored raw rows")
        if stored:
            require(tuple(stored[0]) == row, f"{row[0]}: stored raw row conflicts with explorer")
            present.append(row)
        else:
            missing.append(row)
    insert = ("INSERT OR IGNORE INTO ronin_api_transactions_raw (" + ",".join(TX_FIELDS) +
              ") VALUES (" + ",".join("?" for _ in TX_FIELDS) + ")")
    with tempfile.TemporaryDirectory(prefix="axieos_v015_source_reconcile_") as temp:
        with closing(sqlite3.connect(Path(temp) / "clone.db")) as clone:
            conn.backup(clone)
            require({t: snapshot_table(clone, t) for t in WATCHED} == watched_before,
                    "clone baseline differs")
            clone.execute("PRAGMA foreign_keys=ON")
            before = clone.total_changes
            clone.executemany(insert, missing)
            first = clone.total_changes - before
            clone.commit()
            before = clone.total_changes
            clone.executemany(insert, missing)
            second = clone.total_changes - before
            clone.commit()
            require(first == len(missing) and second == 0, "clone insert count or idempotence differs")
            for row in candidate_rows:
                stored = clone.execute("SELECT " + ",".join(TX_FIELDS) +
                                       " FROM ronin_api_transactions_raw WHERE tx_hash=?", (row[0],)).fetchone()
                require(tuple(stored or ()) == row, f"{row[0]}: clone row differs")
            require(snapshot_table(clone, WATCHED[0], {r[0] for r in missing}) == watched_before[WATCHED[0]] and
                    all(snapshot_table(clone, t) == watched_before[t] for t in WATCHED[1:]) and
                    clone.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                    not clone.execute("PRAGMA foreign_key_check").fetchall(),
                    "clone protected rows or integrity differs")
    require({t: snapshot_table(conn, t) for t in WATCHED} == watched_before,
            "production changed during rehearsal")
    plan = [dict(zip(TX_FIELDS, row)) for row in sorted(missing)]
    return {"already_present_exact": len(present), "missing_rehearsed": len(missing),
            "clone_first_pass": first, "clone_second_pass": second,
            "plan_sha256": hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":"))
                                      .encode("utf-8")).hexdigest(),
            "candidate_raw_transaction_rows": plan,
            "production_raw_rows": watched_before["ronin_api_transactions_raw"]["rows"],
            "production_ledger_rows": watched_before["blockchain_transactions"]["rows"],
            "protected_tables_unchanged": len(WATCHED) - 1,
            "production_writes": 0, "clone_deleted": True}


def render_md(report):
    review, raw = report["roster_review"], report["raw_transaction_rehearsal"]
    lines = ["# AxieOS V0.15 source reconciliation", "",
             f"Pinned source: `{report['source']['filename']}` | SHA-256 `{report['source']['sha256']}`",
             f"Pinned block: `{report['source']['block']}` at {report['source']['block_timestamp_utc']}", "",
             f"Roster review: **{sum(r['lane'] == 'CHAIN_ONLY' for r in review)} chain-only**, "
             f"**{sum(r['lane'] == 'SAVED_ONLY' for r in review)} saved-only**. "
             "The CSV contains saved metadata and review status for each ID. Ownership is observed at one block; "
             "no lifecycle or acquisition reason is inferred.", "",
             "| Saved-only Axie | Last saved observation | Saved acquisition hash | Status |",
             "| --- | --- | --- | --- |"]
    for row in review:
        if row["lane"] == "SAVED_ONLY":
            lines.append(f"| {row['axie_id']} | {row['saved_last_seen'] or 'UNKNOWN'} | "
                         f"{row['saved_acquisition_txhash'] or 'UNKNOWN'} | {row['review_status']} |")
    lines += ["", "## Raw transaction rehearsal", "",
              f"Exact rows already present: **{raw['already_present_exact']}**; missing: "
              f"**{raw['missing_rehearsed']}**. Clone first/second inserts: "
              f"**{raw['clone_first_pass']}/{raw['clone_second_pass']}**. "
              f"Plan SHA-256: `{raw['plan_sha256']}`.", "",
              "The explorer detail was fetched again and checked against the pinned report. "
              "The proposed rows are included in the JSON. Raw fees are evidence, not accepted expenses.", "",
              "Production database: **READ ONLY** | Writes: **0** | "
              f"Network detail calls: **{report['network_calls']}** | Temporary clone: deleted.",
              "Verified income, expenses, profit and PHP recovery: **UNKNOWN**. "
              "Unified Finance: **HOLD**. Checkpoint 96: **OPEN**.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--source", type=Path,
                        default=DEFAULT_SOURCE_DIR / "AxieOS_V015_Source_Catchup_20261105T030132_927019Z.json")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source, digest = load_source(args.source)
    opener = build_opener(NoRedirect())
    calls = 0

    def fetch(txhash):
        nonlocal calls
        calls += 1
        return explorer_detail(opener, txhash)

    with closing(open_ro(args.db)) as conn:
        conn.execute("BEGIN")
        review = roster_review(conn, source)
        raw = rehearse(conn, source, fetch)
    report = {"version": "0.15", "task": "SOURCE_RECONCILIATION",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "source": {"filename": args.source.name, "sha256": digest,
                         "block": source["owned_inventory"]["block"],
                         "block_timestamp_utc": source["owned_inventory"]["block_timestamp_utc"]},
              "roster_review": review, "raw_transaction_rehearsal": raw,
              "network_calls": calls, "production_database": "READ_ONLY",
              "database_writes": 0, "verified_financial_totals": "UNKNOWN",
              "unified_finance": "HOLD", "checkpoint96": "OPEN"}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V015_Source_Reconciliation_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    jp, mp, cp = [args.output_dir / (stem + ext) for ext in (".json", ".md", ".csv")]
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    mp.write_text(render_md(report), encoding="utf-8")
    with cp.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(review[0]))
        writer.writeheader()
        writer.writerows(review)
    print("AXIEOS V0.15 - SOURCE RECONCILIATION")
    print(f"Axie review: 29 chain-only / 3 saved-only | Raw transaction clone: "
          f"{raw['clone_first_pass']}/{raw['clone_second_pass']} inserts")
    print(f"Reports: {jp} {mp} {cp}")
    print("Production read only | Writes: 0 | Network detail calls: " + str(calls))
    print("Financial totals: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
