import argparse
import sqlite3
from decimal import Decimal, InvalidOperation

from database import connect_database


ZERO = Decimal("0")


def to_decimal(value):
    """
    Convert a SQLite value to Decimal without routing through float.

    Missing values remain None because AxieOS must not invent numeric
    evidence when the database does not contain it.
    """
    if value is None:
        return None

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def format_decimal(value, places=None):
    if value is None:
        return "UNKNOWN"

    if places is None:
        return format(value, "f")

    return f"{value:.{places}f}"


def signed_decimal(value, places):
    if value is None:
        return "UNKNOWN"

    return f"{value:+.{places}f}"


def load_snapshots(conn, player_id):
    rows = conn.execute(
        """
        SELECT
            ts.id AS snapshot_id,
            ts.daily_session_id,
            ds.session_date,
            ds.player_id,
            ts.snapshot_datetime,
            ts.snapshot_type,
            ts.global_lunium,
            ts.claimable_baxs,
            ts.buff_active,
            ts.buff_activation_time,
            ts.estimated_unbuffed_hours,
            ts.notes
        FROM terrarium_snapshots ts
        JOIN gameplay_daily_sessions ds
          ON ds.id = ts.daily_session_id
        WHERE ds.player_id = ?
        ORDER BY
            ds.session_date,
            ts.snapshot_datetime,
            ts.id
        """,
        (player_id,),
    ).fetchall()

    snapshots = []

    for row in rows:
        snapshot = {
            "snapshot_id": row["snapshot_id"],
            "daily_session_id": row["daily_session_id"],
            "session_date": row["session_date"],
            "player_id": row["player_id"],
            "snapshot_datetime": row["snapshot_datetime"],
            "snapshot_type": row["snapshot_type"],
            "global_lunium": row["global_lunium"],
            "claimable_baxs": to_decimal(row["claimable_baxs"]),
            "buff_active": row["buff_active"],
            "buff_activation_time": row["buff_activation_time"],
            "estimated_unbuffed_hours": to_decimal(
                row["estimated_unbuffed_hours"]
            ),
            "notes": row["notes"],
            "plots": [],
            "rankings": [],
        }

        plot_rows = conn.execute(
            """
            SELECT
                plot_type,
                plot_number,
                flame,
                next_distribution,
                total_acquired_baxs,
                notes
            FROM terrarium_plot_snapshots
            WHERE terrarium_snapshot_id = ?
            ORDER BY
                CASE plot_type
                    WHEN 'Forest' THEN 1
                    WHEN 'Savannah' THEN 2
                    ELSE 99
                END,
                plot_type,
                plot_number
            """,
            (row["snapshot_id"],),
        ).fetchall()

        for plot in plot_rows:
            snapshot["plots"].append(
                {
                    "plot_type": plot["plot_type"],
                    "plot_number": plot["plot_number"],
                    "flame": plot["flame"],
                    "next_distribution": to_decimal(
                        plot["next_distribution"]
                    ),
                    "total_acquired_baxs": to_decimal(
                        plot["total_acquired_baxs"]
                    ),
                    "notes": plot["notes"],
                }
            )

        ranking_rows = conn.execute(
            """
            SELECT
                group_type,
                rank,
                global_flame,
                notes
            FROM terrarium_group_rankings
            WHERE terrarium_snapshot_id = ?
            ORDER BY
                CASE group_type
                    WHEN 'Forest' THEN 1
                    WHEN 'Savannah' THEN 2
                    ELSE 99
                END,
                group_type
            """,
            (row["snapshot_id"],),
        ).fetchall()

        for ranking in ranking_rows:
            snapshot["rankings"].append(
                {
                    "group_type": ranking["group_type"],
                    "rank": ranking["rank"],
                    "global_flame": ranking["global_flame"],
                    "notes": ranking["notes"],
                }
            )

        snapshots.append(snapshot)

    return snapshots



def load_evidence_aware_snapshots(conn, player_id):
    """
    Load canonical Terrarium snapshots together with partial historical
    evidence.

    This function does not modify or replace the canonical loader.

    Canonical snapshots remain authoritative complete observations.
    Evidence rows remain explicitly identified as evidence and may contain
    missing metrics.

    No missing values are filled or inferred.
    """
    observations = []

    canonical_snapshots = load_snapshots(
        conn,
        player_id,
    )

    for snapshot in canonical_snapshots:
        item = snapshot.copy()

        item["record_source"] = "CANONICAL"
        item["completeness_status"] = "COMPLETE"
        item["evidence_id"] = None
        item["source"] = None
        item["source_reference"] = None
        item["observed_time_text"] = None

        observations.append(item)

    evidence_rows = conn.execute(
        """
        SELECT
            id,
            session_date,
            player_id,
            snapshot_type,
            observed_datetime,
            observed_time_text,
            completeness_status,
            global_lunium,
            claimable_baxs,
            buff_active,
            source,
            source_reference,
            notes
        FROM terrarium_snapshot_evidence
        WHERE player_id = ?
        ORDER BY
            session_date,
            id
        """,
        (player_id,),
    ).fetchall()

    for row in evidence_rows:
        observation = {
            "snapshot_id": None,
            "daily_session_id": None,
            "session_date": row["session_date"],
            "player_id": row["player_id"],
            "snapshot_datetime": row["observed_datetime"],
            "snapshot_type": row["snapshot_type"],
            "global_lunium": row["global_lunium"],
            "claimable_baxs": to_decimal(
                row["claimable_baxs"]
            ),
            "buff_active": row["buff_active"],
            "buff_activation_time": None,
            "estimated_unbuffed_hours": None,
            "notes": row["notes"],
            "plots": [],
            "rankings": [],

            "record_source": "EVIDENCE",
            "completeness_status": (
                row["completeness_status"]
            ),
            "evidence_id": row["id"],
            "source": row["source"],
            "source_reference": (
                row["source_reference"]
            ),
            "observed_time_text": (
                row["observed_time_text"]
            ),
        }

        plot_rows = conn.execute(
            """
            SELECT
                plot_type,
                plot_number,
                flame,
                next_distribution,
                total_acquired_baxs,
                notes
            FROM terrarium_plot_evidence
            WHERE terrarium_evidence_id = ?
            ORDER BY
                CASE plot_type
                    WHEN 'Forest' THEN 1
                    WHEN 'Savannah' THEN 2
                    ELSE 99
                END,
                plot_type,
                plot_number
            """,
            (row["id"],),
        ).fetchall()

        for plot in plot_rows:
            observation["plots"].append(
                {
                    "plot_type": plot["plot_type"],
                    "plot_number": plot["plot_number"],
                    "flame": plot["flame"],
                    "next_distribution": to_decimal(
                        plot["next_distribution"]
                    ),
                    "total_acquired_baxs": to_decimal(
                        plot["total_acquired_baxs"]
                    ),
                    "notes": plot["notes"],
                }
            )

        ranking_rows = conn.execute(
            """
            SELECT
                group_type,
                rank,
                global_flame,
                notes
            FROM terrarium_group_ranking_evidence
            WHERE terrarium_evidence_id = ?
            ORDER BY
                CASE group_type
                    WHEN 'Forest' THEN 1
                    WHEN 'Savannah' THEN 2
                    ELSE 99
                END,
                group_type
            """,
            (row["id"],),
        ).fetchall()

        for ranking in ranking_rows:
            observation["rankings"].append(
                {
                    "group_type": ranking["group_type"],
                    "rank": ranking["rank"],
                    "global_flame": ranking["global_flame"],
                    "notes": ranking["notes"],
                }
            )

        observations.append(observation)

    snapshot_type_order = {
        "morning": 1,
        "afternoon": 2,
        "evening": 3,
        "end_of_day": 4,
    }

    def observation_sort_key(observation):
        return (
            observation["session_date"],
            snapshot_type_order.get(
                observation["snapshot_type"],
                99,
            ),
            0
            if observation["record_source"] == "CANONICAL"
            else 1,
            observation["snapshot_id"]
            if observation["snapshot_id"] is not None
            else observation["evidence_id"],
        )

    observations.sort(
        key=observation_sort_key
    )

    return observations



def add_evidence_aware_history_deltas(observations):
    """
    Add metric-aware deltas to mixed canonical/evidence observations.

    Unlike add_history_deltas(), this function does not require the
    immediately previous observation to contain the same metric.

    Each metric is compared with its last known prior value.

    The number of skipped intervening observations is recorded so AxieOS
    does not misrepresent a multi-observation change as an adjacent
    observation interval.
    """

    last_global_lunium = None
    last_claimable_baxs = None

    last_plot_metrics = {}
    last_ranking_metrics = {}

    for observation_index, observation in enumerate(
        observations
    ):
        # ----------------------------------------------------
        # Top-level metrics
        # ----------------------------------------------------

        observation["global_lunium_delta"] = None
        observation[
            "global_lunium_delta_from_session_date"
        ] = None
        observation[
            "global_lunium_delta_skipped_observations"
        ] = None

        observation["claimable_baxs_delta"] = None
        observation[
            "claimable_baxs_delta_from_session_date"
        ] = None
        observation[
            "claimable_baxs_delta_skipped_observations"
        ] = None

        observation["claimable_reset_possible"] = False

        current_lunium = observation[
            "global_lunium"
        ]

        if current_lunium is not None:
            if last_global_lunium is not None:
                observation["global_lunium_delta"] = (
                    current_lunium
                    - last_global_lunium["value"]
                )

                observation[
                    "global_lunium_delta_from_session_date"
                ] = last_global_lunium[
                    "session_date"
                ]

                observation[
                    "global_lunium_delta_skipped_observations"
                ] = (
                    observation_index
                    - last_global_lunium[
                        "observation_index"
                    ]
                    - 1
                )

            last_global_lunium = {
                "value": current_lunium,
                "session_date": observation[
                    "session_date"
                ],
                "observation_index": observation_index,
            }

        current_claimable = observation[
            "claimable_baxs"
        ]

        if current_claimable is not None:
            if last_claimable_baxs is not None:
                claimable_delta = (
                    current_claimable
                    - last_claimable_baxs["value"]
                )

                observation[
                    "claimable_baxs_delta"
                ] = claimable_delta

                observation[
                    "claimable_baxs_delta_from_session_date"
                ] = last_claimable_baxs[
                    "session_date"
                ]

                observation[
                    "claimable_baxs_delta_skipped_observations"
                ] = (
                    observation_index
                    - last_claimable_baxs[
                        "observation_index"
                    ]
                    - 1
                )

                if claimable_delta < ZERO:
                    observation[
                        "claimable_reset_possible"
                    ] = True

            last_claimable_baxs = {
                "value": current_claimable,
                "session_date": observation[
                    "session_date"
                ],
                "observation_index": observation_index,
            }

        # ----------------------------------------------------
        # Plot metrics
        # ----------------------------------------------------

        for plot in observation["plots"]:
            plot_key = (
                plot["plot_type"],
                plot["plot_number"],
            )

            if plot_key not in last_plot_metrics:
                last_plot_metrics[plot_key] = {}

            metric_state = last_plot_metrics[
                plot_key
            ]

            for metric_name in (
                "flame",
                "next_distribution",
                "total_acquired_baxs",
            ):
                delta_field = (
                    f"{metric_name}_delta"
                )

                from_date_field = (
                    f"{metric_name}_delta_"
                    "from_session_date"
                )

                skipped_field = (
                    f"{metric_name}_delta_"
                    "skipped_observations"
                )

                plot[delta_field] = None
                plot[from_date_field] = None
                plot[skipped_field] = None

                current_value = plot[
                    metric_name
                ]

                if current_value is None:
                    continue

                previous = metric_state.get(
                    metric_name
                )

                if previous is not None:
                    plot[delta_field] = (
                        current_value
                        - previous["value"]
                    )

                    plot[from_date_field] = (
                        previous["session_date"]
                    )

                    plot[skipped_field] = (
                        observation_index
                        - previous[
                            "observation_index"
                        ]
                        - 1
                    )

                metric_state[metric_name] = {
                    "value": current_value,
                    "session_date": observation[
                        "session_date"
                    ],
                    "observation_index": (
                        observation_index
                    ),
                }

        # ----------------------------------------------------
        # Ranking metrics
        # ----------------------------------------------------

        for ranking in observation["rankings"]:
            group_type = ranking[
                "group_type"
            ]

            if (
                group_type
                not in last_ranking_metrics
            ):
                last_ranking_metrics[
                    group_type
                ] = {}

            metric_state = last_ranking_metrics[
                group_type
            ]

            for metric_name in (
                "rank",
                "global_flame",
            ):
                delta_field = (
                    f"{metric_name}_delta"
                )

                from_date_field = (
                    f"{metric_name}_delta_"
                    "from_session_date"
                )

                skipped_field = (
                    f"{metric_name}_delta_"
                    "skipped_observations"
                )

                ranking[delta_field] = None
                ranking[from_date_field] = None
                ranking[skipped_field] = None

                current_value = ranking[
                    metric_name
                ]

                if current_value is None:
                    continue

                previous = metric_state.get(
                    metric_name
                )

                if previous is not None:
                    ranking[delta_field] = (
                        current_value
                        - previous["value"]
                    )

                    ranking[from_date_field] = (
                        previous["session_date"]
                    )

                    ranking[skipped_field] = (
                        observation_index
                        - previous[
                            "observation_index"
                        ]
                        - 1
                    )

                metric_state[metric_name] = {
                    "value": current_value,
                    "session_date": observation[
                        "session_date"
                    ],
                    "observation_index": (
                        observation_index
                    ),
                }




def calculate_evidence_aware_summary(observations):
    """
    Calculate evidence-aware Terrarium coverage and latest-known metrics.

    Each metric is evaluated independently.

    Missing values are skipped rather than filled, so a partial historical
    observation can contribute to metrics that are actually present without
    being treated as a complete Terrarium snapshot.
    """

    if not observations:
        return {
            "observation_count": 0,
            "canonical_count": 0,
            "evidence_count": 0,
            "represented_dates": [],
            "represented_day_count": 0,
            "global_lunium": None,
            "claimable_baxs": None,
            "plots": [],
            "rankings": [],
            "accumulation": None,
            "latest_complete_distribution": None,
        }

    def summarize_metric(
        metric_observations,
    ):
        known = [
            item
            for item in metric_observations
            if item["value"] is not None
        ]

        if not known:
            return {
                "observation_count": 0,
                "first_value": None,
                "first_date": None,
                "latest_value": None,
                "latest_date": None,
                "latest_snapshot_type": None,
                "latest_record_source": None,
                "latest_record_id": None,
            }

        first = known[0]
        latest = known[-1]

        return {
            "observation_count": len(known),
            "first_value": first["value"],
            "first_date": first["observation"][
                "session_date"
            ],
            "latest_value": latest["value"],
            "latest_date": latest["observation"][
                "session_date"
            ],
            "latest_snapshot_type": latest[
                "observation"
            ]["snapshot_type"],
            "latest_record_source": latest[
                "observation"
            ]["record_source"],
            "latest_record_id": (
                latest["observation"]["snapshot_id"]
                if latest["observation"][
                    "record_source"
                ] == "CANONICAL"
                else latest["observation"][
                    "evidence_id"
                ]
            ),
        }

    canonical_count = sum(
        1
        for observation in observations
        if observation["record_source"]
        == "CANONICAL"
    )

    evidence_count = sum(
        1
        for observation in observations
        if observation["record_source"]
        == "EVIDENCE"
    )

    represented_dates = sorted(
        {
            observation["session_date"]
            for observation in observations
        }
    )

    global_lunium = summarize_metric(
        [
            {
                "observation": observation,
                "value": observation[
                    "global_lunium"
                ],
            }
            for observation in observations
        ]
    )

    claimable_baxs = summarize_metric(
        [
            {
                "observation": observation,
                "value": observation[
                    "claimable_baxs"
                ],
            }
            for observation in observations
        ]
    )

    # --------------------------------------------------------
    # Plot metric coverage
    # --------------------------------------------------------

    plot_keys = sorted(
        {
            (
                plot["plot_type"],
                plot["plot_number"],
            )
            for observation in observations
            for plot in observation["plots"]
        },
        key=lambda key: (
            1
            if key[0] == "Forest"
            else 2
            if key[0] == "Savannah"
            else 99,
            key[0],
            key[1],
        ),
    )

    plot_summaries = []

    for plot_type, plot_number in plot_keys:
        matched = []

        for observation in observations:
            plot = next(
                (
                    item
                    for item in observation["plots"]
                    if item["plot_type"]
                    == plot_type
                    and item["plot_number"]
                    == plot_number
                ),
                None,
            )

            if plot is not None:
                matched.append(
                    {
                        "observation": observation,
                        "plot": plot,
                    }
                )

        flame = summarize_metric(
            [
                {
                    "observation": item[
                        "observation"
                    ],
                    "value": item["plot"][
                        "flame"
                    ],
                }
                for item in matched
            ]
        )

        next_distribution = summarize_metric(
            [
                {
                    "observation": item[
                        "observation"
                    ],
                    "value": item["plot"][
                        "next_distribution"
                    ],
                }
                for item in matched
            ]
        )

        total_acquired_baxs = summarize_metric(
            [
                {
                    "observation": item[
                        "observation"
                    ],
                    "value": item["plot"][
                        "total_acquired_baxs"
                    ],
                }
                for item in matched
            ]
        )

        accumulation_delta = None

        if (
            total_acquired_baxs[
                "first_value"
            ] is not None
            and total_acquired_baxs[
                "latest_value"
            ] is not None
        ):
            accumulation_delta = (
                total_acquired_baxs[
                    "latest_value"
                ]
                - total_acquired_baxs[
                    "first_value"
                ]
            )

        plot_summaries.append(
            {
                "plot_type": plot_type,
                "plot_number": plot_number,
                "row_observation_count": len(
                    matched
                ),
                "flame": flame,
                "next_distribution": (
                    next_distribution
                ),
                "total_acquired_baxs": (
                    total_acquired_baxs
                ),
                "accumulation_delta": (
                    accumulation_delta
                ),
            }
        )

    # --------------------------------------------------------
    # Ranking metric coverage
    # --------------------------------------------------------

    ranking_groups = sorted(
        {
            ranking["group_type"]
            for observation in observations
            for ranking in observation[
                "rankings"
            ]
        },
        key=lambda group: (
            1
            if group == "Forest"
            else 2
            if group == "Savannah"
            else 99,
            group,
        ),
    )

    ranking_summaries = []

    for group_type in ranking_groups:
        matched = []

        for observation in observations:
            ranking = next(
                (
                    item
                    for item in observation[
                        "rankings"
                    ]
                    if item["group_type"]
                    == group_type
                ),
                None,
            )

            if ranking is not None:
                matched.append(
                    {
                        "observation": observation,
                        "ranking": ranking,
                    }
                )

        rank = summarize_metric(
            [
                {
                    "observation": item[
                        "observation"
                    ],
                    "value": item["ranking"][
                        "rank"
                    ],
                }
                for item in matched
            ]
        )

        global_flame = summarize_metric(
            [
                {
                    "observation": item[
                        "observation"
                    ],
                    "value": item["ranking"][
                        "global_flame"
                    ],
                }
                for item in matched
            ]
        )

        ranking_summaries.append(
            {
                "group_type": group_type,
                "row_observation_count": len(
                    matched
                ),
                "rank": rank,
                "global_flame": global_flame,
            }
        )

    # --------------------------------------------------------
    # First-to-latest cumulative bAXS composition
    # --------------------------------------------------------

    accumulation_rows = []
    combined_accumulation_delta = ZERO

    for plot in plot_summaries:
        delta = plot[
            "accumulation_delta"
        ]

        accumulation_rows.append(
            {
                "plot_type": plot[
                    "plot_type"
                ],
                "plot_number": plot[
                    "plot_number"
                ],
                "first_value": plot[
                    "total_acquired_baxs"
                ]["first_value"],
                "first_date": plot[
                    "total_acquired_baxs"
                ]["first_date"],
                "latest_value": plot[
                    "total_acquired_baxs"
                ]["latest_value"],
                "latest_date": plot[
                    "total_acquired_baxs"
                ]["latest_date"],
                "delta": delta,
            }
        )

        if delta is not None:
            combined_accumulation_delta += delta

    accumulation = {
        "plots": accumulation_rows,
        "combined_delta": (
            combined_accumulation_delta
        ),
    }

    # --------------------------------------------------------
    # Latest observation with all 3 Next Distribution metrics
    # --------------------------------------------------------

    expected_plot_keys = {
        ("Forest", 1),
        ("Savannah", 1),
        ("Savannah", 2),
    }

    latest_complete_distribution = None

    for observation in reversed(
        observations
    ):
        plot_map = {
            (
                plot["plot_type"],
                plot["plot_number"],
            ): plot
            for plot in observation["plots"]
        }

        if not expected_plot_keys.issubset(
            plot_map
        ):
            continue

        values = []

        complete = True

        for key in (
            ("Forest", 1),
            ("Savannah", 1),
            ("Savannah", 2),
        ):
            value = plot_map[key][
                "next_distribution"
            ]

            if value is None:
                complete = False
                break

            values.append(
                {
                    "plot_type": key[0],
                    "plot_number": key[1],
                    "value": value,
                }
            )

        if not complete:
            continue

        combined = sum(
            (
                row["value"]
                for row in values
            ),
            ZERO,
        )

        latest_complete_distribution = {
            "session_date": observation[
                "session_date"
            ],
            "snapshot_type": observation[
                "snapshot_type"
            ],
            "record_source": observation[
                "record_source"
            ],
            "record_id": (
                observation["snapshot_id"]
                if observation[
                    "record_source"
                ] == "CANONICAL"
                else observation[
                    "evidence_id"
                ]
            ),
            "plots": values,
            "combined": combined,
        }

        break

    return {
        "observation_count": len(
            observations
        ),
        "canonical_count": canonical_count,
        "evidence_count": evidence_count,
        "represented_dates": (
            represented_dates
        ),
        "represented_day_count": len(
            represented_dates
        ),
        "global_lunium": global_lunium,
        "claimable_baxs": claimable_baxs,
        "plots": plot_summaries,
        "rankings": ranking_summaries,
        "accumulation": accumulation,
        "latest_complete_distribution": (
            latest_complete_distribution
        ),
    }





def add_history_deltas(snapshots):
    previous_snapshot = None
    previous_plots = {}

    for snapshot in snapshots:
        snapshot["global_lunium_delta"] = None
        snapshot["claimable_baxs_delta"] = None
        snapshot["claimable_reset_possible"] = False

        if previous_snapshot is not None:
            current_lunium = snapshot["global_lunium"]
            previous_lunium = previous_snapshot["global_lunium"]

            if current_lunium is not None and previous_lunium is not None:
                snapshot["global_lunium_delta"] = (
                    current_lunium - previous_lunium
                )

            current_claimable = snapshot["claimable_baxs"]
            previous_claimable = previous_snapshot["claimable_baxs"]

            if (
                current_claimable is not None
                and previous_claimable is not None
            ):
                claimable_delta = current_claimable - previous_claimable
                snapshot["claimable_baxs_delta"] = claimable_delta

                if claimable_delta < ZERO:
                    snapshot["claimable_reset_possible"] = True

        for plot in snapshot["plots"]:
            key = (
                plot["plot_type"],
                plot["plot_number"],
            )

            plot["flame_delta"] = None
            plot["total_acquired_baxs_delta"] = None

            previous_plot = previous_plots.get(key)

            if previous_plot is not None:
                current_flame = plot["flame"]
                previous_flame = previous_plot["flame"]

                if current_flame is not None and previous_flame is not None:
                    plot["flame_delta"] = (
                        current_flame - previous_flame
                    )

                current_total = plot["total_acquired_baxs"]
                previous_total = previous_plot["total_acquired_baxs"]

                if current_total is not None and previous_total is not None:
                    plot["total_acquired_baxs_delta"] = (
                        current_total - previous_total
                    )

            previous_plots[key] = plot.copy()

        previous_snapshot = snapshot


def print_summary(snapshots, player_id):
    print("=" * 72)
    print("AXIEOS V0.11 — TERRARIUM HISTORICAL SUMMARY")
    print("=" * 72)

    print(f"Player: {player_id}")
    print(f"Snapshots: {len(snapshots)}")

    if not snapshots:
        print("No Terrarium snapshots found.")
        return

    print(
        "Date range: "
        f"{snapshots[0]['session_date']} "
        f"to {snapshots[-1]['session_date']}"
    )

    print()

    for snapshot in snapshots:
        print("-" * 72)

        print(
            f"Snapshot #{snapshot['snapshot_id']} | "
            f"{snapshot['session_date']} | "
            f"{snapshot['snapshot_type'] or 'UNKNOWN'}"
        )

        print(
            "Stored snapshot datetime: "
            f"{snapshot['snapshot_datetime']}"
        )

        lunium_text = str(snapshot["global_lunium"])

        if snapshot["global_lunium_delta"] is not None:
            lunium_text += (
                f" ({snapshot['global_lunium_delta']:+d})"
            )

        print(f"Global Lunium: {lunium_text}")

        claimable_text = format_decimal(
            snapshot["claimable_baxs"],
            2,
        )

        if snapshot["claimable_baxs_delta"] is not None:
            claimable_text += (
                " ("
                + signed_decimal(
                    snapshot["claimable_baxs_delta"],
                    2,
                )
                + ")"
            )

        if snapshot["claimable_reset_possible"]:
            claimable_text += " [RESET/CLAIM POSSIBLE]"

        print(f"Claimable bAXS: {claimable_text}")

        print("Plots:")

        for plot in snapshot["plots"]:
            plot_name = (
                f"{plot['plot_type']} #{plot['plot_number']}"
            )

            flame_text = str(plot["flame"])

            if plot["flame_delta"] is not None:
                flame_text += (
                    f" ({plot['flame_delta']:+d})"
                )

            acquired_text = format_decimal(
                plot["total_acquired_baxs"],
                4,
            )

            if plot["total_acquired_baxs_delta"] is not None:
                acquired_text += (
                    " ("
                    + signed_decimal(
                        plot["total_acquired_baxs_delta"],
                        4,
                    )
                    + ")"
                )

            print(f"  {plot_name}")
            print(f"    Flame: {flame_text}")
            print(
                "    Next distribution: "
                f"{format_decimal(plot['next_distribution'], 4)}"
            )
            print(
                "    Total acquired bAXS: "
                f"{acquired_text}"
            )

        if snapshot["rankings"]:
            print("Rankings:")

            for ranking in snapshot["rankings"]:
                print(
                    f"  {ranking['group_type']}: "
                    f"rank {ranking['rank']}, "
                    f"global flame {ranking['global_flame']}"
                )

        if snapshot["notes"]:
            print(f"Notes: {snapshot['notes']}")

        print()

    print("=" * 72)
    print("DATA QUALITY NOTES")
    print("=" * 72)
    print(
        "- Historical snapshot_datetime values may contain only a date."
    )
    print(
        "- Snapshot types are preserved exactly as stored."
    )
    print(
        "- Negative claimable-bAXS movement is not treated as negative yield."
    )
    print(
        "- total_acquired_baxs deltas are observational changes between "
        "stored snapshots."
    )
    print(
        "- No hourly rates, projections, or ROI are calculated."
    )




def validate_history(snapshots):
    errors = []
    warnings = []

    if not snapshots:
        errors.append("No Terrarium snapshots were loaded.")

        return {
            "status": "FAIL",
            "errors": errors,
            "warnings": warnings,
            "snapshot_count": 0,
            "plot_keys": [],
            "ranking_groups": [],
        }

    # --------------------------------------------------------
    # Establish observed structural baseline.
    # --------------------------------------------------------

    first_snapshot = snapshots[0]

    expected_plot_keys = [
        (
            plot["plot_type"],
            plot["plot_number"],
        )
        for plot in first_snapshot["plots"]
    ]

    expected_ranking_groups = [
        ranking["group_type"]
        for ranking in first_snapshot["rankings"]
    ]

    expected_plot_key_set = set(expected_plot_keys)
    expected_ranking_group_set = set(expected_ranking_groups)

    if len(expected_plot_keys) != len(expected_plot_key_set):
        errors.append(
            "The first snapshot contains duplicate plot identities."
        )

    if (
        len(expected_ranking_groups)
        != len(expected_ranking_group_set)
    ):
        errors.append(
            "The first snapshot contains duplicate ranking groups."
        )

    # --------------------------------------------------------
    # Chronological and structural validation.
    # --------------------------------------------------------

    previous_order_key = None
    previous_plot_totals = {}

    for snapshot in snapshots:
        snapshot_id = snapshot["snapshot_id"]

        order_key = (
            snapshot["session_date"],
            snapshot["snapshot_datetime"] or "",
            snapshot_id,
        )

        if (
            previous_order_key is not None
            and order_key < previous_order_key
        ):
            errors.append(
                f"Snapshot #{snapshot_id} is out of chronological order."
            )

        previous_order_key = order_key

        plot_keys = [
            (
                plot["plot_type"],
                plot["plot_number"],
            )
            for plot in snapshot["plots"]
        ]

        plot_key_set = set(plot_keys)

        if len(plot_keys) != len(plot_key_set):
            errors.append(
                f"Snapshot #{snapshot_id} contains duplicate plot rows."
            )

        if plot_key_set != expected_plot_key_set:
            missing = (
                expected_plot_key_set
                - plot_key_set
            )

            unexpected = (
                plot_key_set
                - expected_plot_key_set
            )

            if missing:
                errors.append(
                    f"Snapshot #{snapshot_id} is missing plots: "
                    f"{sorted(missing)}"
                )

            if unexpected:
                warnings.append(
                    f"Snapshot #{snapshot_id} contains new/unexpected "
                    f"plots: {sorted(unexpected)}"
                )

        ranking_groups = [
            ranking["group_type"]
            for ranking in snapshot["rankings"]
        ]

        ranking_group_set = set(ranking_groups)

        if len(ranking_groups) != len(ranking_group_set):
            errors.append(
                f"Snapshot #{snapshot_id} contains duplicate "
                "ranking groups."
            )

        if ranking_group_set != expected_ranking_group_set:
            missing = (
                expected_ranking_group_set
                - ranking_group_set
            )

            unexpected = (
                ranking_group_set
                - expected_ranking_group_set
            )

            if missing:
                errors.append(
                    f"Snapshot #{snapshot_id} is missing ranking "
                    f"groups: {sorted(missing)}"
                )

            if unexpected:
                warnings.append(
                    f"Snapshot #{snapshot_id} contains new/unexpected "
                    f"ranking groups: {sorted(unexpected)}"
                )

        # ----------------------------------------------------
        # Required parent observations.
        # ----------------------------------------------------

        if snapshot["global_lunium"] is None:
            warnings.append(
                f"Snapshot #{snapshot_id} has no Global Lunium value."
            )

        if snapshot["claimable_baxs"] is None:
            warnings.append(
                f"Snapshot #{snapshot_id} has no claimable bAXS value."
            )

        # ----------------------------------------------------
        # Plot-level observations and cumulative integrity.
        # ----------------------------------------------------

        for plot in snapshot["plots"]:
            plot_key = (
                plot["plot_type"],
                plot["plot_number"],
            )

            plot_name = (
                f"{plot['plot_type']} "
                f"#{plot['plot_number']}"
            )

            if plot["flame"] is None:
                warnings.append(
                    f"Snapshot #{snapshot_id} {plot_name} "
                    "has no Flame value."
                )

            if plot["next_distribution"] is None:
                warnings.append(
                    f"Snapshot #{snapshot_id} {plot_name} "
                    "has no next-distribution value."
                )

            current_total = plot["total_acquired_baxs"]

            if current_total is None:
                warnings.append(
                    f"Snapshot #{snapshot_id} {plot_name} "
                    "has no total-acquired-bAXS value."
                )

                continue

            previous_total = previous_plot_totals.get(
                plot_key
            )

            if (
                previous_total is not None
                and current_total < previous_total
            ):
                errors.append(
                    f"Snapshot #{snapshot_id} {plot_name} "
                    "total acquired bAXS decreased from "
                    f"{previous_total} to {current_total}."
                )

            previous_plot_totals[plot_key] = current_total

        # ----------------------------------------------------
        # Ranking observations.
        # ----------------------------------------------------

        for ranking in snapshot["rankings"]:
            group_type = ranking["group_type"]

            if ranking["rank"] is None:
                warnings.append(
                    f"Snapshot #{snapshot_id} {group_type} "
                    "has no rank."
                )

            if ranking["global_flame"] is None:
                warnings.append(
                    f"Snapshot #{snapshot_id} {group_type} "
                    "has no global Flame value."
                )

    if errors:
        status = "FAIL"
    elif warnings:
        status = "REVIEW"
    else:
        status = "PASS"

    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "snapshot_count": len(snapshots),
        "plot_keys": sorted(expected_plot_key_set),
        "ranking_groups": sorted(
            expected_ranking_group_set
        ),
    }


def print_history_validation(validation):
    print()
    print("=" * 72)
    print("HISTORICAL DATA VALIDATION")
    print("=" * 72)

    print(
        f"Snapshots checked: "
        f"{validation['snapshot_count']}"
    )

    print(
        f"Observed plots: "
        f"{len(validation['plot_keys'])}"
    )

    for plot_type, plot_number in validation["plot_keys"]:
        print(
            f"  {plot_type} #{plot_number}"
        )

    print(
        f"Ranking groups: "
        f"{len(validation['ranking_groups'])}"
    )

    for group_type in validation["ranking_groups"]:
        print(
            f"  {group_type}"
        )

    print(
        f"Errors: {len(validation['errors'])}"
    )

    print(
        f"Warnings: {len(validation['warnings'])}"
    )

    if validation["errors"]:
        print()
        print("Errors:")

        for error in validation["errors"]:
            print(
                f"  - {error}"
            )

    if validation["warnings"]:
        print()
        print("Warnings:")

        for warning in validation["warnings"]:
            print(
                f"  - {warning}"
            )

    print()
    print(
        f"Historical validation: "
        f"{validation['status']}"
    )




def calculate_period_summary(snapshots):
    if not snapshots:
        return None

    first_snapshot = snapshots[0]
    last_snapshot = snapshots[-1]

    summary = {
        "snapshot_count": len(snapshots),
        "first_date": first_snapshot["session_date"],
        "last_date": last_snapshot["session_date"],
        "global_lunium_start": first_snapshot["global_lunium"],
        "global_lunium_end": last_snapshot["global_lunium"],
        "global_lunium_delta": None,
        "claimable_reset_signals": sum(
            1
            for snapshot in snapshots
            if snapshot["claimable_reset_possible"]
        ),
        "plots": [],
        "rankings": [],
        "combined_acquired_baxs_delta": None,
    }

    if (
        first_snapshot["global_lunium"] is not None
        and last_snapshot["global_lunium"] is not None
    ):
        summary["global_lunium_delta"] = (
            last_snapshot["global_lunium"]
            - first_snapshot["global_lunium"]
        )

    plot_history = {}

    for snapshot in snapshots:
        for plot in snapshot["plots"]:
            key = (
                plot["plot_type"],
                plot["plot_number"],
            )

            if key not in plot_history:
                plot_history[key] = {
                    "first": plot,
                    "last": plot,
                }
            else:
                plot_history[key]["last"] = plot

    acquired_deltas = []

    for key, history in plot_history.items():
        first_plot = history["first"]
        last_plot = history["last"]

        flame_delta = None
        acquired_delta = None
        distribution_delta = None

        if (
            first_plot["flame"] is not None
            and last_plot["flame"] is not None
        ):
            flame_delta = (
                last_plot["flame"]
                - first_plot["flame"]
            )

        if (
            first_plot["total_acquired_baxs"] is not None
            and last_plot["total_acquired_baxs"] is not None
        ):
            acquired_delta = (
                last_plot["total_acquired_baxs"]
                - first_plot["total_acquired_baxs"]
            )

            acquired_deltas.append(acquired_delta)

        if (
            first_plot["next_distribution"] is not None
            and last_plot["next_distribution"] is not None
        ):
            distribution_delta = (
                last_plot["next_distribution"]
                - first_plot["next_distribution"]
            )

        summary["plots"].append(
            {
                "plot_type": key[0],
                "plot_number": key[1],
                "flame_start": first_plot["flame"],
                "flame_end": last_plot["flame"],
                "flame_delta": flame_delta,
                "total_acquired_baxs_start": (
                    first_plot["total_acquired_baxs"]
                ),
                "total_acquired_baxs_end": (
                    last_plot["total_acquired_baxs"]
                ),
                "total_acquired_baxs_delta": acquired_delta,
                "next_distribution_start": (
                    first_plot["next_distribution"]
                ),
                "next_distribution_end": (
                    last_plot["next_distribution"]
                ),
                "next_distribution_delta": distribution_delta,
            }
        )

    if (
        acquired_deltas
        and len(acquired_deltas) == len(plot_history)
    ):
        summary["combined_acquired_baxs_delta"] = sum(
            acquired_deltas,
            ZERO,
        )

    ranking_history = {}

    for snapshot in snapshots:
        for ranking in snapshot["rankings"]:
            key = ranking["group_type"]

            if key not in ranking_history:
                ranking_history[key] = {
                    "first": ranking,
                    "last": ranking,
                }
            else:
                ranking_history[key]["last"] = ranking

    for group_type, history in ranking_history.items():
        first_ranking = history["first"]
        last_ranking = history["last"]

        rank_delta = None
        global_flame_delta = None

        if (
            first_ranking["rank"] is not None
            and last_ranking["rank"] is not None
        ):
            rank_delta = (
                last_ranking["rank"]
                - first_ranking["rank"]
            )

        if (
            first_ranking["global_flame"] is not None
            and last_ranking["global_flame"] is not None
        ):
            global_flame_delta = (
                last_ranking["global_flame"]
                - first_ranking["global_flame"]
            )

        summary["rankings"].append(
            {
                "group_type": group_type,
                "rank_start": first_ranking["rank"],
                "rank_end": last_ranking["rank"],
                "rank_delta": rank_delta,
                "global_flame_start": (
                    first_ranking["global_flame"]
                ),
                "global_flame_end": (
                    last_ranking["global_flame"]
                ),
                "global_flame_delta": global_flame_delta,
            }
        )

    return summary


def print_period_summary(summary):
    if summary is None:
        return

    print()
    print("=" * 72)
    print("OBSERVED PERIOD SUMMARY")
    print("=" * 72)

    print(
        f"Observed range: "
        f"{summary['first_date']} "
        f"to {summary['last_date']}"
    )

    print(
        f"Snapshots: "
        f"{summary['snapshot_count']}"
    )

    lunium_text = (
        f"{summary['global_lunium_start']} "
        f"-> {summary['global_lunium_end']}"
    )

    if summary["global_lunium_delta"] is not None:
        lunium_text += (
            f" ({summary['global_lunium_delta']:+d})"
        )

    print(f"Global Lunium: {lunium_text}")

    print(
        "Claim/reset signals: "
        f"{summary['claimable_reset_signals']}"
    )

    print()
    print("Observed cumulative bAXS change:")

    for plot in summary["plots"]:
        plot_name = (
            f"{plot['plot_type']} #{plot['plot_number']}"
        )

        print(
            f"  {plot_name}: "
            f"{format_decimal(
                plot['total_acquired_baxs_start'],
                4,
            )} "
            f"-> "
            f"{format_decimal(
                plot['total_acquired_baxs_end'],
                4,
            )} "
            f"("
            f"{signed_decimal(
                plot['total_acquired_baxs_delta'],
                4,
            )}"
            f")"
        )

    print(
        "  Combined change: "
        f"{signed_decimal(
            summary['combined_acquired_baxs_delta'],
            4,
        )}"
    )

    print()
    print("Flame movement:")

    for plot in summary["plots"]:
        plot_name = (
            f"{plot['plot_type']} #{plot['plot_number']}"
        )

        flame_delta = plot["flame_delta"]

        if flame_delta is None:
            flame_delta_text = "UNKNOWN"
        else:
            flame_delta_text = f"{flame_delta:+d}"

        print(
            f"  {plot_name}: "
            f"{plot['flame_start']} "
            f"-> {plot['flame_end']} "
            f"({flame_delta_text})"
        )

    print()
    print("Ranking movement:")

    for ranking in summary["rankings"]:
        rank_delta = ranking["rank_delta"]

        if rank_delta is None:
            rank_delta_text = "UNKNOWN"
        else:
            rank_delta_text = f"{rank_delta:+d}"

        print(
            f"  {ranking['group_type']}: "
            f"{ranking['rank_start']} "
            f"-> {ranking['rank_end']} "
            f"({rank_delta_text}; lower rank number is better)"
        )

    print()
    print("Interpretation:")
    print(
        "- Changes are calculated only between the first and last "
        "stored observations."
    )
    print(
        "- Observed cumulative bAXS change is not converted into an "
        "hourly or daily yield."
    )
    print(
        "- Missing exact historical snapshot times prevent precise "
        "time-normalized yield calculations."
    )



def calculate_trend_summary(snapshots):
    if not snapshots:
        return None

    summary = {
        "snapshot_count": len(snapshots),
        "global_lunium_min": None,
        "global_lunium_max": None,
        "global_lunium_latest": None,
        "plots": [],
        "rankings": [],
    }

    lunium_values = [
        snapshot["global_lunium"]
        for snapshot in snapshots
        if snapshot["global_lunium"] is not None
    ]

    if lunium_values:
        summary["global_lunium_min"] = min(lunium_values)
        summary["global_lunium_max"] = max(lunium_values)
        summary["global_lunium_latest"] = lunium_values[-1]

    plot_history = {}

    for snapshot in snapshots:
        for plot in snapshot["plots"]:
            key = (
                plot["plot_type"],
                plot["plot_number"],
            )

            if key not in plot_history:
                plot_history[key] = []

            plot_history[key].append(plot)

    for key, observations in plot_history.items():
        flame_values = [
            observation["flame"]
            for observation in observations
            if observation["flame"] is not None
        ]

        distribution_values = [
            observation["next_distribution"]
            for observation in observations
            if observation["next_distribution"] is not None
        ]

        acquired_values = [
            observation["total_acquired_baxs"]
            for observation in observations
            if observation["total_acquired_baxs"] is not None
        ]

        plot_summary = {
            "plot_type": key[0],
            "plot_number": key[1],
            "observations": len(observations),
            "flame_min": None,
            "flame_max": None,
            "flame_latest": None,
            "distribution_min": None,
            "distribution_max": None,
            "distribution_latest": None,
            "acquired_min": None,
            "acquired_max": None,
            "acquired_latest": None,
        }

        if flame_values:
            plot_summary["flame_min"] = min(flame_values)
            plot_summary["flame_max"] = max(flame_values)
            plot_summary["flame_latest"] = flame_values[-1]

        if distribution_values:
            plot_summary["distribution_min"] = min(
                distribution_values
            )
            plot_summary["distribution_max"] = max(
                distribution_values
            )
            plot_summary["distribution_latest"] = (
                distribution_values[-1]
            )

        if acquired_values:
            plot_summary["acquired_min"] = min(
                acquired_values
            )
            plot_summary["acquired_max"] = max(
                acquired_values
            )
            plot_summary["acquired_latest"] = (
                acquired_values[-1]
            )

        summary["plots"].append(plot_summary)

    ranking_history = {}

    for snapshot in snapshots:
        for ranking in snapshot["rankings"]:
            group_type = ranking["group_type"]

            if group_type not in ranking_history:
                ranking_history[group_type] = []

            ranking_history[group_type].append(ranking)

    for group_type, observations in ranking_history.items():
        rank_values = [
            observation["rank"]
            for observation in observations
            if observation["rank"] is not None
        ]

        global_flame_values = [
            observation["global_flame"]
            for observation in observations
            if observation["global_flame"] is not None
        ]

        ranking_summary = {
            "group_type": group_type,
            "observations": len(observations),
            "best_rank": None,
            "worst_rank": None,
            "latest_rank": None,
            "global_flame_min": None,
            "global_flame_max": None,
            "global_flame_latest": None,
        }

        if rank_values:
            ranking_summary["best_rank"] = min(rank_values)
            ranking_summary["worst_rank"] = max(rank_values)
            ranking_summary["latest_rank"] = rank_values[-1]

        if global_flame_values:
            ranking_summary["global_flame_min"] = min(
                global_flame_values
            )
            ranking_summary["global_flame_max"] = max(
                global_flame_values
            )
            ranking_summary["global_flame_latest"] = (
                global_flame_values[-1]
            )

        summary["rankings"].append(
            ranking_summary
        )

    return summary


def print_trend_summary(summary):
    if summary is None:
        return

    print()
    print("=" * 72)
    print("TERRARIUM TREND SUMMARY")
    print("=" * 72)

    print(
        f"Snapshots observed: "
        f"{summary['snapshot_count']}"
    )

    print()
    print("Global Lunium:")

    print(
        f"  Range: "
        f"{summary['global_lunium_min']} "
        f"to {summary['global_lunium_max']}"
    )

    print(
        f"  Latest: "
        f"{summary['global_lunium_latest']}"
    )

    print()
    print("Plot trends:")

    for plot in summary["plots"]:
        plot_name = (
            f"{plot['plot_type']} "
            f"#{plot['plot_number']}"
        )

        print()
        print(
            f"  {plot_name} "
            f"({plot['observations']} observations)"
        )

        print(
            f"    Flame range: "
            f"{plot['flame_min']} "
            f"to {plot['flame_max']}"
        )

        print(
            f"    Latest Flame: "
            f"{plot['flame_latest']}"
        )

        print(
            "    Next-distribution range: "
            f"{format_decimal(
                plot['distribution_min'],
                4,
            )} "
            "to "
            f"{format_decimal(
                plot['distribution_max'],
                4,
            )}"
        )

        print(
            "    Latest next distribution: "
            f"{format_decimal(
                plot['distribution_latest'],
                4,
            )}"
        )

        print(
            "    Latest total acquired bAXS: "
            f"{format_decimal(
                plot['acquired_latest'],
                4,
            )}"
        )

    print()
    print("Ranking trends:")

    for ranking in summary["rankings"]:
        print()
        print(
            f"  {ranking['group_type']} "
            f"({ranking['observations']} observations)"
        )

        print(
            f"    Best rank: "
            f"{ranking['best_rank']}"
        )

        print(
            f"    Worst rank: "
            f"{ranking['worst_rank']}"
        )

        print(
            f"    Latest rank: "
            f"{ranking['latest_rank']}"
        )

        print(
            f"    Global Flame range: "
            f"{ranking['global_flame_min']} "
            f"to {ranking['global_flame_max']}"
        )

        print(
            f"    Latest Global Flame: "
            f"{ranking['global_flame_latest']}"
        )

    print()
    print("Interpretation:")
    print(
        "- These are observation-based ranges, not time-normalized rates."
    )
    print(
        "- Best rank means the lowest numerical rank observed."
    )
    print(
        "- Historical observations are preserved without invented "
        "timestamps."
    )



def calculate_change_summary(snapshots):
    if len(snapshots) < 2:
        return None

    summary = {
        "interval_count": len(snapshots) - 1,
        "global_lunium": {
            "decreased": 0,
            "increased": 0,
            "unchanged": 0,
        },
        "plots": {},
        "rankings": {},
    }

    previous_plots = {}
    previous_rankings = {}

    previous_snapshot = snapshots[0]

    for plot in previous_snapshot["plots"]:
        key = (
            plot["plot_type"],
            plot["plot_number"],
        )
        previous_plots[key] = plot

    for ranking in previous_snapshot["rankings"]:
        previous_rankings[
            ranking["group_type"]
        ] = ranking

    for snapshot in snapshots[1:]:
        current_lunium = snapshot["global_lunium"]
        previous_lunium = previous_snapshot["global_lunium"]

        if (
            current_lunium is not None
            and previous_lunium is not None
        ):
            if current_lunium < previous_lunium:
                summary["global_lunium"]["decreased"] += 1
            elif current_lunium > previous_lunium:
                summary["global_lunium"]["increased"] += 1
            else:
                summary["global_lunium"]["unchanged"] += 1

        for plot in snapshot["plots"]:
            key = (
                plot["plot_type"],
                plot["plot_number"],
            )

            if key not in summary["plots"]:
                summary["plots"][key] = {
                    "distribution_increased": 0,
                    "distribution_decreased": 0,
                    "distribution_unchanged": 0,
                    "acquired_delta_count": 0,
                    "largest_acquired_delta": None,
                    "smallest_acquired_delta": None,
                }

            plot_summary = summary["plots"][key]
            previous_plot = previous_plots.get(key)

            if previous_plot is not None:
                current_distribution = plot["next_distribution"]
                previous_distribution = (
                    previous_plot["next_distribution"]
                )

                if (
                    current_distribution is not None
                    and previous_distribution is not None
                ):
                    if current_distribution > previous_distribution:
                        plot_summary[
                            "distribution_increased"
                        ] += 1
                    elif current_distribution < previous_distribution:
                        plot_summary[
                            "distribution_decreased"
                        ] += 1
                    else:
                        plot_summary[
                            "distribution_unchanged"
                        ] += 1

                current_acquired = plot["total_acquired_baxs"]
                previous_acquired = (
                    previous_plot["total_acquired_baxs"]
                )

                if (
                    current_acquired is not None
                    and previous_acquired is not None
                ):
                    acquired_delta = (
                        current_acquired
                        - previous_acquired
                    )

                    plot_summary[
                        "acquired_delta_count"
                    ] += 1

                    largest = plot_summary[
                        "largest_acquired_delta"
                    ]

                    smallest = plot_summary[
                        "smallest_acquired_delta"
                    ]

                    if (
                        largest is None
                        or acquired_delta > largest
                    ):
                        plot_summary[
                            "largest_acquired_delta"
                        ] = acquired_delta

                    if (
                        smallest is None
                        or acquired_delta < smallest
                    ):
                        plot_summary[
                            "smallest_acquired_delta"
                        ] = acquired_delta

            previous_plots[key] = plot

        for ranking in snapshot["rankings"]:
            group_type = ranking["group_type"]

            if group_type not in summary["rankings"]:
                summary["rankings"][group_type] = {
                    "improved": 0,
                    "worsened": 0,
                    "unchanged": 0,
                }

            ranking_summary = summary["rankings"][
                group_type
            ]

            previous_ranking = previous_rankings.get(
                group_type
            )

            if previous_ranking is not None:
                current_rank = ranking["rank"]
                previous_rank = previous_ranking["rank"]

                if (
                    current_rank is not None
                    and previous_rank is not None
                ):
                    if current_rank < previous_rank:
                        ranking_summary["improved"] += 1
                    elif current_rank > previous_rank:
                        ranking_summary["worsened"] += 1
                    else:
                        ranking_summary["unchanged"] += 1

            previous_rankings[group_type] = ranking

        previous_snapshot = snapshot

    return summary


def print_change_summary(summary):
    if summary is None:
        return

    print()
    print("=" * 72)
    print("OBSERVATION-TO-OBSERVATION CHANGE SUMMARY")
    print("=" * 72)

    print(
        f"Comparable observation intervals: "
        f"{summary['interval_count']}"
    )

    lunium = summary["global_lunium"]

    print()
    print("Global Lunium movement:")
    print(
        f"  Decreased: {lunium['decreased']}"
    )
    print(
        f"  Increased: {lunium['increased']}"
    )
    print(
        f"  Unchanged: {lunium['unchanged']}"
    )

    print()
    print("Plot movement:")

    for key in sorted(summary["plots"]):
        plot_type, plot_number = key
        plot = summary["plots"][key]

        print()
        print(
            f"  {plot_type} #{plot_number}"
        )

        print(
            "    Next distribution:"
        )

        print(
            f"      Increased: "
            f"{plot['distribution_increased']}"
        )

        print(
            f"      Decreased: "
            f"{plot['distribution_decreased']}"
        )

        print(
            f"      Unchanged: "
            f"{plot['distribution_unchanged']}"
        )

        print(
            "    Observed cumulative-bAXS deltas:"
        )

        print(
            f"      Comparable intervals: "
            f"{plot['acquired_delta_count']}"
        )

        print(
            f"      Largest increase: "
            f"{format_decimal(
                plot['largest_acquired_delta'],
                4,
            )}"
        )

        print(
            f"      Smallest increase: "
            f"{format_decimal(
                plot['smallest_acquired_delta'],
                4,
            )}"
        )

    print()
    print("Ranking movement:")

    for group_type in sorted(summary["rankings"]):
        ranking = summary["rankings"][
            group_type
        ]

        print()
        print(f"  {group_type}")

        print(
            f"    Improved: "
            f"{ranking['improved']}"
        )

        print(
            f"    Worsened: "
            f"{ranking['worsened']}"
        )

        print(
            f"    Unchanged: "
            f"{ranking['unchanged']}"
        )

    print()
    print("Interpretation:")
    print(
        "- Each interval is one pair of consecutive stored observations."
    )
    print(
        "- Intervals are not assumed to represent equal amounts of time."
    )
    print(
        "- Lower numerical rank means better competitive position."
    )
    print(
        "- Cumulative-bAXS changes are observational increments, "
        "not hourly or daily yield rates."
    )



def calculate_accumulation_composition(period_summary):
    if period_summary is None:
        return None

    combined_delta = period_summary[
        "combined_acquired_baxs_delta"
    ]

    if combined_delta is None:
        return None

    summary = {
        "combined_delta": combined_delta,
        "plots": [],
        "land_types": {},
    }

    for plot in period_summary["plots"]:
        delta = plot["total_acquired_baxs_delta"]

        if delta is None:
            share_percent = None
        elif combined_delta == ZERO:
            share_percent = None
        else:
            share_percent = (
                delta
                / combined_delta
                * Decimal("100")
            )

        plot_summary = {
            "plot_type": plot["plot_type"],
            "plot_number": plot["plot_number"],
            "delta": delta,
            "share_percent": share_percent,
        }

        summary["plots"].append(
            plot_summary
        )

        plot_type = plot["plot_type"]

        if plot_type not in summary["land_types"]:
            summary["land_types"][plot_type] = ZERO

        if delta is not None:
            summary["land_types"][plot_type] += delta

    land_type_rows = []

    for plot_type in sorted(summary["land_types"]):
        delta = summary["land_types"][plot_type]

        if combined_delta == ZERO:
            share_percent = None
        else:
            share_percent = (
                delta
                / combined_delta
                * Decimal("100")
            )

        land_type_rows.append(
            {
                "plot_type": plot_type,
                "delta": delta,
                "share_percent": share_percent,
            }
        )

    summary["land_types"] = land_type_rows

    return summary


def print_accumulation_composition(summary):
    if summary is None:
        return

    print()
    print("=" * 72)
    print("BAXS ACCUMULATION COMPOSITION")
    print("=" * 72)

    print(
        "Observed cumulative bAXS increase: "
        f"{format_decimal(
            summary['combined_delta'],
            4,
        )}"
    )

    print()
    print("By plot:")

    for plot in summary["plots"]:
        plot_name = (
            f"{plot['plot_type']} "
            f"#{plot['plot_number']}"
        )

        if plot["share_percent"] is None:
            share_text = "UNKNOWN"
        else:
            share_text = (
                f"{plot['share_percent']:.2f}%"
            )

        print(
            f"  {plot_name}: "
            f"{signed_decimal(plot['delta'], 4)} "
            f"({share_text})"
        )

    print()
    print("By land type:")

    for land_type in summary["land_types"]:
        if land_type["share_percent"] is None:
            share_text = "UNKNOWN"
        else:
            share_text = (
                f"{land_type['share_percent']:.2f}%"
            )

        print(
            f"  {land_type['plot_type']}: "
            f"{signed_decimal(
                land_type['delta'],
                4,
            )} "
            f"({share_text})"
        )

    print()
    print("Interpretation:")
    print(
        "- Contribution shares use cumulative total-acquired-bAXS "
        "changes between the first and last stored observations."
    )
    print(
        "- Shares describe the observed accumulation composition only."
    )
    print(
        "- They are not daily yield rates, ROI, or projections."
    )
    print(
        "- Unequal historical observation intervals do not affect "
        "the first-to-last cumulative composition calculation."
    )



def calculate_competitive_flame_share(snapshots):
    if not snapshots:
        return None

    observations = []

    for snapshot in snapshots:
        plot_flame_by_type = {}

        for plot in snapshot["plots"]:
            plot_type = plot["plot_type"]
            flame = plot["flame"]

            if flame is None:
                continue

            if plot_type not in plot_flame_by_type:
                plot_flame_by_type[plot_type] = 0

            plot_flame_by_type[plot_type] += flame

        for ranking in snapshot["rankings"]:
            group_type = ranking["group_type"]
            global_flame = ranking["global_flame"]

            owned_flame = plot_flame_by_type.get(
                group_type
            )

            share_percent = None

            if (
                owned_flame is not None
                and global_flame is not None
                and global_flame != 0
            ):
                share_percent = (
                    Decimal(owned_flame)
                    / Decimal(global_flame)
                    * Decimal("100")
                )

            observations.append(
                {
                    "snapshot_id": snapshot["snapshot_id"],
                    "session_date": snapshot["session_date"],
                    "snapshot_type": snapshot["snapshot_type"],
                    "group_type": group_type,
                    "owned_flame": owned_flame,
                    "global_flame": global_flame,
                    "share_percent": share_percent,
                    "rank": ranking["rank"],
                }
            )

    grouped = {}

    for observation in observations:
        group_type = observation["group_type"]

        if group_type not in grouped:
            grouped[group_type] = []

        grouped[group_type].append(
            observation
        )

    summary = {
        "groups": [],
    }

    for group_type in sorted(grouped):
        group_observations = grouped[group_type]

        share_values = [
            observation["share_percent"]
            for observation in group_observations
            if observation["share_percent"] is not None
        ]

        latest = group_observations[-1]

        summary["groups"].append(
            {
                "group_type": group_type,
                "observations": len(group_observations),
                "share_min": (
                    min(share_values)
                    if share_values
                    else None
                ),
                "share_max": (
                    max(share_values)
                    if share_values
                    else None
                ),
                "share_latest": latest[
                    "share_percent"
                ],
                "owned_flame_latest": latest[
                    "owned_flame"
                ],
                "global_flame_latest": latest[
                    "global_flame"
                ],
                "rank_latest": latest[
                    "rank"
                ],
            }
        )

    return summary


def print_competitive_flame_share(summary):
    if summary is None:
        return

    print()
    print("=" * 72)
    print("COMPETITIVE FLAME SHARE")
    print("=" * 72)

    for group in summary["groups"]:
        print()
        print(
            f"{group['group_type']} "
            f"({group['observations']} observations)"
        )

        print(
            f"  Latest owned Flame: "
            f"{group['owned_flame_latest']}"
        )

        print(
            f"  Latest Global Flame: "
            f"{group['global_flame_latest']}"
        )

        if group["share_latest"] is None:
            latest_share_text = "UNKNOWN"
        else:
            latest_share_text = (
                f"{group['share_latest']:.6f}%"
            )

        print(
            f"  Latest Flame share: "
            f"{latest_share_text}"
        )

        if (
            group["share_min"] is None
            or group["share_max"] is None
        ):
            range_text = "UNKNOWN"
        else:
            range_text = (
                f"{group['share_min']:.6f}% "
                f"to "
                f"{group['share_max']:.6f}%"
            )

        print(
            f"  Observed Flame-share range: "
            f"{range_text}"
        )

        print(
            f"  Latest rank: "
            f"{group['rank_latest']}"
        )

    print()
    print("Interpretation:")
    print(
        "- Flame share is owned group Flame divided by recorded "
        "Global Flame for the same group."
    )
    print(
        "- Savannah owned Flame combines Savannah #1 and Savannah #2."
    )
    print(
        "- Higher Flame share means a larger share of the recorded "
        "competitive Flame pool."
    )
    print(
        "- This metric does not imply a direct bAXS payout formula."
    )



def calculate_distribution_composition(snapshots):
    if not snapshots:
        return None

    combined_observations = []

    for snapshot in snapshots:
        distributions = [
            plot["next_distribution"]
            for plot in snapshot["plots"]
        ]

        if (
            distributions
            and all(
                value is not None
                for value in distributions
            )
        ):
            combined_observations.append(
                sum(distributions, ZERO)
            )

    latest_snapshot = snapshots[-1]

    latest_plots = []

    latest_combined = ZERO
    latest_complete = True

    for plot in latest_snapshot["plots"]:
        distribution = plot["next_distribution"]

        if distribution is None:
            latest_complete = False
        else:
            latest_combined += distribution

        latest_plots.append(
            {
                "plot_type": plot["plot_type"],
                "plot_number": plot["plot_number"],
                "next_distribution": distribution,
            }
        )

    if not latest_complete:
        latest_combined = None

    land_type_totals = {}

    for plot in latest_plots:
        plot_type = plot["plot_type"]
        value = plot["next_distribution"]

        if plot_type not in land_type_totals:
            land_type_totals[plot_type] = ZERO

        if value is not None:
            land_type_totals[plot_type] += value

    for plot in latest_plots:
        value = plot["next_distribution"]

        if (
            value is None
            or latest_combined is None
            or latest_combined == ZERO
        ):
            share_percent = None
        else:
            share_percent = (
                value
                / latest_combined
                * Decimal("100")
            )

        plot["share_percent"] = share_percent

    land_types = []

    for plot_type in sorted(land_type_totals):
        value = land_type_totals[plot_type]

        if (
            latest_combined is None
            or latest_combined == ZERO
        ):
            share_percent = None
        else:
            share_percent = (
                value
                / latest_combined
                * Decimal("100")
            )

        land_types.append(
            {
                "plot_type": plot_type,
                "next_distribution": value,
                "share_percent": share_percent,
            }
        )

    return {
        "observations": len(combined_observations),
        "combined_min": (
            min(combined_observations)
            if combined_observations
            else None
        ),
        "combined_max": (
            max(combined_observations)
            if combined_observations
            else None
        ),
        "latest_combined": latest_combined,
        "latest_date": latest_snapshot["session_date"],
        "latest_snapshot_type": latest_snapshot["snapshot_type"],
        "plots": latest_plots,
        "land_types": land_types,
    }


def print_distribution_composition(summary):
    if summary is None:
        return

    print()
    print("=" * 72)
    print("NEXT-DISTRIBUTION COMPOSITION")
    print("=" * 72)

    print(
        f"Complete observations: "
        f"{summary['observations']}"
    )

    print(
        f"Latest observation: "
        f"{summary['latest_date']} "
        f"({summary['latest_snapshot_type']})"
    )

    print(
        "Observed combined range: "
        f"{format_decimal(summary['combined_min'], 4)} "
        "to "
        f"{format_decimal(summary['combined_max'], 4)} "
        "bAXS"
    )

    print(
        "Latest combined next distribution: "
        f"{format_decimal(
            summary['latest_combined'],
            4,
        )} bAXS"
    )

    print()
    print("Latest composition by plot:")

    for plot in summary["plots"]:
        plot_name = (
            f"{plot['plot_type']} "
            f"#{plot['plot_number']}"
        )

        if plot["share_percent"] is None:
            share_text = "UNKNOWN"
        else:
            share_text = (
                f"{plot['share_percent']:.2f}%"
            )

        print(
            f"  {plot_name}: "
            f"{format_decimal(
                plot['next_distribution'],
                4,
            )} bAXS "
            f"({share_text})"
        )

    print()
    print("Latest composition by land type:")

    for land_type in summary["land_types"]:
        if land_type["share_percent"] is None:
            share_text = "UNKNOWN"
        else:
            share_text = (
                f"{land_type['share_percent']:.2f}%"
            )

        print(
            f"  {land_type['plot_type']}: "
            f"{format_decimal(
                land_type['next_distribution'],
                4,
            )} bAXS "
            f"({share_text})"
        )

    print()
    print("Interpretation:")
    print(
        "- Values are the game's stored Next Distribution estimates."
    )
    print(
        "- Composition shows how the latest combined estimate is "
        "distributed across owned plots."
    )
    print(
        "- This is not a realized-yield calculation."
    )
    print(
        "- No hourly, daily, projected, or ROI values are inferred."
    )



def calculate_distribution_mix_comparison(
    accumulation_summary,
    distribution_summary,
):
    if (
        accumulation_summary is None
        or distribution_summary is None
    ):
        return None

    accumulation_by_plot = {
        (
            row["plot_type"],
            row["plot_number"],
        ): row
        for row in accumulation_summary["plots"]
    }

    distribution_by_plot = {
        (
            row["plot_type"],
            row["plot_number"],
        ): row
        for row in distribution_summary["plots"]
    }

    plot_rows = []

    for key in sorted(distribution_by_plot):
        distribution_row = distribution_by_plot[key]
        accumulation_row = accumulation_by_plot.get(key)

        accumulation_share = (
            accumulation_row["share_percent"]
            if accumulation_row is not None
            else None
        )

        distribution_share = distribution_row[
            "share_percent"
        ]

        if (
            accumulation_share is None
            or distribution_share is None
        ):
            difference_pp = None
        else:
            difference_pp = (
                distribution_share
                - accumulation_share
            )

        plot_rows.append(
            {
                "plot_type": key[0],
                "plot_number": key[1],
                "accumulation_share": accumulation_share,
                "distribution_share": distribution_share,
                "difference_pp": difference_pp,
            }
        )

    accumulation_by_type = {
        row["plot_type"]: row
        for row in accumulation_summary["land_types"]
    }

    distribution_by_type = {
        row["plot_type"]: row
        for row in distribution_summary["land_types"]
    }

    land_type_rows = []

    for plot_type in sorted(distribution_by_type):
        distribution_row = distribution_by_type[
            plot_type
        ]

        accumulation_row = accumulation_by_type.get(
            plot_type
        )

        accumulation_share = (
            accumulation_row["share_percent"]
            if accumulation_row is not None
            else None
        )

        distribution_share = distribution_row[
            "share_percent"
        ]

        if (
            accumulation_share is None
            or distribution_share is None
        ):
            difference_pp = None
        else:
            difference_pp = (
                distribution_share
                - accumulation_share
            )

        land_type_rows.append(
            {
                "plot_type": plot_type,
                "accumulation_share": accumulation_share,
                "distribution_share": distribution_share,
                "difference_pp": difference_pp,
            }
        )

    return {
        "latest_date": distribution_summary["latest_date"],
        "latest_snapshot_type": (
            distribution_summary["latest_snapshot_type"]
        ),
        "plots": plot_rows,
        "land_types": land_type_rows,
    }


def print_distribution_mix_comparison(summary):
    if summary is None:
        return

    print()
    print("=" * 72)
    print("DISTRIBUTION MIX VS HISTORICAL ACCUMULATION")
    print("=" * 72)

    print(
        f"Latest distribution observation: "
        f"{summary['latest_date']} "
        f"({summary['latest_snapshot_type']})"
    )

    print()
    print("By plot:")

    for row in summary["plots"]:
        plot_name = (
            f"{row['plot_type']} "
            f"#{row['plot_number']}"
        )

        if row["accumulation_share"] is None:
            accumulation_text = "UNKNOWN"
        else:
            accumulation_text = (
                f"{row['accumulation_share']:.2f}%"
            )

        if row["distribution_share"] is None:
            distribution_text = "UNKNOWN"
        else:
            distribution_text = (
                f"{row['distribution_share']:.2f}%"
            )

        if row["difference_pp"] is None:
            difference_text = "UNKNOWN"
        else:
            difference_text = (
                f"{row['difference_pp']:+.2f} pp"
            )

        print(
            f"  {plot_name}: "
            f"historical {accumulation_text}, "
            f"latest distribution {distribution_text}, "
            f"difference {difference_text}"
        )

    print()
    print("By land type:")

    for row in summary["land_types"]:
        if row["accumulation_share"] is None:
            accumulation_text = "UNKNOWN"
        else:
            accumulation_text = (
                f"{row['accumulation_share']:.2f}%"
            )

        if row["distribution_share"] is None:
            distribution_text = "UNKNOWN"
        else:
            distribution_text = (
                f"{row['distribution_share']:.2f}%"
            )

        if row["difference_pp"] is None:
            difference_text = "UNKNOWN"
        else:
            difference_text = (
                f"{row['difference_pp']:+.2f} pp"
            )

        print(
            f"  {row['plot_type']}: "
            f"historical {accumulation_text}, "
            f"latest distribution {distribution_text}, "
            f"difference {difference_text}"
        )

    print()
    print("Interpretation:")
    print(
        "- Historical shares use first-to-last cumulative "
        "total-acquired-bAXS change."
    )
    print(
        "- Latest distribution shares use the game's latest stored "
        "Next Distribution estimate."
    )
    print(
        "- Difference is expressed in percentage points."
    )
    print(
        "- Similar shares indicate similar composition, not proof of "
        "a payout formula."
    )



def calculate_evidence_aware_change_summary(observations):
    """
    Summarize metric-aware changes across canonical and evidence records.

    A comparison is:
    - adjacent when no stored observation was skipped for that metric
    - bridged when one or more intervening observations lacked that metric

    Bridged comparisons remain valid observed changes, but they must not be
    described as ordinary adjacent-observation intervals.
    """

    def summarize_deltas(items, direction_mode="normal"):
        comparable = [
            item
            for item in items
            if item["delta"] is not None
        ]

        adjacent = [
            item
            for item in comparable
            if item["skipped"] == 0
        ]

        bridged = [
            item
            for item in comparable
            if (
                item["skipped"] is not None
                and item["skipped"] > 0
            )
        ]

        increased = 0
        decreased = 0
        unchanged = 0

        improved = 0
        worsened = 0

        for item in comparable:
            delta = item["delta"]

            if direction_mode == "rank":
                if delta < 0:
                    improved += 1
                elif delta > 0:
                    worsened += 1
                else:
                    unchanged += 1
            else:
                if delta > 0:
                    increased += 1
                elif delta < 0:
                    decreased += 1
                else:
                    unchanged += 1

        deltas = [
            item["delta"]
            for item in comparable
        ]

        return {
            "comparable_count": len(comparable),
            "adjacent_count": len(adjacent),
            "bridged_count": len(bridged),
            "increased": increased,
            "decreased": decreased,
            "unchanged": unchanged,
            "improved": improved,
            "worsened": worsened,
            "largest_delta": (
                max(deltas)
                if deltas
                else None
            ),
            "smallest_delta": (
                min(deltas)
                if deltas
                else None
            ),
            "largest_bridge": (
                max(
                    (
                        item["skipped"]
                        for item in bridged
                    ),
                    default=0,
                )
            ),
        }

    global_lunium_items = []
    claimable_items = []

    plot_items = {}
    ranking_items = {}

    for observation in observations:
        global_lunium_items.append(
            {
                "delta": observation.get(
                    "global_lunium_delta"
                ),
                "skipped": observation.get(
                    "global_lunium_delta_skipped_observations"
                ),
            }
        )

        claimable_items.append(
            {
                "delta": observation.get(
                    "claimable_baxs_delta"
                ),
                "skipped": observation.get(
                    "claimable_baxs_delta_skipped_observations"
                ),
            }
        )

        for plot in observation["plots"]:
            key = (
                plot["plot_type"],
                plot["plot_number"],
            )

            if key not in plot_items:
                plot_items[key] = {
                    "flame": [],
                    "next_distribution": [],
                    "total_acquired_baxs": [],
                }

            for metric_name in (
                "flame",
                "next_distribution",
                "total_acquired_baxs",
            ):
                plot_items[key][
                    metric_name
                ].append(
                    {
                        "delta": plot.get(
                            f"{metric_name}_delta"
                        ),
                        "skipped": plot.get(
                            f"{metric_name}_delta_"
                            "skipped_observations"
                        ),
                    }
                )

        for ranking in observation["rankings"]:
            group_type = ranking[
                "group_type"
            ]

            if group_type not in ranking_items:
                ranking_items[
                    group_type
                ] = {
                    "rank": [],
                    "global_flame": [],
                }

            for metric_name in (
                "rank",
                "global_flame",
            ):
                ranking_items[
                    group_type
                ][metric_name].append(
                    {
                        "delta": ranking.get(
                            f"{metric_name}_delta"
                        ),
                        "skipped": ranking.get(
                            f"{metric_name}_delta_"
                            "skipped_observations"
                        ),
                    }
                )

    plot_summaries = []

    for key in sorted(
        plot_items,
        key=lambda item: (
            1
            if item[0] == "Forest"
            else 2
            if item[0] == "Savannah"
            else 99,
            item[0],
            item[1],
        ),
    ):
        plot_type, plot_number = key

        plot_summaries.append(
            {
                "plot_type": plot_type,
                "plot_number": plot_number,
                "flame": summarize_deltas(
                    plot_items[key]["flame"]
                ),
                "next_distribution": (
                    summarize_deltas(
                        plot_items[key][
                            "next_distribution"
                        ]
                    )
                ),
                "total_acquired_baxs": (
                    summarize_deltas(
                        plot_items[key][
                            "total_acquired_baxs"
                        ]
                    )
                ),
            }
        )

    ranking_summaries = []

    for group_type in sorted(
        ranking_items,
        key=lambda item: (
            1
            if item == "Forest"
            else 2
            if item == "Savannah"
            else 99,
            item,
        ),
    ):
        ranking_summaries.append(
            {
                "group_type": group_type,
                "rank": summarize_deltas(
                    ranking_items[
                        group_type
                    ]["rank"],
                    direction_mode="rank",
                ),
                "global_flame": (
                    summarize_deltas(
                        ranking_items[
                            group_type
                        ]["global_flame"]
                    )
                ),
            }
        )

    return {
        "observation_count": len(
            observations
        ),
        "global_lunium": summarize_deltas(
            global_lunium_items
        ),
        "claimable_baxs": summarize_deltas(
            claimable_items
        ),
        "plots": plot_summaries,
        "rankings": ranking_summaries,
    }



def print_evidence_aware_change_summary(summary):
    """
    Print metric-aware change coverage for canonical plus evidence records.

    Adjacent comparisons use the immediately preceding stored observation
    for that metric.

    Bridged comparisons skip one or more intervening observations where the
    metric was not present and compare against the last known prior value.
    """

    print()
    print("=" * 72)
    print("EVIDENCE-AWARE OBSERVATION CHANGE SUMMARY")
    print("=" * 72)

    print()
    print(
        f"Observations considered: "
        f"{summary['observation_count']}"
    )

    print()
    print("Top-level metrics:")

    global_lunium = summary[
        "global_lunium"
    ]

    print(
        "  Global Lunium comparisons: "
        f"{global_lunium['comparable_count']} "
        f"(adjacent {global_lunium['adjacent_count']}, "
        f"bridged {global_lunium['bridged_count']})"
    )

    print(
        "    Movement: "
        f"decreased {global_lunium['decreased']}, "
        f"increased {global_lunium['increased']}, "
        f"unchanged {global_lunium['unchanged']}"
    )

    claimable = summary[
        "claimable_baxs"
    ]

    print(
        "  Claimable bAXS comparisons: "
        f"{claimable['comparable_count']} "
        f"(adjacent {claimable['adjacent_count']}, "
        f"bridged {claimable['bridged_count']})"
    )

    print(
        "    Movement: "
        f"increased {claimable['increased']}, "
        f"decreased {claimable['decreased']}, "
        f"unchanged {claimable['unchanged']}"
    )

    print()
    print("Plot metrics:")

    for plot in summary["plots"]:
        print()
        print(
            f"  {plot['plot_type']} "
            f"#{plot['plot_number']}"
        )

        flame = plot["flame"]

        print(
            "    Flame comparisons: "
            f"{flame['comparable_count']} "
            f"(adjacent {flame['adjacent_count']}, "
            f"bridged {flame['bridged_count']})"
        )

        next_distribution = plot[
            "next_distribution"
        ]

        print(
            "    Next Distribution comparisons: "
            f"{next_distribution['comparable_count']} "
            f"(adjacent "
            f"{next_distribution['adjacent_count']}, "
            f"bridged "
            f"{next_distribution['bridged_count']})"
        )

        print(
            "      Movement: "
            f"increased "
            f"{next_distribution['increased']}, "
            f"decreased "
            f"{next_distribution['decreased']}, "
            f"unchanged "
            f"{next_distribution['unchanged']}"
        )

        total = plot[
            "total_acquired_baxs"
        ]

        print(
            "    Total-acquired bAXS comparisons: "
            f"{total['comparable_count']} "
            f"(adjacent {total['adjacent_count']}, "
            f"bridged {total['bridged_count']})"
        )

        print(
            "      Largest observed increase: "
            f"{format_decimal(total['largest_delta'], 4)}"
        )

        print(
            "      Smallest observed increase: "
            f"{format_decimal(total['smallest_delta'], 4)}"
        )

        print(
            "      Largest bridge: "
            f"{total['largest_bridge']} "
            f"skipped observation(s)"
        )

    print()
    print("Ranking metrics:")

    for ranking in summary["rankings"]:
        print()
        print(
            f"  {ranking['group_type']}"
        )

        rank = ranking["rank"]

        print(
            "    Rank comparisons: "
            f"{rank['comparable_count']} "
            f"(adjacent {rank['adjacent_count']}, "
            f"bridged {rank['bridged_count']})"
        )

        print(
            "      Improved: "
            f"{rank['improved']}"
        )

        print(
            "      Worsened: "
            f"{rank['worsened']}"
        )

        print(
            "      Unchanged: "
            f"{rank['unchanged']}"
        )

        global_flame = ranking[
            "global_flame"
        ]

        print(
            "    Global Flame comparisons: "
            f"{global_flame['comparable_count']} "
            f"(adjacent "
            f"{global_flame['adjacent_count']}, "
            f"bridged "
            f"{global_flame['bridged_count']})"
        )

    print()
    print("Interpretation:")
    print(
        "- Comparison counts are metric-specific."
    )
    print(
        "- Adjacent means the metric was present in the immediately "
        "preceding stored observation."
    )
    print(
        "- Bridged means one or more intervening stored observations "
        "did not contain that metric."
    )
    print(
        "- Bridged changes remain observed first-to-next-known changes; "
        "they are not reconstructed intermediate values."
    )
    print(
        "- A bridged comparison does not imply equal time intervals "
        "between observations."
    )
    print(
        "- Negative claimable-bAXS movement may represent a claim/reset "
        "and is not interpreted as negative Terrarium yield."
    )




def print_evidence_aware_summary(summary):
    """
    Print the evidence-aware Terrarium analytical view.

    This report keeps canonical and partial evidence provenance visible and
    reports metric-specific coverage without filling missing observations.
    """

    print()
    print("=" * 72)
    print("AXIEOS V0.11 — TERRARIUM EVIDENCE-AWARE SUMMARY")
    print("=" * 72)

    print()
    print("Coverage:")
    print(
        f"  Total observations: "
        f"{summary['observation_count']}"
    )
    print(
        f"  Canonical observations: "
        f"{summary['canonical_count']}"
    )
    print(
        f"  Partial evidence observations: "
        f"{summary['evidence_count']}"
    )
    print(
        f"  Represented calendar days: "
        f"{summary['represented_day_count']}"
    )

    if summary["represented_dates"]:
        print(
            f"  Observed range: "
            f"{summary['represented_dates'][0]} "
            f"to "
            f"{summary['represented_dates'][-1]}"
        )

    print()
    print("Latest known top-level metrics:")

    global_lunium = summary[
        "global_lunium"
    ]

    print(
        "  Global Lunium: "
        f"{global_lunium['latest_value']} "
        f"({global_lunium['latest_date']} "
        f"{global_lunium['latest_snapshot_type']}, "
        f"{global_lunium['latest_record_source']})"
    )

    claimable = summary[
        "claimable_baxs"
    ]

    print(
        "  Claimable bAXS: "
        f"{format_decimal(claimable['latest_value'])} "
        f"({claimable['latest_date']} "
        f"{claimable['latest_snapshot_type']}, "
        f"{claimable['latest_record_source']})"
    )

    print()
    print("Metric-specific plot coverage:")

    for plot in summary["plots"]:
        flame = plot["flame"]
        next_distribution = plot[
            "next_distribution"
        ]
        total = plot[
            "total_acquired_baxs"
        ]

        print()
        print(
            f"  {plot['plot_type']} "
            f"#{plot['plot_number']}"
        )

        print(
            f"    Plot rows observed: "
            f"{plot['row_observation_count']}"
        )

        print(
            f"    Flame observations: "
            f"{flame['observation_count']}"
        )

        print(
            f"      Latest: "
            f"{flame['latest_value']} "
            f"({flame['latest_date']}, "
            f"{flame['latest_record_source']})"
        )

        print(
            f"    Next Distribution observations: "
            f"{next_distribution['observation_count']}"
        )

        print(
            f"      Latest: "
            f"{format_decimal(next_distribution['latest_value'])} "
            f"({next_distribution['latest_date']}, "
            f"{next_distribution['latest_record_source']})"
        )

        print(
            f"    Total-acquired-bAXS observations: "
            f"{total['observation_count']}"
        )

        print(
            f"      Latest: "
            f"{format_decimal(total['latest_value'])} "
            f"({total['latest_date']}, "
            f"{total['latest_record_source']})"
        )

    print()
    print("Metric-specific ranking coverage:")

    for ranking in summary["rankings"]:
        rank = ranking["rank"]
        global_flame = ranking[
            "global_flame"
        ]

        print()
        print(
            f"  {ranking['group_type']}"
        )

        print(
            f"    Ranking rows observed: "
            f"{ranking['row_observation_count']}"
        )

        print(
            f"    Rank observations: "
            f"{rank['observation_count']}"
        )

        print(
            f"      Latest rank: "
            f"{rank['latest_value']} "
            f"({rank['latest_date']}, "
            f"{rank['latest_record_source']})"
        )

        print(
            f"    Global Flame observations: "
            f"{global_flame['observation_count']}"
        )

        print(
            f"      Latest Global Flame: "
            f"{global_flame['latest_value']} "
            f"({global_flame['latest_date']}, "
            f"{global_flame['latest_record_source']})"
        )

    print()
    print("Evidence-aware cumulative bAXS movement:")

    for row in summary[
        "accumulation"
    ]["plots"]:
        print(
            f"  {row['plot_type']} "
            f"#{row['plot_number']}: "
            f"{format_decimal(row['first_value'])} "
            f"({row['first_date']}) -> "
            f"{format_decimal(row['latest_value'])} "
            f"({row['latest_date']}) "
            f"({signed_decimal(row['delta'], 4)})"
        )

    combined_accumulation = summary[
        "accumulation"
    ]["combined_delta"]

    print(
        "  Combined observed increase: "
        f"{signed_decimal(combined_accumulation, 4)}"
    )

    distribution = summary[
        "latest_complete_distribution"
    ]

    print()
    print("Latest complete Next Distribution observation:")

    if distribution is None:
        print(
            "  No observation contains all required "
            "Next Distribution metrics."
        )
    else:
        print(
            f"  Date: "
            f"{distribution['session_date']}"
        )
        print(
            f"  Snapshot type: "
            f"{distribution['snapshot_type']}"
        )
        print(
            f"  Source: "
            f"{distribution['record_source']}"
        )

        for row in distribution["plots"]:
            print(
                f"  {row['plot_type']} "
                f"#{row['plot_number']}: "
                f"{format_decimal(row['value'])}"
            )

        print(
            "  Combined: "
            f"{format_decimal(distribution['combined'])}"
        )

    print()
    print("Interpretation:")
    print(
        "- Canonical snapshots and partial evidence remain "
        "separate source classes."
    )
    print(
        "- Missing metrics are skipped, not inferred or filled."
    )
    print(
        "- Observation counts are metric-specific because partial "
        "records do not always contain every Terrarium value."
    )
    print(
        "- First-to-latest cumulative bAXS movement is observational "
        "and is not converted into hourly or daily yield."
    )
    print(
        "- Latest known values may come from different dates when "
        "later partial observations omit a metric."
    )




def main():
    parser = argparse.ArgumentParser(
        description=(
            "Read-only historical Terrarium summary for AxieOS V0.11."
        )
    )

    parser.add_argument(
        "--player",
        default="primary",
        help="Gameplay player_id to report. Default: primary",
    )

    parser.add_argument(
        "--evidence-aware",
        action="store_true",
        help=(
            "Include canonical snapshots plus partial Terrarium evidence "
            "using metric-specific evidence-aware analytics."
        ),
    )

    args = parser.parse_args()

    conn = connect_database()
    conn.row_factory = sqlite3.Row

    try:
        if args.evidence_aware:
            observations = load_evidence_aware_snapshots(
                conn,
                args.player,
            )

            add_evidence_aware_history_deltas(
                observations
            )

            evidence_summary = (
                calculate_evidence_aware_summary(
                    observations
                )
            )

            print_evidence_aware_summary(
                evidence_summary
            )

            evidence_change_summary = (
                calculate_evidence_aware_change_summary(
                    observations
                )
            )

            print_evidence_aware_change_summary(
                evidence_change_summary
            )

            return

        snapshots = load_snapshots(
            conn,
            args.player,
        )

        add_history_deltas(snapshots)

        print_summary(
            snapshots,
            args.player,
        )

        period_summary = calculate_period_summary(
            snapshots,
        )

        print_period_summary(
            period_summary,
        )

        validation = validate_history(
            snapshots,
        )

        print_history_validation(
            validation,
        )

        trend_summary = calculate_trend_summary(
            snapshots,
        )

        print_trend_summary(
            trend_summary,
        )

        change_summary = calculate_change_summary(
            snapshots,
        )

        print_change_summary(
            change_summary,
        )

        accumulation_summary = (
            calculate_accumulation_composition(
                period_summary,
            )
        )

        print_accumulation_composition(
            accumulation_summary,
        )

        competitive_summary = (
            calculate_competitive_flame_share(
                snapshots,
            )
        )

        print_competitive_flame_share(
            competitive_summary,
        )

        distribution_summary = (
            calculate_distribution_composition(
                snapshots,
            )
        )

        print_distribution_composition(
            distribution_summary,
        )

        distribution_mix_comparison = (
            calculate_distribution_mix_comparison(
                accumulation_summary,
                distribution_summary,
            )
        )

        print_distribution_mix_comparison(
            distribution_mix_comparison,
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()
