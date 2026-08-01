"""Generate a transaction-level summary from the AxieOS database."""

from database import connect_database

WALLET_ADDRESS = "0x1ed8b3f3bd6a624de47f81beea101f0d15cdfbc8"


def print_header():
    """Display the report header."""

    print("=" * 57)
    print("              AXIEOS TRANSACTION SUMMARY")
    print("=" * 57)

def print_status_summary(conn):
    """Display transaction counts grouped by status."""

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            status,
            COUNT(*) AS transaction_count
        FROM blockchain_transactions
        GROUP BY status
        ORDER BY transaction_count DESC;
    """)

    rows = cursor.fetchall()

    print("\nTRANSACTION STATUS")
    print("-" * 40)

    for status, count in rows:
        display_status = status if status else "(blank)"
        print(f"{display_status:<30} {count:>5}")

def print_method_summary(conn):
    """Display transaction counts grouped by method."""

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            method,
            COUNT(*) AS transaction_count
        FROM blockchain_transactions
        GROUP BY method
        ORDER BY transaction_count DESC, method ASC;
    """)

    rows = cursor.fetchall()

    print("\nTRANSACTION METHODS")
    print("-" * 40)

    for method, count in rows:
        display_method = method if method else "(blank)"
        print(f"{display_method:<30} {count:>5}")

def print_monthly_activity(conn):
    """Display transaction counts grouped by month."""

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            substr(datetime, 1, 7) AS month,
            COUNT(*) AS transaction_count
        FROM blockchain_transactions
        GROUP BY month
        ORDER BY month ASC;
    """)

    rows = cursor.fetchall()

    print("\nMONTHLY ACTIVITY")
    print("-" * 40)

    for month, count in rows:
        display_month = month if month else "(unknown)"
        print(f"{display_month:<30} {count:>5}")

def print_wallet_direction_summary(conn):
    """Display incoming and outgoing transaction counts for the primary wallet."""

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            SUM(
                CASE
                    WHEN LOWER(to_address) = ?
                    AND LOWER(from_address) != ?
                    THEN 1
                    ELSE 0
                END
            ) AS incoming_count,

            SUM(
                CASE
                    WHEN LOWER(from_address) = ?
                    AND LOWER(to_address) != ?
                    THEN 1
                    ELSE 0
                END
            ) AS outgoing_count,

            SUM(
                CASE
                    WHEN LOWER(from_address) = ?
                    AND LOWER(to_address) = ?
                    THEN 1
                    ELSE 0
                END
            ) AS self_transfer_count

        FROM blockchain_transactions;
        """,
        (
            WALLET_ADDRESS,
            WALLET_ADDRESS,
            WALLET_ADDRESS,
            WALLET_ADDRESS,
            WALLET_ADDRESS,
            WALLET_ADDRESS,
        ),
    )

    incoming, outgoing, self_transfers = cursor.fetchone()

    incoming = incoming or 0
    outgoing = outgoing or 0
    self_transfers = self_transfers or 0

    print("\nWALLET DIRECTION")
    print("-" * 40)
    print(f"Primary Wallet      : {WALLET_ADDRESS}")
    print(f"Incoming            : {incoming}")
    print(f"Outgoing            : {outgoing}")
    print(f"Self Transfers      : {self_transfers}")

def print_latest_transactions(conn, limit=5):
    """Display the most recent blockchain transactions."""

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            datetime,
            method,
            token_collectibles,
            from_address,
            to_address,
            status
        FROM blockchain_transactions
        ORDER BY datetime DESC
        LIMIT ?;
        """,
        (limit,),
    )

    rows = cursor.fetchall()

    print("\nLATEST TRANSACTIONS")
    print("-" * 80)

    for (
        transaction_time,
        method,
        token,
        from_address,
        to_address,
        status,
    ) in rows:
        display_method = method or "(blank)"
        display_token = token or "(blank)"
        display_status = status or "(blank)"

        print(f"Date   : {transaction_time}")
        print(f"Method : {display_method}")
        print(f"Token  : {display_token}")
        print(f"From   : {from_address}")
        print(f"To     : {to_address}")
        print(f"Status : {display_status}")
        print("-" * 80)

def print_duplicate_hashes(conn):
    """Display transaction hashes that appear more than once."""

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            txhash,
            COUNT(*) AS occurrence_count
        FROM blockchain_transactions
        GROUP BY txhash
        HAVING COUNT(*) > 1
        ORDER BY occurrence_count DESC, txhash ASC;
    """)

    rows = cursor.fetchall()

    print("\nDUPLICATE TRANSACTION HASHES")
    print("-" * 80)

    if not rows:
        print("No duplicate transaction hashes found.")
        return

    for txhash, count in rows:
        print(f"{txhash}  ({count} rows)")

def main():
    """Run the transaction summary report."""

    conn = connect_database()

    try:
        print_header()
        print_status_summary(conn)
        print_method_summary(conn)
        print_monthly_activity(conn)
        print_wallet_direction_summary(conn)
        print_latest_transactions(conn)
        print_duplicate_hashes(conn)

    finally:
        conn.close()


if __name__ == "__main__":
    main()