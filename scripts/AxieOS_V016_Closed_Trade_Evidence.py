r"""One bounded V0.16 purchase-side crosswalk for 26 closed Axie flows.

Save this single file in scripts/ and run from repo root:
    py -B .\scripts\AxieOS_V016_Closed_Trade_Evidence.py

Reads the linked Task136AJ/BM/BN reports, checks each purchase transaction
and token-transfer page on the Ronin explorer, and joins it to the already
corroborated sale transfer. Reports a WETH wallet difference before gas only.
No accepted profit, PHP conversion, accounting write or database connection.
"""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

WALLET = "0x1ed8b3f3bd6a624de47f81beea101f0d15cdfbc8"
BASE = "https://explorer.roninchain.com/api/v2/transactions/"
WETH = "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5"
AXIE = "0x32950db2a7164ae833121501c797d79e7b79d74c"
MAX_BYTES = 1048576


def require(ok, reason):
    if not ok:
        raise ValueError("STOP: " + reason)


def load(path):
    require(path.is_file(), f"missing report: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def by_sha(directory, digest, task):
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        if hashlib.sha256(path.read_bytes()).hexdigest() == digest:
            doc, _ = load(path)
            if doc.get("task") == task:
                matches.append(path)
    require(len(matches) == 1, f"expected one SHA-matched Task{task} in {directory}")
    return matches[0]


def extract_address(value):
    return value.get("hash") if isinstance(value, dict) else value


def normalize_transaction(row):
    fee = row.get("fee")
    return {"tx_hash": row.get("hash"), "timestamp": row.get("timestamp"),
            "block_number": row.get("block_number"),
            "from_address": extract_address(row.get("from")),
            "to_address": extract_address(row.get("to")), "method": row.get("method"),
            "status": row.get("status"), "value": row.get("value"),
            "fee": fee.get("value") if isinstance(fee, dict) else fee,
            "gas_used": row.get("gas_used")}


def normalize_token_transfer(row):
    token, total = row.get("token") or {}, row.get("total") or {}
    token_id = total.get("token_id")
    decimals = total.get("decimals")
    if decimals is None:
        decimals = token.get("decimals")
    return {"transfer_key": f"{row.get('transaction_hash')}:{row.get('log_index')}:"
            f"{token.get('address_hash')}:{token_id or ''}",
            "tx_hash": row.get("transaction_hash"), "log_index": row.get("log_index"),
            "timestamp": row.get("timestamp"), "block_number": row.get("block_number"),
            "from_address": extract_address(row.get("from")),
            "to_address": extract_address(row.get("to")),
            "token_type": row.get("token_type"), "token_symbol": token.get("symbol"),
            "token_name": token.get("name"), "token_address": token.get("address_hash"),
            "token_id": token_id,
            "amount_raw": "1" if row.get("token_type") == "ERC-721" else total.get("value"),
            "decimals": decimals}


def fetch(url, timeout):
    require(url.startswith(BASE) and "?" not in url and "#" not in url,
            "unexpected explorer URL")
    req = Request(url, headers={"Accept": "application/json",
                                "User-Agent": "AxieOS-Readonly-Closed-Trade/0.16"})
    with urlopen(req, timeout=timeout) as response:
        require(response.status == 200 and
                "json" in response.headers.get("Content-Type", "").lower(),
                "explorer response status/type differs")
        raw = response.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, "explorer response too large")
    doc = json.loads(raw.decode("utf-8"))
    require(isinstance(doc, dict), "explorer response is not an object")
    return doc, hashlib.sha256(raw).hexdigest()


def latest_complete(directory):
    matches = []
    for path in directory.glob("*.json"):
        try:
            doc, digest = load(path)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if doc.get("task") == "136BN" and doc.get("coverage", {}).get("complete") is True:
            matches.append((doc.get("created_at_utc", ""), path, doc, digest))
    require(bool(matches), "no complete Task136BN sale crosswalk found")
    _created, path, doc, digest = max(matches)
    return path, doc, digest


def sources(bn_dir, aj_dir, bm_dir):
    bp, bn, bs = latest_complete(bn_dir)
    ap = by_sha(aj_dir, bn["sources"]["136AJ"]["sha256"], "136AJ")
    mp = by_sha(bm_dir, bn["sources"]["136BM"]["sha256"], "136BM")
    aj, ash = load(ap)
    bm, msh = load(mp)
    require(ash == bn["sources"]["136AJ"]["sha256"] and
            msh == bn["sources"]["136BM"]["sha256"] and
            bm["source_reports"]["136AJ"]["sha256"] == ash and
            bn.get("checkpoint96") == aj.get("checkpoint96") == bm.get("checkpoint96") == "OPEN" and
            all(d.get("accepted_financial_totals") is None for d in (bn, aj, bm)) and
            bn.get("database_writes") == bm.get("database_writes") == 0 and
            bn["coverage"].get("explorer_correlated") == 26 and
            bn.get("independent_receipts_verified_by_this_report") == 0,
            "sale crosswalk, source hashes or financial acceptance boundary differ")
    flows = {r["sale_hash"].lower(): r for r in aj["closed_flow_candidates"]}
    selected = bn["sale_checks"]
    require(len(selected) == len({r["sale_hash"].lower() for r in selected}) == 26 and
            len({r["purchase_hash"].lower() for r in selected}) == 26 and
            all(r["status"] == "EXPLORER_PAIR_CORROBORATED" and
                r["evidence"]["explorer_transaction_success"] is True and
                r["evidence"]["independent_receipt_verified"] is False and
                r["accepted_financial_value"] is None and
                r["sale_hash"].lower() in flows and
                r["axie_id"] == flows[r["sale_hash"].lower()]["axie_id"] and
                r["purchase_hash"].lower() == flows[r["sale_hash"].lower()]["purchase_hash"].lower()
                for r in selected),
            "closed-flow identities or sale evidence differ")
    conflict_sales = {r["sale_hash"].lower() for r in bm["review_queue"]
                      if r["review_lane"] == "SALE_BASIS_CONFLICT"}
    require(not conflict_sales & set(flows) and len(conflict_sales) == 24,
            "scoped closed trades overlap historical cost conflicts")
    return {"136AJ": (ap, ash), "136BM": (mp, msh), "136BN": (bp, bs)}, \
           sorted(selected, key=lambda r: r["sale_hash"]), flows


def evaluate(sale, flow, tx_doc, transfer_doc):
    h = sale["purchase_hash"].lower()
    tx = normalize_transaction(tx_doc)
    require(str(tx.get("tx_hash") or "").lower() == h and tx.get("status") == "ok" and
            str(tx.get("from_address") or "").lower() == WALLET,
            f"{h}: purchase transaction hash/status/payer differs")
    require(isinstance(transfer_doc.get("items"), list) and
            transfer_doc.get("next_page_params") is None,
            f"{h}: purchase transfer page incomplete")
    rows = [normalize_token_transfer(x) for x in transfer_doc["items"]]
    require(all(str(r.get("tx_hash") or "").lower() == h for r in rows),
            f"{h}: foreign transfer in purchase page")
    axies = [r for r in rows if str(r.get("token_address") or "").lower() == AXIE and
             str(r.get("token_id")) == sale["axie_id"] and r.get("token_type") == "ERC-721" and
             str(r.get("to_address") or "").lower() == WALLET and
             str(r.get("from_address") or "").lower() != WALLET]
    weth = [r for r in rows if str(r.get("token_address") or "").lower() == WETH and
            r.get("token_type") == "ERC-20" and str(r.get("decimals")) == "18" and
            str(r.get("from_address") or "").lower() == WALLET and
            str(r.get("to_address") or "").lower() != WALLET and
            str(r.get("amount_raw") or "").isdecimal()]
    require(len(axies) == len(weth) == 1,
            f"{h}: unique Axie acquisition and WETH outflow absent")
    out = Decimal(weth[0]["amount_raw"]) / Decimal(10) ** 18
    net = Decimal(sale["evidence"]["explorer_weth_net_to_wallet"])
    require(out == Decimal(flow["purchase_weth_sent_observed"]) and
            net == Decimal(flow["sale_weth_received_observed"]) and out > 0 and net > 0,
            f"{h}: purchase/sale WETH mismatch")
    sale_tx = sale["evidence"]["normalized_transaction"]
    bought = datetime.fromisoformat(tx["timestamp"].replace("Z", "+00:00"))
    sold = datetime.fromisoformat(sale_tx["timestamp"].replace("Z", "+00:00"))
    require(bought.tzinfo is not None and sold.tzinfo is not None and bought < sold and
            bought.isoformat() == flow["purchase_utc"] and
            sold.isoformat() == flow["sale_utc"] and
            flow["cached_transfer_interval_clear"] is True,
            f"{h}: ownership interval or timestamps differ")
    require(sale["evidence"]["matched_axie_transfer"]["token_id"] == sale["axie_id"] and
            sale["evidence"]["matched_weth_transfer"]["amount_raw"].isdecimal() and
            str(sale["evidence"]["matched_weth_transfer"]["to_address"]).lower() == WALLET,
            f"{h}: sale payment evidence differs")
    difference = net - out
    require(difference == Decimal(flow["observed_wallet_weth_difference_before_gas"]),
            f"{h}: cached wallet difference differs")
    return {"purchase_utc": bought.isoformat(), "sale_utc": sold.isoformat(),
            "purchase_weth_out_observed": str(out), "sale_weth_net_in_observed": str(net),
            "wallet_weth_difference_before_gas": str(difference),
            "matched_axie_in": axies[0], "matched_weth_out": weth[0],
            "purchase_transaction": tx, "purchase_transfer_rows": len(rows),
            "accepted_profit": None, "gas_expense_accepted": None,
            "independent_receipt_verified": False}


def run(bn_dir, aj_dir, bm_dir, out_dir, timeout):
    require(1 <= timeout <= 25, "timeout must be 1..25 seconds")
    src, sales, flows = sources(bn_dir, aj_dir, bm_dir)
    checks, calls, consecutive_failures = [], 0, 0
    for sale in sales:
        h = sale["purchase_hash"].lower()
        require(h.startswith("0x") and len(h) == 66 and
                all(c in "0123456789abcdef" for c in h[2:]), "invalid purchase hash")
        row = {"axie_id": sale["axie_id"], "purchase_hash": h,
               "sale_hash": sale["sale_hash"].lower(),
               "accepted_financial_value": None}
        try:
            calls += 1
            tx, txsha = fetch(BASE + h, timeout)
            calls += 1
            transfers, trsha = fetch(BASE + h + "/token-transfers", timeout)
            result = evaluate(sale, flows[row["sale_hash"]], tx, transfers)
            row.update(status="PURCHASE_AND_SALE_TRANSFERS_CORROBORATED",
                       transaction_sha256=txsha, transfers_sha256=trsha,
                       evidence=result)
            consecutive_failures = 0
        except (HTTPError, URLError, TimeoutError, OSError, ValueError,
                TypeError, KeyError, ArithmeticError) as exc:
            row.update(status="INCOMPLETE_OR_CONFLICTING",
                       failure_type=type(exc).__name__, reason=str(exc)[:180])
            consecutive_failures += 1
        checks.append(row)
        if consecutive_failures >= 2:
            break
    complete = len(checks) == 26 and all(
        r["status"] == "PURCHASE_AND_SALE_TRANSFERS_CORROBORATED" for r in checks)
    observed = [r for r in checks if r["status"] == "PURCHASE_AND_SALE_TRANSFERS_CORROBORATED"]
    delta = sum((Decimal(r["evidence"]["wallet_weth_difference_before_gas"]) for r in observed), Decimal(0))
    signs = Counter("POSITIVE" if Decimal(r["evidence"]["wallet_weth_difference_before_gas"]) > 0
                    else "NEGATIVE" if Decimal(r["evidence"]["wallet_weth_difference_before_gas"]) < 0
                    else "ZERO" for r in observed)
    report = {"project": "AxieOS", "version": "0.16", "task": "CLOSED_TRADE_EVIDENCE",
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "sources": {k: {"filename": path.name, "sha256": digest}
                          for k, (path, digest) in src.items()},
              "coverage": {"target_closed_flows": 26, "attempted": len(checks),
                           "both_sides_correlated": len(observed),
                           "unattempted": 26-len(checks), "complete": complete,
                           "historical_sale_basis_conflicts_separate": 24,
                           "difference_signs_for_correlated": dict(signs)},
              "observed_weth_wallet_difference_before_gas_for_correlated": str(delta),
              "accepted_financial_totals": None, "verified_profit_php": None,
              "closed_trade_checks": checks,
              "database_opened": False, "database_writes": 0, "network_calls_attempted": calls,
              "unified_finance": "HOLD", "checkpoint96": "OPEN"}
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V016_Closed_Trade_Evidence_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = out_dir / (stem + ".json"), out_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as out:
        json.dump(report, out, indent=2)
        out.write("\n")
    mp.write_text("\n".join(["# AxieOS V0.16 — Closed Axie trade evidence", "",
        f"Purchase/sale transfers corroborated: **{len(observed)}/26**; "
        f"attempted **{len(checks)}/26**. Coverage: **{'COMPLETE' if complete else 'INCOMPLETE'}**.",
        f"Observed WETH wallet difference before gas across corroborated pairs: **{delta} WETH**.",
        "This difference is a limited wallet-flow observation. It is not accepted profit, "
        "complete cost basis, a PHP figure or proof that gas was paid by the user.",
        "The 24 historical sale-basis conflicts are a separate cohort. Do not add their "
        "amounts to this view as new transactions.", "",
        "Verified all-time income, expenses, profit and PHP recovery: **UNKNOWN**. "
        "Unified Finance: **HOLD**. Checkpoint 96: **OPEN**.", "",
        f"Database opened: NO | Writes: 0 | Network calls attempted: {calls}", ""]),
        encoding="utf-8")
    print("AXIEOS V0.16 - CLOSED AXIE TRADE EVIDENCE")
    print(f"Corroborated: {len(observed)}/26 | Attempted: {len(checks)}/26 | "
          f"Observed WETH difference before gas: {delta}")
    print(f"Reports: {jp} {mp}")
    print("Verified profit/PHP recovery: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN")
    print(f"Database opened: NO | Writes: 0 | Network calls attempted: {calls}")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bn-dir", type=Path, default=Path("reports/axieos_v014/task136bn"))
    p.add_argument("--aj-dir", type=Path, default=Path("reports/axieos_v014/task136aj"))
    p.add_argument("--bm-dir", type=Path, default=Path("reports/axieos_v014/task136bm"))
    p.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v016/closed_trades"))
    p.add_argument("--timeout", type=int, default=12)
    a = p.parse_args()
    run(a.bn_dir, a.aj_dir, a.bm_dir, a.output_dir, a.timeout)


if __name__ == "__main__":
    main()
