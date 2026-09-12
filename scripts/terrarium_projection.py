import argparse
import sqlite3
from datetime import date
from decimal import Decimal

from database import connect_database
from terrarium_summary import (
    calculate_evidence_aware_summary,
    load_evidence_aware_snapshots,
)


DEFAULT_HORIZONS = (
    7,
    30,
    365,
)



DEFAULT_SCENARIOS = (
    (
        "conservative",
        Decimal("0.75"),
    ),
    (
        "base",
        Decimal("1.00"),
    ),
    (
        "upside",
        Decimal("1.25"),
    ),
)



def calculate_calendar_span_projection(
    summary,
    horizons,
):
    """
    Calculate nominal calendar-span bAXS accumulation rates.

    Rates use:

        observed cumulative bAXS change
        --------------------------------
        difference between recorded dates

    This is not an exact elapsed-time yield calculation because historical
    Terrarium observations do not contain reliable exact timestamps.

    No buff adjustment is applied.
    No missing observations are reconstructed.
    """

    accumulation = summary.get(
        "accumulation"
    )

    if not accumulation:
        raise ValueError(
            "Evidence-aware accumulation summary is unavailable."
        )

    results = []

    for row in accumulation["plots"]:
        if (
            row["first_value"] is None
            or row["latest_value"] is None
            or row["delta"] is None
            or row["first_date"] is None
            or row["latest_date"] is None
        ):
            continue

        first_date = date.fromisoformat(
            row["first_date"]
        )

        latest_date = date.fromisoformat(
            row["latest_date"]
        )

        calendar_span_days = (
            latest_date - first_date
        ).days

        if calendar_span_days <= 0:
            raise ValueError(
                "Calendar span must be greater than zero."
            )

        nominal_daily_rate = (
            row["delta"]
            / Decimal(calendar_span_days)
        )

        projections = {
            days: (
                nominal_daily_rate
                * Decimal(days)
            )
            for days in horizons
        }

        results.append(
            {
                "plot_type": row["plot_type"],
                "plot_number": row["plot_number"],
                "first_date": row["first_date"],
                "latest_date": row["latest_date"],
                "first_value": row["first_value"],
                "latest_value": row["latest_value"],
                "delta": row["delta"],
                "calendar_span_days": (
                    calendar_span_days
                ),
                "nominal_daily_rate": (
                    nominal_daily_rate
                ),
                "projections": projections,
            }
        )

    if not results:
        raise ValueError(
            "No plot has sufficient cumulative bAXS endpoints."
        )

    endpoint_pairs = {
        (
            row["first_date"],
            row["latest_date"],
            row["calendar_span_days"],
        )
        for row in results
    }

    combined = None

    if len(endpoint_pairs) == 1:
        (
            first_date,
            latest_date,
            calendar_span_days,
        ) = next(
            iter(endpoint_pairs)
        )

        combined_delta = sum(
            (
                row["delta"]
                for row in results
            ),
            Decimal("0"),
        )

        nominal_daily_rate = (
            combined_delta
            / Decimal(calendar_span_days)
        )

        scenario_rows = []

        for (
            scenario_name,
            multiplier,
        ) in DEFAULT_SCENARIOS:
            scenario_rate = (
                nominal_daily_rate
                * multiplier
            )

            scenario_rows.append(
                {
                    "name": scenario_name,
                    "multiplier": multiplier,
                    "nominal_daily_rate": (
                        scenario_rate
                    ),
                    "projections": {
                        days: (
                            scenario_rate
                            * Decimal(days)
                        )
                        for days in horizons
                    },
                }
            )

        combined = {
            "first_date": first_date,
            "latest_date": latest_date,
            "calendar_span_days": (
                calendar_span_days
            ),
            "delta": combined_delta,
            "nominal_daily_rate": (
                nominal_daily_rate
            ),
            "projections": {
                days: (
                    nominal_daily_rate
                    * Decimal(days)
                )
                for days in horizons
            },
            "scenarios": scenario_rows,
        }

    return {
        "observation_count": summary[
            "observation_count"
        ],
        "canonical_count": summary[
            "canonical_count"
        ],
        "evidence_count": summary[
            "evidence_count"
        ],
        "plots": results,
        "combined": combined,
        "horizons": list(horizons),
    }


def print_projection(projection):
    print("=" * 72)
    print(
        "AXIEOS V0.11 — TERRARIUM CALENDAR-SPAN PROJECTION"
    )
    print("=" * 72)

    print()
    print("Evidence basis:")
    print(
        f"  Total observations: "
        f"{projection['observation_count']}"
    )
    print(
        f"  Canonical observations: "
        f"{projection['canonical_count']}"
    )
    print(
        f"  Partial evidence observations: "
        f"{projection['evidence_count']}"
    )

    print()
    print("Observed cumulative accumulation:")

    for row in projection["plots"]:
        print()
        print(
            f"  {row['plot_type']} "
            f"#{row['plot_number']}"
        )

        print(
            f"    Period: "
            f"{row['first_date']} "
            f"to {row['latest_date']}"
        )

        print(
            f"    Calendar-date span: "
            f"{row['calendar_span_days']} days"
        )

        print(
            f"    Cumulative bAXS: "
            f"{row['first_value']:.4f} "
            f"-> {row['latest_value']:.4f}"
        )

        print(
            f"    Observed increase: "
            f"{row['delta']:+.4f}"
        )

        print(
            f"    Nominal calendar-span average: "
            f"{row['nominal_daily_rate']:.4f} "
            f"bAXS/day"
        )

    combined = projection[
        "combined"
    ]

    print()
    print("Combined owned plots:")

    if combined is None:
        print(
            "  Combined rate unavailable because plot endpoint "
            "periods do not match."
        )
    else:
        print(
            f"  Period: "
            f"{combined['first_date']} "
            f"to {combined['latest_date']}"
        )

        print(
            f"  Calendar-date span: "
            f"{combined['calendar_span_days']} days"
        )

        print(
            f"  Observed cumulative increase: "
            f"{combined['delta']:+.4f} bAXS"
        )

        print(
            f"  Nominal calendar-span average: "
            f"{combined['nominal_daily_rate']:.4f} "
            f"bAXS/day"
        )

        print()
        print("Nominal continuation scenarios:")

        for days in projection[
            "horizons"
        ]:
            value = combined[
                "projections"
            ][days]

            print(
                f"  {days} days: "
                f"{value:.4f} bAXS"
            )

        print()
        print("Sensitivity scenarios:")

        for scenario in combined[
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
                f"    Nominal rate: "
                f"{scenario['nominal_daily_rate']:.4f} "
                f"bAXS/day"
            )

            for days in projection[
                "horizons"
            ]:
                value = scenario[
                    "projections"
                ][days]

                print(
                    f"    {days} days: "
                    f"{value:.4f} bAXS"
                )



    print()
    print("Interpretation:")
    print(
        "- The rate uses cumulative total-acquired-bAXS change divided "
        "by the difference between recorded calendar dates."
    )
    print(
        "- Historical exact observation times are unavailable, so this "
        "is not a precise elapsed-time daily yield."
    )
    print(
        "- Projection scenarios assume the observed calendar-span pace "
        "continues unchanged."
    )
    print(
        "- No buff adjustment, unbuffed reconstruction, price forecast, "
        "or ROI assumption is included."
    )
    print(
        "- These projections describe bAXS accumulation only."
    )
    print(
        "- Conservative/base/upside scenarios are explicit pace "
        "multipliers, not confidence intervals or probability forecasts."
    )

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Evidence-aware Terrarium calendar-span "
            "projection for AxieOS V0.11."
        )
    )

    parser.add_argument(
        "--player",
        default="primary",
        help="Gameplay player_id. Default: primary",
    )

    parser.add_argument(
        "--horizons",
        type=int,
        nargs="+",
        default=list(DEFAULT_HORIZONS),
        help=(
            "Projection horizons in calendar days. "
            "Default: 7 30 365"
        ),
    )

    args = parser.parse_args()

    if any(
        days <= 0
        for days in args.horizons
    ):
        parser.error(
            "Projection horizons must be positive integers."
        )

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
            args.horizons,
        )
    )

    print_projection(
        projection
    )


if __name__ == "__main__":
    main()
