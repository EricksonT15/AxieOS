r"""Apply 29 Axie classes from the exact Nov 5 saved Ronin gene report.

Save this plain file in AxieOS/scripts/ and run from the repository root:
    py -B .\scripts\AxieOS_V016_Offline_Class_Apply.py --apply

Uses the already collected Task V0.16 JSON, no network. First gene byte maps
all nine classes exactly across 133 saved controls. Validates source SHA-256,
current roster and 29 target breeds, rehearses a clone, creates an outside-repo
backup, then fills ONLY the 29 NULL class values. Level and finance untouched.
"""

import argparse
import hashlib
import json
import re
import sqlite3
import tempfile
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import AxieOS_V015_Source_Reconciliation as prior
import AxieOS_V015_Onchain_Core_Enrichment as core
import AxieOS_V015_Guarded_Roster_Refresh as roster
import AxieOS_V016_Onchain_Class_Recovery as previous

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports/axieos_v016/onchain_class"
SOURCE = OUTPUT / "AxieOS_V016_Onchain_Class_Recovery_20261105T083456_937495Z.json"
SOURCE_SHA = "764c27e6bbef71e9e80f1a24ea9bc1cfd0ef4d49d95bc51165656a2dec88f58a"
ROSTER_SHA = "f09f4ad564f15505e56f11bd271e86c2c7171217364fb1ca0b414a7b600cb1f0"
CODE_CLASS = {"00": "Beast", "08": "Bug", "10": "Bird", "18": "Plant",
              "20": "Aquatic", "28": "Reptile", "80": "Mech", "88": "Dawn", "90": "Dusk"}


def require(condition, reason):
    prior.require(condition, reason)


def gene_word(value, aid, kind):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value),
            f"{aid}: invalid {kind} gene word")
    require(int(value, 16) != 0, f"{aid}: zero {kind} gene word")
    return value.lower()


def load_evidence(path):
    require(path.is_file(), f"saved evidence missing: {path}")
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    require(sha == SOURCE_SHA, "saved gene report SHA-256 differs; no update")
    doc = json.loads(raw.decode("utf-8-sig"))
    controls, targets = doc.get("control_gene_evidence"), doc.get("targets")
    require(doc.get("version") == "0.16" and doc.get("task") == "ONCHAIN_CLASS_RECOVERY" and
            doc.get("status") == "GENE_CLASS_CONTROLS_HELD" and
            doc.get("source_sha256") == ROSTER_SHA and
            doc.get("validation", {}).get("control_count") == 133 and
            doc.get("target_count") == 29 and doc.get("class_updated") == 0 and
            doc.get("level_updated") == 0 and doc.get("finance_writes") == 0 and
            doc.get("checkpoint96") == "OPEN" and
            isinstance(controls, dict) and len(controls) == 133 and
            isinstance(targets, dict) and len(targets) == 29 and
            not (set(controls) & set(targets)), "saved gene report structure differs")
    for aid, row in controls.items():
        require(aid.isdecimal() and isinstance(row, dict) and
                previous.canonical(row.get("saved_class")) in roster.CLASSES,
                f"{aid}: invalid saved control class")
        gene_word(row.get("gene_x"), aid, "x")
        gene_word(row.get("gene_y"), aid, "y")
    for aid, row in targets.items():
        require(aid.isdecimal() and isinstance(row, dict) and row.get("class") is None and
                row.get("class_code") is None and
                type(row.get("breed_count")) is int and 0 <= row["breed_count"] <= 7,
                f"{aid}: invalid target record")
        gene_word(row.get("gene_x"), aid, "x")
        gene_word(row.get("gene_y"), aid, "y")
    return doc, sha


def plan(doc, ids, saved_targets, controls):
    source_controls = doc["control_gene_evidence"]
    require(set(source_controls) == {a for a, _, _ in controls},
            "saved controls differ from evidence")
    support = Counter()
    class_codes = defaultdict(set)
    for aid, saved_class, _breed in controls:
        row = source_controls[aid]
        require(previous.canonical(row["saved_class"]) == saved_class,
                f"{aid}: saved control class changed")
        code = row["gene_x"][:2].lower()
        require(code in CODE_CLASS and CODE_CLASS[code] == saved_class,
                f"{aid}: on-chain code disagrees with saved class")
        support[code] += 1
        class_codes[saved_class].add(code)
    require(set(support) == set(CODE_CLASS) and all(n >= 8 for n in support.values()) and
            len(class_codes) == 9 and all(len(codes) == 1 for codes in class_codes.values()),
            "nine-class gene code validation incomplete")
    require(set(doc["targets"]) == set(ids), "29 source IDs differ from applied roster")
    rows = []
    for aid in ids:
        record = doc["targets"][aid]
        require(record["breed_count"] == saved_targets[aid][4],
                f"{aid}: saved breed changed since Ronin evidence")
        code = record["gene_x"][:2].lower()
        require(code in CODE_CLASS, f"{aid}: gene class code not supported by 133 controls")
        rows.append((aid, CODE_CLASS[code]))
    require(len(rows) == len(set(a for a, _ in rows)) == 29,
            "class update plan is not exactly 29 rows")
    return rows, dict(sorted(support.items()))


def verify_post(conn, before, ids, rows):
    require(all(prior.snapshot_table(conn, t) == before["protected"][t]
                for t in previous.PROTECTED) and
            roster.unchanged_roster(conn, set(ids)) == before["untouched"] and
            prior.snapshot_table(conn, "gameplay_owned_axies")["rows"] == before["roster_count"] and
            conn.execute("SELECT count(*) FROM gameplay_owned_axies WHERE ownership_status='OWNED'").fetchone()[0] == 162 and
            conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
            not conn.execute("PRAGMA foreign_key_check").fetchall(),
            "post-commit protected state or integrity differs")
    actual = previous.changed(conn, ids)
    mapping = dict(rows)
    for aid in ids:
        old, new = before["targets"][aid], actual[aid]
        require(new[:2] == old[:2] and new[2] == mapping[aid] and
                new[3:5] == old[3:5] and
                new[5] == old[5] + "|" + previous.TAG and
                new[6] == old[6], f"{aid}: post-commit target differs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=prior.DEFAULT_DB)
    parser.add_argument("--evidence", type=Path, default=SOURCE)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "reports/axieos_v015/source_catchup")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--backup-dir", type=Path, default=Path.home() / "AxieOSBackups")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    evidence, evidence_sha = load_evidence(args.evidence)
    refresh_path = core.latest_applied(args.source_dir)
    _, roster_sha, ids = core.source(refresh_path)
    require(roster_sha == ROSTER_SHA, "applied V0.15 roster report changed")
    db = args.db.expanduser().resolve()
    with closing(prior.open_ro(db)) as conn:
        saved_targets, controls = previous.state(conn, ids)
    rows, support = plan(evidence, ids, saved_targets, controls)
    with closing(prior.open_ro(db)) as conn:
        conn.execute("BEGIN")
        require(previous.state(conn, ids) == (saved_targets, controls),
                "saved roster changed while planning")
        before = previous.baseline(conn, ids)
        with tempfile.TemporaryDirectory(prefix="axieos_v016_class_offline_") as temp:
            with closing(sqlite3.connect(Path(temp) / "clone.db")) as clone:
                conn.backup(clone)
                require(previous.baseline(clone, ids) == before, "clone baseline differs")
                clone.execute("PRAGMA foreign_keys=ON")
                previous.update(clone, rows, before, ids)
                clone.commit()
    backup_path = None
    if args.apply:
        directory = args.backup_dir.expanduser().resolve()
        require(not directory.is_relative_to(ROOT.resolve()) and directory != db.parent and
                not db.is_relative_to(directory), "backup location must be outside repository")
        directory.mkdir(parents=True, exist_ok=True)
        backup_path = directory / ("axieos_before_v016_class_offline_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6] + ".db")
        with closing(prior.open_ro(db)) as source, closing(sqlite3.connect(backup_path)) as dest:
            source.backup(dest)
            require(previous.baseline(dest, ids) == before and
                    dest.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                    "backup differs from read-only baseline")
        with closing(sqlite3.connect(db, timeout=15)) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("BEGIN IMMEDIATE")
            try:
                require(previous.baseline(conn, ids) == before,
                        "production changed since backup")
                previous.update(conn, rows, before, ids)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        with closing(prior.open_ro(db)) as verify:
            verify_post(verify, before, ids, rows)
    status = "APPLIED_AND_RECONCILED" if args.apply else "READ_ONLY_CLONE_READY"
    report = {"version": "0.16", "task": "OFFLINE_GENE_CLASS_APPLY", "status": status,
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "evidence": str(args.evidence), "evidence_sha256": evidence_sha,
              "applied_roster_report": str(refresh_path), "roster_report_sha256": roster_sha,
              "source_ronin_block": evidence["ronin_block"],
              "class_controls": len(controls), "nine_class_code_support": support,
              "class_plan_count": len(rows), "class_updated": len(rows) if args.apply else 0,
              "level_updated": 0,
              "class_results": {aid: name for aid, name in rows},
              "backup": str(backup_path) if backup_path else None,
              "network_calls": 0, "finance_writes": 0,
              "verified_financial_totals": "UNKNOWN", "unified_finance": "HOLD",
              "checkpoint96": "OPEN"}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V016_Offline_Class_Apply_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    jp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    mp.write_text("\n".join(["# AxieOS V0.16 offline class application", "",
        f"Status: **{status}**. Class plan: **29/29**; class updated: **{report['class_updated']}/29**; "
        "level updated: **0/29**.",
        f"All nine gene class codes agree across **{len(controls)}** saved controls.",
        f"Evidence SHA-256: `{evidence_sha}`. Backup: `{backup_path or 'none'}`.", "",
        "Database changes are limited to the 29 previously NULL class fields and provenance/timestamp.",
        "Network calls: **0**. Finance totals: **UNKNOWN**; Unified Finance: **HOLD**; "
        "Checkpoint 96: **OPEN**.", ""]), encoding="utf-8")
    print("AXIEOS V0.16 - OFFLINE GENE CLASS APPLY")
    print(f"Status: {status} | Controls: {len(controls)} / nine classes | Class: {report['class_updated']}/29 | Level: 0/29")
    print(f"Reports: {jp} {mp} | Backup: {backup_path or 'none'}")
    print("Network: 0 | Finance totals: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
