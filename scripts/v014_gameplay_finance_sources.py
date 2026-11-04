r"""Task136N: export small gameplay finance candidate tables, read only.

Run from the AxieOS repository root:
    py -B .\scripts\v014_gameplay_finance_sources.py

This does not add rows to Unified Finance or calculate any financial total.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


TABLES = {
    "marketplace_events": "manual_marketplace_not_an_extra_sale_or_purchase",
    "marketplace_event_bounty_tasks": "marketplace_to_bounty_link",
    "bounty_board_tasks": "task_reward_and_reroll_candidates",
    "weekly_bounty_results": "weekly_reward_claim_candidate",
    "terrarium_snapshots": "claimable_observation_not_income",
    "terrarium_plot_snapshots": "cumulative_plot_observation_not_income",
    "staking_reward_events": "claims_and_principal_movements",
    "inventory_events": "gameplay_item_movements",
    "pouch_opening_events": "pouch_cost_candidate",
    "pouch_reward_items": "pouch_item_movements",
}
MAX_ROWS_PER_TABLE = 10000


def ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def extract(conn: sqlite3.Connection) -> dict:
    present = {name for (name,) in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )}
    tables = {}
    for name, role in TABLES.items():
        if name not in present:
            tables[name] = {"candidate_role": role, "present": False, "rows": None}
            continue
        count = conn.execute(f"SELECT COUNT(*) FROM {ident(name)}").fetchone()[0]
        if count > MAX_ROWS_PER_TABLE:
            raise ValueError(f"STOP: {name} has {count} rows; narrow the extraction before exporting")
        cursor = conn.execute(f"SELECT * FROM {ident(name)}")
        columns = [c[0] for c in cursor.description]
        rows = [dict(zip(columns, values)) for values in cursor.fetchall()]
        tables[name] = {"candidate_role": role, "present": True, "row_count": count,
                        "columns": columns, "rows": rows}
    return tables


def validate(tables: dict) -> tuple[dict, dict]:
    counts = {name: entry.get("row_count") for name, entry in tables.items()}
    unresolved_links = {}
    for name, entry in tables.items():
        if entry["present"]:
            if entry["row_count"] != len(entry["rows"]):
                raise ValueError(f"STOP: {name}: row count changed during read")
            if "id" in entry["columns"]:
                ids = [row["id"] for row in entry["rows"]]
                if None in ids or len(set(ids)) != len(ids):
                    raise ValueError(f"STOP: {name}: duplicate or empty id")
    for child, parent, child_field in (
        ("terrarium_plot_snapshots", "terrarium_snapshots", "terrarium_snapshot_id"),
        ("pouch_reward_items", "pouch_opening_events", "pouch_opening_event_id"),
        ("inventory_events", "marketplace_events", "related_marketplace_event_id"),
        ("staking_reward_events", "bounty_board_tasks", "related_bounty_task_id"),
        ("marketplace_event_bounty_tasks", "marketplace_events", "marketplace_event_id"),
        ("marketplace_event_bounty_tasks", "bounty_board_tasks", "bounty_task_id"),
    ):
        if not tables[child]["present"] or not tables[parent]["present"]:
            continue
        if child_field not in tables[child]["columns"] or "id" not in tables[parent]["columns"]:
            continue
        parent_ids = {row["id"] for row in tables[parent]["rows"]}
        dangling = [row[child_field] for row in tables[child]["rows"]
                    if row[child_field] is not None and row[child_field] not in parent_ids]
        unresolved_links[f"{child}.{child_field}"] = len(dangling)
    return counts, unresolved_links


def markdown(report: dict) -> str:
    lines = ["# AxieOS V0.14 — Task136N: Gameplay finance source rows", "",
             "**Mode:** Read-only source extraction. No rows promoted into verified Unified Finance.", "",
             "| Source table | Rows | Candidate role |", "|---|---:|---|"]
    for name, entry in report["tables"].items():
        lines.append(f"| `{name}` | {entry.get('row_count', 'absent')} | {entry['candidate_role']} |")
    lines += ["", "Manual marketplace events may overlap the blockchain sale/purchase records. "
              "Weekly bounty results may overlap staking claims, and Terrarium snapshots are claimable or "
              "cumulative observations. Pouch and inventory rows may describe the same token transfers. "
              "None is an additional verified income or expense solely because this extraction found it.", "",
              "The companion JSON preserves source IDs, amounts as stored, notes, and related IDs for a later "
              "crosswalk. No value is converted or summed.", "",
              "Verified income, expenses, realized profit and recovery: **UNKNOWN**.", "",
              "Database opened: YES (read only) | Database writes: 0 | Network calls: 0", "",
              "VALIDATION: PASS (extraction only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136n"))
    args = parser.parse_args()
    db = args.db.resolve()
    if not db.is_file():
        raise SystemExit(f"STOP: database not found: {db}. Pass --db PATH.")
    with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=10)) as conn:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        tables = extract(conn)
    counts, unresolved_links = validate(tables)
    report = {"project": "AxieOS", "version": "0.14", "task": "136N",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "source_database": str(args.db), "table_counts": counts,
              "unresolved_local_link_counts": unresolved_links, "tables": tables,
              "accepted_financial_totals": None, "database_writes": 0, "network_calls": 0,
              "checkpoint96": "OPEN"}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136N_Gameplay_Finance_Sources_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with mp.open("x", encoding="utf-8") as f:
        f.write(markdown(report))
    print("AXIEOS V0.14 - TASK136N - GAMEPLAY FINANCE SOURCE ROWS")
    print(f"Tables present: {sum(v is not None for v in counts.values())} | Rows: {sum(v or 0 for v in counts.values())}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: YES (read only) | Database writes: 0 | Network calls: 0")
    print("VALIDATION: PASS (extraction only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
