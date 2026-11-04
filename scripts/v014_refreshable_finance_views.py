r"""Task136AM: four refreshable, offline post-apply finance evidence views.

Run from the AxieOS repository root:
    py -B .\scripts\v014_refreshable_finance_views.py
    py -B .\scripts\v014_refreshable_finance_views.py --view income

Reads Task136AK, Task136T, and its SHA-matched Task136R JSON only. Inputs
produce deterministic report filenames and content; a repeat run reuses them.
The views keep every source ID stable and all accepted financial values NULL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


POLICY_VERSION = "post-apply-evidence-1"
VIEWS = ("income", "expense", "capital", "portfolio")
TOTAL_FIELDS = ("income_php", "expenses_php", "realized_profit_php",
                "capital_recovery_php", "portfolio_value_php")
HISTORICAL_PRIMARY = {
    "income": {"REWARD_QUANTITY_CANDIDATE", "SALE_PAYMENT_STORED"},
    "expense": {"ASSET_OUTLAY_STORED"},
    "capital": {"CAPITAL_PROVISIONAL", "CASH_RECEIPT_ATTESTED"},
    "portfolio": None,
}
CACHED_CONTEXT = {
    "income": {"MARKETPLACE_SALE", "MINT_OR_CLAIM", "STAKING_OR_REWARD"},
    "expense": {"MARKETPLACE_BUY", "CONSUMABLE_BURN", "NFT_BURN", "TOKEN_BURN"},
    "capital": None,
    "portfolio": None,
}


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError("STOP: " + reason)


def load(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing report: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def latest(directory: Path, task: str) -> Path:
    matches = []
    for p in directory.glob("*.json") if directory.is_dir() else []:
        d, _ = load(p)
        if d.get("task") == task:
            matches.append((d.get("created_at_utc", ""), p))
    require(matches, f"missing Task{task} JSON in {directory}; pass exact path")
    return max(matches)[1]


def registry_by_sha(directory: Path, sha: str) -> Path:
    matches = [p for p in directory.glob("*.json") if hashlib.sha256(p.read_bytes()).hexdigest() == sha]
    require(len(matches) == 1, f"expected one SHA-matched Task136R in {directory}")
    return matches[0]


def validate(ak: dict, t: dict, r: dict, shas: dict[str, str]) -> tuple[list[dict], list[dict]]:
    require(ak.get("task") == "136AK" and ak.get("checkpoint96") == "OPEN" and
            ak.get("accepted_financial_totals") is None and ak.get("database_writes") == 0 and
            t.get("task") == "136T" and
            t.get("validation", {}).get("status") == "PASS_OFFLINE_TREATMENT_ONLY" and
            t["validation"].get("checkpoint96_closed") is False and
            r.get("task") == "136R" and
            r.get("validation", {}).get("status") == "PASS_OFFLINE_REGISTRY_ONLY" and
            t.get("source_registry_sha256") == shas["136R"],
            "source validation, release boundary, or historical digest differs")
    require(all(v is None for v in t["verified_totals"].values()) and
            all(v is None for v in r["accepted_totals"].values()),
            "historical accepted totals changed")
    original = r["registry_rows"]
    treatments = t["treatment_rows"]
    refreshed = ak["registry_rows"]
    require(len(original) == len(treatments) == t["coverage"]["references"] ==
            ak["coverage"]["historical_references"] and
            len(refreshed) == ak["coverage"]["combined_references"] and
            len({row["registry_id"] for row in refreshed}) == len(refreshed),
            "historical treatment or combined source coverage differs")
    by_id = {row["registry_id"]: row for row in original}
    t_by_id = {row["registry_id"]: row for row in treatments}
    require(len(by_id) == len(t_by_id) == len(original) and
            set(by_id) == set(t_by_id), "historical treatment identity differs")
    historical = refreshed[:len(original)]
    cached = refreshed[len(original):]
    require(len(cached) == ak["coverage"]["cached_references"] and
            [x["registry_id"] for x in historical] == [x["registry_id"] for x in original],
            "historical identity or cached reference count differs")
    for current, prior in zip(historical, original):
        stripped = {k: v for k, v in current.items() if k not in
                    ("post_apply_ledger_status", "post_apply_accounting_status")}
        require(stripped == prior and current["post_apply_ledger_status"] ==
                "HISTORICAL_NOT_REASSESSED", "historical source value changed")
        treatment = t_by_id[current["registry_id"]]
        require(treatment["txhash"] == prior.get("txhash") and
                treatment["source_lane"] == prior["lane"] and
                all(treatment.get(field) is None for field in
                    ("accepted_income", "accepted_expense", "accepted_profit",
                     "accepted_capital_recovery", "accepted_php_value")),
                "historical treatment or accepted value changed")
    cache_ids = set()
    for row in cached:
        key = row["registry_id"]
        require(key.startswith("CACHED_RAW:") and key not in cache_ids and
                key == "CACHED_RAW:" + str(row["txhash"]).lower() and
                row["post_apply_accounting_status"] == "NO_STORED_ACCOUNTING" and
                row["accepted_financial_value"] is None,
                "cached identity or accounting state changed")
        cache_ids.add(key)
    require(Counter(x["post_apply_ledger_status"] for x in cached) ==
            ak["coverage"]["cached_ledger_statuses"] and
            len(cache_ids) == ak["coverage"]["cached_accounting_absent"] and
            not ({str(x["txhash"]).lower() for x in historical if x.get("txhash")} &
                 {str(x["txhash"]).lower() for x in cached}),
            "post-apply status or historical/cached hash overlap differs")
    return historical, cached


def build(kind: str, historical: list[dict], cached: list[dict],
          t: dict, ak: dict, sources: dict) -> dict:
    t_by_id = {row["registry_id"]: row for row in t["treatment_rows"]}
    primary = HISTORICAL_PRIMARY[kind]
    hist = []
    for source in historical:
        item = t_by_id[source["registry_id"]]
        if primary is not None and item["treatment_status"] not in primary:
            continue
        hist.append({"registry_id": source["registry_id"], "txhash": source.get("txhash"),
                     "origin": source["origin"], "source_lane": source["lane"],
                     "treatment_status": item["treatment_status"],
                     "date_as_stored": source.get("date_as_stored"),
                     "asset_as_stored": source.get("asset_as_stored"),
                     "quantity_as_stored": source.get("quantity_as_stored"),
                     "gross_as_stored": source.get("gross_as_stored"),
                     "accepted_financial_value": None})
    selected_labels = CACHED_CONTEXT[kind]
    context = []
    for row in cached:
        label = row.get("candidate_legacy_label")
        if selected_labels is not None and label not in selected_labels:
            continue
        context.append({"registry_id": row["registry_id"], "txhash": row["txhash"],
                        "date_as_stored": row.get("date_as_stored"),
                        "structural_bucket": row["structural_bucket"],
                        "ledger_status": row["post_apply_ledger_status"],
                        "accounting_status": row["post_apply_accounting_status"],
                        "legacy_label_candidate": label,
                        "payment_route_candidate": row.get("candidate_payment_route_status"),
                        "review_lane": row.get("candidate_review_lane"),
                        "linked_closed_axie_flow": bool(row.get("linked_closed_axie_flow")),
                        "accepted_financial_value": None})
    require(len({x["registry_id"] for x in hist + context}) == len(hist) + len(context),
            "view reference duplicate")
    fingerprint = hashlib.sha256(json.dumps({"policy": POLICY_VERSION, "kind": kind,
        "sources": {k: v["sha256"] for k, v in sources.items()}},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"project": "AxieOS", "version": "0.14", "task": "136AM",
            "view": kind, "schema_version": "1.0", "policy_version": POLICY_VERSION,
            "input_fingerprint_sha256": fingerprint, "sources": sources,
            "coverage": {"combined_unique_references": ak["coverage"]["combined_references"],
                         "historical_primary": len(hist), "cached_context": len(context),
                         "historical_primary_statuses": dict(sorted(Counter(
                             x["treatment_status"] for x in hist).items())),
                         "cached_ledger_statuses": dict(sorted(Counter(
                             x["ledger_status"] for x in context).items())),
                         "cached_candidate_labels": dict(sorted(Counter(
                             x["legacy_label_candidate"] or "UNCLASSIFIED" for x in context).items()))},
            "historical_primary": hist, "cached_unaccepted_context": context,
            "accepted_totals": {k: None for k in TOTAL_FIELDS},
            "database_opened": False, "database_writes": 0, "network_calls": 0,
            "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = [f"# AxieOS V0.14 — Task136AM {report['view'].title()} evidence view", "",
             f"Combined registry: **{c['combined_unique_references']}** unique references. "
             f"Historical primary: **{c['historical_primary']}**; "
             f"cached unaccepted context: **{c['cached_context']}**.", "",
             "| Cached ledger state in this view | References |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in c["cached_ledger_statuses"].items()]
    lines += ["", "Historical primary is stored evidence. Cached rows may appear as context "
              "in several views; they are the same registry references and must not be added "
              "across reports. Legacy marketplace labels are candidates, including seven "
              "fungible WETH/SLP exchanges held for separate review.", "",
              "Verified income, expenses, profit, portfolio value, and PHP recovery: **UNKNOWN**. "
              "Raw cache coverage ends at its source snapshot; later activity is not included.", "",
              "Database opened: NO | Writes: 0 | Network: 0", "",
              "VALIDATION: PASS (refreshable evidence view only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def save(report: dict, directory: Path) -> tuple[Path, Path, bool]:
    directory.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AM_" + report["view"].title() +
            "_Post_Apply_" + report["input_fingerprint_sha256"][:16])
    jp, mp = directory / (stem + ".json"), directory / (stem + ".md")
    content = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    body = markdown(report)
    for p, desired in ((jp, content), (mp, body)):
        if p.exists():
            require(p.read_text(encoding="utf-8") == desired,
                    f"{p}: existing snapshot differs; preserve it and inspect")
    fresh = not jp.exists()
    if not jp.exists():
        with jp.open("x", encoding="utf-8") as stream:
            stream.write(content)
    if not mp.exists():
        with mp.open("x", encoding="utf-8") as stream:
            stream.write(body)
    return jp, mp, fresh


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view", choices=("all",) + VIEWS, default="all")
    parser.add_argument("--ak", type=Path)
    parser.add_argument("--ak-dir", type=Path, default=Path("reports/axieos_v014/task136ak"))
    parser.add_argument("--treatment", type=Path)
    parser.add_argument("--treatment-dir", type=Path, default=Path("reports/axieos_v014/task136t"))
    parser.add_argument("--registry-dir", type=Path, default=Path("reports/axieos_v014/task136r"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136am"))
    args = parser.parse_args()
    ap = args.ak or latest(args.ak_dir, "136AK")
    tp = args.treatment or latest(args.treatment_dir, "136T")
    ak, ak_sha = load(ap)
    t, t_sha = load(tp)
    rp = registry_by_sha(args.registry_dir, t["source_registry_sha256"])
    r, r_sha = load(rp)
    historical, cached = validate(ak, t, r,
                                   {"136AK": ak_sha, "136T": t_sha, "136R": r_sha})
    sources = {"136AK": {"filename": ap.name, "sha256": ak_sha},
               "136T": {"filename": tp.name, "sha256": t_sha},
               "136R": {"filename": rp.name, "sha256": r_sha}}
    kinds = VIEWS if args.view == "all" else (args.view,)
    print("AXIEOS V0.14 - TASK136AM - REFRESHABLE FINANCE EVIDENCE VIEWS")
    for kind in kinds:
        report = build(kind, historical, cached, t, ak, sources)
        jp, mp, fresh = save(report, args.output_dir)
        cov = report["coverage"]
        print(f"{kind.upper()}: historical primary {cov['historical_primary']} | "
              f"cached context {cov['cached_context']} | "
              f"{'CREATED' if fresh else 'REUSED'} | {jp} | {mp}")
    print(f"Combined registry references: {len(historical) + len(cached)} | "
          "Verified financial totals: UNKNOWN")
    print("Database opened: NO | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (stable-ID offline report refresh only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
