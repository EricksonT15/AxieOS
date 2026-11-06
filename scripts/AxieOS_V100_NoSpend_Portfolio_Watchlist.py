#!/usr/bin/env python3
r"""Build one read-only watchlist for every saved owned Axie.

Save as scripts/AxieOS_V100_NoSpend_Portfolio_Watchlist.py, then from the repo root:
    py -B .\scripts\AxieOS_V100_NoSpend_Portfolio_Watchlist.py

Requires the existing AxieOS_V100_NoSpend_Review.py and the latest reconciled
operational sync. It never makes a trade, rotates Dojo occupants, calculates
financial totals, updates the roster, or calls a network service.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import AxieOS_V100_NoSpend_Review as source


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/axieos_v100/no_spend_watchlist"
PHT = timezone(timedelta(hours=8))
FIELDS = ("axie_id", "axie_class", "level", "breed_count", "collection_traits",
          "is_evolved_recorded", "review_lane", "review_flags", "next_review")


def require(ok, message):
    if not ok:
        raise ValueError("STOP: " + message)


def build(db, sync_dir, as_of):
    sync = source.sync_evidence(sync_dir, as_of)
    roster = source.roster(db, sync["saved_owned_count"])
    require(len(roster) == sync["saved_owned_count"], "roster and sync count differ")
    rows = []
    for axie in roster:
        flags = []
        if axie["is_collectible_recorded"]:
            flags.append("SOURCE_BACKED_COLLECTIBLE" if
                         axie["collections"] and
                         axie["collection_trait_sources"] == ["RONIN_AXIE_GENES"] and
                         not any(x.startswith("COLLECTION_") for x in axie["issues"])
                         else "COLLECTIBLE_SOURCE_REVIEW")
        flags.extend(axie["issues"])
        if axie["is_evolved_recorded"]:
            flags.append("EVOLVED_RECORDED")
        if "COLLECTIBLE_SOURCE_REVIEW" in flags or any(x.startswith("COLLECTION_") for x in flags):
            lane = "COLLECTION_EVIDENCE_REVIEW"
        elif axie["is_collectible_recorded"]:
            lane = "PROTECTED_COLLECTIBLE"
        elif axie["issues"]:
            lane = "SOURCE_EXCEPTION"
        else:
            lane = "OBSERVE_ONLY"
        next_review = ("Reconcile collection evidence; retain protection" if lane == "COLLECTION_EVIDENCE_REVIEW"
                       else "Keep collectible protection; review only" if lane == "PROTECTED_COLLECTIBLE"
                       else "Wait for authoritative level or trait evidence" if lane == "SOURCE_EXCEPTION"
                       else "No action without a fresh source and separate approval")
        rows.append({"axie_id": axie["axie_id"], "axie_class": axie["axie_class"],
                     "level": axie["level"], "breed_count": axie["breed_count"],
                     "collection_traits": axie["collections"],
                     "is_evolved_recorded": axie["is_evolved_recorded"],
                     "review_lane": lane, "review_flags": flags, "next_review": next_review,
                     "sale_approved": False, "release_approved": False,
                     "dojo_reassignment_authorized": False})
    require(len({r["axie_id"] for r in rows}) == len(rows), "duplicate Axie ID")
    lanes = dict(sorted(Counter(r["review_lane"] for r in rows).items()))
    require(sum(lanes.values()) == len(rows), "watchlist lane count differs")
    return sync, rows, lanes


def write(folder, doc):
    folder.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V100_NoSpend_Portfolio_Watchlist_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    jp, mp, cp = (folder / (stem + ext) for ext in (".json", ".md", ".csv"))
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(doc, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    with cp.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for row in doc["axies"]:
            writer.writerow({**{key: row[key] for key in FIELDS},
                             "collection_traits": ", ".join(row["collection_traits"]),
                             "review_flags": ", ".join(row["review_flags"])})
    lines = ["# AxieOS V1.0 — No-spend portfolio watchlist", "",
             f"As of Philippine date: **{doc['as_of_philippines_date']}**. "
             f"Saved owned Axies: **{doc['owned_axies']}**. "
             f"Pinned sync age: **{doc['sync_age_days']} day(s)**.", "",
             "| Review lane | Axies |", "| --- | ---: |"]
    lines += [f"| {lane} | {count} |" for lane, count in doc["review_lanes"].items()]
    lines += ["", f"Unknown levels: **{doc['unknown_levels']}**. "
              "Source-backed collectibles: **{doc['source_backed_collectibles']}**. "
              "The CSV contains one row per Axie and review flags.", "",
              "No purchase, sale, release, ascension, reroll, or Dojo reassignment is approved. "
              "Bounty Board remains paused. Financial totals remain UNKNOWN; "
              "Unified Finance HOLD; Checkpoint 96 OPEN.", "",
              "Database read only | Writes: 0 | Network calls: 0", ""]
    mp.write_text("\n".join(lines), encoding="utf-8")
    return jp, mp, cp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=source.DB)
    parser.add_argument("--sync-dir", type=Path, default=source.SYNC)
    parser.add_argument("--output-dir", type=Path, default=OUT)
    parser.add_argument("--as-of", type=lambda s: datetime.fromisoformat(s).date(),
                        default=datetime.now(PHT).date())
    args = parser.parse_args()
    sync, rows, lanes = build(args.db, args.sync_dir, args.as_of)
    report = {"project": "AxieOS", "version": "1.0-pilot", "task": "NO_SPEND_PORTFOLIO_WATCHLIST",
              "generated_utc": datetime.now(timezone.utc).isoformat(),
              "as_of_philippines_date": args.as_of.isoformat(),
              "operational_sync_path": sync["path"], "operational_sync_sha256": sync["sha256"],
              "sync_age_days": sync["age_days"], "owned_axies": len(rows),
              "unknown_levels": sum(r["level"] is None for r in rows),
              "source_backed_collectibles": sum("SOURCE_BACKED_COLLECTIBLE" in r["review_flags"] for r in rows),
              "review_lanes": lanes, "axies": rows,
              "bounty_board": "PAUSED_NO_OPERATING_FUNDS", "financial_totals": "UNKNOWN",
              "unified_finance": "HOLD", "checkpoint96": "OPEN",
              "automatic_execution": False, "database_opened": "READ_ONLY", "database_writes": 0,
              "network_calls": 0}
    paths = write(args.output_dir, report)
    print("AXIEOS V1.0 - NO-SPEND PORTFOLIO WATCHLIST")
    print("Owned:", len(rows), "| Review lanes:", lanes)
    print("Unknown levels:", report["unknown_levels"], "| Source-backed collectibles:",
          report["source_backed_collectibles"])
    print("Reports:", *paths)
    print("Bounty Board: PAUSED | Finance: HOLD | Checkpoint 96: OPEN")
    print("Database: read only | Writes: 0 | Network: 0")


if __name__ == "__main__":
    main()
