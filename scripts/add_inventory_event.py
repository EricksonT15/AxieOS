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



def add_inventory_event(
    conn,
    daily_session_id,
    event_datetime,
    item_type,
    item_name,
    event_type,
    quantity_change,
    notes=None,
):
    cursor = conn.execute(
        """
        INSERT INTO inventory_events (
            daily_session_id,
            event_datetime,
            item_type,
            item_name,
            event_type,
            quantity_change,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            daily_session_id,
            event_datetime,
            item_type,
            item_name,
            event_type,
            quantity_change,
            notes,
        ),
    )

    conn.commit()

    return cursor.lastrowid


def link_inventory_event_to_bounty_tasks(
    conn,
    inventory_event_id,
    daily_session_id,
    task_slots,
):
    for task_slot in task_slots:
        bounty_task_id = get_final_bounty_task_id(
            conn,
            daily_session_id,
            task_slot,
        )

        conn.execute(
            """
            INSERT OR IGNORE INTO inventory_event_bounty_tasks (
                inventory_event_id,
                bounty_task_id
            )
            VALUES (?, ?)
            """,
            (
                inventory_event_id,
                bounty_task_id,
            ),
        )

    conn.commit()





def main():
    parser = argparse.ArgumentParser(
        description="Add an AxieOS inventory event."
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
        help="Event date/time, for example 2026-08-08 11:26.",
    )

    parser.add_argument(
        "--item-type",
        required=True,
        help="Inventory category, for example Consumable.",
    )

    parser.add_argument(
        "--item-name",
        required=True,
        help="Item name, for example Regular Choco.",
    )

    parser.add_argument(
        "--event-type",
        required=True,
        help="Event type, for example pouch_reward or feed.",
    )

    parser.add_argument(
        "--quantity",
        type=int,
        required=True,
        help="Signed quantity change, for example +10 or -10.",
    )

    parser.add_argument(
        "--notes",
        default=None,
        help="Optional notes.",
    )

    parser.add_argument(
        "--bounty-task",
        type=int,
        action="append",
        default=[],
        help=(
            "Bounty task slot completed by this inventory event. "
            "May be repeated."
        ),
    )


    args = parser.parse_args()

    conn = connect_database()

    daily_session_id = get_daily_session_id(
        conn,
        args.date,
        args.player,
    )

    inventory_event_id = add_inventory_event(
        conn,
        daily_session_id,
        args.datetime,
        args.item_type,
        args.item_name,
        args.event_type,
        args.quantity,
        args.notes,
    )

    if args.bounty_task:
        link_inventory_event_to_bounty_tasks(
            conn,
            inventory_event_id,
            daily_session_id,
            args.bounty_task,
        )


    print(f"Inventory event ID: {inventory_event_id}")

    conn.close()


if __name__ == "__main__":
    main()