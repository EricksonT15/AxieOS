#!/usr/bin/env python3
r"""AxieOS V1.0 no-spend inventory review; no chain, wallet, or DB writes.

Save in scripts/AxieOS_V100_NoSpend_Review.py and run from the repo root:
    py -B .\scripts\AxieOS_V100_NoSpend_Review.py

Reads the latest reconciled operational sync and saved owned-Axie roster.
The October 2026 Dojo register is historical only. No Bounty Board, purchase,
sale, release, ascension, rotation, financial total, or automatic action.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/blockchain/database/axieos.db"
SYNC = ROOT / "reports/axieos/operational_sync"
DOJO = ROOT / "reports/axieos_v013/checkpoint95/dojo_weekly_register_5.csv"
OUT = ROOT / "reports/axieos_v100/no_spend_review"
PHT = timezone(timedelta(hours=8))


def require(ok, message):
    if not ok:
        raise ValueError("STOP: " + message)


def sync_evidence(folder, as_of):
    paths = sorted(folder.glob("AxieOS_Operational_Sync_*.json"))
    require(paths, "operational sync report missing")
    path = paths[-1]
    raw = path.read_bytes()
    require(len(raw) < 25_000_000, "sync report exceeds size cap")
    doc = json.loads(raw.decode("utf-8-sig"))
    own, coverage = doc.get("ownership", {}), doc.get("raw_coverage", {})
    require(doc.get("task") == "REUSABLE_OPERATIONAL_SYNC" and
            doc.get("status") == "CURRENT_NO_WRITES" and
            doc.get("finance_totals") == "UNKNOWN" and
            doc.get("unified_finance") == "HOLD" and doc.get("checkpoint96") == "OPEN" and
            own.get("status") == "COMPLETE_AT_PINNED_BLOCK" and
            type(own.get("saved_owned_count")) is int and own["saved_owned_count"] > 0 and
            own["saved_owned_count"] == own.get("pinned_chain_owned_count") and
            own.get("chain_only_ids") == own.get("saved_only_ids") == [] and
            coverage.get("all_four_complete") is True and
            len(coverage.get("routes", [])) == 4 and
            coverage.get("transaction_hashes_absent_from_raw") == [] and
            coverage.get("transfer_hashes_absent_from_raw") == [],
            "latest operational sync is not reconciled and current; run source review")
    stamp = datetime.fromisoformat(own["pinned_block_timestamp_utc"].replace("Z", "+00:00"))
    require(stamp.tzinfo is not None, "sync timestamp missing timezone")
    local_date = stamp.astimezone(PHT).date()
    require(local_date <= as_of, "pinned block is later than requested review date")
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
            "pinned_utc": stamp.astimezone(timezone.utc).isoformat(),
            "pinned_philippines_date": local_date.isoformat(),
            "age_days": (as_of - local_date).days,
            "saved_owned_count": own["saved_owned_count"], "status": doc["status"]}


def roster(db_path, expected):
    require(db_path.is_file(), "production database missing")
    with closing(sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.execute("PRAGMA query_only=ON")
        require(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='gameplay_owned_axies'").fetchone(),
                "gameplay_owned_axies table missing")
        required = {"axie_id", "ownership_status", "axie_class", "level", "breed_count",
                    "is_collectible", "collectible_type", "is_evolved"}
        columns = {r[1] for r in conn.execute("PRAGMA table_info(gameplay_owned_axies)")}
        require(required <= columns, "owned Axie schema changed")
        rows = conn.execute("SELECT axie_id,axie_class,level,breed_count,is_collectible,"
                            "collectible_type,is_evolved FROM gameplay_owned_axies "
                            "WHERE UPPER(ownership_status)='OWNED'").fetchall()
        trait_table = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='gameplay_axie_traits'").fetchone()
        traits = {}
        if trait_table:
            trait_columns = {r[1] for r in conn.execute("PRAGMA table_info(gameplay_axie_traits)")}
            require({"axie_id", "trait_type", "trait_value", "data_source"} <= trait_columns,
                    "collection trait schema changed")
            for aid, value, source in conn.execute(
                "SELECT axie_id,trait_value,data_source FROM gameplay_axie_traits "
                "WHERE UPPER(trait_type)='COLLECTION'"):
                traits.setdefault(str(aid).strip(), []).append((str(value or "").strip(), source))
    ids = [str(r[0] or "").strip() for r in rows]
    require(len(rows) == expected and len(set(ids)) == expected and
            all(x.isdecimal() and int(x) > 0 for x in ids),
            "saved owned roster differs from the reconciled sync")
    result = []
    for raw in rows:
        aid, cls, level, breed, collectible, kind, evolved = raw
        require(level is None or (type(level) is int and level >= 0),
                f"Axie {aid}: level is invalid")
        require(breed is None or (type(breed) is int and 0 <= breed <= 7),
                f"Axie {aid}: breed count is invalid")
        issues = []
        if not str(cls or "").strip():
            issues.append("CLASS_SOURCE_MISSING")
        if level is None:
            issues.append("LEVEL_SOURCE_MISSING")
        if breed is None:
            issues.append("BREED_SOURCE_MISSING")
        collection_rows = traits.get(str(aid).strip(), [])
        collections = sorted({v for v, _ in collection_rows if v})
        sources = sorted({str(s or "") for _, s in collection_rows})
        if collectible == 1:
            if not collections:
                issues.append("COLLECTION_TRAIT_MISSING")
            elif not all(v and s == "RONIN_AXIE_GENES" for v, s in collection_rows):
                issues.append("COLLECTION_TRAIT_SOURCE_REVIEW")
        elif collections:
            issues.append("COLLECTION_STATUS_CONFLICT")
        result.append({"axie_id": str(aid).strip(), "axie_class": cls,
                       "level": level, "breed_count": breed,
                       "is_collectible_recorded": collectible == 1,
                       "collectible_type": kind, "is_evolved_recorded": evolved == 1,
                       "collections": collections, "collection_trait_sources": sources,
                       "issues": issues})
    return sorted(result, key=lambda row: int(row["axie_id"]))


def dojo_history(path, owned_ids, as_of):
    if not path.is_file():
        return {"status": "NO_HISTORICAL_REGISTER", "source": None, "rows": 0}
    raw = path.read_bytes()
    require(len(raw) < 1_000_000, "Dojo register exceeds size cap")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        entries = list(csv.DictReader(stream))
    require(all(r.get("axie_id") and r.get("observation_date") for r in entries),
            "historical Dojo register is malformed")
    dates = sorted({r["observation_date"] for r in entries})
    require(all(datetime.fromisoformat(d).date() <= as_of for d in dates),
            "historical Dojo register has a future observation")
    return {"status": "HISTORICAL_ONLY_NO_CURRENT_ASSIGNMENT" if entries else "EMPTY_REGISTER",
            "source": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
            "rows": len(entries), "observation_dates": dates,
            "ids_still_saved_owned": sorted({r["axie_id"] for r in entries} & owned_ids, key=int),
            "current_training_verified": False, "reassignment_authorized": False}


def write(output, report):
    output.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V100_NoSpend_Review_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    jp, mp, cp = (output / (stem + ext) for ext in (".json", ".md", ".csv"))
    jp.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with cp.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["axie_id", "axie_class", "level", "breed_count",
                                                    "is_collectible_recorded", "collectible_type",
                                                    "collection_traits", "issue_codes"])
        writer.writeheader()
        for row in report["exception_rows"]:
            writer.writerow({k: row.get(k) for k in writer.fieldnames
                             if k not in ("issue_codes", "collection_traits")} |
                            {"collection_traits": ",".join(row["collections"]),
                             "issue_codes": ",".join(row["issues"])})
    counts, sync, dojo = report["counts"], report["operational_sync"], report["dojo_register"]
    lines = ["# AxieOS V1.0 — No-spend inventory review", "",
             f"Saved owned Axies: **{counts['owned']}**; source exceptions: **{counts['exception_axies']}**.",
             f"Class / level / breed missing: **{counts['missing_class']} / {counts['missing_level']} / {counts['missing_breed']}**.",
             f"Recorded collectibles: **{counts['recorded_collectibles']}**; "
             f"with source-backed collection traits: **{counts['collectibles_with_source_backed_traits']}**.", "",
             f"Operational sync: **{sync['status']}**, pinned {sync['pinned_utc']}; "
             f"{sync['age_days']} Philippines calendar days old at this report date.",
             f"Historical Dojo: **{dojo['status']}**; observations "
             f"{', '.join(dojo.get('observation_dates', [])) or 'none'}. "
             "These rows do not prove today's trainees or plot assignments.", "",
             "| Issue | Axies | Treatment |", "| --- | ---: | --- |",
             f"| Unknown level | {counts['missing_level']} | Wait for an authoritative source; never infer a level from on-chain zero. |",
             f"| Unknown class | {counts['missing_class']} | Reconcile before using class in a recommendation. |",
             f"| Unknown breed | {counts['missing_breed']} | Reconcile before using breed in a recommendation. |",
             f"| Missing collection traits | {counts['collection_trait_missing']} | Preserve collectible protection; investigate source. |",
             f"| Collection trait source review | {counts['collection_trait_source_review']} | Review provenance before using collection labels. |",
             f"| Collection status conflict | {counts['collection_status_conflict']} | Reconcile flag and traits before advising. |", "",
             f"Blank legacy collectible_type field: **{counts['blank_collectible_type']}**. "
             "This field is not an exception when source-backed COLLECTION traits exist; "
             "an Axie can have multiple collection labels.", "",
             "## Recorded collectibles", "",
             "| Axie | Collection traits | Trait source | Review issue |",
             "| --- | --- | --- | --- |"]
    for row in report["collectible_rows"]:
        lines.append(f"| #{row['axie_id']} | {', '.join(row['collections']) or 'UNKNOWN'} | "
                     f"{', '.join(row['collection_trait_sources']) or 'UNKNOWN'} | "
                     f"{', '.join(row['issues']) or 'none'} |")
    lines += ["",
             "Bounty Board paused because operating funds are unavailable. No purchasing, rerolling, "
             "crafting, trading, releasing, ascending, or Dojo rotation is recommended.",
             "Financial totals: **UNKNOWN**; Unified Finance: **HOLD**; Checkpoint 96: **OPEN**.",
             "Production database read only; writes: 0; network calls: 0.", ""]
    mp.write_text("\n".join(lines), encoding="utf-8")
    return jp, mp, cp


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=DB)
    p.add_argument("--sync-dir", type=Path, default=SYNC)
    p.add_argument("--dojo-register", type=Path, default=DOJO)
    p.add_argument("--output-dir", type=Path, default=OUT)
    p.add_argument("--as-of", type=lambda s: datetime.fromisoformat(s).date(),
                   default=datetime.now(PHT).date())
    args = p.parse_args()
    sync = sync_evidence(args.sync_dir, args.as_of)
    rows = roster(args.db, sync["saved_owned_count"])
    exceptions = [r for r in rows if r["issues"]]
    codes = Counter(code for row in rows for code in row["issues"])
    dojo = dojo_history(args.dojo_register, {r["axie_id"] for r in rows}, args.as_of)
    counts = {"owned": len(rows), "exception_axies": len(exceptions),
              "missing_class": codes["CLASS_SOURCE_MISSING"],
              "missing_level": codes["LEVEL_SOURCE_MISSING"],
              "missing_breed": codes["BREED_SOURCE_MISSING"],
              "collection_trait_missing": codes["COLLECTION_TRAIT_MISSING"],
              "collection_trait_source_review": codes["COLLECTION_TRAIT_SOURCE_REVIEW"],
              "collection_status_conflict": codes["COLLECTION_STATUS_CONFLICT"],
              "recorded_collectibles": sum(r["is_collectible_recorded"] for r in rows),
              "blank_collectible_type": sum(r["is_collectible_recorded"] and
                                            not str(r["collectible_type"] or "").strip() for r in rows),
              "collectibles_with_source_backed_traits": sum(
                  r["is_collectible_recorded"] and bool(r["collections"]) and
                  r["collection_trait_sources"] == ["RONIN_AXIE_GENES"] and
                  not any(code.startswith("COLLECTION_") for code in r["issues"]) for r in rows)}
    report = {"project": "AxieOS", "version": "1.0-pilot", "task": "NO_SPEND_INVENTORY_REVIEW",
              "generated_utc": datetime.now(timezone.utc).isoformat(),
              "as_of_philippines_date": args.as_of.isoformat(),
              "operational_sync": sync, "counts": counts, "dojo_register": dojo,
              "exception_rows": exceptions,
              "collectible_rows": [r for r in rows if r["is_collectible_recorded"]],
              "bounty_board": "PAUSED_NO_OPERATING_FUNDS",
              "finance_totals": "UNKNOWN", "unified_finance": "HOLD", "checkpoint96": "OPEN",
              "automatic_execution": False, "database_opened": "READ_ONLY",
              "database_writes": 0, "network_calls": 0}
    jp, mp, cp = write(args.output_dir, report)
    print("AXIEOS V1.0 - NO-SPEND INVENTORY REVIEW")
    print("Owned:", counts["owned"], "| Exceptions:", counts["exception_axies"],
          "| Unknown levels:", counts["missing_level"])
    print("Historical Dojo:", dojo["status"], "| Bounty Board: PAUSED")
    print("Reports:", jp, mp, cp)
    print("Financial totals: UNKNOWN | Database read only | Writes: 0 | Network: 0")


if __name__ == "__main__":
    main()
