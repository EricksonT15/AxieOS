r"""Task136BL: read-only post-apply audit and scoped V0.14 evidence closeout.

From the AxieOS repository root:
    py -B .\scripts\v014_scoped_closeout.py

Compares production to the Task136BK persistent backup, validates exact raw
row inserts and the four Task136BG views, then writes one JSON and Markdown
closeout report. No production writes or network calls. Financial totals and
Checkpoint 96 remain unresolved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from v013_fullrow_materialization_sandbox import PROTECTED_TABLES, table_fingerprint
from v014_detail_raw_clone import TABLE, WATCH, old_raw_digest
from v014_post_apply_reconcile import connect_ro, require
from v014_raw_import_clone import TX_FIELDS, by_sha, load


VIEWS = ("income", "expense", "capital", "portfolio")


def applied_path(directory: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    candidates = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        doc, _ = load(path)
        if doc.get("task") == "136BK" and doc.get("mode") == "APPLIED":
            candidates.append((doc.get("created_at_utc", ""), path))
    require(candidates, f"no Task136BK APPLIED report in {directory}")
    return max(candidates)[1]


def views(directory: Path, bf_sha: str) -> dict[str, tuple[Path, dict, str]]:
    result = {}
    for path in directory.glob("*.json") if directory.is_dir() else []:
        doc, sha = load(path)
        if doc.get("task") != "136BG" or doc.get("view") not in VIEWS or \
                doc.get("sources", {}).get("136BF", {}).get("sha256") != bf_sha:
            continue
        kind = doc["view"]
        require(kind not in result, f"duplicate Task136BG {kind} view")
        result[kind] = (path, doc, sha)
    require(set(result) == set(VIEWS),
            "expected four Task136BG views linked to the selected registry")
    return result


def verify(current, backup, bk: dict, bj: dict, bi: dict, bf: dict,
           view_docs: dict[str, tuple[Path, dict, str]],
           shas: dict[str, str]) -> dict:
    require(bk.get("task") == "136BK" and bk.get("mode") == "APPLIED" and
            bj.get("task") == "136BJ" and bi.get("task") == "136BI" and
            bf.get("task") == "136BF" and
            all(doc.get("checkpoint96") == "OPEN" and
                doc.get("accepted_financial_totals") is None
                for doc in (bk, bj, bi, bf)) and
            all(bk["sources"][task]["sha256"] == shas[task]
                for task in ("136BJ", "136BI", "136BF")) and
            bj["sources"]["136BI"]["sha256"] == shas["136BI"] and
            bk.get("network_calls") == 0 and
            bk.get("production_database_writes") ==
                bk["result"]["inserted_rows"],
            "applied report or source chain differs")
    rows = bj["proposed_raw_transaction_rows"]
    applied = bk["result"]
    prior, after = applied["raw_before"], applied["raw_after"]
    require(len(rows) == applied["inserted_rows"] ==
                bi["coverage"]["candidate_raw_transactions"] ==
                bj["coverage"]["proposed_raw_transactions"] and
            prior == bj["coverage"]["production_raw_transactions"] and
            after == prior + len(rows) and
            bk["plan"]["plan_sha256"] == bj["plan_sha256"] and
            applied["ledger_unchanged"] ==
                bj["coverage"]["production_ledger_rows"],
            "applied row plan, arithmetic, or ledger scope differs")
    hashes = {row["tx_hash"].lower() for row in rows}
    require(len(hashes) == len(rows) and
            all(set(row) == set(TX_FIELDS) for row in rows) and
            backup.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0] == prior and
            current.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0] == after and
            backup.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0] ==
                current.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0] ==
                    applied["ledger_unchanged"],
            "production/backup raw or ledger counts differ")
    require(all(conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                not conn.execute("PRAGMA foreign_key_check").fetchall()
                for conn in (backup, current)),
            "production or backup SQLite integrity failed")
    for row in rows:
        key = row["tx_hash"]
        expected = tuple(row[field] for field in TX_FIELDS)
        stored = current.execute("SELECT " + ",".join(TX_FIELDS) +
            f" FROM {TABLE} WHERE tx_hash=?", (key,)).fetchall()
        require(stored == [expected], f"inserted raw transaction differs: {key}")
        require(backup.execute(f"SELECT COUNT(*) FROM {TABLE} WHERE tx_hash=?",
                               (key,)).fetchone()[0] == 0,
                f"new transaction already existed in backup: {key}")
    prior_digest, preserved = old_raw_digest(current, hashes)
    require(preserved == prior and prior_digest == table_fingerprint(backup, TABLE),
            "prior raw transaction rows changed")
    for table in WATCH:
        require(table_fingerprint(current, table) == table_fingerprint(backup, table),
                f"ledger, raw transfer, or protected table changed: {table}")
    old = bf["coverage"]
    require(old["combined_references"] == old["historical_references"] +
                old["prior_cached_references"] + old["recent_raw_hash_references"] and
            len(bf["registry_rows"]) == old["combined_references"] and
            all(row.get("accepted_financial_value") is None
                for row in bf["registry_rows"]),
            "source registry reference coverage or value differs")
    recent_ids = {row["registry_id"] for row in bf["registry_rows"]
                  if row.get("origin") == "TASK136AU_RECENT_RAW"}
    require(len(recent_ids) == old["recent_raw_hash_references"],
            "recent source identities duplicate")
    view_summary = {}
    for kind, (_, report, _) in view_docs.items():
        c = report["coverage"]
        context = report["recent_unaccepted_context"]
        require(report["task"] == "136BG" and report["view"] == kind and
                report["checkpoint96"] == "OPEN" and
                all(v is None for v in report["accepted_totals"].values()) and
                report["database_writes"] == report["network_calls"] == 0 and
                c["combined_unique_references"] == old["combined_references"] and
                len(context) == c["recent_unaccepted_sources"] == len(recent_ids) and
                {row["registry_id"] for row in context} == recent_ids and
                all(row["accepted_financial_value"] is None for row in context) and
                c["recent_relevant_candidates"] + c["recent_other_unresolved"] ==
                    len(context),
                f"{kind}: view coverage, source identities, or accepted value differs")
        view_summary[kind] = {"historical_primary": c["historical_primary"],
                              "prior_cached_context": c["prior_cached_context"],
                              "recent_unaccepted": len(context),
                              "recent_relevant_candidates": c["recent_relevant_candidates"]}
    return {"raw_transactions_before": prior,
            "raw_transactions_after": after,
            "exact_inserted_raw_rows": len(rows),
            "prior_raw_rows_preserved": preserved,
            "ledger_rows_unchanged": applied["ledger_unchanged"],
            "raw_transfers_unchanged": True,
            "protected_tables_unchanged": len(PROTECTED_TABLES),
            "historical_references": old["historical_references"],
            "prior_cached_references": old["prior_cached_references"],
            "recent_raw_hash_references": old["recent_raw_hash_references"],
            "combined_source_references": old["combined_references"],
            "four_views": view_summary,
            "sqlite_integrity": "ok", "foreign_key_violations": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path,
                        default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--applied", type=Path)
    for suffix in ("bk", "bj", "bi", "bf", "bg"):
        parser.add_argument(f"--{suffix}-dir", type=Path,
                            default=Path(f"reports/axieos_v014/task136{suffix}"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("reports/axieos_v014/task136bl"))
    args = parser.parse_args()
    paths = {"136BK": applied_path(args.bk_dir, args.applied)}
    bk, bk_sha = load(paths["136BK"])
    for task in ("136BJ", "136BI", "136BF"):
        paths[task] = by_sha(getattr(args, task[3:].lower() + "_dir"),
                              bk["sources"][task]["sha256"], task)
    docs, shas = {}, {}
    for task, path in paths.items():
        docs[task], shas[task] = load(path)
    found = views(args.bg_dir, shas["136BF"])
    require(Path(bk["result"]["backup_path"]).expanduser().resolve() !=
            args.db.expanduser().resolve(), "backup equals production database")
    with closing(connect_ro(args.db)) as current, closing(connect_ro(
            Path(bk["result"]["backup_path"]))) as backup:
        current.execute("BEGIN")
        backup.execute("BEGIN")
        coverage = verify(current, backup, docs["136BK"], docs["136BJ"],
                          docs["136BI"], docs["136BF"], found, shas)
    report = {"project": "AxieOS", "version": "0.14", "task": "136BL",
              "release_state": "SCOPED_EVIDENCE_READY_FOR_REVIEW",
              "full_finance_closeout": False,
              "sources": {task: {"filename": path.name, "sha256": shas[task]}
                          for task, path in paths.items()},
              "view_sources": {kind: {"filename": p.name, "sha256": digest}
                               for kind, (p, doc, digest) in found.items()},
              "backup_path": bk["result"]["backup_path"],
              "coverage": coverage,
              "remaining_boundaries": [
                  "Verified income, expense, profit, portfolio value and PHP recovery are UNKNOWN",
                  "Checkpoint 96 remains OPEN",
                  "Stored fees and raw fees do not establish who paid gas or accepted expense",
                  "Historical cost basis conflicts and unhashed capital references remain unresolved",
                  "Candidate marketplace routes do not establish verified trades"],
              "accepted_financial_totals": None,
              "production_database_opened_read_only": True,
              "backup_database_opened_read_only": True,
              "database_writes": 0, "network_calls": 0,
              "checkpoint96": "OPEN",
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136BL_Scoped_Evidence_Closeout_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
            "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    c = report["coverage"]
    body = ["# AxieOS V0.14 — Scoped finance evidence closeout review", "",
            "**Release state:** Scoped evidence ready for review. "
            "Full finance closeout remains open.", "",
            f"Raw transaction rows before/after: **{c['raw_transactions_before']}/"
            f"{c['raw_transactions_after']}**; exact inserted: "
            f"**{c['exact_inserted_raw_rows']}**. Ledger preserved: "
            f"**{c['ledger_rows_unchanged']}** rows. Raw transfers and "
            f"**{c['protected_tables_unchanged']}** protected tables unchanged.", "",
            f"Source references: **{c['combined_source_references']}** = "
            f"**{c['historical_references']}** historical + "
            f"**{c['prior_cached_references']}** prior cached + "
            f"**{c['recent_raw_hash_references']}** recent. "
            "The same hash can occur in several report views.", "",
            "| View | Historical primary | Prior cached context | Recent unresolved |",
            "|---|---:|---:|---:|"]
    body.extend(f"| {kind.title()} | {v['historical_primary']} | "
                f"{v['prior_cached_context']} | {v['recent_unaccepted']} |"
                for kind, v in c["four_views"].items())
    body += ["", "## Unresolved for full financial closeout", ""]
    body.extend("- " + item for item in report["remaining_boundaries"])
    body += ["", "Verified financial totals: **UNKNOWN**. "
             "Checkpoint 96: **OPEN**. No financial values accepted.", "",
             "Production and backup opened read only | Writes: 0 | Network: 0", ""]
    mp.write_text("\n".join(body), encoding="utf-8")
    print("AXIEOS V0.14 - TASK136BL - SCOPED EVIDENCE CLOSEOUT REVIEW")
    print(f"Raw transactions: {c['raw_transactions_before']}/"
          f"{c['raw_transactions_after']} | Exact inserted: "
          f"{c['exact_inserted_raw_rows']} | Ledger: {c['ledger_rows_unchanged']}")
    print(f"Historical/prior cached/recent/combined: "
          f"{c['historical_references']}/{c['prior_cached_references']}/"
          f"{c['recent_raw_hash_references']}/{c['combined_source_references']}")
    print("Scoped evidence ready for review | Full finance closeout: OPEN")
    print("Verified financial totals: UNKNOWN | Checkpoint 96: OPEN")
    print(f"Reports: {jp} {mp}")
    print("Production and backup read only | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (post-apply reconciliation and scoped evidence review only)")


if __name__ == "__main__":
    main()
