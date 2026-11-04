r"""Task136R: build an offline, non-additive finance source registry.

Run from AxieOS root:
    py -B .\scripts\v014_unified_finance_registry.py

The registry indexes existing preview/accounting rows once and attaches
gameplay source coverage. It does not accept financial totals, open the
database, access the network, or change any source report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


PREVIEW_LANES = {"EXTERNAL_CAPITAL": 108, "REPORTED_CASH_RECEIPT": 4,
                 "TOKEN_REWARD": 18, "MARKETPLACE_SALE": 75,
                 "MARKETPLACE_PURCHASE": 53}
ACCOUNTING_CLASSES = {"MINT_OR_CLAIM", "MARKETPLACE_SALE", "MARKETPLACE_BUY",
                      "TOKEN_BURN", "NFT_BURN", "TRANSFER_IN", "TRANSFER_OUT", "STAKING_OR_REWARD",
                      "TOKEN_SWAP", "UNKNOWN"}
GAMEPLAY_TABLES = {"marketplace_events": 49, "marketplace_event_bounty_tasks": 34,
                   "bounty_board_tasks": 119, "weekly_bounty_results": 2,
                   "terrarium_snapshots": 17, "terrarium_plot_snapshots": 51,
                   "staking_reward_events": 10, "inventory_events": 21,
                   "pouch_opening_events": 5, "pouch_reward_items": 6}


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError("STOP: " + reason)


def source(explicit: Path | None, directory: Path, task: str) -> tuple[Path, dict, str]:
    paths = [explicit] if explicit else list(directory.glob("*.json")) if directory.is_dir() else []
    matches = []
    for path in paths:
        if path is None or not path.is_file():
            continue
        raw = path.read_bytes()
        try:
            data = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and (data.get("task") == task or
                                       (task == "96BV" and data.get("checkpoint") == "96BV")):
            matches.append((path, data, hashlib.sha256(raw).hexdigest()))
    require(len(matches) == 1, f"{task}: expected one JSON in {directory}, found {[str(p) for p, _, _ in matches]}; use an explicit --{task.lower()} path")
    return matches[0]


def build(preview: dict, bv: dict, gameplay: dict, provenance: dict) -> dict:
    require(preview.get("task") == "136B" and preview.get("schema_version") == "0.1", "wrong preview")
    v = preview.get("validation", {})
    require(v.get("status") == "PASS_OFFLINE_PREVIEW_ONLY" and v.get("database_opened") is False
            and v.get("database_writes") == 0 and v.get("network_calls") == 0
            and v.get("checkpoint96_closed") is False, "preview validation changed")
    events = preview.get("events")
    require(isinstance(events, list) and len(events) == 258, "preview must have 258 rows")
    require(Counter(e.get("lane") for e in events) == PREVIEW_LANES, "preview lane counts changed")
    ids = [e.get("event_id") for e in events]
    require(all(ids) and len(set(ids)) == len(ids), "preview duplicate event ID")
    require(all(e.get("accepted_cost_basis") is None and e.get("accepted_realized_profit") is None
                and e.get("accepted_php_value") is None and e.get("receipt_verified") is False
                for e in events), "preview acceptance fields changed")

    require(bv.get("task") == "135H" and bv.get("checkpoint") == "96BV", "wrong Checkpoint96BV")
    tables = bv.get("tables", {})
    accounting = tables.get("blockchain_accounting_records", {}).get("rows")
    economic = tables.get("blockchain_economic_events", {}).get("rows")
    staking = tables.get("staking_reward_events", {}).get("rows")
    require(isinstance(accounting, list) and len(accounting) == 405, "accounting coverage changed")
    require(isinstance(economic, list) and len(economic) == 128, "economic comparison changed")
    require(isinstance(staking, list) and len(staking) == 10, "staking source changed")
    require(len({r.get("accounting_key") for r in accounting}) == 405
            and len({r.get("txhash") for r in accounting}) == 405
            and all(r.get("accounting_key") and r.get("txhash") for r in accounting), "accounting keys/hashes invalid")
    require(set(r.get("classification") for r in accounting) <= ACCOUNTING_CLASSES, "new accounting classification needs review")
    acc_by_key = {r["accounting_key"]: r for r in accounting}
    acc_by_hash = {r["txhash"].lower(): r for r in accounting}
    economic_hashes = [r.get("txhash") for r in economic]
    require(len(set(economic_hashes)) == 128 and all(h and h.lower() in acc_by_hash for h in economic_hashes),
            "economic rows not fully mapped to accounting")
    require(all(acc_by_hash[r["txhash"].lower()]["classification"] in ("MARKETPLACE_SALE", "MARKETPLACE_BUY")
                for r in economic), "economic comparison includes unexpected event")

    require(gameplay.get("task") == "136N", "wrong gameplay extract")
    g = gameplay.get("tables", {})
    require({k: v.get("row_count") for k, v in g.items()} == GAMEPLAY_TABLES, "gameplay table counts changed")
    require(all(len(v.get("rows", [])) == GAMEPLAY_TABLES[k] for k, v in g.items()), "gameplay rows changed")
    require(g["staking_reward_events"]["rows"] == staking, "staking duplicated source differs")

    attached_keys = []
    registry = []
    for e in events:
        key = e.get("accounting_key")
        if key is not None:
            require(key in acc_by_key and e.get("txhash") == acc_by_key[key]["txhash"],
                    "preview accounting crosswalk differs")
            expected = {"TOKEN_REWARD": "STAKING_OR_REWARD", "MARKETPLACE_SALE": "MARKETPLACE_SALE",
                        "MARKETPLACE_PURCHASE": "MARKETPLACE_BUY"}.get(e["lane"])
            require(expected == acc_by_key[key]["classification"], "preview accounting lane differs")
            attached_keys.append(key)
        registry.append({"registry_id": e["event_id"], "origin": "TASK136B_PREVIEW",
                         "lane": e["lane"], "accounting_key": key, "txhash": e.get("txhash"),
                         "date_as_stored": e.get("date_as_stored"), "asset_as_stored": e.get("asset"),
                         "quantity_as_stored": e.get("quantity_as_stored"),
                         "gross_as_stored": e.get("payment_gross_as_stored"),
                         "source_status": e.get("source_status"),
                         "evidence_status": e.get("evidence_status"),
                         "accepted_financial_value": None})
    require(len(attached_keys) == 146 and len(set(attached_keys)) == 146, "preview accounting attachment changed")
    preview_keys = set(attached_keys)
    remaining = [r for r in accounting if r["accounting_key"] not in preview_keys]
    require(len(remaining) == 259, "remaining accounting count changed")
    for r in remaining:
        registry.append({"registry_id": "ACCOUNTING_REVIEW:" + r["accounting_key"],
                         "origin": "CHECKPOINT96BV_ACCOUNTING_ONLY",
                         "lane": r["classification"], "accounting_key": r["accounting_key"],
                         "txhash": r["txhash"], "date_as_stored": r["datetime"],
                         "asset_as_stored": r["asset_name"],
                         "quantity_as_stored": r["quantity"],
                         "gross_as_stored": r["gross_amount"],
                         "source_status": r["accounting_status"],
                         "evidence_status": "UNCLASSIFIED_FINANCE_TREATMENT",
                         "accepted_financial_value": None})
    require(len(registry) == 517 and len({r["registry_id"] for r in registry}) == 517,
            "registry rows duplicate")
    require(len({r["accounting_key"] for r in registry if r["accounting_key"]}) == 405,
            "accounting rows duplicated")

    return {"project": "AxieOS", "version": "0.14", "task": "136R",
            "scope": "Non-additive evidence reference registry; not accepted economic events or totals",
            "sources": provenance,
            "coverage": {"registry_references": 517, "existing_preview_references": 258,
                         "accounting_only_references_added": 259,
                         "unique_accounting_keys": 405,
                         "economic_comparison_rows_not_added": 128,
                         "staking_gameplay_rows_not_added": 10,
                         "manual_marketplace_rows_not_added": 49,
                         "other_gameplay_rows_not_added": sum(GAMEPLAY_TABLES.values()) - 49 - 10,
                         "preview_lanes": dict(PREVIEW_LANES),
                         "unclassified_accounting_classes": dict(sorted(Counter(
                             r["classification"] for r in remaining).items())),
                         "gameplay_source_counts": GAMEPLAY_TABLES},
            "source_areas": {
                "marketplace": "preview sale/purchase; manual rows context only",
                "bounty_board": "preview resolved reward; tasks and weekly result context only",
                "terrariums": "preview resolved reward; snapshots not extra receipts",
                "staking": "unresolved accounting principal/reward movements indexed separately",
                "token_swaps": "accounting swap rows indexed, financial treatment unresolved",
                "consumables": "accounting mint/burn and marketplace movements indexed; opening basis unresolved",
                "axie_releases": "manual release observations indexed as source coverage only",
                "gas": "preview gas candidates remain attachments; raw fees not additional events",
                "internal_transfers": "remaining accounting transfer rows indexed; economic treatment unresolved"},
            "registry_rows": registry,
            "accepted_totals": {"income_php": None, "expenses_php": None,
                                "realized_profit_php": None, "capital_recovery_php": None,
                                "portfolio_value_php": None},
            "validation": {"status": "PASS_OFFLINE_REGISTRY_ONLY", "database_opened": False,
                           "database_writes": 0, "network_calls": 0, "checkpoint96_closed": False}}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136R Unified finance source registry", "",
             "**Status:** Offline, non-additive source registry. Financial values remain UNKNOWN; Checkpoint 96 OPEN.", "",
             f"The registry contains **{c['registry_references']} source references**: "
             f"{c['existing_preview_references']} existing preview entries plus "
             f"{c['accounting_only_references_added']} previously unrepresented accounting rows. "
             "A registry reference is not an accepted income or expense event.", "",
             "| Remaining accounting class | References |", "|---|---:|"]
    for kind, count in c["unclassified_accounting_classes"].items():
        lines.append(f"| {kind} | {count} |")
    lines += ["", "Economic comparison rows (128) and duplicated gameplay staking rows (10) were **not** added as new entries. "
              "The 49 manual marketplace rows and other gameplay observations remain separate source context.", "",
              "| Roadmap area | Registry treatment |", "|---|---|"]
    for area, treatment in report["source_areas"].items():
        lines.append(f"| {area.replace('_', ' ').title()} | {treatment} |")
    lines += ["", "This is a coverage foundation, not the finished V0.14 Unified Finance layer: "
              "receipt attribution, swaps, release costs, consumable basis, complete payer-verified gas, "
              "PHP valuation and current portfolio value still require review.", "",
              "Verified income, expenses, realized profit and recovery: **UNKNOWN**.", "",
              "Database opened: NO | Writes: 0 | Network calls: 0", "",
              "VALIDATION: PASS (offline registry only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path, help="Task136B JSON")
    parser.add_argument("--bv", type=Path, help="Checkpoint96BV JSON")
    parser.add_argument("--gameplay", type=Path, help="Task136N JSON")
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("reports/axieos_v013/checkpoint96"))
    parser.add_argument("--report-root", type=Path, default=Path("reports/axieos_v014"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136r"))
    args = parser.parse_args()
    p = source(args.preview, args.report_root / "task136b", "136B")
    b = source(args.bv, args.checkpoint_dir, "96BV")
    g = source(args.gameplay, args.report_root / "task136n", "136N")
    provenance = {task: {"filename": item[0].name, "sha256": item[2]}
                  for task, item in (("136B", p), ("96BV", b), ("136N", g))}
    report = build(p[1], b[1], g[1], provenance)
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136R_Unified_Finance_Registry_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as out:
        json.dump(report, out, ensure_ascii=False, indent=2)
        out.write("\n")
    with mp.open("x", encoding="utf-8") as out:
        out.write(markdown(report))
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136R - UNIFIED FINANCE SOURCE REGISTRY")
    print(f"Registry references: {c['registry_references']} | Existing preview: "
          f"{c['existing_preview_references']} | Accounting-only: {c['accounting_only_references_added']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network calls: 0")
    print("VALIDATION: PASS (offline registry only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
