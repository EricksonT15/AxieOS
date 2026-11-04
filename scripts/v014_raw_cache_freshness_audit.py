r"""Task136AR: read-only freshness audit against the Task136W raw cache.

From the AxieOS repository root:
    py -B .\scripts\v014_raw_cache_freshness_audit.py

Compares the SHA-matched Task136W/AK snapshot with current raw transaction
and transfer tables for registered owned wallets. No API, accounting, import,
classification, or financial totals are run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from v014_post_apply_reconcile import connect_ro, require


def load(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing report: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def latest(directory: Path, task: str) -> Path:
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        doc, _ = load(path)
        if doc.get("task") == task:
            matches.append((doc.get("created_at_utc", ""), path))
    require(matches, f"missing Task{task} JSON in {directory}")
    return max(matches)[1]


def sha_match(directory: Path, sha: str) -> Path:
    matches = [path for path in directory.glob("*.json")
               if hashlib.sha256(path.read_bytes()).hexdigest() == sha]
    require(len(matches) == 1, f"expected one SHA-matched Task136W in {directory}")
    return matches[0]


def utc(value: str, label: str) -> datetime:
    require(isinstance(value, str) and value.strip(), f"{label}: missing time")
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"STOP: {label}: invalid ISO timestamp") from exc
    # Task136W interprets existing timezone-free raw timestamps as UTC.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def build(ak: dict, w: dict, w_sha: str, conn, now: datetime) -> dict:
    require(ak.get("task") == "136AK" and w.get("task") == "136W" and
            w.get("report_schema_version") == "1.1" and
            ak.get("checkpoint96") == w.get("checkpoint96") == "OPEN" and
            ak.get("accepted_financial_totals") is None and
            w.get("accepted_financial_totals") is None and
            ak["sources"]["136W"]["sha256"] == w_sha and
            ak["coverage"]["cached_references"] == w["coverage"]["candidate_hashes"],
            "Task136AK and W snapshot or financial boundary differs")
    prior = {str(item["txhash"]).lower() for item in w["candidate_rows"]}
    require(len(prior) == len(w["candidate_rows"]) == w["coverage"]["candidate_hashes"],
            "Task136W cohort hash duplicates or count differs")
    cutoff = utc(w["cutoff"]["raw_latest_utc"], "Task136W raw latest")
    require(cutoff <= now, "Task136W latest raw time is after audit clock")
    wallet_rows = conn.execute("SELECT address,ownership_type FROM ronin_wallet_registry").fetchall()
    owned = {str(address).lower() for address, typ in wallet_rows
             if typ and str(typ).upper() == "USER_OWNED" and address}
    source_owned = {str(row["address"]).lower() for row in w["registered_owned_wallets"]}
    require(owned == source_owned and len(owned) == len(w["registered_owned_wallets"]),
            "registered owned wallets changed since Task136W; refresh wallet scope first")
    required = {"ronin_api_transactions_raw": {"tx_hash", "timestamp", "from_address", "to_address"},
                "ronin_token_transfers_raw": {"tx_hash", "timestamp", "from_address", "to_address"}}
    after = defaultdict(lambda: {"raw_transaction_rows": 0, "raw_transfer_rows": 0,
                                 "first_utc": None, "last_utc": None})
    max_raw = None
    total_rows = Counter()
    post_rows = Counter()
    for table, kind in (("ronin_api_transactions_raw", "transaction"),
                        ("ronin_token_transfers_raw", "transfer")):
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        require(required[table] <= columns,
                f"{table}: missing {sorted(required[table] - columns)}")
        for h, stamp, sender, recipient in conn.execute(
                f"SELECT tx_hash,timestamp,from_address,to_address FROM {table}"):
            total_rows[kind] += 1
            at = utc(stamp, f"{table}.timestamp")
            if max_raw is None or at > max_raw:
                max_raw = at
            if at <= cutoff:
                continue
            if str(sender or "").lower() not in owned and str(recipient or "").lower() not in owned:
                continue
            require(isinstance(h, str) and h.strip(), f"{table}: new owned row missing tx hash")
            key = h.lower()
            require(key.startswith("0x") and len(key) == 66,
                    f"{table}: invalid new owned tx hash")
            post_rows[kind] += 1
            slot = after[key]
            slot["raw_" + kind + "_rows"] += 1
            iso = at.isoformat()
            slot["first_utc"] = min(slot["first_utc"], iso) if slot["first_utc"] else iso
            slot["last_utc"] = max(slot["last_utc"], iso) if slot["last_utc"] else iso
    require(max_raw is not None and max_raw >= cutoff, "raw source was removed or earlier than snapshot")
    new_hashes = set(after) - prior
    existing_hashes = set(after) & prior
    details = [{"txhash": h, "snapshot_hash_present": h in prior, **after[h]}
               for h in sorted(after)]
    return {"project": "AxieOS", "version": "0.14", "task": "136AR",
            "snapshot_latest_raw_utc": cutoff.isoformat(),
            "current_latest_raw_utc": max_raw.isoformat(),
            "audit_as_of_utc": now.isoformat(),
            "coverage": {"snapshot_wallet_hashes": len(prior),
                         "current_raw_rows_total": dict(total_rows),
                         "new_owned_raw_rows_after_snapshot": dict(post_rows),
                         "wallet_hashes_with_later_raw_rows": len(after),
                         "new_wallet_hashes_after_snapshot": len(new_hashes),
                         "existing_wallet_hashes_with_later_rows": len(existing_hashes),
                         "no_new_cached_owned_rows": not bool(after),
                         "snapshot_age_days": (now - cutoff).total_seconds() / 86400},
            "later_wallet_rows": details, "accepted_financial_totals": None,
            "production_database_opened_read_only": True,
            "production_database_writes": 0, "network_calls": 0,
            "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136AR Raw cache freshness audit", "",
             f"Task136W raw latest: **{report['snapshot_latest_raw_utc']}**. "
             f"Current database raw latest: **{report['current_latest_raw_utc']}**. "
             f"Audit time: **{report['audit_as_of_utc']}**.", "",
             f"Snapshot wallet hashes: **{c['snapshot_wallet_hashes']}**. "
             f"New owned wallet hashes after snapshot: **{c['new_wallet_hashes_after_snapshot']}**. "
             f"Existing hashes with later raw rows: **{c['existing_wallet_hashes_with_later_rows']}**.", "",
             "A zero means no later owned-wallet rows are present in this local raw cache. "
             "It does not show that no later wallet activity occurred on-chain. "
             "The JSON lists hashes and row counts if later cache rows exist.", "",
             "Verified income, expenses, profit, and PHP recovery: **UNKNOWN**.", "",
             "Production opened read only | Writes: 0 | Network: 0", "",
             "VALIDATION: PASS (local raw-cache freshness only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--ak", type=Path)
    parser.add_argument("--ak-dir", type=Path, default=Path("reports/axieos_v014/task136ak"))
    parser.add_argument("--w", type=Path)
    parser.add_argument("--w-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136ar"))
    args = parser.parse_args()
    ap = args.ak or latest(args.ak_dir, "136AK")
    ak, ak_sha = load(ap)
    wp = args.w or sha_match(args.w_dir, ak["sources"]["136W"]["sha256"])
    w, w_sha = load(wp)
    with closing(connect_ro(args.db)) as conn:
        conn.execute("BEGIN")
        report = build(ak, w, w_sha, conn, datetime.now(timezone.utc))
    report["sources"] = {"136AK": {"filename": ap.name, "sha256": ak_sha},
                         "136W": {"filename": wp.name, "sha256": w_sha}}
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AR_Raw_Cache_Freshness_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136AR - RAW CACHE FRESHNESS")
    print(f"Snapshot wallet hashes: {c['snapshot_wallet_hashes']} | New owned hashes: "
          f"{c['new_wallet_hashes_after_snapshot']} | Existing hashes with later raw rows: "
          f"{c['existing_wallet_hashes_with_later_rows']}")
    print(f"Snapshot raw latest UTC: {report['snapshot_latest_raw_utc']} | "
          f"Current raw latest UTC: {report['current_latest_raw_utc']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Production read only | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (local raw-cache freshness only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
