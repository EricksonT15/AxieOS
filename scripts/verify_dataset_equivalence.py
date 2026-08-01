"""
verify_dataset_equivalence.py

Purpose:
Verify whether Legacy Transactions, Transfers, and Internal Transfers
contain identical blockchain data.

Author: AxieOS
"""

from pathlib import Path
import pandas as pd


# --------------------------------------------------
# Configuration
# --------------------------------------------------

DATA_DIR = Path("data/blockchain/raw")

FILES = {
    "Transactions": "legacy_transactions_2021.csv",
    "Transfers": "legacy_transfers_2021.csv",
    "Internal": "legacy_internal_transactions_2021.csv",
}


# --------------------------------------------------
# Functions
# --------------------------------------------------

def load_csv(filename):
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    return pd.read_csv(path)


def normalize_columns(df):
    """
    Lowercase column names and remove spaces.
    """
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
    )
    return df


def get_hash_column(df):
    """
    Automatically detect the transaction hash column.
    """

    possible = [
        "txhash",
        "tx_hash",
        "hash",
        "transaction_hash",
    ]

    for col in possible:
        if col in df.columns:
            return col

    return None


def compare_columns(dataframes):
    print("\n========== COLUMN COMPARISON ==========\n")

    for name, df in dataframes.items():
        print(f"{name}")
        print(f"Columns ({len(df.columns)}):")

        for col in df.columns:
            print(f"  - {col}")

        print()


def compare_hashes(dataframes):

    print("\n========== HASH COMPARISON ==========\n")

    hash_sets = {}

    for name, df in dataframes.items():

        hash_col = get_hash_column(df)

        if hash_col is None:
            print(f"{name}: No transaction hash column found.\n")
            continue

        hash_sets[name] = set(df[hash_col].astype(str))

    names = list(hash_sets.keys())

    for i in range(len(names)):
        for j in range(i + 1, len(names)):

            a = names[i]
            b = names[j]

            common = hash_sets[a] == hash_sets[b]

            print(f"{a} vs {b}")

            if common:
                print("   IDENTICAL\n")
            else:

                only_a = len(hash_sets[a] - hash_sets[b])
                only_b = len(hash_sets[b] - hash_sets[a])

                print(f"   Unique to {a}: {only_a}")
                print(f"   Unique to {b}: {only_b}\n")


def row_summary(dataframes):

    print("\n========== ROW SUMMARY ==========\n")

    for name, df in dataframes.items():
        print(f"{name:20} : {len(df):,} rows")


# --------------------------------------------------
# Main
# --------------------------------------------------

def main():

    print("=" * 60)
    print("VERIFY DATASET EQUIVALENCE")
    print("=" * 60)

    dataframes = {}

    for name, filename in FILES.items():

        df = load_csv(filename)
        df = normalize_columns(df)

        dataframes[name] = df

    row_summary(dataframes)

    compare_columns(dataframes)

    compare_hashes(dataframes)

    print("=" * 60)
    print("Verification Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
