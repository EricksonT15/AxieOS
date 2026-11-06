#!/usr/bin/env python3
r"""Validate the scoped V0.16 evidence, update two docs, optionally commit.

Save as scripts/AxieOS_V016_Final_Closeout.py in the AxieOS repository.
From VS PowerShell at the repository root run:
    py -B .\scripts\AxieOS_V016_Final_Closeout.py --commit

The script reads JSON reports and Markdown only. It does not open the database,
call a network service, push Git, or accept portfolio financial totals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START = "<!-- AXIEOS_V016_SCOPED_CLOSEOUT_START -->"
END = "<!-- AXIEOS_V016_SCOPED_CLOSEOUT_END -->"
SUMMARY = "AxieOS V0.16 scoped operational and trade evidence closeout"


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError("STOP: " + message)


def load(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing report: {path}")
    raw = path.read_bytes()
    doc = json.loads(raw.decode("utf-8-sig"))
    require(isinstance(doc, dict), f"expected JSON object: {path}")
    return doc, hashlib.sha256(raw).hexdigest()


def report_from_ref(folder: Path, ref: dict) -> dict:
    name, digest = ref.get("filename"), ref.get("sha256")
    require(isinstance(name, str) and Path(name).name == name and name.endswith(".json") and
            isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest),
            "dashboard report reference malformed")
    path = folder / name
    doc, found = load(path)
    require(found == digest, f"referenced report changed: {path}")
    return doc


def latest_bs(folder: Path) -> tuple[Path, dict, str]:
    require(folder.is_dir(), f"Task136BS folder absent: {folder}")
    candidates = []
    for path in folder.glob("AxieOS_V014_Task136BS_Legacy_Consumable_Crosswalk_*.json"):
        doc, sha = load(path)
        if doc.get("task") == "136BS" and doc.get("refresh_coverage"):
            candidates.append((path, doc, sha))
    require(len(candidates) == 1, "expected one Task136BS JSON with refresh coverage")
    return candidates[0]


def evidence(repo: Path) -> dict:
    dash_path = repo / "reports/axieos_v016/dashboards/AxieOS_V016_Operational_Dashboard_2026-11-05_all.json"
    dash, dash_sha = load(dash_path)
    roster, klass, trades = (dash.get("catchup_source", {}),
                             dash.get("new_axie_class_coverage", {}),
                             dash.get("scoped_closed_trades", {}))
    require(dash.get("version") == "0.16" and dash.get("as_of_philippines_date") == "2026-11-05" and
            len(dash.get("views", [])) == 3 and
            dash.get("verified_financial_totals") == "UNKNOWN" and
            dash.get("unified_finance") == "HOLD" and dash.get("checkpoint96") == "OPEN" and
            dash.get("database_opened") == "READ_ONLY" and
            dash.get("database_writes") == dash.get("network_calls") == 0,
            "V0.16 dashboard scope or financial boundary differs")
    require(roster.get("status") == "POST_APPLY_ROSTER_RECONCILED" and
            roster.get("chain_owned_count") == 162 and
            klass.get("status") == "APPLIED_CLASS_RECONCILED" and
            klass.get("cohort_axies") == klass.get("class_known") == klass.get("level_unknown") == 29 and
            klass.get("class_unknown") == klass.get("breed_unknown") == 0 and
            trades.get("status") == "CORROBORATED_SCOPED_WALLET_FLOW" and
            trades.get("source_pairs") == trades.get("pairs_through_as_of") == 26,
            "dashboard ownership, class or trade status differs")
    require(Decimal(trades["observed_weth_difference_before_gas"]) ==
            Decimal("0.000155213253102621") and
            Decimal(trades["candidate_purchase_gas_ron"]) ==
            Decimal("0.160638235692803757"), "scoped wallet-flow amounts differ")

    class_report = report_from_ref(repo / "reports/axieos_v016/onchain_class", klass)
    trade_report = report_from_ref(repo / "reports/axieos_v016/scoped_closeout", trades)
    require(class_report.get("version") == "0.16" and
            class_report.get("task") == "OFFLINE_GENE_CLASS_APPLY" and
            class_report.get("status") == "APPLIED_AND_RECONCILED" and
            class_report.get("class_controls") == 133 and
            class_report.get("class_updated") == 29 and
            class_report.get("level_updated") == class_report.get("finance_writes") == 0 and
            class_report.get("checkpoint96") == "OPEN", "class application report differs")
    require(trade_report.get("task") == "SCOPED_CLOSED_TRADE_CLOSEOUT" and
            trade_report.get("scope_status") == "COMPLETE_FOR_REPOSITORY_REVIEW" and
            trade_report.get("coverage", {}).get("pair_count") == 26 and
            trade_report.get("accepted_profit") is None and
            trade_report.get("verified_php_recovery") is None and
            trade_report.get("unified_finance") == "HOLD" and
            trade_report.get("checkpoint96") == "OPEN", "trade closeout report differs")
    require(Decimal(trade_report["coverage"]["observed_weth_difference_before_gas"]) ==
            Decimal(trades["observed_weth_difference_before_gas"]) and
            Decimal(trade_report["coverage"]["purchase_gas_ron_candidate"]) ==
            Decimal(trades["candidate_purchase_gas_ron"]), "dashboard and trade report differ")

    bs_path, bs, bs_sha = latest_bs(repo / "reports/axieos_v014/task136bs")
    old, fresh, summary = bs.get("summary", {}), bs.get("refresh_coverage", {}), bs.get("sources", {})
    require(bs.get("financial_totals") == "UNKNOWN" and bs.get("checkpoint96") == "OPEN" and
            bs.get("database_writes") == bs.get("network_calls") == 0 and
            old.get("candidate_purchase_hashes") == 116 and
            old.get("legacy_vs_136bo_purchase_hash_overlap") == 0 and
            old.get("legacy_vs_136bm_basis_sale_hash_overlap") == 0 and
            old.get("136bm_sale_basis_conflicts") == 24 and
            fresh.get("rows") == 598 and
            fresh.get("earliest_utc") == "2026-05-13T05:49:15+00:00" and
            fresh.get("latest_utc") == "2026-07-06T01:51:07+00:00" and
            old.get("last_utc", "").startswith("2026-03-03") and
            isinstance(summary.get("refresh", {}).get("sha256"), str),
            "Task136BS refreshed export or uncertainty boundary differs")
    require(bs_path.with_suffix(".md").is_file(), "paired Task136BS Markdown absent")
    return {"dashboard": (dash_path, dash_sha), "class": klass,
            "trades": trades, "basis": (bs_path, bs_sha)}


def section(repo: Path, data: dict) -> str:
    dashboard, dashboard_sha = data["dashboard"]
    bs_path, bs_sha = data["basis"]
    return "\n".join([
        START,
        "## V0.16 — Scoped operational closeout (2026-11-05)",
        "",
        "**Status: scoped operational dashboard and closed-trade evidence complete for repository release.** "
        "Unified Finance remains **HOLD**; Checkpoint 96 remains **OPEN**.",
        "This dated closeout governs current scoped status. Older release and next-task lines below "
        "remain historical records.",
        "",
        "- Pinned chain ownership: **162 Axies**; the guarded roster is reconciled to its saved snapshot.",
        "- New Axie cohort: **29/29 classes** reconciled from gene evidence validated against **133 controls / nine classes**. "
        "The **29 levels remain UNKNOWN**. No level values were inferred from unreliable contract readings.",
        "- Closed Axie trades: **26/26** corroborated purchase/sale wallet flows. Observed WETH difference before gas "
        "is **0.000155213253102621 WETH**; candidate purchase gas is **0.160638235692803757 RON**. "
        "Neither amount is accepted all-time profit or a verified portfolio expense.",
        "- Task136BS refresh coverage: legacy export ends **2026-03-03**; the separate 598-row refresh begins "
        "**2026-05-13**. The intervening period is reported inactivity consistent with the saved exports. "
        "The **24 consumable sale-basis conflicts** remain unresolved.",
        "- Verified all-time income, expenses, realized profit, PHP recovery and complete gas: **UNKNOWN**. "
        "No automatic sale, release or financial acceptance follows from this scoped milestone.",
        "",
        f"Evidence: `{dashboard.relative_to(repo).as_posix()}` (SHA-256 `{dashboard_sha}`); "
        f"`{bs_path.relative_to(repo).as_posix()}` (SHA-256 `{bs_sha}`). "
        "The dashboard carries SHA-matched references to the class application and closed-trade closeout reports.",
        END,
    ]) + "\n"


def insert(text: str, block: str) -> str:
    require(text.startswith("# "), "documentation title not found")
    require(text.count(START) == text.count(END) and text.count(START) <= 1,
            "existing V0.16 closeout markers ambiguous")
    if START in text:
        a, b = text.index(START), text.index(END) + len(END)
        require(a < b, "closeout markers reversed")
        return text[:a] + block.rstrip("\n") + text[b:]
    first_line = text.find("\n")
    require(first_line > 0, "documentation title incomplete")
    return text[:first_line + 1] + "\n" + block + "\n" + text[first_line + 1:]


def command(repo: Path, *parts: str) -> list[str]:
    run = subprocess.run(["git", *parts], cwd=repo, text=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    require(run.returncode == 0, f"git {' '.join(parts)} failed: "
            f"{(run.stdout + run.stderr).strip()}")
    return run.stdout.splitlines()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--commit", action="store_true", help="make one targeted local commit; never push")
    args = parser.parse_args()
    repo = args.repo.resolve()
    context = repo / "LLM_Project_Context.md"
    roadmap = repo / "docs/Engineering/ROADMAP.md"
    closeout = repo / "docs/Engineering/AxieOS_V016_Final_Scoped_Closeout.md"
    script = repo / "scripts/AxieOS_V016_Final_Closeout.py"
    require(context.is_file() and roadmap.is_file(), "canonical documentation files absent")
    if args.commit:
        require(script.is_file(), f"save this plain Python file at {script} first")
        require(not command(repo, "diff", "--cached", "--name-only"),
                "other staged changes exist; leave them out of this targeted commit")
    data = evidence(repo)
    block = section(repo, data)
    originals = {context: context.read_bytes(), roadmap: roadmap.read_bytes()}
    output = {}
    for path, raw in originals.items():
        text = raw.decode("utf-8-sig")
        require("\x00" not in text, f"invalid Markdown: {path}")
        # Preserve pre-existing line ending convention.
        newline = "\r\n" if b"\r\n" in raw else "\n"
        content = insert(text, block).replace("\r\n", "\n").replace("\n", newline)
        output[path] = (b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b"") + content.encode("utf-8")
    closeout_text = "# AxieOS V0.16 — Final scoped closeout\n\n" + block
    files = {**output, closeout: closeout_text.encode("utf-8")}
    changes = [p for p, raw in files.items() if not p.is_file() or p.read_bytes() != raw]
    if changes:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        backup_dir = Path.home() / "AxieOSBackups" / "documentation" / f"v016_closeout_{stamp}"
        backup_dir.mkdir(parents=True, exist_ok=False)
        for path in changes:
            if path.is_file():
                shutil.copy2(path, backup_dir / path.name)
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_name(path.name + ".v016.tmp")
            temp.write_bytes(files[path])
            temp.replace(path)
    selected = [context, roadmap, closeout, data["basis"][0],
                data["basis"][0].with_suffix(".md")]
    if args.commit:
        selected.append(script)
        rel = [p.relative_to(repo).as_posix() for p in selected]
        command(repo, "add", "--", *rel)
        staged = command(repo, "diff", "--cached", "--name-only")
        require(set(staged) <= set(rel), "unexpected staged files; commit stopped")
        require(staged, "no documentation or evidence changes to commit")
        command(repo, "diff", "--cached", "--check")
        command(repo, "commit", "-m", SUMMARY)
        print("Local commit:", command(repo, "rev-parse", "--short", "HEAD")[0])
        print("GitHub push: NO — use GitHub Desktop Push origin")
    print("AXIEOS V0.16 - FINAL SCOPED CLOSEOUT")
    print("Ownership: 162 | New classes: 29/29 | Levels unknown: 29 | Closed trade pairs: 26")
    print("Task136BS: 598-row refresh checked | Reported inactivity: 2026-03-04 through 2026-05-12 | Basis conflicts: 24")
    print("Documentation:", context, roadmap, closeout)
    print("Files updated:", len(changes), "| Database opened: NO | Network: 0")
    print("Financial totals: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
