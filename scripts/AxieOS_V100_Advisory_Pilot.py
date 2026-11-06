#!/usr/bin/env python3
r"""V1.0 pilot: evidence-backed Bounty Board review suggestions, read-only.

Save as scripts/AxieOS_V100_Advisory_Pilot.py; from the repository root:
    py -B .\scripts\AxieOS_V100_Advisory_Pilot.py

Uses the latest reconciled operational sync and today's saved board. Bounty
review is paused by default while operating funds are unavailable. Resume it
only with --enable-bounty-review after the user decides to return to bounties.
No reroll, wallet action, financial calculation, sale, release, or database
write is performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/blockchain/database/axieos.db"
SYNC = ROOT / "reports/axieos/operational_sync"
OUT = ROOT / "reports/axieos_v100/advisory_pilot"
PHT = timezone(timedelta(hours=8))
LOW_BP_REVIEW = 200  # User's saved policy; not a game-wide threshold.
MAX_REROLLS = 10     # Official Bounty Board daily per-slot cap.


def require(ok, reason):
    if not ok:
        raise ValueError("STOP: " + reason)


def latest_sync(folder, as_of):
    matches = sorted(folder.glob("AxieOS_Operational_Sync_*.json"))
    require(matches, "operational sync report missing")
    path = matches[-1]
    raw = path.read_bytes()
    require(len(raw) < 25_000_000, "sync report exceeds size cap")
    doc = json.loads(raw.decode("utf-8-sig"))
    own, coverage = doc.get("ownership", {}), doc.get("raw_coverage", {})
    require(doc.get("task") == "REUSABLE_OPERATIONAL_SYNC" and
            doc.get("status") == "CURRENT_NO_WRITES" and
            doc.get("finance_totals") == "UNKNOWN" and
            doc.get("unified_finance") == "HOLD" and doc.get("checkpoint96") == "OPEN" and
            own.get("status") == "COMPLETE_AT_PINNED_BLOCK" and
            own.get("saved_owned_count") == own.get("pinned_chain_owned_count") and
            own.get("chain_only_ids") == own.get("saved_only_ids") == [] and
            coverage.get("all_four_complete") is True and len(coverage.get("routes", [])) == 4 and
            coverage.get("transaction_hashes_absent_from_raw") == [] and
            coverage.get("transfer_hashes_absent_from_raw") == [],
            "latest sync is not a reconciled no-write report; run the operational update")
    stamp = datetime.fromisoformat(own["pinned_block_timestamp_utc"].replace("Z", "+00:00"))
    require(stamp.tzinfo is not None and stamp.astimezone(PHT).date() == as_of,
            "latest pinned sync is not from the requested Philippine date")
    return path, hashlib.sha256(raw).hexdigest(), doc


def read_board(path, expected_owned, as_of):
    require(path.is_file(), "production database missing")
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        required = {
            "gameplay_owned_axies": {"axie_id", "ownership_status", "level"},
            "gameplay_daily_sessions": {"id", "session_date", "player_id", "ending_fortune_slips"},
            "bounty_board_tasks": {"id", "daily_session_id", "task_slot", "roll_number",
                                   "requirement", "reward_bp", "reroll_cost_slips", "completed", "selected_final"},
        }
        for table, columns in required.items():
            present = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
            require(present, "missing table " + table)
            actual = {r[1] for r in db.execute("PRAGMA table_info(" + table + ")")}
            require(columns <= actual, "missing columns in " + table)
        axies = db.execute("SELECT axie_id, level FROM gameplay_owned_axies "
                           "WHERE UPPER(ownership_status)='OWNED'").fetchall()
        require(len(axies) == expected_owned and len({str(r[0]) for r in axies}) == expected_owned,
                "saved roster differs from latest sync")
        sessions = db.execute("SELECT id, ending_fortune_slips FROM gameplay_daily_sessions "
                              "WHERE session_date=? AND player_id='primary'", (as_of.isoformat(),)).fetchall()
        require(len(sessions) <= 1, "multiple primary daily sessions")
        if not sessions:
            return {"status": "NO_CURRENT_BOARD", "recorded_slips": None,
                    "tasks": [], "owned_axies": len(axies),
                    "unknown_axie_levels": sum(r[1] is None for r in axies)}
        sid, slips = sessions[0]
        require(slips is None or (type(slips) is int and slips >= 0),
                "recorded Fortune Slips invalid")
        tasks = db.execute("SELECT id, task_slot, roll_number, requirement, reward_bp, "
                           "reroll_cost_slips, completed FROM bounty_board_tasks "
                           "WHERE daily_session_id=? AND selected_final=1 ORDER BY task_slot", (sid,)).fetchall()
        slots = [r[1] for r in tasks]
        require(len(set(slots)) == len(slots) and all(type(s) is int and 1 <= s <= 6 for s in slots),
                "selected task slots invalid or duplicated")
        result = []
        for row in tasks:
            tid, slot, roll, requirement, bp, cost, done = row
            require(type(tid) is int and type(roll) is int and 0 <= roll <= MAX_REROLLS and
                    type(bp) is int and bp >= 0 and (cost is None or (type(cost) is int and cost >= 0)) and
                    done in (0, 1), "selected task row invalid")
            result.append({"task_id": tid, "slot": slot, "roll_number": roll,
                           "requirement": str(requirement or ""), "reward_bp": bp,
                           "reroll_cost_slips_recorded": cost, "completed": bool(done)})
        return {"status": "CURRENT_BOARD_SAVED" if len(tasks) == 6 else "PARTIAL_BOARD_SAVED",
                "recorded_slips": slips, "tasks": result,
                "owned_axies": len(axies),
                "unknown_axie_levels": sum(r[1] is None for r in axies)}


def advise(board, as_of):
    if board["status"] != "CURRENT_BOARD_SAVED":
        return []
    recommendations = []
    for task in board["tasks"]:
        bp, cost, roll = (task[k] for k in
                          ("reward_bp", "reroll_cost_slips_recorded", "roll_number"))
        if task["completed"] or bp >= LOW_BP_REVIEW or roll >= MAX_REROLLS:
            continue
        recommendations.append({
            "type": "REVIEW_LOW_BP_REROLL", "task_id": task["task_id"], "slot": task["slot"],
            "action": "Compare the current in-app reroll cost and Fortune Slips balance before deciding",
            "evidence": {"session_date": as_of.isoformat(), "task_id": task["task_id"],
                         "requirement": task["requirement"], "reward_bp": bp,
                         "roll_number": roll, "reroll_cost_slips_recorded": cost,
                         "ending_fortune_slips_recorded": board["recorded_slips"]},
            "reason": "Recorded reward is below the user's 200 BP review threshold",
            "expected_benefit": "UNKNOWN; next bounty is random",
            "expected_cost": "UNKNOWN; recorded cost may describe the prior roll",
            "risk": "Live board or slip balance may have changed; replacement may be worse",
            "confidence": "LOW; review cue only, not a live cost or benefit estimate",
            "alternative": "Keep the task and review its requirement separately",
            "execution_authorized": False,
        })
    return sorted(recommendations, key=lambda r:(r["evidence"]["reward_bp"],r["slot"]))


def write_report(folder, report):
    folder.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V100_Advisory_Pilot_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    jp, mp = folder / (stem + ".json"), folder / (stem + ".md")
    with jp.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    lines = ["# AxieOS V1.0 — Advisory pilot", "",
             f"As of Philippine date: **{report['as_of_philippines_date']}**. "
             f"Board: **{report['board']['status']}**.",
             f"Bounty review: **{report['bounty_review_status']}**. "
             f"Review suggestions: **{len(report['recommendations'])}**. "
             "Human review required; no automatic action.", "",
             "These suggestions use the user's <200 BP review rule and the saved board, "
             "not live App.Axie state. A reroll's next reward is unknown.", ""]
    for rec in report["recommendations"]:
        ev = rec["evidence"]
        lines += [f"## Slot {rec['slot']} — {ev['reward_bp']} BP", "",
                  f"- Suggested review: {rec['action']}",
                  f"- Evidence: task {ev['task_id']}, roll {ev['roll_number']}, "
                  f"recorded slips {ev['ending_fortune_slips_recorded']}, "
                  f"recorded prior-roll cost {ev['reroll_cost_slips_recorded']}",
                  f"- Requirement: {ev['requirement']}",
                  f"- Risk: {rec['risk']}",
                  f"- Alternative: {rec['alternative']}", ""]
    if not report["recommendations"]:
        lines += ["No reroll suggestion was issued. Bounty review remains paused until "
                  "the user chooses to resume after operating funds become available. "
                  "A missing or partial current board also does not justify using "
                  "older tasks as today's advice.", ""]
    lines += ["Financial totals: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN", "",
              "Database opened read only | Writes: 0 | Network calls: 0", ""]
    mp.write_text("\n".join(lines), encoding="utf-8")
    return jp, mp


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=DB)
    p.add_argument("--sync-dir", type=Path, default=SYNC)
    p.add_argument("--output-dir", type=Path, default=OUT)
    p.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(PHT).date())
    p.add_argument("--enable-bounty-review", action="store_true",
                   help="Opt in only after operating funds are available and the user resumes bounty play")
    args = p.parse_args()
    source_path, source_sha, source = latest_sync(args.sync_dir, args.as_of)
    board = read_board(args.db, source["ownership"]["saved_owned_count"], args.as_of)
    advice = advise(board, args.as_of) if args.enable_bounty_review else []
    bounty_review_status = "USER_ENABLED" if args.enable_bounty_review else "PAUSED_NO_OPERATING_FUNDS"
    report = {"project": "AxieOS", "version": "1.0-pilot", "task": "ADVISORY_PILOT",
              "generated_utc": datetime.now(timezone.utc).isoformat(),
              "as_of_philippines_date": args.as_of.isoformat(),
              "operational_sync": {"path": str(source_path), "sha256": source_sha},
              "policy": {"low_bp_review_threshold_exclusive": LOW_BP_REVIEW,
                         "maximum_rerolls_per_slot": MAX_REROLLS,
                         "official_guide": "https://support.axieinfinity.com/hc/en-us/articles/42313486303771-App-Axie-Codex-and-Bounty-Board"},
              "board": board, "bounty_review_status": bounty_review_status,
              "recommendations": advice,
              "status": "BOUNTY_PAUSED_NO_OPERATING_FUNDS" if not args.enable_bounty_review else
                        ("ADVISORY_REVIEW" if advice else board["status"]),
              "accepted_financial_totals": None, "unified_finance": "HOLD",
              "checkpoint96": "OPEN", "automatic_execution": False,
              "database_opened": "READ_ONLY", "database_writes": 0, "network_calls": 0}
    jp, mp = write_report(args.output_dir, report)
    print("AXIEOS V1.0 - READ-ONLY ADVISORY PILOT")
    print("Board:", board["status"], "| Low-BP review suggestions:", len(advice))
    print("Bounty review:", bounty_review_status)
    print("Owned Axies:", board["owned_axies"], "| Unknown levels:", board["unknown_axie_levels"])
    print("Reports:", jp, mp)
    print("Financial totals: UNKNOWN | Automatic execution: NO | Database writes: 0 | Network: 0")


if __name__ == "__main__":
    main()
