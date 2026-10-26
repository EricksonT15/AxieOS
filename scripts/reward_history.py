"""Read-only historical staking reward report for AxieOS V0.12.

Consumes the validated staking_event_resolver through staking_summary.
Keeps CLAIM and RESTAKE_REWARD separate; never treats stake/unstake
principal movements as rewards. No APR is estimated without principal.
"""

import argparse
from collections import defaultdict
from datetime import date
from decimal import Decimal

from staking_event_resolver import connect_read_only
from staking_summary import load_normalized_events


REWARD_EVENT_TYPES = frozenset({"CLAIM", "RESTAKE_REWARD"})
ZERO = Decimal("0")


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date {value!r}; use YYYY-MM-DD"
        ) from exc


def event_date(event):
    """Use the stored calendar date without inventing a timezone."""
    return date.fromisoformat(event["datetime"][:10])


def period_label(day, group_by):
    if group_by == "day":
        return day.isoformat()
    if group_by == "month":
        return day.strftime("%Y-%m")
    iso_year, iso_week, _ = day.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def select_reward_events(events, start=None, end=None):
    """Select rewards; exclude all principal stake/unstake movements."""
    selected = []
    for event in events:
        if event["event_type"] not in REWARD_EVENT_TYPES:
            continue
        day = event_date(event)
        if start is not None and day < start:
            continue
        if end is not None and day > end:
            continue
        selected.append(event)
    return sorted(selected, key=lambda event: (
        event["datetime"], event["txhash"], event["accounting_key"]
    ))


def aggregate_rewards(events, group_by):
    """Group by calendar bucket, token, source, and economic event type."""
    buckets = defaultdict(lambda: {
        "count": 0,
        "amount": ZERO,
        "high": 0,
        "medium": 0,
        "other": 0,
    })
    for event in events:
        key = (
            period_label(event_date(event), group_by),
            event["token"],
            event["economic_source"],
            event["event_type"],
        )
        bucket = buckets[key]
        bucket["count"] += 1
        bucket["amount"] += Decimal(str(event["quantity"]))
        if event["confidence"] == "HIGH":
            bucket["high"] += 1
        elif event["confidence"] == "MEDIUM":
            bucket["medium"] += 1
        else:
            bucket["other"] += 1
    return dict(sorted(buckets.items()))


def source_totals(events):
    """Reward totals by token/source without converting AXS into bAXS."""
    amounts = defaultdict(lambda: ZERO)
    counts = defaultdict(int)
    for event in events:
        key = (event["token"], event["economic_source"], event["event_type"])
        amounts[key] += Decimal(str(event["quantity"]))
        counts[key] += 1
    return dict(sorted(amounts.items())), counts


def run_report(events, group_by="day", start=None, end=None, details=False):
    rewards = select_reward_events(events, start=start, end=end)
    print("AXIEOS V0.12 REWARD HISTORY")
    print("Data source: normalized on-chain/accounting evidence")
    print("Stored timestamps: no timezone conversion")
    print("Calendar buckets:", group_by.upper())
    print("Reward event types: CLAIM + RESTAKE_REWARD")
    print("APR: NOT AVAILABLE (historical staked principal not established)")
    print("No missing days are interpreted as zero rewards.")
    if start or end:
        print("Date filter:", start or "unbounded", "to", end or "unbounded")
    print()

    print("COVERAGE")
    print("Available normalized events:", len(events))
    print("Selected reward events:", len(rewards))
    print("HIGH:", sum(e["confidence"] == "HIGH" for e in rewards))
    print("MEDIUM:", sum(e["confidence"] == "MEDIUM" for e in rewards))
    print("Other confidence:", sum(e["confidence"] not in {"HIGH", "MEDIUM"} for e in rewards))
    if rewards:
        print("First selected reward:", rewards[0]["datetime"])
        print("Last selected reward:", rewards[-1]["datetime"])
    print()

    print("HISTORICAL REWARD BUCKETS")
    print("period | token | source | type | events | amount | HIGH | MEDIUM | OTHER")
    buckets = aggregate_rewards(rewards, group_by)
    for (period, token, source, event_type), bucket in buckets.items():
        print(
            f"{period} | {token} | {source} | {event_type} | "
            f"{bucket['count']} | {format(bucket['amount'], 'f')} | "
            f"{bucket['high']} | {bucket['medium']} | {bucket['other']}"
        )
    if not buckets:
        print("No reward events in the selected range.")
    print()

    print("TOTALS BY TOKEN / SOURCE / TYPE")
    totals, counts = source_totals(rewards)
    for (token, source, event_type), amount in totals.items():
        print(f"{token} | {source} | {event_type} | {counts[(token, source, event_type)]} | {format(amount, 'f')}")
    by_token = defaultdict(lambda: ZERO)
    for (token, _source, _event_type), amount in totals.items():
        by_token[token] += amount
    for token, amount in sorted(by_token.items()):
        print(f"TOTAL {token}: {format(amount, 'f')}")
    print()

    if details:
        print("REWARD TRANSACTION EVIDENCE")
        print("stored_datetime | token | source | type | quantity | confidence | basis | txhash")
        for event in rewards:
            print(
                f"{event['datetime']} | {event['token']} | "
                f"{event['economic_source']} | {event['event_type']} | "
                f"{event['quantity']} | {event['confidence']} | "
                f"{event['resolution_basis']} | {event['txhash']}"
            )
        print()

    print("NOTES")
    print("- Totals count RESTAKE_REWARD once, not as separate CLAIM and STAKE.")
    print("- AXS and bAXS are reported separately, with no exchange-rate assumption.")
    print("- Inferred MEDIUM-confidence event types remain distinct from HIGH explicit-method evidence.")
    print("- Results reflect currently imported data, not live balances or lifetime earnings.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group-by", choices=("day", "week", "month"), default="day")
    parser.add_argument("--start", type=parse_date, metavar="YYYY-MM-DD")
    parser.add_argument("--end", type=parse_date, metavar="YYYY-MM-DD")
    parser.add_argument("--details", action="store_true", help="Include every reward transaction and evidence basis")
    args = parser.parse_args()
    if args.start and args.end and args.start > args.end:
        parser.error("--start must not be later than --end")
    conn = connect_read_only()
    try:
        events = load_normalized_events(conn)
    finally:
        conn.close()
    run_report(events, args.group_by, args.start, args.end, args.details)


if __name__ == "__main__":
    main()
