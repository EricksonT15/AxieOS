r"""Task136AQ: rehearse scoped classifications in a disposable SQLite clone.

From the AxieOS repository root:
    py -B .\scripts\v014_scoped_classification_clone.py

Production is opened read only. This inserts 564 proposed classification rows
only into a temporary clone, with seven WETH/SLP hashes on a distinct review
label. It never invokes legacy accounting, economic, or sync writers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import ronin_api_sync as legacy
from v013_fullrow_materialization_sandbox import PROTECTED_TABLES, table_fingerprint
from v014_post_apply_reconcile import connect_ro, require


VERSION = "v0.14-136AQ-scoped-1"
INSERT = """INSERT INTO blockchain_transaction_classifications
    (txhash, classification, confidence, reason, method, classifier_version)
    VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(txhash) DO NOTHING"""


def read(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing source: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def latest(explicit: Path | None, directory: Path, task: str) -> Path:
    if explicit is not None:
        return explicit
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        doc, _ = read(path)
        if doc.get("task") == task and doc.get("checkpoint96") == "OPEN":
            matches.append((doc.get("created_at_utc", ""), path))
    require(bool(matches), f"missing Task{task} JSON in {directory}")
    return max(matches)[1]


def plan(af: dict, ag: dict, al: dict, ao: dict, shas: dict) -> tuple[list[tuple], set[str]]:
    require(all(doc.get("task") == task and doc.get("checkpoint96") == "OPEN"
                and doc.get("accepted_financial_totals") is None
                for task, doc in (("136AF", af), ("136AG", ag), ("136AL", al), ("136AO", ao))),
            "source task, checkpoint, or financial boundary differs")
    require(ag["source_task136af_sha256"] == shas["136AF"] and
            al["sources"]["136AF"]["sha256"] == shas["136AF"] and
            al["sources"]["136AG"]["sha256"] == shas["136AG"] and
            ao["sources"]["136AG"]["sha256"] == shas["136AG"] and
            ao["sources"]["136AI"]["sha256"] == al["sources"]["136AI"]["sha256"] and
            al["decision"] == "HOLD_LEGACY_ACCOUNTING_AND_ECONOMIC_WRITERS_PENDING_SCOPED_CORRECTION",
            "Task136AF/AG/AL/AO source chain or writer hold differs")
    candidates = {str(r["txhash"]).lower(): r for r in ag["candidates"]}
    overrides = {str(r["txhash"]).lower(): r for r in ao["overrides"]}
    require(len(candidates) == len(ag["candidates"]) ==
            ag["coverage"]["guarded_hashes"] ==
            af["coverage"]["inserted_hashes_exact"] ==
            al["coverage"]["guarded_hashes_classified_in_clone"] ==
            ao["coverage"]["guarded_hashes"] == 564 and
            len(overrides) == len(ao["overrides"]) ==
            ao["coverage"]["fungible_overrides"] == 7 and
            set(overrides).issubset(candidates), "guarded classification cohort differs")
    require(ag["coverage"]["stored_accounting_for_cohort"] == 0 and
            al["coverage"]["production_accounting_added"] == 0 and
            ao["legacy_writer_decision"] == "HOLD", "accounting state differs")
    rows = []
    for h, item in sorted(candidates.items()):
        require(item["accounting_treatment"] == "UNREVIEWED_CANDIDATE",
                f"{h}: accounting treatment changed")
        if h in overrides:
            overlay = overrides[h]
            require(item["legacy_label"] == overlay["legacy_label"] == "MARKETPLACE_BUY" and
                    item["shape"] == "BUY_CANDIDATE" and
                    overlay["proposed_evidence_label"] == "FUNGIBLE_EXCHANGE_CANDIDATE" and
                    overlay["accepted_marketplace_purchase"] is False and
                    overlay["accepted_swap_financial_treatment"] is None,
                    f"{h}: fungible overlay differs from shadow")
            classification = "FUNGIBLE_EXCHANGE_CANDIDATE"
            confidence = "LOW"
            reason = "Opposing WETH/SLP transfer candidate; financial treatment unverified"
        else:
            classification = item["legacy_label"]
            confidence = item["legacy_confidence"]
            reason = item["legacy_reason"]
        rows.append((h, classification, confidence, reason, item["method"], VERSION))
    require(Counter(r[1] for r in rows)["MARKETPLACE_BUY"] ==
            ao["coverage"]["marketplace_buy_after_overlay"] == 84,
            "marketplace buy count after overlay differs")
    return rows, set(candidates)


def rehearse(db: Path, rows: list[tuple], hashes: set[str], ag: dict, af: dict) -> dict:
    with closing(connect_ro(db)) as prod:
        prod.execute("BEGIN")
        require(prod.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                prod.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0] ==
                af["coverage"]["ledger_after"],
                "production ledger or integrity changed since Task136AF")
        baseline = {table: table_fingerprint(prod, table)
                    for table in ("blockchain_transactions",) + PROTECTED_TABLES}
        already = {str(r[0]).lower() for r in prod.execute(
            "SELECT txhash FROM blockchain_transaction_classifications WHERE txhash IS NOT NULL")}
        accounting = {str(r[0]).lower() for r in prod.execute(
            "SELECT txhash FROM blockchain_accounting_records WHERE txhash IS NOT NULL")}
        require(not already & hashes and not accounting & hashes,
                "cohort classification or accounting already exists; reconcile first")
        with TemporaryDirectory(prefix="axieos_v014_classification_clone_") as temp:
            clone_path = Path(temp) / "clone.db"
            with closing(sqlite3.connect(clone_path)) as dst:
                prod.backup(dst)
            grouped = {str(t["txhash"]).lower(): t for t in
                       legacy.group_ledger_rows_by_txhash(clone_path)
                       if str(t["txhash"]).lower() in hashes}
            require(set(grouped) == hashes, "clone grouped transaction coverage differs")
            shadow_by_hash = {str(r["txhash"]).lower(): r for r in ag["candidates"]}
            for h, item in grouped.items():
                shadow = shadow_by_hash[h]
                result = legacy.classify_grouped_transaction(item)
                require(item["method"] == shadow["method"] and
                        result["classification"] == shadow["legacy_label"] and
                        result["confidence"] == shadow["legacy_confidence"] and
                        result["reason"] == shadow["legacy_reason"],
                        f"{h}: clone legacy source changed since Task136AG")
            with closing(sqlite3.connect(clone_path)) as clone:
                protected = {table: table_fingerprint(clone, table)
                             for table in PROTECTED_TABLES
                             if table != "blockchain_transaction_classifications"}
                require(all(table_fingerprint(clone, table) == baseline[table]
                            for table in baseline), "clone differs from production baseline")
                before = clone.execute(
                    "SELECT COUNT(*) FROM blockchain_transaction_classifications").fetchone()[0]
                clone.execute("PRAGMA foreign_keys=ON")
                initial = clone.total_changes
                clone.executemany(INSERT, rows)
                first = clone.total_changes - initial
                clone.commit()
                initial = clone.total_changes
                clone.executemany(INSERT, rows)
                second = clone.total_changes - initial
                clone.commit()
                actual = {str(h).lower(): (label, confidence, reason, method, version)
                          for h, label, confidence, reason, method, version in clone.execute(
                              "SELECT txhash,classification,confidence,reason,method,classifier_version "
                              "FROM blockchain_transaction_classifications")
                          if str(h).lower() in hashes}
                expected = {r[0]: r[1:] for r in rows}
                require(first == len(rows) and second == 0 and
                        len(actual) == len(expected) and actual == expected and
                        clone.execute("SELECT COUNT(*) FROM blockchain_transaction_classifications").fetchone()[0]
                        == before + len(rows), "clone scoped insert or idempotence differs")
                require(clone.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                        not clone.execute("PRAGMA foreign_key_check").fetchall() and
                        table_fingerprint(clone, "blockchain_transactions") ==
                        baseline["blockchain_transactions"] and
                        all(table_fingerprint(clone, table) == digest
                            for table, digest in protected.items()),
                        "clone integrity or protected table changed")
        require(all(table_fingerprint(prod, table) == digest for table, digest in baseline.items()),
                "production changed during clone rehearsal")
    return {"clone_rows_first_pass": first, "clone_rows_second_pass": second,
            "production_classification_rows_added": 0,
            "clone_accounting_rows_added": 0, "clone_integrity": "ok",
            "protected_clone_tables_unchanged": len(protected), "clone_deleted": True}


def markdown(report: dict) -> str:
    c = report["coverage"]
    return "\n".join([
        "# AxieOS V0.14 — Task136AQ Scoped classification clone rehearsal", "",
        f"Guarded hashes: **{c['guarded_hashes']}**; fungible candidate labels: "
        f"**{c['fungible_candidates']}**; remaining marketplace buy candidates: "
        f"**{c['marketplace_buy_candidates']}**.", "",
        f"Clone classification inserts first/second run: "
        f"**{c['clone_rows_first_pass']}/{c['clone_rows_second_pass']}**. "
        "No production classification or accounting rows were added.", "",
        "A classification is a candidate label, not an accepted marketplace event. "
        "Economic/accounting writers remain held. Verified income, expenses, profit, "
        "portfolio value, and PHP recovery: **UNKNOWN**.", "",
        "Production opened read only | Production writes: 0 | Clone deleted | Network: 0", "",
        "VALIDATION: PASS (scoped classification clone only; Checkpoint 96 OPEN).", ""])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    for suffix in ("af", "ag", "al", "ao"):
        parser.add_argument("--" + suffix, type=Path)
        parser.add_argument("--" + suffix + "-dir", type=Path,
                            default=Path("reports/axieos_v014/task136" + suffix))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136aq"))
    args = parser.parse_args()
    paths = {"136" + suffix.upper(): latest(getattr(args, suffix),
             getattr(args, suffix + "_dir"), "136" + suffix.upper())
             for suffix in ("af", "ag", "al", "ao")}
    docs, shas = {}, {}
    for key, path in paths.items():
        docs[key], shas[key] = read(path)
    rows, hashes = plan(docs["136AF"], docs["136AG"], docs["136AL"], docs["136AO"], shas)
    result = rehearse(args.db, rows, hashes, docs["136AG"], docs["136AF"])
    coverage = {"guarded_hashes": len(rows),
                "fungible_candidates": sum(r[1] == "FUNGIBLE_EXCHANGE_CANDIDATE" for r in rows),
                "marketplace_buy_candidates": sum(r[1] == "MARKETPLACE_BUY" for r in rows),
                **result}
    report = {"project": "AxieOS", "version": "0.14", "task": "136AQ",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "sources": {key: {"filename": paths[key].name, "sha256": shas[key]}
                          for key in sorted(paths)},
              "classifier_version_candidate": VERSION, "coverage": coverage,
              "accepted_financial_totals": None, "production_database_opened_read_only": True,
              "production_database_writes": 0, "network_calls": 0, "checkpoint96": "OPEN"}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AQ_Scoped_Classification_Clone_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    print("AXIEOS V0.14 - TASK136AQ - SCOPED CLASSIFICATION CLONE")
    print(f"Guarded hashes: {coverage['guarded_hashes']} | Fungible review labels: "
          f"{coverage['fungible_candidates']} | Marketplace buy candidates: "
          f"{coverage['marketplace_buy_candidates']}")
    print(f"Clone inserts first/second: {coverage['clone_rows_first_pass']}/"
          f"{coverage['clone_rows_second_pass']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Production read only | Writes: 0 | Clone: deleted | Network: 0")
    print("VALIDATION: PASS (scoped classification clone only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
