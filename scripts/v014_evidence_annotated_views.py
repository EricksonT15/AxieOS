r"""Task136AP: refresh four finance views with AO and AN evidence annotations.

From the AxieOS repository root:
    py -B .\scripts\v014_evidence_annotated_views.py

Reads only Task136AK, AM (four views), AN and AO JSON reports. Existing
registry IDs and cached rows are preserved. No accepted totals, SQLite, RPC,
or writes outside new Task136AP report files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


VIEWS = ("income", "expense", "capital", "portfolio")
POLICY = "evidence-annotations-1"


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError("STOP: " + reason)


def load(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing source: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def latest(directory: Path, task: str) -> Path:
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        doc, _ = load(path)
        if doc.get("task") == task:
            matches.append((doc.get("created_at_utc", ""), path))
    require(bool(matches), f"missing Task{task} JSON in {directory}")
    return max(matches)[1]


def am_views(directory: Path, ak_sha: str) -> dict[str, tuple[Path, dict, str]]:
    found: dict[str, tuple[Path, dict, str]] = {}
    for path in directory.glob("*.json") if directory.is_dir() else []:
        doc, sha = load(path)
        if doc.get("task") != "136AM" or doc.get("view") not in VIEWS:
            continue
        if doc.get("sources", {}).get("136AK", {}).get("sha256") != ak_sha:
            continue
        kind = doc["view"]
        require(kind not in found, f"multiple Task136AM {kind} views for selected Task136AK")
        found[kind] = path, doc, sha
    require(set(found) == set(VIEWS), "expected four Task136AM views for selected Task136AK")
    return found


def build(ak: dict, am: dict, an: dict, ao: dict, kind: str,
          sources: dict[str, dict]) -> dict:
    require(all(doc.get("checkpoint96") == "OPEN" for doc in (ak, am, an, ao)) and
            ak.get("task") == "136AK" and am.get("task") == "136AM" and
            an.get("task") == "136AN" and ao.get("task") == "136AO" and
            am.get("view") == kind and
            ak.get("accepted_financial_totals") is None and
            an.get("accepted_financial_totals") is None and
            ao.get("accepted_financial_totals") is None and
            all(value is None for value in am["accepted_totals"].values()),
            "source task or financial state differs")
    require(am["sources"]["136AK"]["sha256"] == sources["136AK"]["sha256"] and
            ao["sources"]["136AG"]["sha256"] == ak["sources"]["136AG"]["sha256"] and
            ao["sources"]["136AI"]["sha256"] == ak["sources"]["136AI"]["sha256"] and
            an["sources"]["136AJ"]["sha256"] == ak["sources"]["136AJ"]["sha256"],
            "Task136AK/AM/AN/AO are from different source snapshots")
    require(am["coverage"]["combined_unique_references"] ==
            ak["coverage"]["combined_references"] and
            am["coverage"]["historical_primary"] == len(am["historical_primary"]) and
            am["coverage"]["cached_context"] == len(am["cached_unaccepted_context"]),
            "Task136AM view coverage differs")
    overrides = {row["txhash"].lower(): row for row in ao["overrides"]}
    sale = an["matched_case"]
    sale_hash = sale["sale_hash"].lower()
    require(len(overrides) == ao["coverage"]["fungible_overrides"] == 7 and
            ao["coverage"]["guarded_hashes"] ==
            ak["coverage"]["cached_ledger_statuses"]["MATERIALIZED_GUARDED"] and
            an["coverage"]["historical_receipt_crosswalked"] == 1 and
            an["coverage"]["other_closed_axie_candidates_not_receipt_checked"] == 26 and
            sale_hash not in overrides and
            sale["registry_action"] == "ANNOTATE_EXISTING_SOURCE_ONLY_NO_NEW_EVENT",
            "receipt or fungible overlay coverage differs")
    raw = ak["registry_rows"]
    registry = {row["registry_id"]: row for row in raw}
    require(len(raw) == len(registry) == ak["coverage"]["combined_references"],
            "combined registry identities differ")
    for h in overrides:
        row = registry.get("CACHED_RAW:" + h)
        require(row is not None and row["candidate_legacy_label"] == "MARKETPLACE_BUY" and
                row["candidate_review_lane"] == "FUNGIBLE_EXCHANGE_REVIEW" and
                row["post_apply_accounting_status"] == "NO_STORED_ACCOUNTING" and
                overrides[h]["proposed_evidence_label"] == "FUNGIBLE_EXCHANGE_CANDIDATE",
                f"{h}: fungible overlay differs from registry")
    receipt_row = registry.get("CACHED_RAW:" + sale_hash)
    require(receipt_row is not None and receipt_row["candidate_legacy_label"] ==
            "MARKETPLACE_SALE" and receipt_row["linked_closed_axie_flow"] is True and
            receipt_row["post_apply_accounting_status"] == "NO_STORED_ACCOUNTING",
            "receipt sale differs from cached registry")
    prior = am["cached_unaccepted_context"]
    prior_ids = [row["registry_id"] for row in prior]
    require(len(prior_ids) == len(set(prior_ids)) and
            all(key in registry and registry[key]["txhash"].lower() ==
                str(row["txhash"]).lower() for key, row in zip(prior_ids, prior)) and
            all(row["accepted_financial_value"] is None for row in prior),
            "Task136AM context IDs or accepted values differ")
    context = []
    for source in prior:
        row = dict(source)
        h = str(row["txhash"]).lower()
        row["evidence_classification"] = (
            "FUNGIBLE_EXCHANGE_CANDIDATE" if h in overrides else
            "RECEIPT_CHECKED_SALE_CANDIDATE" if h == sale_hash else
            "LEGACY_CANDIDATE_UNCHANGED")
        row["receipt_verified_sale_net_weth"] = (
            sale["receipt_verified_sale_net_weth"] if h == sale_hash else None)
        row["accepted_financial_value"] = None
        context.append(row)
    expected_overrides = 7 if kind in ("expense", "capital", "portfolio") else 0
    expected_receipts = 1 if kind in ("income", "capital", "portfolio") else 0
    labels = Counter(row["evidence_classification"] for row in context)
    require(labels["FUNGIBLE_EXCHANGE_CANDIDATE"] == expected_overrides and
            labels["RECEIPT_CHECKED_SALE_CANDIDATE"] == expected_receipts,
            f"{kind}: AO/AN reference not visible in expected view")
    hist = am["historical_primary"]
    require(all(row["accepted_financial_value"] is None for row in hist) and
            not set(row["registry_id"] for row in hist) & set(prior_ids),
            "historical primary accepted value or overlap differs")
    fingerprint = hashlib.sha256(json.dumps(
        {"policy": POLICY, "view": kind,
         "sources": {k: v["sha256"] for k, v in sources.items()}},
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"project": "AxieOS", "version": "0.14", "task": "136AP",
            "view": kind, "policy_version": POLICY,
            "input_fingerprint_sha256": fingerprint, "sources": sources,
            "coverage": {"combined_unique_references": len(registry),
                         "historical_primary": len(hist), "cached_context": len(context),
                         "fungible_overrides_visible": labels["FUNGIBLE_EXCHANGE_CANDIDATE"],
                         "receipt_checked_sales_visible": labels["RECEIPT_CHECKED_SALE_CANDIDATE"],
                         "closed_axie_flows_without_receipt_check": 26},
            "historical_primary": hist, "cached_unaccepted_context": context,
            "accepted_totals": am["accepted_totals"], "database_opened": False,
            "database_writes": 0, "network_calls": 0, "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    return "\n".join([
        f"# AxieOS V0.14 — Task136AP {report['view'].title()} annotated view", "",
        f"Combined references: **{c['combined_unique_references']}**; historical primary: "
        f"**{c['historical_primary']}**; cached context: **{c['cached_context']}**.", "",
        f"Fungible WETH/SLP overrides visible here: **{c['fungible_overrides_visible']}**. "
        f"Saved receipt checked Axie sale visible here: **{c['receipt_checked_sales_visible']}**. "
        "Other closed Axie flows without receipt checks: **26**.", "",
        "The receipt verifies one sale net transfer, not its profit. The fungible "
        "overlay is a review label. Historical and cached source IDs are preserved; "
        "cached references can appear in several views and must not be summed across them.", "",
        "Verified income, expenses, profit, portfolio value, and PHP recovery: **UNKNOWN**.", "",
        "Database opened: NO | Writes: 0 | Network: 0", "",
        "VALIDATION: PASS (offline evidence annotations only; Checkpoint 96 OPEN).", ""])


def save(report: dict, directory: Path) -> tuple[Path, Path, bool]:
    directory.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AP_" + report["view"].title() +
            "_Annotated_" + report["input_fingerprint_sha256"][:16])
    jp, mp = directory / (stem + ".json"), directory / (stem + ".md")
    fresh = not jp.exists()
    for path, content in ((jp, json.dumps(report, ensure_ascii=False, indent=2,
                                          sort_keys=True) + "\n"), (mp, markdown(report))):
        if path.exists():
            require(path.read_text(encoding="utf-8") == content,
                    f"{path}: existing report differs; inspect instead of overwriting")
        else:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(content)
    return jp, mp, fresh


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("ak", "an", "ao"):
        parser.add_argument("--" + key, type=Path)
        parser.add_argument("--" + key + "-dir", type=Path,
                            default=Path("reports/axieos_v014/task136" + key))
    parser.add_argument("--am-dir", type=Path, default=Path("reports/axieos_v014/task136am"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136ap"))
    args = parser.parse_args()
    paths = {"136" + k.upper(): getattr(args, k) or
             latest(getattr(args, k + "_dir"), "136" + k.upper())
             for k in ("ak", "an", "ao")}
    docs, shas = {}, {}
    for key, path in paths.items():
        docs[key], shas[key] = load(path)
    views = am_views(args.am_dir, shas["136AK"])
    print("AXIEOS V0.14 - TASK136AP - EVIDENCE ANNOTATED FINANCE VIEWS")
    for kind in VIEWS:
        path, am, sha = views[kind]
        sources = {k: {"filename": paths[k].name, "sha256": shas[k]} for k in paths}
        sources["136AM"] = {"filename": path.name, "sha256": sha}
        report = build(docs["136AK"], am, docs["136AN"], docs["136AO"], kind, sources)
        jp, mp, _ = save(report, args.output_dir)
        c = report["coverage"]
        print(f"{kind.upper()}: historical {c['historical_primary']} | cached "
              f"{c['cached_context']} | fungible {c['fungible_overrides_visible']} | "
              f"receipt {c['receipt_checked_sales_visible']} | {jp} | {mp}")
    print("Verified financial totals: UNKNOWN | Database opened: NO | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (offline evidence annotations only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
