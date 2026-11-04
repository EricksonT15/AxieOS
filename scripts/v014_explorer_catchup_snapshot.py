r"""Task136AT: bounded, read-only Ronin explorer catch-up snapshot.

From the AxieOS repository root, while connected to the working network:
    py -B .\scripts\v014_explorer_catchup_snapshot.py

Requires the successful Task136AS probe and its SHA-matched Task136W source.
Requests at most three pages per wallet/route by default, stopping once the
October 22 raw-cache boundary is reached. Saves the exact response bodies in
new report files. Never opens SQLite, syncs, classifies, or accepts totals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener
from uuid import uuid4

from v014_explorer_readonly_probe import BASE, HOST, KINDS, NoRedirect, load, utc


MAX_BYTES = 2_000_000


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError("STOP: " + reason)


def latest(directory: Path, task: str) -> Path:
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        doc, _ = load(path)
        if doc.get("task") == task:
            matches.append((doc.get("created_at_utc", ""), path))
    require(matches, f"missing Task{task} JSON in {directory}")
    return max(matches)[1]


def by_sha(directory: Path, sha: str) -> Path:
    matches = [path for path in directory.glob("*.json")
               if hashlib.sha256(path.read_bytes()).hexdigest() == sha]
    require(len(matches) == 1, f"expected one SHA-matched Task136W JSON in {directory}")
    return matches[0]


def params_query(params: dict | None) -> str:
    if params is None:
        return ""
    require(isinstance(params, dict) and len(params) <= 20, "invalid pagination cursor")
    pairs = []
    for key, value in sorted(params.items()):
        require(isinstance(key, str) and re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]*", key)
                and len(key) <= 48 and
                (value is None or isinstance(value, (str, int, float, bool))) and
                len(str(value)) <= 256,
                "unexpected explorer pagination parameter")
        pairs.append((key, "" if value is None else str(value)))
    return urlencode(pairs)


def request_page(opener, address: str, kind: str, cursor: dict | None,
                 timeout: int) -> tuple[dict | None, dict]:
    require(kind in KINDS and re.fullmatch(r"0x[0-9a-f]{40}", address) is not None,
            "invalid address route")
    query = params_query(cursor)
    url = BASE + address + "/" + kind + ("?" + query if query else "")
    parsed = urlsplit(url)
    require(parsed.scheme == "https" and parsed.hostname == HOST and
            parsed.username is None and parsed.password is None and
            not parsed.fragment, "unexpected request host")
    meta = {"route": kind, "cursor": cursor, "http_status": None,
            "status": None, "failure_type": None}
    try:
        req = Request(url, headers={"Accept": "application/json",
                                    "User-Agent": "AxieOS-Readonly-Catchup/0.14"})
        with opener.open(req, timeout=timeout) as response:
            meta["http_status"] = response.status
            if response.status != 200 or "json" not in response.headers.get("Content-Type", "").lower():
                raise ValueError("unexpected response status or content type")
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("page exceeds bounded response size")
        body = raw.decode("utf-8")
        doc = json.loads(body)
        if (not isinstance(doc, dict) or not isinstance(doc.get("items"), list) or
                len(doc["items"]) > 100 or
                (doc.get("next_page_params") is not None and
                 not isinstance(doc["next_page_params"], dict))):
            raise ValueError("unexpected explorer pagination shape")
        params_query(doc.get("next_page_params"))
        meta.update(status="PASS_PAGE", response_sha256=hashlib.sha256(raw).hexdigest(),
                    raw_body_utf8=body)
        return doc, meta
    except HTTPError as exc:
        meta.update(status="BLOCKED", http_status=exc.code,
                    failure_type="HTTP_ERROR_OR_REDIRECT_REFUSED")
    except (URLError, TimeoutError, OSError) as exc:
        meta.update(status="BLOCKED", failure_type=type(exc).__name__)
    except (ValueError, UnicodeError) as exc:
        meta.update(status="INVALID_RESPONSE", failure_type=type(exc).__name__)
    return None, meta


def collect_route(opener, address: str, role: str, kind: str,
                  cutoff: datetime, max_pages: int, timeout: int) -> dict:
    pages, cursor, seen = [], None, set()
    previous_oldest = None
    stop = None
    for page_no in range(1, max_pages + 1):
        key = params_query(cursor)
        require(key not in seen, "explorer repeated pagination cursor")
        seen.add(key)
        doc, page = request_page(opener, address, kind, cursor, timeout)
        page["page_number"] = page_no
        if doc is None:
            pages.append(page)
            stop = "ROUTE_" + page["status"]
            break
        stamps = [utc(item.get("timestamp")) if isinstance(item, dict) else None
                  for item in doc["items"]]
        page["page_items"] = len(stamps)
        page["items_newer_than_snapshot"] = sum(at is not None and at > cutoff for at in stamps)
        page["newest_utc"] = max(stamps).isoformat() if stamps and all(stamps) else None
        page["oldest_utc"] = min(stamps).isoformat() if stamps and all(stamps) else None
        pages.append(page)
        if any(at is None for at in stamps) or any(a < b for a, b in zip(stamps, stamps[1:])) or (
                stamps and previous_oldest is not None and stamps[0] > previous_oldest):
            stop = "UNORDERED_OR_UNPARSEABLE_PAGE"
            break
        if stamps:
            previous_oldest = stamps[-1]
        if any(at <= cutoff for at in stamps):
            stop = "REACHED_SNAPSHOT_TIME_BOUNDARY"
            break
        next_cursor = doc.get("next_page_params")
        if next_cursor is None:
            stop = "SOURCE_PAGINATION_END"
            break
        if not stamps:
            stop = "EMPTY_PAGE_WITH_CURSOR"
            break
        if page_no == max_pages:
            stop = "PAGE_CAP_BEFORE_SNAPSHOT_BOUNDARY"
            page["resume_cursor"] = next_cursor
            break
        cursor = next_cursor
        time.sleep(0.25)
    require(stop is not None, "bounded page loop did not stop")
    successful = [p for p in pages if p["status"] == "PASS_PAGE"]
    return {"wallet_role": role, "wallet_address": address, "route": kind,
            "stop_reason": stop, "pages_attempted": len(pages),
            "pages_read": len(successful),
            "items_newer_than_snapshot_on_read_pages": sum(
                p["items_newer_than_snapshot"] for p in successful),
            "time_boundary_or_source_end_reached": stop in
                ("REACHED_SNAPSHOT_TIME_BOUNDARY", "SOURCE_PAGINATION_END"),
            "pages": pages}


def build(w: dict, wp: Path, w_sha: str, probe: dict, probe_sha: str,
          opener, max_pages: int, timeout: int) -> dict:
    require(w.get("task") == "136W" and w.get("report_schema_version") == "1.1" and
            w.get("checkpoint96") == "OPEN" and w.get("accepted_financial_totals") is None and
            probe.get("task") == "136AS" and probe.get("checkpoint96") == "OPEN" and
            probe.get("source_136w_sha256") == w_sha and
            probe.get("source_136w_filename") == wp.name and
            probe["coverage"]["all_routes_one_page_success"] is True and
            probe.get("accepted_financial_totals") is None,
            "Task136AS successful probe or Task136W source differs")
    wallets = w["registered_owned_wallets"]
    expected = {(str(row["address"]).lower(), str(row["wallet_role"]), kind)
                for row in wallets for kind in KINDS}
    observed = {(str(row["wallet_address"]).lower(), str(row["wallet_role"]), row["route"])
                for row in probe["routes"]}
    require(len(expected) == len(probe["routes"]) == len(observed) and
            expected == observed and
            all(row["status"] == "PASS_ONE_PAGE" for row in probe["routes"]) and
            1 <= max_pages <= 10 and 1 <= timeout <= 20,
            "probe route or bounded collection parameters differ")
    cutoff = utc(w["cutoff"]["raw_latest_utc"])
    require(cutoff is not None, "snapshot raw latest UTC missing")
    routes = [collect_route(opener, address, role, kind, cutoff, max_pages, timeout)
              for address, role, kind in sorted(expected) ]
    complete = all(row["time_boundary_or_source_end_reached"] for row in routes)
    return {"project": "AxieOS", "version": "0.14", "task": "136AT",
            "sources": {"136W": {"filename": wp.name, "sha256": w_sha},
                        "136AS": {"sha256": probe_sha}},
            "snapshot_raw_latest_utc": cutoff.isoformat(),
            "coverage": {"wallets": len(wallets), "routes": len(routes),
                         "pages_attempted": sum(r["pages_attempted"] for r in routes),
                         "pages_read": sum(r["pages_read"] for r in routes),
                         "items_newer_than_snapshot_on_read_pages": sum(
                             r["items_newer_than_snapshot_on_read_pages"] for r in routes),
                         "route_stop_reasons": dict(sorted(Counter(
                             r["stop_reason"] for r in routes).items())),
                         "all_routes_reached_time_boundary_or_end": complete,
                         "max_pages_per_route": max_pages},
            "routes": routes, "accepted_financial_totals": None,
            "database_opened": False, "database_writes": 0,
            "network_calls": sum(r["pages_attempted"] for r in routes),
            "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136AT Explorer catch-up snapshot", "",
             f"Snapshot latest raw UTC: **{report['snapshot_raw_latest_utc']}**. "
             f"Pages read/attempted: **{c['pages_read']}/{c['pages_attempted']}**. "
             f"All routes reached time boundary or source end: "
             f"**{'YES' if c['all_routes_reached_time_boundary_or_end'] else 'NO'}**.", "",
             "| Wallet role | Route | Pages | Newer page items | Stop |",
             "|---|---|---:|---:|---|"]
    for r in report["routes"]:
        lines.append(f"| {r['wallet_role']} | {r['route']} | {r['pages_read']} | "
                     f"{r['items_newer_than_snapshot_on_read_pages']} | {r['stop_reason']} |")
    lines += ["", "The JSON preserves exact response bodies and page digests for review. "
              "Page-item counts can overlap across wallets/routes, and are not unique "
              "transactions or verified financial events. A page cap, failed request, "
              "or ordering issue leaves that route incomplete.", "",
              "Verified income, expenses, profit, and PHP recovery: **UNKNOWN**.", "",
              f"Database opened: NO | Writes: 0 | Network calls attempted: {c['pages_attempted']}", "",
              "VALIDATION: bounded raw evidence collection only; Checkpoint 96 OPEN.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--w", type=Path)
    parser.add_argument("--w-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--probe", type=Path)
    parser.add_argument("--probe-dir", type=Path, default=Path("reports/axieos_v014/task136as"))
    parser.add_argument("--max-pages", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136at"))
    args = parser.parse_args()
    require(1 <= args.max_pages <= 10 and 1 <= args.timeout <= 20,
            "max-pages must be 1..10 and timeout 1..20")
    pp = args.probe or latest(args.probe_dir, "136AS")
    probe, probe_sha = load(pp)
    wp = args.w or by_sha(args.w_dir, probe["source_136w_sha256"])
    w, w_sha = load(wp)
    report = build(w, wp, w_sha, probe, probe_sha, build_opener(NoRedirect()),
                   args.max_pages, args.timeout)
    report["sources"]["136AS"]["filename"] = pp.name
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AT_Explorer_Catchup_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136AT - EXPLORER CATCH-UP SNAPSHOT")
    print(f"Routes complete: {sum(r['time_boundary_or_source_end_reached'] for r in report['routes'])}/"
          f"{c['routes']} | Pages read/attempted: {c['pages_read']}/{c['pages_attempted']}")
    print(f"Newer page items (overlap possible): {c['items_newer_than_snapshot_on_read_pages']} | "
          f"Stop reasons: {c['route_stop_reasons']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print(f"Database opened: NO | Writes: 0 | Network calls attempted: {c['pages_attempted']}")
    print("VALIDATION: bounded raw evidence collection only; Checkpoint 96 OPEN")


if __name__ == "__main__":
    main()
