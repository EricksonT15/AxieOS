r"""Task136H: summarize source coverage and blocked finance gates, offline.

From the AxieOS repository root:
    py -B .\scripts\v014_finance_readiness.py

Reads one Task136B preview and one Checkpoint96CD sale report. It never opens
the database or network, and produces no income, expense, profit or PHP totals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError("STOP: " + message)


def find_one(root: Path, predicate, label: str) -> Path:
    require(root.is_dir(), f"{label}: directory missing: {root}")
    found = []
    for path in root.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and predicate(data):
            found.append(path)
    require(len(found) == 1, f"{label}: expected one report, found {[p.name for p in found]}; pass its path explicitly")
    return found[0]


def load(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def build(preview: dict, sale: dict, sale_hash: str) -> dict:
    require(preview.get("task") == "136B" and preview.get("schema_version") == "0.1", "unexpected preview version")
    require(preview.get("validation", {}).get("status") == "PASS_OFFLINE_PREVIEW_ONLY", "preview validation")
    require(sale.get("checkpoint") == "96CD", "unexpected sale source")
    require(preview["sources"]["sales"]["sha256"] == sale_hash, "sale report hash differs from preview input")
    events = preview["events"]
    require(len(events) == 258 and len({e["event_id"] for e in events}) == 258, "preview event cardinality")
    require(all(e.get("accepted_cost_basis") is None and e.get("accepted_realized_profit") is None
                and e.get("accepted_php_value") is None for e in events), "finance fields unexpectedly accepted")
    require(all(e.get("receipt_verified") is False for e in events), "receipt verification status changed")
    lane_counts = Counter(e["lane"] for e in events)
    require(lane_counts == {"EXTERNAL_CAPITAL":108,"REPORTED_CASH_RECEIPT":4,"TOKEN_REWARD":18,
                            "MARKETPLACE_SALE":75,"MARKETPLACE_PURCHASE":53}, "lane counts changed")
    sale_events = {e["txhash"]: e for e in events if e["lane"] == "MARKETPLACE_SALE"}
    conflicts = sale["cost_basis_profit_conflicts_preserved"]
    require(len(conflicts) == 24 and len({r["txhash"] for r in conflicts}) == 24, "sale conflicts changed")
    require(all(r["txhash"] in sale_events for r in conflicts), "conflict hash missing from preview")
    buckets = Counter()
    by_status = Counter()
    missing_dates = Counter()
    for e in events:
        date = e.get("date_as_stored")
        month = str(date)[:7] if date and len(str(date)) >= 7 and str(date)[4] == "-" else "UNKNOWN_DATE"
        buckets[(month, e["lane"])] += 1
        by_status[(e["lane"], str(e.get("source_status") or "UNSPECIFIED"), e["evidence_status"])] += 1
        if month == "UNKNOWN_DATE":
            missing_dates[e["lane"]] += 1
    gas = Counter(e["gas_evidence"]["status"] for e in events if e.get("gas_evidence"))
    return {
        "project":"AxieOS", "version":"0.14", "task":"136H",
        "mode":"offline_coverage_and_acceptance_gate_only",
        "coverage":{"preview_events":len(events), "lanes":dict(sorted(lane_counts.items())),
                    "unknown_date_rows":dict(sorted(missing_dates.items())),
                    "monthly_counts":[{"month":month,"lane":lane,"rows":n} for (month,lane),n in sorted(buckets.items())],
                    "status_counts":[{"lane":lane,"stored_status":status,"evidence_status":evidence,"rows":n}
                                     for (lane,status,evidence),n in sorted(by_status.items())],
                    "sale_cost_profit_conflict_hashes":sorted(r["txhash"] for r in conflicts),
                    "event_linked_gas_evidence_statuses":dict(sorted(gas.items()))},
        "acceptance_gates":{
            "verified_income":"OPEN: reward receipt, scope and valuation incomplete",
            "verified_expenses":"OPEN: gas payer/unit, gameplay costs and coverage incomplete",
            "approved_purchase_basis":"OPEN: asset acquisition allocation and fees incomplete",
            "realized_profit":"OPEN: 24 consumable sale basis conflicts and broader lot coverage unresolved",
            "php_capital_recovery":"OPEN: funding history and permanent cash extraction not fully verified",
        },
        "accepted_totals":{"income_php":None,"expenses_php":None,"realized_profit_php":None,
                           "capital_recovery_php":None},
        "checkpoint96":"OPEN", "database_opened":False,"database_writes":0,"network_calls":0,
    }


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136H: Finance evidence readiness", "",
             "**Status:** Scoped event coverage is available. Verified financial totals remain UNKNOWN; Checkpoint 96 is OPEN.", "",
             "| Source lane | Distinct preview records |", "|---|---:|"]
    lines += [f"| {name} | {count} |" for name,count in c["lanes"].items()]
    lines += ["", f"Total distinct preview records: **{c['preview_events']}**. These are counts, not amounts.",
              f"Consumable sale basis conflicts: **{len(c['sale_cost_profit_conflict_hashes'])}** (hashes in JSON).",
              "Raw transfer quantity corroboration from Task136G does not resolve those costs or make profit accepted.", "",
              "## Acceptance gates", ""]
    lines += [f"- **{name.replace('_',' ').title()}:** {reason}" for name,reason in report["acceptance_gates"].items()]
    lines += ["", "## Reporting rule", "",
              "Keep marketplace gross, fee and net as components of one sale; do not add them as separate receipts. Keep purchases as asset outlays until basis allocation is supported. Keep rewards and stake principal movements separate. Show unknown dates as UNKNOWN_DATE; do not infer a month.", "",
              "This report does not sum WETH, RON, AXS, bAXS or PHP. It does not change stored READY/REVIEW statuses or claim receipt verification.", "",
              "Database opened: NO | Writes: 0 | Network calls: 0", "",
              "VALIDATION: PASS (offline coverage only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--sales", type=Path)
    parser.add_argument("--preview-dir", type=Path, default=Path("reports/axieos_v014/task136b"))
    parser.add_argument("--sales-dir", type=Path, default=Path("reports/axieos_v013/checkpoint96"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136h"))
    args = parser.parse_args()
    preview_path = args.preview or find_one(args.preview_dir, lambda d:d.get("task")=="136B" and "events" in d,"preview")
    sales_path = args.sales or find_one(args.sales_dir, lambda d:d.get("checkpoint")=="96CD" and "sale_evidence_reviews" in d,"sales")
    preview, preview_hash = load(preview_path)
    sales, sales_hash = load(sales_path)
    report = build(preview,sales,sales_hash)
    report["source_files"] = {"preview":{"name":preview_path.name,"sha256":preview_hash},
                              "sales":{"name":sales_path.name,"sha256":sales_hash}}
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    stem="AxieOS_V014_Task136H_Finance_Readiness_"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")+"_"+uuid4().hex[:6]
    jp,mp=args.output_dir/(stem+".json"),args.output_dir/(stem+".md")
    with jp.open("x",encoding="utf-8") as f: json.dump(report,f,indent=2,ensure_ascii=False); f.write("\n")
    with mp.open("x",encoding="utf-8") as f: f.write(markdown(report))
    print("AXIEOS V0.14 - TASK136H - FINANCE EVIDENCE READINESS")
    print("Preview events: 258 | Consumable basis conflicts: 24")
    print("Verified income, expenses, profit, recovery: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network calls: 0")
    print("VALIDATION: PASS (offline coverage only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
