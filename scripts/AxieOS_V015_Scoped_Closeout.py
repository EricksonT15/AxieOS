r"""Validate and locally commit the V0.15 scoped operational milestone.

Save in scripts/AxieOS_V015_Scoped_Closeout.py. From the repository root:
    py -B .\scripts\AxieOS_V015_Scoped_Closeout.py --commit

Checks pinned source links and current SQLite state read-only, refreshes the
offline dashboard, writes one closeout note, and commits only the exact V0.15
source/evidence files. Does not push; use GitHub Desktop to push the commit.
No production DB write or network call.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from contextlib import closing
from datetime import date
from pathlib import Path

import AxieOS_V015_Source_Reconciliation as prior


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "reports/axieos_v015/source_catchup"
DASH_DIR = ROOT / "reports/axieos_v015/dashboards"
DOC = ROOT / "docs/Engineering/AxieOS_V015_Scoped_Operational_Closeout.md"
CATCHUP = SOURCE_DIR / "AxieOS_V015_Source_Catchup_20261105T030132_927019Z.json"
RECON = SOURCE_DIR / "AxieOS_V015_Source_Reconciliation_20261105T033632_937141Z.json"
OWNERSHIP = SOURCE_DIR / "AxieOS_V015_Ownership_Evidence_20261105T034538_032864Z.json"
DASH = DASH_DIR / "AxieOS_V015_Operational_Dashboard_2026-11-05_all.json"
SCRIPTS = (
    "AxieOS_V015_Source_Catchup.py",
    "AxieOS_V015_Source_Reconciliation.py",
    "AxieOS_V015_Guarded_Raw_Import.py",
    "AxieOS_V015_Ownership_Evidence_Batch.py",
    "AxieOS_V015_Guarded_Roster_Refresh.py",
    "AxieOS_V015_Onchain_Core_Enrichment.py",
    "AxieOS_V015_Operational_Dashboard.py",
    "AxieOS_V015_Scoped_Closeout.py",
)


def require(ok, reason):
    prior.require(ok, reason)


def read(path, task=None):
    require(path.is_file(), f"report missing: {path}")
    raw = path.read_bytes()
    doc = json.loads(raw.decode("utf-8-sig"))
    require(isinstance(doc, dict) and (task is None or doc.get("task") == task),
            f"unexpected report: {path}")
    return doc, hashlib.sha256(raw).hexdigest()


def latest_applied(prefix, statuses):
    matches = sorted(SOURCE_DIR.glob(prefix + "*.json"), reverse=True)
    for path in matches:
        try:
            doc, digest = read(path)
        except (OSError, ValueError, TypeError):
            continue
        if doc.get("status") in statuses:
            return path, doc, digest
    raise ValueError(f"STOP: applied {prefix} report missing")


def check_report_pair(path, csv=False):
    paths = [path, path.with_suffix(".md")]
    if csv:
        paths.append(path.with_suffix(".csv"))
    require(all(p.is_file() for p in paths), f"JSON/Markdown/CSV report pair incomplete: {path}")
    return paths


def check_sources():
    catch, catch_sha = prior.load_source(CATCHUP)
    recon, recon_sha = read(RECON, "SOURCE_RECONCILIATION")
    own, own_sha = read(OWNERSHIP, "OWNERSHIP_EVIDENCE_BATCH")
    raw_p, raw, raw_sha = latest_applied("AxieOS_V015_Guarded_Raw_Import_", {"APPLIED_AND_RECONCILED"})
    roster_p, roster, roster_sha = latest_applied("AxieOS_V015_Guarded_Roster_Refresh_", {"APPLIED_AND_RECONCILED"})
    core_p, core, core_sha = latest_applied("AxieOS_V015_Onchain_Core_Enrichment_",
                                           {"PARTIAL_APPLIED_AND_RECONCILED", "APPLIED_AND_RECONCILED"})
    require(recon["source"]["sha256"] == catch_sha and
            own["sources"]["catchup_sha256"] == catch_sha and
            own["sources"]["reconciliation_sha256"] == recon_sha and
            raw.get("source_catchup_sha256") == catch_sha and
            raw.get("source_reconciliation_sha256") == recon_sha and
            roster.get("sources", {}).get("catchup_sha256") == catch_sha and
            roster.get("sources", {}).get("reconciliation_sha256") == recon_sha and
            roster.get("sources", {}).get("evidence_sha256") == own_sha and
            core.get("source_sha256") == roster_sha,
            "source report hashes do not form the expected chain")
    ids = roster.get("metadata_unknown_ids")
    require(catch["owned_inventory"]["status"] == "COMPLETE_AT_PINNED_BLOCK" and
            catch["owned_inventory"]["chain_owned_count"] == 162 and
            catch["owned_inventory"]["saved_owned_rows"] == 136 and
            set(catch["owned_inventory"]["chain_only_ids"]) == set(ids or []) and
            len(ids or []) == 29 and len(catch["owned_inventory"]["saved_only_ids"]) == 3 and
            own.get("saved_only_complete_histories") == 3 and
            raw.get("raw_before") == 1193 and raw.get("raw_after") == 1196 and
            raw.get("raw_rows_inserted") == 3 and raw.get("database_writes") == 3 and
            roster.get("fresh_chain_owned") == 162 and roster.get("chain_only_inserted") == 29 and
            roster.get("saved_only_to_unknown") == 3 and roster.get("metadata_validated") == 0 and
            roster.get("database_writes") == 32 and
            core.get("target_axies") == 29 and core.get("breed_count_validated") == 29 and
            core.get("level_validated") == 0 and core.get("control_breed_matches") == 8 and
            core.get("control_level_matches") == 1 and core.get("roster_updates") == 29 and
            core.get("database_writes") == 29 and core.get("class_still_unknown") == 29 and
            all(d.get("finance_writes") == 0 and d.get("unified_finance") == "HOLD" and
                d.get("checkpoint96") == "OPEN" for d in (raw, roster, core)),
            "scope counts, applied statuses, or finance boundary differ")
    for doc in (raw, roster, core):
        require(bool(doc.get("backup")) and Path(doc["backup"]).is_file(),
                "one verified backup is missing outside repository")
    return {"catchup": (CATCHUP, catch_sha), "reconciliation": (RECON, recon_sha),
            "ownership": (OWNERSHIP, own_sha), "raw": (raw_p, raw_sha),
            "roster": (roster_p, roster_sha), "core": (core_p, core_sha)}, catch, recon, roster, core


def check_database(db, catch, recon, roster, core):
    ids = sorted(roster["metadata_unknown_ids"], key=int)
    with closing(prior.open_ro(db)) as conn:
        require(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                not conn.execute("PRAGMA foreign_key_check").fetchall(), "SQLite integrity differs")
        require(conn.execute("SELECT count(*) FROM ronin_api_transactions_raw").fetchone()[0] == 1196,
                "raw transaction row count differs")
        require(conn.execute("SELECT count(*) FROM gameplay_owned_axies WHERE ownership_status='OWNED'").fetchone()[0] == 162,
                "saved OWNED roster count differs")
        targets = conn.execute("SELECT axie_id,wallet_address,ownership_status,axie_class,level,breed_count "
                               "FROM gameplay_owned_axies WHERE axie_id IN (" +
                               ",".join("?" for _ in ids) + ")", ids).fetchall()
        require(len(targets) == 29 and len({str(r[0]) for r in targets}) == 29 and
                all(r[1] == "0x1ed8b3f3bd6a624de47f81beea101f0d15cdfbc8" and
                    r[2] == "OWNED" and r[3] is None and r[4] is None and
                    type(r[5]) is int and 0 <= r[5] <= 7 for r in targets),
                "current target metadata differs from core enrichment")
        saved_only = catch["owned_inventory"]["saved_only_ids"]
        statuses = conn.execute("SELECT axie_id,ownership_status FROM gameplay_owned_axies WHERE axie_id IN (?,?,?)",
                                tuple(saved_only)).fetchall()
        require(len(statuses) == 3 and {str(r[0]) for r in statuses} == set(saved_only) and
                all(r[1] == "UNKNOWN" for r in statuses), "three stale Axie statuses differ")
        hashes = [r["tx_hash"] for r in recon["raw_transaction_rehearsal"]["candidate_raw_transaction_rows"]]
        require(len(hashes) == 3 and all(conn.execute(
            "SELECT count(*) FROM ronin_api_transactions_raw WHERE lower(tx_hash)=?", (h.lower(),)).fetchone()[0] == 1
            for h in hashes), "exact raw transaction hashes missing")


def refresh_dashboard():
    script = ROOT / "scripts/AxieOS_V015_Operational_Dashboard.py"
    require(script.is_file(), "V0.15 dashboard script missing")
    subprocess.run([sys.executable, "-B", str(script), "--period", "all",
                    "--as-of", "2026-11-05"], cwd=ROOT, check=True)
    dashboard, _sha = read(DASH)
    snap = dashboard.get("catchup_source", {})
    require(dashboard.get("version") == "0.15" and
            dashboard.get("as_of_philippines_date") == "2026-11-05" and
            snap.get("status") == "POST_APPLY_ROSTER_RECONCILED" and
            snap.get("chain_owned_count") == 162 and
            len(snap.get("metadata_unknown_ids", [])) == 29 and
            dashboard.get("database_writes") == 0 and dashboard.get("network_calls") == 0 and
            dashboard.get("verified_financial_totals") == "UNKNOWN" and
            dashboard.get("unified_finance") == "HOLD" and dashboard.get("checkpoint96") == "OPEN",
            "refreshed operational dashboard differs")
    return dashboard


def note(sources, core):
    lines = ["# AxieOS V0.15 — Scoped Operational Closeout", "",
        "**Date:** 2026-11-05 (Philippines)",
        "**Status:** Scoped operational milestone ready for repository release.",
        "**Unified Finance:** HOLD. **Checkpoint 96:** OPEN.", "",
        "## Reconciled scope", "",
        "- A pinned Ronin snapshot found 162 owned Axies. The guarded roster refresh added 29 OWNED rows and changed three stale OWNED rows to UNKNOWN.",
        "- Three missing raw transaction details were imported with backup and exact post-apply reconciliation. Raw transaction rows are now 1,196.",
        "- On-chain core evidence and eight breed controls support breed counts for all 29 new Axies. Class and level remain UNKNOWN for all 29; only one of eight saved-level controls matched current contract levels.",
        "- The read-only operational dashboard recognizes the post-apply roster and reports the dated 162-Axie snapshot.", "",
        "## Evidence retained", ""]
    for name, (path, digest) in sources.items():
        lines.append(f"- {name.replace('_', ' ').title()}: `{path.relative_to(ROOT).as_posix()}` (SHA-256 `{digest}`).")
    lines += [f"- Dashboard: `{DASH.relative_to(ROOT).as_posix()}`.", "",
        "Production backups are outside the repository; their paths are recorded in the applied reports.", "",
        "## Open boundaries", "",
        "- Class and level for the 29 new Axies require a separate authoritative source. Contract level zero and mismatched control levels were not treated as gameplay level.",
        "- Acquisition basis, consumable opening inventory, complete gas, verified income and expenses, realized profit, and PHP capital recovery remain UNKNOWN.",
        "- This milestone does not accept or run legacy accounting writers, approve marketplace actions, or close Unified Finance or Checkpoint 96.", "",
        "Run the operational dashboard again when activity changes; this report is a dated snapshot, not continuous live synchronization.", ""]
    return "\n".join(lines)


def run_git(args):
    proc = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    require(proc.returncode == 0, f"git {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout.strip()


def git_commit(files):
    require(Path(run_git(["rev-parse", "--show-toplevel"])).resolve() == ROOT.resolve(),
            "current script is not running inside the intended repository")
    paths = [p.relative_to(ROOT).as_posix() for p in files]
    run_git(["add", "--", *paths])
    run_git(["diff", "--cached", "--check", "--", *paths])
    changed = run_git(["diff", "--cached", "--name-only", "--", *paths]).splitlines()
    require(bool(changed), "no scoped V0.15 changes to commit")
    run_git(["commit", "--only", "-m", "Close scoped V0.15 operational source catch-up", "--", *paths])
    committed = set(run_git(["show", "--pretty=format:", "--name-only", "HEAD"]).splitlines())
    require(committed and committed <= set(paths), "commit included an unexpected path")
    return run_git(["rev-parse", "--short", "HEAD"]), len(committed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=prior.DEFAULT_DB)
    parser.add_argument("--commit", action="store_true", help="Create a local scoped commit; push in GitHub Desktop")
    args = parser.parse_args()
    sources, catch, recon, roster, core = check_sources()
    check_database(args.db.expanduser().resolve(), catch, recon, roster, core)
    refresh_dashboard()
    DOC.parent.mkdir(parents=True, exist_ok=True)
    content = note(sources, core)
    DOC.write_text(content, encoding="utf-8")
    files = [ROOT / "scripts" / s for s in SCRIPTS] + [DOC]
    for name, (path, _digest) in sources.items():
        files.extend(check_report_pair(path, csv=name in {"reconciliation", "ownership"}))
    files += check_report_pair(DASH)
    require(all(p.is_file() and p.resolve().is_relative_to(ROOT.resolve()) for p in files),
            "scoped file manifest contains a missing or external file")
    commit, count = git_commit(files) if args.commit else (None, 0)
    print("AXIEOS V0.15 - SCOPED OPERATIONAL CLOSEOUT")
    print("Ownership: 162 | Raw: 1196 | New breed: 29/29 | Level/class: UNKNOWN 29")
    print(f"Documentation: {DOC}")
    print(f"Local commit: {commit or 'NO'} | Committed files: {count} | GitHub push: NO")
    print("Verified financial totals: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
