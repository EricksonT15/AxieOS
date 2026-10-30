import csv
import json
import tempfile
from pathlib import Path
from decimal import Decimal as D
from collections import Counter, defaultdict

ROOT = Path(tempfile.gettempdir())

SOURCE = ROOT / "axieos_v013_task135f_portfolio_v1.csv"
OUTPUT = ROOT / "axieos_v013_checkpoint67_listing_scenarios.csv"
ASSUMPTIONS = ROOT / "axieos_v013_checkpoint67_assumptions.json"

# Historical observed marketplace fee.
# NOT verified as the current executable fee.
FEE_RATE = D("0.0425")

SCENARIOS = {
    "ASKING_100_PERCENT": D("1.00"),
    "ASKING_90_PERCENT": D("0.90"),
    "ASKING_80_PERCENT": D("0.80"),
}

def read_csv(path):
    if not path.is_file():
        raise SystemExit(f"Missing input: {path}")

    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    portfolio = read_csv(SOURCE)
    ids = {r["axie_id"] for r in portfolio}
    lanes = Counter(r["analysis_lane"] for r in portfolio)

    expected_lanes = {
        "RETAIN": 91,
        "ORIGINS": 23,
        "FORREL": 30,
        "SELL": 15,
        "REVIEW": 1,
    }

    if (
        len(portfolio) != 160
        or len(ids) != 160
        or dict(lanes) != expected_lanes
    ):
        raise SystemExit("STOP: Portfolio baseline mismatch.")

    listing_rows = []
    listed_by_lane = Counter()
    totals = defaultdict(lambda: D("0"))
    asking_total = D("0")

    for axie in portfolio:
        axie_id = axie["axie_id"]
        lane = axie["analysis_lane"]

        if (
            axie["release_approved"] != "NO"
            or axie["sell_approved"] != "NO"
            or axie["automatic_execution"] != "DISABLED"
        ):
            raise SystemExit(
                f"STOP: Transaction safeguard conflict #{axie_id}"
            )

        price_text = axie["asking_price_weth"].strip()

        if not price_text:
            if lane == "SELL":
                raise SystemExit(
                    f"STOP: SELL lane missing asking price #{axie_id}"
                )
            continue

        if lane not in ("SELL", "ORIGINS"):
            raise SystemExit(
                f"STOP: Protected/research Axie has listing #{axie_id}"
            )

        asking = D(price_text)

        if not asking.is_finite() or asking <= 0:
            raise SystemExit(
                f"STOP: Invalid asking price #{axie_id}"
            )

        listed_by_lane[lane] += 1
        asking_total += asking

        for scenario, multiplier in SCENARIOS.items():
            gross = asking * multiplier
            fee = gross * FEE_RATE
            net = gross - fee

            totals[(lane, scenario)] += net

            listing_rows.append({
                "axie_id": axie_id,
                "analysis_lane": lane,
                "scenario": scenario,
                "asking_price_weth": str(asking),
                "scenario_gross_weth": str(gross),
                "assumed_fee_rate": str(FEE_RATE),
                "estimated_fee_weth": str(fee),
                "estimated_sale_net_weth": str(net),
                "release_net_break_even_weth": str(net),
                "release_net_value_verified": "NO",
                "current_fee_verified": "NO",
                "executable_bid_verified": "NO",
                "sale_execution_verified": "NO",
                "economic_recommendation": (
                    "ORIGINS_REVIEW_FIRST"
                    if lane == "ORIGINS"
                    else "COMPARE_WITH_RELEASE_VALUE"
                ),
                "release_approved": "NO",
                "sell_approved": "NO",
            })

    if not (
        len(listing_rows) == 72
        and listed_by_lane == {"SELL": 15, "ORIGINS": 9}
        and asking_total == D("0.01249")
    ):
        raise SystemExit(
            "STOP: Listing coverage or gross total mismatch."
        )

    full_net = sum(
        totals[(lane, "ASKING_100_PERCENT")]
        for lane in ("SELL", "ORIGINS")
    )

    expected_net = D("0.011959175")

    if full_net != expected_net:
        raise SystemExit(
            "STOP: Net proceeds calculation mismatch."
        )

    with OUTPUT.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=list(listing_rows[0])
        )
        writer.writeheader()
        writer.writerows(listing_rows)

    assumptions = {
        "version": "V0.13",
        "checkpoint": 67,
        "source": str(SOURCE),
        "fee_rate": str(FEE_RATE),
        "fee_basis": "HISTORICAL_OBSERVED_MARKETPLACE_FEE",
        "current_fee_verified": False,
        "scenario_multipliers": {
            k: str(v) for k, v in SCENARIOS.items()
        },
        "executable_quotes_verified": False,
        "marketplace_prices_are_asks": True,
        "approved_sales": 0,
        "approved_releases": 0,
    }

    ASSUMPTIONS.write_text(
        json.dumps(assumptions, indent=2),
        encoding="utf-8"
    )

    print("AXIEOS V0.13 - TASK 135F")
    print("CHECKPOINT 67: MARKET NET VALUE ENGINE")

    print("\nLISTING COVERAGE")
    print("SELL lane listings:", listed_by_lane["SELL"])
    print("ORIGINS lane listings:", listed_by_lane["ORIGINS"])
    print("Total priced Axies:", sum(listed_by_lane.values()))
    print("Gross asking value:", asking_total, "WETH")
    print("Assumed marketplace fee:", FEE_RATE * 100, "%")

    print("\nPROJECTED NET PROCEEDS")
    for scenario in SCENARIOS:
        sell_net = totals[("SELL", scenario)]
        origins_net = totals[("ORIGINS", scenario)]

        print(scenario)
        print("  SELL lane:", sell_net, "WETH")
        print("  ORIGINS lane:", origins_net, "WETH")
        print("  Combined:", sell_net + origins_net, "WETH")

    print("\nSAFETY")
    print("Current fee verified: NO")
    print("Executable bids verified: NO")
    print("Release values verified: NO")
    print("Sales approved: 0")
    print("Releases approved: 0")
    print("Production database writes: 0")

    print("\nScenario report:", OUTPUT)
    print("Assumptions:", ASSUMPTIONS)
    print("VALIDATION: PASS")


if __name__ == "__main__":
    main()
