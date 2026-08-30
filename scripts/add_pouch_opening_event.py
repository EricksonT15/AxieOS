import argparse

from database import connect_database
from add_inventory_event import add_inventory_event


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




def add_pouch_reward_inventory_event(
    conn,
    daily_session_id,
    event_datetime,
    pouch_opening_event_id,
    item_name,
    quantity,
):
    """
    Mirror supported pouch rewards into inventory_events.

    inventory_events is the canonical quantity ledger.
    pouch_reward_items remains the detailed pouch-reward record.

    V0.9 currently treats Regular Choco and Premium Choco
    as supported optimizer inventory resources.
    """

    normalized_name = " ".join(
        str(item_name).strip().split()
    )

    supported_items = {
        "regular choco": "Regular Choco",
        "premium choco": "Premium Choco",
    }

    canonical_name = supported_items.get(
        normalized_name.casefold()
    )

    if canonical_name is None:
        return None

    if quantity <= 0:
        raise ValueError(
            "Pouch reward inventory quantity "
            "must be positive."
        )

    return add_inventory_event(
        conn=conn,
        daily_session_id=daily_session_id,
        event_datetime=event_datetime,
        item_type="Consumable",
        item_name=canonical_name,
        event_type="pouch_reward",
        quantity_change=quantity,
        notes=(
            "Inventory mirror from pouch opening "
            f"event #{pouch_opening_event_id}."
        ),
    )



def run_v09_pouch_inventory_mirror_test():
    import sqlite3

    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 POUCH INVENTORY MIRROR TEST"
    )
    print(
        "============================================================"
    )

    conn = sqlite3.connect(
        ":memory:"
    )

    conn.execute(
        """
        CREATE TABLE inventory_events (
            id INTEGER PRIMARY KEY,
            daily_session_id INTEGER,
            event_datetime TEXT NOT NULL,
            item_type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            quantity_change INTEGER NOT NULL,
            related_bounty_task_id INTEGER,
            related_marketplace_event_id INTEGER,
            notes TEXT,
            created_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    all_passed = True

    # --------------------------------------------------------
    # Regular Choco
    # --------------------------------------------------------

    regular_id = (
        add_pouch_reward_inventory_event(
            conn=conn,
            daily_session_id=100,
            event_datetime=(
                "2026-08-25 12:00:00"
            ),
            pouch_opening_event_id=500,
            item_name="Regular Choco",
            quantity=3,
        )
    )

    regular_row = conn.execute(
        """
        SELECT
            daily_session_id,
            event_datetime,
            item_type,
            item_name,
            event_type,
            quantity_change
        FROM inventory_events
        WHERE id = ?
        """,
        (
            regular_id,
        ),
    ).fetchone()

    regular_expected = (
        100,
        "2026-08-25 12:00:00",
        "Consumable",
        "Regular Choco",
        "pouch_reward",
        3,
    )

    regular_passed = (
        regular_row
        == regular_expected
    )

    print(
        "Regular Choco mirror:",
        "PASS" if regular_passed else "FAIL",
    )
    print(
        "  Row:",
        regular_row,
    )

    if not regular_passed:
        all_passed = False

    # --------------------------------------------------------
    # Premium Choco
    # --------------------------------------------------------

    premium_id = (
        add_pouch_reward_inventory_event(
            conn=conn,
            daily_session_id=100,
            event_datetime=(
                "2026-08-25 12:01:00"
            ),
            pouch_opening_event_id=501,
            item_name="Premium Choco",
            quantity=1,
        )
    )

    premium_row = conn.execute(
        """
        SELECT
            item_type,
            item_name,
            event_type,
            quantity_change
        FROM inventory_events
        WHERE id = ?
        """,
        (
            premium_id,
        ),
    ).fetchone()

    premium_passed = (
        premium_row
        == (
            "Consumable",
            "Premium Choco",
            "pouch_reward",
            1,
        )
    )

    print(
        "Premium Choco mirror:",
        "PASS" if premium_passed else "FAIL",
    )
    print(
        "  Row:",
        premium_row,
    )

    if not premium_passed:
        all_passed = False

    # --------------------------------------------------------
    # Unsupported reward must not corrupt inventory ledger
    # --------------------------------------------------------

    unsupported_result = (
        add_pouch_reward_inventory_event(
            conn=conn,
            daily_session_id=100,
            event_datetime=(
                "2026-08-25 12:02:00"
            ),
            pouch_opening_event_id=502,
            item_name="Unknown Reward",
            quantity=5,
        )
    )

    row_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM inventory_events
        """
    ).fetchone()[0]

    unsupported_passed = (
        unsupported_result is None
        and row_count == 2
    )

    print(
        "Unsupported reward guardrail:",
        (
            "PASS"
            if unsupported_passed
            else "FAIL"
        ),
    )
    print(
        "  Inventory rows:",
        row_count,
    )

    if not unsupported_passed:
        all_passed = False

    conn.close()

    print(
        "\nV0.9 Pouch Inventory Mirror:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



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

        add_pouch_reward_inventory_event(
            conn=conn,
            daily_session_id=daily_session_id,
            event_datetime=args.datetime,
            pouch_opening_event_id=(
                pouch_event_id
            ),
            item_name=item_name,
            quantity=quantity,
        )
    
    print(f"Pouch opening event ID: {pouch_event_id}")

    conn.close()


if __name__ == "__main__":
    main()