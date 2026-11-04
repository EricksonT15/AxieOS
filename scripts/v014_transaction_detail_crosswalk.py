r"""Task136BI: offline crosswalk for recent transaction detail responses.

From the AxieOS repository root:
    py -B .\scripts\v014_transaction_detail_crosswalk.py

Reads SHA-linked Task136BH/BF/BC/AY/AU JSON. Rechecks every saved explorer
body against its digest and existing raw transfer/ledger evidence. Candidate
raw transaction rows remain unaccepted; no SQLite or network access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ronin_api_sync import normalize_transaction
from v013_fullrow_materialization_sandbox import utc_datetime
from v014_post_apply_reconcile import require
from v014_raw_import_clone import TX_FIELDS, address, by_sha, latest, load, txhash


def build(bh: dict, bf: dict, bc: dict, ay: dict, au: dict,
          shas: dict[str, str]) -> dict:
    require(all(doc.get("task") == task and doc.get("checkpoint96") == "OPEN" and
                doc.get("accepted_financial_totals") is None
                for task, doc in (("136BH", bh), ("136BF", bf),
                                  ("136BC", bc), ("136AY", ay), ("136AU", au))) and
            all(bh["sources"][t]["sha256"] == shas[t]
                for t in ("136BF", "136BC", "136AY", "136AU")) and
            bf["sources"]["136BC"]["sha256"] == shas["136BC"] and
            ay["sources"]["136AU"]["sha256"] == shas["136AU"],
            "Task136BH source chain or finance boundary differs")
    coverage = bh["coverage"]
    outcomes = bh["lookup_results"]
    require(coverage["complete"] is True and
            coverage["requests_attempted"] ==
                coverage["responses_validated"] ==
                coverage["target_transfer_only_hashes"] == len(outcomes) and
            coverage["failed_or_unvalidated"] == 0 and
            coverage["unattempted"] == 0 and
            bh["network_calls_attempted"] == len(outcomes) and
            bh["database_opened"] is False and bh["database_writes"] == 0,
            "Task136BH lookup is incomplete or its boundary changed")
    ledger = defaultdict(list)
    for row in ay["guarded_ledger_rows"]:
        ledger[str(row["txhash"]).lower()].append(row)
    transfers = defaultdict(list)
    for row in au["normalized_new_transfers"]:
        transfers[str(row["tx_hash"]).lower()].append(row)
    prior_tx = {str(row["tx_hash"]).lower()
                for row in au["normalized_new_transactions"]}
    shadow = {str(row["txhash"]).lower(): row for row in bc["candidates"]}
    recent = {str(row["txhash"]).lower(): row for row in bf["registry_rows"]
              if row.get("origin") == "TASK136AU_RECENT_RAW"}
    require(set(ledger) == set(transfers) == set(shadow) and
            len(recent) == bf["coverage"]["recent_raw_hash_references"],
            "guarded ledger, transfer or shadow coverage differs")
    expected = {h for h, rows in ledger.items()
                if h not in prior_tx and
                all(row["method"] is None and row["status"] is None
                    for row in rows)}
    require(len(expected) == coverage["target_transfer_only_hashes"] ==
            ay["coverage"]["new_transfer_hashes_with_no_transaction_row"] and
            len({str(item["txhash"]).lower() for item in outcomes}) == len(outcomes) and
            {str(item["txhash"]).lower() for item in outcomes} == expected,
            "Task136BH target set differs from missing transaction sources")
    proposed, evidence = [], []
    for item in sorted(outcomes, key=lambda row: row["txhash"].lower()):
        source = item["source"]
        h = str(item["txhash"]).lower()
        raw = item.get("raw_body_utf8")
        require(item["result"] == "EVIDENCE_FETCHED" and
                source["txhash"] == h and txhash(h) and
                isinstance(raw, str) and
                hashlib.sha256(raw.encode("utf-8")).hexdigest() ==
                    item["response_sha256"] and
                item.get("http_status") == 200,
                f"{h}: saved explorer response digest or status differs")
        doc = json.loads(raw)
        require(isinstance(doc, dict), f"{h}: saved response is not one object")
        normalized = normalize_transaction(doc)
        require(normalized == item["normalized_candidate"] and
                str(normalized["tx_hash"]).lower() == h and
                normalized["block_number"] == source["block_number"] and
                address(normalized["from_address"]) and
                address(normalized["to_address"]),
                f"{h}: saved normalized transaction differs")
        unix, _ = utc_datetime(normalized["timestamp"])
        require(unix == source["unixtimestamp"] and
                all(row["blockno"] == normalized["block_number"] and
                    row["unixtimestamp"] == unix for row in ledger[h]) and
                all(row["block_number"] == normalized["block_number"] and
                    utc_datetime(row["timestamp"])[0] == unix for row in transfers[h]) and
                len(ledger[h]) == source["ledger_rows"] ==
                    shadow[h]["ledger_rows"] and
                recent[h]["post_apply_ledger_status"] == "MATERIALIZED_GUARDED",
                f"{h}: transaction block/time differs from saved transfers or ledger")
        fee, gas = normalized.get("fee"), normalized.get("gas_used")
        require(fee is None or str(fee).isdecimal(),
                f"{h}: raw fee is not a nonnegative integer quantity")
        require(gas is None or str(gas).isdecimal(),
                f"{h}: gas used is not a nonnegative integer quantity")
        proposal = (h, normalized["timestamp"], normalized["block_number"],
                    normalized["from_address"], normalized["to_address"],
                    normalized.get("method"), normalized.get("status"),
                    str(normalized["value"]) if normalized.get("value") is not None else None,
                    str(fee) if fee is not None else None,
                    int(gas) if gas is not None else None)
        proposed.append(dict(zip(TX_FIELDS, proposal)))
        evidence.append({"txhash": h, "ledger_rows": len(ledger[h]),
                         "method_candidate": normalized.get("method"),
                         "status_candidate": normalized.get("status"),
                         "raw_fee_candidate": proposal[8],
                         "gas_used_candidate": proposal[9],
                         "fee_payer_verified": False,
                         "financial_treatment": "UNREVIEWED_CANDIDATE"})
    require(len(proposed) == len(expected) and
            len({row["tx_hash"] for row in proposed}) == len(proposed),
            "proposed raw transaction identities duplicate")
    return {"project": "AxieOS", "version": "0.14", "task": "136BI",
            "sources": {task: {"sha256": shas[task]} for task in shas},
            "coverage": {"lookup_hashes": len(expected),
                         "candidate_raw_transactions": len(proposed),
                         "raw_fee_present": sum(row["fee_raw"] is not None
                                                for row in proposed),
                         "method_present": sum(row["method"] is not None
                                               for row in proposed),
                         "statuses": dict(sorted(Counter(str(row["status"])
                             for row in proposed).items()))},
            "candidate_raw_transaction_rows": proposed,
            "evidence_rows": evidence,
            "accepted_financial_totals": None,
            "database_opened": False, "database_writes": 0,
            "network_calls": 0, "checkpoint96": "OPEN"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for suffix in ("bh", "bf", "bc", "ay", "au"):
        parser.add_argument(f"--{suffix}-dir", type=Path,
                            default=Path(f"reports/axieos_v014/task136{suffix}"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("reports/axieos_v014/task136bi"))
    args = parser.parse_args()
    paths = {"136BH": latest(args.bh_dir, "136BH")}
    bh, bh_sha = load(paths["136BH"])
    for task in ("136BF", "136BC", "136AY", "136AU"):
        paths[task] = by_sha(getattr(args, task[3:].lower() + "_dir"),
                              bh["sources"][task]["sha256"], task)
    docs, shas = {}, {}
    for task, path in paths.items():
        docs[task], shas[task] = load(path)
    report = build(docs["136BH"], docs["136BF"], docs["136BC"],
                   docs["136AY"], docs["136AU"], shas)
    for task, path in paths.items():
        report["sources"][task]["filename"] = path.name
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136BI_Transaction_Detail_Crosswalk_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
            "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    c = report["coverage"]
    mp.write_text("\n".join([
        "# AxieOS V0.14 — Task136BI Transaction detail crosswalk", "",
        f"Validated raw transaction candidates: **{c['candidate_raw_transactions']}**. "
        f"Raw fees present: **{c['raw_fee_present']}**; methods present: "
        f"**{c['method_present']}**.", "",
        f"Statuses: **{c['statuses']}**. These are raw evidence fields. "
        "Fee payer, gas expense, classification and profit remain unverified.", "",
        "Verified financial totals: **UNKNOWN**. Checkpoint 96: **OPEN**.", "",
        "Database opened: NO | Writes: 0 | Network: 0", ""]), encoding="utf-8")
    print("AXIEOS V0.14 - TASK136BI - TRANSACTION DETAIL CROSSWALK")
    print(f"Candidate raw transactions: {c['candidate_raw_transactions']} | "
          f"Raw fees present: {c['raw_fee_present']} | "
          f"Methods present: {c['method_present']}")
    print(f"Statuses: {c['statuses']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (offline raw crosswalk only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
