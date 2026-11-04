r"""Task136AO: offline classification overlay for seven fungible exchange candidates.

From the AxieOS repository root:
    py -B .\scripts\v014_fungible_classification_overlay.py

Reads only Task136AG/AI/AL JSON. Creates an auditable overlay for the seven
WETH/SLP pairs that the legacy classifier calls marketplace purchases. This
does not change the legacy classifier, SQLite, accounting, or financial totals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("STOP: " + message)


def load(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing source: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def find(explicit: Path | None, directory: Path, task: str) -> Path:
    if explicit is not None:
        return explicit
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        doc, _ = load(path)
        if doc.get("task") == task and doc.get("checkpoint96") == "OPEN":
            matches.append((doc.get("created_at_utc", ""), path))
    require(bool(matches), f"missing Task{task} JSON in {directory}; pass --{task[3:].lower()} PATH")
    return max(matches)[1]


def build(ag: dict, ai: dict, al: dict, paths: dict, shas: dict) -> dict:
    require(all(doc.get("task") == task and doc.get("checkpoint96") == "OPEN"
                and doc.get("accepted_financial_totals") is None
                for task, doc in (("136AG", ag), ("136AI", ai), ("136AL", al))),
            "source task, checkpoint, or financial boundary differs")
    require(al["sources"]["136AG"]["sha256"] == shas["136AG"] and
            al["sources"]["136AI"]["sha256"] == shas["136AI"] and
            al["decision"] == "HOLD_LEGACY_ACCOUNTING_AND_ECONOMIC_WRITERS_PENDING_SCOPED_CORRECTION",
            "Task136AL does not match source snapshots or writer hold")
    candidates = ag["candidates"]
    legacy = {str(row["txhash"]).lower(): row for row in candidates}
    require(len(candidates) == len(legacy) == ag["coverage"]["guarded_hashes"] ==
            al["coverage"]["guarded_hashes_classified_in_clone"] and
            al["coverage"]["shadow_label_mismatches"] == 0,
            "guarded cohort differs from clone classification")
    route_rows = ai["new_candidates"]
    routes = {str(row["txhash"]).lower(): row for row in route_rows}
    require(len(routes) == len(route_rows) == ai["coverage"]["new_marketplace_shaped_pairs"]
            and set(routes).issubset(legacy), "paired route coverage differs")
    flagged = {h for h, row in routes.items()
               if row["review_lane"] == "FUNGIBLE_EXCHANGE_REVIEW"}
    require(flagged == {h for h, row in routes.items()
                        if row["control_status"] == "FUNGIBLE_ROUTE_REVIEW"}
            and len(flagged) == al["coverage"]["fungible_exchange_hashes_legacy_labeled_marketplace_buy"]
            and len(flagged) == 7, "fungible review cohort changed; inspect source evidence")
    overlay = []
    for h in sorted(flagged):
        row, route = legacy[h], routes[h]
        require(row["legacy_label"] == "MARKETPLACE_BUY" and
                row["shape"] == "BUY_CANDIDATE" and
                route["shape"] == "BUY_CANDIDATE" and
                route["asset_symbol"] == "SLP" and
                len(row["assets"]) == 2 and "Ronin Wrapped Ether" in row["assets"],
                f"{h}: expected exact WETH/SLP purchase-shaped route differs")
        overlay.append({"txhash": h, "legacy_label": row["legacy_label"],
                        "proposed_evidence_label": "FUNGIBLE_EXCHANGE_CANDIDATE",
                        "reason": "WETH out and SLP in; paired fungible transfers",
                        "route_status": route["control_status"],
                        "accepted_marketplace_purchase": False,
                        "accepted_swap_financial_treatment": None})
    other = {h: row["legacy_label"] for h, row in legacy.items() if h not in flagged}
    require(len(other) + len(overlay) == len(legacy) and
            sum(v == "MARKETPLACE_BUY" for v in other.values()) ==
            ag["coverage"]["legacy_labels"]["MARKETPLACE_BUY"] - len(overlay),
            "overlay would affect labels outside the seven flagged hashes")
    return {"project": "AxieOS", "version": "0.14", "task": "136AO",
            "sources": {key: {"filename": paths[key].name, "sha256": shas[key]}
                        for key in sorted(paths)},
            "coverage": {"guarded_hashes": len(legacy),
                         "paired_candidate_hashes": len(routes),
                         "fungible_overrides": len(overlay),
                         "other_guarded_hashes_untouched": len(other),
                         "legacy_marketplace_buy": ag["coverage"]["legacy_labels"]["MARKETPLACE_BUY"],
                         "marketplace_buy_after_overlay": Counter(other.values())["MARKETPLACE_BUY"]},
            "overrides": overlay, "accepted_financial_totals": None,
            "legacy_writer_decision": "HOLD", "database_opened": False,
            "database_writes": 0, "network_calls": 0, "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136AO Fungible classification overlay", "",
             f"Guarded cohort: **{c['guarded_hashes']}** hashes; paired candidates: "
             f"**{c['paired_candidate_hashes']}**. Seven WETH/SLP hashes have a proposed "
             "fungible exchange candidate label.", "",
             "| Legacy marketplace buys | After overlay | Other guarded hashes untouched |",
             "|---:|---:|---:|",
             f"| {c['legacy_marketplace_buy']} | {c['marketplace_buy_after_overlay']} | "
             f"{c['other_guarded_hashes_untouched']} |", "",
             "The overlay is evidence classification only; it does not establish swap "
             "treatment or authorize the legacy accounting/economic writers. The seven "
             "transaction hashes and their source digests are in the JSON report.", "",
             "Verified income, expenses, profit, and PHP recovery: **UNKNOWN**.", "",
             "Database opened: NO | Writes: 0 | Network: 0", "",
             "VALIDATION: PASS (offline classification overlay only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for suffix in ("ag", "ai", "al"):
        parser.add_argument("--" + suffix, type=Path)
        parser.add_argument("--" + suffix + "-dir", type=Path,
                            default=Path("reports/axieos_v014/task136" + suffix))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136ao"))
    args = parser.parse_args()
    paths = {"136" + suffix.upper(): find(getattr(args, suffix),
              getattr(args, suffix + "_dir"), "136" + suffix.upper())
             for suffix in ("ag", "ai", "al")}
    docs, shas = {}, {}
    for task, path in paths.items():
        docs[task], shas[task] = load(path)
    report = build(docs["136AG"], docs["136AI"], docs["136AL"], paths, shas)
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AO_Fungible_Classification_Overlay_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136AO - FUNGIBLE CLASSIFICATION OVERLAY")
    print(f"Guarded hashes: {c['guarded_hashes']} | Fungible candidate overrides: "
          f"{c['fungible_overrides']} | Marketplace buy labels: "
          f"{c['legacy_marketplace_buy']} -> {c['marketplace_buy_after_overlay']}")
    print("Verified income, expenses, profit, and PHP recovery: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (offline classification overlay only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
