import sqlite3
from pathlib import Path

DB_PATH = Path("data/blockchain/database/axieos.db")

conn = sqlite3.connect(DB_PATH)

cursor = conn.cursor()

print("="*60)
print("TABLES")
print("="*60)

cursor.execute("""
SELECT name
FROM sqlite_master
WHERE type='table';
""")

for row in cursor.fetchall():
    print(row[0])

print()

print("="*60)
print("COLUMNS")
print("="*60)

cursor.execute("""
PRAGMA table_info(blockchain_transactions);
""")

for col in cursor.fetchall():
    print(col)

conn.close()