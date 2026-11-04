r"""Task136AA: combine historical and cached finance source references offline.

From the AxieOS repository root:
    py -B .\scripts\v014_combined_source_registry.py

The result is a source registry, not an accepted event ledger. Reads only
Task136R and Task136Z JSON files; no database, network, or financial totals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


EXPECTED_TOTAL_FIELDS = ("income_php", "expenses_php", "realized_profit_php",
                         "capital_recovery_php", "portfolio_value_php")


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError("STOP: " + reason)


def read_json(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing input: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def find_report(directory: Path, task: str) -> Path:
    require(directory.is_dir(), f"missing report directory: {directory}")
    matches = []
    for path in directory.glob("*.json"):
        d, _ = read_json(path)
        if d.get("task") == task and (task != "136Z" or d.get("coverage", {}).get("cached_hashes")):
            matches.append((d.get("created_at_utc", ""), path))
    require(bool(matches), f"no Task{task} JSON in {directory}; use explicit --historical/--cached")
    return max(matches)[1]


def validate_historical(d: dict) -> list[dict]:
    require(d.get("task") == "136R" and
            d.get("validation", {}).get("status") == "PASS_OFFLINE_REGISTRY_ONLY",
            "historical input must be validated Task136R registry")
    require(d["validation"].get("database_writes") == 0 and
            d["validation"].get("network_calls") == 0 and
            d["validation"].get("checkpoint96_closed") is False,
            "historical validation state changed")
    require(all(d.get("accepted_totals", {}).get(k, "MISSING") is None
                for k in EXPECTED_TOTAL_FIELDS), "historical accepted totals changed")
    rows = d["registry_rows"]
    require(len(rows) == d["coverage"]["registry_references"], "historical count mismatch")
    ids = [r.get("registry_id") for r in rows]
    require(all(ids) and len(ids) == len(set(ids)), "historical duplicate/empty registry ID")
    require(all(r.get("accepted_financial_value") is None for r in rows),
            "historical accepted value changed")
    return rows


def validate_cached(d: dict) -> list[dict]:
    require(d.get("task") == "136Z" and d.get("checkpoint96") == "OPEN" and
            d.get("database_writes") == 0 and d.get("network_calls") == 0 and
            d.get("accepted_new_events") == 0 and d.get("accepted_financial_totals") is None,
            "cached input must be unaccepted Task136Z triage")
    rows = d["inventory_rows"]
    require(len(rows) == d["coverage"]["cached_hashes"], "cached count mismatch")
    hashes = [str(r.get("txhash") or "").lower() for r in rows]
    require(all(hashes) and len(hashes) == len(set(hashes)), "cached duplicate/empty hash")
    require(Counter(r["bucket"] for r in rows) == d["coverage"]["bucket_counts"],
            "cached structural bucket counts changed")
    require(all(r.get("financial_treatment") == "UNCLASSIFIED_CANDIDATE" for r in rows),
            "cached treatment changed")
    return rows


def build(historical: dict, cached: dict, historical_path: Path, cached_path: Path,
          historical_sha: str, cached_sha: str) -> dict:
    previous = validate_historical(historical)
    newer = validate_cached(cached)
    previous_hashes = {str(r["txhash"]).lower() for r in previous if r.get("txhash")}
    newer_hashes = {str(r["txhash"]).lower() for r in newer}
    require(not previous_hashes & newer_hashes,
            "a cached hash is already in historical registry; refresh the sources before combining")
    require(len(previous_hashes) == historical["coverage"]["unique_accounting_keys"],
            "historical hash coverage differs")
    unhashed = [r for r in previous if not r.get("txhash")]
    require(len(unhashed) + len(previous_hashes) == len(previous),
            "historical references include duplicate hashes; review source registry")
    result = list(previous)
    for row in newer:
        result.append({"registry_id": "CACHED_RAW:" + row["txhash"].lower(),
                       "origin": "TASK136Z_CACHED_RAW", "lane": "CACHED_UNATTRIBUTED",
                       "accounting_key": None, "txhash": row["txhash"].lower(),
                       "date_as_stored": row["first_cached_timestamp_utc"],
                       "asset_as_stored": None, "quantity_as_stored": None,
                       "gross_as_stored": None, "source_status": None,
                       "evidence_status": "RAW_CANDIDATE_UNACCEPTED",
                       "accepted_financial_value": None,
                       "structural_bucket": row["bucket"],
                       "pair": row["pair"], "methods": row["methods"],
                       "token_symbols": row["token_symbols"],
                       "raw_transaction_count": row["raw_transaction_count"],
                       "raw_transfer_count": row["raw_transfer_count"]})
    ids = [r["registry_id"] for r in result]
    require(len(ids) == len(set(ids)), "combined registry ID collision")
    require(all(r.get("accepted_financial_value") is None for r in result),
            "combined accepted value must remain empty")
    return {"project": "AxieOS", "version": "0.14", "task": "136AA",
            "scope": "Historical registry plus post-accounting cached source references; no economic event acceptance",
            "sources": {"136R": {"filename": historical_path.name, "sha256": historical_sha},
                        "136Z": {"filename": cached_path.name, "sha256": cached_sha}},
            "coverage": {"combined_references": len(result),
                         "historical_references": len(previous),
                         "historical_hashed_references": len(previous_hashes),
                         "historical_unhashed_references": len(unhashed),
                         "new_cached_hashed_references": len(newer),
                         "hashed_overlap": 0,
                         "combined_unique_hashed_references": len(previous_hashes | newer_hashes),
                         "cached_bucket_counts": cached["coverage"]["bucket_counts"]},
            "registry_rows": result,
            "limitations": ["The historical unhashed capital and cash references cannot be excluded from economic overlap by hash.",
                            "A source reference is not necessarily a distinct economic event.",
                            "The cache has no coverage beyond its recorded latest timestamp.",
                            "No new source is accepted as income, expense, profit or recovery."],
            "accepted_totals": {k: None for k in EXPECTED_TOTAL_FIELDS},
            "validation": {"status": "PASS_OFFLINE_COMBINED_REGISTRY_ONLY",
                           "database_opened": False, "database_writes": 0,
                           "network_calls": 0, "checkpoint96_closed": False}}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136AA Combined source registry", "",
             f"Historical references: **{c['historical_references']}**; new cached hash references: "
             f"**{c['new_cached_hashed_references']}**; combined references: **{c['combined_references']}**.", "",
             f"Historical hashed references: **{c['historical_hashed_references']}**; "
             f"unhashed capital/cash references: **{c['historical_unhashed_references']}**. "
             "The new cache has **zero hash overlap** with the historical references. "
             "Economic duplication involving the unhashed references remains unresolved.", "",
             "| Cached structural bucket | Hash references |", "|---|---:|"]
    for bucket, count in c["cached_bucket_counts"].items():
        lines.append(f"| {bucket} | {count} |")
    lines += ["", "This is a source index. Each cached hash retains its raw structure and "
              "UNACCEPTED status; there is no automated income, expense or trade classification. "
              "The companion JSON preserves source file SHA-256 digests for review.", "",
              "Verified financial totals: **UNKNOWN**. Checkpoint 96: **OPEN**.", "",
              "Database opened: NO | Writes: 0 | Network calls: 0", "",
              "VALIDATION: PASS (offline combined source registry only).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical", type=Path)
    parser.add_argument("--cached", type=Path)
    parser.add_argument("--historical-dir", type=Path, default=Path("reports/axieos_v014/task136r"))
    parser.add_argument("--cached-dir", type=Path, default=Path("reports/axieos_v014/task136z"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136aa"))
    args = parser.parse_args()
    hp = args.historical or find_report(args.historical_dir, "136R")
    cp = args.cached or find_report(args.cached_dir, "136Z")
    h, hsha = read_json(hp)
    c, csha = read_json(cp)
    report = build(h, c, hp, cp, hsha, csha)
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AA_Combined_Source_Registry_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
            + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    with mp.open("x", encoding="utf-8") as stream:
        stream.write(markdown(report))
    cov = report["coverage"]
    print("AXIEOS V0.14 - TASK136AA - COMBINED SOURCE REGISTRY")
    print(f"Historical: {cov['historical_references']} | Cached: {cov['new_cached_hashed_references']} "
          f"| Combined: {cov['combined_references']} | Hash overlap: {cov['hashed_overlap']}")
    print(f"Unhashed references requiring separate reconciliation: {cov['historical_unhashed_references']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network calls: 0")
    print("VALIDATION: PASS (offline combined source registry only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
