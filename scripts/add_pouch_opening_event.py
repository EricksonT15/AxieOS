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


def add_pouch_opening_event(
    conn,
    daily_session_id,
    event_datetime,
    pouch_type,
    quantity_opened,
    slips_spent,
    request_tx_hash=None,
    fulfillment_tx_hash=None,
    upfront_ron=None,
    user_tx_fee_ron=None,
    refund_ron=None,
    net_ron_cost=None,
    notes=None,
):
    cursor = conn.execute(
        """
        INSERT INTO pouch_opening_events (
            daily_session_id,
            event_datetime,
            pouch_type,
            quantity_opened,
            slips_spent,
            request_tx_hash,
            fulfillment_tx_hash,
            upfront_ron,
            user_tx_fee_ron,
            refund_ron,
            net_ron_cost,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            daily_session_id,
            event_datetime,
            pouch_type,
            quantity_opened,
            slips_spent,
            request_tx_hash,
            fulfillment_tx_hash,
            upfront_ron,
            user_tx_fee_ron,
            refund_ron,
            net_ron_cost,
            notes,
        ),
    )

    conn.commit()

    return cursor.lastrowid

def add_pouch_reward_item(
    conn,
    pouch_opening_event_id,
    item_name,
    quantity,
    notes=None,
):
    cursor = conn.execute(
        """
        INSERT INTO pouch_reward_items (
            pouch_opening_event_id,
            item_name,
            quantity,
            notes
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            pouch_opening_event_id,
            item_name,
            quantity,
            notes,
        ),
    )

    conn.commit()

    return cursor.lastrowid


def parse_reward(reward_text):
    try:
        item_name, quantity_text = reward_text.rsplit(":", 1)

        item_name = item_name.strip()
        quantity = int(quantity_text.strip())

        if not item_name:
            raise ValueError

        return item_name, quantity

    except ValueError:
        raise ValueError(
            "Reward must use ITEM:QUANTITY format, "
            'for example "Regular Choco:2".'
        )


def main():
    parser = argparse.ArgumentParser(
        description="Add an AxieOS pouch opening event."
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
        help="Opening date/time.",
    )

    parser.add_argument(
        "--pouch-type",
        required=True,
        help="Pouch type, for example Regular or Premium.",
    )

    parser.add_argument(
        "--quantity",
        type=int,
        required=True,
        help="Number of pouches opened.",
    )

    parser.add_argument(
        "--slips-spent",
        type=int,
        required=True,
        help="Fortune Slips spent.",
    )

    parser.add_argument(
        "--request-tx",
        default=None,
        help="Optional VRF request transaction hash.",
    )

    parser.add_argument(
        "--fulfillment-tx",
        default=None,
        help="Optional VRF fulfillment transaction hash.",
    )

    parser.add_argument(
        "--upfront-ron",
        default=None,
        help="Optional upfront RON amount.",
    )

    parser.add_argument(
        "--tx-fee-ron",
        default=None,
        help="Optional user transaction fee in RON.",
    )

    parser.add_argument(
        "--refund-ron",
        default=None,
        help="Optional VRF refund in RON.",
    )

    parser.add_argument(
        "--net-ron",
        default=None,
        help="Optional calculated net RON cost.",
    )

    parser.add_argument(
        "--notes",
        default=None,
        help="Optional notes.",
    )

    parser.add_argument(
        "--reward",
        action="append",
        default=[],
        help=(
            "Reward in ITEM:QUANTITY format. "
            "May be repeated, for example "
            '--reward "Regular Choco:2" '
            '--reward "Premium Choco:1".'
        ),
    )


    args = parser.parse_args()

    conn = connect_database()

    daily_session_id = get_daily_session_id(
        conn,
        args.date,
        args.player,
    )

    pouch_event_id = add_pouch_opening_event(
        conn,
        daily_session_id,
        args.datetime,
        args.pouch_type,
        args.quantity,
        args.slips_spent,
        args.request_tx,
        args.fulfillment_tx,
        args.upfront_ron,
        args.tx_fee_ron,
        args.refund_ron,
        args.net_ron,
        args.notes,
    )

    for reward_text in args.reward:
        item_name, quantity = parse_reward(
            reward_text
        )

        add_pouch_reward_item(
            conn,
            pouch_event_id,
            item_name,
            quantity,
        )

    print(f"Pouch opening event ID: {pouch_event_id}")

    conn.close()


if __name__ == "__main__":
    main()