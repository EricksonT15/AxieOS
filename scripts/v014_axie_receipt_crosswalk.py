r"""Task136AN: match one cached Axie flow to a saved independent sale receipt.

Run from the AxieOS repository root:
    py -B .\scripts\v014_axie_receipt_crosswalk.py

Reads Task136AJ and the Checkpoint88/90 saved receipt and ledger for Axie
#12254862. No RPC, SQLite, wallet operation, or accepted portfolio total.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4


AXIE_ID = "12254862"
WETH_CONTRACT = "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5"
AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"
TRANSFER_TOPIC = ("0xddf252ad1be2c89b69c2b068fc378daa"
                  "952ba7f163c4a11628f55a4df523b3ef")


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError("STOP: " + reason)


def load(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing source: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def select_aj(explicit: Path | None, directory: Path) -> Path:
    if explicit is not None:
        return explicit
    matches = []
    for p in directory.glob("*.json") if directory.is_dir() else []:
        doc, _ = load(p)
        if doc.get("task") == "136AJ":
            matches.append((doc.get("created_at_utc", ""), p))
    require(matches, f"missing Task136AJ JSON in {directory}; pass --aj PATH")
    return max(matches)[1]


def ledger(path: Path) -> tuple[list[dict], str]:
    require(path.is_file(), f"missing historical ledger: {path}")
    raw = path.read_bytes()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    require(len(rows) == 3 and len({r["axie_id"] for r in rows}) == 3,
            "Checkpoint90 known-sale ledger changed")
    return rows, hashlib.sha256(raw).hexdigest()


def from_topic(topic: str) -> str:
    require(isinstance(topic, str) and topic.startswith("0x") and len(topic) == 66,
            "invalid transfer address topic")
    return "0x" + topic[-40:].lower()


def receipt_log_check(receipt: dict, txhash: str, wallet: str, expected_net: Decimal) -> dict:
    require(receipt.get("transactionHash", "").lower() == txhash and
            receipt.get("status") == "0x1" and
            isinstance(receipt.get("logs"), list), "sale receipt hash, success or logs differ")
    weth_to_wallet = []
    axie_from_wallet = []
    for log in receipt["logs"]:
        topics = log.get("topics") or []
        if not topics or str(topics[0]).lower() != TRANSFER_TOPIC:
            continue
        address = str(log.get("address") or "").lower()
        if address == WETH_CONTRACT and len(topics) == 3:
            sender, recipient = from_topic(topics[1]), from_topic(topics[2])
            amount = Decimal(int(log["data"], 16)) / Decimal(10) ** 18
            if recipient == wallet and amount == expected_net:
                weth_to_wallet.append({"from": sender, "to": recipient,
                                       "amount_weth": format(amount, "f")})
        elif address == AXIE_CONTRACT and len(topics) == 4 and int(topics[3], 16) == int(AXIE_ID):
            sender, recipient = from_topic(topics[1]), from_topic(topics[2])
            if sender == wallet and recipient != wallet:
                axie_from_wallet.append({"from": sender, "to": recipient})
    require(len(weth_to_wallet) == len(axie_from_wallet) == 1,
            "sale receipt lacks unique Axie transfer and net WETH to owned wallet")
    return {"sale_receipt_success": True,
            "unique_axie_transfer_from_owned_wallet": True,
            "unique_net_weth_transfer_to_owned_wallet": True,
            "block_number": int(receipt["blockNumber"], 16),
            "seller_net_weth_on_receipt": weth_to_wallet[0]["amount_weth"]}


def build(aj: dict, proof: dict, receipt: dict, rows: list[dict], sources: dict) -> dict:
    require(aj.get("task") == "136AJ" and aj.get("checkpoint96") == "OPEN" and
            aj.get("accepted_financial_totals") is None and
            aj["coverage"]["closed_cached_axie_sequences"] == len(aj["closed_flow_candidates"]),
            "Task136AJ coverage or financial boundary differs")
    matches = [r for r in aj["closed_flow_candidates"] if str(r["axie_id"]) == AXIE_ID]
    require(len(matches) == 1, "target Axie missing or duplicated in cached matched flows")
    candidate = matches[0]
    transaction = str(candidate["sale_hash"]).lower()
    wallet = str(candidate["owned_wallet"]).lower()
    ledger_row = next(r for r in rows if r["axie_id"] == AXIE_ID)
    require(proof.get("axie_id") == AXIE_ID and
            str(proof.get("transaction_hash") or "").lower() == transaction and
            str(ledger_row.get("transaction_hash") or "").lower() == transaction and
            proof.get("receipt_confirmed") is True and
            proof.get("transaction_successful") is True and
            proof.get("wallet_receipt_reconciled") is True and
            proof.get("exact_net_to_known_wallet") is True and
            ledger_row.get("accounting_status") == "ONCHAIN_SETTLED" and
            ledger_row.get("chain_receipt_verified") == "YES" and
            ledger_row.get("capital_recovery_credited_weth") == "0" and
            proof.get("capital_recovery_credited") is False,
            "historical sale proof, settlement or recovery state differs")
    gross = Decimal(ledger_row["gross_sale_weth"])
    fee = Decimal(ledger_row["marketplace_fee_weth"])
    net = Decimal(ledger_row["verified_wallet_receipt_weth"])
    purchase = Decimal(candidate["purchase_weth_sent_observed"])
    require(gross > 0 and fee > 0 and net > 0 and purchase > 0 and
            gross - fee == net and
            Decimal(ledger_row["documented_net_weth"]) == net and
            Decimal(proof["documented_net_weth"]) == net and
            Decimal(candidate["sale_weth_received_observed"]) == net and
            Decimal(candidate["observed_wallet_weth_difference_before_gas"]) == net - purchase,
            "documented gross/fee/net or cached wallet difference differs")
    checks = receipt_log_check(receipt, transaction, wallet, net)
    require(checks["block_number"] == proof["block_number"] and
            any(str(t.get("recipient") or "").lower() == wallet and
                Decimal(t["amount_weth"]) == net and
                t.get("recipient_is_known_wallet") is True for t in proof["weth_transfers"]),
            "receipt block or historical net transfer summary differs")
    return {"project": "AxieOS", "version": "0.14", "task": "136AN",
            "sources": sources,
            "coverage": {"cached_closed_axie_candidates": len(aj["closed_flow_candidates"]),
                         "historical_receipt_crosswalked": 1,
                         "other_closed_axie_candidates_not_receipt_checked":
                             len(aj["closed_flow_candidates"]) - 1},
            "matched_case": {"axie_id": AXIE_ID, "purchase_hash": candidate["purchase_hash"],
                             "sale_hash": transaction, "seller_wallet": wallet,
                             "observed_purchase_weth_sent": format(purchase, "f"),
                             "receipt_verified_sale_net_weth": format(net, "f"),
                             "documented_sale_gross_weth": format(gross, "f"),
                             "documented_marketplace_fee_weth": format(fee, "f"),
                             "observed_wallet_weth_difference_before_gas": format(net - purchase, "f"),
                             "receipt_checks": checks,
                             "purchase_gas_accepted": None, "cost_basis_accepted": None,
                             "realized_profit_accepted": None,
                             "capital_recovery_credited": False,
                             "registry_action": "ANNOTATE_EXISTING_SOURCE_ONLY_NO_NEW_EVENT"},
            "accepted_financial_totals": None, "database_opened": False,
            "database_writes": 0, "network_calls": 0, "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    a, c = report["matched_case"], report["coverage"]
    return "\n".join([
        "# AxieOS V0.14 — Task136AN Saved sale receipt crosswalk", "",
        f"Axie **#{a['axie_id']}** is one of **{c['cached_closed_axie_candidates']}** "
        "cached same-ID purchase/sale candidates. Its sale hash and owned wallet "
        "match the earlier Checkpoint88 receipt and Checkpoint90 settled ledger.", "",
        f"Observed purchase WETH sent: **{a['observed_purchase_weth_sent']}**. "
        f"Receipt-verified sale net WETH: **{a['receipt_verified_sale_net_weth']}**. "
        f"Observed WETH wallet difference before gas: "
        f"**{a['observed_wallet_weth_difference_before_gas']}**.", "",
        f"Historical documented gross/fee: **{a['documented_sale_gross_weth']} / "
        f"{a['documented_marketplace_fee_weth']} WETH**; their arithmetic matches the receipt net. "
        "The receipt independently confirms seller net and Axie transfer. "
        "The other matched flows have no receipt check here.", "",
        "This crosswalk annotates existing evidence; it does not add another sale. "
        "Purchase basis acceptance, gas, realized profit, and permanent capital "
        "recovery remain unresolved. Verified portfolio financial totals: **UNKNOWN**.", "",
        "Database opened: NO | Writes: 0 | Network: 0", "",
        "VALIDATION: PASS (saved receipt crosswalk only; Checkpoint 96 OPEN).", ""])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aj", type=Path)
    parser.add_argument("--aj-dir", type=Path, default=Path("reports/axieos_v014/task136aj"))
    parser.add_argument("--reconciliation", type=Path,
                        default=Path("reports/axieos_v013/checkpoint88/sale_reconciliation_12254862.json"))
    parser.add_argument("--receipt", type=Path,
                        default=Path("reports/axieos_v013/checkpoint88/sale_receipt_12254862.json"))
    parser.add_argument("--ledger", type=Path,
                        default=Path("reports/axieos_v013/checkpoint90/historical_sales_ledger_3.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136an"))
    args = parser.parse_args()
    ap = select_aj(args.aj, args.aj_dir)
    aj, aj_sha = load(ap)
    proof, proof_sha = load(args.reconciliation)
    receipt, receipt_sha = load(args.receipt)
    rows, ledger_sha = ledger(args.ledger)
    sources = {"136AJ": {"filename": ap.name, "sha256": aj_sha},
               "checkpoint88_reconciliation": {"filename": args.reconciliation.name,
                                               "sha256": proof_sha},
               "checkpoint88_receipt": {"filename": args.receipt.name,
                                        "sha256": receipt_sha},
               "checkpoint90_ledger": {"filename": args.ledger.name,
                                       "sha256": ledger_sha}}
    report = build(aj, proof, receipt, rows, sources)
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AN_Axie12254862_Receipt_Crosswalk_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    a, c = report["matched_case"], report["coverage"]
    print("AXIEOS V0.14 - TASK136AN - SAVED SALE RECEIPT CROSSWALK")
    print(f"Matched Axie #{a['axie_id']} | Receipt-verified sale net: "
          f"{a['receipt_verified_sale_net_weth']} WETH | Cached matched flows still unchecked: "
          f"{c['other_closed_axie_candidates_not_receipt_checked']}")
    print("Verified portfolio income, expenses, profit, and PHP recovery: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (saved receipt crosswalk only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
