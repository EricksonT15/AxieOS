r"""Recover class for the 29 V0.15 Axies from guarded Ronin gene data.

Save this plain .py file in AxieOS/scripts/ next to the V0.15 scripts.
Run from the repository root:
    py -B .\scripts\AxieOS_V016_Onchain_Class_Recovery.py --apply

The earlier public metadata endpoint returned Beast for all 37 sampled Axies,
and App.Axie returned HTTP 403. Neither source is used here. This reads the
on-chain Axie genes at one recent block, validates the proposed class code
against every saved owned Axie with a class, checks target ownership and breed,
rehearses in a clone, backs up outside the repo, then fills only validated
NULL classes. Levels and financial records remain untouched.
"""

import argparse
import hashlib
import json
import re
import sqlite3
import tempfile
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import AxieOS_V015_Source_Catchup as chain
import AxieOS_V015_Source_Reconciliation as prior
import AxieOS_V015_Onchain_Core_Enrichment as core
import AxieOS_V015_Guarded_Roster_Refresh as roster

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/axieos_v016/onchain_class"
PROTECTED = tuple(t for t in prior.WATCHED if t != "gameplay_owned_axies")
TAG = "RONIN_GENE_CLASS_V016"
COUNT = 29


def require(ok, message):
    prior.require(ok, message)


def canonical(value):
    if not isinstance(value, str):
        return None
    value = value.strip().title()
    return "Aquatic" if value == "Aqua" else value if value in roster.CLASSES else None


def state(conn, ids):
    needed = {"axie_id", "wallet_address", "ownership_status", "axie_class", "level",
              "breed_count", "data_source", "last_seen_datetime", "last_updated"}
    require(needed <= prior.table_columns(conn, "gameplay_owned_axies"), "roster schema differs")
    rows = conn.execute("SELECT axie_id,wallet_address,ownership_status,axie_class,level,breed_count,"
                        "data_source,last_seen_datetime FROM gameplay_owned_axies WHERE axie_id IN (" +
                        ",".join("?" for _ in ids) + ")", ids).fetchall()
    targets = {str(r[0]): r[1:] for r in rows}
    require(len(rows) == len(targets) == COUNT and set(targets) == set(ids), "target IDs differ")
    require(all(r[0] == chain.WALLETS[0] and r[1] == "OWNED" and r[2] is None and
                r[3] is None and type(r[4]) is int and 0 <= r[4] <= 7 and
                isinstance(r[5], str) and r[5].startswith("RONIN_OWNER_V015_AND_")
                for r in targets.values()), "target ownership or existing metadata differs")
    require(conn.execute("SELECT count(*) FROM gameplay_owned_axies WHERE ownership_status='OWNED'").fetchone()[0] == 162,
            "owned roster count differs")
    controls = [(str(a), canonical(c), b) for a, c, b in conn.execute(
        "SELECT axie_id,axie_class,breed_count FROM gameplay_owned_axies WHERE ownership_status='OWNED' "
        "AND axie_class IS NOT NULL AND axie_id NOT IN (" + ",".join("?" for _ in ids) +
        ") ORDER BY CAST(axie_id AS INTEGER)", ids)]
    require(len(controls) >= 50 and len({a for a, _, _ in controls}) == len(controls) and
            all(c in roster.CLASSES and a.isdecimal() for a, c, _ in controls) and
            len({c for _, c, _ in controls}) >= 4, "saved class controls insufficient")
    return targets, controls


def read_chain(client, target_ids, control_ids):
    chain_id, head = client.rpc([("eth_chainId", []), ("eth_getBlockByNumber", ["latest", False])])
    require(chain.rpc_hex(chain_id) == 2020 and isinstance(head, dict) and
            re.fullmatch(r"0x[0-9a-fA-F]{64}", head.get("hash", "")), "Ronin chain/head differs")
    block = head["number"]
    observed = datetime.fromtimestamp(chain.rpc_hex(head["timestamp"]), timezone.utc)
    require(timedelta(minutes=-5) <= datetime.now(timezone.utc) - observed <= timedelta(hours=1),
            "Ronin head is stale")
    owners = chain.grouped(client, [chain.eth_call(chain.SELECTORS["owner"],
                [format(int(a), "064x")], block) for a in target_ids])
    require(len(owners) == len(target_ids) and all(
        "0x" + format(chain.uint_abi(owner), "040x") == chain.WALLETS[0] for owner in owners),
        "target on-chain owner changed")
    ids = target_ids + control_ids
    specs = [("eth_call", [{"to": chain.AXIE,
              "data": "0x" + core.CORE_SELECTOR + format(int(a), "064x")}, block]) for a in ids]
    replies = chain.grouped(client, specs)
    require(len(replies) == len(ids), "core reply count differs")
    readings = {}
    for aid, raw in zip(ids, replies):
        require(isinstance(raw, str) and re.fullmatch(r"0x(?:[0-9a-fA-F]{64}){7,}", raw),
                f"{aid}: invalid Axie ABI response")
        words = [int(raw[2 + 64*i:2 + 64*(i+1)], 16) for i in range(7)]
        # Current Axie ABI axie(uint256): sire, matron, birth, genes(x,y), breed, level.
        # Save both words; the top nibble of x failed four control mappings.
        readings[aid] = {"gene_x": format(words[3], "064x"),
                         "gene_y": format(words[4], "064x"),
                         "breed_count": words[5],
                         "response_sha256": hashlib.sha256(raw.encode("ascii")).hexdigest()}
    recheck = client.rpc([("eth_getBlockByNumber", [block, False])])[0]
    require(isinstance(recheck, dict) and recheck.get("hash", "").lower() == head["hash"].lower(),
            "Ronin block changed during reads")
    return block, observed.isoformat(), readings


def gene_code(item, nibble):
    genome = (int(item["gene_x"], 16) << 256) | int(item["gene_y"], 16)
    return (genome >> (508 - 4 * nibble)) & 15


def make_plan(targets, controls, readings, ids):
    require(all(int(readings[a]["gene_x"], 16) and int(readings[a]["gene_y"], 16)
                for a, _, _ in controls), "control gene words absent")
    # Test aligned nibble positions in the two 256-bit gene words. The earlier
    # assumption that the first nibble holds class failed; no preferred offset.
    candidates, diagnostics = [], []
    for nibble in range(128):
        code_classes = defaultdict(set)
        code_support = Counter()
        class_codes = defaultdict(set)
        for aid, name, _breed in controls:
            code = gene_code(readings[aid], nibble)
            code_classes[code].add(name)
            class_codes[name].add(code)
            code_support[code] += 1
        conflicts = {str(code): sorted(names) for code, names in code_classes.items() if len(names) != 1}
        splits = {name: sorted(codes) for name, codes in class_codes.items() if len(codes) != 1}
        diagnostics.append({"nibble": nibble, "conflicting_codes": len(conflicts),
                            "split_classes": len(splits), "distinct_codes": len(code_classes)})
        if (not conflicts and not splits and len(code_classes) == len(class_codes) and
                len(code_classes) >= 4 and all(n >= 2 for n in code_support.values())):
            candidates.append((nibble, {code: next(iter(names)) for code, names in code_classes.items()},
                               dict(code_support)))
    # Multiple equally consistent positions indicate an ambiguous encoding.
    unique = len(candidates) == 1
    nibble, mapping, support = candidates[0] if unique else (None, {}, {})
    breed_mismatch = [aid for aid in ids if readings[aid]["breed_count"] != targets[aid][4]]
    require(not breed_mismatch, f"target breed changed for {breed_mismatch}; no update")
    rows = [(aid, mapping[gene_code(readings[aid], nibble)]) for aid in ids
            if unique and int(readings[aid]["gene_x"], 16) and int(readings[aid]["gene_y"], 16)
            and gene_code(readings[aid], nibble) in mapping]
    return rows, {"control_count": len(controls), "unique_nibble": nibble,
                  "consistent_nibbles": [item[0] for item in candidates],
                  "code_support": support,
                  "class_codes": {str(k): v for k, v in sorted(mapping.items())},
                  "top_diagnostics": sorted(diagnostics, key=lambda d: (
                      d["conflicting_codes"] + d["split_classes"], d["nibble"]))[:12],
                  "code_validation_pass": unique,
                  "target_breed_matches": COUNT}


def changed(conn, ids):
    return {str(r[0]): r[1:] for r in conn.execute(
        "SELECT axie_id,wallet_address,ownership_status,axie_class,level,breed_count,"
        "data_source,last_seen_datetime FROM gameplay_owned_axies WHERE axie_id IN (" +
        ",".join("?" for _ in ids) + ")", ids)}


def baseline(conn, ids):
    return {"protected": {t: prior.snapshot_table(conn, t) for t in PROTECTED},
            "roster_count": prior.snapshot_table(conn, "gameplay_owned_axies")["rows"],
            "untouched": roster.unchanged_roster(conn, set(ids)),
            "targets": changed(conn, ids)}


def update(conn, rows, before, ids):
    start = conn.total_changes
    for aid, name in rows:
        old = before["targets"][aid]
        cursor = conn.execute("UPDATE gameplay_owned_axies SET axie_class=?,"
                              "data_source=data_source || '|" + TAG + "',"
                              "last_updated=CURRENT_TIMESTAMP WHERE axie_id=? "
                              "AND ownership_status='OWNED' AND wallet_address=? "
                              "AND axie_class IS NULL AND level IS NULL AND breed_count=? "
                              "AND data_source=?", (name, aid, old[0], old[4], old[5]))
        require(cursor.rowcount == 1, f"{aid}: guarded update count differs")
    require(conn.total_changes - start == len(rows), "target change count differs")
    require(all(prior.snapshot_table(conn, t) == before["protected"][t] for t in PROTECTED) and
            roster.unchanged_roster(conn, set(ids)) == before["untouched"] and
            prior.snapshot_table(conn, "gameplay_owned_axies")["rows"] == before["roster_count"] and
            conn.execute("SELECT count(*) FROM gameplay_owned_axies WHERE ownership_status='OWNED'").fetchone()[0] == 162 and
            conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
            not conn.execute("PRAGMA foreign_key_check").fetchall(), "protected tables/roster integrity differ")
    expected = dict(rows)
    for aid, after in changed(conn, ids).items():
        old = before["targets"][aid]
        if aid in expected:
            require(after[:2] == old[:2] and after[2] == expected[aid] and after[3:5] == old[3:5]
                    and after[5] == old[5] + "|" + TAG and after[6] == old[6],
                    f"{aid}: target values differ")
        else:
            require(after == old, f"{aid}: held target changed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=prior.DEFAULT_DB)
    parser.add_argument("--refresh", type=Path, help="Exact applied V0.15 roster report")
    parser.add_argument("--source-dir", type=Path, default=ROOT / "reports/axieos_v015/source_catchup")
    parser.add_argument("--output-dir", type=Path, default=OUT)
    parser.add_argument("--backup-dir", type=Path, default=Path.home() / "AxieOSBackups")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    path = args.refresh or core.latest_applied(args.source_dir)
    _, report_sha, ids = core.source(path)
    db = args.db.expanduser().resolve()
    with closing(prior.open_ro(db)) as conn:
        targets, controls = state(conn, ids)
    client = chain.Net(15)
    block, observed, readings = read_chain(client, ids, [r[0] for r in controls])
    rows, validation = make_plan(targets, controls, readings, ids)
    before = None
    if rows:
        with closing(prior.open_ro(db)) as conn:
            conn.execute("BEGIN")
            require(state(conn, ids) == (targets, controls), "saved roster changed during RPC")
            before = baseline(conn, ids)
            with tempfile.TemporaryDirectory(prefix="axieos_v016_class_") as tmp:
                with closing(sqlite3.connect(Path(tmp) / "clone.db")) as clone:
                    conn.backup(clone)
                    require(baseline(clone, ids) == before, "clone baseline differs")
                    clone.execute("PRAGMA foreign_keys=ON")
                    update(clone, rows, before, ids)
                    clone.commit()
    backup_path = None
    if args.apply and rows:
        directory = args.backup_dir.expanduser().resolve()
        require(not directory.is_relative_to(ROOT.resolve()) and directory != db.parent and
                not db.is_relative_to(directory), "backup must be outside repository")
        directory.mkdir(parents=True, exist_ok=True)
        backup_path = directory / ("axieos_before_v016_class_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6] + ".db")
        with closing(prior.open_ro(db)) as src, closing(sqlite3.connect(backup_path)) as dest:
            src.backup(dest)
            require(baseline(dest, ids) == before and
                    dest.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "backup differs")
        with closing(sqlite3.connect(db, timeout=15)) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("BEGIN IMMEDIATE")
            try:
                require(baseline(conn, ids) == before, "production changed since backup")
                update(conn, rows, before, ids)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        with closing(prior.open_ro(db)) as conn:
            require(all(prior.snapshot_table(conn, t) == before["protected"][t] for t in PROTECTED) and
                    roster.unchanged_roster(conn, set(ids)) == before["untouched"] and
                    changed(conn, ids) == {aid: tuple((old[0], old[1], dict(rows).get(aid, old[2]),
                        old[3], old[4], old[5] + ("|" + TAG if aid in dict(rows) else ""), old[6]))
                        for aid, old in before["targets"].items()} and
                    conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                    not conn.execute("PRAGMA foreign_key_check").fetchall(), "post-apply reconciliation differs")
    status = ("APPLIED_AND_RECONCILED" if args.apply and rows else
              "READ_ONLY_CLONE_READY" if rows else "GENE_CLASS_CONTROLS_HELD")
    report = {"version": "0.16", "task": "ONCHAIN_CLASS_RECOVERY", "status": status,
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "source_roster_report": str(path), "source_sha256": report_sha,
              "ronin_block": block, "block_timestamp_utc": observed,
              "failed_public_metadata_class": "BEAST_FOR_37_OF_37", "app_axie_http": 403,
              "validation": validation,
              "target_count": COUNT, "class_candidate_count": len(rows),
              "class_updated": len(rows) if args.apply else 0,
              "level_updated": 0,
              "held_ids": sorted(set(ids) - {a for a, _ in rows}, key=int),
              "targets": {a: {"class_code": gene_code(readings[a], validation["unique_nibble"])
                            if validation["unique_nibble"] is not None else None,
                        "class": dict(rows).get(a), "breed_count": readings[a]["breed_count"],
                        "gene_x": readings[a]["gene_x"], "gene_y": readings[a]["gene_y"],
                        "response_sha256": readings[a]["response_sha256"]} for a in ids},
              "control_gene_evidence": {a: {"saved_class": name, "gene_x": readings[a]["gene_x"],
                  "gene_y": readings[a]["gene_y"]} for a, name, _ in controls},
              "backup": str(backup_path) if backup_path else None,
              "rpc_calls": client.calls, "rpc_batch_400_fallbacks": client.batch_400_fallbacks,
              "finance_writes": 0, "verified_financial_totals": "UNKNOWN",
              "unified_finance": "HOLD", "checkpoint96": "OPEN"}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V016_Onchain_Class_Recovery_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    jp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    mp.write_text("\n".join(["# AxieOS V0.16 on-chain class recovery", "",
        f"Status: **{status}**. Validated class candidates: **{len(rows)}/29**; "
        f"class updated: **{report['class_updated']}/29**; level updated: **0/29**.",
        f"Saved controls: **{len(controls)}**. Consistent nibble positions: "
        f"**{len(validation['consistent_nibbles'])}**. "
        f"Held Axies: **{len(report['held_ids'])}**.",
        f"Ronin block: `{block}` at {observed}. Backup: `{backup_path or 'none'}`.", "",
        "The prior public metadata class and blocked marketplace page were excluded.",
        "Finance totals: **UNKNOWN**; Unified Finance: **HOLD**; Checkpoint 96: **OPEN**.", ""]),
        encoding="utf-8")
    print("AXIEOS V0.16 - ONCHAIN CLASS RECOVERY")
    print(f"Status: {status} | Saved controls: {len(controls)} | Consistent positions: {validation['consistent_nibbles']}")
    print(f"Class candidates/applied: {len(rows)}/{report['class_updated']} | Level: 0/29 | Held: {len(report['held_ids'])}")
    print(f"Reports: {jp} {mp} | Backup: {backup_path or 'none'}")
    print("Finance totals: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
