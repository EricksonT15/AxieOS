import argparse
import sqlite3
from decimal import Decimal, InvalidOperation

from database import connect_database
from terrarium_projection import (
    calculate_calendar_span_projection,
)
from terrarium_summary import (
    calculate_evidence_aware_summary,
    load_evidence_aware_snapshots,
)


DEFAULT_LAND_COST_RON = Decimal("871.81")
DEFAULT_BAXS_TO_AXS_RATE = Decimal("0.70")


def decimal_argument(value):
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid decimal value: {value}"
        ) from exc

    return result


def calculate_terrarium_roi(
    projection,
    axs_price_ron,
    land_cost_ron,
    baxs_to_axs_rate,
):
    """
    Calculate full-cost Terrarium payback scenarios.

    Revenue scope:
        Combined income from all owned Terrarium plots.

    Financial chain:
        gross bAXS
        -> realizable AXS
        -> RON value
        -> Forest acquisition-reference recovery

    This models full acquisition-cost payback from zero recovery.
    Previously earned or realized Terrarium income is not deducted.
    """

    if axs_price_ron <= 0:
        raise ValueError(
            "AXS price must be greater than zero."
        )

    if land_cost_ron <= 0:
        raise ValueError(
            "Land cost must be greater than zero."
        )

    if not (
        Decimal("0")
        < baxs_to_axs_rate
        <= Decimal("1")
    ):
        raise ValueError(
            "bAXS -> AXS conversion rate must be "
            "greater than 0 and no greater than 1."
        )

    combined = projection.get(
        "combined"
    )

    if combined is None:
        raise ValueError(
            "Combined Terrarium projection is unavailable."
        )

    effective_ron_per_baxs = (
        baxs_to_axs_rate
        * axs_price_ron
    )

    required_axs = (
        land_cost_ron
        / axs_price_ron
    )

    required_baxs = (
        land_cost_ron
        / effective_ron_per_baxs
    )

    scenarios = []

    for scenario in combined[
        "scenarios"
    ]:
        baxs_per_day = scenario[
            "nominal_daily_rate"
        ]

        if baxs_per_day <= 0:
            raise ValueError(
                "Scenario bAXS pace must be positive."
            )

        realizable_axs_per_day = (
            baxs_per_day
            * baxs_to_axs_rate
        )

        ron_per_day = (
            realizable_axs_per_day
            * axs_price_ron
        )

        break_even_days = (
            land_cost_ron
            / ron_per_day
        )

        scenarios.append(
            {
                "name": scenario["name"],
                "multiplier": scenario[
                    "multiplier"
                ],
                "gross_baxs_per_day": (
                    baxs_per_day
                ),
                "realizable_axs_per_day": (
                    realizable_axs_per_day
                ),
                "ron_per_day": ron_per_day,
                "break_even_days": (
                    break_even_days
                ),
            }
        )

    return {
        "observed_first_date": combined[
            "first_date"
        ],
        "observed_latest_date": combined[
            "latest_date"
        ],
        "calendar_span_days": combined[
            "calendar_span_days"
        ],
        "observed_baxs_delta": combined[
            "delta"
        ],
        "base_baxs_per_day": combined[
            "nominal_daily_rate"
        ],
        "axs_price_ron": axs_price_ron,
        "land_cost_ron": land_cost_ron,
        "baxs_to_axs_rate": (
            baxs_to_axs_rate
        ),
        "effective_ron_per_baxs": (
            effective_ron_per_baxs
        ),
        "required_axs": required_axs,
        "required_baxs": required_baxs,
        "scenarios": scenarios,
    }


def print_roi_report(roi):
    print("=" * 72)
    print(
        "AXIEOS V0.11 — TERRARIUM FINANCIAL ROI"
    )
    print("=" * 72)

    print()
    print("Historical accumulation basis:")

    print(
        f"  Observed period: "
        f"{roi['observed_first_date']} "
        f"to {roi['observed_latest_date']}"
    )

    print(
        f"  Calendar-date span: "
        f"{roi['calendar_span_days']} days"
    )

    print(
        f"  Combined observed increase: "
        f"{roi['observed_baxs_delta']:+.4f} bAXS"
    )

    print(
        f"  Base calendar-span pace: "
        f"{roi['base_baxs_per_day']:.4f} "
        f"bAXS/day"
    )

    print()
    print("Financial assumptions:")

    print(
        f"  Forest acquisition reference: "
        f"{roi['land_cost_ron']:.2f} RON"
    )

    print(
        f"  bAXS -> AXS conversion: "
        f"{roi['baxs_to_axs_rate'] * Decimal('100'):.2f}%"
    )

    print(
        f"  AXS market input: "
        f"{roi['axs_price_ron']:.4f} RON/AXS"
    )

    print(
        f"  Effective value per bAXS: "
        f"{roi['effective_ron_per_baxs']:.4f} RON"
    )

    print()
    print("Full-cost break-even requirement:")

    print(
        f"  Required AXS: "
        f"{roi['required_axs']:.4f} AXS"
    )

    print(
        f"  Required gross bAXS: "
        f"{roi['required_baxs']:.4f} bAXS"
    )

    print()
    print("Payback scenarios:")

    for scenario in roi[
        "scenarios"
    ]:
        multiplier_percent = (
            scenario["multiplier"]
            * Decimal("100")
        )

        print()
        print(
            f"  {scenario['name'].title()} "
            f"({multiplier_percent:.0f}% "
            f"of observed pace)"
        )

        print(
            f"    Gross bAXS pace: "
            f"{scenario['gross_baxs_per_day']:.6f} "
            f"bAXS/day"
        )

        print(
            f"    Realizable AXS pace: "
            f"{scenario['realizable_axs_per_day']:.6f} "
            f"AXS/day"
        )

        print(
            f"    Value pace: "
            f"{scenario['ron_per_day']:.4f} "
            f"RON/day"
        )

        print(
            f"    Full-cost break-even: "
            f"{scenario['break_even_days']:.4f} "
            f"days"
        )

    print()
    print("Interpretation:")

    print(
        "- Combined income from all owned Terrarium plots is "
        "used to recover the Forest acquisition reference."
    )

    print(
        "- The historical accumulation pace is a calendar-span "
        "average, not an exact 24-hour normalized yield."
    )

    print(
        "- The bAXS -> AXS conversion rate and AXS market price "
        "are financial assumptions separate from yield history."
    )

    print(
        "- AXS price is held constant throughout each scenario."
    )

    print(
        "- This is full-cost payback from zero recovery; previously "
        "earned or realized Terrarium income is not deducted."
    )

    print(
        "- Gas, taxes, transaction fees, staking effects, and future "
        "game-economy changes are excluded."
    )

    print(
        "- Conservative/base/upside scenarios are sensitivity "
        "assumptions, not probability forecasts."
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "AxieOS Terrarium financial ROI analysis."
        )
    )

    parser.add_argument(
        "--player",
        default="primary",
        help="Gameplay player_id. Default: primary",
    )

    parser.add_argument(
        "--axs-price-ron",
        required=True,
        type=decimal_argument,
        help=(
            "Current or scenario AXS price expressed "
            "in RON per AXS."
        ),
    )

    parser.add_argument(
        "--land-cost-ron",
        type=decimal_argument,
        default=DEFAULT_LAND_COST_RON,
        help=(
            "Forest acquisition-cost reference in RON. "
            "Default: 871.81"
        ),
    )

    parser.add_argument(
        "--baxs-to-axs-rate",
        type=decimal_argument,
        default=DEFAULT_BAXS_TO_AXS_RATE,
        help=(
            "Realizable AXS per bAXS. "
            "Default: 0.70"
        ),
    )

    args = parser.parse_args()

    conn = connect_database()
    conn.row_factory = sqlite3.Row

    try:
        observations = (
            load_evidence_aware_snapshots(
                conn,
                args.player,
            )
        )
    finally:
        conn.close()

    summary = (
        calculate_evidence_aware_summary(
            observations
        )
    )

    projection = (
        calculate_calendar_span_projection(
            summary,
            (30,),
        )
    )

    roi = calculate_terrarium_roi(
        projection=projection,
        axs_price_ron=args.axs_price_ron,
        land_cost_ron=args.land_cost_ron,
        baxs_to_axs_rate=(
            args.baxs_to_axs_rate
        ),
    )

    print_roi_report(
        roi
    )


if __name__ == "__main__":
    main()
