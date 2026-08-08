from collections import defaultdict
from decimal import Decimal

from database import connect_database


def to_decimal(value):
    """Convert database text values safely to Decimal."""
    if value is None or str(value).strip() == "":
        return Decimal("0")

    return Decimal(str(value))


def format_amount(value):
    """Display Decimal values without unnecessary trailing zeros."""
    text = format(value, "f")

    if "." in text:
        text = text.rstrip("0").rstrip(".")

    return text or "0"


def main():
    conn = connect_database()

    rows = conn.execute(
        """
        SELECT
            token_collectibles,
            value_in,
            value_out
        FROM blockchain_transactions
        WHERE token_collectibles IS NOT NULL
        ORDER BY token_collectibles
        """
    ).fetchall()

    conn.close()

    summary = defaultdict(
        lambda: {
            "transactions": 0,
            "received": Decimal("0"),
            "sent": Decimal("0"),
            "incoming_transactions": 0,
            "outgoing_transactions": 0,
            "zero_movement_transactions": 0,
        }
    )

    for token, value_in, value_out in rows:
        received = to_decimal(value_in)
        sent = to_decimal(value_out)

        data = summary[token]

        data["transactions"] += 1
        data["received"] += received
        data["sent"] += sent

        if received > 0:
            data["incoming_transactions"] += 1

        if sent > 0:
            data["outgoing_transactions"] += 1

        if received == 0 and sent == 0:
            data["zero_movement_transactions"] += 1

    print("=" * 72)
    print("AXIEOS TOKEN SUMMARY")
    print("=" * 72)

    for token in sorted(summary):
        data = summary[token]
        net = data["received"] - data["sent"]

        print()
        print(f"Token: {token}")
        print(f"  Transactions:             {data['transactions']}")
        print(f"  Incoming transactions:    {data['incoming_transactions']}")
        print(f"  Outgoing transactions:    {data['outgoing_transactions']}")
        print(f"  Zero-movement transactions: {data['zero_movement_transactions']}")
        print(f"  Total received:           {format_amount(data['received'])}")
        print(f"  Total sent:               {format_amount(data['sent'])}")
        print(f"  Net movement:             {format_amount(net)}")

    print()
    print("=" * 72)


if __name__ == "__main__":
    main()