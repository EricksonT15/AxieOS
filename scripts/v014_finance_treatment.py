r"""Task136T: attach conservative finance treatment to each registry reference.

Run from the AxieOS repository root:
    py -B .\scripts\v014_finance_treatment.py

Reads Task136R and Checkpoint96BV JSON only. No database or network access.
No source status, fee or stored payment is promoted to a verified amount.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


PREVIEW_POLICY = {
    "EXTERNAL_CAPITAL": ("CAPITAL_PROVISIONAL", "Included source contribution; complete external-capital reconciliation remains open"),
    "REPORTED_CASH_RECEIPT": ("CASH_RECEIPT_ATTESTED", "Reported receipt has no bank-matched permanent recovery proof"),
    "TOKEN_REWARD": ("REWARD_QUANTITY_CANDIDATE", "Resolved token inflow; receipt and PHP income remain unverified"),
    "MARKETPLACE_SALE": ("SALE_PAYMENT_STORED", "Gross, marketplace fee and net are stored arithmetic; receipt and basis unresolved"),
    "MARKETPLACE_PURCHASE": ("ASSET_OUTLAY_STORED", "Stored acquisition amount; not automatically an expense or new capital"),
}
ACCOUNTING_POLICY = {
    "MINT_OR_CLAIM": ("INCOMING_MOVEMENT_UNRESOLVED", "Claim, mint, reward and inventory origin not separated by this source classification"),
    "TOKEN_BURN": ("TOKEN_DISPOSAL_UNRESOLVED", "Burn quantity observed; consumed inventory, fee, basis and expense unresolved"),
    "NFT_BURN": ("NFT_DISPOSAL_UNRESOLVED", "Axie burn observed; release cost, materials, basis and economic value unresolved"),
    "TRANSFER_IN": ("TRANSFER_PURPOSE_UNRESOLVED", "Incoming transfer direction observed; endpoints and ownership not reconciled"),
    "TRANSFER_OUT": ("TRANSFER_PURPOSE_UNRESOLVED", "Outgoing transfer direction observed; endpoints and ownership not reconciled"),
    "STAKING_OR_REWARD": ("STAKING_OUTFLOW_UNRESOLVED", "Outgoing AXS/bAXS movement; principal, spend and fee purpose unresolved"),
    "TOKEN_SWAP": ("EXCHANGE_BASIS_UNRESOLVED", "Exchange receipt is not additional reward; acquisition basis and gain unresolved"),
    "UNKNOWN": ("UNCLASSIFIED_REVIEW", "Source asset or economic purpose unresolved"),
}
EXPECTED = {"CAPITAL_PROVISIONAL": 108, "CASH_RECEIPT_ATTESTED": 4,
            "REWARD_QUANTITY_CANDIDATE": 18, "SALE_PAYMENT_STORED": 75,
            "ASSET_OUTLAY_STORED": 53, "INCOMING_MOVEMENT_UNRESOLVED": 123,
            "TOKEN_DISPOSAL_UNRESOLVED": 58, "NFT_DISPOSAL_UNRESOLVED": 7,
            "TRANSFER_PURPOSE_UNRESOLVED": 60, "STAKING_OUTFLOW_UNRESOLVED": 6,
            "EXCHANGE_BASIS_UNRESOLVED": 2, "UNCLASSIFIED_REVIEW": 3}


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError("STOP: " + reason)


def select(explicit: Path | None, directory: Path, task: str) -> tuple[Path, dict, str]:
    paths = [explicit] if explicit else list(directory.glob("*.json")) if directory.is_dir() else []
    found = []
    for path in paths:
        if path is None or not path.is_file():
            continue
        raw = path.read_bytes()
        try:
            data = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and (data.get("task") == task or
                                       (task == "96BV" and data.get("checkpoint") == "96BV")):
            found.append((path, data, hashlib.sha256(raw).hexdigest()))
    require(len(found) == 1, f"{task}: expected one JSON in {directory}; use --{task.lower()} PATH")
    return found[0]


def build(registry: dict, bv: dict, registry_sha: str, bv_sha: str) -> dict:
    require(registry.get("task") == "136R" and registry.get("validation", {}).get("status") == "PASS_OFFLINE_REGISTRY_ONLY",
            "wrong registry or validation")
    require(registry.get("validation", {}).get("database_opened") is False
            and registry["validation"].get("database_writes") == 0
            and registry["validation"].get("network_calls") == 0
            and registry["validation"].get("checkpoint96_closed") is False, "registry boundary changed")
    require(registry.get("accepted_totals") and all(x is None for x in registry["accepted_totals"].values()),
            "accepted registry totals changed")
    rows = registry.get("registry_rows")
    require(isinstance(rows, list) and len(rows) == 517, "registry coverage changed")
    require(bv.get("checkpoint") == "96BV" and bv.get("task") == "135H", "wrong accounting extract")
    require(registry.get("sources", {}).get("96BV", {}).get("sha256") == bv_sha, "BV source hash differs from registry")
    accounts = bv.get("tables", {}).get("blockchain_accounting_records", {}).get("rows")
    require(isinstance(accounts, list) and len(accounts) == 405, "accounting coverage changed")
    acc = {a.get("accounting_key"): a for a in accounts}
    require(len(acc) == 405 and None not in acc, "duplicate accounting keys")
    results = []
    for row in rows:
        origin, lane, key = row.get("origin"), row.get("lane"), row.get("accounting_key")
        require(row.get("accepted_financial_value") is None, "accepted registry value changed")
        if origin == "TASK136B_PREVIEW":
            require(lane in PREVIEW_POLICY, f"unexpected preview lane {lane}")
            if key is not None:
                require(key in acc and acc[key]["txhash"] == row.get("txhash"), "preview hash differs")
            treatment, reason = PREVIEW_POLICY[lane]
        elif origin == "CHECKPOINT96BV_ACCOUNTING_ONLY":
            require(key in acc and acc[key]["txhash"] == row.get("txhash")
                    and acc[key]["classification"] == lane, "accounting row differs")
            treatment, reason = ACCOUNTING_POLICY[lane]
            if lane == "STAKING_OR_REWARD":
                require(acc[key].get("direction") == "OUT", "new staking direction needs review")
            if lane in ("TRANSFER_IN", "TRANSFER_OUT"):
                require(acc[key].get("accounting_status") == "REVIEW", "transfer status changed")
                reason += "; stored is_internal_transfer flag is not independent proof"
        else:
            raise ValueError(f"STOP: unknown registry origin {origin}")
        results.append({"registry_id": row["registry_id"], "origin": origin,
                        "source_lane": lane, "source_status": row.get("source_status"),
                        "txhash": row.get("txhash"), "asset_as_stored": row.get("asset_as_stored"),
                        "quantity_as_stored": row.get("quantity_as_stored"),
                        "gross_as_stored": row.get("gross_as_stored"),
                        "treatment_status": treatment, "treatment_reason": reason,
                        "accepted_income": None, "accepted_expense": None,
                        "accepted_profit": None, "accepted_capital_recovery": None,
                        "accepted_php_value": None})
    ids = [r["registry_id"] for r in results]
    require(len(set(ids)) == 517 and all(ids), "duplicate or empty reference")
    actual = dict(Counter(r["treatment_status"] for r in results))
    require(actual == EXPECTED, f"treatment coverage differs: {actual}")
    require(len({r["txhash"] for r in results if r["txhash"]}) == 405,
            "unexpected linked transaction hash count")
    return {"project": "AxieOS", "version": "0.14", "task": "136T",
            "scope": "Policy treatment over source references, not accepted financial events",
            "source_registry_sha256": registry_sha, "source_accounting_sha256": bv_sha,
            "coverage": {"references": len(results), "treatments": dict(sorted(actual.items())),
                         "accepted_financial_values": 0},
            "treatment_rows": results,
            "verified_totals": {"income_php": None, "expenses_php": None,
                                "profit_php": None, "capital_recovery_php": None},
            "validation": {"status": "PASS_OFFLINE_TREATMENT_ONLY", "database_opened": False,
                           "database_writes": 0, "network_calls": 0, "checkpoint96_closed": False}}


def markdown(report: dict) -> str:
    lines = ["# AxieOS V0.14 — Task136T Finance treatment", "",
             "**Status:** All source references have conservative treatment labels. Verified financial totals remain UNKNOWN.", "",
             "| Treatment status | References |", "|---|---:|"]
    for label, count in report["coverage"]["treatments"].items():
        lines.append(f"| {label} | {count} |")
    lines += ["", "The companion JSON preserves the stored asset, quantity, gross amount and source status "
              "alongside each treatment reason. No source amount is placed into an accepted income, expense, "
              "profit, recovery or PHP field. A READY source status is not receipt verification.", "",
              "Transfer direction alone does not establish whether the movement is internal. Burns, swaps, "
              "staking outflows and gameplay observations still require evidence before economic recognition.", "",
              "Database opened: NO | Writes: 0 | Network calls: 0", "",
              "VALIDATION: PASS (offline treatment only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, help="Task136R JSON")
    parser.add_argument("--bv", type=Path, help="Checkpoint96BV JSON")
    parser.add_argument("--report-root", type=Path, default=Path("reports/axieos_v014"))
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("reports/axieos_v013/checkpoint96"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136t"))
    args = parser.parse_args()
    rp, registry, rsha = select(args.registry, args.report_root / "task136r", "136R")
    bp, bv, bsha = select(args.bv, args.checkpoint_dir, "96BV")
    report = build(registry, bv, rsha, bsha)
    report["source_registry_filename"] = rp.name
    report["source_accounting_filename"] = bp.name
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136T_Finance_Treatment_"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as out:
        json.dump(report, out, ensure_ascii=False, indent=2)
        out.write("\n")
    with mp.open("x", encoding="utf-8") as out:
        out.write(markdown(report))
    print("AXIEOS V0.14 - TASK136T - FINANCE TREATMENT")
    print(f"Registry references: {report['coverage']['references']} | Treatment statuses: "
          f"{len(report['coverage']['treatments'])} | Accepted values: 0")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network calls: 0")
    print("VALIDATION: PASS (offline treatment only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
