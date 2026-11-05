r"""One-run guarded V0.15 ownership roster refresh.

Save in scripts/ beside AxieOS_V015_Source_Catchup.py and
AxieOS_V015_Source_Reconciliation.py. From the AxieOS repository root:
    py -B .\scripts\AxieOS_V015_Guarded_Roster_Refresh.py --apply

Checks the exact saved evidence, re-enumerates both wallets by pinned RPC,
fetches metadata for all 29 new Axies, rehearses 29 inserts and 3 UNKNOWN
updates in a disposable clone, creates a verified backup outside the repo,
and applies only those 32 roster changes. If both metadata endpoints cannot
provide complete values, --allow-unknown-metadata stores NULLs only when the
local schema permits them. No finance, ledger, or marketplace writer is called.
"""

import argparse
import hashlib
import json
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener
from uuid import uuid4

import AxieOS_V015_Source_Catchup as chain
import AxieOS_V015_Source_Reconciliation as prior


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports/axieos_v015/source_catchup"
CATCHUP = REPORTS / "AxieOS_V015_Source_Catchup_20261105T030132_927019Z.json"
RECON = REPORTS / "AxieOS_V015_Source_Reconciliation_20261105T033632_937141Z.json"
EVIDENCE = REPORTS / "AxieOS_V015_Ownership_Evidence_20261105T034538_032864Z.json"
EVIDENCE_SHA256 = "f140c32503891503d2e980f1e90a555460fc7279e69be4e5e4c423101296d5bf"
METADATA_URL = "https://graphql-gateway.axieinfinity.com/graphql"
EXPLORER_INSTANCE_URL = ("https://explorer.roninchain.com/api/v2/tokens/"
                         "0x32950db2a7164ae833121501c797d79e7b79d74c/instances/")
CLASSES = {"Aquatic", "Beast", "Bird", "Bug", "Dawn", "Dusk", "Mech", "Plant", "Reptile"}
ROSTER = "gameplay_owned_axies"
OTHERS = tuple(t for t in prior.WATCHED if t != ROSTER)
ADD = ("INSERT INTO gameplay_owned_axies (axie_id,wallet_address,ownership_status,"
       "axie_class,level,breed_count,last_seen_datetime,data_source) "
       "VALUES (?,?, 'OWNED',?,?,?,?,?)")
STALE = ("UPDATE gameplay_owned_axies SET ownership_status='UNKNOWN',last_updated=CURRENT_TIMESTAMP "
         "WHERE axie_id=? AND ownership_status='OWNED'")


def load(path, task, digest=None):
    prior.require(path.is_file(), f"required {task} report missing: {path}")
    body = path.read_bytes()
    sha = hashlib.sha256(body).hexdigest()
    prior.require(digest is None or sha == digest, f"{task} report SHA-256 differs")
    doc = json.loads(body.decode("utf-8-sig"))
    prior.require(doc.get("task") == task and doc.get("version") == "0.15", f"unexpected {task} report")
    return doc, sha


def verify_evidence(catchup, catch_sha, recon, recon_sha, evidence):
    pin = int(catchup["owned_inventory"]["block"], 16)
    prior.require(recon["source"]["sha256"] == catch_sha and
                  evidence["sources"]["catchup_sha256"] == catch_sha and
                  evidence["sources"]["reconciliation_sha256"] == recon_sha and
                  evidence["pinned_block"] == catchup["owned_inventory"]["block"] and
                  evidence["saved_only_complete_histories"] == 3 and
                  evidence["database_writes"] == 0 and evidence["checkpoint96"] == "OPEN",
                  "pinned source chain differs")
    cases = evidence["cases"]
    chain_only = [c for c in cases if c["lane"] == "CHAIN_ONLY"]
    saved_only = [c for c in cases if c["lane"] == "SAVED_ONLY"]
    prior.require(len(cases) == len({c["axie_id"] for c in cases}) == 32 and
                  {c["axie_id"] for c in chain_only} == set(catchup["owned_inventory"]["chain_only_ids"]) and
                  {c["axie_id"] for c in saved_only} == set(catchup["owned_inventory"]["saved_only_ids"]),
                  "ownership case IDs differ")
    for case in chain_only:
        transfer = case["latest_cached_transfer"]
        prior.require(case["saved_status"] is None and case["saved_class"] is None and
                      case["cached_transfer_count"] == 1 and transfer["wallet_direction"] == "IN" and
                      transfer["to"] == chain.WALLETS[0] and transfer["block_number"] <= pin and
                      case["production_update_approved"] is False,
                      f"{case['axie_id']}: chain-only metadata or transfer differs")
    for case in saved_only:
        events = case["explorer_events_at_or_before_pin"]
        wallet_events = [e for e in events if e["wallet_direction"] in ("IN", "OUT", "INTERNAL")]
        latest = wallet_events[-1] if wallet_events else None
        cached = case["latest_cached_transfer"]
        prior.require(case["saved_status"] == "OWNED" and case["history_status"] == "PAGINATION_END" and
                      len(events) == case["history_events_before_pin"] and latest is not None and
                      latest["wallet_direction"] == "OUT" and cached["wallet_direction"] == "OUT" and
                      latest["txhash"] == cached["txhash"] and
                      latest["block_number"] == cached["block_number"] and
                      case["production_update_approved"] is False,
                      f"{case['axie_id']}: latest wallet outbound evidence differs")
    return sorted(chain_only, key=lambda c: int(c["axie_id"])), sorted(saved_only, key=lambda c: int(c["axie_id"]))


def normalize_owner(owner):
    if isinstance(owner, dict):
        owner = owner.get("hash") or owner.get("address")
    if isinstance(owner, str):
        return owner.lower().replace("ronin:", "0x")
    return None


def validate_metadata(axie_id, wallet, values, source, body):
    owner = normalize_owner(values.get("owner"))
    level, breed = values.get("level"), values.get("breedCount")
    if isinstance(level, str) and level.isdecimal():
        level = int(level)
    if isinstance(breed, str) and breed.isdecimal():
        breed = int(breed)
    prior.require(str(values.get("id")) == axie_id and
                  (owner is None or owner == wallet),
                  f"{axie_id}: {source} ID or owner differs")
    complete = (values.get("class") in CLASSES and type(level) is int and level > 0 and
                type(breed) is int and 0 <= breed <= 7)
    return {"axie_id": axie_id, "axie_class": values.get("class") if complete else None,
            "level": level if complete else None, "breed_count": breed if complete else None,
            "metadata_owner": owner, "source": source, "complete": complete,
            "response_sha256": hashlib.sha256(body).hexdigest()}


def explorer_metadata(opener, axie_id, wallet):
    url = EXPLORER_INSTANCE_URL + axie_id
    request = Request(url, headers={"Accept": "application/json",
                                    "User-Agent": "AxieOS-V015-Guarded-Roster/1"})
    try:
        with opener.open(request, timeout=20) as response:
            prior.require(response.status == 200 and response.geturl() == url and
                          "json" in response.headers.get("Content-Type", "").lower(),
                          f"{axie_id}: explorer metadata response differs")
            body = response.read(500_001)
    except (HTTPError, URLError, TimeoutError) as error:
        return {"axie_id": axie_id, "axie_class": None, "level": None,
                "breed_count": None, "metadata_owner": None, "source": "EXPLORER_UNAVAILABLE",
                "complete": False, "error": f"{type(error).__name__}: {getattr(error, 'code', error)}"}
    prior.require(len(body) <= 500_000, f"{axie_id}: explorer response too large")
    doc = json.loads(body)
    prior.require(isinstance(doc, dict) and str(doc.get("id")) == axie_id,
                  f"{axie_id}: explorer instance ID differs")
    values = {"id": doc["id"], "owner": doc.get("owner")}
    metadata_doc = doc.get("metadata")
    if isinstance(metadata_doc, dict):
        traits = metadata_doc.get("properties")
        if not isinstance(traits, dict):
            traits = metadata_doc
        if isinstance(traits, dict):
            for key, aliases in {"class": ("class", "Class"),
                                 "level": ("level", "Level"),
                                 "breedCount": ("breedCount", "breed_count", "Breed Count")}.items():
                values[key] = next((traits[k] for k in aliases if k in traits), None)
        attributes = metadata_doc.get("attributes")
        for attr in attributes if isinstance(attributes, list) else []:
            if isinstance(attr, dict):
                key = str(attr.get("trait_type", "")).lower().replace(" ", "")
                if key in ("class", "level", "breedcount"):
                    values[{"class": "class", "level": "level", "breedcount": "breedCount"}[key]] = attr.get("value")
    return validate_metadata(axie_id, wallet, values, "RONIN_EXPLORER_INSTANCE", body)


def metadata(opener, axie_id, wallet, graphql_enabled=True):
    if not graphql_enabled:
        return explorer_metadata(opener, axie_id, wallet), False
    query = "query GetAxieDetail($axieId: ID!) { axie(axieId: $axieId) { id class level breedCount owner } }"
    request = Request(METADATA_URL, data=json.dumps({"operationName": "GetAxieDetail",
        "variables": {"axieId": axie_id}, "query": query}).encode("utf-8"), method="POST",
        headers={"Accept": "application/json", "Content-Type": "application/json",
                 "User-Agent": "AxieOS-V015-Guarded-Roster/1"})
    try:
        with opener.open(request, timeout=20) as response:
            prior.require(response.status == 200 and response.geturl() == METADATA_URL and
                          "json" in response.headers.get("Content-Type", "").lower(),
                          f"{axie_id}: metadata HTTP response differs")
            body = response.read(500_001)
    except (HTTPError, URLError, TimeoutError):
        return explorer_metadata(opener, axie_id, wallet), False
    prior.require(len(body) <= 500_000, f"{axie_id}: metadata response too large")
    doc = json.loads(body)
    prior.require(not doc.get("errors") and isinstance(doc.get("data", {}).get("axie"), dict),
                  f"{axie_id}: metadata GraphQL error or missing Axie")
    axie = doc["data"]["axie"]
    result = validate_metadata(axie_id, wallet, axie, "AXIE_GRAPHQL", body)
    if result["complete"]:
        return result, True
    fallback = explorer_metadata(opener, axie_id, wallet)
    return (fallback if fallback["complete"] else result), True


def rows_for_plan(chain_only, saved_only, metadata_rows, block_time):
    observed = prior.iso_utc(block_time).astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    additions = [(c["axie_id"], chain.WALLETS[0], metadata_rows[c["axie_id"]]["axie_class"],
                  metadata_rows[c["axie_id"]]["level"], metadata_rows[c["axie_id"]]["breed_count"],
                  observed, "RONIN_OWNER_V015_AND_" + metadata_rows[c["axie_id"]]["source"])
                 for c in chain_only]
    stale = [(c["axie_id"],) for c in saved_only]
    return additions, stale


def unchanged_roster(conn, changed_ids):
    sha, count = hashlib.sha256(), 0
    cursor = conn.execute("SELECT * FROM gameplay_owned_axies WHERE axie_id NOT IN (" +
                          ",".join("?" for _ in changed_ids) + ") ORDER BY rowid",
                          tuple(sorted(changed_ids)))
    for row in cursor:
        sha.update(repr(row).encode("utf-8"))
        sha.update(b"\n")
        count += 1
    return count, sha.hexdigest()


def guard_db(conn, catchup, chain_only, saved_only, live_ids):
    required = {"axie_id", "wallet_address", "ownership_status", "axie_class", "level",
                "breed_count", "last_seen_datetime", "data_source", "last_updated"}
    prior.require(required <= prior.table_columns(conn, ROSTER), "owned Axie table schema differs")
    for table in OTHERS:
        prior.table_columns(conn, table)
    review = prior.roster_review(conn, catchup)
    prior.require(len(review) == 32 and
                  all(row["saved_ownership_status"] is None for row in review if row["lane"] == "CHAIN_ONLY") and
                  all(row["saved_ownership_status"] == "OWNED" for row in review if row["lane"] == "SAVED_ONLY"),
                  "saved roster changed after evidence review")
    saved = {str(r[0]) for r in conn.execute("SELECT axie_id FROM gameplay_owned_axies WHERE ownership_status='OWNED'")}
    expected = (saved - {c["axie_id"] for c in saved_only}) | {c["axie_id"] for c in chain_only}
    prior.require(expected == live_ids and len(expected) == 162 and
                  conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                  not conn.execute("PRAGMA foreign_key_check").fetchall(),
                  "fresh chain IDs, saved roster or SQLite integrity differs")
    baseline = {t: prior.snapshot_table(conn, t) for t in prior.WATCHED}
    changed_ids = {c["axie_id"] for c in chain_only + saved_only}
    baseline["unchanged_roster"] = unchanged_roster(conn, changed_ids)
    return baseline


def guard_nullable_metadata(conn, missing):
    if not missing:
        return
    columns = {row[1]: row for row in conn.execute("PRAGMA table_info(gameplay_owned_axies)")}
    prior.require(all(columns[k][3] == 0 for k in ("axie_class", "level", "breed_count")),
                  "metadata columns require values; no roster update")


def execute_plan(conn, additions, stale):
    before = conn.total_changes
    conn.executemany(ADD, additions)
    added = conn.total_changes - before
    before = conn.total_changes
    conn.executemany(STALE, stale)
    changed = conn.total_changes - before
    prior.require(added == 29 and changed == 3, "roster insert/update counts differ")
    for row in additions:
        actual = conn.execute("SELECT wallet_address,ownership_status,axie_class,level,breed_count,"
                              "last_seen_datetime,data_source FROM gameplay_owned_axies WHERE axie_id=?", (row[0],)).fetchone()
        prior.require(actual == (row[1], "OWNED", *row[2:]), f"{row[0]}: inserted registry row differs")
    for (axie_id,) in stale:
        prior.require(conn.execute("SELECT ownership_status FROM gameplay_owned_axies WHERE axie_id=?",
                                   (axie_id,)).fetchone() == ("UNKNOWN",),
                      f"{axie_id}: saved-only status differs")


def post_check(conn, baseline, changed_ids, expected_live):
    prior.require(all(prior.snapshot_table(conn, t) == baseline[t] for t in OTHERS),
                  "protected tables changed")
    prior.require(unchanged_roster(conn, changed_ids) == baseline["unchanged_roster"] and
                  baseline["unchanged_roster"][0] == baseline[ROSTER]["rows"] - 3 and
                  conn.execute("SELECT count(*) FROM gameplay_owned_axies").fetchone()[0] ==
                      baseline[ROSTER]["rows"] + 29 and
                  {str(r[0]) for r in conn.execute("SELECT axie_id FROM gameplay_owned_axies WHERE ownership_status='OWNED'")} == expected_live and
                  conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                  not conn.execute("PRAGMA foreign_key_check").fetchall(),
                  "post-plan roster or integrity differs")


def clone_check(source, additions, stale, baseline, live_ids):
    changed_ids = {r[0] for r in additions + stale}
    with tempfile.TemporaryDirectory(prefix="axieos_v015_roster_clone_") as temp:
        with closing(sqlite3.connect(Path(temp) / "clone.db")) as clone:
            source.backup(clone)
            prior.require({t: prior.snapshot_table(clone, t) for t in prior.WATCHED} ==
                          {t: baseline[t] for t in prior.WATCHED} and
                          unchanged_roster(clone, changed_ids) == baseline["unchanged_roster"],
                          "clone baseline differs")
            clone.execute("PRAGMA foreign_keys=ON")
            execute_plan(clone, additions, stale)
            post_check(clone, baseline, changed_ids, live_ids)
            clone.commit()
    return changed_ids


def backup(db, directory, baseline):
    directory = directory.expanduser().resolve()
    prior.require(not directory.is_relative_to(ROOT.resolve()) and directory != db.parent and
                  not db.is_relative_to(directory), "backup must be outside repository and database folder")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / ("axieos_before_v015_roster_" +
                          datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") +
                          "_" + uuid4().hex[:6] + ".db")
    with closing(prior.open_ro(db)) as source, closing(sqlite3.connect(target)) as dest:
        source.backup(dest)
        prior.require({t: prior.snapshot_table(dest, t) for t in prior.WATCHED} ==
                      {t: baseline[t] for t in prior.WATCHED} and
                      dest.execute("PRAGMA integrity_check").fetchone()[0] == "ok" and
                      not dest.execute("PRAGMA foreign_key_check").fetchall(),
                      "backup differs from clone baseline; no production update")
    return target


def apply(db, additions, stale, baseline, changed_ids, live_ids):
    with closing(sqlite3.connect(db, timeout=15)) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("BEGIN IMMEDIATE")
        try:
            prior.require({t: prior.snapshot_table(conn, t) for t in prior.WATCHED} ==
                          {t: baseline[t] for t in prior.WATCHED},
                          "production changed after backup")
            execute_plan(conn, additions, stale)
            post_check(conn, baseline, changed_ids, live_ids)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    with closing(prior.open_ro(db)) as verify:
        post_check(verify, baseline, changed_ids, live_ids)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=prior.DEFAULT_DB)
    parser.add_argument("--catchup", type=Path, default=CATCHUP)
    parser.add_argument("--reconciliation", type=Path, default=RECON)
    parser.add_argument("--evidence", type=Path, default=EVIDENCE)
    parser.add_argument("--backup-dir", type=Path, default=Path.home() / "AxieOSBackups")
    parser.add_argument("--output-dir", type=Path, default=REPORTS)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-unknown-metadata", action="store_true",
                        help="Permit NULL class/level/breed when both metadata sources lack values")
    args = parser.parse_args()
    catchup, catch_sha = prior.load_source(args.catchup)
    recon, recon_sha = load(args.reconciliation, "SOURCE_RECONCILIATION")
    evidence, evidence_sha = load(args.evidence, "OWNERSHIP_EVIDENCE_BATCH", EVIDENCE_SHA256)
    chain_only, saved_only = verify_evidence(catchup, catch_sha, recon, recon_sha, evidence)
    opener = build_opener(prior.NoRedirect())
    metadata_rows = {}
    graphql_enabled = True
    for case in chain_only:
        aid = case["axie_id"]
        metadata_rows[aid], graphql_enabled = metadata(opener, aid, chain.WALLETS[0], graphql_enabled)
    prior.require(len(metadata_rows) == 29, "metadata coverage incomplete")
    missing = sorted(aid for aid, item in metadata_rows.items() if not item["complete"])
    prior.require(not missing or args.allow_unknown_metadata,
                  f"metadata incomplete for {len(missing)} Axies (e.g. {missing[:3]}); "
                  "rerun with --allow-unknown-metadata to preserve NULLs")
    client = chain.Net(15)
    live = chain.ownership(client)
    prior.require(live["status"] == "COMPLETE_AT_PINNED_BLOCK" and
                  live["balances"] == catchup["owned_inventory"]["wallet_balances"] and
                  len(live["axie_ids"]) == 162,
                  f"fresh ownership incomplete or changed: {live['error']}")
    live_ids = set(live["axie_ids"])
    additions, stale = rows_for_plan(chain_only, saved_only, metadata_rows, live["block_timestamp_utc"])
    db = args.db.expanduser().resolve()
    with closing(prior.open_ro(db)) as source:
        source.execute("BEGIN")
        baseline = guard_db(source, catchup, chain_only, saved_only, live_ids)
        guard_nullable_metadata(source, missing)
        changed_ids = clone_check(source, additions, stale, baseline, live_ids)
    backup_path = None
    status = "READ_ONLY_CLONE_READY"
    if args.apply:
        backup_path = backup(db, args.backup_dir, baseline)
        apply(db, additions, stale, baseline, changed_ids, live_ids)
        status = "APPLIED_AND_RECONCILED"
    report = {"version": "0.15", "task": "GUARDED_ROSTER_REFRESH", "status": status,
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "sources": {"catchup_sha256": catch_sha, "reconciliation_sha256": recon_sha,
                          "evidence_sha256": evidence_sha},
              "fresh_block": live["block"], "fresh_block_timestamp_utc": live["block_timestamp_utc"],
              "fresh_chain_owned": len(live_ids), "metadata_validated": 29 - len(missing),
              "metadata_unknown_ids": missing,
              "metadata_evidence": list(metadata_rows.values()),
              "roster_before": baseline[ROSTER]["rows"],
              "roster_after": baseline[ROSTER]["rows"] + (29 if args.apply else 0),
              "owned_after_if_applied": 162, "chain_only_inserted": 29 if args.apply else 0,
              "saved_only_to_unknown": 3 if args.apply else 0,
              "backup": str(backup_path) if backup_path else None,
              "rpc_calls": client.calls, "metadata_attempted": len(metadata_rows),
              "database_writes": 32 if args.apply else 0, "finance_writes": 0,
              "verified_financial_totals": "UNKNOWN", "unified_finance": "HOLD",
              "checkpoint96": "OPEN"}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = "AxieOS_V015_Guarded_Roster_Refresh_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as out:
        json.dump(report, out, indent=2)
        out.write("\n")
    mp.write_text("\n".join(["# AxieOS V0.15 guarded roster refresh", "",
        f"Status: **{status}**. Fresh chain Axies: **162**; metadata validated: **{29-len(missing)}/29**.",
        f"Metadata unknown for: {', '.join(missing) if missing else 'none'}.",
        f"Chain-only rows inserted: **{report['chain_only_inserted']}**. "
        f"Saved-only rows set to UNKNOWN: **{report['saved_only_to_unknown']}**.",
        f"Fresh block: `{live['block']}` at {live['block_timestamp_utc']}.",
        f"Backup: `{backup_path or 'none (read-only preflight)'}`.", "",
        "UNKNOWN denotes an outdated OWNED flag. No SOLD, RELEASED, cost, income, "
        "or profit classification was inferred. New class/level/breed values come from "
        "validated Axie metadata; absent metadata stays NULL. Parts, acquisition basis, "
        "and lifecycle causes remain separate.",
        "Verified financial totals: **UNKNOWN**. Unified Finance: **HOLD**. Checkpoint 96: **OPEN**.", ""]),
        encoding="utf-8")
    print("AXIEOS V0.15 - GUARDED ROSTER REFRESH")
    print(f"Status: {status} | Fresh chain: 162 | Metadata: {29-len(missing)}/29 | "
          f"Roster changes: {report['database_writes']}")
    print(f"Backup: {backup_path or 'none'}")
    print(f"Reports: {jp} {mp}")
    print("Financial totals: UNKNOWN | Unified Finance: HOLD | Checkpoint 96: OPEN")


if __name__ == "__main__":
    main()
