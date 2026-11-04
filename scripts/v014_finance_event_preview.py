"""AxieOS V0.14 Task 136B: offline evidence-indexed finance event preview.

Run from the repository root. Reads the five Checkpoint 96 offline JSON reports,
never the database or network. The output is a historical review view, not
accepted income, expenses, realized profit, or capital recovery.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


SOURCES = {
    "capital": ("96BR", "included_contributions", "capital_flow.json"),
    "rewards": ("96CB", "reward_evidence_records", "reward_income.json"),
    "sales": ("96CD", "sale_evidence_reviews", "marketplace_proceeds.json"),
    "purchases": ("96CF", "purchase_evidence_reviews", "purchase_outlays.json"),
    "gas": ("96CL", "raw_fee_evidence_rows", "gas_evidence.json"),
}
EXPECTED_COUNTS = {
    "included_contributions": 108,
    "historical_reported_cash_receipts": 4,
    "reward_evidence_records": 18,
    "staking_movements_excluded_from_income": 16,
    "sale_evidence_reviews": 75,
    "purchase_evidence_reviews": 53,
    "raw_fee_evidence_rows": 227,
    "missing_raw_hashes_preserved": 178,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("STOP: " + message)


def load_source(path: Path, checkpoint: str, collection: str) -> tuple[dict, dict]:
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    require(isinstance(data, dict), f"{path.name}: expected JSON object")
    require(data.get("checkpoint") == checkpoint, f"{path.name}: wrong checkpoint")
    require(isinstance(data.get(collection), list), f"{path.name}: missing {collection}")
    validation = data.get("validation", {})
    require(str(validation.get("status", "")).startswith("PASS_"),
            f"{path.name}: source validation status changed")
    require(validation.get("database_writes") == 0, f"{path.name}: database writes")
    require(validation.get("network_calls") == 0, f"{path.name}: network calls")
    require(validation.get("checkpoint96_closed") is False, f"{path.name}: scope changed")
    require(
        validation.get("database_opened", validation.get("production_database_opened")) is False,
        f"{path.name}: database-open status changed",
    )
    for key, value in data.get("unknown_metrics", {}).items():
        require(value is None, f"{path.name}: unknown metric {key} was filled")
    return data, {"filename": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
                  "checkpoint": checkpoint}


def find_source(directory: Path, lane: str) -> Path:
    checkpoint, collection, alias = SOURCES[lane]
    require(directory.is_dir(), f"input directory does not exist: {directory}")
    candidates = [
        path for path in directory.rglob("*.json")
        if checkpoint.lower() in path.as_posix().lower()
        or path.name.lower() == alias.lower()
    ]
    matches = []
    for path in sorted(set(candidates)):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("checkpoint") == checkpoint and collection in data:
            matches.append(path)
    require(len(matches) == 1,
            f"{lane}: expected one {checkpoint} offline report in {directory}; "
            f"found {[p.name for p in matches]}. Pass --{lane} PATH explicitly.")
    return matches[0]


def unique_values(rows: list, key: str, label: str) -> set:
    values = [row[key] for row in rows]
    require(all(v not in (None, "") for v in values), f"{label}: empty {key}")
    require(len(values) == len(set(values)), f"{label}: duplicate {key}")
    return set(values)


def accounting_rows(rows: list, field: str, label: str) -> tuple[set, set]:
    preserved = [r[field] for r in rows]
    keys = unique_values(preserved, "accounting_key", label)
    hashes = unique_values(preserved, "txhash", label)
    return keys, hashes


def base_event(lane: str, source_id: str, source: dict) -> dict:
    return {
        "event_id": f"{lane}:{source_id}",
        "lane": lane,
        "source_row_id": source_id,
        "source_checkpoint": source["checkpoint"],
        "source_sha256": source["sha256"],
        "accounting_key": None,
        "txhash": None,
        "date_as_stored": None,
        "classification_as_stored": None,
        "asset": None,
        "quantity_as_stored": None,
        "payment_gross_as_stored": None,
        "marketplace_fee_as_stored": None,
        "payment_net_as_stored": None,
        "source_status": None,
        "evidence_status": None,
        "receipt_verified": False,
        "accepted_cost_basis": None,
        "accepted_realized_profit": None,
        "accepted_php_value": None,
        "gas_evidence": None,
    }


def build_preview(data: dict, sources: dict) -> dict:
    capital, rewards, sales, purchases, gas = (
        data[k] for k in ("capital", "rewards", "sales", "purchases", "gas")
    )
    for key, count in EXPECTED_COUNTS.items():
        owner = next(d for d in data.values() if key in d)
        require(len(owner[key]) == count, f"{key}: expected {count}, got {len(owner[key])}")
    for key in ("complete_all_time_external_capital_php",
                "current_all_time_unrecovered_principal_php", "complete_recovery_percentage",
                "all_time_realized_profit_php", "live_portfolio_value_php"):
        require(capital["summary"][key] is None, f"capital: {key} unexpectedly filled")

    contribution_ids = unique_values(capital["included_contributions"], "record_id", "capital")
    excluded_ids = unique_values(capital["excluded_other_game_funding"], "record_id", "excluded")
    receipt_ids = unique_values(capital["historical_reported_cash_receipts"], "record_id", "cash")
    require(not (contribution_ids & excluded_ids), "included/excluded capital overlap")
    require(not (contribution_ids & receipt_ids), "capital/cash ID overlap")

    accounting = {
        "rewards": accounting_rows(rewards["reward_evidence_records"], "source_accounting_row", "rewards"),
        "sales": accounting_rows(sales["sale_evidence_reviews"], "accounting_row_preserved", "sales"),
        "purchases": accounting_rows(purchases["purchase_evidence_reviews"], "accounting_row_preserved", "purchases"),
    }
    lanes = list(accounting)
    for i, a in enumerate(lanes):
        for b in lanes[i + 1:]:
            require(not (accounting[a][0] & accounting[b][0]), f"{a}/{b}: accounting key overlap")
            require(not (accounting[a][1] & accounting[b][1]), f"{a}/{b}: txhash overlap")
    require(sales["coverage"]["economic_rows_added_as_sales"] == 0, "economic sales doubled")
    require(purchases["coverage"]["economic_rows_added_as_purchases"] == 0,
            "economic purchases doubled")

    raw_rows = gas["raw_fee_evidence_rows"]
    raw_hashes = unique_values(raw_rows, "txhash", "raw gas")
    missing_hashes = set(gas["missing_raw_hashes_preserved"])
    require(len(missing_hashes) == 178, "duplicate missing gas hashes")
    require(not raw_hashes & missing_hashes, "raw and missing gas overlap")
    require(len(raw_hashes | missing_hashes) == gas["coverage"]["accounting_hashes"] == 405,
            "gas accounting-hash partition mismatch")
    require(all(r["user_paid_fee_verified_by_receipt"] is False for r in raw_rows),
            "gas receipt verification changed")
    raw_by_hash = {r["txhash"]: r for r in raw_rows}

    events = []
    for r in capital["included_contributions"]:
        e = base_event("EXTERNAL_CAPITAL", r["record_id"], sources["capital"])
        e.update(date_as_stored=r.get("date_time"), classification_as_stored=r["category"],
                 asset="PHP", quantity_as_stored=r["amount_php"],
                 evidence_status="PROVISIONAL_IDENTIFIED_CAPITAL")
        events.append(e)
    for r in capital["historical_reported_cash_receipts"]:
        require(r["net_permanent_extraction_verified"] is False,
                "cash extraction verification changed")
        e = base_event("REPORTED_CASH_RECEIPT", r["record_id"], sources["capital"])
        e.update(date_as_stored=r.get("date_time"), classification_as_stored=r["category"],
                 asset="PHP", quantity_as_stored=r["amount_php"],
                 evidence_status="USER_ATTESTED_NOT_BANK_MATCHED")
        events.append(e)
    for r in rewards["reward_evidence_records"]:
        row, resolved = r["source_accounting_row"], r["resolver_output"]
        key = row["accounting_key"]
        require(resolved["accounting_key"] == key, "reward resolver key mismatch")
        e = base_event("TOKEN_REWARD", key, sources["rewards"])
        e.update(accounting_key=key, txhash=row["txhash"],
                 date_as_stored=row.get("datetime"),
                 classification_as_stored=resolved["economic_source"],
                 asset=resolved["token"], quantity_as_stored=resolved["quantity"],
                 source_status=row["accounting_status"],
                 evidence_status="RESOLVER_" + resolved["confidence"])
        events.append(e)
    for r in sales["sale_evidence_reviews"]:
        row = r["accounting_row_preserved"]
        require(r["accepted_cost_basis"] is None and r["accepted_realized_profit"] is None,
                "accepted sale economics changed")
        require(r["gross_minus_fee_equals_net"] is True, "sale arithmetic flag failed")
        e = base_event("MARKETPLACE_SALE", row["accounting_key"], sources["sales"])
        e.update(accounting_key=row["accounting_key"], txhash=row["txhash"],
                 date_as_stored=row.get("datetime"),
                 classification_as_stored=row["classification"],
                 asset=row["payment_asset"], quantity_as_stored=row["quantity"],
                 payment_gross_as_stored=row["gross_amount"],
                 marketplace_fee_as_stored=row["marketplace_fee"],
                 payment_net_as_stored=row["net_amount"],
                 source_status=row["accounting_status"],
                 evidence_status="STORED_ARITHMETIC_ONLY")
        events.append(e)
    for r in purchases["purchase_evidence_reviews"]:
        row = r["accounting_row_preserved"]
        require(r["approved_cost_basis"] is None, "accepted purchase basis changed")
        e = base_event("MARKETPLACE_PURCHASE", row["accounting_key"], sources["purchases"])
        e.update(accounting_key=row["accounting_key"], txhash=row["txhash"],
                 date_as_stored=row.get("datetime"),
                 classification_as_stored=row["classification"],
                 asset=row["payment_asset"], quantity_as_stored=row["quantity"],
                 payment_gross_as_stored=row["gross_amount"],
                 source_status=row["accounting_status"],
                 evidence_status="STORED_OUTLAY_ONLY")
        events.append(e)

    for e in events:
        h = e["txhash"]
        if h in raw_by_hash:
            r = raw_by_hash[h]
            e["gas_evidence"] = {"status": "RAW_CANDIDATE", "fee_raw": r["fee_raw_preserved"],
                                 "unit": None, "user_paid": None}
        elif h in missing_hashes:
            e["gas_evidence"] = {"status": "RAW_MISSING", "fee_raw": None,
                                 "unit": None, "user_paid": None}

    require(len(events) == 258, "normalized event count mismatch")
    unique_values(events, "event_id", "normalized events")
    require(all(e["accepted_cost_basis"] is None and e["accepted_realized_profit"] is None
                for e in events), "profit or cost basis populated")
    require(all(e["accepted_php_value"] is None for e in events),
            "accepted PHP value populated")
    sale_hashes = accounting["sales"][1]
    purchase_hashes = accounting["purchases"][1]
    require(len(sale_hashes & missing_hashes) == 75, "sale gas gap changed")
    require(len(purchase_hashes & raw_hashes) == 48 and
            len(purchase_hashes & missing_hashes) == 5, "purchase gas coverage changed")
    return {
        "project": "AxieOS V0.14", "task": "136B", "schema_version": "0.1",
        "scope": "Historical source preview; no accepted combined finance totals",
        "sources": sources,
        "coverage": {"external_capital": 108, "reported_cash_receipts": 4,
                     "token_rewards": 18, "marketplace_sales": 75,
                     "marketplace_purchases": 53, "preview_events": 258,
                     "staking_movements_excluded": 16,
                     "other_game_funding_excluded": len(excluded_ids),
                     "gas_raw_rows": 227, "gas_missing_hashes": 178,
                     "sale_hashes_with_raw_gas": 0,
                     "purchase_hashes_with_raw_gas": 48},
        "unknown_metrics": {"verified_income_php": None, "verified_expenses_php": None,
                            "realized_profit_php": None, "complete_gas_ron": None,
                            "current_unrecovered_principal_php": None},
        "events": events,
        "validation": {"status": "PASS_OFFLINE_PREVIEW_ONLY", "database_opened": False,
                       "database_writes": 0, "network_calls": 0,
                       "checkpoint96_closed": False},
    }


def markdown(preview: dict, json_name: str) -> str:
    c = preview["coverage"]
    lines = [
        "# AxieOS V0.14 - Task 136B finance event preview", "",
        "Historical evidence-indexed view; no accepted combined financial total.", "",
        "| Lane | Preview rows |", "|---|---:|",
        f"| External capital | {c['external_capital']} |",
        f"| Reported PHP cash receipts | {c['reported_cash_receipts']} |",
        f"| Token rewards | {c['token_rewards']} |",
        f"| Marketplace sales | {c['marketplace_sales']} |",
        f"| Marketplace purchases | {c['marketplace_purchases']} |",
        f"| **Total distinct preview records** | **{c['preview_events']}** |", "",
        f"Excluded: {c['staking_movements_excluded']} staking movements and "
        f"{c['other_game_funding_excluded']} other-game funding records.", "",
        f"Gas evidence: {c['gas_raw_rows']} raw rows and "
        f"{c['gas_missing_hashes']} missing accounting hashes. "
        f"Raw fee rows cover {c['sale_hashes_with_raw_gas']}/75 sale hashes "
        f"and {c['purchase_hashes_with_raw_gas']}/53 purchase hashes. "
        "Fee units and user payment remain unverified.", "",
        "Verified PHP income, expenses, realized profit, all-time gas and "
        "unrecovered principal: **UNKNOWN**.", "",
        "Accounting comparison rows are annotations, not additional events. "
        "READY/REVIEW are preserved source statuses, not receipt verification. "
        "Stored marketplace fees are already part of sale net arithmetic.", "",
        "Source file hashes and all row-level evidence links are in " + json_name + ".", "",
        "Database opened: NO | Writes: 0 | Network calls: 0", "",
        "VALIDATION: PASS (offline preview only; Checkpoint 96 OPEN).", "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path,
                        default=Path("reports/axieos_v013/checkpoint96"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("reports/axieos_v014/task136b"))
    for lane in SOURCES:
        parser.add_argument(f"--{lane}", type=Path, help=f"Explicit {lane} JSON report")
    args = parser.parse_args()
    data, sources = {}, {}
    for lane, (checkpoint, collection, _) in SOURCES.items():
        path = getattr(args, lane) or find_source(args.input_dir, lane)
        data[lane], sources[lane] = load_source(path, checkpoint, collection)
    preview = build_preview(data, sources)
    preview["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V014_Task136B_Event_Preview_" + datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S_%fZ") + "_" + uuid.uuid4().hex[:6]
    json_path = args.output_dir / (stem + ".json")
    md_path = args.output_dir / (stem + ".md")
    with json_path.open("x", encoding="utf-8") as out:
        json.dump(preview, out, ensure_ascii=False, indent=2)
        out.write("\n")
    with md_path.open("x", encoding="utf-8") as out:
        out.write(markdown(preview, json_path.name))
    print("AXIEOS V0.14 - TASK136B - OFFLINE FINANCE EVENT PREVIEW")
    print("Preview records: 258 | sale/purchase/reward accounting rows: 75/53/18")
    print("Raw gas rows: 227 | missing hashes: 178")
    print("Verified income, expenses, profit and recovery: UNKNOWN")
    print("New reports:", json_path, md_path)
    print("Database opened: NO | Writes: 0 | Network calls: 0")
    print("VALIDATION: PASS (offline preview only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
