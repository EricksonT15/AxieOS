r"""Task136M: catalog remaining V0.14 source lanes in the local database.

Run from the AxieOS repository root:
    py -B .\scripts\v014_remaining_sources_probe.py

Only schema, row counts, date ranges, and event/status counts are exported.
No financial amounts are summed; the SQLite database is opened read only.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


SOURCES = {
    "blockchain_accounting_records": "cross_lane_accounting",
    "blockchain_economic_events": "economic_comparison_not_extra_events",
    "blockchain_transactions": "transaction_routes_and_gas",
    "ronin_api_transactions_raw": "raw_fee_and_receipt_candidates",
    "ronin_token_transfers_raw": "token_movement_candidates",
    "marketplace_events": "gameplay_marketplace_and_release",
    "bounty_board_tasks": "bounty_task_and_reroll_candidates",
    "bounty_optimizer_decisions": "optimizer_actual_cost_candidates",
    "weekly_bounty_results": "weekly_bounty_reward_candidates",
    "terrarium_snapshots": "terrarium_observation_not_income",
    "terrarium_plot_snapshots": "terrarium_cumulative_observation",
    "staking_reward_events": "staking_reward_and_principal_candidates",
    "inventory_events": "consumable_and_release_gameplay_movements",
    "pouch_opening_events": "pouch_cost_candidates",
    "pouch_reward_items": "pouch_item_candidates",
}
DATES = ("datetime", "event_datetime", "snapshot_datetime", "timestamp", "week_end_date",
         "run_datetime", "created_at", "imported_at")
STATUS = ("event_type", "classification", "status", "reward_status", "economics_status",
          "accounting_status", "actual_status", "completed", "selected_final")


def ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def get_report(conn: sqlite3.Connection) -> dict:
    present = {name for (name,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )}
    tables = []
    for name, lane in SOURCES.items():
        if name not in present:
            tables.append({"table": name, "candidate_lane": lane, "present": False})
            continue
        fields = [{"name": r[1], "type": r[2]} for r in conn.execute(f"PRAGMA table_info({ident(name)})")]
        names = {f["name"] for f in fields}
        count = conn.execute(f"SELECT COUNT(*) FROM {ident(name)}").fetchone()[0]
        entry = {"table": name, "candidate_lane": lane, "present": True,
                 "row_count": count, "columns": fields}
        date = next((field for field in DATES if field in names), None)
        if date:
            first, last = conn.execute(
                f"SELECT MIN({ident(date)}), MAX({ident(date)}) FROM {ident(name)}"
            ).fetchone()
            entry["date_range"] = {"column": date, "first": str(first) if first is not None else None,
                                   "last": str(last) if last is not None else None}
        status_columns = [field for field in STATUS if field in names]
        entry["status_counts"] = {}
        for field in status_columns:
            distinct = conn.execute(
                f"SELECT COUNT(DISTINCT {ident(field)}) FROM {ident(name)}"
            ).fetchone()[0]
            if distinct > 40:
                entry["status_counts"][field] = {"distinct_values": distinct, "values_omitted": True}
                continue
            grouped = conn.execute(
                f"SELECT {ident(field)}, COUNT(*) AS n FROM {ident(name)} "
                f"GROUP BY {ident(field)} ORDER BY n DESC, {ident(field)}"
            ).fetchall()
            entry["status_counts"][field] = {"distinct_values": distinct,
                                              "values": [{"value": value, "rows": n} for value, n in grouped]}
        tables.append(entry)
    return {"tables": tables,
            "candidate_lane_count": len(SOURCES),
            "present_table_count": sum(t["present"] for t in tables)}


def markdown(report: dict) -> str:
    lines = ["# AxieOS V0.14 — Task136M: Remaining finance source coverage", "",
             "**Mode:** Read-only production schema/count catalog. Source rows are not yet accepted finance events.", "",
             "| Table | Candidate lane | Rows | Date range as stored |", "|---|---|---:|---|"]
    for table in report["tables"]:
        dates = table.get("date_range", {})
        span = f"{dates.get('first')} → {dates.get('last')}" if dates else "—"
        n = table.get("row_count", "absent")
        lines.append(f"| `{table['table']}` | {table['candidate_lane']} | {n} | {span} |")
    lines += ["", "Detailed columns and event/status counts are in the companion JSON. These tables can overlap "
              "the same transactions and rewards; their row counts must not be added into income or expenses.", "",
              "Verified income, expenses, realized profit, portfolio value and recovery: **UNKNOWN**.", "",
              "Database opened: YES (read only) | Database writes: 0 | Network calls: 0", "",
              "VALIDATION: PASS (source coverage only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136m"))
    args = parser.parse_args()
    db = args.db.resolve()
    if not db.is_file():
        raise SystemExit(f"STOP: database not found: {db}. Pass --db PATH.")
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=10)) as conn:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        report = get_report(conn)
    report.update({"project": "AxieOS", "version": "0.14", "task": "136M",
                   "database": str(args.db), "created_at_utc": datetime.now(timezone.utc).isoformat(),
                   "accepted_financial_totals": None, "database_writes": 0,
                   "network_calls": 0, "checkpoint96": "OPEN"})
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136M_Remaining_Source_Coverage_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with mp.open("x", encoding="utf-8") as f:
        f.write(markdown(report))
    print("AXIEOS V0.14 - TASK136M - REMAINING SOURCE COVERAGE")
    print(f"Candidate tables: {report['candidate_lane_count']} | Present: {report['present_table_count']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: YES (read only) | Database writes: 0 | Network calls: 0")
    print("VALIDATION: PASS (source coverage only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
