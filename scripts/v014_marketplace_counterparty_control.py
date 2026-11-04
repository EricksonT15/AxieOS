r"""Task136AI: compare new marketplace-shaped counterparties to historical controls.

From the AxieOS repository root:
    py -B .\scripts\v014_marketplace_counterparty_control.py

Reads Task136AH, Task136W schema 1.1, Task136Y, and production raw transfer
rows using SQLite mode=ro/query_only. No accounting writes or network access.
Historical agreement is structural evidence, not accepted financial treatment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from v014_post_apply_reconcile import connect_ro, require


def load(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing report: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def find(directory: Path, task: str, schema: str | None = None) -> Path:
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        d, _ = load(path)
        if d.get("task") == task and (schema is None or d.get("report_schema_version") == schema):
            matches.append((d.get("created_at_utc", ""), path))
    require(matches, f"missing Task{task} JSON in {directory}; pass --{task.lower()} PATH")
    return max(matches)[1]


def historical_control(conn, y: dict, owned: set[str]) -> list[dict]:
    rows = y["historical_control_rows"]
    expected = y["coverage"]["historical_exact_pair_controls"]
    require(len(rows) == expected and expected > 0 and
            y["coverage"]["aligned_controls"] == expected and
            y["coverage"]["conflicting_controls"] == 0 and
            y["coverage"]["incomplete_controls"] == 0 and
            len({str(r["txhash"]).lower() for r in rows}) == expected,
            "Task136Y historical controls incomplete, conflicting, or duplicated")
    hashes = {str(r["txhash"]).lower() for r in rows}
    grouped = defaultdict(list)
    cursor = conn.execute(
        "SELECT tx_hash,token_symbol,token_type,token_address,from_address,to_address,"
        "token_id,amount_raw,decimals FROM ronin_token_transfers_raw")
    for h, symbol, typ, contract, from_addr, to_addr, token_id, raw, decimals in cursor:
        if h is not None and str(h).lower() in hashes:
            grouped[str(h).lower()].append({"symbol": symbol, "type": typ,
                "contract": str(contract or "").lower(),
                "from": str(from_addr or "").lower(), "to": str(to_addr or "").lower(),
                "token_id": str(token_id) if token_id is not None else None,
                "raw": str(raw), "decimals": decimals})
    require(set(grouped) == hashes, "historical raw transfer control hash missing")
    result = []
    for item in rows:
        h = str(item["txhash"]).lower()
        ts = grouped[h]
        weth = [t for t in ts if t["symbol"] == "WETH"]
        axie = [t for t in ts if t["symbol"] == "AXIE"]
        require(len(ts) == 2 and len(weth) == len(axie) == 1,
                f"{h}: historical control raw pair changed")
        pay, asset = weth[0], axie[0]
        shape = item["shape"]
        if shape == "PURCHASE_SHAPED":
            require(pay["from"] in owned and pay["to"] not in owned and
                    asset["to"] in owned and asset["from"] not in owned,
                    f"{h}: historical purchase endpoints changed")
            payment_counterparty = pay["to"]
        else:
            require(shape == "SALE_SHAPED" and pay["to"] in owned and
                    pay["from"] not in owned and asset["from"] in owned and
                    asset["to"] not in owned, f"{h}: historical sale endpoints changed")
            payment_counterparty = pay["from"]
        require(pay["type"] == "ERC-20" and pay["decimals"] == 18 and
                asset["type"] == "ERC-721" and asset["raw"] == "1" and
                str(int(asset["token_id"])) == str(item["axie_id"]) and
                pay["contract"], f"{h}: historical asset details changed")
        result.append({"txhash": h, "shape": shape,
                       "payment_counterparty": payment_counterparty,
                       "weth_contract": pay["contract"]})
    return result


def build(ah: dict, w: dict, y: dict, paths: dict[str, Path], digests: dict[str, str],
          conn) -> dict:
    require(ah.get("task") == "136AH" and w.get("task") == "136W" and
            w.get("report_schema_version") == "1.1" and y.get("task") == "136Y" and
            all(d.get("checkpoint96") == "OPEN" and d.get("accepted_financial_totals") is None
                for d in (ah, w, y)), "source task or financial status differs")
    require(ah["sources"]["136W"]["sha256"] == digests["136W"] and
            ah["sources"]["136W"]["filename"] == paths["136W"].name and
            Path(y["source_cache_report"]).name == paths["136W"].name,
            "Task136AH/Y do not refer to the same Task136W snapshot")
    pairs = ah["candidate_pairs"]
    require(len(pairs) == ah["coverage"]["exact_two_transfer_pairs"] and
            len({str(r["txhash"]).lower() for r in pairs}) == len(pairs),
            "Task136AH pair count or uniqueness differs")
    raw_by_hash = {str(r["txhash"]).lower(): r for r in w["candidate_rows"]}
    require(len(raw_by_hash) == w["coverage"]["candidate_hashes"],
            "Task136W cached hashes differ")
    owned = {str(r["address"]).lower() for r in w["registered_owned_wallets"]}
    require(owned, "no registered owned wallets")
    controls = historical_control(conn, y, owned)
    historic_contracts = {r["weth_contract"] for r in controls}
    historic_counterparties = {r["payment_counterparty"] for r in controls}
    require(historic_contracts and historic_counterparties, "empty historical payment controls")
    detail = []
    for item in pairs:
        h = str(item["txhash"]).lower()
        raw = raw_by_hash.get(h)
        require(raw is not None, f"{h}: raw cache hash missing")
        transfers = raw["raw_transfer_rows"]
        payment = [r for r in transfers if r["transfer_key"] == item["weth_transfer_key"]]
        require(len(payment) == 1 and payment[0]["amount_raw"] == item["weth_transfer_raw"],
                f"{h}: payment transfer key or quantity differs")
        p = payment[0]
        shape = item["shape"]
        require(shape in ("BUY_CANDIDATE", "SALE_CANDIDATE") and
                p["token_symbol"] == "WETH" and p["token_type"] == "ERC-20" and
                p["decimals"] == 18, f"{h}: WETH shape or token differs")
        if shape == "BUY_CANDIDATE":
            require(str(p["from_address"]).lower() in owned and
                    str(p["to_address"]).lower() not in owned, f"{h}: buy WETH endpoint differs")
            counterparty = str(p["to_address"]).lower()
        else:
            require(str(p["to_address"]).lower() in owned and
                    str(p["from_address"]).lower() not in owned,
                    f"{h}: sale WETH endpoint differs")
            counterparty = str(p["from_address"]).lower()
        contract = str(p["token_address"]).lower()
        same_contract = contract in historic_contracts
        same_counterparty = counterparty in historic_counterparties
        lane = item["review_lane"]
        # A fungible swap is still distinct even if one endpoint has appeared historically.
        status = ("FUNGIBLE_ROUTE_REVIEW" if lane == "FUNGIBLE_EXCHANGE_REVIEW" else
                  "HISTORICAL_ENDPOINT_MATCH_CANDIDATE" if same_contract and same_counterparty else
                  "NOVEL_PAYMENT_ROUTE_REVIEW")
        detail.append({"txhash": h, "asset_symbol": item["asset_symbol"],
                       "shape": shape, "review_lane": lane,
                       "payment_counterparty": counterparty, "weth_contract": contract,
                       "historical_weth_contract_match": same_contract,
                       "historical_payment_counterparty_match": same_counterparty,
                       "control_status": status,
                       "financial_treatment": "UNREVIEWED_CANDIDATE"})
    counts = Counter(r["control_status"] for r in detail)
    return {"project": "AxieOS", "version": "0.14", "task": "136AI",
            "sources": {k: {"filename": paths[k].name, "sha256": digests[k]}
                        for k in sorted(paths)},
            "coverage": {"historical_exact_aligned_controls": len(controls),
                         "historical_payment_counterparties": dict(sorted(Counter(
                             r["payment_counterparty"] for r in controls).items())),
                         "historical_weth_contracts": dict(sorted(Counter(
                             r["weth_contract"] for r in controls).items())),
                         "new_marketplace_shaped_pairs": len(detail),
                         "new_status_counts": dict(sorted(counts.items())),
                         "new_payment_counterparties": dict(sorted(Counter(
                             r["payment_counterparty"] for r in detail).items()))},
            "new_candidates": detail, "accepted_new_financial_events": 0,
            "accepted_financial_totals": None, "database_opened_read_only": True,
            "database_writes": 0, "network_calls": 0, "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136AI Historical counterparty control", "",
             f"Historical Axie/WETH controls: **{c['historical_exact_aligned_controls']}**. "
             f"New paired candidates: **{c['new_marketplace_shaped_pairs']}**.", "",
             "| New payment-route status | Hashes |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in c["new_status_counts"].items()]
    lines += ["", "| Historical WETH counterparty | Controls |", "|---|---:|"]
    lines += [f"| `{k}` | {v} |" for k, v in c["historical_payment_counterparties"].items()]
    lines += ["", "| New WETH counterparty | Candidates |", "|---|---:|"]
    lines += [f"| `{k}` | {v} |" for k, v in c["new_payment_counterparties"].items()]
    lines += ["", "An endpoint match is structural precedent only. It does not prove that "
              "a transfer is a marketplace trade, who paid gas, sale gross, fees, basis, "
              "profit, or PHP recovery. Fungible exchanges retain a separate lane.", "",
              "Accepted new financial events: **0**. Verified totals: **UNKNOWN**.", "",
              "Database opened: production read only | Writes: 0 | Network: 0", "",
              "VALIDATION: PASS (historical payment-route comparison only; Checkpoint 96 OPEN).", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("data/blockchain/database/axieos.db"))
    parser.add_argument("--ah", type=Path)
    parser.add_argument("--ah-dir", type=Path, default=Path("reports/axieos_v014/task136ah"))
    parser.add_argument("--w", type=Path)
    parser.add_argument("--w-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--y", type=Path)
    parser.add_argument("--y-dir", type=Path, default=Path("reports/axieos_v014/task136y"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136ai"))
    args = parser.parse_args()
    paths = {"136AH": args.ah or find(args.ah_dir, "136AH"),
             "136W": args.w or find(args.w_dir, "136W", "1.1"),
             "136Y": args.y or find(args.y_dir, "136Y")}
    docs, shas = {}, {}
    for k, path in paths.items():
        docs[k], shas[k] = load(path)
    with closing(connect_ro(args.db)) as conn:
        conn.execute("BEGIN")
        report = build(docs["136AH"], docs["136W"], docs["136Y"], paths, shas, conn)
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AI_Historical_Counterparty_Control_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136AI - HISTORICAL COUNTERPARTY CONTROL")
    print(f"Historical controls: {c['historical_exact_aligned_controls']} | "
          f"New candidate pairs: {c['new_marketplace_shaped_pairs']}")
    print(f"Route statuses: {c['new_status_counts']}")
    print("Verified income, expenses, profit, and PHP recovery: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: production read only | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (historical payment-route comparison only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
