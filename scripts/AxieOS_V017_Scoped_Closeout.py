#!/usr/bin/env python3
r"""Verify V0.17 raw catch-up and create one targeted local closeout commit.

Save this plain file as scripts/AxieOS_V017_Scoped_Closeout.py. At the AxieOS
repository root in PowerShell run:
    py -B .\scripts\AxieOS_V017_Scoped_Closeout.py --commit

Reads the production database and its guarded backup only. Does not sync,
classify, write to the database, access the network, or push to GitHub.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from contextlib import closing
from pathlib import Path

import AxieOS_V015_Source_Reconciliation as prior
import AxieOS_V017_Gap_Batch as gap


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/axieos_v017/operational_refresh/AxieOS_V017_Operational_Refresh_20261105T093034_504070Z.json"
APPLIED = ROOT / "reports/axieos_v017/operational_refresh/AxieOS_V017_Gap_Batch_20261105T095321_944253Z.json"
OUT = ROOT / "reports/axieos_v017/operational_refresh"
DOC = ROOT / "docs/Engineering/AxieOS_V017_Scoped_Operational_Closeout.md"
CONTEXT = ROOT / "LLM_Project_Context.md"
ROADMAP = ROOT / "docs/Engineering/ROADMAP.md"
START = "<!-- AXIEOS_V017_SCOPED_CLOSEOUT_START -->"
END = "<!-- AXIEOS_V017_SCOPED_CLOSEOUT_END -->"
TX, TF = gap.TX, gap.TF


def require(condition, message):
    if not condition:
        raise ValueError("STOP: " + message)


def json_file(path):
    require(path.is_file(), f"missing source report: {path}")
    raw = path.read_bytes()
    doc = json.loads(raw.decode("utf-8-sig"))
    require(isinstance(doc, dict), f"invalid source report: {path}")
    require(path.with_suffix(".md").is_file(), f"paired Markdown missing: {path}")
    return doc, hashlib.sha256(raw).hexdigest()


def git(repo, *args):
    run = subprocess.run(["git", *args], cwd=repo, text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(run.returncode == 0, f"git {' '.join(args)} failed: {(run.stdout + run.stderr).strip()}")
    return run.stdout.splitlines()


def verify(repo, db, source_path, applied_path):
    source, source_sha = json_file(source_path)
    applied, applied_sha = json_file(applied_path)
    own, coverage = source.get("ownership", {}), source.get("raw_coverage", {})
    require(source.get("version") == "0.17" and source.get("task") == "OPERATIONAL_SOURCE_REFRESH" and
            own.get("status") == "COMPLETE_AT_PINNED_BLOCK" and
            own.get("saved_owned_count") == own.get("pinned_chain_owned_count") == 162 and
            own.get("chain_only_ids") == own.get("saved_only_ids") == [] and
            coverage.get("all_four_complete") is True and len(coverage.get("routes", [])) == 4 and
            source.get("database_writes") == 0 and source.get("finance", {}).get("unified_finance") == "HOLD" and
            source.get("finance", {}).get("checkpoint96") == "OPEN",
            "V0.17 source ownership, routes, or finance boundary differs")
    tx_hashes = coverage.get("transaction_hashes_absent_from_raw")
    tf_hashes = coverage.get("transfer_hashes_absent_from_raw")
    require(isinstance(tx_hashes, list) and len(tx_hashes) == len(set(tx_hashes)) == 7 and
            isinstance(tf_hashes, list) and len(tf_hashes) == len(set(tf_hashes)) == 6 and
            all(isinstance(h, str) and gap.HASH.fullmatch(h) for h in tx_hashes + tf_hashes),
            "original raw gap hash sets differ")
    require(applied.get("version") == "0.17" and applied.get("task") == "GUARDED_RAW_GAP_BATCH" and
            applied.get("status") == "APPLIED_AND_RECONCILED" and
            applied.get("source") == {"filename": source_path.name, "sha256": source_sha} and
            applied.get("source_sha256") == source_sha and
            applied.get("rows") == {TX: 7, TF: 7} and
            applied.get("clone_first") == {TX: 7, TF: 7} and
            applied.get("clone_second") == {TX: 0, TF: 0} and
            applied.get("raw_writes") == {TX: 7, TF: 7} and
            applied.get("production_writes") == 14 and
            applied.get("ownership_differences", {}).get("chain_only_ids") == [] and
            applied.get("ownership_differences", {}).get("saved_only_ids") == [] and
            applied.get("ledger_writes") == applied.get("roster_writes") == applied.get("finance_writes") == 0 and
            applied.get("verified_financial_totals") == "UNKNOWN" and
            applied.get("unified_finance") == "HOLD" and applied.get("checkpoint96") == "OPEN" and
            isinstance(applied.get("plan_sha256"), str) and
            re.fullmatch(r"[0-9a-f]{64}", applied["plan_sha256"]),
            "applied report, source link, or guarded counts differ")
    backup = Path(applied["backup"])
    require(backup.is_file() and backup.resolve() != db.resolve() and
            not backup.resolve().is_relative_to(repo.resolve()), "guarded backup missing or inside repository")

    with closing(prior.open_ro(backup)) as old, closing(prior.open_ro(db)) as new:
        require(old.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                new.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                not old.execute("PRAGMA foreign_key_check").fetchall() and
                not new.execute("PRAGMA foreign_key_check").fetchall(), "database integrity differs")
        require(all(prior.snapshot_table(old, t) == prior.snapshot_table(new, t)
                    for t in prior.WATCHED if t not in (TX, TF)),
                "ledger, ownership, or protected accounting differs from backup")
        plan = {}
        for table, expected, hashes in ((TX, 7, set(tx_hashes)), (TF, 7, set(tf_hashes))):
            fields = gap.FIELDS[table]
            require(set(fields) <= prior.table_columns(new, table) and
                    set(fields) <= prior.table_columns(old, table), f"{table}: schema changed")
            col = "tx_hash"
            rows = new.execute("SELECT " + ",".join(fields) + " FROM " + table + " ORDER BY " + fields[0]).fetchall()
            hash_col = fields.index(col)
            inserted = [row for row in rows if str(row[hash_col]).lower() in hashes]
            require(len(inserted) == expected and
                    {str(row[hash_col]).lower() for row in inserted} == hashes and
                    all(str(row[0]).lower() not in {str(r[0]).lower() for r in
                            old.execute("SELECT " + fields[0] + " FROM " + table)} for row in inserted),
                    f"{table}: exact guarded rows missing or present in backup")
            require(prior.snapshot_table(new, table, hashes) == prior.snapshot_table(old, table) and
                    prior.snapshot_table(new, table)["rows"] - prior.snapshot_table(old, table)["rows"] == expected,
                    f"{table}: prior rows changed or unreported raw rows added")
            plan[table] = [tuple(r) for r in inserted]
        plan_sha = hashlib.sha256(json.dumps(plan, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
        require(plan_sha == applied["plan_sha256"], "production inserted rows do not match applied plan SHA")
        owned = {str(r[0]) for r in new.execute("SELECT axie_id FROM gameplay_owned_axies "
                                                "WHERE ownership_status='OWNED'")}
        require(len(owned) == 162 and len(owned) == len(set(owned)), "saved roster changed")
        metadata = source.get("metadata", {})
        require(len(metadata.get("class_unknown_ids", [])) == 0 and
                len(metadata.get("level_unknown_ids", [])) == 29 and
                len(metadata.get("breed_unknown_ids", [])) == 0,
                "metadata gap differs from source")
    return source_sha, applied_sha, backup


def block(source_path, source_sha, applied_path, applied_sha):
    return "\n".join([
        START,
        "## V0.17 — Scoped operational raw catch-up (2026-11-05)",
        "",
        "**Status: guarded operational raw catch-up reconciled for repository release.** "
        "Unified Finance remains **HOLD**; Checkpoint 96 remains **OPEN**.",
        "",
        "- Pinned and saved Axie IDs: **162/162**, with zero chain-only or saved-only IDs at the pinned block.",
        "- Four explorer routes complete; **7 raw transaction rows and 7 raw transfer rows** "
        "inserted after clone rehearsal and a persistent backup. The six missing transfer hashes "
        "accounted for seven transfer rows.",
        "- The post-apply comparison confirms the inserted plan SHA, preserves prior raw rows and "
        "all watched ledger, roster, classification and accounting tables.",
        "- Axie class and breed known for this cohort; **29 Axie levels remain UNKNOWN**. "
        "The V0.16 dashboard and 26 closed-trade pairs are dated, historical scoped evidence.",
        "- Verified all-time income, expenses, realized profit, PHP recovery and complete gas: **UNKNOWN**. "
        "The 24 consumable basis conflicts and historical export gap remain unresolved.",
        "",
        f"Sources: `{source_path.relative_to(ROOT).as_posix()}` (SHA-256 `{source_sha}`); "
        f"`{applied_path.relative_to(ROOT).as_posix()}` (SHA-256 `{applied_sha}`).",
        END,
        "",
    ])


def insert(text, section):
    require(text.startswith("# ") and text.count(START) == text.count(END) and text.count(START) <= 1,
            "documentation title or V0.17 markers ambiguous")
    if START in text:
        a, b = text.index(START), text.index(END) + len(END)
        require(a < b, "V0.17 markers reversed")
        return text[:a] + section.rstrip("\n") + text[b:]
    i = text.find("\n")
    require(i > 0, "documentation title incomplete")
    return text[:i + 1] + "\n" + section + "\n" + text[i + 1:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", action="store_true", help="targeted local Git commit, no push")
    parser.add_argument("--db", type=Path, default=gap.DB)
    args = parser.parse_args()
    script = ROOT / "scripts/AxieOS_V017_Scoped_Closeout.py"
    if args.commit:
        require(script.is_file(), f"save the Python file at {script}")
        require(not git(ROOT, "diff", "--cached", "--name-only"),
                "other changes staged; clear staging before this targeted commit")
        for path in (CONTEXT, ROADMAP):
            require(not git(ROOT, "status", "--porcelain", "--untracked-files=no", "--",
                            path.relative_to(ROOT).as_posix()),
                    f"documentation already has uncommitted edits: {path}")
    source_sha, applied_sha, backup = verify(ROOT, args.db, SOURCE, APPLIED)
    section = block(SOURCE, source_sha, APPLIED, applied_sha)
    require(CONTEXT.is_file() and ROADMAP.is_file(), "canonical documentation files missing")
    outputs = {}
    for path in (CONTEXT, ROADMAP):
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        newline = "\r\n" if b"\r\n" in raw else "\n"
        updated = insert(text, section).replace("\r\n", "\n").replace("\n", newline)
        outputs[path] = (b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + updated.encode("utf-8")
    outputs[DOC] = ("# AxieOS V0.17 — Scoped operational closeout\n\n" + section).encode("utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / "AxieOS_V017_Scoped_Operational_Closeout_20261105.json"
    report = {"project": "AxieOS", "version": "0.17", "task": "SCOPED_OPERATIONAL_CLOSEOUT",
              "status": "READY_FOR_REPOSITORY_RELEASE", "source_sha256": source_sha,
              "applied_sha256": applied_sha, "backup": str(backup),
              "owned_axies": 162, "raw_transactions_inserted": 7, "raw_transfers_inserted": 7,
              "levels_unknown": 29, "database_writes": 0, "network_calls": 0,
              "financial_totals": "UNKNOWN", "unified_finance": "HOLD", "checkpoint96": "OPEN"}
    outputs[report_path] = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    outputs[report_path.with_suffix(".md")] = ("# V0.17 scoped operational raw catch-up\n\n" + section).encode("utf-8")
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_file() or path.read_bytes() != content:
            temp = path.with_name(path.name + ".v017.tmp")
            temp.write_bytes(content)
            temp.replace(path)
    if args.commit:
        selected = [CONTEXT, ROADMAP, DOC, SOURCE, SOURCE.with_suffix(".md"), APPLIED,
                    APPLIED.with_suffix(".md"), report_path, report_path.with_suffix(".md"),
                    ROOT / "scripts/AxieOS_V017_Operational_Refresh.py",
                    ROOT / "scripts/AxieOS_V017_Gap_Batch.py", script]
        require(all(p.is_file() for p in selected), "V0.17 script, document or report missing")
        names = [p.relative_to(ROOT).as_posix() for p in selected]
        git(ROOT, "add", "--", *names)
        staged = git(ROOT, "diff", "--cached", "--name-only")
        require(set(staged) <= set(names) and staged, "staged scope differs or nothing to commit")
        git(ROOT, "diff", "--cached", "--check")
        git(ROOT, "commit", "-m", "Close scoped V0.17 operational raw catch-up")
        print("Local commit:", git(ROOT, "rev-parse", "--short", "HEAD")[0])
        print("GitHub push: NO — use GitHub Desktop Push origin")
    print("AXIEOS V0.17 - SCOPED OPERATIONAL CLOSEOUT")
    print("Ownership: 162/162 IDs | Raw transactions/transfers applied: 7/7 | Unknown levels: 29")
    print("Reconciled against backup:", backup)
    print("Documentation:", DOC, "| Report:", report_path)
    print("Database writes: 0 | Network: 0 | Finance: HOLD | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
