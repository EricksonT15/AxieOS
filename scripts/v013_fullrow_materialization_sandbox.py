"""AxieOS V0.13 Task 135C — complete ledger-row disposable rehearsal.

SAFETY
------
* Opens the original database using SQLite mode=ro and PRAGMA query_only=ON.
* Copies it with sqlite3.Connection.backup() to a temporary directory.
* Writes full proposed ledger rows ONLY into the disposable copy.
* Never imports, executes, or modifies ronin_api_sync.py.
* Does not run accounting, classification, economics, marketplace, or network sync.
* Deletes the temporary database automatically.

LIMITATIONS
-----------
This independently reproduces the *observed* legacy ledger-row field mapping,
not the uninspected implementation of convert_api_timestamp(). Timestamps are
converted to UTC. Reconciliation against historical ledger timestamps is
reported, not assumed. Successful validation is NOT production authorization.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

DEFAULT_DB = Path("data/blockchain/database/axieos.db")
HASH_PREFIX = "ronin_api_transfer|"
PROTECTED_TABLES = (
    "blockchain_accounting_records",
    "blockchain_economic_events",
    "blockchain_transaction_classifications",
    "blockchain_transaction_intelligence",
    "staking_reward_events",
    "gameplay_owned_axies",
)


def readonly_connect(db: Path) -> sqlite3.Connection:
    resolved = db.expanduser().resolve(strict=True)
    conn = sqlite3.connect(f"{resolved.as_uri()}?mode=ro", uri=True)
    conn.execute("PRAGMA query_only=ON")
    return conn


def source_hash(transfer_key: object) -> str:
    return hashlib.sha256((HASH_PREFIX + str(transfer_key)).encode("utf-8")).hexdigest()


def utc_datetime(raw: str) -> tuple[int, str]:
    parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Raw timestamp lacks UTC offset: {raw!r}")
    utc = parsed.astimezone(timezone.utc)
    return int(utc.timestamp()), utc.strftime("%Y-%m-%d %H:%M:%S")


def human_amount(amount_raw: object, decimals: object) -> str:
    if amount_raw is None:
        raise ValueError("Missing amount_raw")
    raw = Decimal(str(amount_raw))
    if not raw.is_finite() or raw < 0 or raw != raw.to_integral_value():
        raise ValueError(f"Invalid amount_raw: {amount_raw!r}")
    if decimals is None:
        return str(amount_raw)
    scale = int(decimals)
    if scale < 0 or scale > 255:
        raise ValueError(f"Invalid decimals: {decimals}")
    return format(raw / (Decimal(10) ** scale), "f")


def get_transfers(conn: sqlite3.Connection) -> list[tuple]:
    # Use the legacy materializer's exact LEFT JOIN condition.
    return conn.execute(
        """
        SELECT t.transfer_key, t.tx_hash, t.log_index, t.timestamp,
               t.block_number, t.from_address, t.to_address,
               t.token_type, t.token_symbol, t.token_name,
               t.token_address, t.token_id, t.amount_raw, t.decimals,
               x.method
        FROM ronin_token_transfers_raw AS t
        LEFT JOIN ronin_api_transactions_raw AS x ON t.tx_hash = x.tx_hash
        ORDER BY t.block_number, t.log_index, t.transfer_key
        """
    ).fetchall()


def proposed_rows(conn: sqlite3.Connection) -> tuple[list[tuple], Counter, Counter]:
    wallet_rows = conn.execute(
        "SELECT address FROM ronin_wallet_registry "
        "WHERE ownership_type='USER_OWNED' AND wallet_role='PRIMARY'"
    ).fetchall()
    if len(wallet_rows) != 1:
        raise RuntimeError(f"Expected one PRIMARY user-owned wallet; got {len(wallet_rows)}")
    primary = wallet_rows[0][0].lower()
    prepared: list[tuple] = []
    method_counts: Counter = Counter()
    type_counts: Counter = Counter()
    keys: set[str] = set()
    for t in get_transfers(conn):
        (transfer_key, txhash, log_index, raw_ts, block, from_addr, to_addr,
         token_type, token_symbol, token_name, token_address, token_id,
         amount_raw, decimals, method) = t
        sender = from_addr.lower() if from_addr else ""
        receiver = to_addr.lower() if to_addr else ""
        if sender == primary and receiver == primary:
            continue
        if receiver == primary:
            direction = "IN"
        elif sender == primary:
            direction = "OUT"
        else:
            continue
        h = source_hash(transfer_key)
        if h in keys:
            raise RuntimeError(f"Duplicate materialization source hash for {transfer_key}")
        keys.add(h)
        unix_ts, ledger_dt = utc_datetime(raw_ts)
        amount = human_amount(amount_raw, decimals)
        in_amount, out_amount = (amount, "0.0") if direction == "IN" else ("0.0", amount)
        prepared.append((
            txhash, block, unix_ts, ledger_dt, from_addr, to_addr,
            method, token_name, in_amount, out_amount, "0.0", "Success", h,
        ))
        method_counts["present" if method is not None else "absent"] += 1
        type_counts[(token_type or "UNKNOWN", token_symbol or "UNKNOWN")] += 1
    return prepared, method_counts, type_counts


def table_fingerprint(conn: sqlite3.Connection, table: str) -> str:
    # Digest rows in stable rowid order.  Does not create any DB artifacts.
    digest = hashlib.sha256()
    for row in conn.execute(f"SELECT * FROM {table} ORDER BY rowid"):
        digest.update(repr(row).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    prod = readonly_connect(args.db)
    try:
        initial_count = prod.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
        protected_fingerprints = {t: table_fingerprint(prod, t) for t in PROTECTED_TABLES}
        baseline_ledger = table_fingerprint(prod, "blockchain_transactions")
        prepared, method_counts, type_counts = proposed_rows(prod)
        original_hashes = {h for (h,) in prod.execute(
            "SELECT source_row_hash FROM blockchain_transactions"
        )}
        missing_rows = [row for row in prepared if row[-1] not in original_hashes]
        present_rows = [row for row in prepared if row[-1] in original_hashes]
        if len(prepared) != len({row[-1] for row in prepared}):
            raise AssertionError("Prepared ledger hashes are not unique")

        # Check whether UTC timestamp conversion matches existing rows
        # materialized from the same raw transfer keys.
        existing = {r[0]: (r[1], r[2]) for r in prod.execute(
            "SELECT source_row_hash, unixtimestamp, datetime FROM blockchain_transactions"
        )}
        timestamp_unix_mismatch = sum(
            str(existing[r[-1]][0]) != str(r[2]) for r in present_rows
        )
        timestamp_datetime_mismatch = sum(
            str(existing[r[-1]][1]) != str(r[3]) for r in present_rows
        )

        with TemporaryDirectory(prefix="axieos_v013_fullrow_") as td:
            clone_path = Path(td) / "axieos_fullrow_sandbox.db"
            clone = sqlite3.connect(clone_path)
            try:
                prod.backup(clone)
                clone.execute("PRAGMA foreign_keys=ON")
                copied_count = clone.execute(
                    "SELECT COUNT(*) FROM blockchain_transactions"
                ).fetchone()[0]
                if copied_count != initial_count:
                    raise AssertionError("SQLite clone differs from original ledger count")

                insert_sql = """
                    INSERT OR IGNORE INTO blockchain_transactions
                    (txhash, blockno, unixtimestamp, datetime, from_address,
                     to_address, method, token_collectibles, value_in,
                     value_out, txn_fee_ron, status, source_row_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                before_first = clone.total_changes
                clone.executemany(insert_sql, prepared)
                first_added = clone.total_changes - before_first
                clone.commit()
                after_first = clone.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]

                before_second = clone.total_changes
                clone.executemany(insert_sql, prepared)
                second_added = clone.total_changes - before_second
                clone.commit()

                expected_count = initial_count + len(missing_rows)
                if first_added != len(missing_rows):
                    raise AssertionError(f"First pass inserted {first_added}; expected {len(missing_rows)}")
                if second_added != 0:
                    raise AssertionError(f"Second pass inserted {second_added}; expected 0")
                if after_first != expected_count:
                    raise AssertionError(f"Clone count {after_first} does not equal {expected_count}")
                if any(table_fingerprint(clone, t) != digest for t, digest in protected_fingerprints.items()):
                    raise AssertionError("A protected accounting/gameplay table changed in the clone")

                # Ensure pre-existing ledger rows are byte-for-byte untouched.
                clone.execute("CREATE TEMP TABLE _added_hashes (source_row_hash TEXT PRIMARY KEY)")
                clone.executemany("INSERT INTO _added_hashes VALUES (?)", ((r[-1],) for r in missing_rows))
                preserved = clone.execute(
                    "SELECT COUNT(*) FROM blockchain_transactions WHERE "
                    "source_row_hash NOT IN (SELECT source_row_hash FROM _added_hashes)"
                ).fetchone()[0]
                if preserved != initial_count:
                    raise AssertionError("Unexpected change in original ledger row population")
                clone_original_digest = hashlib.sha256()
                for row in clone.execute(
                    "SELECT * FROM blockchain_transactions WHERE "
                    "source_row_hash NOT IN (SELECT source_row_hash FROM _added_hashes) ORDER BY rowid"
                ):
                    clone_original_digest.update(repr(row).encode("utf-8"))
                    clone_original_digest.update(b"\n")
                if clone_original_digest.hexdigest() != baseline_ledger:
                    raise AssertionError("Existing ledger rows changed in clone")

                integrity = clone.execute("PRAGMA integrity_check").fetchone()[0]
                fk_errors = clone.execute("PRAGMA foreign_key_check").fetchall()
                if integrity != "ok" or fk_errors:
                    raise AssertionError(f"Clone validation failed: integrity={integrity}, fk={fk_errors}")
                # Check new data is populated rather than synthetic placeholders.
                newly_inserted_populated = clone.execute(
                    "SELECT COUNT(*) FROM blockchain_transactions WHERE "
                    "source_row_hash IN (SELECT source_row_hash FROM _added_hashes) "
                    "AND txhash IS NOT NULL AND blockno IS NOT NULL "
                    "AND unixtimestamp IS NOT NULL AND datetime IS NOT NULL "
                    "AND value_in IS NOT NULL AND value_out IS NOT NULL"
                ).fetchone()[0]
                if newly_inserted_populated != len(missing_rows):
                    raise AssertionError("Some proposed full-row inserts lack essential fields")
            finally:
                clone.close()

        final_count = prod.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
        if final_count != initial_count:
            raise AssertionError("Production ledger count changed unexpectedly")
        if any(table_fingerprint(prod, t) != digest for t, digest in protected_fingerprints.items()):
            raise AssertionError("Production protected table changed unexpectedly")

        print("AXIEOS V0.13 — TASK 135C | FULL LEDGER-ROW SANDBOX REHEARSAL")
        print("=" * 69)
        print(f"Raw eligible transfers:               {len(prepared)}")
        print(f"Full rows already represented:        {len(present_rows)}")
        print(f"Missing full ledger rows:             {len(missing_rows)}")
        print(f"With transaction method (all):       {method_counts['present']}")
        print(f"Without transaction method (all):    {method_counts['absent']}")
        print(f"Existing-hash UTC UNIX mismatches:    {timestamp_unix_mismatch}")
        print(f"Existing-hash UTC datetime mismatches:{timestamp_datetime_mismatch:>8}")
        print(f"Sandbox first-pass full-row inserts:  {first_added}")
        print(f"Sandbox second-pass inserts:         {second_added}")
        print(f"Sandbox ledger rows after test:       {after_first}")
        print(f"Original ledger rows preserved:      {preserved}")
        print(f"Protected accounting/gameplay:       UNCHANGED ({len(PROTECTED_TABLES)} tables)")
        print(f"Sandbox integrity check:             {integrity}")
        print(f"Sandbox foreign-key check:           {len(fk_errors)} violations")
        print(f"Production ledger before/after:      {initial_count} / {final_count}")
        print("RESULT: PASS — complete proposed ledger rows inserted into a disposable clone")
        print("LIMITATION: Independent UTC timestamp conversion; no classifications/economics run.")
        print("LIMITATION: No production writes, no network sync, no V0.7 compatibility approval.")
        if timestamp_unix_mismatch or timestamp_datetime_mismatch:
            print("WARNING: Existing ledger timestamp semantics differ from this rehearsal. Investigate before production refresh.")
    finally:
        prod.close()


if __name__ == "__main__":
    main()
