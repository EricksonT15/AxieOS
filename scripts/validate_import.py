"""
validate_import.py

Purpose:
Validate the AxieOS SQLite database after importing blockchain data.

Author: AxieOS
"""

from pathlib import Path
import sqlite3

DB_PATH = Path("data/blockchain/database/axieos.db")

print("=" * 60)
print("DATABASE VALIDATION")
print("=" * 60)

# --------------------------------------------------
# Check Database
# --------------------------------------------------

if not DB_PATH.exists():
    print("Database not found.")
    quit()

print("Database Exists : PASS")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# --------------------------------------------------
# Check Table Exists
# --------------------------------------------------

cursor.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
AND name='blockchain_transactions';
""")

if cursor.fetchone() is None:
    print("Table blockchain_transactions not found.")
    conn.close()
    quit()

print("Table Exists : PASS")

# --------------------------------------------------
# Total Rows
# --------------------------------------------------

cursor.execute("""
SELECT COUNT(*)
FROM blockchain_transactions;
""")

rows = cursor.fetchone()[0]

print(f"Total Rows : {rows:,}")

# --------------------------------------------------
# Duplicate Transaction Hashes
# --------------------------------------------------

cursor.execute("""
SELECT COUNT(*) FROM (

    SELECT txhash

    FROM blockchain_transactions

    GROUP BY txhash

    HAVING COUNT(*) > 1

);
""")

duplicates = cursor.fetchone()[0]

print(f"Duplicate Transaction Hashes : {duplicates}")

if duplicates > 0:

    print("\nDuplicate Transaction Hashes Found:")

    cursor.execute("""
    SELECT
        txhash,
        COUNT(*) AS occurrences
    FROM blockchain_transactions
    GROUP BY txhash
    HAVING COUNT(*) > 1
    ORDER BY occurrences DESC;
    """)

    for txhash, count in cursor.fetchall():
        print(f"  {txhash} ({count} rows)")

# --------------------------------------------------
# Missing Transaction Hashes
# --------------------------------------------------

cursor.execute("""
SELECT COUNT(*)

FROM blockchain_transactions

WHERE txhash IS NULL
OR txhash='';
""")

missing = cursor.fetchone()[0]

print(f"Missing Transaction Hashes : {missing}")

# --------------------------------------------------
# Timestamp Range
# --------------------------------------------------

try:

    cursor.execute("""
    SELECT MIN(datetime), MAX(datetime)
    FROM blockchain_transactions;
    """)

    first, last = cursor.fetchone()

    print()
    print(f"First Transaction : {first}")
    print(f"Latest Transaction: {last}")

except Exception as e:

    print()
    print("Datetime column not available.")
    print(e)

# --------------------------------------------------



# --------------------------------------------------
# Transaction Methods
# --------------------------------------------------

print()
print("Transaction Methods")

cursor.execute("""
SELECT
    method,
    COUNT(*)
FROM blockchain_transactions
GROUP BY method
ORDER BY COUNT(*) DESC;
""")

for method, count in cursor.fetchall():
    print(f"  {method:<30} {count}")



# --------------------------------------------------
# Tokens
# --------------------------------------------------

print()
print("Tokens")

cursor.execute("""
SELECT DISTINCT token_collectibles
FROM blockchain_transactions
WHERE token_collectibles IS NOT NULL
ORDER BY token_collectibles;
""")

for (token,) in cursor.fetchall():
    print(f"  {token}")


# --------------------------------------------------
# Indexes
# --------------------------------------------------

print()
print("Database Indexes")

cursor.execute("""
PRAGMA index_list(blockchain_transactions);
""")

for row in cursor.fetchall():
    print(f"  {row[1]}")

# --------------------------------------------------
# Final Status
# --------------------------------------------------

print()
print("=" * 60)
print("DATABASE HEALTHY")
print("=" * 60)

conn.close()