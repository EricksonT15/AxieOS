r"""Task136AL: clone-only legacy classifier rehearsal and accounting writer audit.

Run from the AxieOS repository root:
    py -B .\scripts\v014_legacy_writer_clone_preflight.py

Reads production in SQLite mode=ro and copies it to a disposable clone.
Runs only the legacy transaction classification writer on that clone. Audits
the legacy economic/accounting writer source without invoking those writers:
they can produce modeled sale gross/fees and read a hard-coded database path.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
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


def load(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing report: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def find(directory: Path, task: str) -> Path:
    matches = []
    for p in directory.glob("*.json") if directory.is_dir() else []:
        d, _ = load(p)
        if d.get("task") == task:
            matches.append((d.get("created_at_utc", ""), p))
    require(matches, f"no Task{task} report in {directory}; pass its exact path")
    return max(matches)[1]


def audit() -> dict[str, bool]:
    signals = {
        "economic_builder_reads_hardcoded_database":
            "AXIEOS_DB_PATH" in inspect.getsource(legacy.build_marketplace_economic_events),
        "seller_fee_is_modeled_rate":
            "MARKETPLACE_SELLER_FEE_RATE" in inspect.getsource(legacy.apply_marketplace_sale_fee),
        "cost_basis_matches_in_memory_axie_id":
            "owned_axies" in inspect.getsource(legacy.match_axie_acquisition_costs),
        "realized_pl_derived_from_matched_basis":
            "realized_pl" in inspect.getsource(legacy.calculate_realized_pl),
        "accounting_writer_upserts_by_accounting_key":
            "ON CONFLICT(accounting_key)" in inspect.getsource(legacy.store_accounting_records),
    }
    require(all(signals.values()), "legacy accounting source changed; review it before rehearsing")
    return signals


def build(ak: dict, af: dict, ag: dict, ai: dict, shas: dict[str, str], db: Path) -> dict:
    require(all(doc.get("task") == key for key, doc in
                (("136AK", ak), ("136AF", af), ("136AG", ag), ("136AI", ai))) and
            all(doc.get("checkpoint96") == "OPEN" and
                doc.get("accepted_financial_totals") is None for doc in (ak, af, ag, ai)),
            "source task or finance state differs")
    require(ak["sources"]["136AF"]["sha256"] == shas["136AF"] and
            ak["sources"]["136AG"]["sha256"] == shas["136AG"] and
            ak["sources"]["136AI"]["sha256"] == shas["136AI"] and
            ag["source_task136af_sha256"] == shas["136AF"],
            "post-apply source report chain differs")
    expected = {str(r["txhash"]).lower(): r for r in ag["candidates"]}
    require(len(expected) == ag["coverage"]["guarded_hashes"] ==
            af["coverage"]["inserted_hashes_exact"] ==
            ak["coverage"]["cached_ledger_statuses"]["MATERIALIZED_GUARDED"] and
            len(ag["candidates"]) == len(expected),
            "guarded classification hash count differs")
    route = {str(r["txhash"]).lower(): r for r in ai["new_candidates"]}
    require(len(route) == ai["coverage"]["new_marketplace_shaped_pairs"] and
            len(route) == len(ai["new_candidates"]) and set(route).issubset(expected) and
            {h for h, r in route.items() if r["review_lane"] == "FUNGIBLE_EXCHANGE_REVIEW"} ==
            {h for h, r in route.items() if r["control_status"] == "FUNGIBLE_ROUTE_REVIEW"},
            "fungible review lane or route count differs")
    risks = audit()
    with closing(connect_ro(db)) as production:
        production.execute("BEGIN")
        prod_ledger_count = production.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
        require(prod_ledger_count == af["coverage"]["ledger_after"],
                "production ledger changed since Task136AF; reconcile first")
        baseline = {t: table_fingerprint(production, t) for t in
                    ("blockchain_transactions",) + PROTECTED_TABLES}
        accounting = {str(h).lower() for (h,) in production.execute(
            "SELECT txhash FROM blockchain_accounting_records WHERE txhash IS NOT NULL")}
        require(not accounting & set(expected), "cohort accounting already present")
        classification_before = {str(h).lower() for (h,) in production.execute(
            "SELECT txhash FROM blockchain_transaction_classifications WHERE txhash IS NOT NULL")}
        require(not classification_before & set(expected),
                "cohort classification already in production; reconcile before clone")
        with TemporaryDirectory(prefix="axieos_v014_legacy_writer_") as temp:
            clone_path = Path(temp) / "clone.db"
            with closing(sqlite3.connect(clone_path)) as dst:
                production.backup(dst)
            with closing(sqlite3.connect(clone_path)) as clone:
                require(table_fingerprint(clone, "blockchain_transactions") ==
                        baseline["blockchain_transactions"], "clone ledger differs")
                protected = {t: table_fingerprint(clone, t) for t in PROTECTED_TABLES
                             if t != "blockchain_transaction_classifications"}
                original_class_count = clone.execute(
                    "SELECT COUNT(*) FROM blockchain_transaction_classifications").fetchone()[0]
            grouped = legacy.group_ledger_rows_by_txhash(clone_path)
            selected = [t for t in grouped if str(t["txhash"]).lower() in expected]
            require(len(selected) == len(expected) and
                    len({str(t["txhash"]).lower() for t in selected}) == len(expected),
                    "clone grouped cohort hash coverage differs")
            first = legacy.store_transaction_classifications(clone_path, selected)
            with closing(sqlite3.connect(clone_path)) as clone:
                rows = {str(h).lower(): (label, method) for h, label, method in clone.execute(
                    "SELECT txhash,classification,method FROM blockchain_transaction_classifications")
                    if h is not None and str(h).lower() in expected}
                after_first = clone.execute(
                    "SELECT COUNT(*) FROM blockchain_transaction_classifications").fetchone()[0]
            mismatches = [h for h, (label, method) in rows.items()
                          if label != expected[h]["legacy_label"] or method != expected[h]["method"]]
            require(first == len(expected) and len(rows) == len(expected) and
                    after_first == original_class_count + len(expected) and not mismatches,
                    "clone first-pass classification differs from Task136AG")
            second = legacy.store_transaction_classifications(clone_path, selected)
            with closing(sqlite3.connect(clone_path)) as clone:
                after_second = clone.execute(
                    "SELECT COUNT(*) FROM blockchain_transaction_classifications").fetchone()[0]
                require(after_second == after_first and
                        clone.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                        not clone.execute("PRAGMA foreign_key_check").fetchall() and
                        table_fingerprint(clone, "blockchain_transactions") ==
                        baseline["blockchain_transactions"] and
                        all(table_fingerprint(clone, t) == digest for t, digest in protected.items()),
                        "clone integrity, idempotent count, or protected tables differ")
            require(second == len(expected), "clone second-pass processed hash count differs")
        require(all(table_fingerprint(production, t) == digest for t, digest in baseline.items()),
                "production table changed during rehearsal")
    return {"project": "AxieOS", "version": "0.14", "task": "136AL",
            "coverage": {"guarded_hashes_classified_in_clone": len(expected),
                         "clone_classification_first_pass": first,
                         "clone_classification_second_pass_processed": second,
                         "clone_new_rows_first_pass": after_first - original_class_count,
                         "clone_new_rows_second_pass": after_second - after_first,
                         "shadow_label_mismatches": len(mismatches),
                         "legacy_labels": dict(sorted(Counter(r["legacy_label"] for r in expected.values()).items())),
                         "fungible_exchange_hashes_legacy_labeled_marketplace_buy": sum(
                             expected[h]["legacy_label"] == "MARKETPLACE_BUY" for h, r in route.items()
                             if r["review_lane"] == "FUNGIBLE_EXCHANGE_REVIEW"),
                         "production_ledger_rows_unchanged": prod_ledger_count,
                         "production_classifications_added": 0,
                         "production_accounting_added": 0,
                         "clone_accounting_added": 0},
            "legacy_accounting_writer_risks": risks,
            "decision": "HOLD_LEGACY_ACCOUNTING_AND_ECONOMIC_WRITERS_PENDING_SCOPED_CORRECTION",
            "accepted_financial_totals": None, "production_database_opened_read_only": True,
            "production_database_writes": 0, "clone_deleted": True,
            "network_calls": 0, "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136AL Legacy writer clone preflight", "",
             f"Guarded cohort: **{c['guarded_hashes_classified_in_clone']}** hashes. "
             f"Clone classification rows inserted first/second pass: "
             f"**{c['clone_new_rows_first_pass']}/{c['clone_new_rows_second_pass']}**. "
             f"Shadow label mismatches: **{c['shadow_label_mismatches']}**.", "",
             f"**{c['fungible_exchange_hashes_legacy_labeled_marketplace_buy']}** fungible "
             "exchange candidates carry the legacy MARKETPLACE_BUY label.", "",
             "| Legacy accounting source risk | Present |", "|---|---|"]
    lines += [f"| {k} | {'YES' if v else 'NO'} |" for k, v in
              report["legacy_accounting_writer_risks"].items()]
    lines += ["", "The clone rehearses classification storage only. The economic/accounting "
              "writers are held because they model sale gross and fees, can derive realized "
              "P/L from incomplete basis, and use a hard-coded database path. "
              "No clone or production accounting rows were added.", "",
              "Verified income, expenses, profit, and PHP recovery: **UNKNOWN**.", "",
              "Production read only | Production writes: 0 | Disposable clone: deleted | Network: 0", "",
              "VALIDATION: PASS (legacy classification clone and source audit only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    for task in ("ak", "af", "ag", "ai"):
        parser.add_argument("--" + task, type=Path)
        parser.add_argument("--" + task + "-dir", type=Path,
                            default=Path("reports/axieos_v014/task136" + task))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136al"))
    args = parser.parse_args()
    paths = {"136" + t.upper(): getattr(args, t) or find(getattr(args, t + "_dir"),
             "136" + t.upper()) for t in ("ak", "af", "ag", "ai")}
    docs, shas = {}, {}
    for key, path in paths.items():
        docs[key], shas[key] = load(path)
    report = build(docs["136AK"], docs["136AF"], docs["136AG"], docs["136AI"],
                   shas, args.db)
    report["sources"] = {k: {"filename": paths[k].name, "sha256": shas[k]}
                         for k in sorted(paths)}
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AL_Legacy_Writer_Clone_Preflight_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136AL - LEGACY WRITER CLONE PREFLIGHT")
    print(f"Guarded hashes: {c['guarded_hashes_classified_in_clone']} | Clone inserts first/second: "
          f"{c['clone_new_rows_first_pass']}/{c['clone_new_rows_second_pass']}")
    print(f"Shadow mismatches: {c['shadow_label_mismatches']} | Fungible buy mislabels: "
          f"{c['fungible_exchange_hashes_legacy_labeled_marketplace_buy']}")
    print("Legacy economic/accounting writers: HOLD | Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Production opened read only | Writes: 0 | Clone: deleted | Network: 0")
    print("VALIDATION: PASS (clone classification only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
