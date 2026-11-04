r"""Task136E: inspect local consumable inventory source coverage, read only.

Run from the AxieOS repository root:
    py -B .\scripts\v014_consumable_source_probe.py

The database is opened in SQLite read-only mode. The only files created are
timestamped JSON and Markdown reports in reports/axieos_v014/task136e/.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


DEFAULT_DB = Path("data/blockchain/database/axieos.db")
DEFAULT_OUT = Path("reports/axieos_v014/task136e")
NAME_RE = re.compile(r"consum|inventory|pouch|feed|craft|release|blockchain_accounting|blockchain_economic|blockchain_transactions|token_transfer", re.I)
TIME_COLUMNS = ("datetime", "event_datetime", "timestamp", "block_timestamp", "created_at", "imported_at")
TOKEN_COLUMNS = ("asset_token_id", "token_id", "item_token_id")


def ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def get_schema(conn: sqlite3.Connection) -> list[dict]:
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    result = []
    for (name,) in tables:
        columns = conn.execute(f"PRAGMA table_info({ident(name)})").fetchall()
        names = [c[1] for c in columns]
        if not (NAME_RE.search(name) or any(re.search(r"consum|inventory|asset_token_id|item_token_id", c, re.I) for c in names)):
            continue
        entry = {
            "table": name,
            "columns": [{"name": c[1], "type": c[2]} for c in columns],
            "row_count": conn.execute(f"SELECT COUNT(*) FROM {ident(name)}").fetchone()[0],
        }
        time_col = next((c for c in TIME_COLUMNS if c in names), None)
        if time_col:
            first, last = conn.execute(
                f"SELECT MIN({ident(time_col)}), MAX({ident(time_col)}) FROM {ident(name)}"
            ).fetchone()
            entry["date_range"] = {"column": time_col, "first": str(first) if first is not None else None,
                                   "last": str(last) if last is not None else None}
        token_col = next((c for c in TOKEN_COLUMNS if c in names), None)
        if token_col:
            entry["target_token_row_counts"] = {
                token: conn.execute(
                    f"SELECT COUNT(*) FROM {ident(name)} WHERE CAST({ident(token_col)} AS TEXT)=?",
                    (token,),
                ).fetchone()[0]
                for token in ("1", "2")
            }
        result.append(entry)
    return result


def accounting_summary(conn: sqlite3.Connection, tables: list[dict]) -> dict:
    entry = next((t for t in tables if t["table"] == "blockchain_accounting_records"), None)
    if not entry:
        return {"available": False, "reason": "accounting table absent"}
    names = {c["name"] for c in entry["columns"]}
    needed = {"asset_token_id", "event_type", "direction", "datetime"}
    if not needed <= names:
        return {"available": False, "reason": "required accounting columns absent"}
    results = {}
    for token in ("1", "2"):
        # Only counts and date extrema. Do not treat this slice as full inventory.
        rows = conn.execute(
            "SELECT event_type, direction, COUNT(*), MIN(datetime), MAX(datetime) "
            "FROM blockchain_accounting_records WHERE CAST(asset_token_id AS TEXT)=? "
            "AND asset_category='CONSUMABLE' GROUP BY event_type, direction ORDER BY event_type, direction",
            (token,),
        ).fetchall() if "asset_category" in names else []
        results[token] = [
            {"event_type": event, "direction": direction, "rows": n,
             "first": str(first), "last": str(last)}
            for event, direction, n, first, last in rows
        ]
    return {"available": True, "token_event_coverage": results,
            "note": "Counts do not establish opening balance, unit cost, or lot assignment."}


def render(report: dict) -> str:
    out = ["# AxieOS V0.14 — Task136E: Consumable source probe", "",
           "**Mode:** SQLite read-only; schema and coverage only. No basis or profit accepted.", "",
           f"Database: `{report['database']['path']}` ({report['database']['size_bytes']} bytes).", "",
           "| Candidate table | Rows | First → last (stored) | Token 1 rows | Token 2 rows |",
           "|---|---:|---|---:|---:|"]
    for t in report["candidate_tables"]:
        span = t.get("date_range", {})
        dates = f"{span.get('first')} → {span.get('last')}" if span else "—"
        tokens = t.get("target_token_row_counts", {})
        out.append(f"| `{t['table']}` | {t['row_count']} | {dates} | {tokens.get('1', '—')} | {tokens.get('2', '—')} |")
    out += ["", "## Columns by candidate table", ""]
    for t in report["candidate_tables"]:
        out += [f"### `{t['table']}`", "",
                ", ".join(f"`{c['name']}` ({c['type'] or 'unspecified'})" for c in t["columns"]), ""]
    out += ["## Interpretation", "",
            "This catalog identifies possible historical movement and balance sources. A date range or token ID match does not prove that a table has complete wallet history, an opening balance, or acquisition cost. Do not allocate FIFO lots or recognize realized profit from these counts.", "",
            "**Validation:** PASS for read-only schema/count extraction. Inventory and financial acceptance remain UNKNOWN; Checkpoint 96 remains OPEN.", ""]
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    db = args.db.resolve()
    if not db.is_file():
        raise SystemExit(f"STOP: database not found: {db}. Pass --db PATH explicitly.")
    # mode=ro reads the current database and WAL without permitting DB writes.
    uri = db.as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=10)) as conn:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        tables = get_schema(conn)
        accounting = accounting_summary(conn, tables)
    report = {
        "project": "AxieOS", "version": "0.14", "task": "136E",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_schema_and_counts", "database": {"path": str(args.db), "size_bytes": db.stat().st_size},
        "candidate_tables": tables, "accounting_coverage": accounting,
        "accepted_opening_balances": None, "accepted_cost_basis": None, "accepted_realized_profit": None,
        "database_writes": 0, "network_calls": 0, "checkpoint96": "OPEN",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"AxieOS_V014_Task136E_Consumable_Source_Probe_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')}_{uuid4().hex[:6]}"
    json_path = args.output_dir / (stem + ".json")
    md_path = args.output_dir / (stem + ".md")
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render(report), encoding="utf-8")
    print("AXIEOS V0.14 - TASK136E - CONSUMABLE SOURCE PROBE")
    print(f"Candidate tables: {len(tables)} | Opening balances, basis and profit: UNKNOWN")
    print(f"Reports: {json_path} {md_path}")
    print("Database opened: YES (read only) | Database writes: 0 | Network calls: 0")
    print("VALIDATION: PASS (source catalog only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
