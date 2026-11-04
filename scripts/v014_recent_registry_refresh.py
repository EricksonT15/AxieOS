r"""Task136BF: append the recent raw cohort to the finance source registry.

Run from the AxieOS repository root:
    py -B .\scripts\v014_recent_registry_refresh.py

Reads SHA-linked Task136AK/AU/BB/BC/BD/BE JSON only. Preserves all prior
registry references and appends one unaccepted reference per new raw hash.
No SQLite, network, accounting, or accepted financial totals.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from v014_post_apply_reconcile import require
from v014_raw_import_clone import by_sha, latest, load


def indexed(rows: list[dict], key: str, label: str) -> dict[str, dict]:
    result = {str(row[key]).lower(): row for row in rows}
    require(len(result) == len(rows) and all(result),
            f"{label}: duplicate or empty identity")
    return result


def build(docs: dict[str, dict], shas: dict[str, str]) -> dict:
    ak, au, bb, bc, bd, be = (docs[t] for t in
                            ("136AK", "136AU", "136BB", "136BC", "136BD", "136BE"))
    require(all(docs[t].get("task") == t and docs[t].get("checkpoint96") == "OPEN"
                and docs[t].get("accepted_financial_totals") is None
                for t in docs) and
            all(be["sources"][t]["sha256"] == shas[t]
                for t in ("136BD", "136AU", "136BB")) and
            all(bd["sources"][t]["sha256"] == shas[t]
                for t in ("136BC", "136BB", "136AU")) and
            bc["sources"]["136BB"]["sha256"] == shas["136BB"] and
            bb["sources"]["136AU"]["sha256"] == shas["136AU"] and
            be.get("accepted_new_financial_events") == 0,
            "report source chain, checkpoint or finance acceptance differs")
    previous = ak["registry_rows"]
    require(len(previous) == ak["coverage"]["combined_references"] and
            len(previous) == ak["coverage"]["historical_references"] +
                ak["coverage"]["cached_references"] and
            len({r["registry_id"] for r in previous}) == len(previous) and
            all(r.get("accepted_financial_value") is None for r in previous),
            "prior registry count, identities or values changed")
    prior_hashes = {str(row["txhash"]).lower() for row in previous if row.get("txhash")}
    require(len(prior_hashes) + ak["coverage"]["historical_unhashed_references"] ==
            len(previous), "prior registry hash overlap or unhashed count differs")
    tx = indexed(au["normalized_new_transactions"], "tx_hash", "new transaction")
    transfers = au["normalized_new_transfers"]
    require(len(tx) == au["coverage"]["unique_transaction_rows"] and
            len(transfers) == au["coverage"]["unique_transfer_rows"] and
            len({str(row["transfer_key"]).lower() for row in transfers}) == len(transfers),
            "new raw identity or row counts differ")
    grouped = defaultdict(list)
    for row in transfers:
        grouped[str(row["tx_hash"]).lower()].append(row)
    recent = set(tx) | set(grouped)
    require(len(recent) == bc["coverage"]["recent_hashes"] +
                bb["coverage"]["transaction_only_hashes_still_omitted"] and
            not recent & prior_hashes and
            not {"RECENT_RAW:" + h for h in recent} &
                {str(row["registry_id"]) for row in previous},
            "recent hashes overlap prior references or cohort count differs")
    shadow = indexed(bc["candidates"], "txhash", "recent shadow")
    pairs = indexed(bd["candidate_pairs"], "txhash", "recent pairs")
    routes = indexed(be["new_candidates"], "txhash", "recent routes")
    require(set(shadow) == set(grouped) and
            len(shadow) == bb["coverage"]["inserted_hashes_exact"] and
            len(pairs) == bd["coverage"]["marketplace_shaped"] and
            set(pairs) == set(routes) and
            len(routes) == be["coverage"]["recent_exact_pairs"] and
            set(pairs) == {h for h, row in shadow.items() if row["legacy_label"] in
                           ("MARKETPLACE_BUY", "MARKETPLACE_SALE")} and
            len(set(tx) - set(grouped)) ==
                bb["coverage"]["transaction_only_hashes_still_omitted"],
            "ledger, shadow, payment pair or transaction-only sets differ")
    require(all(routes[h]["review_lane"] == pairs[h]["review_lane"] and
                routes[h]["shape"] == pairs[h]["shape"] for h in pairs) and
            sum(row["control_status"] == "FUNGIBLE_ROUTE_REVIEW" for row in routes.values())
                == sum(row["review_lane"] == "FUNGIBLE_EXCHANGE_REVIEW"
                       for row in pairs.values()),
            "route review lanes differ")
    added = []
    for h in sorted(recent):
        group = grouped.get(h, [])
        raw_tx = tx.get(h)
        stamps = [str(row["timestamp"]) for row in group]
        if raw_tx is not None:
            stamps.append(str(raw_tx["timestamp"]))
        require(stamps and all(stamps) and
                len({str(row["transfer_key"]) for row in group}) == len(group),
                f"{h}: raw timestamps or transfer identity missing")
        label = shadow.get(h)
        pair = pairs.get(h)
        route = routes.get(h)
        status = ("MATERIALIZED_GUARDED" if label else
                  "TRANSACTION_ONLY_NO_LEDGER")
        added.append({"registry_id": "RECENT_RAW:" + h,
                      "origin": "TASK136AU_RECENT_RAW",
                      "lane": "RECENT_SOURCE_CANDIDATE",
                      "accounting_key": None,
                      "txhash": h,
                      "date_as_stored": min(stamps),
                      "asset_as_stored": None,
                      "quantity_as_stored": None,
                      "gross_as_stored": None,
                      "source_status": None,
                      "evidence_status": "RAW_CANDIDATE_UNACCEPTED",
                      "accepted_financial_value": None,
                      "raw_transaction_count": 1 if raw_tx else 0,
                      "raw_transfer_count": len(group),
                      "token_symbols": sorted({str(row.get("token_symbol") or "UNKNOWN")
                                               for row in group}),
                      "post_apply_ledger_status": status,
                      "post_apply_accounting_status": "NO_STORED_ACCOUNTING",
                      "candidate_legacy_label": label["legacy_label"] if label else None,
                      "candidate_movement_shape": label["shape"] if label else None,
                      "candidate_review_lane": pair["review_lane"] if pair else None,
                      "candidate_payment_route_status":
                          route["control_status"] if route else None,
                      "classification_flags": label["flags"] if label else [],
                      "financial_treatment": "UNREVIEWED_CANDIDATE"})
    combined = list(previous) + added
    require(len(combined) == len(previous) + len(recent) and
            len({row["registry_id"] for row in combined}) == len(combined) and
            all(row.get("accepted_financial_value") is None for row in combined),
            "combined registry identity, coverage or finance value differs")
    statuses = Counter(row["post_apply_ledger_status"] for row in added)
    require(statuses == {"MATERIALIZED_GUARDED": len(shadow),
                         "TRANSACTION_ONLY_NO_LEDGER": len(recent) - len(shadow)},
            "recent ledger status counts differ")
    return {"project": "AxieOS", "version": "0.14", "task": "136BF",
            "sources": {task: {"sha256": shas[task]} for task in shas},
            "coverage": {"historical_references": ak["coverage"]["historical_references"],
                         "prior_cached_references": ak["coverage"]["cached_references"],
                         "recent_raw_hash_references": len(added),
                         "combined_references": len(combined),
                         "unique_hashed_references": len(prior_hashes | recent),
                         "historical_unhashed_references":
                             ak["coverage"]["historical_unhashed_references"],
                         "recent_ledger_statuses": dict(sorted(statuses.items())),
                         "recent_accounting_absent": len(added),
                         "recent_route_statuses": dict(sorted(Counter(
                             row["candidate_payment_route_status"] for row in added
                             if row["candidate_payment_route_status"]).items()))},
            "registry_rows": combined,
            "source_snapshot_note": "Task136AK predates the recent raw catch-up. Source references are not distinct accepted economic events.",
            "accepted_financial_totals": None,
            "database_opened": False, "database_writes": 0,
            "network_calls": 0, "checkpoint96": "OPEN"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for suffix in ("ak", "au", "bb", "bc", "bd", "be"):
        parser.add_argument(f"--{suffix}-dir", type=Path,
                            default=Path(f"reports/axieos_v014/task136{suffix}"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("reports/axieos_v014/task136bf"))
    args = parser.parse_args()
    paths = {"136BE": latest(args.be_dir, "136BE")}
    be, be_sha = load(paths["136BE"])
    for task in ("136BD", "136AU", "136BB"):
        paths[task] = by_sha(getattr(args, task[3:].lower() + "_dir"),
                              be["sources"][task]["sha256"], task)
    bd, bd_sha = load(paths["136BD"])
    paths["136BC"] = by_sha(args.bc_dir, bd["sources"]["136BC"]["sha256"], "136BC")
    paths["136AK"] = latest(args.ak_dir, "136AK")
    docs, shas = {}, {}
    for task, path in paths.items():
        docs[task], shas[task] = load(path)
    report = build(docs, shas)
    for task, path in paths.items():
        report["sources"][task]["filename"] = path.name
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136BF_Recent_Combined_Registry_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
            "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136BF Recent combined source registry", "",
             f"Historical references: **{c['historical_references']}**; prior cached "
             f"references: **{c['prior_cached_references']}**; recent raw hash "
             f"references: **{c['recent_raw_hash_references']}**; combined: "
             f"**{c['combined_references']}**.", "",
             "| Recent ledger state | Hashes |", "|---|---:|"]
    lines.extend(f"| {k} | {v} |" for k, v in c["recent_ledger_statuses"].items())
    lines += ["", "| Recent candidate payment route | Hashes |", "|---|---:|"]
    lines.extend(f"| {k} | {v} |" for k, v in c["recent_route_statuses"].items())
    lines += ["", report["source_snapshot_note"], "",
              "Verified income, expenses, profit and PHP recovery: **UNKNOWN**. "
              "Checkpoint 96: **OPEN**.", "",
              "Database opened: NO | Writes: 0 | Network: 0", ""]
    mp.write_text("\n".join(lines), encoding="utf-8")
    print("AXIEOS V0.14 - TASK136BF - RECENT COMBINED SOURCE REGISTRY")
    print(f"Historical/prior cached/recent/combined: "
          f"{c['historical_references']}/{c['prior_cached_references']}/"
          f"{c['recent_raw_hash_references']}/{c['combined_references']}")
    print(f"Recent ledger states: {c['recent_ledger_statuses']} | "
          f"Route statuses: {c['recent_route_statuses']}")
    print("Verified income, expenses, profit and PHP recovery: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (offline source registry only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
