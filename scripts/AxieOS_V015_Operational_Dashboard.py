r"""Read-only AxieOS daily, weekly, or monthly operational dashboard.

Copy this file to scripts/AxieOS_V015_Operational_Dashboard.py and run:
    py -B .\scripts\AxieOS_V015_Operational_Dashboard.py --period all

Only observed activity is reported. Financial totals stay UNKNOWN until the
separate Unified Finance acceptance gate is satisfied. No network or DB writes.
"""

import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "blockchain" / "database" / "axieos.db"
DEFAULT_OUTPUT = ROOT / "reports" / "axieos_v015" / "dashboards"
DEFAULT_CATCHUP_DIR = ROOT / "reports" / "axieos_v015" / "source_catchup"
PHT = timezone(timedelta(hours=8))

# Fixed names and columns only: a missing or older table yields a coverage gap.
SOURCES = {
    "bounty": ("gameplay_daily_sessions", "session_date", {"id", "ending_fortune_slips"}),
    "tasks": ("bounty_board_tasks", None, {"daily_session_id", "selected_final", "completed", "reward_bp", "reroll_cost_slips"}),
    "marketplace": ("marketplace_events", "event_datetime", {"event_type"}),
    "owned_axies": ("gameplay_owned_axies", "last_seen_datetime", {"ownership_status"}),
    "consumables": ("inventory_events", "event_datetime", {"item_type", "item_name"}),
    "terrariums": ("terrarium_snapshots", "snapshot_datetime", set()),
    "staking": ("staking_reward_events", "event_datetime", {"token"}),
    "wallet": ("ronin_api_transactions_raw", "timestamp", {"tx_hash"}),
}


def bounds(period, as_of):
    end = as_of + timedelta(days=1)
    if period == "daily":
        start = as_of
    elif period == "weekly":
        start = as_of - timedelta(days=6)
    else:
        start = as_of.replace(day=1)
    return start.isoformat(), end.isoformat()


def read_only(db):
    if not db.is_file():
        raise ValueError(f"Database missing: {db}")
    uri = db.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("PRAGMA query_only=ON")
    return conn


def available(conn, key):
    table, _, required = SOURCES[key]
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
        return False, "TABLE_MISSING"
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    expected = required | ({SOURCES[key][1]} if SOURCES[key][1] else set())
    absent = expected - columns
    return (False, "COLUMNS_MISSING:" + ",".join(sorted(absent))) if absent else (True, "AVAILABLE")


def scalar(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return row[0] if row else None


def event_day(key, column):
    # Explorer raw timestamps carry UTC (Z); AxieOS gameplay dates are stored
    # as local calendar dates or naive datetimes and have no offset to convert.
    return f"date({column}, '+8 hours')" if key == "wallet" else f"substr({column},1,10)"


def period_filter(key, column, start, end):
    day = event_day(key, column)
    return f"{day}>=? AND {day}<?", (start, end)


def mark_state(state, start, as_of):
    latest = state["latest_observation_local_date"]
    state["days_since_latest_observed_event"] = (
        (as_of - date.fromisoformat(latest)).days if latest else None
    )
    if state["period_rows"]:
        state["status"] = "OBSERVED_IN_PERIOD_COVERAGE_UNVERIFIED"
    elif latest is None:
        state["status"] = "NO_OBSERVATIONS_THROUGH_AS_OF"
    elif latest < start:
        state["status"] = "HISTORICAL_ONLY"
    else:
        state["status"] = "NO_ROWS_IN_PERIOD"


def source_state(conn, key, start, end, as_of):
    table, column, _ = SOURCES[key]
    ok, reason = available(conn, key)
    state = {"table": table, "status": reason, "period_rows": None,
             "latest_observation": None, "latest_observation_local_date": None,
             "days_since_latest_observed_event": None}
    if not ok:
        return state
    if column:
        where, params = period_filter(key, column, start, end)
        day = event_day(key, column)
        state["period_rows"] = scalar(conn, f"SELECT count(*) FROM {table} WHERE {where}", params)
        state["latest_observation"] = scalar(conn, f"SELECT max({column}) FROM {table} WHERE {day}<=?", (as_of.isoformat(),))
        state["latest_observation_local_date"] = scalar(conn, f"SELECT max({day}) FROM {table} WHERE {day}<=?", (as_of.isoformat(),))
        mark_state(state, start, as_of)
    else:
        state["status"] = "JOINED_TO_SESSION_DATE_WHEN_AVAILABLE"
    return state


def observed(conn, key, sql, params=()):
    if not available(conn, key)[0]:
        return None
    return scalar(conn, sql, params)


def catchup_snapshot(conn, path, as_of, roster_refresh=None):
    state = {"status": "NO_SNAPSHOT", "filename": None, "sha256": None,
             "block_timestamp_utc": None, "chain_owned_count": None,
             "chain_only_ids": [], "saved_only_ids": [], "transaction_gap_details": [],
             "wallet_routes_complete": None, "roster_refresh": None,
             "metadata_unknown_ids": [], "error": None}
    if path is None:
        return state
    state["filename"] = path.name
    try:
        raw = path.read_bytes()
        state["sha256"] = hashlib.sha256(raw).hexdigest()
        report = json.loads(raw)
        if report.get("task") != "SOURCE_CATCHUP" or report.get("version") != "0.15":
            raise ValueError("source is not a V0.15 catch-up report")
        inv, wallet = report["owned_inventory"], report["wallet_coverage"]
        if inv["status"] != "COMPLETE_AT_PINNED_BLOCK":
            state["status"] = "OWNERSHIP_INCOMPLETE"
            return state
        block_time = datetime.fromisoformat(inv["block_timestamp_utc"].replace("Z", "+00:00"))
        if block_time.tzinfo is None:
            raise ValueError("block timestamp lacks timezone")
        state["block_timestamp_utc"] = block_time.isoformat()
        if block_time.astimezone(PHT).date() != as_of:
            state["status"] = "SNAPSHOT_DATE_DIFFERS"
            return state
        if not available(conn, "owned_axies")[0]:
            raise ValueError("saved Axie table unavailable")
        saved = {str(row[0]) for row in conn.execute(
            "SELECT axie_id FROM gameplay_owned_axies WHERE ownership_status='OWNED' AND axie_id IS NOT NULL")}
        chain_only, saved_only = set(inv["chain_only_ids"]), set(inv["saved_only_ids"])
        pre_apply = (len(saved) == inv["saved_owned_rows"] and saved_only <= saved and
                     not chain_only & saved and
                     len(saved - saved_only) + len(chain_only) == inv["chain_owned_count"])
        post_apply = False
        if roster_refresh is not None and roster_refresh.is_file():
            refresh_bytes = roster_refresh.read_bytes()
            refresh = json.loads(refresh_bytes)
            linked = refresh.get("sources", {}).get("catchup_sha256") == state["sha256"]
            if linked:
                unknown = refresh.get("metadata_unknown_ids")
                if (refresh.get("version") != "0.15" or refresh.get("task") != "GUARDED_ROSTER_REFRESH" or
                        refresh.get("status") != "APPLIED_AND_RECONCILED" or
                        refresh.get("fresh_chain_owned") != inv["chain_owned_count"] or
                        refresh.get("chain_only_inserted") != len(chain_only) or
                        refresh.get("saved_only_to_unknown") != len(saved_only) or
                        refresh.get("roster_after") != refresh.get("roster_before", -100) + len(chain_only) or
                        refresh.get("database_writes") != len(chain_only) + len(saved_only) or
                        refresh.get("finance_writes") != 0 or refresh.get("checkpoint96") != "OPEN" or
                        not isinstance(unknown, list) or len(set(unknown)) != len(unknown) or
                        not set(unknown) <= chain_only or
                        not refresh.get("backup")):
                    raise ValueError("linked roster refresh report is incomplete or inconsistent")
                post_apply = (len(saved) == inv["chain_owned_count"] and chain_only <= saved and
                              not saved_only & saved and
                              len(saved) == refresh.get("owned_after_if_applied"))
                if post_apply:
                    state["roster_refresh"] = {"filename": roster_refresh.name,
                        "sha256": hashlib.sha256(refresh_bytes).hexdigest(),
                        "chain_only_inserted": len(chain_only),
                        "saved_only_to_unknown": len(saved_only)}
                    state["metadata_unknown_ids"] = sorted((str(row[0]) for row in conn.execute(
                        "SELECT axie_id FROM gameplay_owned_axies WHERE axie_id IN (" +
                        ",".join("?" for _ in chain_only) + ") AND "
                        "(axie_class IS NULL OR level IS NULL OR breed_count IS NULL)",
                        tuple(sorted(chain_only)))), key=int)
        if not (pre_apply or post_apply) or sum(inv["wallet_balances"].values()) != inv["chain_owned_count"]:
            raise ValueError("saved roster differs from catch-up and linked refresh")
        state.update(status="POST_APPLY_ROSTER_RECONCILED" if post_apply else "PINNED_CHAIN_SNAPSHOT",
                     chain_owned_count=inv["chain_owned_count"],
                     chain_only_ids=[] if post_apply else sorted(chain_only, key=int),
                     saved_only_ids=[] if post_apply else sorted(saved_only, key=int),
                     wallet_routes_complete=wallet["all_routes_reached_cutoff_or_end"])
        if available(conn, "wallet")[0]:
            known = {str(row[0]).lower() for row in conn.execute(
                "SELECT tx_hash FROM ronin_api_transactions_raw WHERE tx_hash IS NOT NULL")}
            gaps = set(wallet["transaction_hashes_at_or_after_cutoff_absent_from_raw"])
            details = wallet["transaction_gap_details"]
            if {d["txhash"] for d in details} != gaps or len(details) != len(gaps):
                raise ValueError("transaction details do not match source gaps")
            for detail in details:
                if detail["status"] == "CORROBORATED_DETAIL":
                    at = datetime.fromisoformat(detail["timestamp"].replace("Z", "+00:00"))
                    if at.tzinfo is None:
                        raise ValueError("transaction detail timestamp lacks timezone")
            state["transaction_gap_details"] = [d for d in details
                 if wallet["all_routes_reached_cutoff_or_end"] and d["txhash"] not in known
                 and d["status"] == "CORROBORATED_DETAIL"]
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        state.update(status="INVALID_OR_CHANGED_SNAPSHOT", chain_owned_count=None,
                     chain_only_ids=[], saved_only_ids=[], transaction_gap_details=[],
                     roster_refresh=None, metadata_unknown_ids=[],
                     error=f"{type(exc).__name__}: {exc}")
    return state


def latest_catchup(directory):
    if not directory.is_dir():
        return None
    matches = sorted(directory.glob("AxieOS_V015_Source_Catchup_*.json"))
    return matches[-1] if matches else None


def latest_roster_refresh(directory):
    if not directory.is_dir():
        return None
    matches = sorted(directory.glob("AxieOS_V015_Guarded_Roster_Refresh_*.json"))
    for path in reversed(matches):
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("status") == "APPLIED_AND_RECONCILED":
                return path
        except (OSError, ValueError, TypeError):
            continue
    return None


def make_view(conn, period, as_of, catchup=None):
    start, end = bounds(period, as_of)
    p = (start, end)
    states = {key: source_state(conn, key, start, end, as_of) for key in SOURCES}
    metrics = {
        "bounty_sessions": observed(conn, "bounty", "SELECT count(*) FROM gameplay_daily_sessions WHERE session_date>=? AND session_date<?", p),
        "selected_completed_bounty_tasks": None,
        "marketplace_recorded_events": states["marketplace"]["period_rows"],
        "saved_owned_axie_rows": observed(conn, "owned_axies", "SELECT count(*) FROM gameplay_owned_axies WHERE ownership_status='OWNED'"),
        "cocochoco_inventory_event_rows": observed(conn, "consumables", "SELECT count(*) FROM inventory_events WHERE substr(event_datetime,1,10)>=? AND substr(event_datetime,1,10)<? AND (lower(coalesce(item_name,'')) LIKE '%coco%' OR lower(coalesce(item_type,'')) LIKE '%coco%')", p),
        "latest_recorded_ending_fortune_slips": None,
        "terrarium_snapshot_rows": states["terrariums"]["period_rows"],
        "staking_event_rows": states["staking"]["period_rows"],
        "wallet_raw_unique_transaction_hashes": observed(conn, "wallet", "SELECT count(DISTINCT tx_hash) FROM ronin_api_transactions_raw WHERE date(timestamp, '+8 hours')>=? AND date(timestamp, '+8 hours')<?", p),
        "verified_realized_profit": "UNKNOWN",
        "verified_capital_allocation": "UNKNOWN",
    }
    if available(conn, "tasks")[0] and available(conn, "bounty")[0]:
        metrics["selected_completed_bounty_tasks"] = scalar(conn, """SELECT count(*) FROM bounty_board_tasks t JOIN gameplay_daily_sessions s ON s.id=t.daily_session_id WHERE s.session_date>=? AND s.session_date<? AND t.selected_final=1 AND t.completed=1""", p)
        states["tasks"]["period_rows"] = scalar(conn, """SELECT count(*) FROM bounty_board_tasks t JOIN gameplay_daily_sessions s ON s.id=t.daily_session_id WHERE s.session_date>=? AND s.session_date<?""", p)
        states["tasks"]["latest_observation"] = scalar(conn, """SELECT max(s.session_date) FROM bounty_board_tasks t JOIN gameplay_daily_sessions s ON s.id=t.daily_session_id WHERE s.session_date<=?""", (as_of.isoformat(),))
        states["tasks"]["latest_observation_local_date"] = states["tasks"]["latest_observation"]
        mark_state(states["tasks"], start, as_of)
    if available(conn, "bounty")[0]:
        metrics["latest_recorded_ending_fortune_slips"] = observed(conn, "bounty", "SELECT ending_fortune_slips FROM gameplay_daily_sessions WHERE session_date>=? AND session_date<? AND ending_fortune_slips IS NOT NULL ORDER BY session_date DESC,id DESC LIMIT 1", p)
    if catchup and catchup["status"] in ("PINNED_CHAIN_SNAPSHOT", "POST_APPLY_ROSTER_RECONCILED"):
        metrics["chain_owned_axies_at_pinned_block"] = catchup["chain_owned_count"]
        metrics["chain_only_axie_ids_for_review"] = len(catchup["chain_only_ids"])
        metrics["saved_only_axie_ids_for_review"] = len(catchup["saved_only_ids"])
        if catchup["status"] == "POST_APPLY_ROSTER_RECONCILED":
            metrics["axies_with_unknown_class_level_breed"] = len(catchup["metadata_unknown_ids"])
        metrics["corroborated_explorer_transactions_missing_raw"] = sum(
            start <= datetime.fromisoformat(d["timestamp"]).astimezone(PHT).date().isoformat() < end
            for d in catchup["transaction_gap_details"])
    return {"period": period, "start_date_inclusive": start, "end_date_exclusive": end, "source_coverage": states, "observations": metrics,
            "interpretation": "Counts are observed rows, not proof of no activity when zero or proof of complete source coverage when positive. Saved owned Axie rows reflect the database at report time; pinned chain ownership is a dated snapshot. The roster refresh is recognized only when its linked applied report and current statuses agree. Explorer transaction gaps are separate from raw counts and must not be added to financial events. CocoChoco event count is not stock on hand; ending slips is one latest observation. Raw wallet UTC timestamps are grouped into Philippines calendar days (+08:00); gameplay timestamps are source-local or timezone unspecified."}


def markdown(report):
    lines = ["# AxieOS V0.15 operational dashboard", "", f"Generated UTC: {report['generated_utc']}", "Calendar: Philippines (+08:00); raw wallet UTC timestamps converted for day buckets.", "", "Financial totals: **UNKNOWN**. Unified Finance: **HOLD**. Checkpoint 96: **OPEN**.", ""]
    snap = report["catchup_source"]
    lines += [f"Catch-up source: **{snap['status']}** | {snap['filename'] or 'none'} | SHA-256: {snap['sha256'] or 'n/a'}", ""]
    for view in report["views"]:
        lines += [f"## {view['period'].title()} ({view['start_date_inclusive']} to {view['end_date_exclusive']} exclusive)", "", "| Observation | Value |", "| --- | ---: |"]
        for name, value in view["observations"].items():
            lines.append(f"| {name.replace('_', ' ')} | {value if value is not None else 'UNKNOWN'} |")
        lines += ["", "| Source | Status | Period rows | Latest recorded event | Local date | Age (days) |", "| --- | --- | ---: | --- | --- | ---: |"]
        for name, state in view["source_coverage"].items():
            lines.append(f"| {name} | {state['status']} | {state['period_rows'] if state['period_rows'] is not None else 'UNKNOWN'} | {state['latest_observation'] or 'UNKNOWN'} | {state['latest_observation_local_date'] or 'UNKNOWN'} | {state['days_since_latest_observed_event'] if state['days_since_latest_observed_event'] is not None else 'UNKNOWN'} |")
        lines += ["", view["interpretation"], ""]
    lines += ["No production database writes or network calls. The JSON contains the same observations and source status.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(PHT).date())
    parser.add_argument("--period", choices=("daily", "weekly", "monthly", "all"), default="all")
    parser.add_argument("--catchup", type=Path, help="Exact V0.15 source catch-up JSON; defaults to latest local report")
    parser.add_argument("--catchup-dir", type=Path, default=DEFAULT_CATCHUP_DIR)
    parser.add_argument("--roster-refresh", type=Path,
                        help="Exact applied V0.15 guarded roster refresh JSON; defaults to latest local report")
    args = parser.parse_args()
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(read_only(args.db)) as conn:
        snapshot = catchup_snapshot(conn, args.catchup or latest_catchup(args.catchup_dir),
                                    args.as_of, args.roster_refresh or latest_roster_refresh(args.catchup_dir))
        views = [make_view(conn, p, args.as_of, snapshot) for p in (("daily", "weekly", "monthly") if args.period == "all" else (args.period,))]
    report = {"version": "0.15", "generated_utc": generated, "as_of_philippines_date": args.as_of.isoformat(), "calendar_timezone": "Asia/Manila (+08:00)", "views": views,
              "catchup_source": snapshot, "verified_financial_totals": "UNKNOWN", "unified_finance": "HOLD", "checkpoint96": "OPEN", "database_opened": "READ_ONLY", "database_writes": 0, "network_calls": 0}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    basename = f"AxieOS_V015_Operational_Dashboard_{args.as_of.isoformat()}_{args.period}"
    (args.output_dir / (basename + ".json")).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / (basename + ".md")).write_text(markdown(report), encoding="utf-8")
    print(f"AXIEOS V0.15 - OPERATIONAL DASHBOARD | {args.period.upper()} | as of {args.as_of}")
    print(f"Reports: {args.output_dir / (basename + '.json')} {args.output_dir / (basename + '.md')}")
    print(f"Catch-up source: {snapshot['status']} | Pinned chain Axies: {snapshot['chain_owned_count'] if snapshot['chain_owned_count'] is not None else 'UNKNOWN'}")
    print("Financial totals: UNKNOWN | Database: read only | Writes: 0 | Network: 0")


if __name__ == "__main__":
    main()
