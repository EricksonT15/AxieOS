import argparse

from database import connect_database


def upsert_daily_session(
    session_date,
    player_id,
    shrine_streak,
    starting_slips,
    claimed_slips,
    ending_slips,
    notes,
):
    conn = connect_database()

    conn.execute(
        """
        INSERT INTO gameplay_daily_sessions (
            session_date,
            player_id,
            shrine_streak,
            starting_fortune_slips,
            claimed_fortune_slips,
            ending_fortune_slips,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(session_date, player_id)
        DO UPDATE SET
            shrine_streak = excluded.shrine_streak,
            starting_fortune_slips = excluded.starting_fortune_slips,
            claimed_fortune_slips = excluded.claimed_fortune_slips,
            ending_fortune_slips = excluded.ending_fortune_slips,
            notes = excluded.notes,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            session_date,
            player_id,
            shrine_streak,
            starting_slips,
            claimed_slips,
            ending_slips,
            notes,
        ),
    )

    conn.commit()

    row = conn.execute(
        """
        SELECT
            id,
            session_date,
            shrine_streak,
            starting_fortune_slips,
            claimed_fortune_slips,
            ending_fortune_slips
        FROM gameplay_daily_sessions
        WHERE session_date = ?
          AND player_id = ?
        """,
        (session_date, player_id),
    ).fetchone()

    conn.close()

    return row


def main():
    parser = argparse.ArgumentParser(
        description="Add or update an AxieOS daily gameplay session."
    )

    parser.add_argument("date")
    parser.add_argument("--player", default="primary")
    parser.add_argument("--streak", type=int)
    parser.add_argument("--starting-slips", type=int)
    parser.add_argument("--claimed-slips", type=int, default=0)
    parser.add_argument("--ending-slips", type=int)
    parser.add_argument("--notes", default="")

    args = parser.parse_args()

    row = upsert_daily_session(
        args.date,
        args.player,
        args.streak,
        args.starting_slips,
        args.claimed_slips,
        args.ending_slips,
        args.notes,
    )

    print("Daily gameplay session saved.")
    print(row)


if __name__ == "__main__":
    main()