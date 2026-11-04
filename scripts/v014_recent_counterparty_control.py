r"""Task136BE: compare recent candidate payment endpoints to historical controls.

From the AxieOS repository root:
    py -B .\scripts\v014_recent_counterparty_control.py

Reads production SQLite mode=ro and SHA-linked Task136BD/AU/BB/Y/W reports.
Historical endpoint agreement is structural evidence only. No accounting,
financial acceptance, production write, or network access.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from v014_marketplace_counterparty_control import historical_control
from v014_post_apply_reconcile import connect_ro, require
from v014_raw_import_clone import by_sha, latest, load


def analyze(conn, bd: dict, au: dict, bb: dict, y: dict, w: dict,
            shas: dict[str, str], paths: dict[str, Path]) -> dict:
    require(all(doc.get("task") == task and doc.get("checkpoint96") == "OPEN"
                and doc.get("accepted_financial_totals") is None
                for task, doc in (("136BD", bd), ("136AU", au),
                                  ("136BB", bb), ("136Y", y), ("136W", w))) and
            w.get("report_schema_version") == "1.1" and
            bd["sources"]["136AU"]["sha256"] == shas["136AU"] and
            bd["sources"]["136BB"]["sha256"] == shas["136BB"] and
            Path(y["source_cache_report"]).name == paths["136W"].name,
            "Task136BD/AU/BB/Y/W source chain or finance boundary differs")
    require(conn.execute("SELECT COUNT(*) FROM blockchain_transactions").fetchone()[0]
                == bb["coverage"]["ledger_after"] and
            conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
            "production ledger or SQLite integrity changed")
    owned = {str(row["address"]).lower() for row in w["registered_owned_wallets"]}
    live_owned = {str(row[0]).lower() for row in conn.execute(
        "SELECT address FROM ronin_wallet_registry WHERE ownership_type='USER_OWNED'")}
    require(owned and live_owned == owned, "registered owned-wallet controls changed")
    controls = historical_control(conn, y, owned)
    routes = {(row["weth_contract"], row["payment_counterparty"])
              for row in controls}
    require(routes and len(controls) == y["coverage"]["aligned_controls"],
            "historical endpoint controls differ")
    pairs = bd["candidate_pairs"]
    require(len(pairs) == bd["coverage"]["marketplace_shaped"] ==
            bd["coverage"]["exact_weth_asset_pairs"] and
            len({str(row["txhash"]).lower() for row in pairs}) == len(pairs),
            "recent exact candidate pair coverage differs")
    raw = {str(row["transfer_key"]): row
           for row in au["normalized_new_transfers"]}
    require(len(raw) == au["coverage"]["unique_transfer_rows"],
            "new raw transfer identities duplicate")
    detail = []
    for candidate in sorted(pairs, key=lambda row: row["txhash"].lower()):
        h = str(candidate["txhash"]).lower()
        matches = [row for row in raw.values() if str(row["tx_hash"]).lower() == h]
        require(len(matches) == 2 and candidate["exact_weth_asset_pair"] is True,
                f"{h}: expected exact raw WETH/asset pair differs")
        weth = [row for row in matches if row["token_symbol"] == "WETH"]
        asset = [row for row in matches if row["token_symbol"] != "WETH"]
        require(len(weth) == len(asset) == 1 and
                candidate["asset_symbol"] == asset[0]["token_symbol"] and
                candidate["asset_type"] == asset[0]["token_type"] and
                candidate["asset_token_id"] == asset[0].get("token_id"),
                f"{h}: Task136BD asset crosswalk differs")
        p = weth[0]
        live = conn.execute(
            "SELECT tx_hash,token_symbol,token_type,token_address,"
            "from_address,to_address,amount_raw,decimals FROM ronin_token_transfers_raw "
            "WHERE transfer_key=?", (p["transfer_key"],)).fetchall()
        require(len(live) == 1,
                f"{h}: expected one production WETH transfer key; found {len(live)}")
        try:
            saved_decimals = int(p["decimals"])
            live_decimals = int(live[0][7])
        except (TypeError, ValueError):
            raise ValueError(f"STOP: {h}: WETH decimals missing or invalid") from None
        fields = ("tx_hash", "token_symbol", "token_type", "token_address",
                  "from_address", "to_address", "amount_raw", "decimals")
        actual = (str(live[0][0]).lower(), live[0][1], live[0][2],
                  str(live[0][3]).lower(), str(live[0][4]).lower(),
                  str(live[0][5]).lower(), str(live[0][6]), live_decimals)
        expected = (h, "WETH", "ERC-20", str(p["token_address"]).lower(),
                    str(p["from_address"]).lower(),
                    str(p["to_address"]).lower(), str(p["amount_raw"]), 18)
        differences = [field for field, got, want in zip(fields, actual, expected)
                       if got != want]
        if saved_decimals != 18:
            differences.append("snapshot_decimals")
        require(not differences,
                f"{h}: production WETH raw transfer differs in {differences}")
        shape = candidate["shape"]
        sender, recipient = str(p["from_address"]).lower(), str(p["to_address"]).lower()
        if shape == "BUY_CANDIDATE":
            require(sender in owned and recipient not in owned,
                    f"{h}: purchase-shaped WETH direction differs")
            counterparty = recipient
        else:
            require(shape == "SALE_CANDIDATE" and recipient in owned and sender not in owned,
                    f"{h}: sale-shaped WETH direction differs")
            counterparty = sender
        contract = str(p["token_address"]).lower()
        route_match = (contract, counterparty) in routes
        status = ("FUNGIBLE_ROUTE_REVIEW"
                  if candidate["review_lane"] == "FUNGIBLE_EXCHANGE_REVIEW" else
                  "HISTORICAL_ENDPOINT_MATCH_CANDIDATE" if route_match else
                  "NOVEL_PAYMENT_ROUTE_REVIEW")
        require(candidate["review_lane"] in
                ("NFT_PAIR_CANDIDATE", "FUNGIBLE_EXCHANGE_REVIEW"),
                f"{h}: unsupported recent review lane")
        detail.append({"txhash": h, "shape": shape,
                       "asset_symbol": candidate["asset_symbol"],
                       "asset_token_id": candidate["asset_token_id"],
                       "review_lane": candidate["review_lane"],
                       "weth_contract": contract,
                       "payment_counterparty": counterparty,
                       "historical_exact_route_match": route_match,
                       "control_status": status,
                       "financial_treatment": "UNREVIEWED_CANDIDATE"})
    return {"project": "AxieOS", "version": "0.14", "task": "136BE",
            "sources": {k: {"filename": paths[k].name, "sha256": shas[k]}
                        for k in sorted(paths)},
            "coverage": {"historical_aligned_controls": len(controls),
                         "recent_exact_pairs": len(detail),
                         "route_statuses": dict(sorted(Counter(
                             row["control_status"] for row in detail).items())),
                         "by_asset_and_status": dict(sorted(Counter(
                             row["asset_symbol"] + "/" + row["control_status"]
                             for row in detail).items()))},
            "new_candidates": detail, "accepted_new_financial_events": 0,
            "accepted_financial_totals": None,
            "production_database_opened_read_only": True,
            "database_writes": 0, "network_calls": 0, "checkpoint96": "OPEN"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path,
                        default=Path("data/blockchain/database/axieos.db"))
    for suffix in ("bd", "au", "bb", "y", "w"):
        parser.add_argument(f"--{suffix}-dir", type=Path,
                            default=Path(f"reports/axieos_v014/task136{suffix}"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("reports/axieos_v014/task136be"))
    args = parser.parse_args()
    paths = {"136BD": latest(args.bd_dir, "136BD")}
    bd, bd_sha = load(paths["136BD"])
    paths["136AU"] = by_sha(args.au_dir, bd["sources"]["136AU"]["sha256"], "136AU")
    paths["136BB"] = by_sha(args.bb_dir, bd["sources"]["136BB"]["sha256"], "136BB")
    paths["136Y"] = latest(args.y_dir, "136Y")
    y, y_sha = load(paths["136Y"])
    paths["136W"] = args.w_dir / Path(y["source_cache_report"]).name
    docs, shas = {}, {}
    for task, path in paths.items():
        docs[task], shas[task] = load(path)
    with closing(connect_ro(args.db)) as conn:
        conn.execute("BEGIN")
        report = analyze(conn, docs["136BD"], docs["136AU"],
                         docs["136BB"], docs["136Y"], docs["136W"],
                         shas, paths)
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136BE_Recent_Counterparty_Control_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
            "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    c = report["coverage"]
    mp.write_text("\n".join([
        "# AxieOS V0.14 — Task136BE Recent counterparty control", "",
        f"Historical aligned Axie/WETH controls: **{c['historical_aligned_controls']}**. "
        f"Recent raw pairs: **{c['recent_exact_pairs']}**.", "",
        "| Payment route status | Hashes |", "|---|---:|",
        *[f"| {status} | {count} |" for status, count in c["route_statuses"].items()],
        "", "An endpoint match is structural precedent only. Fungible routes "
        "remain separate. No new financial events are accepted.", "",
        "Verified income, expenses, profit and PHP recovery: **UNKNOWN**. "
        "Checkpoint 96: **OPEN**.", "",
        "Production read only | Writes: 0 | Network: 0", ""]), encoding="utf-8")
    print("AXIEOS V0.14 - TASK136BE - RECENT COUNTERPARTY CONTROL")
    print(f"Historical controls: {c['historical_aligned_controls']} | "
          f"Recent pairs: {c['recent_exact_pairs']}")
    print(f"Route statuses: {c['route_statuses']}")
    print("Verified income, expenses, profit and PHP recovery: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Production read only | Writes: 0 | Network: 0")
    print("VALIDATION: PASS (historical route comparison only; Checkpoint 96 OPEN)")


if __name__ == "__main__":
    main()
