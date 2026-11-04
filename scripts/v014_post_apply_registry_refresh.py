r"""Task136AK: refresh the combined source registry after guarded ledger apply.

From the AxieOS repository root:
    py -B .\scripts\v014_post_apply_registry_refresh.py

Reads Task136AA, AF, AG, AI, AJ and W reports only. Re-keys no historical
references, creates no new financial events, and makes no SQLite or network
calls. Task136W's pre-apply ledger absence is retained as historical context.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError("STOP: " + reason)


def load(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing report: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def find(directory: Path, task: str, schema: str | None = None) -> Path:
    found = []
    for p in directory.glob("*.json") if directory.is_dir() else []:
        d, _ = load(p)
        if d.get("task") == task and (schema is None or
                                          d.get("report_schema_version") == schema):
            found.append((d.get("created_at_utc", ""), p))
    require(found, f"no Task{task} JSON in {directory}; pass its exact path")
    return max(found)[1]


def indexed(rows: list[dict], field: str, label: str) -> dict[str, dict]:
    result = {str(r[field]).lower(): r for r in rows}
    require(len(result) == len(rows) and all(result), f"{label}: duplicate or empty key")
    return result


def build(d: dict[str, dict], paths: dict[str, Path], shas: dict[str, str]) -> dict:
    aa, af, ag, ai, aj, w = (d[k] for k in ("136AA", "136AF", "136AG", "136AI", "136AJ", "136W"))
    require(all(d[k].get("task") == k for k in d) and
            all(d[k].get("checkpoint96") == "OPEN" for k in
                ("136AF", "136AG", "136AI", "136AJ", "136W")) and
            w.get("report_schema_version") == "1.1" and
            aa.get("validation", {}).get("status") == "PASS_OFFLINE_COMBINED_REGISTRY_ONLY" and
            aa["validation"].get("checkpoint96_closed") is False,
            "source task, schema, or checkpoint changed")
    require(all(d[k].get("accepted_financial_totals") is None for k in
                ("136AF", "136AG", "136AI", "136AJ", "136W")) and
            all(v is None for v in aa["accepted_totals"].values()),
            "accepted financial totals changed")
    require(ag["source_task136af_sha256"] == shas["136AF"] and
            ag["source_task136af_filename"] == paths["136AF"].name and
            af["source_w"] == paths["136W"].name and
            ai["sources"]["136W"]["sha256"] == shas["136W"] and
            aj["sources"]["136W"]["sha256"] == shas["136W"] and
            aj["sources"]["136AI"]["sha256"] == shas["136AI"],
            "source report chain differs")
    raw = indexed(w["candidate_rows"], "txhash", "cached raw")
    shadow = indexed(ag["candidates"], "txhash", "shadow candidates")
    controls = indexed(ai["new_candidates"], "txhash", "payment route controls")
    require(len(raw) == w["coverage"]["candidate_hashes"] ==
            aa["coverage"]["new_cached_hashed_references"] and
            len(shadow) == ag["coverage"]["guarded_hashes"] == af["coverage"]["inserted_hashes_exact"] and
            len(controls) == ai["coverage"]["new_marketplace_shaped_pairs"],
            "raw, shadow or payment route coverage differs")
    require(set(shadow).issubset(raw) and set(controls).issubset(shadow) and
            set(controls) == {h for h, r in shadow.items() if r["legacy_label"] in
                              ("MARKETPLACE_BUY", "MARKETPLACE_SALE")},
            "marketplace shadow and counterparty sets differ")
    remainder = set(raw) - set(shadow)
    tx_only = {h for h, r in raw.items() if not r["raw_transfer_rows"]}
    quarantine = remainder - tx_only
    require(not set(shadow) & tx_only and len(remainder) == af["coverage"]["remaining_without_ledger"] and
            len(tx_only) == af["coverage"]["transaction_only_remaining"] and
            len(quarantine) == af["coverage"]["quarantined_remaining"] and
            all(raw[h]["raw_transfer_rows"] for h in quarantine),
            "post-apply ledger gap differs from Task136AF")
    flows = aj["closed_flow_candidates"]
    require(len(flows) == aj["coverage"]["closed_cached_axie_sequences"],
            "Task136AJ closed-flow count differs")
    flow_hashes = set()
    for f in flows:
        for key in ("purchase_hash", "sale_hash"):
            h = str(f[key]).lower()
            require(h in controls and controls[h]["review_lane"] == "AXIE_PAIR_CANDIDATE" and
                    h not in flow_hashes, "closed-flow hash missing, duplicated, or not Axie")
            flow_hashes.add(h)
    original = aa["registry_rows"]
    require(len(original) == aa["coverage"]["combined_references"] and
            len({r["registry_id"] for r in original}) == len(original),
            "Task136AA combined references missing or duplicated")
    historic, cached = [], []
    for row in original:
        r = dict(row)
        if r.get("origin") != "TASK136Z_CACHED_RAW":
            r["post_apply_ledger_status"] = "HISTORICAL_NOT_REASSESSED"
            r["post_apply_accounting_status"] = "HISTORICAL_SOURCE_PRESERVED"
            historic.append(r)
            continue
        h = str(r.get("txhash") or "").lower()
        require(h in raw and r["registry_id"] == "CACHED_RAW:" + h and
                r.get("accepted_financial_value") is None,
                "Task136AA cached reference differs from raw hash")
        if h in shadow:
            s = shadow[h]
            require(s["accounting_treatment"] == "UNREVIEWED_CANDIDATE", "shadow accepted treatment")
            r["post_apply_ledger_status"] = "MATERIALIZED_GUARDED"
            r["candidate_legacy_label"] = s["legacy_label"]
            r["candidate_movement_shape"] = s["shape"]
        elif h in tx_only:
            r["post_apply_ledger_status"] = "TRANSACTION_ONLY_NO_LEDGER"
        else:
            r["post_apply_ledger_status"] = "QUARANTINED_TRANSFER_NO_LEDGER"
        r["post_apply_accounting_status"] = "NO_STORED_ACCOUNTING"
        r["candidate_payment_route_status"] = controls[h]["control_status"] if h in controls else None
        r["candidate_review_lane"] = controls[h]["review_lane"] if h in controls else None
        r["linked_closed_axie_flow"] = h in flow_hashes
        cached.append(r)
    require(len(historic) == aa["coverage"]["historical_references"] and
            len(cached) == len(raw) and {r["txhash"].lower() for r in cached} == set(raw),
            "historical/cached registry partition differs")
    result = historic + cached
    require(len(result) == len(original) and
            [r["registry_id"] for r in result] == [r["registry_id"] for r in original] and
            all(r.get("accepted_financial_value") is None for r in result),
            "registry identity/order/value changed")
    status_counts = Counter(r["post_apply_ledger_status"] for r in cached)
    require(status_counts == {"MATERIALIZED_GUARDED": len(shadow),
                              "TRANSACTION_ONLY_NO_LEDGER": len(tx_only),
                              "QUARANTINED_TRANSFER_NO_LEDGER": len(quarantine)},
            "post-apply status count differs")
    return {"project": "AxieOS", "version": "0.14", "task": "136AK",
            "sources": {k: {"filename": paths[k].name, "sha256": shas[k]}
                        for k in sorted(paths)},
            "coverage": {"historical_references": len(historic),
                         "historical_unhashed_references": aa["coverage"]["historical_unhashed_references"],
                         "cached_references": len(cached), "combined_references": len(result),
                         "cached_ledger_statuses": dict(sorted(status_counts.items())),
                         "cached_accounting_absent": len(cached),
                         "legacy_candidate_labels": dict(sorted(Counter(
                             r["candidate_legacy_label"] for r in cached
                             if r.get("candidate_legacy_label")).items())),
                         "payment_route_statuses": dict(sorted(Counter(
                             r["candidate_payment_route_status"] for r in cached
                             if r.get("candidate_payment_route_status")).items())),
                         "closed_axie_flow_hash_references": len(flow_hashes),
                         "closed_axie_flow_pairs": len(flows)},
            "registry_rows": result,
            "source_snapshot_note": "Task136W and Task136AA predate the ledger apply; their no-ledger fields are historical snapshots.",
            "accepted_financial_totals": None, "database_opened": False,
            "database_writes": 0, "network_calls": 0, "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136AK Post-apply combined registry", "",
             f"Source references: **{c['combined_references']}** = "
             f"**{c['historical_references']}** historical + **{c['cached_references']}** cached. "
             "Registry IDs and original order are preserved.", "",
             "| Current cached ledger state | Hashes |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in c["cached_ledger_statuses"].items()]
    lines += ["", "| Candidate payment route | Hashes |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in c["payment_route_statuses"].items()]
    lines += ["", f"Cached hashes without stored accounting: **{c['cached_accounting_absent']}**. "
              f"Linked closed Axie flow references: **{c['closed_axie_flow_hash_references']}** "
              f"across **{c['closed_axie_flow_pairs']}** same-ID pairs.", "",
              report["source_snapshot_note"], "",
              "All labels and pair links remain evidence candidates. Historical unhashed "
              "capital references and raw activity after the cache cutoff remain unresolved. "
              "Verified income, expenses, profit, and PHP recovery: **UNKNOWN**.", "",
              "Database opened: NO | Writes: 0 | Network: 0", "",
              "VALIDATION: PASS (post-apply registry status refresh only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for task in ("aa", "af", "ag", "ai", "aj", "w"):
        parser.add_argument("--" + task, type=Path)
        parser.add_argument("--" + task + "-dir", type=Path,
                            default=Path("reports/axieos_v014/task136" + task))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136ak"))
    args = parser.parse_args()
    paths = {"136" + t.upper(): getattr(args, t) or find(getattr(args, t + "_dir"),
             "136" + t.upper(), "1.1" if t == "w" else None)
             for t in ("aa", "af", "ag", "ai", "aj", "w")}
    docs, shas = {}, {}
    for key, path in paths.items():
        docs[key], shas[key] = load(path)
    report = build(docs, paths, shas)
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AK_Post_Apply_Combined_Registry_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136AK - POST-APPLY COMBINED REGISTRY")
    print(f"Historical/cached/combined: {c['historical_references']}/{c['cached_references']}/"
          f"{c['combined_references']}")
    print(f"Cached ledger states: {c['cached_ledger_statuses']} | Accounting absent: "
          f"{c['cached_accounting_absent']}")
    print(f"Route statuses: {c['payment_route_statuses']} | Closed Axie pairs: "
          f"{c['closed_axie_flow_pairs']}")
    print("Verified income, expenses, profit, and PHP recovery: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (post-apply registry status refresh only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
