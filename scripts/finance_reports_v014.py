"""Shared, offline V0.14 finance evidence reports.

Preview mode preserves Task136I-L. Treatment mode reads Task136T and its
hash-matched Task136R registry. Combined mode adds Task136AA cached references
as a separate unresolved coverage bucket. No accepted income, expense, profit,
portfolio value or cash recovery is calculated. No mode connects to SQLite or
any network service.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


KINDS = {
    "income": ("136I", "Income_Evidence", ("TOKEN_REWARD", "MARKETPLACE_SALE")),
    "expense": ("136J", "Expense_Evidence", ("MARKETPLACE_PURCHASE",)),
    "capital": ("136K", "Capital_Flow_Evidence", ("EXTERNAL_CAPITAL", "REPORTED_CASH_RECEIPT")),
    "portfolio": ("136L", "Portfolio_Finance_Coverage", ("EXTERNAL_CAPITAL", "REPORTED_CASH_RECEIPT",
                                                     "TOKEN_REWARD", "MARKETPLACE_SALE", "MARKETPLACE_PURCHASE")),
}
TREATMENT_VIEWS = {
    "income": ({"REWARD_QUANTITY_CANDIDATE", "SALE_PAYMENT_STORED"},
               {"INCOMING_MOVEMENT_UNRESOLVED", "TRANSFER_PURPOSE_UNRESOLVED"}),
    "expense": ({"ASSET_OUTLAY_STORED"},
                {"TOKEN_DISPOSAL_UNRESOLVED", "NFT_DISPOSAL_UNRESOLVED",
                 "STAKING_OUTFLOW_UNRESOLVED", "EXCHANGE_BASIS_UNRESOLVED",
                 "TRANSFER_PURPOSE_UNRESOLVED"}),
    "capital": ({"CAPITAL_PROVISIONAL", "CASH_RECEIPT_ATTESTED"},
                {"TRANSFER_PURPOSE_UNRESOLVED", "EXCHANGE_BASIS_UNRESOLVED"}),
    "portfolio": (None, set()),
}
EXPECTED = {"EXTERNAL_CAPITAL": 108, "REPORTED_CASH_RECEIPT": 4,
            "TOKEN_REWARD": 18, "MARKETPLACE_SALE": 75, "MARKETPLACE_PURCHASE": 53}


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError("STOP: " + reason)


def select_preview(explicit: Path | None, directory: Path) -> Path:
    if explicit is not None:
        require(explicit.is_file(), f"preview missing: {explicit}")
        return explicit
    require(directory.is_dir(), f"preview directory missing: {directory}")
    matches = []
    for path in directory.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("task") == "136B" and isinstance(data.get("events"), list):
            matches.append(path)
    require(len(matches) == 1, f"expected one Task136B preview, found {[p.name for p in matches]}; use --preview PATH")
    return matches[0]


def select_treatment(explicit: Path | None, directory: Path) -> Path:
    if explicit is not None:
        require(explicit.is_file(), f"treatment missing: {explicit}")
        return explicit
    require(directory.is_dir(), f"treatment directory missing: {directory}")
    matches = []
    for path in directory.glob("*.json"):
        try:
            item = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(item, dict) and item.get("task") == "136T":
            matches.append(path)
    require(len(matches) == 1, f"expected one Task136T treatment, found {[p.name for p in matches]}; use --treatment PATH")
    return matches[0]


def read_treatment(path: Path, registry_dir: Path) -> tuple[dict, dict, str, str]:
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    require(data.get("task") == "136T", "wrong treatment task")
    v = data.get("validation", {})
    require(v.get("status") == "PASS_OFFLINE_TREATMENT_ONLY" and v.get("database_opened") is False
            and v.get("database_writes") == 0 and v.get("network_calls") == 0
            and v.get("checkpoint96_closed") is False, "treatment validation changed")
    require(data.get("verified_totals") and all(x is None for x in data["verified_totals"].values()),
            "accepted treatment totals changed")
    rows = data.get("treatment_rows")
    require(isinstance(rows, list) and len(rows) == data.get("coverage", {}).get("references"),
            "treatment row count differs")
    ids = [r.get("registry_id") for r in rows]
    require(all(ids) and len(set(ids)) == len(ids), "duplicate or empty treatment reference")
    require(all(all(r.get(field) is None for field in (
        "accepted_income", "accepted_expense", "accepted_profit",
        "accepted_capital_recovery", "accepted_php_value")) for r in rows),
        "accepted treatment field changed")
    require(Counter(r.get("treatment_status") for r in rows) ==
            data.get("coverage", {}).get("treatments"), "treatment status counts differ")

    expected_sha = data.get("source_registry_sha256")
    require(isinstance(expected_sha, str) and len(expected_sha) == 64, "missing registry digest")
    candidates = list(registry_dir.glob("*.json")) if registry_dir.is_dir() else []
    matched = [(p, p.read_bytes()) for p in candidates
               if hashlib.sha256(p.read_bytes()).hexdigest() == expected_sha]
    require(len(matched) == 1, "expected one hash-matched Task136R registry in "
            f"{registry_dir}; restore the source snapshot before reporting")
    registry_path, registry_raw = matched[0]
    registry = json.loads(registry_raw.decode("utf-8-sig"))
    require(registry.get("task") == "136R" and registry.get("validation", {}).get("status") ==
            "PASS_OFFLINE_REGISTRY_ONLY", "wrong registry or validation")
    rrows = registry.get("registry_rows")
    require(isinstance(rrows, list) and len(rrows) == len(rows), "registry count differs")
    by_id = {r.get("registry_id"): r for r in rrows}
    require(len(by_id) == len(rows) and set(by_id) == set(ids), "registry identities differ")
    for row in rows:
        original = by_id[row["registry_id"]]
        require(row.get("txhash") == original.get("txhash") and
                row.get("source_lane") == original.get("lane") and
                row.get("gross_as_stored") == original.get("gross_as_stored") and
                row.get("quantity_as_stored") == original.get("quantity_as_stored") and
                original.get("accepted_financial_value") is None,
                "treatment and registry source row differ")
    return data, registry, hashlib.sha256(raw).hexdigest(), registry_path.name


def build_treatment(kind: str, treatment: dict, registry: dict,
                    treatment_sha: str, treatment_name: str, registry_name: str) -> dict:
    primary, context = TREATMENT_VIEWS[kind]
    originals = {r["registry_id"]: r for r in registry["registry_rows"]}
    grouped = {"primary_evidence": [], "related_unresolved_context": []}
    for row in treatment["treatment_rows"]:
        label = row["treatment_status"]
        lane = row["source_lane"]
        if primary is None or label in primary:
            bucket = "primary_evidence"
        elif label in context:
            if kind == "income" and lane == "TRANSFER_OUT":
                continue
            if kind == "expense" and lane == "TRANSFER_IN":
                continue
            bucket = "related_unresolved_context"
        else:
            continue
        source = originals[row["registry_id"]]
        grouped[bucket].append({"registry_id": row["registry_id"], "origin": row["origin"],
                                "source_lane": row["source_lane"],
                                "treatment_status": label, "treatment_reason": row["treatment_reason"],
                                "date_as_stored": source.get("date_as_stored"),
                                "asset_as_stored": row.get("asset_as_stored"),
                                "quantity_as_stored": row.get("quantity_as_stored"),
                                "gross_as_stored": row.get("gross_as_stored"),
                                "txhash": row.get("txhash"),
                                "source_status": row.get("source_status"),
                                "accepted_financial_value": None})
    require(not ({r["registry_id"] for r in grouped["primary_evidence"]} &
                 {r["registry_id"] for r in grouped["related_unresolved_context"]}),
            "report buckets overlap")
    return {"project": "AxieOS", "version": "0.14", "task": "136V",
            "view": kind, "source_mode": "TREATMENT_SNAPSHOT",
            "scope": "Versioned treatment view; stored source strings and unresolved context only",
            "source_treatment": {"filename": treatment_name, "sha256": treatment_sha},
            "source_registry_filename": registry_name,
            "coverage": {"source_references": len(treatment["treatment_rows"]),
                         "primary_rows": len(grouped["primary_evidence"]),
                         "related_unresolved_rows": len(grouped["related_unresolved_context"]),
                         "primary_status_counts": dict(sorted(Counter(
                             r["treatment_status"] for r in grouped["primary_evidence"]).items())),
                         "context_status_counts": dict(sorted(Counter(
                             r["treatment_status"] for r in grouped["related_unresolved_context"]).items()))},
            "accepted_totals": {"income_php": None, "expenses_php": None,
                                "realized_profit_php": None, "capital_recovery_php": None,
                                "portfolio_value_php": None},
            **grouped,
            "validation": {"status": "PASS_OFFLINE_TREATMENT_VIEW_ONLY", "database_opened": False,
                           "database_writes": 0, "network_calls": 0, "checkpoint96_closed": False}}


def render_treatment(report: dict) -> str:
    c = report["coverage"]
    lines = [f"# AxieOS V0.14 — Task136V {report['view'].title()} treatment view", "",
             "**Status:** Source evidence and treatment only. Verified financial totals UNKNOWN; Checkpoint 96 OPEN.", "",
             f"Source references: {c['source_references']}. Primary evidence: {c['primary_rows']}. "
             f"Related unresolved context: {c['related_unresolved_rows']}.", "",
             "| Bucket | Treatment | References |", "|---|---|---:|"]
    for bucket, field in (("Primary", "primary_status_counts"), ("Context", "context_status_counts")):
        for status, count in c[field].items():
            lines.append(f"| {bucket} | {status} | {count} |")
    lines += ["", "Primary evidence is still provisional: a stored purchase is an asset outlay, "
              "a sale has stored payment arithmetic, and a reward is a token quantity candidate. "
              "Related unresolved rows are not additional income, expense or recovery. "
              "The companion JSON gives each reference, treatment reason and original stored value. "
              "The report does not aggregate across tokens, convert to PHP or accept financial amounts.", "",
              "Database opened: NO | Writes: 0 | Network calls: 0", "",
              "VALIDATION: PASS (offline treatment view only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def select_combined(explicit: Path | None, directory: Path) -> Path:
    if explicit is not None:
        require(explicit.is_file(), f"combined registry missing: {explicit}")
        return explicit
    require(directory.is_dir(), f"combined registry directory missing: {directory}")
    matches = []
    for path in directory.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("task") == "136AA":
            matches.append((data.get("created_at_utc", ""), path))
    require(bool(matches), f"no Task136AA JSON in {directory}; use --combined PATH")
    return max(matches)[1]


def read_combined(path: Path, treatment: dict, historical_registry: dict) -> tuple[dict, str]:
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    require(data.get("task") == "136AA" and
            data.get("validation", {}).get("status") == "PASS_OFFLINE_COMBINED_REGISTRY_ONLY",
            "wrong combined registry or validation")
    require(data["validation"].get("database_opened") is False and
            data["validation"].get("database_writes") == 0 and
            data["validation"].get("network_calls") == 0 and
            data["validation"].get("checkpoint96_closed") is False,
            "combined registry safety boundary changed")
    require(data.get("accepted_totals") and all(v is None for v in data["accepted_totals"].values()),
            "combined accepted totals changed")
    require(data.get("sources", {}).get("136R", {}).get("sha256") ==
            treatment["source_registry_sha256"], "combined source does not match treatment registry")
    historical = historical_registry["registry_rows"]
    rows = data.get("registry_rows")
    cov = data.get("coverage", {})
    require(isinstance(rows, list) and len(rows) == cov.get("combined_references"),
            "combined reference count differs")
    require(len(historical) == cov.get("historical_references"),
            "historical count differs")
    originals = {r["registry_id"]: r for r in historical}
    combined_historical = {r["registry_id"]: r for r in rows
                           if r.get("origin") != "TASK136Z_CACHED_RAW"}
    require(originals == combined_historical, "combined historical references differ")
    cached = [r for r in rows if r.get("origin") == "TASK136Z_CACHED_RAW"]
    require(len(cached) == cov.get("new_cached_hashed_references") and
            cov.get("hashed_overlap") == 0, "cached coverage differs")
    ids = [r.get("registry_id") for r in rows]
    require(all(ids) and len(ids) == len(set(ids)), "duplicate combined reference ID")
    historical_hashes = {str(r["txhash"]).lower() for r in historical if r.get("txhash")}
    cached_hashes = [str(r.get("txhash") or "").lower() for r in cached]
    require(all(cached_hashes) and len(cached_hashes) == len(set(cached_hashes)) and
            not historical_hashes.intersection(cached_hashes), "cached hash overlap")
    require(all(r.get("accepted_financial_value") is None and
                r.get("lane") == "CACHED_UNATTRIBUTED" and
                r.get("evidence_status") == "RAW_CANDIDATE_UNACCEPTED" for r in cached),
            "cached reference treatment changed")
    require(Counter(r.get("structural_bucket") for r in cached) ==
            cov.get("cached_bucket_counts"), "cached structural bucket counts differ")
    return data, hashlib.sha256(raw).hexdigest()


def build_combined(kind: str, treatment: dict, historical_registry: dict,
                   treatment_sha: str, treatment_name: str, historical_name: str,
                   combined: dict, combined_sha: str, combined_name: str) -> dict:
    report = build_treatment(kind, treatment, historical_registry,
                             treatment_sha, treatment_name, historical_name)
    cached = [r for r in combined["registry_rows"]
              if r.get("origin") == "TASK136Z_CACHED_RAW"]
    report["task"] = "136AB"
    report["scope"] = "Historical treatment and separately unresolved cached source coverage"
    report["source_mode"] = "COMBINED_SOURCE_COVERAGE"
    report["source_combined"] = {"filename": combined_name, "sha256": combined_sha}
    report["coverage"]["combined_references"] = combined["coverage"]["combined_references"]
    report["coverage"]["historical_unhashed_references"] = combined["coverage"]["historical_unhashed_references"]
    report["coverage"]["cached_unresolved_rows"] = len(cached)
    report["coverage"]["cached_bucket_counts"] = dict(sorted(Counter(
        r["structural_bucket"] for r in cached).items()))
    report["cached_unresolved_rows"] = [
        {"registry_id": r["registry_id"], "txhash": r["txhash"],
         "date_as_stored": r["date_as_stored"],
         "structural_bucket": r["structural_bucket"],
         "pair": r.get("pair"), "methods": r.get("methods"),
         "token_symbols": r.get("token_symbols"),
         "treatment_status": "CACHED_SOURCE_UNRESOLVED",
         "accepted_financial_value": None} for r in cached]
    require(report["coverage"]["source_references"] + len(cached) ==
            report["coverage"]["combined_references"], "combined report coverage mismatch")
    report["validation"]["status"] = "PASS_OFFLINE_COMBINED_VIEW_ONLY"
    return report


def render_combined(report: dict) -> str:
    c = report["coverage"]
    lines = [f"# AxieOS V0.14 — Task136AB {report['view'].title()} combined coverage", "",
             f"Combined source references: **{c['combined_references']}**; "
             f"historical treatment: **{c['source_references']}**; "
             f"cached unresolved hashes: **{c['cached_unresolved_rows']}**.", "",
             f"Historical primary evidence: **{c['primary_rows']}**; "
             f"historical related unresolved: **{c['related_unresolved_rows']}**. "
             "The cache is a separate unresolved section in the companion JSON and does not add to these counts.", "",
             "| Cached structural bucket | Hashes |", "|---|---:|"]
    for bucket, count in c["cached_bucket_counts"].items():
        lines.append(f"| {bucket} | {count} |")
    lines += ["", f"Historical references without hashes: **{c['historical_unhashed_references']}**; "
              "their potential economic overlap with cached hashes is unresolved.", "",
              "The four views can each reference the same cached hash as unresolved context; "
              "these are not four sets of financial events. No cached hash is accepted as "
              "income, expense, capital, portfolio value or profit.", "",
              "Verified financial totals: **UNKNOWN**. Checkpoint 96: **OPEN**.", "",
              "Database opened: NO | Writes: 0 | Network calls: 0", "",
              "VALIDATION: PASS (offline combined view only).", ""]
    return "\n".join(lines)


def read_preview(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    require(data.get("task") == "136B" and data.get("schema_version") == "0.1", "wrong preview schema")
    v = data.get("validation", {})
    require(v.get("status") == "PASS_OFFLINE_PREVIEW_ONLY" and v.get("database_opened") is False
            and v.get("database_writes") == 0 and v.get("network_calls") == 0
            and v.get("checkpoint96_closed") is False, "preview validation changed")
    events = data.get("events")
    require(isinstance(events, list) and len(events) == 258, "preview event count changed")
    ids = [e.get("event_id") for e in events]
    require(None not in ids and len(set(ids)) == 258, "duplicate or empty event ID")
    require(Counter(e.get("lane") for e in events) == EXPECTED, "preview lane counts changed")
    require(all(e.get("accepted_cost_basis") is None and e.get("accepted_realized_profit") is None
                and e.get("accepted_php_value") is None and e.get("receipt_verified") is False
                for e in events), "accepted financial or receipt field changed")
    require(all(value is None for value in data.get("unknown_metrics", {}).values()),
            "unknown preview metric changed")
    return data, hashlib.sha256(raw).hexdigest()


def narrow_event(event: dict) -> dict:
    """Retain stored strings and provenance; do not derive a financial amount."""
    return {key: event.get(key) for key in (
        "event_id", "lane", "source_row_id", "source_checkpoint", "source_sha256",
        "accounting_key", "txhash", "date_as_stored", "classification_as_stored",
        "asset", "quantity_as_stored", "payment_gross_as_stored", "marketplace_fee_as_stored",
        "payment_net_as_stored", "source_status", "evidence_status", "receipt_verified",
        "accepted_cost_basis", "accepted_realized_profit", "accepted_php_value", "gas_evidence"
    )}


def build(kind: str, preview: dict, sha256: str, name: str) -> dict:
    task, _, lanes = KINDS[kind]
    selected = [narrow_event(e) for e in preview["events"] if e["lane"] in lanes]
    counts = dict(sorted(Counter(e["lane"] for e in selected).items()))
    statuses = [
        {"lane": lane, "stored_status": status, "evidence_status": evidence, "rows": n}
        for (lane, status, evidence), n in sorted(Counter(
            (e["lane"], str(e["source_status"] or "UNSPECIFIED"), e["evidence_status"])
            for e in selected
        ).items())
    ]
    missing_dates = sum(not e["date_as_stored"] for e in selected)
    gas = Counter(e["gas_evidence"]["status"] for e in selected if e["gas_evidence"])
    return {
        "project": "AxieOS", "version": "0.14", "task": task,
        "scope": "Offline historical evidence view; no accepted combined financial total",
        "source_preview": {"filename": name, "sha256": sha256},
        "coverage": {"selected_rows": len(selected), "lanes": counts,
                     "unknown_date_rows": missing_dates, "statuses": statuses,
                     "event_linked_gas_evidence": dict(sorted(gas.items())),
                     "all_preview_rows": len(preview["events"]),
                     "raw_fee_source_rows_not_added_as_events": preview["coverage"]["gas_raw_rows"]},
        "accepted_totals": {"income_php": None, "expenses_php": None,
                            "realized_profit_php": None, "capital_recovery_php": None,
                            "portfolio_value_php": None},
        "evidence_rows": selected,
        "validation": {"status": "PASS_OFFLINE_EVIDENCE_ONLY", "database_opened": False,
                       "database_writes": 0, "network_calls": 0, "checkpoint96_closed": False},
    }


def render(kind: str, report: dict) -> str:
    title = KINDS[kind][1].replace("_", " ")
    lines = [f"# AxieOS V0.14 — Task{report['task']}: {title}", "",
             "**Status:** Stored source evidence only. Verified financial totals remain UNKNOWN; Checkpoint 96 OPEN.", "",
             "| Lane | Rows |", "|---|---:|"]
    lines += [f"| {lane} | {n} |" for lane, n in report["coverage"]["lanes"].items()]
    lines += ["", f"Selected rows: **{report['coverage']['selected_rows']}**. "
              f"Rows without a stored date: **{report['coverage']['unknown_date_rows']}**.", ""]
    if kind == "income":
        lines += ["Rewards are token quantity evidence; staking principal movements are excluded. "
                  "Marketplace sales contain stored gross, fee, and net components of the same event. "
                  "No receipt or PHP income has been verified.", ""]
    elif kind == "expense":
        lines += ["The 53 purchase rows are **asset outlays**, not approved operating expenses or fresh capital. "
                  "Event-linked raw gas is candidate evidence; its unit and payer remain unverified. "
                  "Other raw fee rows are not added to these purchase rows.", ""]
    elif kind == "capital":
        lines += ["Included contributions are provisionally identified. Reported cash receipts are user attested "
                  "and have not been bank matched as permanent recovery. Neither is a verified all-time capital total.", ""]
    else:
        lines += ["This coverage view separates capital, reported cash receipts, token rewards, marketplace "
                  "proceeds and asset purchases. It does not include complete Bounty, Terrarium, swap, release "
                  "or gas economics. Current holdings and unrealized value are unknown.", ""]
    lines += ["| Lane | Stored status | Evidence status | Rows |", "|---|---|---|---:|"]
    for item in report["coverage"]["statuses"]:
        lines.append(f"| {item['lane']} | {item['stored_status']} | {item['evidence_status']} | {item['rows']} |")
    lines += ["", "Each row, its exact stored strings and source SHA-256 are preserved in the companion JSON. "
              "READY/REVIEW are source labels, not independent receipt verification. "
              "No assets are converted to PHP or added across tokens.", "",
              "Database opened: NO | Writes: 0 | Network calls: 0", "",
              "VALIDATION: PASS (offline evidence only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def run(kind: str) -> None:
    require(kind in KINDS, f"unknown report kind: {kind}")
    task, label, _ = KINDS[kind]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preview", "treatment", "combined"), default="preview",
                        help="Task136B preview, Task136T treatment, or Task136AA combined coverage")
    parser.add_argument("--preview", type=Path, help="Exact Task136B JSON path")
    parser.add_argument("--preview-dir", type=Path, default=Path("reports/axieos_v014/task136b"))
    parser.add_argument("--treatment", type=Path, help="Exact Task136T JSON path")
    parser.add_argument("--treatment-dir", type=Path, default=Path("reports/axieos_v014/task136t"))
    parser.add_argument("--registry-dir", type=Path, default=Path("reports/axieos_v014/task136r"))
    parser.add_argument("--combined", type=Path, help="Exact Task136AA JSON path")
    parser.add_argument("--combined-dir", type=Path, default=Path("reports/axieos_v014/task136aa"))
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.mode == "combined":
        require(args.preview is None, "--preview is only for --mode preview")
        treatment_path = select_treatment(args.treatment, args.treatment_dir)
        treatment, registry, sha256, registry_name = read_treatment(
            treatment_path, args.registry_dir)
        combined_path = select_combined(args.combined, args.combined_dir)
        combined, combined_sha = read_combined(combined_path, treatment, registry)
        report = build_combined(kind, treatment, registry, sha256, treatment_path.name,
                                registry_name, combined, combined_sha, combined_path.name)
        report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
        directory = args.output_dir or Path("reports/axieos_v014/task136ab")
        directory.mkdir(parents=True, exist_ok=True)
        stem = (f"AxieOS_V014_Task136AB_{kind.title()}_Combined_Coverage_"
                + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
                + "_" + uuid4().hex[:6])
        jp, mp = directory / (stem + ".json"), directory / (stem + ".md")
        with jp.open("x", encoding="utf-8") as out:
            json.dump(report, out, ensure_ascii=False, indent=2)
            out.write("\n")
        with mp.open("x", encoding="utf-8") as out:
            out.write(render_combined(report))
        c = report["coverage"]
        print(f"AXIEOS V0.14 - TASK136AB - {kind.upper()} COMBINED COVERAGE")
        print(f"Combined references: {c['combined_references']} | "
              f"Historical primary: {c['primary_rows']} | Cached unresolved: {c['cached_unresolved_rows']}")
        print("Verified financial totals: UNKNOWN")
        print(f"Reports: {jp} {mp}")
        print("Database opened: NO | Writes: 0 | Network calls: 0")
        print("VALIDATION: PASS (offline combined view only; Checkpoint 96 OPEN)")
        return
    if args.mode == "treatment":
        require(args.preview is None and args.combined is None,
                "--preview/--combined are not for --mode treatment")
        path = select_treatment(args.treatment, args.treatment_dir)
        treatment, registry, sha256, registry_name = read_treatment(path, args.registry_dir)
        report = build_treatment(kind, treatment, registry, sha256, path.name, registry_name)
        report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
        directory = args.output_dir or Path("reports/axieos_v014/task136v")
        directory.mkdir(parents=True, exist_ok=True)
        stem = (f"AxieOS_V014_Task136V_{kind.title()}_Treatment_View_"
                + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
        jp, mp = directory / (stem + ".json"), directory / (stem + ".md")
        with jp.open("x", encoding="utf-8") as out:
            json.dump(report, out, ensure_ascii=False, indent=2)
            out.write("\n")
        with mp.open("x", encoding="utf-8") as out:
            out.write(render_treatment(report))
        print(f"AXIEOS V0.14 - TASK136V - {kind.upper()} TREATMENT VIEW")
        print(f"Primary references: {report['coverage']['primary_rows']} | "
              f"Related unresolved: {report['coverage']['related_unresolved_rows']}")
        print("Verified financial totals: UNKNOWN")
        print(f"Reports: {jp} {mp}")
        print("Database opened: NO | Writes: 0 | Network calls: 0")
        print("VALIDATION: PASS (offline treatment view only; Checkpoint 96 OPEN)")
        return
    require(args.treatment is None and args.combined is None,
            "--treatment/--combined require --mode treatment/combined")
    path = select_preview(args.preview, args.preview_dir)
    preview, sha256 = read_preview(path)
    report = build(kind, preview, sha256, path.name)
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    directory = args.output_dir or Path(f"reports/axieos_v014/task{task.lower()}")
    directory.mkdir(parents=True, exist_ok=True)
    stem = (f"AxieOS_V014_Task{task}_{label}_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = directory / (stem + ".json"), directory / (stem + ".md")
    with jp.open("x", encoding="utf-8") as out:
        json.dump(report, out, ensure_ascii=False, indent=2)
        out.write("\n")
    with mp.open("x", encoding="utf-8") as out:
        out.write(render(kind, report))
    print(f"AXIEOS V0.14 - TASK{task} - {label.upper()}")
    print(f"Evidence rows: {report['coverage']['selected_rows']} | Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network calls: 0")
    print("VALIDATION: PASS (offline evidence only; Checkpoint 96 OPEN)")
