r"""Task136BH: bounded explorer lookup for recent transfer-only hashes.

From the AxieOS repository root:
    py -B .\scripts\v014_missing_transaction_probe.py

Reads SHA-linked Task136BF/BC/AY/AU reports. Requests at most 22 transaction
detail pages from explorer.roninchain.com, writes only JSON/Markdown evidence
reports. Never opens SQLite, syncs a wallet, or accepts gas/financial totals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from ronin_api_sync import normalize_transaction
from v014_post_apply_reconcile import require
from v014_raw_import_clone import by_sha, latest, load


BASE = "https://explorer.roninchain.com/api/v2/transactions/"
MAX_BODY = 1_048_576


def candidates(bf: dict, bc: dict, ay: dict, au: dict,
               shas: dict[str, str]) -> list[dict]:
    require(all(doc.get("task") == task and doc.get("checkpoint96") == "OPEN"
                and doc.get("accepted_financial_totals") is None
                for task, doc in (("136BF", bf), ("136BC", bc),
                                  ("136AY", ay), ("136AU", au))) and
            bf["sources"]["136BC"]["sha256"] == shas["136BC"] and
            bf["sources"]["136AU"]["sha256"] == shas["136AU"] and
            bc["sources"]["136AY"]["sha256"] == shas["136AY"] and
            ay["sources"]["136AU"]["sha256"] == shas["136AU"],
            "Task136BF/BC/AY/AU source chain or financial boundary differs")
    transfer_hashes = {str(r["tx_hash"]).lower()
                       for r in au["normalized_new_transfers"]}
    new_transaction_hashes = {str(r["tx_hash"]).lower()
                              for r in au["normalized_new_transactions"]}
    ledger = defaultdict(list)
    for row in ay["guarded_ledger_rows"]:
        ledger[str(row["txhash"]).lower()].append(row)
    shadow = {str(r["txhash"]).lower(): r for r in bc["candidates"]}
    registry = {str(r["txhash"]).lower(): r for r in bf["registry_rows"]
                if r.get("origin") == "TASK136AU_RECENT_RAW"}
    require(len(shadow) == bc["coverage"]["recent_hashes"] == len(ledger) and
            set(ledger) == transfer_hashes and
            len(registry) == bf["coverage"]["recent_raw_hash_references"] and
            set(shadow).issubset(registry),
            "recent raw/ledger/shadow/registry cohort differs")
    missing = []
    for h in sorted(set(ledger) - new_transaction_hashes):
        rows, detail = ledger[h], shadow[h]
        if detail["method"] is not None or detail["status"] is not None:
            continue  # A prior raw transaction already supplied this hash.
        require(all(r["method"] is None and r["status"] is None and
                    r["txn_fee_ron"] is None for r in rows) and
                registry[h]["post_apply_ledger_status"] == "MATERIALIZED_GUARDED" and
                registry[h]["post_apply_accounting_status"] == "NO_STORED_ACCOUNTING" and
                detail["ledger_rows"] == len(rows) and
                "METHOD_MISSING" in detail["flags"] and
                "STATUS_MISSING" in detail["flags"],
                f"{h}: transfer-only evidence changed")
        missing.append({"txhash": h,
                        "block_number": rows[0]["blockno"],
                        "unixtimestamp": rows[0]["unixtimestamp"],
                        "ledger_rows": len(rows),
                        "legacy_label_candidate": detail["legacy_label"]})
    require(len(missing) == ay["coverage"]["new_transfer_hashes_with_no_transaction_row"] and
            len(missing) == sum("STATUS_MISSING" in r["flags"] for r in shadow.values()),
            "transfer-only hash count differs from Task136AY/BC")
    return missing


def fetch_one(item: dict, timeout: int) -> dict:
    h = item["txhash"]
    req = Request(BASE + h, headers={"Accept": "application/json",
                                     "User-Agent": "AxieOS-ReadOnly-Evidence/0.14"})
    try:
        with urlopen(req, timeout=timeout) as response:
            status = response.status
            content = response.read(MAX_BODY + 1)
        require(len(content) <= MAX_BODY,
                f"{h}: explorer response exceeds evidence size limit")
        body = content.decode("utf-8")
        document = json.loads(body)
        require(status == 200 and isinstance(document, dict),
                f"{h}: explorer response is not one transaction object")
        normalized = normalize_transaction(document)
        require(str(normalized.get("tx_hash") or "").lower() == h and
                normalized.get("block_number") == item["block_number"] and
                normalized.get("timestamp") and
                normalized.get("from_address") and
                normalized.get("to_address"),
                f"{h}: transaction identity, block, or endpoints differ")
        return {"txhash": h, "result": "EVIDENCE_FETCHED",
                "http_status": status,
                "response_sha256": hashlib.sha256(content).hexdigest(),
                "raw_body_utf8": body, "normalized_candidate": normalized,
                "financial_treatment": "UNREVIEWED_CANDIDATE"}
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeError,
            ValueError, json.JSONDecodeError) as exc:
        return {"txhash": h, "result": "FETCH_OR_VALIDATION_FAILED",
                "error_type": type(exc).__name__,
                "http_status": getattr(exc, "code", None),
                "reason": str(exc)[:240],
                "financial_treatment": "UNREVIEWED_CANDIDATE"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for suffix in ("bf", "bc", "ay", "au"):
        parser.add_argument(f"--{suffix}-dir", type=Path,
                            default=Path(f"reports/axieos_v014/task136{suffix}"))
    parser.add_argument("--limit", type=int, default=22,
                        help="Maximum hashes to request (1..22; default all 22)")
    parser.add_argument("--timeout", type=int, default=12,
                        help="Per-request timeout in seconds (1..30)")
    parser.add_argument("--output-dir", type=Path,
                        default=Path("reports/axieos_v014/task136bh"))
    args = parser.parse_args()
    require(1 <= args.limit <= 22 and 1 <= args.timeout <= 30,
            "bounded lookup requires --limit 1..22 and --timeout 1..30")
    paths = {"136BF": latest(args.bf_dir, "136BF")}
    bf, bf_sha = load(paths["136BF"])
    for task in ("136BC", "136AU"):
        paths[task] = by_sha(getattr(args, task[3:].lower() + "_dir"),
                              bf["sources"][task]["sha256"], task)
    bc, bc_sha = load(paths["136BC"])
    paths["136AY"] = by_sha(args.ay_dir, bc["sources"]["136AY"]["sha256"], "136AY")
    docs = {task: load(path)[0] for task, path in paths.items()}
    shas = {"136BF": bf_sha, "136BC": bc_sha,
            "136AY": hashlib.sha256(paths["136AY"].read_bytes()).hexdigest(),
            "136AU": hashlib.sha256(paths["136AU"].read_bytes()).hexdigest()}
    missing = candidates(docs["136BF"], docs["136BC"],
                         docs["136AY"], docs["136AU"], shas)
    results, consecutive_failures = [], 0
    for item in missing[:args.limit]:
        outcome = fetch_one(item, args.timeout)
        results.append({"source": item, **outcome})
        consecutive_failures = 0 if outcome["result"] == "EVIDENCE_FETCHED" else \
            consecutive_failures + 1
        if consecutive_failures >= 2:
            break
    complete = len(results) == len(missing) and all(
        row["result"] == "EVIDENCE_FETCHED" for row in results)
    report = {"project": "AxieOS", "version": "0.14", "task": "136BH",
              "sources": {task: {"filename": path.name, "sha256": shas[task]}
                          for task, path in paths.items()},
              "coverage": {"target_transfer_only_hashes": len(missing),
                           "requests_attempted": len(results),
                           "responses_validated": sum(row["result"] ==
                               "EVIDENCE_FETCHED" for row in results),
                           "failed_or_unvalidated": sum(row["result"] !=
                               "EVIDENCE_FETCHED" for row in results),
                           "unattempted": len(missing) - len(results),
                           "complete": complete},
              "lookup_results": results,
              "unattempted_hashes": [r["txhash"] for r in missing[len(results):]],
              "accepted_financial_totals": None,
              "database_opened": False, "database_writes": 0,
              "network_calls_attempted": len(results),
              "checkpoint96": "OPEN",
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136BH_Transaction_Detail_Evidence_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
            "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    c = report["coverage"]
    mp.write_text("\n".join([
        "# AxieOS V0.14 — Task136BH Recent transaction detail evidence", "",
        f"Target transfer-only hashes: **{c['target_transfer_only_hashes']}**. "
        f"Requests/valid responses: **{c['requests_attempted']}/"
        f"{c['responses_validated']}**. Unattempted: **{c['unattempted']}**.", "",
        "Raw response bodies and SHA-256 values appear in the companion JSON. "
        "Any explorer fee is unverified raw evidence; gas payer and monetary "
        "treatment remain unresolved.", "",
        "Verified income, expenses, profit and PHP recovery: **UNKNOWN**. "
        "Checkpoint 96: **OPEN**.", "",
        f"Database opened: NO | Writes: 0 | Network attempts: {len(results)}", ""]),
        encoding="utf-8")
    print("AXIEOS V0.14 - TASK136BH - TRANSACTION DETAIL EVIDENCE")
    print(f"Transfer-only hashes: {c['target_transfer_only_hashes']} | "
          f"Requests: {c['requests_attempted']} | Validated: "
          f"{c['responses_validated']} | Unattempted: {c['unattempted']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print(f"Database opened: NO | Writes: 0 | Network calls attempted: {len(results)}")
    print("VALIDATION: " + ("PASS" if complete else "INCOMPLETE") +
          " (bounded evidence collection only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
