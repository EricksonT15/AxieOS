"""
create_database_schema.py

Purpose:
Create the SQLite database schema for AxieOS.

Author: AxieOS
"""

from pathlib import Path
import sqlite3

# --------------------------------------------------
# Configuration
# --------------------------------------------------

DB_DIR = Path("data/blockchain/database")
DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "axieos.db"

# --------------------------------------------------
# Create Database
# --------------------------------------------------

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()

# --------------------------------------------------
# Blockchain Transactions
# --------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS blockchain_transactions (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    block_number INTEGER,
    timestamp TEXT,

    hash TEXT UNIQUE,

    from_address TEXT,
    to_address TEXT,

    value REAL,

    method TEXT,

    tx_fee REAL,

    status TEXT

);
""")

# --------------------------------------------------
# Useful Indexes
# --------------------------------------------------

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_hash
ON blockchain_transactions(hash);
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_timestamp
ON blockchain_transactions(timestamp);
""")

conn.commit()

conn.close()

print("=" * 60)
print("AxieOS Database Created Successfully")
print(DB_PATH)
print("=" * 60)