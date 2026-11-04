r"""Task136BQ: update V0.14 scoped release documentation from Task136BP.

Run once from the AxieOS repository root:
    py -B .\scripts\v014_scoped_docs_closeout.py

Checks exact saved report hashes, backs up the two existing Markdown files
outside the repository, then adds a bounded status note near the top of each
and writes a separate release note. Rerunning is idempotent. No SQLite,
network, wallet, financial acceptance, commit, or push.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


START = "<!-- AXIEOS_V014_SCOPED_EVIDENCE_START -->"
END = "<!-- AXIEOS_V014_SCOPED_EVIDENCE_END -->"
NOTE_NAME = "AxieOS_V014_Scoped_Finance_Evidence_Closeout.md"
DIRECTORIES = {"96BV": "reports/axieos_v013/checkpoint96",
               "136F": "reports/axieos_v014/task136f",
               "136AJ": "reports/axieos_v014/task136aj",
               "136BF": "reports/axieos_v014/task136bf",
               "136BL": "reports/axieos_v014/task136bl",
               "136BM": "reports/axieos_v014/task136bm",
               "136BN": "reports/axieos_v014/task136bn",
               "136BO": "reports/axieos_v014/task136bo",
               **{"136BG_" + name: "reports/axieos_v014/task136bg"
                  for name in ("income", "expense", "capital", "portfolio")}}


def require(ok, why):
    if not ok:
        raise ValueError("STOP: " + why)


def latest_bp(folder):
    found = []
    for path in folder.glob("*.json") if folder.is_dir() else []:
        raw = path.read_bytes()
        doc = json.loads(raw.decode("utf-8-sig"))
        if doc.get("task") == "136BP":
            found.append((str(doc.get("created_at_utc", "")), path, doc,
                          hashlib.sha256(raw).hexdigest()))
    require(found, "Task136BP JSON missing; run the consolidated acceptance batch first")
    _, path, doc, sha = max(found)
    return path, doc, sha


def verify(root, bp):
    c = bp.get("coverage", {})
    require(bp.get("project") == "AxieOS" and bp.get("version") == "0.14" and
            bp.get("decision") == "SCOPED_EVIDENCE_READY_FOR_RELEASE_REVIEW" and
            bp.get("planned_unified_finance_release") == "HOLD" and
            bp.get("checkpoint96") == "OPEN" and
            bp.get("accepted_financial_totals") is None and
            bp.get("database_opened") is False and
            bp.get("database_writes") == bp.get("network_calls") == 0 and
            c.get("combined_registry_references") == 1339 and
            c.get("scoped_finance_views") == 4 and
            c.get("axie_sale_pairs_corroborated") == 26 and
            c.get("consumable_purchases_corroborated") == 26 and
            c.get("consumable_fifo_candidates_match_stored") == 24 and
            c.get("recent_detail_queue_unaccepted") == 22 and
            len(bp.get("candidate_basis_review", [])) == 24 and
            all(case.get("stored_basis_matches_model") is True and
                case.get("accepted_cost_basis") is None and
                case.get("accepted_profit") is None
                for case in bp["candidate_basis_review"]),
            "Task136BP scoped boundary, counts or conditional basis differs")
    require(set(bp.get("sources", {})) == set(DIRECTORIES),
            "Task136BP source map has missing or extra references")
    for key, directory in DIRECTORIES.items():
        item = bp["sources"][key]
        name, sha = item.get("filename"), item.get("sha256")
        require(isinstance(name, str) and Path(name).name == name and
                name.endswith(".json") and isinstance(sha, str) and
                re.fullmatch(r"[0-9a-f]{64}", sha),
                f"{key}: invalid saved source reference")
        path = root / directory / name
        require(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == sha,
                f"{key}: saved source changed since Task136BP")


def decode_markdown(path):
    require(path.is_file() and not path.is_symlink(), f"missing or linked document: {path}")
    raw = path.read_bytes()
    require(len(raw) >= 100 and len(raw) <= 2_000_000, f"unexpected document size: {path}")
    bom = raw.startswith(b"\xef\xbb\xbf")
    content = raw.decode("utf-8-sig")
    newline = "\r\n" if b"\r\n" in raw else "\n"
    require(bool(re.search(r"(?m)^# [^\r\n]+", content)),
            f"top-level Markdown heading missing: {path}")
    return raw, content, newline, bom


def replace_status(content, newline, message):
    block = START + newline + message.replace("\n", newline) + newline + END
    a, b = content.count(START), content.count(END)
    require(a == b and a <= 1, "existing scoped-status markers are inconsistent")
    if a:
        start = content.index(START)
        stop = content.index(END) + len(END)
        require(stop > start, "scoped-status markers out of order")
        return content[:start] + block + content[stop:]
    heading = re.search(r"(?m)^# [^\r\n]+(?:\r?\n|$)", content)
    require(heading is not None, "cannot find Markdown title")
    at = heading.end()
    return content[:at] + newline + block + newline + content[at:]


def release_note(bp_name, bp_sha, c, date):
    return "\n".join([
        "# AxieOS V0.14 — Scoped Finance Evidence Closeout", "",
        f"**Review date:** {date}  ",
        "**Decision:** Scoped evidence milestone ready for repository release.  ",
        "**Planned Unified Finance release:** HOLD.  ",
        "**Checkpoint 96:** OPEN. Verified income, expense, realized profit, "
        "portfolio value and PHP recovery: UNKNOWN.", "",
        "## Acceptance evidence", "",
        f"Task136BP passed its offline checks: `{bp_name}` (SHA-256 `{bp_sha}`).", "",
        f"- Combined registry: {c['combined_registry_references']} source references; "
        "these are not independently verified financial events.",
        f"- Four linked finance views: {c['scoped_finance_views']}; "
        "they predate the later purchase and sale explorer crosswalks.",
        f"- Axie sale pairs corroborated: {c['axie_sale_pairs_corroborated']}; "
        "seller proceeds alone do not establish basis or profit.",
        f"- CocoChoco purchase pairs corroborated: {c['consumable_purchases_corroborated']}.",
        f"- Stored CocoChoco FIFO candidates reproduced: "
        f"{c['consumable_fifo_candidates_match_stored']}; all remain conditional "
        "because pre-visible opening lots and their cost are unknown.",
        f"- Recent transaction-detail review cases: "
        f"{c['recent_detail_queue_unaccepted']}; no automatic label changes.", "",
        "## Release boundary", "",
        "This milestone certifies linked source coverage and reproducible evidence "
        "views. It does not accept income, expenses, gas, basis, profit, "
        "PHP recovery, or a current portfolio value. Task136BP did not open "
        "the database, write to it, or contact the network.", "",
        "The new explorer's oldest visible CocoChoco transfers are outgoing "
        "burns after the May 2026 migration. Its pagination end is not proof "
        "that earlier inventory did not exist. Keep the 24 FIFO values as "
        "candidates; do not copy them into deferred economic rows.", "",
        "## Next finance work", "",
        "Find a defensible pre-migration inventory and cost source if available; "
        "otherwise preserve unknown opening cost. Refresh the four evidence "
        "views to include the newer sale/purchase crosswalks, then resolve "
        "receipt, gas payer, PHP conversion, capital and current holdings gates "
        "before claiming Unified Finance completion.", "",
        "**Repository status:** ready for a scoped documentation and source "
        "commit using GitHub Desktop. This file does not commit or push.", ""])


def atomic_bytes(path, data):
    fd, temp = tempfile.mkstemp(prefix=".axieos-doc-", dir=path.parent)
    tmp = Path(temp)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--bp", type=Path, help="Exact Task136BP JSON")
    parser.add_argument("--backup-dir", type=Path,
                        default=Path.home() / "AxieOSBackups" / "documentation")
    args = parser.parse_args()
    root = args.root.resolve()
    bp_path, bp, bp_sha = (latest_bp(root / "reports/axieos_v014/task136bp")
                           if args.bp is None else
                           (args.bp, *read_exact_bp(args.bp)))
    verify(root, bp)
    date = str(bp["created_at_utc"])[:10]
    require(re.fullmatch(r"20\d\d-\d\d-\d\d", date), "invalid acceptance date")
    c = bp["coverage"]
    summary = (f"Task136BP PASS: {c['combined_registry_references']} source references, "
               f"four linked views, {c['axie_sale_pairs_corroborated']} Axie sale pairs, "
               f"{c['consumable_purchases_corroborated']} CocoChoco purchases and "
               f"{c['consumable_fifo_candidates_match_stored']} conditional FIFO bases. "
               "Verified finance totals remain UNKNOWN; Checkpoint 96 OPEN.")
    context_text = "\n".join([
        f"## Current scoped checkpoint — {date}", "",
        "**V0.14 scoped finance evidence is ready for repository release review. "
        "The planned Unified Finance release remains HOLD.**", "",
        summary, "",
        "See `docs/Engineering/" + NOTE_NAME + "` for exact source scope and remaining gates."])
    roadmap_text = "\n".join([
        f"## V0.14 scoped finance evidence — {date}", "",
        "**Scoped evidence milestone: READY FOR RELEASE REVIEW. "
        "Unified Finance objective: HOLD. Checkpoint 96: OPEN.**", "",
        summary, "",
        "The 24 stored CocoChoco FIFO candidates match confirmed paid purchase lots "
        "under the stored model, but opening inventory and cost remain unknown. "
        "No verified profit, cash recovery or PHP conversion has been accepted.", "",
        "Release boundary and follow-on gates: `docs/Engineering/" + NOTE_NAME + "`."])
    targets = [(root / "LLM_Project_Context.md", context_text),
               (root / "docs/Engineering/ROADMAP.md", roadmap_text)]
    planned = []
    for path, block in targets:
        raw, content, newline, bom = decode_markdown(path)
        changed = replace_status(content, newline, block)
        data = (b"\xef\xbb\xbf" if bom else b"") + changed.encode("utf-8")
        planned.append((path, raw, data))
    note = root / "docs/Engineering" / NOTE_NAME
    require(note.parent.is_dir() and not note.is_symlink(), "release note location invalid")
    release = release_note(bp_path.name, bp_sha, c, date).encode("utf-8")
    note_was_present = note.exists()
    if note_was_present:
        require(note.read_bytes() == release,
                "release note exists with different content; inspect it before rerunning")
    changed_docs = [(p, old, new) for p, old, new in planned if old != new]
    args.backup_dir.mkdir(parents=True, exist_ok=True)
    backups = []
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6]
    for p, old, _ in changed_docs:
        backup = args.backup_dir / (stamp + "_" + p.name)
        with backup.open("xb") as stream:
            stream.write(old)
        backups.append(backup)
    written = []
    try:
        for path, old, new in changed_docs:
            require(path.read_bytes() == old, f"document changed during preflight: {path}")
            atomic_bytes(path, new)
            written.append((path, old))
        if not note.exists():
            atomic_bytes(note, release)
    except Exception:
        for path, original in reversed(written):
            atomic_bytes(path, original)
        raise
    print("AXIEOS V0.14 - TASK136BQ - SCOPED DOCUMENTATION CLOSEOUT")
    print(f"Acceptance: Task136BP PASS | Sources: {len(bp['sources'])} SHA-matched")
    print("Scoped milestone: READY FOR REPOSITORY RELEASE | Unified Finance: HOLD")
    print("Checkpoint 96: OPEN | Verified totals: UNKNOWN")
    print(f"Documentation: {targets[0][0]} {targets[1][0]} {note}")
    print(f"Files changed: {len(changed_docs) + (0 if note_was_present else 1)}")
    print(f"Backups created: {len(backups)} in {args.backup_dir}")
    print("Database opened: NO | Database writes: 0 | Network: 0 | Git commit/push: NO")
    print("VALIDATION: PASS (scoped documentation only; no Unified Finance release)")


def read_exact_bp(path):
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


if __name__ == "__main__":
    main()
