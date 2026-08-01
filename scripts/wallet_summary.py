"""Generate a high-level summary of the AxieOS blockchain database."""

from database import connect_database

def print_header():
    """Display the report header."""

    print("=" * 57)
    print("                 AXIEOS WALLET SUMMARY")
    print("=" * 57)


def print_database_overview(conn):
    """Display basic information about the blockchain database."""

    cursor = conn.cursor()

    # Total transactions
    cursor.execute("""
        SELECT COUNT(*)
        FROM blockchain_transactions;
    """)
    total_transactions = cursor.fetchone()[0]

    cursor.execute("""
        SELECT
            MIN(datetime),
            MAX(datetime)
        FROM blockchain_transactions;
    """)
    first_date, latest_date = cursor.fetchone()

    print("\nDATABASE OVERVIEW")
    print("-" * 40)
    print(f"Total Transactions : {total_transactions}")
    print(f"Date Range         : {first_date} -> {latest_date}")
    print(f"Latest Transaction : {latest_date}")


def print_wallets(conn):
    """Display unique values found in the sender and receiver columns."""

    cursor = conn.cursor()

    cursor.execute("""
    SELECT DISTINCT from_address
    FROM blockchain_transactions

    UNION

    SELECT DISTINCT to_address
    FROM blockchain_transactions;
""")

    wallets = []

    for row in cursor.fetchall():
        wallet = row[0]

        if wallet is None:
            continue

        wallet = str(wallet).strip()

        if not wallet:
            continue

        wallets.append(wallet)

    print("\nWALLETS")
    print("-" * 40)
    print(f"Wallets Found : {len(wallets)}")

    for index, wallet in enumerate(wallets, start=1):
        print(f"{index}. {wallet}")

def print_transaction_methods(conn):
    """Display transaction methods and their occurrence counts."""

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            method,
            COUNT(*) AS transaction_count
        FROM blockchain_transactions
        GROUP BY method
        ORDER BY transaction_count DESC, method ASC;
    """)

    methods = cursor.fetchall()

    print("\nTRANSACTION METHODS")
    print("-" * 40)

    for method, count in methods:
        display_method = method if method else "(blank)"
        print(f"{display_method:<30} {count:>5}")

def print_tokens(conn):
    """Display tokens and collectibles found in the transaction data."""

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            token_collectibles,
            COUNT(*) AS transaction_count
        FROM blockchain_transactions
        GROUP BY token_collectibles
        ORDER BY transaction_count DESC, token_collectibles ASC;
    """)

    tokens = cursor.fetchall()

    print("\nTOKENS AND COLLECTIBLES")
    print("-" * 40)

    for token, count in tokens:
        display_token = token if token else "(blank)"
        print(f"{display_token:<30} {count:>5}")

def print_network_fees(conn):
    """Display the total RON spent on blockchain transaction fees."""

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            SUM(txn_fee_ron)
        FROM blockchain_transactions;
    """)

    total_fee = cursor.fetchone()[0]

    if total_fee is None:
        total_fee = 0

    print("\nNETWORK FEES")
    print("-" * 40)
    print(f"Total RON Fees : {total_fee:.8f}")

    if total_fee == 0:
        print("Note           : Source dataset contains zero recorded fees.")

def main():
    """Run the wallet summary report."""

    conn = connect_database()

    try:
        print_header()
        print_database_overview(conn)
        print_wallets(conn)
        print_transaction_methods(conn)
        print_tokens(conn)
        print_network_fees(conn)

    finally:
        conn.close()


if __name__ == "__main__":
    main()

def print_table_columns(conn):
    """Display the actual blockchain transaction column names."""

    cursor = conn.cursor()

    cursor.execute("""
        PRAGMA table_info(blockchain_transactions);
    """)

    print("\nTABLE COLUMNS")
    print("-" * 40)

    for row in cursor.fetchall():
        print(row[1])