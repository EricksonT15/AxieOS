r"""Task136AU: offline deduplication of the bounded explorer catch-up snapshot.

From the AxieOS repository root:
    py -B .\scripts\v014_explorer_snapshot_crosswalk.py

Reads Task136AT and its SHA-matched Task136AS/W snapshots. Rechecks each
saved response body and uses existing pure normalization helpers. No SQLite,
network, transaction import, financial acceptance, or wallet operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ronin_api_sync import normalize_token_transfer, normalize_transaction
from v014_explorer_readonly_probe import utc


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError("STOP: " + reason)


def load(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing source: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def latest(directory: Path, task: str) -> Path:
    matches = []
    for p in directory.glob("*.json") if directory.is_dir() else []:
        doc, _ = load(p)
        if doc.get("task") == task:
            matches.append((doc.get("created_at_utc", ""), p))
    require(matches, f"missing Task{task} JSON in {directory}")
    return max(matches)[1]


def by_sha(directory: Path, digest: str, task: str) -> Path:
    matches = []
    for p in directory.glob("*.json") if directory.is_dir() else []:
        if hashlib.sha256(p.read_bytes()).hexdigest() == digest:
            doc, _ = load(p)
            if doc.get("task") == task:
                matches.append(p)
    require(len(matches) == 1, f"expected one SHA-matched Task{task} in {directory}")
    return matches[0]


def valid_hash(value: object) -> bool:
    return isinstance(value, str) and len(value) == 66 and value[:2].lower() == "0x" and all(
        c in "0123456789abcdef" for c in value[2:].lower())


def valid_address(value: object) -> bool:
    return isinstance(value, str) and len(value) == 42 and value[:2].lower() == "0x" and all(
        c in "0123456789abcdef" for c in value[2:].lower())


def normalize(kind: str, item: dict, cutoff: datetime) -> tuple[dict | None, str | None]:
    try:
        row = normalize_transaction(item) if kind == "transactions" else normalize_token_transfer(item)
        at = utc(row.get("timestamp"))
        h = row.get("tx_hash")
        if not valid_hash(h) or at is None or at <= cutoff:
            return None, "BAD_HASH_OR_TIMESTAMP"
        if not valid_address(row.get("from_address")) or not valid_address(row.get("to_address")):
            return None, "BAD_ENDPOINT"
        block = row.get("block_number")
        if isinstance(block, bool) or not isinstance(block, int) or block <= 0:
            return None, "BAD_BLOCK_NUMBER"
        if kind == "token-transfers":
            key = row.get("transfer_key")
            if (not isinstance(key, str) or not key.startswith(str(h) + ":") or
                    not isinstance(row.get("log_index"), int) or
                    not valid_address(row.get("token_address")) or
                    row.get("token_type") not in ("ERC-20", "ERC-721", "ERC-1155") or
                    str(row.get("amount_raw") or "").isdecimal() is False):
                return None, "BAD_TOKEN_TRANSFER_IDENTITY"
        row["tx_hash"] = h.lower()
        return row, None
    except (TypeError, ValueError, KeyError, AttributeError):
        return None, "NORMALIZATION_ERROR"


def build(at: dict, a: dict, w: dict, shas: dict[str, str]) -> dict:
    require(at.get("task") == "136AT" and a.get("task") == "136AS" and
            w.get("task") == "136W" and w.get("report_schema_version") == "1.1" and
            all(doc.get("checkpoint96") == "OPEN" and
                doc.get("accepted_financial_totals") is None for doc in (at, a, w)) and
            at["sources"]["136AS"]["sha256"] == shas["136AS"] and
            at["sources"]["136W"]["sha256"] == shas["136W"] and
            a["source_136w_sha256"] == shas["136W"] and
            at["coverage"]["all_routes_reached_time_boundary_or_end"] is True,
            "Task136AT/AS/W provenance, completeness or finance boundary differs")
    cutoff = utc(w["cutoff"]["raw_latest_utc"])
    require(cutoff is not None and at["snapshot_raw_latest_utc"] == cutoff.isoformat(),
            "snapshot cutoff differs")
    prior_hashes = {str(r["txhash"]).lower() for r in w["candidate_rows"]}
    prior_keys = {str(t["transfer_key"]).lower()
                  for r in w["candidate_rows"] for t in r["raw_transfer_rows"]}
    require(len(prior_hashes) == w["coverage"]["candidate_hashes"] and
            len(prior_keys) == sum(len(r["raw_transfer_rows"]) for r in w["candidate_rows"]),
            "Task136W identity duplicates")
    expected_routes = {(str(r["address"]).lower(), str(r["wallet_role"]), kind)
                       for r in w["registered_owned_wallets"]
                       for kind in ("transactions", "token-transfers")}
    require(len(expected_routes) == len(at["routes"]) == at["coverage"]["routes"],
            "Task136AT route count differs")
    seen_routes = set()
    selected = {"transactions": defaultdict(list), "token-transfers": defaultdict(list)}
    invalid = []
    read_pages = 0
    counted_newer = 0
    for route in at["routes"]:
        address = str(route["wallet_address"]).lower()
        role, kind = str(route["wallet_role"]), route["route"]
        identity = address, role, kind
        require(identity in expected_routes and identity not in seen_routes and
                route["time_boundary_or_source_end_reached"] is True and
                route["stop_reason"] in ("REACHED_SNAPSHOT_TIME_BOUNDARY", "SOURCE_PAGINATION_END") and
                route["pages_attempted"] == route["pages_read"] == len(route["pages"]),
                "route identity or completion differs")
        seen_routes.add(identity)
        for page in route["pages"]:
            require(page["status"] == "PASS_PAGE" and
                    isinstance(page["raw_body_utf8"], str) and
                    hashlib.sha256(page["raw_body_utf8"].encode("utf-8")).hexdigest() ==
                    page["response_sha256"], "saved explorer body digest differs")
            doc = json.loads(page["raw_body_utf8"])
            items = doc["items"]
            require(isinstance(items, list) and len(items) == page["page_items"],
                    "saved explorer page item count differs")
            read_pages += 1
            newer = 0
            for item in items:
                stamp = utc(item.get("timestamp")) if isinstance(item, dict) else None
                if stamp is None:
                    invalid.append({"route": kind, "page_sha256": page["response_sha256"],
                                    "reason": "BAD_SOURCE_TIMESTAMP"})
                    continue
                if stamp <= cutoff:
                    continue
                newer += 1
                row, reason = normalize(kind, item, cutoff)
                if reason:
                    invalid.append({"route": kind, "page_sha256": page["response_sha256"],
                                    "item_sha256": hashlib.sha256(json.dumps(item, sort_keys=True)
                                        .encode("utf-8")).hexdigest(), "reason": reason})
                    continue
                key = (row["tx_hash"] if kind == "transactions" else
                       row["transfer_key"].lower())
                selected[kind][key].append(row)
            require(newer == page["items_newer_than_snapshot"],
                    "saved page newer-item count differs")
            counted_newer += newer
    require(seen_routes == expected_routes and
            read_pages == at["coverage"]["pages_read"] and
            counted_newer == at["coverage"]["items_newer_than_snapshot_on_read_pages"],
            "Task136AT page coverage differs")
    unique = {}
    conflicts = []
    for kind, groups in selected.items():
        out = []
        for key, variants in sorted(groups.items()):
            serial = {json.dumps(v, sort_keys=True, default=str) for v in variants}
            if len(serial) != 1:
                conflicts.append({"route": kind, "identity": key,
                                  "variants": len(serial)})
                continue
            out.append({"source_routes_seen": len(variants), **variants[0]})
        unique[kind] = out
    overlapping_hashes = sorted({r["tx_hash"] for rows in unique.values() for r in rows}
                                & prior_hashes)
    overlapping_keys = sorted({str(r["transfer_key"]).lower()
                               for r in unique["token-transfers"]} & prior_keys)
    counts = {kind: sum(map(len, groups.values())) for kind, groups in selected.items()}
    duplicate_occurrences = sum(len(variants) - 1
                                for groups in selected.values()
                                for variants in groups.values())
    return {"project": "AxieOS", "version": "0.14", "task": "136AU",
            "snapshot_raw_latest_utc": cutoff.isoformat(),
            "coverage": {"newer_page_items": counted_newer,
                         "normalized_occurrences": counts,
                         "unique_transaction_rows": len(unique["transactions"]),
                         "unique_transfer_rows": len(unique["token-transfers"]),
                         "duplicate_occurrences": duplicate_occurrences,
                         "invalid_items": len(invalid), "conflicting_identities": len(conflicts),
                         "hash_overlap_with_prior_snapshot": len(overlapping_hashes),
                         "transfer_key_overlap_with_prior_snapshot": len(overlapping_keys),
                         "ready_for_guarded_raw_import_plan": not (
                             invalid or conflicts or overlapping_hashes or overlapping_keys)},
            "normalized_new_transactions": unique["transactions"],
            "normalized_new_transfers": unique["token-transfers"],
            "invalid_items": invalid, "conflicting_identities": conflicts,
            "overlapping_prior_hashes": overlapping_hashes,
            "overlapping_prior_transfer_keys": overlapping_keys,
            "accepted_financial_totals": None, "database_opened": False,
            "database_writes": 0, "network_calls": 0, "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    return "\n".join([
        "# AxieOS V0.14 — Task136AU Explorer snapshot crosswalk", "",
        f"Newer page items: **{c['newer_page_items']}**; unique normalized "
        f"transaction/transfer rows: **{c['unique_transaction_rows']}/"
        f"{c['unique_transfer_rows']}**.", "",
        f"Invalid items: **{c['invalid_items']}**; conflicting identities: "
        f"**{c['conflicting_identities']}**; overlap with prior snapshot hashes/keys: "
        f"**{c['hash_overlap_with_prior_snapshot']}/{c['transfer_key_overlap_with_prior_snapshot']}**.", "",
        "The JSON preserves candidate raw-table rows and the source snapshot digests. "
        "The data is still unaccepted evidence. It is not imported into SQLite and "
        "does not establish gas payer, marketplace fees, basis, profit, or cash recovery.", "",
        "Verified income, expenses, profit, and PHP recovery: **UNKNOWN**.", "",
        "Database opened: NO | Writes: 0 | Network: 0", "",
        "VALIDATION: offline deduplication only; Checkpoint 96 OPEN.", ""])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--at", type=Path)
    parser.add_argument("--at-dir", type=Path, default=Path("reports/axieos_v014/task136at"))
    parser.add_argument("--as-dir", type=Path, default=Path("reports/axieos_v014/task136as"))
    parser.add_argument("--w-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136au"))
    args = parser.parse_args()
    ap = args.at or latest(args.at_dir, "136AT")
    at, at_sha = load(ap)
    sp = by_sha(args.as_dir, at["sources"]["136AS"]["sha256"], "136AS")
    wp = by_sha(args.w_dir, at["sources"]["136W"]["sha256"], "136W")
    a, as_sha = load(sp)
    w, w_sha = load(wp)
    report = build(at, a, w, {"136AT": at_sha, "136AS": as_sha, "136W": w_sha})
    report["sources"] = {"136AT": {"filename": ap.name, "sha256": at_sha},
                         "136AS": {"filename": sp.name, "sha256": as_sha},
                         "136W": {"filename": wp.name, "sha256": w_sha}}
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AU_Explorer_Snapshot_Crosswalk_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136AU - EXPLORER SNAPSHOT CROSSWALK")
    print(f"Newer page items: {c['newer_page_items']} | Unique transactions/transfers: "
          f"{c['unique_transaction_rows']}/{c['unique_transfer_rows']}")
    print(f"Invalid/conflicting: {c['invalid_items']}/{c['conflicting_identities']} | "
          f"Prior overlap hashes/keys: {c['hash_overlap_with_prior_snapshot']}/"
          f"{c['transfer_key_overlap_with_prior_snapshot']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print("Database opened: NO | Writes: 0 | Network: 0")
    print("VALIDATION: offline deduplication only; Checkpoint 96 OPEN")


if __name__ == "__main__":
    main()
