r"""Task136AS: bounded, read-only Ronin explorer availability probe.

From the AxieOS repository root:
    py -B .\scripts\v014_explorer_readonly_probe.py

Reads the saved Task136W wallet registry and requests one page each of the
official explorer's transactions and token-transfers endpoints per wallet.
No SQLite, wallet signing, RPC, imports, pagination, or finance totals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4


HOST = "explorer.roninchain.com"
BASE = "https://" + HOST + "/api/v2/addresses/"
KINDS = ("transactions", "token-transfers")
MAX_BYTES = 2_000_000


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError("STOP: " + message)


def load(path: Path) -> tuple[dict, str]:
    require(path.is_file(), f"missing Task136W JSON: {path}")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def latest(directory: Path) -> Path:
    matches = []
    for path in directory.glob("*.json") if directory.is_dir() else []:
        doc, _ = load(path)
        if doc.get("task") == "136W" and doc.get("report_schema_version") == "1.1":
            matches.append((doc.get("created_at_utc", ""), path))
    require(matches, f"missing Task136W schema 1.1 JSON in {directory}")
    return max(matches)[1]


def utc(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        dt = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "redirect refused", headers, fp)


def probe(address: str, role: str, kind: str, cutoff: datetime, opener,
          timeout: int) -> dict:
    require(kind in KINDS and address.startswith("0x") and len(address) == 42 and
            all(ch in "0123456789abcdef" for ch in address[2:].lower()),
            "invalid explorer route or wallet address")
    url = BASE + address + "/" + kind
    parsed = urlsplit(url)
    require(parsed.scheme == "https" and parsed.hostname == HOST and
            parsed.username is None and parsed.password is None and
            parsed.query == "" and parsed.fragment == "", "unexpected request URL")
    out = {"wallet_role": role, "wallet_address": address, "route": kind,
           "status": None, "http_status": None, "page_items": None,
           "items_newer_than_snapshot_on_page": None, "page_newest_utc": None,
           "has_next_page": None, "failure_type": None}
    try:
        request = Request(url, headers={"Accept": "application/json",
                                        "User-Agent": "AxieOS-Readonly-Probe/0.14"})
        with opener.open(request, timeout=timeout) as response:
            out["http_status"] = response.status
            require(response.status == 200 and
                    "json" in response.headers.get("Content-Type", "").lower(),
                    "explorer response status or content type differs")
            raw = response.read(MAX_BYTES + 1)
            require(len(raw) <= MAX_BYTES, "explorer page exceeds bounded response size")
        doc = json.loads(raw.decode("utf-8"))
        require(isinstance(doc, dict) and isinstance(doc.get("items"), list) and
                (doc.get("next_page_params") is None or
                 isinstance(doc["next_page_params"], dict)),
                "explorer JSON pagination shape differs")
        require(len(doc["items"]) <= 100, "unexpectedly large explorer page")
        stamps = [utc(item.get("timestamp")) if isinstance(item, dict) else None
                  for item in doc["items"]]
        require(all(at is not None for at in stamps),
                "explorer item timestamp missing or unparsable")
        out.update(status="PASS_ONE_PAGE", page_items=len(stamps),
                   items_newer_than_snapshot_on_page=sum(at > cutoff for at in stamps),
                   page_newest_utc=max(stamps).isoformat() if stamps else None,
                   has_next_page=bool(doc.get("next_page_params")))
    except HTTPError as exc:
        out.update(status="BLOCKED", http_status=exc.code,
                   failure_type="HTTP_ERROR_OR_REDIRECT_REFUSED")
    except (URLError, TimeoutError, OSError) as exc:
        out.update(status="BLOCKED", failure_type=type(exc).__name__)
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        out.update(status="INVALID_RESPONSE", failure_type=type(exc).__name__)
    return out


def build(w: dict, source_sha: str, opener, timeout: int) -> dict:
    require(w.get("task") == "136W" and w.get("report_schema_version") == "1.1" and
            w.get("checkpoint96") == "OPEN" and
            w.get("accepted_financial_totals") is None,
            "Task136W snapshot or finance boundary differs")
    wallets = w["registered_owned_wallets"]
    addresses = {str(row["address"]).lower() for row in wallets}
    require(len(wallets) == len(addresses) and 0 < len(wallets) <= 4,
            "owned wallet registry changed or exceeds bounded probe")
    cutoff = utc(w["cutoff"]["raw_latest_utc"])
    require(cutoff is not None, "Task136W raw latest UTC invalid")
    results = [probe(str(wallet["address"]).lower(), str(wallet["wallet_role"]),
                     kind, cutoff, opener, timeout)
               for wallet in wallets for kind in KINDS]
    complete = all(r["status"] == "PASS_ONE_PAGE" for r in results)
    successes = [r for r in results if r["status"] == "PASS_ONE_PAGE"]
    return {"project": "AxieOS", "version": "0.14", "task": "136AS",
            "source_136w_sha256": source_sha,
            "snapshot_raw_latest_utc": cutoff.isoformat(),
            "coverage": {"registered_owned_wallets": len(wallets),
                         "http_requests_attempted": len(results),
                         "successful_one_page_routes": len(successes),
                         "blocked_or_invalid_routes": len(results) - len(successes),
                         "page_items_newer_than_snapshot_on_successful_routes":
                             sum(r["items_newer_than_snapshot_on_page"] for r in successes),
                         "all_routes_one_page_success": complete},
            "routes": results, "accepted_financial_totals": None,
            "database_opened": False, "database_writes": 0,
            "network_calls": len(results), "checkpoint96": "OPEN"}


def markdown(report: dict) -> str:
    c = report["coverage"]
    lines = ["# AxieOS V0.14 — Task136AS Explorer read-only probe", "",
             f"Snapshot latest raw UTC: **{report['snapshot_raw_latest_utc']}**. "
             f"One-page routes passed: **{c['successful_one_page_routes']}/"
             f"{c['http_requests_attempted']}**.", "",
             "| Wallet role | Route | Result | HTTP | Items on page | Newer on page | More pages |",
             "|---|---|---|---:|---:|---:|---|"]
    for r in report["routes"]:
        lines.append(f"| {r['wallet_role']} | {r['route']} | {r['status']} | "
                     f"{r['http_status'] or '-'} | {r['page_items'] if r['page_items'] is not None else '-'} | "
                     f"{r['items_newer_than_snapshot_on_page'] if r['items_newer_than_snapshot_on_page'] is not None else '-'} | "
                     f"{'YES' if r['has_next_page'] else 'NO' if r['has_next_page'] is False else '-'} |")
    lines += ["", "Only the first page of each address route was inspected. "
              "A successful page does not prove complete history; a blocked route does not prove "
              "no activity. No downloaded items are imported or treated as financial events.", "",
              "Verified income, expenses, profit, and PHP recovery: **UNKNOWN**.", "",
              f"Database opened: NO | Writes: 0 | Network calls attempted: {c['http_requests_attempted']}", "",
              "VALIDATION: read-only explorer availability probe; Checkpoint 96 OPEN.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--w", type=Path)
    parser.add_argument("--w-dir", type=Path, default=Path("reports/axieos_v014/task136w"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/axieos_v014/task136as"))
    parser.add_argument("--timeout", type=int, default=12)
    args = parser.parse_args()
    require(1 <= args.timeout <= 20, "timeout must be 1..20 seconds")
    wp = args.w or latest(args.w_dir)
    w, sha = load(wp)
    report = build(w, sha, build_opener(NoRedirect()), args.timeout)
    report["source_136w_filename"] = wp.name
    report["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = ("AxieOS_V014_Task136AS_Explorer_Readonly_Probe_" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + uuid4().hex[:6])
    jp, mp = args.output_dir / (stem + ".json"), args.output_dir / (stem + ".md")
    with jp.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    mp.write_text(markdown(report), encoding="utf-8")
    c = report["coverage"]
    print("AXIEOS V0.14 - TASK136AS - EXPLORER READ-ONLY PROBE")
    print(f"One-page routes passed: {c['successful_one_page_routes']}/"
          f"{c['http_requests_attempted']} | Newer items on successful pages: "
          f"{c['page_items_newer_than_snapshot_on_successful_routes']}")
    for row in report["routes"]:
        print(f"{row['wallet_role']} {row['route']}: {row['status']} "
              f"HTTP={row['http_status']} items={row['page_items']} "
              f"newer={row['items_newer_than_snapshot_on_page']} "
              f"failure={row['failure_type']}")
    print("Verified financial totals: UNKNOWN")
    print(f"Reports: {jp} {mp}")
    print(f"Database opened: NO | Writes: 0 | Network calls attempted: "
          f"{c['http_requests_attempted']}")
    print("VALIDATION: read-only explorer probe; Checkpoint 96 OPEN")


if __name__ == "__main__":
    main()
