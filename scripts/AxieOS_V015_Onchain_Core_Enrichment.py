r"""Guarded on-chain breed/level recovery for the 29 newly owned Axies.

Save in scripts/ beside AxieOS_V015_Source_Catchup.py,
AxieOS_V015_Source_Reconciliation.py and AxieOS_V015_Guarded_Roster_Refresh.py.
From the repository root:
    py -B .\scripts\AxieOS_V015_Onchain_Core_Enrichment.py --apply

Reads current Axie core data from Ronin at one pinned block, checks owners,
compares control Axies, rehearses in a disposable clone, makes a backup outside
the repository, and updates only individually validated missing fields.
Unexpected values are reported and kept NULL. Class remains UNKNOWN.
Never changes finance/accounting or signs a tx.
"""

import argparse
import hashlib
import json
import re
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import AxieOS_V015_Source_Catchup as chain
import AxieOS_V015_Source_Reconciliation as prior
import AxieOS_V015_Guarded_Roster_Refresh as roster


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/axieos_v015/source_catchup"
CORE_SELECTOR = "3e2156aa"  # Existing V0.8 getAxie contract call.
TARGET_COUNT = 29
CONTROL_COUNT = 8
PROTECTED = tuple(t for t in prior.WATCHED if t != "gameplay_owned_axies")


def require(ok, reason):
    prior.require(ok, reason)


def source(path):
    require(path.is_file(), f"applied roster report missing: {path}")
    body = path.read_bytes()
    doc = json.loads(body.decode("utf-8-sig"))
    ids = doc.get("metadata_unknown_ids")
    require(doc.get("version") == "0.15" and doc.get("task") == "GUARDED_ROSTER_REFRESH" and
            doc.get("status") == "APPLIED_AND_RECONCILED" and
            doc.get("sources", {}).get("catchup_sha256") == prior.SOURCE_SHA256 and
            doc.get("fresh_chain_owned") == 162 and doc.get("chain_only_inserted") == TARGET_COUNT and
            doc.get("saved_only_to_unknown") == 3 and doc.get("finance_writes") == 0 and
            doc.get("checkpoint96") == "OPEN" and isinstance(ids, list) and
            len(ids) == len(set(ids)) == TARGET_COUNT and
            all(isinstance(i, str) and i.isdecimal() and int(i) > 0 for i in ids),
            "applied roster report differs")
    return doc, hashlib.sha256(body).hexdigest(), sorted(ids, key=int)


def latest_applied(directory):
    for path in sorted(directory.glob("AxieOS_V015_Guarded_Roster_Refresh_*.json"), reverse=True):
        try:
            if json.loads(path.read_text(encoding="utf-8-sig")).get("status") == "APPLIED_AND_RECONCILED":
                return path
        except (OSError, ValueError, TypeError):
            continue
    raise ValueError("STOP: no applied V0.15 roster refresh report found")


def database_state(conn, ids):
    required = {"axie_id", "wallet_address", "ownership_status", "axie_class", "level",
                "breed_count", "data_source", "last_updated"}
    require(required <= prior.table_columns(conn, "gameplay_owned_axies"), "roster schema differs")
    rows = conn.execute("SELECT axie_id,wallet_address,ownership_status,axie_class,level,breed_count,"
                        "data_source FROM gameplay_owned_axies WHERE axie_id IN (" +
                        ",".join("?" for _ in ids) + ")", ids).fetchall()
    by_id = {str(r[0]): r for r in rows}
    require(len(rows) == len(by_id) == TARGET_COUNT and set(by_id) == set(ids), "target rows missing/duplicated")
    require(all(row[1] == chain.WALLETS[0] and row[2] == "OWNED" and row[3] is None and
                row[4] is None and row[5] is None and isinstance(row[6], str) and
                row[6].startswith("RONIN_OWNER_V015_AND_") for row in rows),
            "target ownership or empty metadata has changed; no update")
    require(conn.execute("SELECT count(*) FROM gameplay_owned_axies WHERE ownership_status='OWNED'").fetchone()[0] == 162,
            "owned roster count differs")
    controls = conn.execute("SELECT axie_id,level,breed_count FROM gameplay_owned_axies WHERE "
                            "ownership_status='OWNED' AND axie_id NOT IN (" +
                            ",".join("?" for _ in ids) + ") AND level IS NOT NULL AND "
                            "breed_count IS NOT NULL ORDER BY CAST(axie_id AS INTEGER) LIMIT ?",
                            (*ids, CONTROL_COUNT)).fetchall()
    require(len(controls) == CONTROL_COUNT and all(str(r[0]).isdecimal() for r in controls),
            "insufficient saved Axie core controls")
    return by_id, controls


def read_core(client, ids):
    chain_id, head = client.rpc([("eth_chainId", []), ("eth_getBlockByNumber", ["latest", False])])
    require(chain.rpc_hex(chain_id) == 2020 and isinstance(head, dict) and
            re.fullmatch(r"0x[0-9a-fA-F]{64}", head.get("hash", "")), "Ronin chain/block differs")
    block = head["number"]
    observed = datetime.fromtimestamp(chain.rpc_hex(head["timestamp"]), timezone.utc)
    require(timedelta(minutes=-5) <= datetime.now(timezone.utc) - observed <= timedelta(hours=1),
            "Ronin head is not recent")
    all_ids = list(ids)
    owners = chain.grouped(client, [chain.eth_call(chain.SELECTORS["owner"],
                [format(int(i), "064x")], block) for i in all_ids])
    require(all("0x" + format(chain.uint_abi(owner), "040x") == chain.WALLETS[0]
                for owner in owners), "core target/control ownership differs")
    calls = [("eth_call", [{"to": chain.AXIE,
              "data": "0x" + CORE_SELECTOR + format(int(i), "064x")}, block]) for i in all_ids]
    replies = chain.grouped(client, calls)
    result = {}
    for aid, raw in zip(all_ids, replies):
        require(isinstance(raw, str) and re.fullmatch(r"0x(?:[0-9a-fA-F]{64}){7,}", raw),
                f"{aid}: invalid core ABI response")
        words = [int(raw[2 + 64*k:2 + 64*(k+1)], 16) for k in range(7)]
        breed, level = words[5], words[6]
        result[aid] = {"breed_count": breed if 0 <= breed <= 7 else None,
                       "contract_level": level if 0 < level <= 1000 else None,
                       "raw_breed_word": str(breed), "raw_level_word": str(level),
                       "response_sha256": hashlib.sha256(raw.encode()).hexdigest()}
    recheck = client.rpc([("eth_getBlockByNumber", [block, False])])[0]
    require(isinstance(recheck, dict) and recheck.get("hash", "").lower() == head["hash"].lower(),
            "Ronin block changed during reads")
    return block, observed.isoformat(), result


def changed_rows(conn, ids):
    return {str(row[0]): row[1:] for row in conn.execute(
        "SELECT axie_id,wallet_address,ownership_status,axie_class,level,breed_count,data_source,"
        "last_seen_datetime FROM gameplay_owned_axies WHERE axie_id IN (" +
        ",".join("?" for _ in ids) + ")", ids)}


def baseline(conn, ids):
    return {"protected": {t: prior.snapshot_table(conn, t) for t in PROTECTED},
            "roster": prior.snapshot_table(conn, "gameplay_owned_axies"),
            "untouched": roster.unchanged_roster(conn, set(ids)),
            "targets": changed_rows(conn, ids)}


def plan(ids, control_ids, readings):
    breed_matches = [readings[str(i)]["breed_count"] == b for i, _l, b in control_ids]
    breed_ok = all(breed_matches)
    level_matches = [readings[str(i)]["contract_level"] == l for i, l, _b in control_ids]
    level_ok = all(level_matches)
    rows = []
    for aid in ids:
        breed = readings[aid]["breed_count"] if breed_ok else None
        level = readings[aid]["contract_level"] if level_ok else None
        if breed is not None or level is not None:
            rows.append((breed, level, "RONIN_CORE_V015", aid))
    return rows, sum(breed_matches), sum(level_matches)


def update(conn, rows, before, ids):
    n = conn.total_changes
    conn.executemany("UPDATE gameplay_owned_axies SET breed_count=COALESCE(?,breed_count),"
                     "level=COALESCE(?,level),"
                     "data_source=data_source || '|' || ?,last_updated=CURRENT_TIMESTAMP "
                     "WHERE axie_id=? AND ownership_status='OWNED' AND breed_count IS NULL AND level IS NULL",
                     rows)
    require(conn.total_changes - n == len(rows), "exact roster update count differs")
    require(all(prior.snapshot_table(conn, t) == before["protected"][t] for t in PROTECTED) and
            roster.unchanged_roster(conn, set(ids)) == before["untouched"] and
            conn.execute("SELECT count(*) FROM gameplay_owned_axies WHERE ownership_status='OWNED'").fetchone()[0] == 162 and
            conn.execute("SELECT count(*) FROM gameplay_owned_axies").fetchone()[0] == before["roster"]["rows"] and
            conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
            not conn.execute("PRAGMA foreign_key_check").fetchall(),
            "protected state or SQLite integrity differs")
    actual = changed_rows(conn, ids)
    for breed, level, origin, aid in rows:
        old, new = before["targets"][aid], actual[aid]
        require(new[:3] == old[:3] and new[3] == level and new[4] == breed and
                new[5] == old[5] + "|" + origin and new[6] == old[6],
                f"{aid}: target update differs")
    for aid in set(ids) - {row[3] for row in rows}:
        require(actual[aid] == before["targets"][aid], f"{aid}: held target changed")


def clone(source_conn, rows, before, ids):
    with tempfile.TemporaryDirectory(prefix="axieos_v015_core_clone_") as tmp:
        with closing(sqlite3.connect(Path(tmp) / "clone.db")) as conn:
            source_conn.backup(conn)
            require(baseline(conn, ids) == before, "clone baseline differs")
            conn.execute("PRAGMA foreign_keys=ON")
            update(conn, rows, before, ids)
            conn.commit()


def backup(db, directory, before, ids):
    directory = directory.expanduser().resolve()
    require(not directory.is_relative_to(ROOT.resolve()) and directory != db.parent and
            not db.is_relative_to(directory), "backup location must be outside repository")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ("axieos_before_v015_core_" +
                        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
                        "_" + uuid4().hex[:6] + ".db")
    with closing(prior.open_ro(db)) as src, closing(sqlite3.connect(path)) as dest:
        src.backup(dest)
        require(baseline(dest, ids) == before and
                dest.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                "backup differs from read-only baseline")
    return path


def apply(db, rows, before, ids):
    with closing(sqlite3.connect(db, timeout=15)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("BEGIN IMMEDIATE")
        try:
            require(baseline(conn, ids) == before, "production changed after backup")
            update(conn, rows, before, ids)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    with closing(prior.open_ro(db)) as verify:
        # Compare the exact intended target fields and all protected sources.
        require(all(prior.snapshot_table(verify, t) == before["protected"][t] for t in PROTECTED) and
                roster.unchanged_roster(verify, set(ids)) == before["untouched"],
                "post-commit protected state differs")
        for breed, level, origin, aid in rows:
            old = before["targets"][aid]
            new = changed_rows(verify, [aid])[aid]
            require(new[:3] == old[:3] and new[3] == level and new[4] == breed and
                    new[5] == old[5] + "|" + origin and new[6] == old[6],
                    f"{aid}: post-commit core values differ")
        for aid in set(ids) - {row[3] for row in rows}:
            require(changed_rows(verify, [aid])[aid] == before["targets"][aid],
                    f"{aid}: held target changed after commit")
        require(verify.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                not verify.execute("PRAGMA foreign_key_check").fetchall(),
                "post-commit SQLite integrity differs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=prior.DEFAULT_DB)
    parser.add_argument("--refresh", type=Path, help="Exact applied roster refresh JSON")
    parser.add_argument("--report-dir", type=Path, default=OUT)
    parser.add_argument("--backup-dir", type=Path, default=Path.home() / "AxieOSBackups")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    refresh_path = args.refresh or latest_applied(args.report_dir)
    refresh, refresh_sha, ids = source(refresh_path)
    db = args.db.expanduser().resolve()
    with closing(prior.open_ro(db)) as conn:
        targets, controls = database_state(conn, ids)
    all_ids = ids + [str(c[0]) for c in controls]
    client = chain.Net(15)
    block, observed, readings = read_core(client, all_ids)
    rows, breed_matches, level_matches = plan(ids, controls, readings)
    with closing(prior.open_ro(db)) as conn:
        conn.execute("BEGIN")
        require(database_state(conn, ids) == (targets, controls), "saved target/control rows changed")
        before = baseline(conn, ids)
        if rows:
            clone(conn, rows, before, ids)
    status, backup_path = ("READ_ONLY_CLONE_READY" if rows else "NO_VERIFIED_FIELDS"), None
    if args.apply and rows:
        backup_path = backup(db, args.backup_dir, before, ids)
        apply(db, rows, before, ids)
        status = "PARTIAL_APPLIED_AND_RECONCILED" if len(rows) < TARGET_COUNT or any(
            breed is None or level is None for breed, level, _origin, _aid in rows) else "APPLIED_AND_RECONCILED"
    target_breed = sum(readings[i]["breed_count"] is not None for i in ids) if breed_matches == CONTROL_COUNT else 0
    target_level = sum(readings[i]["contract_level"] is not None for i in ids) if level_matches == CONTROL_COUNT else 0
    invalid_core = [{"axie_id": i, "raw_breed_word": readings[i]["raw_breed_word"],
                     "raw_level_word": readings[i]["raw_level_word"]} for i in ids
                    if readings[i]["breed_count"] is None or readings[i]["contract_level"] is None]
    report = {"version": "0.15", "task": "ONCHAIN_CORE_ENRICHMENT", "status": status,
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "source_roster_report": str(refresh_path), "source_sha256": refresh_sha,
              "fresh_block": block, "fresh_block_timestamp_utc": observed,
              "target_axies": TARGET_COUNT, "breed_count_validated": target_breed,
              "level_validated": target_level,
              "control_axies": CONTROL_COUNT, "control_breed_matches": breed_matches,
              "control_level_matches": level_matches,
              "class_still_unknown": TARGET_COUNT, "core_evidence": readings,
              "invalid_core_targets": invalid_core,
              "held_ids": sorted(set(ids) - {row[3] for row in rows}, key=int),
              "roster_updates": len(rows) if args.apply else 0,
              "backup": str(backup_path) if backup_path else None,
              "rpc_calls": client.calls, "database_writes": len(rows) if args.apply else 0,
              "finance_writes": 0, "verified_financial_totals": "UNKNOWN",
              "unified_finance": "HOLD", "checkpoint96": "OPEN"}
    args.report_dir.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V015_Onchain_Core_Enrichment_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    jp, mp = args.report_dir / (stem + ".json"), args.report_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as out:
        json.dump(report, out, indent=2)
        out.write("\n")
    mp.write_text("\n".join(["# AxieOS V0.15 on-chain core enrichment", "",
        f"Status: **{status}**. Breed count verified: **{target_breed}/29**; "
        f"level verified: **{report['level_validated']}/29**; class still unknown: **29**.",
        f"Control Axie breed/level matches: **{breed_matches}/{CONTROL_COUNT}** / "
        f"**{level_matches}/{CONTROL_COUNT}**. Held IDs: **{len(report['held_ids'])}**.",
        f"Out-of-range core words for target Axies: **{len(invalid_core)}** "
        "(see JSON for exact words).",
        f"Pinned block: `{block}` at {observed}. Backup: `{backup_path or 'none'}`.",
        "", "No class or acquisition value was inferred from genome or wallet movement.",
        "Financial totals: **UNKNOWN**; Unified Finance: **HOLD**; Checkpoint 96: **OPEN**.", ""]), encoding="utf-8")
    print("AXIEOS V0.15 - ONCHAIN CORE ENRICHMENT")
    print(f"Status: {status} | Breed: {target_breed}/29 | Level: {target_level}/29 | Class: UNKNOWN 29")
    print(f"Control matches breed/level: {breed_matches}/{CONTROL_COUNT}, {level_matches}/{CONTROL_COUNT} | Held IDs: {len(report['held_ids'])}")
    print(f"Out-of-range core targets: {len(invalid_core)} | First five: {invalid_core[:5]}")
    print(f"Backup: {backup_path or 'none'} | Reports: {jp} {mp}")
    print("Financial totals: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
