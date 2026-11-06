#!/usr/bin/env python3
r"""Make a local, filterable HTML screen from the latest no-spend watchlist.

Save as scripts/AxieOS_V100_Watchlist_App.py and run from the repo root:
    py -B .\scripts\AxieOS_V100_Watchlist_App.py

Standard Python only. Reads a saved JSON report and writes one HTML page.
No database, network, wallet, or gameplay action.
"""

from __future__ import annotations

import html
import json
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports/axieos_v100/no_spend_watchlist"
FINANCE_REPORTS = ROOT / "reports/axieos_v100/finance_basis_review"
PREFIX = "AxieOS_V100_NoSpend_Portfolio_Watchlist_"
LANES = {"OBSERVE_ONLY", "PROTECTED_COLLECTIBLE", "SOURCE_EXCEPTION",
         "COLLECTION_EVIDENCE_REVIEW"}


def require(ok, message):
    if not ok:
        raise ValueError("STOP: " + message)


def load_latest(folder):
    matches = sorted(folder.glob(PREFIX + "*.json"))
    require(matches, "No watchlist JSON found. Run AxieOS_V100_NoSpend_Portfolio_Watchlist.py first.")
    path = matches[-1]
    raw = path.read_bytes()
    require(len(raw) <= 5_000_000, "Watchlist exceeds size limit")
    doc = json.loads(raw.decode("utf-8-sig"))
    require(isinstance(doc, dict) and doc.get("task") == "NO_SPEND_PORTFOLIO_WATCHLIST" and
            doc.get("version") == "1.0-pilot" and doc.get("automatic_execution") is False and
            doc.get("database_writes") == doc.get("network_calls") == 0 and
            doc.get("bounty_board") == "PAUSED_NO_OPERATING_FUNDS" and
            doc.get("financial_totals") == "UNKNOWN" and doc.get("unified_finance") == "HOLD" and
            doc.get("checkpoint96") == "OPEN", "Report boundary differs")
    rows = doc.get("axies")
    require(isinstance(rows, list) and type(doc.get("owned_axies")) is int and
            len(rows) == doc["owned_axies"] and bool(rows), "Watchlist row count differs")
    ids, counts = set(), {}
    for row in rows:
        require(isinstance(row, dict) and isinstance(row.get("axie_id"), str) and
                row["axie_id"].isdecimal() and row["axie_id"] not in ids and
                row.get("review_lane") in LANES and isinstance(row.get("review_flags"), list) and
                isinstance(row.get("collection_traits"), list) and
                row.get("sale_approved") is False and row.get("release_approved") is False and
                row.get("dojo_reassignment_authorized") is False,
                "Duplicate ID, invalid lane, or unexpected approval")
        ids.add(row["axie_id"])
        counts[row["review_lane"]] = counts.get(row["review_lane"], 0) + 1
    require(counts == doc.get("review_lanes") and
            sum(r["level"] is None for r in rows) == doc.get("unknown_levels") and
            sum("SOURCE_BACKED_COLLECTIBLE" in r["review_flags"] for r in rows) ==
            doc.get("source_backed_collectibles"), "Summary differs from watchlist rows")
    return path, doc


def esc(value):
    return html.escape(str(value), quote=True)


def load_finance_exception(folder):
    matches = sorted(folder.glob("AxieOS_V100_Finance_Source_Exceptions_*.json"))
    if not matches:
        return None, None
    path = matches[-1]
    raw = path.read_bytes()
    require(len(raw) <= 5_000_000, "Finance exception report exceeds size limit")
    report = json.loads(raw.decode("utf-8-sig"))
    exceptions = report.get("exceptions")
    floors = report.get("minimum_starting_units_for_observed_path_only")
    require(report.get("task") == "FINANCE_SOURCE_EXCEPTION_CLOSEOUT" and
            report.get("sale_conflicts") == 24 and
            report.get("by_token_id") == {"1": 6, "2": 18} and
            isinstance(exceptions, list) and len(exceptions) == 24 and
            len({r.get("sale_hash") for r in exceptions}) == 24 and
            all(r.get("exception_status") == "OPEN_SOURCE_GAP" and
                r.get("accepted_cost_basis") is None and r.get("accepted_profit") is None
                for r in exceptions) and
            isinstance(floors, dict) and set(floors) == {"1", "2"} and
            all(type(floors[t]) is int and floors[t] >= 0 for t in ("1", "2")) and
            report.get("actual_opening_inventory") is None and
            report.get("accepted_cost_basis") is None and report.get("accepted_profit") is None and
            report.get("unified_finance") == "HOLD" and report.get("checkpoint96") == "OPEN" and
            report.get("database_opened") is False and report.get("database_writes") == 0 and
            report.get("network_calls") == 0, "Finance exception boundary differs")
    return path, report


def render(path, doc, finance=None, finance_name=None):
    options = ['<option value="">All review lanes</option>']
    for lane, count in sorted(doc["review_lanes"].items()):
        options.append(f'<option value="{esc(lane)}">{esc(lane.replace("_", " ").title())} ({count})</option>')
    trs = []
    for row in doc["axies"]:
        values = ["#" + row["axie_id"], row["axie_class"] or "UNKNOWN",
                  "UNKNOWN" if row["level"] is None else row["level"],
                  "UNKNOWN" if row["breed_count"] is None else row["breed_count"],
                  row["review_lane"].replace("_", " ").title(),
                  ", ".join(row["collection_traits"]), ", ".join(row["review_flags"]),
                  row["next_review"]]
        trs.append(f'<tr data-lane="{esc(row["review_lane"])}" data-id="{esc(row["axie_id"])}">' +
                   "".join(f"<td>{esc(v)}</td>" for v in values) + "</tr>")
    headings = ("Axie ID", "Class", "Level", "Breed", "Lane", "Collections", "Flags", "Next review")
    finance_panel = ""
    if finance is not None:
        floors = finance["minimum_starting_units_for_observed_path_only"]
        finance_panel = (
            '<div class="cards"><div class="card">Consumable sale exceptions<strong>24 open</strong></div>'
            f'<div class="card">Regular starting floor<strong>{floors["1"]}</strong></div>'
            f'<div class="card">Premium starting floor<strong>{floors["2"]}</strong></div></div>'
            '<p class="muted">Saved finance source exception report: ' + esc(finance_name) +
            '. Starting floors apply only to the observed transfer path; actual opening inventory '
            'and profit remain unknown.</p>')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'">
<title>AxieOS | No-spend watchlist</title><style>
body{{font:16px system-ui,Arial,sans-serif;background:#101723;color:#eaf0f8;margin:0 auto;padding:28px;max-width:1500px}}
.muted{{color:#aebbd0;overflow-wrap:anywhere}}.cards{{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0}}
.card{{background:#1b2738;border-radius:12px;padding:14px 20px;min-width:170px}}.card strong{{display:block;font-size:26px}}
.notice{{background:#302b1d;border:1px solid #9b7b31;padding:14px;border-radius:10px;margin:18px 0}}
.controls{{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0}}input,select{{font:inherit;padding:10px;border-radius:8px;background:#1b2738;color:#fff;border:1px solid #516079}}
.scroll{{overflow:auto;border:1px solid #40516a;border-radius:10px}}table{{border-collapse:collapse;width:100%;min-width:980px}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #344256;vertical-align:top}}th{{background:#233248}}tr:hover{{background:#1d2d41}}
</style></head><body><h1>AxieOS · No-spend portfolio</h1>
<p class="muted">Saved report: {esc(path.name)} · Philippine as-of date: {esc(doc['as_of_philippines_date'])} · Pinned sync age at report: {esc(doc['sync_age_days'])} day(s)</p>
<div class="cards"><div class="card">Owned Axies<strong>{doc['owned_axies']}</strong></div><div class="card">Protected collectibles<strong>{doc['source_backed_collectibles']}</strong></div><div class="card">Unknown levels<strong>{doc['unknown_levels']}</strong></div><div class="card">Bounty Board<strong>Paused</strong></div></div>
{finance_panel}
<div class="notice">Finance remains on hold. Income, expenses, profit and PHP recovery are UNKNOWN. No sale, release, purchase, reroll, ascension or Dojo reassignment is approved.</div>
<p class="muted">Saved evidence only; this page does not query live ownership or gameplay state. Checkpoint 96 remains open.</p>
<div class="controls"><label>Review lane <select id="lane">{''.join(options)}</select></label><label>Axie ID contains <input id="search" placeholder="e.g. 122" autocomplete="off"></label></div>
<p id="shown"></p><div class="scroll"><table><thead><tr>{''.join(f'<th>{esc(h)}</th>' for h in headings)}</tr></thead><tbody>{''.join(trs)}</tbody></table></div>
<script>const lane=document.getElementById('lane'), search=document.getElementById('search');
const rows=[...document.querySelectorAll('tbody tr')];
function filter(){{let n=0;for(const row of rows){{const show=(!lane.value||row.dataset.lane===lane.value)&&row.dataset.id.includes(search.value.trim().replace(/^#/,''));row.hidden=!show;if(show)n++;}}document.getElementById('shown').textContent=`Showing ${{n}} of ${{rows.length}} saved owned Axies`;}}
lane.addEventListener('change',filter);search.addEventListener('input',filter);filter();</script></body></html>'''


def main():
    path, doc = load_latest(REPORTS)
    finance_path, finance = load_finance_exception(FINANCE_REPORTS)
    output = REPORTS / "AxieOS_V100_NoSpend_Portfolio_Watchlist_Latest.html"
    output.write_text(render(path, doc, finance, finance_path.name if finance_path else None), encoding="utf-8")
    print("AXIEOS V1.0 - LOCAL NO-SPEND WATCHLIST")
    print("Owned:", doc["owned_axies"], "| Unknown levels:", doc["unknown_levels"])
    print("Consumable sale exceptions:", "24 OPEN_SOURCE_GAP" if finance else "no saved exception report")
    print("HTML:", output)
    print("Database: not opened | Network: 0 | Report file written: 1")
    if not webbrowser.open(output.resolve().as_uri()):
        print("Open the HTML path above in your browser.")


if __name__ == "__main__":
    main()
