r"""Task136BG: refresh four finance evidence views with recent raw sources.

From the AxieOS repository root:
    py -B .\scripts\v014_recent_finance_views.py

Uses SHA-linked Task136BF/AK and the four existing Task136AP reports. Keeps
prior view rows and values unchanged; shows every recent hash as unresolved
context with a relevance marker per view. Offline, deterministic, no totals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from v014_post_apply_reconcile import require
from v014_raw_import_clone import by_sha, latest, load


VIEWS = ("income", "expense", "capital", "portfolio")
POLICY = "recent-unaccepted-coverage-1"
RELEVANT = {
    "income": {"MARKETPLACE_SALE", "MINT_OR_CLAIM", "STAKING_OR_REWARD"},
    "expense": {"MARKETPLACE_BUY", "CONSUMABLE_BURN", "NFT_BURN", "TOKEN_BURN"},
    "capital": None,
    "portfolio": None,
}


def ap_views(directory: Path, ak_sha: str) -> dict[str, tuple[Path, dict, str]]:
    found = {}
    for path in directory.glob("*.json") if directory.is_dir() else []:
        doc, sha = load(path)
        if doc.get("task") != "136AP" or doc.get("view") not in VIEWS or \
                doc.get("sources", {}).get("136AK", {}).get("sha256") != ak_sha:
            continue
        kind = doc["view"]
        require(kind not in found,
                f"multiple Task136AP {kind} snapshots for Task136AK")
        found[kind] = (path, doc, sha)
    require(set(found) == set(VIEWS),
            "expected four Task136AP views for the Task136AK source")
    return found


def build(kind: str, ap: dict, bf: dict, ak: dict,
          sources: dict[str, dict]) -> dict:
    require(kind in VIEWS and ap.get("task") == "136AP" and
            ap.get("view") == kind and bf.get("task") == "136BF" and
            ak.get("task") == "136AK" and
            all(doc.get("checkpoint96") == "OPEN" for doc in (ap, bf, ak)) and
            bf.get("accepted_financial_totals") is None and
            ak.get("accepted_financial_totals") is None and
            ap.get("accepted_totals") and
            all(v is None for v in ap["accepted_totals"].values()) and
            bf["sources"]["136AK"]["sha256"] == sources["136AK"]["sha256"] and
            ap["sources"]["136AK"]["sha256"] == sources["136AK"]["sha256"],
            "source task, view, digest or financial boundary differs")
    old = ak["registry_rows"]
    combined = bf["registry_rows"]
    require(len(old) == ak["coverage"]["combined_references"] ==
            ap["coverage"]["combined_unique_references"] and
            len(combined) == bf["coverage"]["combined_references"] and
            combined[:len(old)] == old and
            len(combined) - len(old) ==
                bf["coverage"]["recent_raw_hash_references"],
            "Task136BF changed prior source registry or recent count")
    hist = ap["historical_primary"]
    cached = ap["cached_unaccepted_context"]
    old_by_id = {row["registry_id"]: row for row in old}
    require(len(old_by_id) == len(old) and
            len(hist) == ap["coverage"]["historical_primary"] and
            len(cached) == ap["coverage"]["cached_context"] and
            len({row["registry_id"] for row in hist + cached}) ==
                len(hist) + len(cached) and
            all(row["registry_id"] in old_by_id and
                row.get("accepted_financial_value") is None
                for row in hist + cached),
            "Task136AP historical or cached view rows changed")
    recent_rows = combined[len(old):]
    relevant_labels = RELEVANT[kind]
    recent = []
    for source in recent_rows:
        h = str(source.get("txhash") or "").lower()
        require(source["registry_id"] == "RECENT_RAW:" + h and
                source.get("origin") == "TASK136AU_RECENT_RAW" and
                source["post_apply_accounting_status"] == "NO_STORED_ACCOUNTING" and
                source["accepted_financial_value"] is None and
                source["financial_treatment"] == "UNREVIEWED_CANDIDATE",
                "recent source identity, accounting or value differs")
        label = source.get("candidate_legacy_label")
        route = source.get("candidate_payment_route_status")
        fungible = route == "FUNGIBLE_ROUTE_REVIEW"
        require(not fungible or (label == "MARKETPLACE_BUY" and
                source.get("candidate_review_lane") == "FUNGIBLE_EXCHANGE_REVIEW"),
                "recent fungible candidate treatment differs")
        relevant = relevant_labels is None or label in relevant_labels
        evidence = ("FUNGIBLE_EXCHANGE_CANDIDATE" if fungible else
                    "HISTORICAL_ENDPOINT_NFT_CANDIDATE" if route ==
                        "HISTORICAL_ENDPOINT_MATCH_CANDIDATE" else
                    "LEGACY_CANDIDATE_UNVERIFIED" if label else
                    "UNATTRIBUTED_RAW_SOURCE")
        recent.append({"registry_id": source["registry_id"],
                       "txhash": h, "date_as_stored": source["date_as_stored"],
                       "legacy_label_candidate": label,
                       "evidence_classification": evidence,
                       "relevance": "RELEVANT_CANDIDATE" if relevant else
                           "OTHER_UNRESOLVED_SOURCE",
                       "ledger_status": source["post_apply_ledger_status"],
                       "accounting_status": source["post_apply_accounting_status"],
                       "review_lane": source.get("candidate_review_lane"),
                       "payment_route_candidate": route,
                       "accepted_financial_value": None})
    ids = [row["registry_id"] for row in hist + cached + recent]
    require(len(ids) == len(set(ids)) and
            len(recent) == bf["coverage"]["recent_raw_hash_references"],
            "finance view source identities duplicate")
    fingerprint = hashlib.sha256(json.dumps(
        {"policy": POLICY, "view": kind,
         "sources": {k: v["sha256"] for k, v in sources.items()}},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    counts = Counter(row["relevance"] for row in recent)
    return {"project": "AxieOS", "version": "0.14", "task": "136BG",
            "view": kind, "policy_version": POLICY,
            "input_fingerprint_sha256": fingerprint,
            "sources": sources,
            "coverage": {"combined_unique_references": len(combined),
                         "historical_primary": len(hist),
                         "prior_cached_context": len(cached),
                         "recent_unaccepted_sources": len(recent),
                         "recent_relevant_candidates": counts["RELEVANT_CANDIDATE"],
                         "recent_other_unresolved": counts["OTHER_UNRESOLVED_SOURCE"],
                         "recent_fungible_review": sum(row["evidence_classification"] ==
                             "FUNGIBLE_EXCHANGE_CANDIDATE" for row in recent),
                         "recent_route_match_candidates": sum(
                             row["evidence_classification"] ==
                             "HISTORICAL_ENDPOINT_NFT_CANDIDATE" for row in recent)},
            "historical_primary": hist,
            "cached_unaccepted_context": cached,
            "recent_unaccepted_context": recent,
            "accepted_totals": ap["accepted_totals"],
            "database_opened": False, "database_writes": 0,
            "network_calls": 0, "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    return "\n".join([
        f"# AxieOS V0.14 — Task136BG {report['view'].title()} recent evidence view", "",
        f"Combined source references: **{c['combined_unique_references']}**. "
        f"Historical primary: **{c['historical_primary']}**; prior cached context: "
        f"**{c['prior_cached_context']}**; recent unaccepted sources: "
        f"**{c['recent_unaccepted_sources']}**.", "",
        f"Recent relevant candidates: **{c['recent_relevant_candidates']}**; "
        f"other unresolved sources: **{c['recent_other_unresolved']}**. "
        f"Fungible exchange review: **{c['recent_fungible_review']}**; "
        f"historical route matched NFT candidates: "
        f"**{c['recent_route_match_candidates']}**.", "",
        "The same recent hash can appear in all four views. Relevance and a "
        "historical endpoint match are evidence labels only. The prior receipt "
        "annotation is preserved. No recent transaction has accepted income, "
        "expense, basis, profit or cash recovery.", "",
        "Verified financial totals: **UNKNOWN**. Checkpoint 96: **OPEN**.", "",
        "Database opened: NO | Writes: 0 | Network: 0", ""])


def save(report: dict, directory: Path) -> tuple[Path, Path, bool]:
    directory.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136BG_" + report["view"].title() +
            "_Recent_Evidence_" + report["input_fingerprint_sha256"][:16])
    jp, mp = directory / (stem + ".json"), directory / (stem + ".md")
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    body = markdown(report)
    for path, desired in ((jp, payload), (mp, body)):
        if path.exists():
            require(path.read_text(encoding="utf-8") == desired,
                    f"{path}: existing report differs; inspect instead of overwrite")
    fresh = not jp.exists()
    if not jp.exists():
        with jp.open("x", encoding="utf-8") as stream:
            stream.write(payload)
    if not mp.exists():
        with mp.open("x", encoding="utf-8") as stream:
            stream.write(body)
    return jp, mp, fresh


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view", choices=("all",) + VIEWS, default="all")
    parser.add_argument("--bf-dir", type=Path,
                        default=Path("reports/axieos_v014/task136bf"))
    parser.add_argument("--ak-dir", type=Path,
                        default=Path("reports/axieos_v014/task136ak"))
    parser.add_argument("--ap-dir", type=Path,
                        default=Path("reports/axieos_v014/task136ap"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("reports/axieos_v014/task136bg"))
    args = parser.parse_args()
    bp = latest(args.bf_dir, "136BF")
    bf, bf_sha = load(bp)
    apath = by_sha(args.ak_dir, bf["sources"]["136AK"]["sha256"], "136AK")
    ak, ak_sha = load(apath)
    views = ap_views(args.ap_dir, ak_sha)
    kinds = VIEWS if args.view == "all" else (args.view,)
    print("AXIEOS V0.14 - TASK136BG - RECENT FINANCE EVIDENCE VIEWS")
    for kind in kinds:
        path, ap, ap_sha = views[kind]
        sources = {"136BF": {"filename": bp.name, "sha256": bf_sha},
                   "136AK": {"filename": apath.name, "sha256": ak_sha},
                   "136AP": {"filename": path.name, "sha256": ap_sha}}
        report = build(kind, ap, bf, ak, sources)
        jp, mp, fresh = save(report, args.output_dir)
        c = report["coverage"]
        print(f"{kind.upper()}: historical {c['historical_primary']} | "
              f"prior cached {c['prior_cached_context']} | recent "
              f"{c['recent_unaccepted_sources']} (relevant "
              f"{c['recent_relevant_candidates']}) | "
              f"{'CREATED' if fresh else 'REUSED'} | {jp} | {mp}")
    print(f"Combined registry references: {bf['coverage']['combined_references']} | "
          "Verified financial totals: UNKNOWN")
    print("Database opened: NO | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (recent source coverage only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
