#!/usr/bin/env python3
r"""Validate and locally commit the scoped V1.0 no-spend pilot in one command.

Save as scripts/AxieOS_V100_Scoped_Closeout.py. From the AxieOS repo root:
    py -B .\scripts\AxieOS_V100_Scoped_Closeout.py --commit

Reads saved reports and Python source, updates Markdown documentation, and
commits only the named files. No database, network, GitHub push, finance
acceptance, Bounty Board play, or game action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_REL = Path("reports/axieos_v100/no_spend_review/"
                  "AxieOS_V100_NoSpend_Review_20261106T053750_094951Z.json")
DOC_REL = Path("docs/Engineering/AxieOS_V100_Scoped_NoSpend_Closeout.md")
OUT_REL = Path("reports/axieos_v100/scoped_closeout/"
                  "AxieOS_V100_Scoped_NoSpend_Closeout_2026-11-06.json")
CONTEXT_REL = Path("LLM_Project_Context.md")
ROADMAP_REL = Path("docs/Engineering/ROADMAP.md")
ADVISORY_REL = Path("scripts/AxieOS_V100_Advisory_Pilot.py")
REVIEW_REL = Path("scripts/AxieOS_V100_NoSpend_Review.py")
SELF_REL = Path("scripts/AxieOS_V100_Scoped_Closeout.py")
START = "<!-- AXIEOS_V100_SCOPED_NO_SPEND_START -->"
END = "<!-- AXIEOS_V100_SCOPED_NO_SPEND_END -->"


def require(ok, message):
    if not ok:
        raise ValueError("STOP: " + message)


def load(path):
    require(path.is_file(), f"missing source: {path}")
    raw = path.read_bytes()
    require(len(raw) < 25_000_000, f"source exceeds size cap: {path}")
    doc = json.loads(raw.decode("utf-8-sig"))
    require(isinstance(doc, dict), f"JSON object required: {path}")
    return doc, hashlib.sha256(raw).hexdigest()


def under(repo, value, label):
    path = Path(value).resolve()
    require(path.is_relative_to(repo) and path.is_file(), f"{label} missing or outside repository: {path}")
    return path


def verify(repo, report_path):
    report_path = under(repo, report_path, "no-spend report")
    report, digest = load(report_path)
    require(all(report_path.with_suffix(ext).is_file() for ext in (".md", ".csv")),
            "paired no-spend Markdown or CSV missing")
    counts, sync, dojo = (report.get("counts", {}), report.get("operational_sync", {}),
                          report.get("dojo_register", {}))
    require(report.get("version") == "1.0-pilot" and
            report.get("task") == "NO_SPEND_INVENTORY_REVIEW" and
            report.get("as_of_philippines_date") == "2026-11-06" and
            report.get("bounty_board") == "PAUSED_NO_OPERATING_FUNDS" and
            report.get("finance_totals") == "UNKNOWN" and
            report.get("unified_finance") == "HOLD" and report.get("checkpoint96") == "OPEN" and
            report.get("automatic_execution") is False and
            report.get("database_opened") == "READ_ONLY" and
            report.get("database_writes") == report.get("network_calls") == 0,
            "no-spend report boundary differs")
    require(counts.get("owned") == 162 and counts.get("exception_axies") == 29 and
            counts.get("missing_level") == 29 and
            counts.get("missing_class") == counts.get("missing_breed") == 0 and
            counts.get("recorded_collectibles") == 16 and
            counts.get("blank_collectible_type") == 16 and
            counts.get("collectibles_with_source_backed_traits") == 16 and
            all(counts.get(k) == 0 for k in
                ("collection_trait_missing", "collection_trait_source_review", "collection_status_conflict")),
            "owned roster, level or collection crosswalk differs")
    exceptions, collectibles = report.get("exception_rows"), report.get("collectible_rows")
    require(isinstance(exceptions, list) and len(exceptions) == 29 and
            len({r.get("axie_id") for r in exceptions}) == 29 and
            all(r.get("issues") == ["LEVEL_SOURCE_MISSING"] and r.get("level") is None
                and str(r.get("axie_id", "")).isdecimal() for r in exceptions),
            "unknown level exception rows differ")
    require(isinstance(collectibles, list) and len(collectibles) == 16 and
            len({r.get("axie_id") for r in collectibles}) == 16 and
            all(r.get("is_collectible_recorded") is True and r.get("collections") and
                r.get("collection_trait_sources") == ["RONIN_AXIE_GENES"] and
                not r.get("issues") for r in collectibles),
            "collection trait rows are not fully source-backed")
    require(sync.get("status") == "CURRENT_NO_WRITES" and
            sync.get("saved_owned_count") == 162 and sync.get("age_days") == 0 and
            sync.get("pinned_philippines_date") == "2026-11-06" and
            isinstance(sync.get("sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", sync["sha256"]),
            "operational sync summary differs")
    linked = under(repo, sync.get("path", ""), "linked operational sync")
    require(linked.with_suffix(".md").is_file(), "paired operational sync Markdown missing")
    linked_report, linked_sha = load(linked)
    require(linked_sha == sync["sha256"] and
            linked_report.get("task") == "REUSABLE_OPERATIONAL_SYNC" and
            linked_report.get("status") == "CURRENT_NO_WRITES" and
            linked_report.get("ownership", {}).get("saved_owned_count") == 162 and
            linked_report.get("ownership", {}).get("pinned_chain_owned_count") == 162 and
            linked_report.get("finance_totals") == "UNKNOWN" and
            linked_report.get("unified_finance") == "HOLD" and
            linked_report.get("checkpoint96") == "OPEN",
            "linked operational sync changed")
    require(dojo.get("status") == "HISTORICAL_ONLY_NO_CURRENT_ASSIGNMENT" and
            dojo.get("observation_dates") == ["2026-10-27"] and
            dojo.get("rows") == 5 and dojo.get("current_training_verified") is False and
            dojo.get("reassignment_authorized") is False,
            "Dojo history scope differs")
    historical = under(repo, dojo.get("source", ""), "historical Dojo register")
    require(hashlib.sha256(historical.read_bytes()).hexdigest() == dojo.get("sha256"),
            "historical Dojo register changed")
    advisory = under(repo, repo / ADVISORY_REL, "paused advisory source")
    review = under(repo, repo / REVIEW_REL, "no-spend review source")
    require("BOUNTY_PAUSED_NO_OPERATING_FUNDS" in advisory.read_text(encoding="utf-8-sig") and
            "--enable-bounty-review" in advisory.read_text(encoding="utf-8-sig"),
            "save the updated paused advisory script before closeout")
    require("gameplay_axie_traits" in review.read_text(encoding="utf-8-sig") and
            "collection_trait_sources" in review.read_text(encoding="utf-8-sig"),
            "save the corrected collection crosswalk script before closeout")
    return {"report_path": report_path, "report_sha256": digest,
            "sync_path": linked, "sync_sha256": linked_sha,
            "dojo_path": historical, "dojo_sha256": dojo["sha256"],
            "advisory_sha256": hashlib.sha256(advisory.read_bytes()).hexdigest(),
            "review_sha256": hashlib.sha256(review.read_bytes()).hexdigest()}


def section(repo, evidence):
    report = evidence["report_path"].relative_to(repo).as_posix()
    sync = evidence["sync_path"].relative_to(repo).as_posix()
    return "\n".join([
        START,
        "## V1.0 — Scoped read-only, no-spend pilot (2026-11-06)",
        "",
        "**Status: scoped pilot ready for repository review; full V1.0 is not closed.** "
        "Unified Finance remains **HOLD** and Checkpoint 96 remains **OPEN**.",
        "",
        "- Reconciled saved and pinned ownership: **162 Axies** at the dated block; "
        "the read-only inventory review reports **29 unknown levels** and zero missing class or breed values.",
        "- **16/16 recorded collectibles** have source-backed COLLECTION traits. The blank "
        "legacy `collectible_type` scalar is not an unresolved exception; collection labels may be multiple.",
        "- The five-row Dojo register was observed **2026-10-27** and does not establish current "
        "training or plot assignments. No reassignment is authorized.",
        "- Bounty Board advice is paused while operating funds are unavailable. No new capital, "
        "reroll, purchase, crafting, ascension, sale, or release is authorized.",
        "- Verified income, expenses, profit, PHP recovery and complete gas remain **UNKNOWN**. "
        "The 24 consumable basis conflicts and the historical source gap remain open.",
        "",
        f"Evidence: `{report}` (SHA-256 `{evidence['report_sha256']}`); "
        f"`{sync}` (SHA-256 `{evidence['sync_sha256']}`).",
        END,
        "",
    ])


def insert(original, block):
    require(original.startswith("# ") and original.count(START) == original.count(END) and
            original.count(START) <= 1, "canonical Markdown title or closeout markers ambiguous")
    if START in original:
        a, b = original.index(START), original.index(END) + len(END)
        require(a < b, "closeout markers reversed")
        return original[:a] + block.rstrip("\n") + original[b:]
    first = original.find("\n")
    require(first > 0, "canonical Markdown title incomplete")
    return original[:first + 1] + "\n" + block + "\n" + original[first + 1:]


def git(repo, *parts):
    run = subprocess.run(["git", *parts], cwd=repo, text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(run.returncode == 0,
            f"git {' '.join(parts)} failed: {(run.stdout + run.stderr).strip()[-1000:]}")
    return run.stdout.splitlines()


def write_docs(repo, evidence):
    block = section(repo, evidence)
    targets = [repo / CONTEXT_REL, repo / ROADMAP_REL]
    require(all(p.is_file() for p in targets), "canonical context or roadmap missing")
    outputs = {}
    for path in targets:
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        require("\x00" not in text, f"invalid Markdown: {path}")
        newline = "\r\n" if b"\r\n" in raw else "\n"
        updated = insert(text.replace("\r\n", "\n"), block).replace("\n", newline)
        outputs[path] = (b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + updated.encode("utf-8")
    outputs[repo / DOC_REL] = ("# AxieOS V1.0 — Scoped no-spend closeout\n\n" + block).encode("utf-8")
    closeout = {"project": "AxieOS", "version": "1.0-pilot", "task": "SCOPED_NO_SPEND_CLOSEOUT",
                "status": "READY_FOR_REPOSITORY_REVIEW", "as_of_philippines_date": "2026-11-06",
                "source_report": evidence["report_path"].relative_to(repo).as_posix(),
                "source_sha256": evidence["report_sha256"],
                "sync_sha256": evidence["sync_sha256"],
                "advisory_source_sha256": evidence["advisory_sha256"],
                "review_source_sha256": evidence["review_sha256"],
                "owned_axies": 162, "collection_traits_source_backed": 16,
                "unknown_levels": 29, "dojo_current_assignments_verified": False,
                "bounty_board": "PAUSED_NO_OPERATING_FUNDS", "financial_totals": "UNKNOWN",
                "unified_finance": "HOLD", "checkpoint96": "OPEN", "full_v100_closed": False,
                "database_opened": False, "database_writes": 0, "network_calls": 0}
    outputs[repo / OUT_REL] = (json.dumps(closeout, indent=2) + "\n").encode("utf-8")
    outputs[(repo / OUT_REL).with_suffix(".md")] = ("# AxieOS V1.0 scoped pilot evidence\n\n" + block).encode("utf-8")
    changed = [p for p, content in outputs.items() if not p.is_file() or p.read_bytes() != content]
    if any(p.is_file() and p in changed for p in targets):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        backup = Path.home() / "AxieOSBackups" / "documentation" / f"v100_scoped_{stamp}"
        backup.mkdir(parents=True, exist_ok=False)
        for path in targets:
            if path in changed:
                shutil.copy2(path, backup / path.name)
    for path in changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".v100.tmp")
        temp.write_bytes(outputs[path])
        temp.replace(path)
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--report", type=Path, default=REPORT_REL)
    parser.add_argument("--commit", action="store_true", help="make one targeted local commit; never push")
    args = parser.parse_args()
    repo = args.repo.resolve()
    report_path = args.report if args.report.is_absolute() else repo / args.report
    if args.commit:
        require(report_path.resolve() == (repo / REPORT_REL).resolve(),
                "--commit requires the pinned no-spend report; omit --report")
        require((repo / SELF_REL).is_file(), f"save this script at {repo / SELF_REL}")
        require(not git(repo, "diff", "--cached", "--name-only"),
                "other changes staged; clear staging before targeted commit")
        for rel in (CONTEXT_REL, ROADMAP_REL, DOC_REL):
            require(not git(repo, "status", "--porcelain", "--untracked-files=no", "--",
                            rel.as_posix()), f"documentation has prior edits: {rel}")
    evidence = verify(repo, report_path)
    changed = write_docs(repo, evidence)
    if args.commit:
        selected = [CONTEXT_REL, ROADMAP_REL, DOC_REL, OUT_REL, OUT_REL.with_suffix(".md"),
                    REPORT_REL, REPORT_REL.with_suffix(".md"), REPORT_REL.with_suffix(".csv"),
                    evidence["sync_path"].relative_to(repo),
                    evidence["sync_path"].with_suffix(".md").relative_to(repo),
                    ADVISORY_REL, REVIEW_REL, SELF_REL]
        names = [p.as_posix() for p in selected]
        require(all((repo / p).is_file() for p in selected), "selected closeout file missing")
        git(repo, "add", "--", *names)
        staged = git(repo, "diff", "--cached", "--name-only")
        require(staged and set(staged) <= set(names), "staged scope differs or nothing changed")
        git(repo, "diff", "--cached", "--check")
        git(repo, "commit", "-m", "Close scoped V1.0 no-spend pilot")
        print("Local commit:", git(repo, "rev-parse", "--short", "HEAD")[0])
        print("GitHub push: NO — use GitHub Desktop Push origin")
    print("AXIEOS V1.0 - SCOPED NO-SPEND CLOSEOUT")
    print("Owned: 162 | Source-backed collectibles: 16/16 | Unknown levels: 29")
    print("Documentation:", repo / DOC_REL, "| Closeout report:", repo / OUT_REL)
    print("Files updated:", len(changed), "| Database opened: NO | Network: 0")
    print("Bounty Board: PAUSED | Unified Finance: HOLD | Checkpoint 96: OPEN | Full V1.0: OPEN")


if __name__ == "__main__":
    main()
