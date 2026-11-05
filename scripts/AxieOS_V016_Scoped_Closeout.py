r"""Close the 26-pair Axie trade evidence milestone without accepting profit.

Save this single file in scripts/ and run from the AxieOS repository root:
    py -B .\scripts\AxieOS_V016_Scoped_Closeout.py

Reads only the completed V0.16 closed-trade report and its exact SHA-matched
Task136BN source. No database or network access. Produces JSON and Markdown
under reports/axieos_v016/scoped_closeout/.
"""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

WALLET = "0x1ed8b3f3bd6a624de47f81beea101f0d15cdfbc8"
SCALE = Decimal(10) ** 18


def require(ok, message):
    if not ok:
        raise ValueError("STOP: " + message)


def load(path):
    require(path.is_file(), f"missing file: {path}")
    data = path.read_bytes()
    doc = json.loads(data.decode("utf-8-sig"))
    require(isinstance(doc, dict), f"invalid report object: {path}")
    return doc, hashlib.sha256(data).hexdigest()


def latest_complete(directory):
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        try:
            doc, digest = load(path)
        except (ValueError, OSError, UnicodeError):
            continue
        if doc.get("task") == "CLOSED_TRADE_EVIDENCE" and doc.get("version") == "0.16" and \
                doc.get("coverage", {}).get("complete") is True:
            matches.append((doc.get("created_at_utc", ""), path.name, path, doc, digest))
    require(bool(matches), f"complete V0.16 closed-trade JSON absent in {directory}")
    _, _, path, doc, digest = max(matches)
    return path, doc, digest


def match_source(directory, digest):
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        if hashlib.sha256(path.read_bytes()).hexdigest() == digest:
            doc, _ = load(path)
            if doc.get("task") == "136BN":
                matches.append((path, doc))
    require(len(matches) == 1, f"exact Task136BN source not found in {directory}")
    return matches[0]


def amount(value, label):
    require(isinstance(value, str) and value and not value.strip().startswith(("-", "+")),
            f"{label}: invalid unsigned amount")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("STOP: " + label + ": invalid decimal") from exc
    require(result.is_finite() and result >= 0, f"{label}: invalid decimal")
    return result


def raw_fee(tx, label):
    fee = tx.get("fee")
    require(isinstance(fee, str) and fee.isdecimal(), f"{label}: raw gas fee absent")
    result = int(fee)
    require(result >= 0, f"{label}: invalid raw gas fee")
    return result


def analyze(report, bn):
    coverage = report["coverage"]
    require(report.get("database_opened") is False and report.get("database_writes") == 0 and
            report.get("checkpoint96") == "OPEN" and report.get("unified_finance") == "HOLD" and
            report.get("accepted_financial_totals") is None and
            report.get("verified_profit_php") is None and
            coverage.get("target_closed_flows") == 26 and
            coverage.get("attempted") == coverage.get("both_sides_correlated") == 26 and
            coverage.get("unattempted") == 0 and
            coverage.get("historical_sale_basis_conflicts_separate") == 24 and
            report.get("network_calls_attempted") == 52,
            "V0.16 evidence coverage or acceptance boundary differs")
    require(bn.get("task") == "136BN" and bn.get("checkpoint96") == "OPEN" and
            bn.get("accepted_financial_totals") is None and
            bn.get("independent_receipts_verified_by_this_report") == 0 and
            bn.get("coverage", {}).get("complete") is True and
            bn.get("coverage", {}).get("explorer_correlated") == 26,
            "Task136BN acceptance boundary differs")
    sales = bn["sale_checks"]
    checks = report["closed_trade_checks"]
    require(len(checks) == len(sales) == 26, "pair count differs")
    sale_by_hash = {s["sale_hash"].lower(): s for s in sales}
    require(len(sale_by_hash) == 26 and len({s["purchase_hash"].lower() for s in sales}) == 26,
            "duplicate source transaction hash")
    pairs, seen_purchases, purchase_fee_raw = [], set(), 0
    observed_delta = Decimal(0)
    signs = Counter()
    for row in checks:
        h, sh = row["purchase_hash"].lower(), row["sale_hash"].lower()
        require(h not in seen_purchases and sh in sale_by_hash and
                row.get("status") == "PURCHASE_AND_SALE_TRANSFERS_CORROBORATED" and
                row.get("accepted_financial_value") is None and
                len(row.get("transaction_sha256", "")) == 64 and
                len(row.get("transfers_sha256", "")) == 64,
                f"{h}: pair identity or status differs")
        seen_purchases.add(h)
        s = sale_by_hash[sh]
        e = row["evidence"]
        se = s["evidence"]
        purchase = e["purchase_transaction"]
        sale = se["normalized_transaction"]
        require(row["axie_id"] == s["axie_id"] and h == s["purchase_hash"].lower() and
                s.get("status") == "EXPLORER_PAIR_CORROBORATED" and
                s.get("accepted_financial_value") is None and
                e.get("accepted_profit") is None and
                e.get("gas_expense_accepted") is None and
                e.get("independent_receipt_verified") is False and
                se.get("independent_receipt_verified") is False and
                purchase.get("tx_hash", "").lower() == h and
                sale.get("tx_hash", "").lower() == sh and
                purchase.get("status") == sale.get("status") == "ok" and
                str(purchase.get("from_address") or "").lower() == WALLET and
                str(sale.get("from_address") or "").lower() != WALLET,
                f"{h}: pair/fee payer/acceptance evidence differs")
        out = amount(e["purchase_weth_out_observed"], h + " purchase WETH")
        net = amount(e["sale_weth_net_in_observed"], h + " sale WETH")
        delta = Decimal(e["wallet_weth_difference_before_gas"])
        require(delta.is_finite() and out > 0 and net > 0 and delta == net - out and
                net == amount(se["explorer_weth_net_to_wallet"], sh + " explorer sale") and
                net == amount(s["cached_wallet_net_weth"], sh + " cached sale") and
                e["purchase_utc"] < e["sale_utc"],
                f"{h}: observed WETH or time sequence differs")
        fee = raw_fee(purchase, h)
        raw_fee(sale, sh)
        purchase_fee_raw += fee
        observed_delta += delta
        signs["POSITIVE" if delta > 0 else "NEGATIVE" if delta < 0 else "ZERO"] += 1
        pairs.append({"axie_id": row["axie_id"], "purchase_hash": h, "sale_hash": sh,
                      "purchase_weth_out_observed": str(out),
                      "sale_weth_net_in_observed": str(net),
                      "wallet_weth_difference_before_gas": str(delta),
                      "purchase_tx_from_wallet": True,
                      "purchase_gas_raw_candidate": str(fee),
                      "purchase_gas_ron_candidate": str(Decimal(fee) / SCALE),
                      "sale_tx_from_wallet": False,
                      "sale_gas_attributed_to_wallet": None,
                      "accepted_profit": None, "accepted_gas_expense": None})
    require(len(seen_purchases) == 26 and set(sale_by_hash) == {r["sale_hash"] for r in pairs} and
            observed_delta == Decimal(report["observed_weth_wallet_difference_before_gas_for_correlated"]) and
            dict(signs) == coverage["difference_signs_for_correlated"],
            "aggregate source totals or coverage differ")
    return {"pair_count": 26, "purchase_tx_sender_wallet": 26,
            "sale_tx_sender_external": 26,
            "observed_weth_difference_before_gas": str(observed_delta),
            "purchase_gas_raw_candidate": str(purchase_fee_raw),
            "purchase_gas_ron_candidate": str(Decimal(purchase_fee_raw) / SCALE),
            "difference_signs": dict(signs), "pairs": pairs}


def run(evidence_dir, bn_dir, output_dir):
    ep, evidence, esha = latest_complete(evidence_dir)
    digest = evidence["sources"]["136BN"]["sha256"]
    bp, bn = match_source(bn_dir, digest)
    require(evidence["sources"]["136BN"]["filename"] == bp.name,
            "V0.16 source filename differs")
    view = analyze(evidence, bn)
    report = {"project": "AxieOS", "version": "0.16", "task": "SCOPED_CLOSED_TRADE_CLOSEOUT",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "sources": {"V016_CLOSED_TRADE_EVIDENCE": {"filename": ep.name, "sha256": esha},
                          "136BN": {"filename": bp.name, "sha256": digest}},
              "scope_status": "COMPLETE_FOR_REPOSITORY_REVIEW",
              "gas_fee_interpretation": "CANDIDATE_RAW_FEE_DIVIDED_BY_1E18_RON",
              "coverage": {k: v for k, v in view.items() if k != "pairs"},
              "closed_trade_cases": view["pairs"],
              "accepted_income": None, "accepted_expenses": None,
              "accepted_profit": None, "verified_php_recovery": None,
              "unified_finance": "HOLD", "checkpoint96": "OPEN",
              "database_opened": False, "database_writes": 0, "network_calls": 0}
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V016_Scoped_Closeout_" + datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6]
    jp, mp = output_dir / (stem + ".json"), output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as out:
        json.dump(report, out, indent=2)
        out.write("\n")
    mp.write_text("\n".join([
        "# AxieOS V0.16 — Scoped closed-trade evidence closeout", "",
        "**Scope:** 26 linked Axie purchase/sale transactions. The purchase and sale token transfers "
        "are corroborated by explorer evidence; the two source reports are hash linked.", "",
        f"- Observed aggregate wallet WETH difference before gas: "
        f"**{view['observed_weth_difference_before_gas']} WETH**.",
        f"- Purchase transaction senders: wallet **26/26**. Candidate purchase transaction "
        f"gas: **{view['purchase_gas_ron_candidate']} RON**, derived from raw explorer "
        "fee fields divided by 10^18; not accepted as a portfolio expense.",
        "- Sale transaction senders: external **26/26**. No sale transaction gas is assigned "
        "to this wallet by these records.", "- Separate historical sale basis conflicts: **24**.", "",
        "The WETH difference is a scoped wallet-flow observation, not accepted realized profit. "
        "RON gas is a separate asset and is not subtracted from WETH without supported conversion. "
        "Independent receipt acceptance, historical basis coverage, complete gas accounting and "
        "capital/PHP reconciliation remain open.", "",
        "**Scoped milestone: COMPLETE FOR REPOSITORY REVIEW.** Unified Finance: **HOLD**; "
        "Checkpoint 96: **OPEN**. Verified all-time income, expenses, profit and PHP recovery: "
        "**UNKNOWN**.", "",
        f"Sources: `{ep.as_posix()}` and `{bp.as_posix()}` (SHA-256 linked).", "",
        "Database opened: NO | Writes: 0 | Network calls: 0", ""]), encoding="utf-8")
    print("AXIEOS V0.16 - SCOPED CLOSED-TRADE CLOSEOUT")
    print("Pairs: 26/26 | Purchase sender wallet: 26 | Sale sender external: 26")
    print(f"Observed WETH difference before gas: {view['observed_weth_difference_before_gas']}")
    print(f"Candidate purchase gas: {view['purchase_gas_ron_candidate']} RON (not accepted expense)")
    print(f"Reports: {jp} {mp}")
    print("Scoped milestone: COMPLETE FOR REPOSITORY REVIEW | Unified Finance: HOLD | Checkpoint 96: OPEN")
    print("Verified all-time profit and PHP recovery: UNKNOWN | Database opened: NO | Writes: 0 | Network: 0")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path,
                        default=Path("reports/axieos_v016/closed_trades"))
    parser.add_argument("--bn-dir", type=Path,
                        default=Path("reports/axieos_v014/task136bn"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("reports/axieos_v016/scoped_closeout"))
    args = parser.parse_args()
    run(args.evidence_dir, args.bn_dir, args.output_dir)


if __name__ == "__main__":
    main()
