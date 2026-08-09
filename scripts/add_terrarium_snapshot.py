import argparse

from database import connect_database


def get_daily_session_id(conn, session_date, player_id):
    row = conn.execute(
        """
        SELECT id
        FROM gameplay_daily_sessions
        WHERE session_date = ?
          AND player_id = ?
        """,
        (session_date, player_id),
    ).fetchone()

    if row is None:
        raise ValueError(
            f"No gameplay session found for {session_date}. "
            "Create the daily session first."
        )

    return row[0]


def save_snapshot(args):
    conn = connect_database()

    daily_session_id = get_daily_session_id(
        conn,
        args.date,
        args.player,
    )

    # Reuse an existing snapshot of the same type for the day.
    existing = conn.execute(
        """
        SELECT id
        FROM terrarium_snapshots
        WHERE daily_session_id = ?
          AND snapshot_type = ?
        ORDER BY id
        LIMIT 1
        """,
        (
            daily_session_id,
            args.snapshot_type,
        ),
    ).fetchone()

    if existing:
        snapshot_id = existing[0]

        conn.execute(
            """
            UPDATE terrarium_snapshots
            SET
                snapshot_datetime = ?,
                global_lunium = ?,
                claimable_baxs = ?,
                buff_active = ?,
                buff_activation_time = ?,
                estimated_unbuffed_hours = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                args.snapshot_datetime,
                args.global_lunium,
                args.claimable_baxs,
                int(not args.buff_inactive),
                args.buff_activation_time,
                args.unbuffed_hours,
                args.notes,
                snapshot_id,
            ),
        )
    else:
        cursor = conn.execute(
            """
            INSERT INTO terrarium_snapshots (
                daily_session_id,
                snapshot_datetime,
                snapshot_type,
                global_lunium,
                claimable_baxs,
                buff_active,
                buff_activation_time,
                estimated_unbuffed_hours,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                daily_session_id,
                args.snapshot_datetime,
                args.snapshot_type,
                args.global_lunium,
                args.claimable_baxs,
                int(not args.buff_inactive),
                args.buff_activation_time,
                args.unbuffed_hours,
                args.notes,
            ),
        )

        snapshot_id = cursor.lastrowid

    plots = [
        (
            snapshot_id,
            "Forest",
            1,
            args.forest_flame,
            args.forest_next,
            args.forest_acquired,
        ),
        (
            snapshot_id,
            "Savannah",
            1,
            args.savannah1_flame,
            args.savannah1_next,
            args.savannah1_acquired,
        ),
        (
            snapshot_id,
            "Savannah",
            2,
            args.savannah2_flame,
            args.savannah2_next,
            args.savannah2_acquired,
        ),
    ]

    conn.executemany(
        """
        INSERT INTO terrarium_plot_snapshots (
            terrarium_snapshot_id,
            plot_type,
            plot_number,
            flame,
            next_distribution,
            total_acquired_baxs
        )
        VALUES (?, ?, ?, ?, ?, ?)

        ON CONFLICT(
            terrarium_snapshot_id,
            plot_type,
            plot_number
        )
        DO UPDATE SET
            flame = excluded.flame,
            next_distribution = excluded.next_distribution,
            total_acquired_baxs = excluded.total_acquired_baxs
        """,
        plots,
    )

    rankings = [
        (
            snapshot_id,
            "Forest",
            args.forest_rank,
            args.forest_global_flame,
        ),
        (
            snapshot_id,
            "Savannah",
            args.savannah_rank,
            args.savannah_global_flame,
        ),
    ]

    conn.executemany(
        """
        INSERT INTO terrarium_group_rankings (
            terrarium_snapshot_id,
            group_type,
            rank,
            global_flame
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(
            terrarium_snapshot_id,
            group_type
        )
        DO UPDATE SET
            rank = excluded.rank,
            global_flame = excluded.global_flame
        """,
        rankings,
    )

    conn.commit()

    print("Terrarium snapshot saved.")
    print("Snapshot ID:", snapshot_id)

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Add or update an AxieOS Terrarium snapshot."
    )

    parser.add_argument("date")
    parser.add_argument(
        "--type",
        dest="snapshot_type",
        required=True,
    )

    parser.add_argument("--player", default="primary")
    parser.add_argument("--datetime", dest="snapshot_datetime")
    parser.add_argument("--global-lunium", type=int, required=True)
    parser.add_argument("--claimable-baxs", required=True)

    parser.add_argument(
        "--buff-inactive",
        action="store_true",
    )
    parser.add_argument("--buff-activation-time")
    parser.add_argument("--unbuffed-hours", default="0")
    parser.add_argument("--notes", default="")

    parser.add_argument("--forest-flame", type=int, required=True)
    parser.add_argument("--forest-next", required=True)
    parser.add_argument("--forest-acquired", required=True)
    parser.add_argument("--forest-rank", type=int, required=True)
    parser.add_argument("--forest-global-flame", type=int, required=True)

    parser.add_argument("--savannah1-flame", type=int, required=True)
    parser.add_argument("--savannah1-next", required=True)
    parser.add_argument("--savannah1-acquired", required=True)

    parser.add_argument("--savannah2-flame", type=int, required=True)
    parser.add_argument("--savannah2-next", required=True)
    parser.add_argument("--savannah2-acquired", required=True)

    parser.add_argument("--savannah-rank", type=int, required=True)
    parser.add_argument("--savannah-global-flame", type=int, required=True)

    args = parser.parse_args()

    if args.snapshot_datetime is None:
        args.snapshot_datetime = args.date

    save_snapshot(args)


if __name__ == "__main__":
    main()