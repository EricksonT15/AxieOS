import argparse
from email import parser

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


def get_bounty_task_id(conn, daily_session_id, task_slot):
    if task_slot is None:
        return None

    row = conn.execute(
        """
        SELECT id
        FROM bounty_board_tasks
        WHERE daily_session_id = ?
          AND task_slot = ?
          AND selected_final = 1
        """,
        (daily_session_id, task_slot),
    ).fetchone()

    if row is None:
        raise ValueError(
            f"No final Bounty task found for slot {task_slot}."
        )

    return row[0]


def add_marketplace_event(args):
    conn = connect_database()

    daily_session_id = get_daily_session_id(
        conn,
        args.date,
        args.player,
    )

    bounty_task_ids = []

    for task_slot in args.bounty_task:
        bounty_task_ids.append(
            get_bounty_task_id(
                conn,
                daily_session_id,
                task_slot,
            )
        )

    primary_bounty_task_id = (
        bounty_task_ids[0]
        if bounty_task_ids
        else None
    )

    cursor = conn.execute(
        """
        INSERT INTO marketplace_events (
            daily_session_id,
            event_datetime,
            event_type,
            asset_type,
            asset_id,
            asset_name,
            quantity,
            amount,
            currency,
            related_bounty_task_id,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            daily_session_id,
            args.datetime,
            args.event_type,
            args.asset_type,
            args.asset_id,
            args.asset_name,
            args.quantity,
            args.amount,
            args.currency,
            primary_bounty_task_id,
            args.notes,
        ),
    )

   

    event_id = cursor.lastrowid

    for bounty_task_id in bounty_task_ids:
        conn.execute(
            """
            INSERT OR IGNORE INTO marketplace_event_bounty_tasks (
                marketplace_event_id,
                bounty_task_id
            )
            VALUES (?, ?)
            """,
            (
                event_id,
                bounty_task_id,
            ),
        )

    conn.commit()

    row = conn.execute(
        """
        SELECT
            id,
            event_datetime,
            event_type,
            asset_type,
            asset_id,
            quantity,
            amount,
            currency,
            related_bounty_task_id
        FROM marketplace_events
        WHERE id = ?
        """,
        (event_id,),
    ).fetchone()

    conn.close()

    return row


def main():
    parser = argparse.ArgumentParser(
        description="Add an AxieOS marketplace event."
    )

    parser.add_argument("date")
    parser.add_argument("event_type")
    parser.add_argument("asset_type")

    parser.add_argument("--player", default="primary")
    parser.add_argument("--datetime", required=True)
    parser.add_argument("--asset-id")
    parser.add_argument("--asset-name", default="")
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--amount", required=True)
    parser.add_argument("--currency", required=True)
    parser.add_argument(
        "--bounty-task",
        type=int,
        action="append",
        default=[],
        help="Bounty task slot completed by this event. May be repeated.",
)
    parser.add_argument("--notes", default="")

    args = parser.parse_args()

    row = add_marketplace_event(args)

    print("Marketplace event saved.")
    print(row)


if __name__ == "__main__":
    main()