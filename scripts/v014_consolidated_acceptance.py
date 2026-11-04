r"""Task136BP: one offline acceptance review for the V0.14 evidence milestone.

Run from the AxieOS repository root:
    py -B .\scripts\v014_consolidated_acceptance.py

Reads saved reports only. Verifies source hashes, the four scoped evidence
views, 26 Axie sale and 26 CocoChoco purchase explorer matches, and all 24
stored FIFO candidates. Never opens SQLite, contacts a network, changes
accounting, or promotes an unverified financial amount to an accepted total.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4


def require(ok, message):
    if not ok:
        raise ValueError("STOP: " + message)


def read(path):
    require(path.is_file(), f"missing source {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def latest(folder, task):
    found = []
    for path in folder.glob("*.json") if folder.is_dir() else []:
        doc, sha = read(path)
        if doc.get("task") == task:
            found.append((str(doc.get("created_at_utc", "")), path, doc, sha))
    require(found, f"missing Task{task} in {folder}")
    _, path, doc, sha = max(found)
    return path, doc, sha


def linked(folder, task, sha):
    matches = []
    for path in folder.glob("*.json") if folder.is_dir() else []:
        if hashlib.sha256(path.read_bytes()).hexdigest() == sha:
            doc, actual = read(path)
            if doc.get("task") == task or doc.get("checkpoint") == task:
                matches.append((path, doc, actual))
    require(len(matches) == 1, f"expected one SHA-linked Task{task} in {folder}")
    return matches[0]


def ref(path, sha):
    return {"filename": path.name, "sha256": sha}


def linked_views(folder, bl):
    refs = bl.get("view_sources", {})
    require(set(refs) == {"income", "expense", "capital", "portfolio"},
            "four Task136BG view references missing in Task136BL")
    result = {}
    for name in refs:
        path, doc, sha = linked(folder, "136BG", refs[name]["sha256"])
        require(doc.get("view") == name and doc.get("checkpoint96") == "OPEN" and
                all(v is None for v in doc.get("accepted_totals", {}).values()),
                f"{name}: scoped evidence view identity or accepted totals differ")
        result[name] = (path, doc, sha)
    return result


def fifo_candidates(bv, bo, bm):
    D = Decimal
    queue = [r for r in bm["review_queue"] if r["review_lane"] == "SALE_BASIS_CONFLICT"]
    hashes = {str(r["txhash"]).lower() for r in queue}
    require(len(queue) == len(hashes) == 24, "24 basis queue identities changed")
    checks = {str(r["txhash"]).lower(): r for r in bo["purchase_checks"]}
    require(len(checks) == 26 and all(r["status"] == "EXPLORER_PURCHASE_CORROBORATED"
                                     for r in checks.values()), "purchase checks incomplete")
    rows = [r for r in bv["tables"]["blockchain_accounting_records"]["rows"]
            if r.get("asset_name") == "Axie Consumable Item" and
            str(r.get("asset_token_id")) in ("1", "2")]
    rows.sort(key=lambda r: (str(r["datetime"]), str(r["txhash"])))
    economic = {}
    for row in bv["tables"]["blockchain_economic_events"]["rows"]:
        economic.setdefault(str(row["txhash"]).lower(), []).append(row)
    pools = {"1": [], "2": []}
    cases = []
    for row in rows:
        q = D(str(row["quantity"]))
        if q <= 0:
            continue
        tid, h = str(row["asset_token_id"]), str(row["txhash"]).lower()
        if row["direction"] == "IN":
            paid = row["event_type"] == "ASSET_PURCHASE" and row["gross_amount"] is not None
            if paid:
                require(h in checks and checks[h]["token_id"] == tid and
                        D(checks[h]["observed_weth_out"]) == D(str(row["gross_amount"])) and
                        D(checks[h]["observed_quantity_in"]) == q,
                        f"{h}: purchased lot differs from explorer")
            pools[tid].append({"hash": h, "event": row["event_type"],
                               "left": q, "unit": D(str(row["gross_amount"])) / q if paid else None})
            continue
        if row["direction"] != "OUT":
            continue
        left, subtotal, segments = q, D(0), []
        for lot in pools[tid]:
            take = min(lot["left"], left)
            if take <= 0:
                continue
            lot["left"] -= take
            left -= take
            component = take * lot["unit"] if lot["unit"] is not None else None
            if component is not None:
                subtotal += component
            segments.append({"purchase_hash": lot["hash"], "quantity": str(take),
                             "source_event": lot["event"],
                             "candidate_weth_cost": str(component) if component is not None else None})
            if not left:
                break
        if h not in hashes:
            continue
        match = (row["event_type"] == "ASSET_SALE" and row["accounting_status"] == "READY" and
                 row["cost_basis"] is not None and row["realized_pl"] is not None and
                 left == 0 and segments and
                 all(s["source_event"] == "ASSET_PURCHASE" and
                     s["purchase_hash"] in checks for s in segments) and
                 subtotal == D(str(row["cost_basis"])) and
                 D(str(row["net_amount"])) - subtotal == D(str(row["realized_pl"])))
        ev = economic.get(h, [])
        require(len(ev) == 1 and ev[0]["cost_basis"] is None and
                ev[0]["realized_pl"] is None,
                f"{h}: economic comparison no longer defers basis and profit")
        cases.append({"sale_hash": h, "token_id": tid, "sale_quantity": str(q),
                      "candidate_cost_basis_weth": str(subtotal) if match else None,
                      "stored_basis_matches_model": bool(match),
                      "purchase_lot_segments": segments,
                      "economic_cost_basis_deferred": True,
                      "accepted_cost_basis": None, "accepted_profit": None,
                      "limitation": "Pre-visible opening lots and cost are unknown; accounting-only FIFO order is conditional"})
    require(len(cases) == 24 and all(c["stored_basis_matches_model"] for c in cases),
            "24 disputed stored bases do not reproduce from corroborated purchase lots")
    return cases


def audit(root):
    v14 = root / "reports/axieos_v014"
    cp = root / "reports/axieos_v013/checkpoint96"
    bp, bm, bsha = latest(v14 / "task136bm", "136BM")
    np, bn, nsha = latest(v14 / "task136bn", "136BN")
    op, bo, osha = latest(v14 / "task136bo", "136BO")
    require(bn["sources"]["136BM"]["sha256"] == bsha and
            bn["coverage"]["explorer_correlated"] ==
                bn["coverage"]["attempted"] == bn["coverage"]["target_sale_candidates"] == 26 and
            bn["coverage"]["complete"] is True and
            bo["coverage"]["corroborated"] ==
                bo["coverage"]["attempted"] == bo["coverage"]["stored_purchases"] == 26 and
            bo["wallet_transfer_history"]["stop_reason"] == "EXPLORER_PAGINATION_END",
            "Task136BN/BO cohort or source mismatch")
    blp, bl, blsha = linked(v14 / "task136bl", "136BL",
                           bm["source_reports"]["136BL"]["sha256"])
    bfp, bf, bfsha = linked(v14 / "task136bf", "136BF",
                           bm["source_reports"]["136BF"]["sha256"])
    ap, aj, ajsha = linked(v14 / "task136aj", "136AJ",
                          bn["sources"]["136AJ"]["sha256"])
    vp, bv, bvsha = linked(cp, "96BV", bo["sources"]["96BV"]["sha256"])
    fp, f, fsha = linked(v14 / "task136f", "136F",
                         bo["sources"]["136F"]["sha256"])
    require(ajsha == bm["source_reports"]["136AJ"]["sha256"] and
            bl.get("release_state") == "SCOPED_EVIDENCE_READY_FOR_REVIEW" and
            bl.get("full_finance_closeout") is False and
            bl["sources"]["136BF"]["sha256"] == bfsha and
            bf["coverage"]["combined_references"] ==
                bm["coverage"]["combined_references"] == 1339 and
            len(bf["registry_rows"]) == 1339 and
            f.get("accepted_opening_balance") is None and
            bo["accepted_opening_balance"] is None,
            "scoped evidence report chain or opening inventory state differs")
    views = linked_views(v14 / "task136bg", bl)
    require(all(doc["sources"]["136BF"]["sha256"] == bfsha and
                doc["coverage"]["combined_unique_references"] == 1339
                for _, doc, _ in views.values()),
            "four scoped views do not cover Task136BF registry")
    sale_checks = bn["sale_checks"]
    sale_hashes = {str(c["sale_hash"]).lower() for c in sale_checks}
    queued = {str(q["sale_hash"]).lower() for q in bm["review_queue"]
              if q["review_lane"] == "AXIE_CLOSED_FLOW_RECEIPT"}
    require(len(sale_hashes) == len(queued) == 26 and sale_hashes == queued and
            all(c["status"] == "EXPLORER_PAIR_CORROBORATED" and
                c.get("accepted_financial_value") is None for c in sale_checks),
            "26 Axie sale explorer checks differ from queue")
    queue_counts = Counter(q["review_lane"] for q in bm["review_queue"])
    require(queue_counts == {"SALE_BASIS_CONFLICT": 24,
                             "AXIE_CLOSED_FLOW_RECEIPT": 26,
                             "RECENT_DETAIL_REVIEW": 22} and
            bm["coverage"]["detail_candidate_label_changes"] == 0,
            "Task136BM review queue changed")
    cases = fifo_candidates(bv, bo, bm)
    earliest = bo["wallet_transfer_history"]["earliest_explorer_aci"]
    first_raw = {str(g["token_id"]): g["first_raw_timestamp"]
                 for g in f["summary"]["contract_token_groups"]}
    require(set(earliest) == {"1", "2"} and
            all(earliest[i]["timestamp"] == first_raw[i] and
                str(earliest[i]["from_address"]).lower() == bo["owned_wallet"].lower() and
                str(earliest[i]["to_address"]).lower() ==
                    "0x0000000000000000000000000000000000000000"
                for i in ("1", "2")) and
            bo["wallet_transfer_history"]["aci_rows_older_than_saved_local_snapshot"] == {},
            "opening history boundary differs; inspect before closeout")
    for task, doc in (("136BM", bm), ("136BN", bn), ("136BO", bo),
                      ("136BL", bl), ("136BF", bf)):
        require(doc.get("checkpoint96") == "OPEN" and
                doc.get("accepted_financial_totals") is None,
                f"Task{task} financial boundary changed")
    require(all(row.get("accepted_financial_value") is None
                for row in bf["registry_rows"]), "registry contains accepted values")
    sources = {"136BM": ref(bp,bsha), "136BN": ref(np,nsha), "136BO": ref(op,osha),
               "136BL": ref(blp,blsha), "136BF": ref(bfp,bfsha),
               "136AJ": ref(ap,ajsha), "96BV": ref(vp,bvsha), "136F": ref(fp,fsha)}
    sources.update({"136BG_"+kind: ref(path,sha)
                    for kind,(path,_,sha) in views.items()})
    return {"project": "AxieOS", "version": "0.14", "task": "136BP",
            "decision": "SCOPED_EVIDENCE_READY_FOR_RELEASE_REVIEW",
            "planned_unified_finance_release": "HOLD",
            "checkpoint96": "OPEN", "sources": sources,
            "coverage": {"combined_registry_references": 1339,
                         "scoped_finance_views": 4,
                         "axie_sale_pairs_corroborated": 26,
                         "consumable_purchases_corroborated": 26,
                         "consumable_fifo_candidates_match_stored": len(cases),
                         "recent_detail_queue_unaccepted": 22,
                         "opening_history_pages": bo["wallet_transfer_history"]["pages_read"]},
            "earliest_visible_aci": earliest, "candidate_basis_review": cases,
            "release_boundaries": [
                "Pre-visible CocoChoco opening lots and their cost remain unknown",
                "Matching stored FIFO arithmetic does not prove which fungible units were sold",
                "Explorer sale pairs corroborate wallet net receipts, not independent gross, fee, basis or profit",
                "The four scoped views predate Tasks136BN and 136BO and contain no accepted totals",
                "Verified income, expense, realized profit, portfolio value and PHP capital recovery remain unknown",
                "Checkpoint96 remains OPEN; full V0.14 Unified Finance acceptance is HOLD"],
            "accepted_financial_totals": None, "database_opened": False,
            "database_writes": 0, "network_calls": 0,
            "created_at_utc": datetime.now(timezone.utc).isoformat()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--output-dir", type=Path,
                   default=Path("reports/axieos_v014/task136bp"))
    args = p.parse_args()
    report = audit(args.root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136BP_Consolidated_Acceptance_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
            "_" + uuid4().hex[:6])
    jp, mp = args.output_dir/(stem+".json"), args.output_dir/(stem+".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    c = report["coverage"]
    mp.write_text("\n".join([
        "# AxieOS V0.14 — Consolidated scoped finance acceptance", "",
        "**Decision:** Scoped evidence ready for release review. "
        "Planned Unified Finance release: **HOLD**. Checkpoint 96: **OPEN**.", "",
        f"Combined source references: **{c['combined_registry_references']}**; "
        f"scoped views: **{c['scoped_finance_views']}**.",
        f"Axie sale pairs: **{c['axie_sale_pairs_corroborated']}**; "
        f"CocoChoco purchases: **{c['consumable_purchases_corroborated']}**; "
        f"stored FIFO candidates reproduced: **{c['consumable_fifo_candidates_match_stored']}**.", "",
        "The first visible transfer of each CocoChoco token is an outgoing burn. "
        "Pre-visible opening inventory and basis remain unresolved.", "",
        "## Release boundaries", "",
        *["- " + item for item in report["release_boundaries"]], "",
        "Verified finance totals: **UNKNOWN**. Database opened: NO | Writes: 0 | Network: 0.", ""]),
        encoding="utf-8")
    print("AXIEOS V0.14 - TASK136BP - CONSOLIDATED SCOPED ACCEPTANCE")
    print(f"Registry: {c['combined_registry_references']} | Views: {c['scoped_finance_views']} | "
          f"Axie pairs: {c['axie_sale_pairs_corroborated']} | "
          f"CocoChoco purchases: {c['consumable_purchases_corroborated']} | "
          f"FIFO candidates: {c['consumable_fifo_candidates_match_stored']}")
    print("Scoped evidence: READY FOR RELEASE REVIEW | Unified Finance: HOLD")
    print("Verified totals: UNKNOWN | Checkpoint 96: OPEN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (linked evidence and conditional basis candidates only)")


if __name__ == "__main__":
    main()
