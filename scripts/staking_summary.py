"""Read-only V0.12 staking and reward summary for AxieOS.

Consumes normalized economic events from staking_event_resolver.py.
All token arithmetic uses Decimal; no production database writes.
"""

from collections import Counter
from decimal import Decimal

from staking_event_resolver import (
    connect_read_only,
    load_accounting_candidates,
    load_blockchain_evidence,
    load_staking_addresses,
    load_user_owned_addresses,
    normalize_event,
)


ZERO = Decimal("0")


def to_decimal(value):
    if value is None:
        return ZERO
    return Decimal(str(value))


def format_decimal(value):
    return format(value, "f")


def load_normalized_events(conn):
    accounting_rows = load_accounting_candidates(conn)
    user_addresses = load_user_owned_addresses(conn)
    staking_addresses = load_staking_addresses(conn)
    blockchain_evidence = load_blockchain_evidence(conn)

    events = []
    for row in accounting_rows:
        events.append(
            normalize_event(
                row,
                blockchain_evidence.get(row["txhash"]),
                user_addresses,
                staking_addresses,
            )
        )
    return events


def sum_amounts(events):
    total = ZERO
    for event in events:
        total += to_decimal(event["quantity"])
    return total


def filter_events(events, token=None, event_type=None, economic_source=None):
    result = []
    for event in events:
        if token is not None and event["token"] != token:
            continue
        if event_type is not None and event["event_type"] != event_type:
            continue
        if economic_source is not None and event["economic_source"] != economic_source:
            continue
        result.append(event)
    return result


def build_summary(events):
    if not events:
        return None

    ordered = sorted(events, key=lambda event: (event["datetime"], event["txhash"]))
    event_counts = Counter(event["event_type"] for event in events)
    confidence_counts = Counter(event["confidence"] for event in events)
    basis_counts = Counter(event["resolution_basis"] for event in events)

    bounty_claims = filter_events(
        events, token="bAXS", event_type="CLAIM", economic_source="BOUNTY"
    )
    terrarium_claims = filter_events(
        events, token="bAXS", event_type="CLAIM", economic_source="TERRARIUMS"
    )
    axs_claims = filter_events(events, token="AXS", event_type="CLAIM")
    axs_restake_rewards = filter_events(
        events, token="AXS", event_type="RESTAKE_REWARD"
    )
    baxs_stakes = filter_events(events, token="bAXS", event_type="STAKE")
    baxs_unstakes = filter_events(events, token="bAXS", event_type="UNSTAKE")
    axs_stakes = filter_events(events, token="AXS", event_type="STAKE")
    axs_unstakes = filter_events(events, token="AXS", event_type="UNSTAKE")

    bounty_total = sum_amounts(bounty_claims)
    terrarium_total = sum_amounts(terrarium_claims)
    axs_claim_total = sum_amounts(axs_claims)
    axs_restake_reward_total = sum_amounts(axs_restake_rewards)
    baxs_stake_total = sum_amounts(baxs_stakes)
    baxs_unstake_total = sum_amounts(baxs_unstakes)
    axs_stake_total = sum_amounts(axs_stakes)
    axs_unstake_total = sum_amounts(axs_unstakes)

    return {
        "first_datetime": ordered[0]["datetime"],
        "last_datetime": ordered[-1]["datetime"],
        "event_count": len(events),
        "event_counts": event_counts,
        "confidence_counts": confidence_counts,
        "basis_counts": basis_counts,
        "bounty_claim_count": len(bounty_claims),
        "bounty_total": bounty_total,
        "terrarium_claim_count": len(terrarium_claims),
        "terrarium_total": terrarium_total,
        "baxs_reward_total": bounty_total + terrarium_total,
        "axs_claim_count": len(axs_claims),
        "axs_claim_total": axs_claim_total,
        "axs_restake_reward_count": len(axs_restake_rewards),
        "axs_restake_reward_total": axs_restake_reward_total,
        "axs_reward_total": axs_claim_total + axs_restake_reward_total,
        "baxs_stake_count": len(baxs_stakes),
        "baxs_stake_total": baxs_stake_total,
        "baxs_unstake_count": len(baxs_unstakes),
        "baxs_unstake_total": baxs_unstake_total,
        "baxs_net_user_flow": baxs_stake_total - baxs_unstake_total,
        "axs_stake_count": len(axs_stakes),
        "axs_stake_total": axs_stake_total,
        "axs_unstake_count": len(axs_unstakes),
        "axs_unstake_total": axs_unstake_total,
        "axs_net_user_flow": axs_stake_total - axs_unstake_total,
        "axs_position_increase": (
            axs_stake_total + axs_restake_reward_total - axs_unstake_total
        ),
    }


def print_summary(summary):
    print("AXIEOS V0.12 STAKING SUMMARY")
    print()
    print("COVERAGE")
    print("Stored datetime range:", summary["first_datetime"], "to", summary["last_datetime"])
    print("Normalized events:", summary["event_count"])
    print()
    print("EVENT TYPES")
    for event_type in ("CLAIM", "RESTAKE_REWARD", "STAKE", "UNSTAKE", "UNRESOLVED"):
        print(f"{event_type}:", summary["event_counts"].get(event_type, 0))

    print()
    print("EVIDENCE QUALITY")
    for confidence in ("HIGH", "MEDIUM", "UNRESOLVED"):
        print(f"{confidence}:", summary["confidence_counts"].get(confidence, 0))
    print("Explicit method:", summary["basis_counts"].get("EXPLICIT_METHOD", 0))
    print("Flow pattern:", summary["basis_counts"].get("FLOW_PATTERN", 0))

    print()
    print("bAXS REWARDS")
    print("Bounty claims:", summary["bounty_claim_count"])
    print("Bounty bAXS:", format_decimal(summary["bounty_total"]))
    print("Terrarium claims:", summary["terrarium_claim_count"])
    print("Terrarium bAXS:", format_decimal(summary["terrarium_total"]))
    print("Total bAXS rewards:", format_decimal(summary["baxs_reward_total"]))

    print()
    print("AXS STAKING REWARDS")
    print("Claim events:", summary["axs_claim_count"])
    print("Claimed AXS:", format_decimal(summary["axs_claim_total"]))
    print("Immediate restake events:", summary["axs_restake_reward_count"])
    print(
        "Immediate-restake reward AXS:",
        format_decimal(summary["axs_restake_reward_total"]),
    )
    print("Total AXS staking rewards:", format_decimal(summary["axs_reward_total"]))

    print()
    print("bAXS STAKING FLOWS")
    print("Stake events:", summary["baxs_stake_count"])
    print("Staked bAXS:", format_decimal(summary["baxs_stake_total"]))
    print("Unstake events:", summary["baxs_unstake_count"])
    print("Unstaked bAXS:", format_decimal(summary["baxs_unstake_total"]))
    print(
        "Net user-directed bAXS stake flow:",
        format_decimal(summary["baxs_net_user_flow"]),
    )

    print()
    print("AXS STAKING FLOWS")
    print("Standalone stake events:", summary["axs_stake_count"])
    print("Standalone staked AXS:", format_decimal(summary["axs_stake_total"]))
    print("Unstake events:", summary["axs_unstake_count"])
    print("Unstaked AXS:", format_decimal(summary["axs_unstake_total"]))
    print(
        "Net user-directed AXS stake flow:",
        format_decimal(summary["axs_net_user_flow"]),
    )
    print(
        "Position increase incl. immediate reward restakes:",
        format_decimal(summary["axs_position_increase"]),
    )

    print()
    print("NOTES")
    print("- Datetimes are reported as stored; no timezone normalization is applied.")
    print("- HIGH = explicit blockchain method; MEDIUM = inferred token-flow pattern.")
    print("- RESTAKE_REWARD is one operation, not a separate CLAIM plus STAKE.")
    print("- Totals cover available normalized events, not necessarily complete history.")
    print("- Net staking flows are activity changes, not opening/closing balances.")


def main():
    conn = connect_read_only()
    try:
        events = load_normalized_events(conn)
        summary = build_summary(events)
        if summary is None:
            print("No normalized staking events found.")
            return
        print_summary(summary)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
