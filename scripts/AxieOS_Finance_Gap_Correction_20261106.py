#!/usr/bin/env python3
r"""Correct the AxieOS V0.16/V0.17 historical-gap wording in one local commit.

Save as scripts/AxieOS_Finance_Gap_Correction_20261106.py and run from repo root:
    py -B .\scripts\AxieOS_Finance_Gap_Correction_20261106.py --commit

Uses the saved Task136BT report; no database or network access. Push the local
commit separately through GitHub Desktop.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
START = "<!-- AXIEOS_FINANCE_SOURCE_EXCEPTION_20261106_START -->"
END = "<!-- AXIEOS_FINANCE_SOURCE_EXCEPTION_20261106_END -->"


def require(ok, reason):
    if not ok:
        raise ValueError("STOP: " + reason)


def git(*parts):
    r = subprocess.run(["git", *parts], cwd=ROOT, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(r.returncode == 0, "git " + " ".join(parts) + ": " +
            (r.stdout + r.stderr).strip()[:350])
    return r.stdout.strip().splitlines()


def source():
    folder = ROOT / "reports/axieos_v014/task136bt"
    paths = sorted(folder.glob("AxieOS_V014_Task136BT_Legacy_Token_Identity_*.json"))
    require(paths, "Task136BT JSON report missing")
    path = paths[-1]
    raw = path.read_bytes()
    doc = json.loads(raw.decode("utf-8-sig"))
    checks, coverage = doc.get("checks", []), doc.get("coverage", {})
    require(doc.get("task") == "136BT" and doc.get("checkpoint96") == "OPEN" and
            coverage.get("candidate_hashes") == 116 and coverage.get("attempted") == 2 and
            coverage.get("unattempted") == 114 and len(checks) == 2 and
            all(c.get("error_type") == "HTTPError" and c.get("http_status") == 404
                for c in checks) and
            doc.get("accepted_cost_basis") is None and doc.get("financial_totals") is None,
            "Task136BT evidence differs from the two reported 404 results")
    return path, hashlib.sha256(raw).hexdigest()


def replace_exact(text, old, new):
    return text.replace(old, new)


def corrected(path, text):
    name = path.name
    if name == "AxieOS_V016_Final_Closeout.py":
        text = replace_exact(text,
            '"**2026-05-13**. The **2026-03-04 through 2026-05-12** interval lacks export coverage. "',
            '"**2026-05-13**. The intervening period is reported inactivity consistent with the saved exports. "')
        text = replace_exact(text,
            'Gap: 2026-03-04 through 2026-05-12 | Basis conflicts: 24',
            'Reported inactivity: 2026-03-04 through 2026-05-12 | Basis conflicts: 24')
    elif name == "AxieOS_V017_Scoped_Closeout.py":
        text = replace_exact(text,
            'The 24 consumable basis conflicts and historical export gap remain unresolved.',
            'The 24 consumable basis conflicts remain unresolved; the March–May interval is reported inactivity, not a proven missing-transaction gap.')
    else:
        text = replace_exact(text,
            'The **2026-03-04 through 2026-05-12** interval lacks export coverage. '
            'The **24 consumable sale-basis conflicts** remain unresolved.',
            'The **2026-03-04 through 2026-05-12** interval is reported inactivity '
            'consistent with the saved transaction files, not an established missing-transaction gap. '
            'The **24 consumable sale-basis conflicts** remain unresolved.')
        text = replace_exact(text,
            'The 24 consumable basis conflicts and historical export gap remain unresolved.',
            'The 24 consumable basis conflicts remain unresolved; the March–May interval is reported inactivity, not a proven missing-transaction gap.')
    return text


def mark(text, section):
    require(text.startswith("# ") and text.count(START) == text.count(END) and
            text.count(START) <= 1, "documentation heading or markers ambiguous")
    if START in text:
        a, b = text.index(START), text.index(END) + len(END)
        return text[:a] + section.rstrip("\n") + text[b:]
    first = text.index("\n")
    return text[:first + 1] + "\n" + section + "\n" + text[first + 1:]


def encode(original, text):
    bom = b"\xef\xbb\xbf" if original.startswith(b"\xef\xbb\xbf") else b""
    newline = "\r\n" if b"\r\n" in original else "\n"
    return bom + text.replace("\r\n", "\n").replace("\n", newline).encode("utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--commit", action="store_true", help="targeted local commit, no push")
    args = p.parse_args()
    report, sha = source()
    report_md = report.with_suffix(".md")
    require(report_md.is_file(), "paired Task136BT Markdown report missing")
    note = ROOT / "docs/Engineering/AxieOS_Finance_Source_Exception_20261106.md"
    script = ROOT / "scripts/AxieOS_Finance_Gap_Correction_20261106.py"
    docs = [ROOT / "LLM_Project_Context.md", ROOT / "docs/Engineering/ROADMAP.md",
            ROOT / "docs/Engineering/AxieOS_V016_Final_Scoped_Closeout.md",
            ROOT / "docs/Engineering/AxieOS_V017_Scoped_Operational_Closeout.md"]
    writers = [ROOT / "scripts/AxieOS_V016_Final_Closeout.py",
               ROOT / "scripts/AxieOS_V017_Scoped_Closeout.py"]
    targets = docs + writers
    require(all(f.is_file() for f in targets), "canonical closeout docs or scripts missing")
    require(not note.exists() or START in note.read_text(encoding="utf-8-sig"),
            "existing exception note has a different format")
    if args.commit:
        require(script.is_file(), "save this Python file in scripts first")
        require(not git("diff", "--cached", "--name-only"), "other files already staged")
        selected = [x.relative_to(ROOT).as_posix() for x in targets + [note, script, report, report_md]]
        require(not git("status", "--porcelain", "--untracked-files=no", "--", *selected),
                "target files have uncommitted edits; review before a targeted commit")
    section = "\n".join([
        START, "## Historical consumable source exception — 2026-11-06", "",
        "The legacy export ends March 3 and the refresh starts May 13, 2026. The owner reports no Ronin",
        "activity during the intervening months; the supplied transaction files contain no rows in that",
        "interval. This is **reported inactivity consistent with saved records**, not evidence of missing",
        "transactions. Task136BT attempted two of 116 historical consumable candidates through the current",
        "explorer token-transfer route; both returned HTTP 404. The other 114 were not tested. No token IDs,",
        "opening inventory, or cost basis were accepted. The 24 consumable sale-basis cases remain UNKNOWN",
        "and outside accepted profit. Unified Finance stays HOLD; Checkpoint 96 stays OPEN.", "",
        f"Source: `{report.relative_to(ROOT).as_posix()}` (SHA-256 `{sha}`).",
        END, ""
    ])
    output = {}
    changed_old = 0
    for path in targets:
        raw = path.read_bytes()
        original = raw.decode("utf-8-sig")
        updated = corrected(path, original)
        changed_old += updated != original
        if path in docs[:2]:
            updated = mark(updated, section)
        if path.suffix == ".py":
            compile(updated, str(path), "exec")
        output[path] = encode(raw, updated)
    require(changed_old >= 3, "expected historical-gap wording absent; inspect repo version")
    note_text = "# AxieOS — Finance source exception\n\n" + section
    output[note] = note_text.encode("utf-8")
    changed = [path for path, data in output.items() if not path.exists() or path.read_bytes() != data]
    if changed:
        backup = Path.home() / "AxieOSBackups" / "documentation" / ("finance_gap_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ"))
        backup.mkdir(parents=True, exist_ok=False)
        for path in changed:
            if path.is_file():
                shutil.copy2(path, backup / path.name)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".finance-gap.tmp")
            tmp.write_bytes(output[path])
            tmp.replace(path)
    if args.commit:
        names = [path.relative_to(ROOT).as_posix() for path in changed]
        for path in (script, report, report_md):
            name = path.relative_to(ROOT).as_posix()
            if name not in names:
                names.append(name)
        require(names, "nothing to commit")
        git("add", "--", *names)
        require(set(git("diff", "--cached", "--name-only")) <= set(names),
                "staged scope differs")
        git("diff", "--cached", "--check")
        git("commit", "-m", "Correct historical inactivity and finance source exception")
        print("Local commit:", git("rev-parse", "--short", "HEAD")[0])
        print("GitHub push: NO — use GitHub Desktop Push origin")
    print("AXIEOS - HISTORICAL INACTIVITY AND FINANCE EXCEPTION CORRECTION")
    print(f"Task136BT: 2 HTTP 404 | Not attempted: 114 | Basis conflicts: 24")
    print(f"Documentation and closeout writers updated: {len(changed)} files")
    print(f"Source report: {report.name} | Exception note: {note}")
    print("Database opened: NO | Writes: 0 | Network: 0 | Unified Finance: HOLD | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
