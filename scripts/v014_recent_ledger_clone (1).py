r"""Task136AY: guarded ledger rehearsal for the post-October-22 raw cohort.

From the AxieOS repository root:
    py -B .\scripts\v014_recent_ledger_clone.py

Reads production in mode=ro and the Task136AX/AU evidence. Quarantines entire
hashes with ambiguous or invalid transfers. Inserts remaining proposed ledger
rows only into a disposable clone, then deletes it. Fee remains NULL, and a
transfer without a raw transaction keeps NULL status. No finance acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from v013_fullrow_materialization_sandbox import (
    get_transfers, human_amount, source_hash, utc_datetime,
)
from v014_cache_cohort_materialization_sandbox import (
    LEDGER_FIELDS, rehearse,
)
from v014_post_apply_reconcile import connect_ro, require
from v014_raw_import_clone import by_sha, latest, load


def validate_sources(ax: dict, au: dict, aw: dict, af: dict, shas: dict) -> None:
    require(all(doc.get("task") == task and doc.get("checkpoint96") == "OPEN" and
                doc.get("accepted_financial_totals") is None
                for task, doc in (("136AX", ax), ("136AU", au), ("136AW", aw), ("136AF", af))),
            "source task or financial boundary differs")
    require(aw.get("mode") == "APPLIED" and
            ax["source_applied_sha256"] == shas["136AW"] and
            ax["sources"]["136AU"]["sha256"] == shas["136AU"] and
            ax["coverage"]["exact_inserted_transactions"] ==
                au["coverage"]["unique_transaction_rows"] and
            ax["coverage"]["exact_inserted_transfers"] ==
                au["coverage"]["unique_transfer_rows"] and
            ax["coverage"]["preexisting_raw_rows_preserved"] is True and
            ax["coverage"]["integrity_check"] == "ok" and
            ax["coverage"]["protected_tables_equal_backup"] == 7 and
            aw["result"]["raw_after"] == ax["coverage"]["raw_after"],
            "post-apply source chain or raw reconciliation differs")


def plan(conn, ax: dict, au: dict, af: dict) -> tuple[list[tuple], list[dict], dict]:
    counts = ax["coverage"]["raw_after"]
    require(all(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == counts[table]
                for table in ("ronin_api_transactions_raw", "ronin_token_transfers_raw")) and
            conn.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0] ==
                af["coverage"]["ledger_after"],
            "production raw or ledger counts changed since reconciliation")
    wallets = conn.execute("SELECT address,wallet_role FROM ronin_wallet_registry "
                           "WHERE ownership_type='USER_OWNED'").fetchall()
    primary = {str(addr).lower() for addr, role in wallets
               if str(role).upper() == "PRIMARY"}
    require(len(primary) == 1, "expected exactly one registered PRIMARY wallet")
    wallet = next(iter(primary))
    expected_tx = {str(r["tx_hash"]).lower(): r for r in au["normalized_new_transactions"]}
    expected_transfers = {str(r["transfer_key"]).lower(): r
                          for r in au["normalized_new_transfers"]}
    require(len(expected_tx) == len(au["normalized_new_transactions"]) ==
            ax["coverage"]["exact_inserted_transactions"] and
            len(expected_transfers) == len(au["normalized_new_transfers"]) ==
            ax["coverage"]["exact_inserted_transfers"],
            "Task136AU new raw identities differ")
    transfer_hashes = {str(r["tx_hash"]).lower()
                       for r in expected_transfers.values()}
    raw_tx = {str(h).lower(): {"method": method, "status": status}
              for h, method, status in conn.execute(
                  "SELECT tx_hash,method,status FROM ronin_api_transactions_raw")
              if str(h).lower() in set(expected_tx) | transfer_hashes}
    older_tx = set(raw_tx) - set(expected_tx)
    require(set(expected_tx).issubset(raw_tx) and
            all(raw_tx[h]["method"] == r.get("method") and
                raw_tx[h]["status"] == r.get("status")
                for h, r in expected_tx.items()),
            "Task136AU transaction methods/statuses differ from production")
    joined = {str(row[0]).lower(): row for row in get_transfers(conn)
              if str(row[0]).lower() in expected_transfers}
    require(len(joined) == len(expected_transfers) and
            set(joined) == set(expected_transfers),
            "Task136AU raw transfer keys missing or duplicated")
    existing_sources = {str(r[0]) for r in conn.execute(
        "SELECT source_row_hash FROM blockchain_transactions WHERE source_row_hash IS NOT NULL")}
    existing_hashes = {str(r[0]).lower() for r in conn.execute(
        "SELECT DISTINCT txhash FROM blockchain_transactions WHERE txhash IS NOT NULL")}
    account_hashes = {str(r[0]).lower() for r in conn.execute(
        "SELECT DISTINCT txhash FROM blockchain_accounting_records WHERE txhash IS NOT NULL")}
    groups = defaultdict(lambda: {"rows": [], "reasons": set(), "keys": []})
    for key, source in sorted(expected_transfers.items()):
        t = joined[key]
        (transfer_key, h, log_index, stamp, block, sender, recipient,
         token_type, symbol, name, contract, token_id,
         raw_amount, decimals, method) = t
        h = str(h).lower()
        group = groups[h]
        group["keys"].append(transfer_key)
        expected = (source["tx_hash"].lower(), source["log_index"], source["timestamp"],
                    source["block_number"], source["from_address"].lower(),
                    source["to_address"].lower(), source["token_type"],
                    source["token_symbol"], source["token_name"],
                    source["token_address"].lower(),
                    str(source["token_id"]) if source["token_id"] is not None else None,
                    str(source["amount_raw"]),
                    int(source["decimals"]) if source["decimals"] is not None else None)
        actual = (h, log_index, stamp, block, str(sender).lower(),
                  str(recipient).lower(), token_type, symbol, name,
                  str(contract).lower(), token_id, raw_amount, decimals)
        columns = ("tx_hash", "log_index", "timestamp", "block_number",
                   "from_address", "to_address", "token_type", "token_symbol",
                   "token_name", "token_address", "token_id", "amount_raw", "decimals")
        differences = [field for field, live, saved in zip(columns, actual, expected)
                       if live != saved]
        if str(transfer_key) != source["transfer_key"]:
            differences.append("transfer_key")
        require(not differences,
                f"{key}: live raw transfer differs in {differences}")
        if h in existing_hashes or h in account_hashes or source_hash(transfer_key) in existing_sources:
            group["reasons"].add("PREEXISTING_LEDGER_OR_ACCOUNTING")
        if h in older_tx:
            group["reasons"].add("OLDER_RAW_TRANSACTION_FOR_NEW_TRANSFER")
        sender_is_primary, recipient_is_primary = (
            str(sender).lower() == wallet, str(recipient).lower() == wallet)
        if sender_is_primary == recipient_is_primary:
            group["reasons"].add("NOT_SINGLE_PRIMARY_WALLET_DIRECTION")
        if not name:
            group["reasons"].add("MISSING_ASSET_NAME")
        try:
            unix_ts, ledger_dt = utc_datetime(stamp)
            amount = human_amount(raw_amount, decimals)
            if Decimal(amount) <= 0:
                group["reasons"].add("ZERO_OR_INVALID_AMOUNT")
        except (ValueError, TypeError, OverflowError):
            group["reasons"].add("INVALID_AMOUNT_OR_TIMESTAMP")
            continue
        transaction = raw_tx.get(h)
        if transaction and str(transaction["status"]).lower() != "ok":
            group["reasons"].add("RAW_TRANSACTION_NOT_OK")
        if transaction and method != transaction["method"]:
            group["reasons"].add("JOINED_METHOD_DIFFERS")
        inbound = recipient_is_primary and not sender_is_primary
        ledger_row = (h, block, unix_ts, ledger_dt, sender, recipient,
                      method, name, amount if inbound else "0.0",
                      "0.0" if inbound else amount, None,
                      "Success" if transaction and str(transaction["status"]).lower() == "ok"
                      else None, source_hash(transfer_key))
        group["rows"].append(ledger_row)
    selected = []
    quarantine = []
    for h, group in sorted(groups.items()):
        if len(group["rows"]) != len(group["keys"]):
            group["reasons"].add("PARTIAL_HASH_ROWS")
        if group["reasons"]:
            quarantine.append({"txhash": h, "transfer_keys": group["keys"],
                               "reasons": sorted(group["reasons"])})
        else:
            selected.extend(group["rows"])
    require(len(selected) + sum(len(r["transfer_keys"]) for r in quarantine) ==
            len(expected_transfers) and len({r[-1] for r in selected}) == len(selected) and
            all(r[10] is None and r[11] in (None, "Success") for r in selected),
            "guarded/held transfer partition or unknown gas/status differs")
    require(selected, "no guarded full ledger rows; inspect quarantine")
    observed_hashes = set(expected_tx) | set(groups)
    require(len(observed_hashes) == ax["coverage"]["new_unique_hashes_across_raw_tables"],
            "Task136AX union hash count differs")
    summary = {"new_raw_transaction_hashes": len(expected_tx),
               "new_raw_transfer_hashes": len(groups),
               "new_unique_raw_hashes": len(observed_hashes),
               "new_transfer_only_hashes": len(set(groups) - set(expected_tx)),
               "new_transfer_hashes_with_older_transaction_row": len(older_tx),
               "new_transfer_hashes_with_no_transaction_row":
                   len(set(groups) - set(expected_tx) - older_tx),
               "new_transaction_only_hashes": len(set(expected_tx) - set(groups)),
               "guarded_rows": len(selected),
               "guarded_hashes": len({r[0] for r in selected}),
               "quarantined_rows": sum(len(r["transfer_keys"]) for r in quarantine),
               "quarantined_hashes": len(quarantine),
               "no_accounting_or_economic_acceptance": True}
    require(summary["new_transfer_only_hashes"] ==
            ax["coverage"]["new_transfer_hashes_without_new_transaction_row"],
            "Task136AX transfer-only hash count differs")
    return selected, quarantine, summary


def markdown(report: dict) -> str:
    c, s = report["coverage"], report["sandbox"]
    return "\n".join([
        "# AxieOS V0.14 — Task136AY Recent raw cohort ledger clone", "",
        f"New raw hashes: **{c['new_unique_raw_hashes']}**; transaction-only: "
        f"**{c['new_transaction_only_hashes']}**; transfer-only: "
        f"**{c['new_transfer_only_hashes']}**.", "",
        f"Guarded ledger rows/hashes: **{c['guarded_rows']}/{c['guarded_hashes']}**. "
        f"Quarantined rows/hashes: **{c['quarantined_rows']}/{c['quarantined_hashes']}**. "
        f"Clone first/second inserts: **{s['clone_rows_first_pass']}/"
        f"{s['clone_rows_second_pass']}**.", "",
        "Unverified gas remains NULL. Transfer-only hashes retain NULL status. "
        "The JSON keeps the guarded plan and quarantine reasons for review. "
        "No income, expense, basis, profit or recovery is accepted.", "",
        "Verified financial totals: **UNKNOWN**. Checkpoint 96: **OPEN**.", "",
        "Production read only | Production writes: 0 | Clone deleted | Network: 0", ""])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--ax", type=Path)
    parser.add_argument("--ax-dir", type=Path, default=Path("reports/axieos_v014/task136ax"))
    parser.add_argument("--au-dir", type=Path, default=Path("reports/axieos_v014/task136au"))
    parser.add_argument("--aw-dir", type=Path, default=Path("reports/axieos_v014/task136aw"))
    parser.add_argument("--af-dir", type=Path, default=Path("reports/axieos_v014/task136af"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136ay"))
    args = parser.parse_args()
    ap = args.ax or latest(args.ax_dir, "136AX")
    ax, ax_sha = load(ap)
    up = by_sha(args.au_dir, ax["sources"]["136AU"]["sha256"], "136AU")
    wp = by_sha(args.aw_dir, ax["sources"]["136AW"]["sha256"], "136AW")
    fp = latest(args.af_dir, "136AF")
    au, au_sha = load(up)
    aw, aw_sha = load(wp)
    af, af_sha = load(fp)
    validate_sources(ax, au, aw, af,
                     {"136AX": ax_sha, "136AU": au_sha, "136AW": aw_sha, "136AF": af_sha})
    with closing(connect_ro(args.db)) as conn:
        conn.execute("BEGIN")
        safe, quarantine, coverage = plan(conn, ax, au, af)
        sandbox = rehearse(conn, safe)
    report = {"project": "AxieOS", "version": "0.14", "task": "136AY",
              "sources": {"136AX": {"filename": ap.name, "sha256": ax_sha},
                          "136AU": {"filename": up.name, "sha256": au_sha},
                          "136AW": {"filename": wp.name, "sha256": aw_sha},
                          "136AF": {"filename": fp.name, "sha256": af_sha}},
              "coverage": coverage,
              "guarded_ledger_rows": [dict(zip(LEDGER_FIELDS, row)) for row in safe],
              "quarantined": quarantine, "sandbox": sandbox,
              "accepted_financial_totals": None,
              "production_database_opened_read_only": True,
              "production_database_writes": 0, "clone_deleted": True,
              "network_calls": 0, "checkpoint96": "OPEN",
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AY_Recent_Ledger_Clone_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136AY - RECENT LEDGER CLONE")
    print(f"New raw hashes: {c['new_unique_raw_hashes']} | Transaction-only: "
          f"{c['new_transaction_only_hashes']} | Transfer-only: {c['new_transfer_only_hashes']}")
    print(f"Guarded rows/hashes: {c['guarded_rows']}/{c['guarded_hashes']} | "
          f"Quarantined rows/hashes: {c['quarantined_rows']}/{c['quarantined_hashes']}")
    print(f"Clone inserts first/second: {sandbox['clone_rows_first_pass']}/"
          f"{sandbox['clone_rows_second_pass']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Production read only | Writes: 0 | Clone: deleted | Network: 0")
    print("VALIDATION: PASS (recent ledger clone only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
