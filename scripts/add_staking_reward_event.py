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


def get_final_bounty_task_id(
    conn,
    daily_session_id,
    task_slot,
):
    row = conn.execute(
        """
        SELECT id
        FROM bounty_board_tasks
        WHERE daily_session_id = ?
          AND task_slot = ?
          AND selected_final = 1
        """,
        (
            daily_session_id,
            task_slot,
        ),
    ).fetchone()

    if row is None:
        raise ValueError(
            f"No final Bounty task found for slot {task_slot}."
        )

    return row[0]



def add_staking_reward_event(
    conn,
    daily_session_id,
    event_datetime,
    event_type,
    source,
    token,
    amount,
    related_bounty_task_id=None,
    notes=None,
):
    cursor = conn.execute(
        """
        INSERT INTO staking_reward_events (
            daily_session_id,
            event_datetime,
            event_type,
            source,
            token,
            amount,
            related_bounty_task_id,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            daily_session_id,
            event_datetime,
            event_type,
            source,
            token,
            amount,
            related_bounty_task_id,
            notes,
        ),
    )

    conn.commit()

    return cursor.lastrowid



def main():
    parser = argparse.ArgumentParser(
        description="Add an AxieOS staking or reward event."
    )

    parser.add_argument(
        "date",
        help="Gameplay date in YYYY-MM-DD format.",
    )

    parser.add_argument(
        "--player",
        default="primary",
        help="Player ID. Default: primary",
    )

    parser.add_argument(
        "--datetime",
        required=True,
        help="Event date/time, for example 2026-08-08 11:37.",
    )

    parser.add_argument(
        "--event-type",
        required=True,
        help="Event type, for example claim, stake, unstake, or restake.",
    )

    parser.add_argument(
        "--source",
        required=True,
        help="Source, for example Bounty, Terrariums, Staking, or Ascension.",
    )

    parser.add_argument(
        "--token",
        required=True,
        help="Token symbol, for example bAXS or AXS.",
    )

    parser.add_argument(
        "--amount",
        required=True,
        help="Token amount, stored as text for precision.",
    )

    parser.add_argument(
        "--notes",
        default=None,
        help="Optional notes.",
    )

    parser.add_argument(
        "--bounty-task",
        type=int,
        default=None,
        help="Optional final Bounty task slot linked to this event.",
    )


    args = parser.parse_args()

    conn = connect_database()

    daily_session_id = get_daily_session_id(
        conn,
        args.date,
        args.player,
    )

    related_bounty_task_id = None

    if args.bounty_task is not None:
        related_bounty_task_id = get_final_bounty_task_id(
            conn,
            daily_session_id,
            args.bounty_task,
        )

    staking_event_id = add_staking_reward_event(
        conn,
        daily_session_id,
        args.datetime,
        args.event_type,
        args.source,
        args.token,
        args.amount,
        related_bounty_task_id,
        args.notes,
    )

    print(f"Staking/reward event ID: {staking_event_id}")

    conn.close()


if __name__ == "__main__":
    main()