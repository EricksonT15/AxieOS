import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import sqlite3
import shutil
from decimal import Decimal
import hashlib
from datetime import datetime



SAMPLE_PATH = Path(
    "data/blockchain/api_samples/"
    "ronin_transactions_sample.json"
)

RONIN_WALLET_ADDRESS = (
    "0x1eD8B3F3BD6a624De47f81Beea101f0d15CDfbC8"
)

RONIN_TRANSACTIONS_URL = (
    "https://explorer.roninchain.com/api/v2/"
    "addresses/"
    "0x1eD8B3F3BD6a624De47f81Beea101f0d15CDfbC8/"
    "transactions"
)


RONIN_TOKEN_TRANSFERS_URL = (
    "https://explorer.roninchain.com/api/v2/"
    "addresses/"
    "0x1eD8B3F3BD6a624De47f81Beea101f0d15CDfbC8/"
    "token-transfers"
)


TRANSACTION_CLASSIFICATIONS = {
    "MARKETPLACE_BUY",
    "MARKETPLACE_SALE",
    "TOKEN_SWAP",
    "TRANSFER_IN",
    "TRANSFER_OUT",
    "CONSUMABLE_BURN",
    "NFT_BURN",
    "MINT_OR_CLAIM",
    "STAKING_OR_REWARD",
    "UNKNOWN",
}


CLASSIFICATION_DESCRIPTIONS = {
    "MARKETPLACE_BUY": (
        "Asset received and payment sent"
    ),
    "MARKETPLACE_SALE": (
        "Asset sent and payment received"
    ),
    "TOKEN_SWAP": (
        "One fungible token sent and "
        "another fungible token received"
    ),
    "TRANSFER_IN": (
        "Asset received without a detected "
        "matching payment"
    ),
    "TRANSFER_OUT": (
        "Asset sent without a detected "
        "matching receipt"
    ),
    "CONSUMABLE_BURN": (
        "Consumable sent to the zero address"
    ),
    "NFT_BURN": (
        "NFT sent to the zero address"
    ),
    "MINT_OR_CLAIM": (
        "Asset received from the zero address"
    ),
    "STAKING_OR_REWARD": (
        "Staking or reward-related activity"
    ),
    "UNKNOWN": (
        "Transaction needs review"
    ),
}


ECONOMICS_VERSION = "0.3"


MARKETPLACE_SELLER_FEE_RATE = Decimal(
    "0.0425"
)

ECONOMIC_EVENT_FIELDS = {
    "event_key",
    "txhash",
    "classification",
    "asset_name",
    "asset_token_id",
    "quantity",
    "payment_asset",
    "gross_amount",
    "marketplace_fee",
    "net_amount",
    "cost_basis",
    "realized_pl",
    "economics_status",
    "economics_version",
}




TEST_DB_PATH = Path(
    "data/blockchain/database/"
    "ronin_sync_test.db"
)


IDEMPOTENCY_DB_PATH = Path(
    "data/blockchain/database/"
    "ronin_idempotency_test.db"
)


AXIEOS_DB_PATH = Path(
    "data/blockchain/database/"
    "axieos.db"
)


AXIEOS_BACKUP_PATH = Path(
    "data/blockchain/database/backups/"
    "axieos_pre_ronin_sync_2026-08-20.db"
)


ZERO_ADDRESS = (
    "0x0000000000000000000000000000000000000000"
)


CLASSIFIER_VERSION = "0.2"




def load_transaction_response(
    file_path,
):
    with open(
        file_path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)




def extract_address(
    address_data,
):
    if isinstance(address_data, dict):
        return address_data.get("hash")

    return address_data


def normalize_transaction(
    transaction,
):
    fee = transaction.get(
        "fee"
    )

    if isinstance(fee, dict):
        fee_value = fee.get("value")
    else:
        fee_value = fee

    return {
        "tx_hash": transaction.get("hash"),
        "timestamp": transaction.get(
            "timestamp"
        ),
        "block_number": transaction.get(
            "block_number"
        ),
        "from_address": extract_address(
            transaction.get("from")
        ),
        "to_address": extract_address(
            transaction.get("to")
        ),
        "method": transaction.get("method"),
        "status": transaction.get("status"),
        "value": transaction.get("value"),
        "fee": fee_value,
        "gas_used": transaction.get(
            "gas_used"
        ),
    }


def normalize_transactions(
    transactions,
):
    return [
        normalize_transaction(transaction)
        for transaction in transactions
    ]


def deduplicate_transactions(
    transactions,
):
    unique_transactions = {}

    for transaction in transactions:
        tx_hash = transaction[
            "tx_hash"
        ]

        unique_transactions[
            tx_hash
        ] = transaction

    return list(
        unique_transactions.values()
    )


def get_next_page_params(
    response,
):
    return response.get(
        "next_page_params"
    )


def build_pagination_query(
    next_page_params,
):
    if not next_page_params:
        return None

    return urlencode(
        next_page_params
    )


def fetch_json(
    url,
    params=None,
):
    if params:
        url = (
            f"{url}?"
            f"{urlencode(params)}"
        )

    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": (
                "AxieOS-Ronin-Sync/0.1"
            ),
        },
    )

    with urlopen(
        request,
        timeout=20,
    ) as response:
        return json.load(response)


def initialize_transaction_database(
    db_path,
):
    db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ronin_transactions (
            tx_hash TEXT PRIMARY KEY,
            timestamp TEXT,
            block_number INTEGER,
            from_address TEXT,
            to_address TEXT,
            method TEXT,
            status TEXT,
            value_raw TEXT,
            fee_raw TEXT,
            gas_used INTEGER
        )
        """
    )

    connection.commit()
    connection.close()


def initialize_economic_events_table(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        blockchain_economic_events (
            event_key TEXT PRIMARY KEY,
            txhash TEXT NOT NULL,
            classification TEXT NOT NULL,
            asset_name TEXT,
            asset_token_id TEXT,
            quantity TEXT,
            payment_asset TEXT,
            gross_amount TEXT,
            marketplace_fee TEXT,
            net_amount TEXT,
            cost_basis TEXT,
            realized_pl TEXT,
            economics_status TEXT NOT NULL,
            economics_version TEXT NOT NULL,
            calculated_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_economic_events_txhash
        ON blockchain_economic_events (
            txhash
        )
        """
    )

    connection.commit()
    connection.close()



def insert_transactions(
    db_path,
    transactions,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = [
        (
            transaction["tx_hash"],
            transaction["timestamp"],
            transaction["block_number"],
            transaction["from_address"],
            transaction["to_address"],
            transaction["method"],
            transaction["status"],
            transaction["value"],
            transaction["fee"],
            transaction["gas_used"],
        )
        for transaction in transactions
    ]

    connection.executemany(
        """
        INSERT OR IGNORE INTO ronin_transactions (
            tx_hash,
            timestamp,
            block_number,
            from_address,
            to_address,
            method,
            status,
            value_raw,
            fee_raw,
            gas_used
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    inserted_count = (
        connection.total_changes
    )

    connection.commit()
    connection.close()

    return inserted_count


def inspect_axieos_database(
    db_path,
):
    database_uri = (
        f"file:{db_path.as_posix()}?mode=ro"
    )

    connection = sqlite3.connect(
        database_uri,
        uri=True,
    )

    cursor = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    )

    tables = [
        row[0]
        for row in cursor.fetchall()
    ]

    connection.close()

    return tables


def validate_economic_events_storage(
    db_path,
    expected_events,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT
            event_key,
            txhash,
            classification,
            asset_name,
            asset_token_id,
            quantity,
            gross_amount,
            marketplace_fee,
            net_amount,
            cost_basis,
            realized_pl,
            economics_status,
            economics_version
        FROM blockchain_economic_events
        """
    ).fetchall()

    connection.close()

    stored_total = len(rows)

    unique_event_keys = len(
        {
            row[0]
            for row in rows
        }
    )

    missing_identifiers = sum(
        1
        for row in rows
        if row[4] is None
    )

    invalid_classifications = sum(
        1
        for row in rows
        if row[2] not in {
            "MARKETPLACE_BUY",
            "MARKETPLACE_SALE",
        }
    )

    realized_rows = [
        row
        for row in rows
        if row[10] is not None
    ]

    realized_formula_errors = 0

    for row in realized_rows:
        net_amount = Decimal(
            row[8]
        )

        cost_basis = Decimal(
            row[9]
        )

        realized_pl = Decimal(
            row[10]
        )

        if (
            net_amount
            - cost_basis
            != realized_pl
        ):
            realized_formula_errors += 1

    axie_1429698 = next(
        (
            event
            for event in expected_events
            if (
                event[
                    "asset_token_id"
                ]
                == "1429698"
                and event[
                    "classification"
                ]
                == "MARKETPLACE_SALE"
            )
        ),
        None,
    )

    regression_passed = (
        axie_1429698 is not None
        and axie_1429698[
            "realized_pl"
        ] is not None
        and Decimal(
            axie_1429698[
                "realized_pl"
            ]
        )
        == Decimal(
            "0.00000555"
        )
    )

    passed = (
        stored_total
        == len(expected_events)
        == unique_event_keys
        and missing_identifiers == 0
        and invalid_classifications == 0
        and realized_formula_errors == 0
        and regression_passed
    )

    return {
        "expected_total": len(
            expected_events
        ),
        "stored_total": stored_total,
        "unique_event_keys": (
            unique_event_keys
        ),
        "missing_identifiers": (
            missing_identifiers
        ),
        "realized_total": len(
            realized_rows
        ),
        "realized_formula_errors": (
            realized_formula_errors
        ),
        "regression_passed": (
            regression_passed
        ),
        "passed": passed,
    }



def initialize_classification_table(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        blockchain_transaction_classifications (
            txhash TEXT PRIMARY KEY,
            classification TEXT NOT NULL,
            confidence TEXT NOT NULL,
            reason TEXT NOT NULL,
            method TEXT,
            classifier_version TEXT NOT NULL,
            classified_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


def store_transaction_classifications(
    db_path,
    transactions,
):
    connection = sqlite3.connect(
        db_path
    )

    stored = 0

    for transaction in transactions:
        result = (
            classify_grouped_transaction(
                transaction
            )
        )

        connection.execute(
            """
            INSERT INTO
                blockchain_transaction_classifications (
                    txhash,
                    classification,
                    confidence,
                    reason,
                    method,
                    classifier_version
                )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(txhash)
            DO UPDATE SET
                classification =
                    excluded.classification,
                confidence =
                    excluded.confidence,
                reason =
                    excluded.reason,
                method =
                    excluded.method,
                classifier_version =
                    excluded.classifier_version,
                classified_at =
                    CURRENT_TIMESTAMP
            """,
            (
                transaction["txhash"],
                result["classification"],
                result["confidence"],
                result["reason"],
                transaction.get("method"),
                CLASSIFIER_VERSION,
            ),
        )

        stored += 1

    connection.commit()
    connection.close()

    return stored




def inspect_blockchain_transactions(
    db_path,
):
    database_uri = (
        f"file:{db_path.as_posix()}?mode=ro"
    )

    connection = sqlite3.connect(
        database_uri,
        uri=True,
    )

    columns = connection.execute(
        """
        PRAGMA table_info(
            blockchain_transactions
        )
        """
    ).fetchall()

    indexes = connection.execute(
        """
        PRAGMA index_list(
            blockchain_transactions
        )
        """
    ).fetchall()

    row_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_transactions
        """
    ).fetchone()[0]

    connection.close()

    return {
        "columns": columns,
        "indexes": indexes,
        "row_count": row_count,
    }


def run_blockchain_table_inspection():
    result = inspect_blockchain_transactions(
        AXIEOS_DB_PATH
    )

    print(
        "\nBLOCKCHAIN TRANSACTIONS INSPECTION"
    )

    print(
        "Rows:",
        result["row_count"],
    )

    print("\nColumns:")

    for column in result["columns"]:
        print(column)

    print("\nIndexes:")

    for index in result["indexes"]:
        print(index)


def inspect_blockchain_table_details(
    db_path,
):
    database_uri = (
        f"file:{db_path.as_posix()}?mode=ro"
    )

    connection = sqlite3.connect(
        database_uri,
        uri=True,
    )

    indexes = connection.execute(
        """
        PRAGMA index_list(
            blockchain_transactions
        )
        """
    ).fetchall()

    index_details = {}

    for index in indexes:
        index_name = index[1]

        columns = connection.execute(
            f"""
            PRAGMA index_info(
                {index_name}
            )
            """
        ).fetchall()

        index_details[index_name] = columns

    sample_rows = connection.execute(
        """
        SELECT
            id,
            txhash,
            blockno,
            datetime,
            from_address,
            to_address,
            method,
            value_in,
            value_out,
            txn_fee_ron,
            status,
            source_row_hash
        FROM blockchain_transactions
        ORDER BY id DESC
        LIMIT 3
        """
    ).fetchall()

    connection.close()

    return {
        "indexes": indexes,
        "index_details": index_details,
        "sample_rows": sample_rows,
    }


def run_blockchain_detail_inspection():
    result = (
        inspect_blockchain_table_details(
            AXIEOS_DB_PATH
        )
    )

    print(
        "\nBLOCKCHAIN TABLE DETAILS"
    )

    print("\nINDEX DETAILS")

    for index in result["indexes"]:
        index_name = index[1]
        unique = bool(index[2])

        print(
            f"{index_name} | "
            f"unique={unique} | "
            f"columns="
            f"{result['index_details'][index_name]}"
        )

    print("\nSAMPLE ROWS")

    for row in result["sample_rows"]:
        print(row)


def initialize_raw_api_table(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ronin_api_transactions_raw (
            tx_hash TEXT PRIMARY KEY,
            timestamp TEXT,
            block_number INTEGER,
            from_address TEXT,
            to_address TEXT,
            method TEXT,
            status TEXT,
            value_raw TEXT,
            fee_raw TEXT,
            gas_used INTEGER,
            imported_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


def insert_raw_api_transactions(
    db_path,
    transactions,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = [
        (
            transaction["tx_hash"],
            transaction["timestamp"],
            transaction["block_number"],
            transaction["from_address"],
            transaction["to_address"],
            transaction["method"],
            transaction["status"],
            transaction["value"],
            transaction["fee"],
            transaction["gas_used"],
        )
        for transaction in transactions
    ]

    connection.executemany(
        """
        INSERT OR IGNORE INTO ronin_api_transactions_raw (
            tx_hash,
            timestamp,
            block_number,
            from_address,
            to_address,
            method,
            status,
            value_raw,
            fee_raw,
            gas_used
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    inserted_count = (
        connection.total_changes
    )

    connection.commit()
    connection.close()

    return inserted_count


def run_transaction_structure_test():
    response = fetch_json(
        RONIN_TRANSACTIONS_URL
    )

    transactions = response.get(
        "items",
        [],
    )

    print(
        "\nRONIN TRANSACTION STRUCTURE"
    )

    if not transactions:
        print("No transactions found")
        return

    transaction = transactions[0]

    print("\nAVAILABLE FIELDS")

    for key in sorted(
        transaction.keys()
    ):
        print(key)

    print(
        "\nTRANSACTION TYPES:"
    )

    print(
        transaction.get(
            "transaction_types"
        )
    )

    print(
        "\nDECODED INPUT:"
    )

    print(
        transaction.get(
            "decoded_input"
        )
    )

    print(
        "\nTOKEN TRANSFERS:"
    )

    print(
        transaction.get(
            "token_transfers"
        )
    )


def run_transfer_availability_test():
    response = fetch_json(
        RONIN_TRANSACTIONS_URL
    )

    transactions = response.get(
        "items",
        [],
    )

    with_token_transfers = 0
    with_actions = 0
    overflow_count = 0
    token_transfer_type = 0

    example_with_transfers = None
    example_with_actions = None

    for transaction in transactions:
        transaction_types = (
            transaction.get(
                "transaction_types"
            )
            or []
        )

        token_transfers = (
            transaction.get(
                "token_transfers"
            )
        )

        actions = transaction.get(
            "actions"
        )

        overflow = transaction.get(
            "token_transfers_overflow"
        )

        if "token_transfer" in transaction_types:
            token_transfer_type += 1

        if token_transfers:
            with_token_transfers += 1

            if example_with_transfers is None:
                example_with_transfers = (
                    transaction
                )

        if actions:
            with_actions += 1

            if example_with_actions is None:
                example_with_actions = (
                    transaction
                )

        if overflow:
            overflow_count += 1

    print(
        "\nRONIN TRANSFER AVAILABILITY"
    )

    print(
        "Transactions checked:",
        len(transactions),
    )

    print(
        "Marked token_transfer:",
        token_transfer_type,
    )

    print(
        "With embedded token_transfers:",
        with_token_transfers,
    )

    print(
        "With actions:",
        with_actions,
    )

    print(
        "Transfer overflow:",
        overflow_count,
    )

    if example_with_transfers:
        print(
            "\nEXAMPLE TOKEN TRANSFERS"
        )

        print(
            example_with_transfers.get(
                "token_transfers"
            )
        )

    if example_with_actions:
        print(
            "\nEXAMPLE ACTIONS"
        )

        print(
            example_with_actions.get(
                "actions"
            )
        )


def extract_transfer_address(
    address_data,
):
    if isinstance(address_data, dict):
        return address_data.get("hash")

    return address_data


def initialize_raw_transfer_table(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ronin_token_transfers_raw (
            transfer_key TEXT PRIMARY KEY,
            tx_hash TEXT NOT NULL,
            log_index INTEGER,
            timestamp TEXT,
            block_number INTEGER,
            from_address TEXT,
            to_address TEXT,
            token_type TEXT,
            token_symbol TEXT,
            token_name TEXT,
            token_address TEXT,
            token_id TEXT,
            amount_raw TEXT,
            decimals INTEGER,
            imported_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_ronin_transfers_tx_hash
        ON ronin_token_transfers_raw(
            tx_hash
        )
        """
    )

    connection.commit()
    connection.close()


def insert_raw_token_transfers(
    db_path,
    transfers,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = [
        (
            transfer["transfer_key"],
            transfer["tx_hash"],
            transfer["log_index"],
            transfer["timestamp"],
            transfer["block_number"],
            transfer["from_address"],
            transfer["to_address"],
            transfer["token_type"],
            transfer["token_symbol"],
            transfer["token_name"],
            transfer["token_address"],
            transfer["token_id"],
            transfer["amount_raw"],
            transfer["decimals"],
        )
        for transfer in transfers
    ]

    connection.executemany(
        """
        INSERT OR IGNORE INTO ronin_token_transfers_raw (
            transfer_key,
            tx_hash,
            log_index,
            timestamp,
            block_number,
            from_address,
            to_address,
            token_type,
            token_symbol,
            token_name,
            token_address,
            token_id,
            amount_raw,
            decimals
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    inserted_count = (
        connection.total_changes
    )

    connection.commit()
    connection.close()

    return inserted_count




def backup_axieos_database(
    source_path,
    backup_path,
):
    backup_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source_path,
        backup_path,
    )

    return backup_path


def normalize_address(
    address,
):
    if address is None:
        return None

    return address.lower()


def classify_transfer_direction(
    transfer,
):
    wallet = normalize_address(
        RONIN_WALLET_ADDRESS
    )

    from_address = normalize_address(
        transfer["from_address"]
    )

    to_address = normalize_address(
        transfer["to_address"]
    )

    if (
        from_address == wallet
        and to_address == wallet
    ):
        return "SELF"

    if to_address == wallet:
        return "IN"

    if from_address == wallet:
        return "OUT"

    return "OTHER"


def get_human_amount(
    transfer,
):
    amount_raw = transfer.get(
        "amount_raw"
    )

    decimals = transfer.get(
        "decimals"
    )

    if amount_raw is None:
        return None

    if decimals is None:
        return str(amount_raw)

    amount = (
        Decimal(str(amount_raw))
        / (
            Decimal(10)
            ** int(decimals)
        )
    )

    return format(
        amount,
        "f",
    )


def build_accounting_transfer_preview(
    transfer,
):
    direction = classify_transfer_direction(
        transfer
    )

    return {
        "tx_hash": transfer[
            "tx_hash"
        ],
        "log_index": transfer[
            "log_index"
        ],
        "direction": direction,
        "token_type": transfer[
            "token_type"
        ],
        "token_symbol": transfer[
            "token_symbol"
        ],
        "token_id": transfer[
            "token_id"
        ],
        "amount": get_human_amount(
            transfer
        ),
        "from_address": transfer[
            "from_address"
        ],
        "to_address": transfer[
            "to_address"
        ],
    }


def validate_classification_taxonomy():
    description_keys = set(
        CLASSIFICATION_DESCRIPTIONS
    )

    return (
        TRANSACTION_CLASSIFICATIONS
        == description_keys
    )


def group_ledger_rows_by_txhash(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT
            txhash,
            blockno,
            datetime,
            from_address,
            to_address,
            method,
            token_collectibles,
            value_in,
            value_out,
            status
        FROM blockchain_transactions
        ORDER BY
            blockno,
            id
        """
    ).fetchall()

    connection.close()

    grouped = {}

    for row in rows:
        txhash = row[0]

        if txhash not in grouped:
            grouped[txhash] = {
                "txhash": txhash,
                "blockno": row[1],
                "datetime": row[2],
                "method": row[5],
                "status": row[9],
                "movements": [],
            }

        grouped[txhash][
            "movements"
        ].append(
            {
                "from_address": row[3],
                "to_address": row[4],
                "asset": row[6],
                "value_in": row[7],
                "value_out": row[8],
            }
        )

    return list(
        grouped.values()
    )










def build_empty_economic_event(
    txhash,
    classification,
):
    return {
        "event_key": txhash,
        "txhash": txhash,
        "classification": classification,
        "asset_name": None,
        "asset_token_id": None,
        "quantity": None,
        "payment_asset": None,
        "gross_amount": None,
        "marketplace_fee": None,
        "net_amount": None,
        "cost_basis": None,
        "realized_pl": None,
        "economics_status": "UNPROCESSED",
        "economics_version": ECONOMICS_VERSION,
    }


def extract_marketplace_buy_economics(
    transaction,
):
    classification_result = (
        classify_grouped_transaction(
            transaction
        )
    )

    if (
        classification_result[
            "classification"
        ]
        != "MARKETPLACE_BUY"
    ):
        return None

    weth_paid = Decimal("0")
    purchased_movements = []

    for movement in transaction[
        "movements"
    ]:
        asset = movement.get(
            "asset"
        )

        direction = (
            get_movement_direction(
                movement
            )
        )

        if (
            asset == "Ronin Wrapped Ether"
            and direction == "OUT"
        ):
            weth_paid += Decimal(
                str(
                    movement.get(
                        "value_out",
                        "0",
                    )
                )
            )

        elif (
            asset != "Ronin Wrapped Ether"
            and direction == "IN"
        ):
            purchased_movements.append(
                movement
            )

    event = build_empty_economic_event(
        txhash=transaction["txhash"],
        classification=(
            "MARKETPLACE_BUY"
        ),
    )

    if (
        weth_paid <= 0
        or not purchased_movements
    ):
        event[
            "economics_status"
        ] = "REVIEW"

        return event

    asset_names = {
        movement.get("asset")
        for movement
        in purchased_movements
    }

    if len(asset_names) != 1:
        event[
            "economics_status"
        ] = "REVIEW"

        return event

    asset_name = next(
        iter(asset_names)
    )

    quantity = sum(
        Decimal(
            str(
                movement.get(
                    "value_in",
                    "0",
                )
            )
        )
        for movement
        in purchased_movements
    )

    event["asset_name"] = asset_name
    event["quantity"] = str(
        quantity
    )
    event[
        "payment_asset"
    ] = "Ronin Wrapped Ether"
    event[
        "gross_amount"
    ] = str(
        weth_paid
    )
    event[
        "economics_status"
    ] = "BUY_EXTRACTED"

    return event



def extract_marketplace_sale_economics(
    transaction,
):
    classification_result = (
        classify_grouped_transaction(
            transaction
        )
    )

    if (
        classification_result[
            "classification"
        ]
        != "MARKETPLACE_SALE"
    ):
        return None

    weth_received = Decimal("0")
    sold_movements = []

    for movement in transaction[
        "movements"
    ]:
        asset = movement.get(
            "asset"
        )

        direction = (
            get_movement_direction(
                movement
            )
        )

        if (
            asset == "Ronin Wrapped Ether"
            and direction == "IN"
        ):
            weth_received += Decimal(
                str(
                    movement.get(
                        "value_in",
                        "0",
                    )
                )
            )

        elif (
            asset != "Ronin Wrapped Ether"
            and direction == "OUT"
        ):
            sold_movements.append(
                movement
            )

    event = build_empty_economic_event(
        txhash=transaction["txhash"],
        classification=(
            "MARKETPLACE_SALE"
        ),
    )

    if (
        weth_received <= 0
        or not sold_movements
    ):
        event[
            "economics_status"
        ] = "REVIEW"

        return event

    asset_names = {
        movement.get("asset")
        for movement
        in sold_movements
    }

    if len(asset_names) != 1:
        event[
            "economics_status"
        ] = "REVIEW"

        return event

    asset_name = next(
        iter(asset_names)
    )

    quantity = sum(
        Decimal(
            str(
                movement.get(
                    "value_out",
                    "0",
                )
            )
        )
        for movement
        in sold_movements
    )

    event[
        "asset_name"
    ] = asset_name

    event[
        "quantity"
    ] = str(
        quantity
    )

    event[
        "payment_asset"
    ] = "Ronin Wrapped Ether"

    event[
        "net_amount"
    ] = str(
        weth_received
    )

    event[
        "economics_status"
    ] = "SALE_NET_EXTRACTED"

    return event


def build_marketplace_economic_events(
    transactions,
):
    events = []

    for transaction in transactions:
        result = (
            classify_grouped_transaction(
                transaction
            )
        )

        classification = result[
            "classification"
        ]

        if classification == "MARKETPLACE_BUY":
            event = (
                extract_marketplace_buy_economics(
                    transaction
                )
            )

        elif classification == "MARKETPLACE_SALE":
            event = (
                extract_marketplace_sale_economics(
                    transaction
                )
            )

            event = (
                apply_marketplace_sale_fee(
                    event
                )
            )

        else:
            continue

        if event is not None:
            event = (
                enrich_economic_event_identifier(
                    AXIEOS_DB_PATH,
                    event,
                )
            )

            events.append(event)
    return events


def store_economic_events(
    db_path,
    events,
):
    connection = sqlite3.connect(
        db_path
    )

    processed = 0

    for event in events:
        connection.execute(
            """
            INSERT INTO blockchain_economic_events (
                event_key,
                txhash,
                classification,
                asset_name,
                asset_token_id,
                quantity,
                payment_asset,
                gross_amount,
                marketplace_fee,
                net_amount,
                cost_basis,
                realized_pl,
                economics_status,
                economics_version
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(event_key)
            DO UPDATE SET
                txhash =
                    excluded.txhash,
                classification =
                    excluded.classification,
                asset_name =
                    excluded.asset_name,
                asset_token_id =
                    excluded.asset_token_id,
                quantity =
                    excluded.quantity,
                payment_asset =
                    excluded.payment_asset,
                gross_amount =
                    excluded.gross_amount,
                marketplace_fee =
                    excluded.marketplace_fee,
                net_amount =
                    excluded.net_amount,
                cost_basis =
                    excluded.cost_basis,
                realized_pl =
                    excluded.realized_pl,
                economics_status =
                    excluded.economics_status,
                economics_version =
                    excluded.economics_version,
                calculated_at =
                    CURRENT_TIMESTAMP
            """,
            (
                event["event_key"],
                event["txhash"],
                event["classification"],
                event["asset_name"],
                event["asset_token_id"],
                event["quantity"],
                event["payment_asset"],
                event["gross_amount"],
                event["marketplace_fee"],
                event["net_amount"],
                event["cost_basis"],
                event["realized_pl"],
                event["economics_status"],
                event["economics_version"],
            ),
        )

        processed += 1

    connection.commit()
    connection.close()

    return processed


def match_axie_acquisition_costs(
    events,
):
    owned_axies = {}

    for event in events:
        if (
            event["asset_name"] != "Axie"
            or event["asset_token_id"] is None
        ):
            if (
                event["classification"]
                == "MARKETPLACE_SALE"
                and event["asset_name"]
                != "Axie"
            ):
                event[
                    "economics_status"
                ] = (
                    "COST_BASIS_DEFERRED_INVENTORY"
                )

            continue

        token_id = event[
            "asset_token_id"
        ]

        if (
            event["classification"]
            == "MARKETPLACE_BUY"
        ):
            if event["gross_amount"] is not None:
                owned_axies[
                    token_id
                ] = event[
                    "gross_amount"
                ]

        elif (
            event["classification"]
            == "MARKETPLACE_SALE"
        ):
            acquisition_cost = (
                owned_axies.get(
                    token_id
                )
            )

            if acquisition_cost is None:
                event[
                    "economics_status"
                ] = (
                    "UNKNOWN_COST_BASIS"
                )

                continue

            event[
                "cost_basis"
            ] = acquisition_cost

            event[
                "economics_status"
            ] = (
                "COST_BASIS_MATCHED"
            )

            del owned_axies[
                token_id
            ]

    return events


def calculate_realized_pl(
    events,
):
    for event in events:
        if (
            event["classification"]
            != "MARKETPLACE_SALE"
        ):
            continue

        if (
            event["asset_name"] != "Axie"
        ):
            continue

        if (
            event["cost_basis"] is None
            or event["net_amount"] is None
        ):
            continue

        cost_basis = Decimal(
            event["cost_basis"]
        )

        net_proceeds = Decimal(
            event["net_amount"]
        )

        realized_pl = (
            net_proceeds
            - cost_basis
        )

        event[
            "realized_pl"
        ] = decimal_to_plain_string(
            realized_pl
        )

        event[
            "economics_status"
        ] = "REALIZED_PL_COMPLETE"

    return events





def find_event_asset_token_ids(
    db_path,
    event,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT
            from_address,
            to_address,
            token_name,
            token_id
        FROM ronin_token_transfers_raw
        WHERE tx_hash = ?
        ORDER BY log_index
        """,
        (
            event["txhash"],
        ),
    ).fetchall()

    connection.close()

    token_ids = []

    for (
        from_address,
        to_address,
        token_name,
        token_id,
    ) in rows:
        if token_id is None:
            continue

        if (
            token_name
            == "Ronin Wrapped Ether"
        ):
            continue

        from_normalized = (
            normalize_address(
                from_address
            )
        )

        to_normalized = (
            normalize_address(
                to_address
            )
        )

        wallet_normalized = (
            normalize_address(
                RONIN_WALLET_ADDRESS
            )
        )

        if (
            event["classification"]
            == "MARKETPLACE_BUY"
            and to_normalized
            == wallet_normalized
        ):
            token_ids.append(
                str(token_id)
            )

        elif (
            event["classification"]
            == "MARKETPLACE_SALE"
            and from_normalized
            == wallet_normalized
        ):
            token_ids.append(
                str(token_id)
            )

    return list(
        dict.fromkeys(
            token_ids
        )
    )


def enrich_economic_event_identifier(
    db_path,
    event,
):
    token_ids = (
        find_event_asset_token_ids(
            db_path,
            event,
        )
    )

    if len(token_ids) == 1:
        event[
            "asset_token_id"
        ] = token_ids[0]

        return event

    if len(token_ids) > 1:
        event[
            "asset_token_id"
        ] = ",".join(
            token_ids
        )

        event[
            "economics_status"
        ] = (
            "REVIEW_MULTIPLE_TOKEN_IDS"
        )

    return event




def apply_marketplace_sale_fee(
    event,
):
    if event is None:
        return None

    if (
        event["classification"]
        != "MARKETPLACE_SALE"
    ):
        return event

    if event["net_amount"] is None:
        event[
            "economics_status"
        ] = "REVIEW"

        return event

    net_amount = Decimal(
        event["net_amount"]
    )

    net_rate = (
        Decimal("1")
        - MARKETPLACE_SELLER_FEE_RATE
    )

    if net_amount <= 0:
        event[
            "economics_status"
        ] = "REVIEW"

        return event

    gross_amount = (
        net_amount
        / net_rate
    )

    marketplace_fee = (
        gross_amount
        - net_amount
    )

    event[
        "gross_amount"
    ] = decimal_to_plain_string(
        gross_amount
    )

    event[
        "marketplace_fee"
    ] = decimal_to_plain_string(
        marketplace_fee
    )

    event[
        "economics_status"
    ] = "SALE_ECONOMICS_COMPLETE"

    return event







def validate_economic_event(
    event,
):
    return (
        set(event.keys())
        == ECONOMIC_EVENT_FIELDS
    )






def run_ronin_sync_v03(
    max_pages=3,
):
    run_ronin_sync_v02(
        max_pages=max_pages
    )

    initialize_economic_events_table(
        AXIEOS_DB_PATH
    )

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    events = (
        build_marketplace_economic_events(
            transactions
        )
    )

    events = (
        match_axie_acquisition_costs(
            events
        )
    )

    events = (
        calculate_realized_pl(
            events
        )
    )

    processed = store_economic_events(
        AXIEOS_DB_PATH,
        events,
    )

    validation = (
        validate_economic_events_storage(
            AXIEOS_DB_PATH,
            events,
        )
    )

    matched_pl = [
        event
        for event in events
        if event[
            "realized_pl"
        ] is not None
    ]

    unknown_cost_basis = [
        event
        for event in events
        if event[
            "economics_status"
        ]
        == "UNKNOWN_COST_BASIS"
    ]

    deferred_inventory = [
        event
        for event in events
        if event[
            "economics_status"
        ]
        == (
            "COST_BASIS_DEFERRED_INVENTORY"
        )
    ]

    total_realized_pl = sum(
        (
            Decimal(
                event[
                    "realized_pl"
                ]
            )
            for event in matched_pl
        ),
        Decimal("0"),
    )

    print(
        "\nRONIN TRANSACTION ECONOMICS"
    )

    print(
        "Economic events processed:",
        processed,
    )

    print(
        "Economic events stored:",
        validation["stored_total"],
    )

    print(
        "Unique event keys:",
        validation[
            "unique_event_keys"
        ],
    )

    print(
        "Missing asset identifiers:",
        validation[
            "missing_identifiers"
        ],
    )

    print(
        "Realized Axie trades:",
        validation["realized_total"],
    )

    print(
        "Unknown Axie cost basis:",
        len(
            unknown_cost_basis
        ),
    )

    print(
        "Inventory cost basis deferred:",
        len(
            deferred_inventory
        ),
    )

    print(
        "Realized formula errors:",
        validation[
            "realized_formula_errors"
        ],
    )

    print(
        "Total realized P/L:",
        decimal_to_plain_string(
            total_realized_pl
        ),
        "WETH",
    )

    print(
        "Axie #1429698 regression:",
        (
            "PASS"
            if validation[
                "regression_passed"
            ]
            else "FAIL"
        ),
    )

    print(
        "Economics version:",
        ECONOMICS_VERSION,
    )

    print(
        "Validation:",
        (
            "PASS"
            if validation["passed"]
            else "FAIL"
        ),
    )












def run_sample_test():
    response = load_transaction_response(
        SAMPLE_PATH
    )

    transactions = response.get(
        "items",
        [],
    )

    print("RONIN API SAMPLE")
    print(
        "Transactions:",
        len(transactions),
    )

    if transactions:
        first_transaction = transactions[0]

        print(
            "First tx hash:",
            first_transaction.get("hash"),
        )

        print(
            "Timestamp:",
            first_transaction.get("timestamp"),
        )

        print(
            "Block:",
            first_transaction.get(
                "block_number"
            ),
        )

        print(
            "Status:",
            first_transaction.get("status"),
        )

        normalized = normalize_transaction(
            first_transaction
        )

        print("\nNORMALIZED TRANSACTION")

        for key, value in normalized.items():
            print(
                f"{key}: {value}"
            )

    normalized_transactions = (
        normalize_transactions(
            transactions
        )
    )

    tx_hashes = [
        transaction["tx_hash"]
        for transaction
        in normalized_transactions
    ]

    unique_tx_hashes = set(
        tx_hashes
    )

    duplicate_count = (
        len(tx_hashes)
        - len(unique_tx_hashes)
    )

    print("\nNORMALIZATION SUMMARY")

    print(
        "Normalized transactions:",
        len(normalized_transactions),
    )

    print(
        "Unique tx hashes:",
        len(unique_tx_hashes),
    )

    print(
        "Duplicate tx hashes:",
        duplicate_count,
    )

    overlapping_transactions = (
        normalized_transactions
        + normalized_transactions[:2]
    )

    deduplicated_transactions = (
        deduplicate_transactions(
            overlapping_transactions
        )
    )

    print("\nDEDUPLICATION TEST")

    print(
        "Before deduplication:",
        len(overlapping_transactions),
    )

    print(
        "After deduplication:",
        len(deduplicated_transactions),
    )

    print(
        "Duplicates removed:",
        len(overlapping_transactions)
        - len(deduplicated_transactions),
    )

    next_page_params = response.get(
        "next_page_params"
    )

    print("\nPAGINATION")

    print(
        "Has next page:",
        next_page_params is not None,
    )

    print(
        "Next page params:",
        next_page_params,
    )

    pagination_query = (
        build_pagination_query(
            next_page_params
        )
    )

    print("\nPAGINATION QUERY")

    print(
        pagination_query
    )


def fetch_next_page(
    response,
):
    next_page_params = response.get(
        "next_page_params"
    )

    if not next_page_params:
        return None

    return fetch_json(
        RONIN_TRANSACTIONS_URL,
        params=next_page_params,
    )


def fetch_transaction_pages(
    max_pages=3,
):
    pages = []

    response = fetch_json(
        RONIN_TRANSACTIONS_URL
    )

    pages.append(response)

    while len(pages) < max_pages:
        response = fetch_next_page(
            response
        )

        if response is None:
            break

        pages.append(response)

    return pages



def fetch_normalized_transactions(
    max_pages=3,
):
    pages = fetch_transaction_pages(
        max_pages=max_pages
    )

    transactions = []

    for page in pages:
        transactions.extend(
            page.get(
                "items",
                [],
            )
        )

    normalized_transactions = (
        normalize_transactions(
            transactions
        )
    )

    deduplicated_transactions = (
        deduplicate_transactions(
            normalized_transactions
        )
    )

    return deduplicated_transactions


def normalize_token_transfer(
    transfer,
):
    token = transfer.get("token") or {}
    total = transfer.get("total") or {}

    token_type = transfer.get(
        "token_type"
    )

    token_id = total.get(
        "token_id"
    )

    decimals = total.get(
        "decimals"
    )

    if decimals is None:
        decimals = token.get(
            "decimals"
        )

    if token_type == "ERC-721":
        amount_raw = "1"

    else:
        amount_raw = total.get(
            "value"
        )

    return {
        "transfer_key": (
            f"{transfer.get('transaction_hash')}:"
            f"{transfer.get('log_index')}:"
            f"{token.get('address_hash')}:"
            f"{token_id or ''}"
        ),
        "tx_hash": transfer.get(
            "transaction_hash"
        ),
        "log_index": transfer.get(
            "log_index"
        ),
        "timestamp": transfer.get(
            "timestamp"
        ),
        "block_number": transfer.get(
            "block_number"
        ),
        "from_address": (
            extract_transfer_address(
                transfer.get("from")
            )
        ),
        "to_address": (
            extract_transfer_address(
                transfer.get("to")
            )
        ),
        "token_type": token_type,
        "token_symbol": token.get(
            "symbol"
        ),
        "token_name": token.get(
            "name"
        ),
        "token_address": token.get(
            "address_hash"
        ),
        "token_id": token_id,
        "amount_raw": amount_raw,
        "decimals": decimals,
    }



def fetch_normalized_token_transfers(
    max_pages=3,
):
    pages = fetch_token_transfer_pages(
        max_pages=max_pages
    )

    raw_transfers = []

    for page in pages:
        raw_transfers.extend(
            page.get(
                "items",
                [],
            )
        )

    normalized = normalize_token_transfers(
        raw_transfers
    )

    unique_transfers = {}

    for transfer in normalized:
        unique_transfers[
            transfer["transfer_key"]
        ] = transfer

    return list(
        unique_transfers.values()
    )



def normalize_token_transfers(
    transfers,
):
    return [
        normalize_token_transfer(
            transfer
        )
        for transfer in transfers
    ]


def run_transfer_key_collision_test():
    response = fetch_json(
        RONIN_TOKEN_TRANSFERS_URL
    )

    transfers = normalize_token_transfers(
        response.get(
            "items",
            [],
        )
    )

    grouped = {}

    for transfer in transfers:
        transfer_key = transfer[
            "transfer_key"
        ]

        grouped.setdefault(
            transfer_key,
            [],
        ).append(
            transfer
        )

    collisions = {
        key: items
        for key, items in grouped.items()
        if len(items) > 1
    }

    print(
        "\nTRANSFER KEY COLLISIONS"
    )

    print(
        "Transfers:",
        len(transfers),
    )

    print(
        "Unique keys:",
        len(grouped),
    )

    print(
        "Collision groups:",
        len(collisions),
    )

    print(
        "Rows involved:",
        sum(
            len(items)
            for items
            in collisions.values()
        ),
    )

    for key, items in collisions.items():
        print(
            f"\nKEY: {key}"
        )

        for item in items:
            print(
                {
                    "token_type": item[
                        "token_type"
                    ],
                    "token_symbol": item[
                        "token_symbol"
                    ],
                    "token_address": item[
                        "token_address"
                    ],
                    "token_id": item[
                        "token_id"
                    ],
                    "amount_raw": item[
                        "amount_raw"
                    ],
                    "from": item[
                        "from_address"
                    ],
                    "to": item[
                        "to_address"
                    ],
                }
            )


def fetch_next_token_transfer_page(
    response,
):
    next_page_params = response.get(
        "next_page_params"
    )

    if not next_page_params:
        return None

    return fetch_json(
        RONIN_TOKEN_TRANSFERS_URL,
        params=next_page_params,
    )


def fetch_token_transfer_pages(
    max_pages=3,
):
    pages = []

    response = fetch_json(
        RONIN_TOKEN_TRANSFERS_URL
    )

    pages.append(response)

    while len(pages) < max_pages:
        response = (
            fetch_next_token_transfer_page(
                response
            )
        )

        if response is None:
            break

        pages.append(response)

    return pages


def inspect_existing_ledger_format(
    db_path,
):
    database_uri = (
        f"file:{db_path.as_posix()}?mode=ro"
    )

    connection = sqlite3.connect(
        database_uri,
        uri=True,
    )

    rows = connection.execute(
        """
        SELECT
            id,
            txhash,
            method,
            token_collectibles,
            value_in,
            value_out,
            txn_fee_ron
        FROM blockchain_transactions
        ORDER BY id DESC
        LIMIT 15
        """
    ).fetchall()

    connection.close()

    return rows


def run_ledger_convention_test():
    database_uri = (
        f"file:{AXIEOS_DB_PATH.as_posix()}?mode=ro"
    )

    connection = sqlite3.connect(
        database_uri,
        uri=True,
    )

    asset_names = connection.execute(
        """
        SELECT DISTINCT token_collectibles
        FROM blockchain_transactions
        WHERE token_collectibles IS NOT NULL
        ORDER BY token_collectibles
        """
    ).fetchall()

    fee_rows = connection.execute(
        """
        SELECT
            id,
            txhash,
            token_collectibles,
            txn_fee_ron
        FROM blockchain_transactions
        WHERE CAST(txn_fee_ron AS REAL) != 0
        ORDER BY id
        """
    ).fetchall()

    connection.close()

    print(
        "\nLEDGER CONVENTIONS"
    )

    print("\nASSETS")

    for row in asset_names:
        print(row[0])

    print(
        "\nNONZERO FEE ROWS:",
        len(fee_rows),
    )

    for row in fee_rows:
        print(row)


def convert_api_timestamp(
    timestamp,
):
    if timestamp is None:
        return None, None

    parsed = datetime.fromisoformat(
        timestamp.replace(
            "Z",
            "+00:00",
        )
    )

    unix_timestamp = int(
        parsed.timestamp()
    )

    ledger_datetime = (
        parsed.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    return (
        unix_timestamp,
        ledger_datetime,
    )


def build_api_source_row_hash(
    transfer,
):
    source_text = (
        "ronin_api_transfer|"
        f"{transfer['transfer_key']}"
    )

    return hashlib.sha256(
        source_text.encode("utf-8")
    ).hexdigest()


def build_ledger_row_from_transfer(
    transfer,
    method=None,
):
    direction = classify_transfer_direction(
        transfer
    )

    amount = get_human_amount(
        transfer
    )

    unix_timestamp, ledger_datetime = (
        convert_api_timestamp(
            transfer["timestamp"]
        )
    )

    if direction == "IN":
        value_in = amount
        value_out = "0.0"

    elif direction == "OUT":
        value_in = "0.0"
        value_out = amount

    else:
        value_in = "0.0"
        value_out = "0.0"

    return {
        "txhash": transfer["tx_hash"],
        "blockno": transfer[
            "block_number"
        ],
        "unixtimestamp": unix_timestamp,
        "datetime": ledger_datetime,
        "from_address": transfer[
            "from_address"
        ],
        "to_address": transfer[
            "to_address"
        ],
        "method": method,
        "token_collectibles": transfer[
            "token_name"
        ],
        "value_in": value_in,
        "value_out": value_out,
        "txn_fee_ron": "0.0",
        "status": "Success",
        "source_row_hash": (
            build_api_source_row_hash(
                transfer
            )
        ),
    }


def validate_economic_event(
    event,
):
    return (
        set(event.keys())
        == ECONOMIC_EVENT_FIELDS
    )





def run_ledger_date_overlap_test():
    database_uri = (
        f"file:{AXIEOS_DB_PATH.as_posix()}?mode=ro"
    )

    connection = sqlite3.connect(
        database_uri,
        uri=True,
    )

    ledger_range = connection.execute(
        """
        SELECT
            MIN(datetime),
            MAX(datetime),
            COUNT(*)
        FROM blockchain_transactions
        """
    ).fetchone()

    staging_range = connection.execute(
        """
        SELECT
            MIN(timestamp),
            MAX(timestamp),
            COUNT(*)
        FROM ronin_token_transfers_raw
        """
    ).fetchone()

    connection.close()

    print(
        "\nLEDGER DATE OVERLAP CHECK"
    )

    print(
        "Existing ledger rows:",
        ledger_range[2],
    )

    print(
        "Existing ledger earliest:",
        ledger_range[0],
    )

    print(
        "Existing ledger latest:",
        ledger_range[1],
    )

    print(
        "Staged transfer rows:",
        staging_range[2],
    )

    print(
        "Staged transfer earliest:",
        staging_range[0],
    )

    print(
        "Staged transfer latest:",
        staging_range[1],
    )


def load_staged_transfers(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT
            t.transfer_key,
            t.tx_hash,
            t.log_index,
            t.timestamp,
            t.block_number,
            t.from_address,
            t.to_address,
            t.token_type,
            t.token_symbol,
            t.token_name,
            t.token_address,
            t.token_id,
            t.amount_raw,
            t.decimals,
            x.method
        FROM ronin_token_transfers_raw AS t
        LEFT JOIN ronin_api_transactions_raw AS x
            ON t.tx_hash = x.tx_hash
        ORDER BY
            t.block_number,
            t.log_index
        """
    ).fetchall()

    connection.close()

    transfers = []

    for row in rows:
        transfers.append(
            {
                "transfer_key": row[0],
                "tx_hash": row[1],
                "log_index": row[2],
                "timestamp": row[3],
                "block_number": row[4],
                "from_address": row[5],
                "to_address": row[6],
                "token_type": row[7],
                "token_symbol": row[8],
                "token_name": row[9],
                "token_address": row[10],
                "token_id": row[11],
                "amount_raw": row[12],
                "decimals": row[13],
                "method": row[14],
            }
        )

    return transfers


def insert_ledger_rows(
    db_path,
    ledger_rows,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = [
        (
            row["txhash"],
            row["blockno"],
            row["unixtimestamp"],
            row["datetime"],
            row["from_address"],
            row["to_address"],
            row["method"],
            row["token_collectibles"],
            row["value_in"],
            row["value_out"],
            row["txn_fee_ron"],
            row["status"],
            row["source_row_hash"],
        )
        for row in ledger_rows
    ]

    connection.executemany(
        """
        INSERT OR IGNORE INTO blockchain_transactions (
            txhash,
            blockno,
            unixtimestamp,
            datetime,
            from_address,
            to_address,
            method,
            token_collectibles,
            value_in,
            value_out,
            txn_fee_ron,
            status,
            source_row_hash
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    inserted_count = (
        connection.total_changes
    )

    connection.commit()
    connection.close()

    return inserted_count


def run_production_ledger_insert_test():
    staged_transfers = (
        load_staged_transfers(
            AXIEOS_DB_PATH
        )
    )

    ledger_rows = []
    skipped = 0

    for transfer in staged_transfers:
        direction = (
            classify_transfer_direction(
                transfer
            )
        )

        if direction not in {
            "IN",
            "OUT",
        }:
            skipped += 1
            continue

        ledger_rows.append(
            build_ledger_row_from_transfer(
                transfer,
                method=transfer.get(
                    "method"
                ),
            )
        )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    before_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_transactions
        """
    ).fetchone()[0]

    connection.close()

    first_insert = insert_ledger_rows(
        AXIEOS_DB_PATH,
        ledger_rows,
    )

    second_insert = insert_ledger_rows(
        AXIEOS_DB_PATH,
        ledger_rows,
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    after_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_transactions
        """
    ).fetchone()[0]

    connection.close()

    print(
        "\nRONIN PRODUCTION LEDGER INSERT"
    )

    print(
        "Staged transfers:",
        len(staged_transfers),
    )

    print(
        "Ledger rows prepared:",
        len(ledger_rows),
    )

    print(
        "Transfers skipped:",
        skipped,
    )

    print(
        "Ledger rows before:",
        before_count,
    )

    print(
        "First insert:",
        first_insert,
    )

    print(
        "Second insert:",
        second_insert,
    )

    print(
        "Ledger rows after:",
        after_count,
    )


def get_movement_direction(
    movement,
):
    value_in = Decimal(
        str(
            movement.get(
                "value_in",
                "0",
            )
        )
    )

    value_out = Decimal(
        str(
            movement.get(
                "value_out",
                "0",
            )
        )
    )

    if value_in > 0:
        return "IN"

    if value_out > 0:
        return "OUT"

    return "NONE"


def is_zero_address(
    address,
):
    return (
        normalize_address(address)
        == ZERO_ADDRESS
    )


def classify_single_movement(
    movement,
    method=None,
):
    direction = get_movement_direction(
        movement
    )

    asset = movement.get(
        "asset"
    )

    from_address = movement.get(
        "from_address"
    )

    to_address = movement.get(
        "to_address"
    )

    if (
        direction == "OUT"
        and is_zero_address(to_address)
    ):
        if asset == "Axie Consumable Item":
            return {
                "classification": (
                    "CONSUMABLE_BURN"
                ),
                "confidence": "HIGH",
                "reason": (
                    "consumable sent to "
                    "zero address"
                ),
            }

        if asset == "Axie":
            return {
                "classification": "NFT_BURN",
                "confidence": "HIGH",
                "reason": (
                    "Axie sent to zero address"
                ),
            }

    if (
        direction == "IN"
        and is_zero_address(from_address)
    ):
        return {
            "classification": (
                "MINT_OR_CLAIM"
            ),
            "confidence": "HIGH",
            "reason": (
                "asset received from "
                "zero address"
            ),
        }

    # Legacy CSV checkpoint rows are not
    # ordinary blockchain transfers.
    if method == "checkpoint":
        return None

    if direction == "IN":
        return {
            "classification": "TRANSFER_IN",
            "confidence": "MEDIUM",
            "reason": (
                "single incoming movement "
                "without detected payment"
            ),
        }

    if direction == "OUT":
        return {
            "classification": "TRANSFER_OUT",
            "confidence": "MEDIUM",
            "reason": (
                "single outgoing movement "
                "without detected receipt"
            ),
        }

    return None


def all_movements_are_zero_address_mints(
    movements,
):
    if not movements:
        return False

    for movement in movements:
        direction = (
            get_movement_direction(
                movement
            )
        )

        if direction != "IN":
            return False

        if not is_zero_address(
            movement.get(
                "from_address"
            )
        ):
            return False

    return True






def classify_grouped_transaction(
    transaction,
):
    method = transaction.get(
        "method"
    )

    movements = transaction.get(
        "movements",
        [],
    )

    if method == "swapExactTokensForTokens":
        return {
            "classification": "TOKEN_SWAP",
            "confidence": "HIGH",
            "reason": (
                "swap method detected"
            ),
        }

    if method in {
        "restakeRewards",
        "claimRewards",
        "claimReward",
    }:
        return {
            "classification": (
                "STAKING_OR_REWARD"
            ),
            "confidence": "HIGH",
            "reason": (
                "staking or reward "
                "method detected"
            ),
        }

    if (
        len(movements) > 1
        and all_movements_are_zero_address_mints(
            movements
        )
    ):
        return {
            "classification": (
                "MINT_OR_CLAIM"
            ),
            "confidence": "HIGH",
            "reason": (
                "all movements received "
                "from zero address"
            ),
        }

    weth_in = False
    weth_out = False

    non_weth_in = False
    non_weth_out = False

    for movement in movements:
        asset = movement.get(
            "asset"
        )

        direction = (
            get_movement_direction(
                movement
            )
        )

        is_weth = (
            asset
            == "Ronin Wrapped Ether"
        )

        if is_weth:
            if direction == "IN":
                weth_in = True

            elif direction == "OUT":
                weth_out = True

        else:
            if direction == "IN":
                non_weth_in = True

            elif direction == "OUT":
                non_weth_out = True

    if (
        weth_out
        and non_weth_in
    ):
        return {
            "classification": (
                "MARKETPLACE_BUY"
            ),
            "confidence": "HIGH",
            "reason": (
                "WETH sent and "
                "non-WETH asset received"
            ),
        }

    if (
        weth_in
        and non_weth_out
    ):
        return {
            "classification": (
                "MARKETPLACE_SALE"
            ),
            "confidence": "HIGH",
            "reason": (
                "WETH received and "
                "non-WETH asset sent"
            ),
        }

    if len(movements) == 1:
        simple_result = (
            classify_single_movement(
                movements[0],
                method=method,
            )
        )

        if simple_result is not None:
            return simple_result

    return {
        "classification": "UNKNOWN",
        "confidence": "LOW",
        "reason": (
            "no strong classification "
            "pattern detected"
        ),
    }


def validate_classification_storage(
    db_path,
):
    transactions = (
        group_ledger_rows_by_txhash(
            db_path
        )
    )

    expected_total = len(
        transactions
    )

    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT
            txhash,
            classification
        FROM blockchain_transaction_classifications
        """
    ).fetchall()

    connection.close()

    stored_total = len(rows)

    stored_txhashes = {
        row[0]
        for row in rows
    }

    invalid_classifications = [
        classification
        for _, classification in rows
        if classification
        not in TRANSACTION_CLASSIFICATIONS
    ]

    unknown_total = sum(
        1
        for _, classification in rows
        if classification == "UNKNOWN"
    )

    return {
        "expected_total": expected_total,
        "stored_total": stored_total,
        "unique_txhashes": len(
            stored_txhashes
        ),
        "unknown_total": unknown_total,
        "invalid_total": len(
            invalid_classifications
        ),
        "taxonomy_valid": (
            validate_classification_taxonomy()
        ),
        "passed": (
            stored_total
            == expected_total
            == len(stored_txhashes)
            and len(
                invalid_classifications
            )
            == 0
            and validate_classification_taxonomy()
        ),
    }


def decimal_to_plain_string(
    value,
):
    return format(
        value,
        "f",
    )














def run_live_api_test():
    response = fetch_json(
        RONIN_TRANSACTIONS_URL
    )

    transactions = response.get(
        "items",
        [],
    )

    print("\nRONIN LIVE API")

    print(
        "Transactions:",
        len(transactions),
    )

    if transactions:
        print(
            "First tx:",
            transactions[0].get(
                "hash"
            ),
        )

        print(
            "Last tx:",
            transactions[-1].get(
                "hash"
            ),
        )

    print(
        "Has next page:",
        response.get(
            "next_page_params"
        ) is not None,
    )



def run_two_page_test():
    page_1 = fetch_json(
        RONIN_TRANSACTIONS_URL
    )

    page_2 = fetch_next_page(
        page_1
    )

    page_1_items = page_1.get(
        "items",
        [],
    )

    page_2_items = (
        page_2.get("items", [])
        if page_2
        else []
    )

    page_1_hashes = {
        transaction.get("hash")
        for transaction in page_1_items
    }

    page_2_hashes = {
        transaction.get("hash")
        for transaction in page_2_items
    }

    overlap = (
        page_1_hashes
        & page_2_hashes
    )

    print("\nRONIN TWO-PAGE TEST")

    print(
        "Page 1 transactions:",
        len(page_1_items),
    )

    print(
        "Page 2 transactions:",
        len(page_2_items),
    )

    if page_2_items:
        print(
            "Page 2 first tx:",
            page_2_items[0].get(
                "hash"
            ),
        )

        print(
            "Page 2 last tx:",
            page_2_items[-1].get(
                "hash"
            ),
        )

    print(
        "Cross-page duplicates:",
        len(overlap),
    )

    print(
        "Page 2 has next page:",
        (
            page_2.get(
                "next_page_params"
            ) is not None
            if page_2
            else False
        ),
    )


def run_multi_page_test():
    pages = fetch_transaction_pages(
        max_pages=3
    )

    all_transactions = []

    print("\nRONIN MULTI-PAGE TEST")

    for page_number, page in enumerate(
        pages,
        start=1,
    ):
        transactions = page.get(
            "items",
            [],
        )

        all_transactions.extend(
            transactions
        )

        print(
            f"Page {page_number}: "
            f"{len(transactions)} transactions"
        )

    tx_hashes = [
        transaction.get("hash")
        for transaction
        in all_transactions
    ]

    unique_hashes = set(
        tx_hashes
    )

    duplicate_count = (
        len(tx_hashes)
        - len(unique_hashes)
    )

    print(
        "Pages fetched:",
        len(pages),
    )

    print(
        "Total transactions:",
        len(all_transactions),
    )

    print(
        "Unique tx hashes:",
        len(unique_hashes),
    )

    print(
        "Duplicates:",
        duplicate_count,
    )

    print(
        "More history available:",
        pages[-1].get(
            "next_page_params"
        ) is not None,
    )


def run_normalized_sync_test():
    transactions = (
        fetch_normalized_transactions(
            max_pages=3
        )
    )

    print(
        "\nRONIN NORMALIZED SYNC TEST"
    )

    print(
        "Transactions:",
        len(transactions),
    )

    if transactions:
        first_transaction = (
            transactions[0]
        )

        last_transaction = (
            transactions[-1]
        )

        print(
            "First tx:",
            first_transaction[
                "tx_hash"
            ],
        )

        print(
            "First timestamp:",
            first_transaction[
                "timestamp"
            ],
        )

        print(
            "Last tx:",
            last_transaction[
                "tx_hash"
            ],
        )

        print(
            "Last timestamp:",
            last_transaction[
                "timestamp"
            ],
        )

        print(
            "Fields:",
            list(
                first_transaction.keys()
            ),
        )




def run_database_init_test():
    initialize_transaction_database(
        TEST_DB_PATH
    )

    connection = sqlite3.connect(
        TEST_DB_PATH
    )

    cursor = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = 'ronin_transactions'
        """
    )

    table_exists = (
        cursor.fetchone()
        is not None
    )

    connection.close()

    print(
        "\nRONIN DATABASE TEST"
    )

    print(
        "Database:",
        TEST_DB_PATH,
    )

    print(
        "ronin_transactions table:",
        (
            "READY"
            if table_exists
            else "MISSING"
        ),
    )


def run_database_insert_test():
    initialize_transaction_database(
        TEST_DB_PATH
    )

    transactions = (
        fetch_normalized_transactions(
            max_pages=3
        )
    )

    inserted_count = (
        insert_transactions(
            TEST_DB_PATH,
            transactions,
        )
    )

    connection = sqlite3.connect(
        TEST_DB_PATH
    )

    cursor = connection.execute(
        """
        SELECT COUNT(*)
        FROM ronin_transactions
        """
    )

    database_count = cursor.fetchone()[0]

    connection.close()

    print(
        "\nRONIN DATABASE INSERT TEST"
    )

    print(
        "Transactions fetched:",
        len(transactions),
    )

    print(
        "Transactions inserted:",
        inserted_count,
    )

    print(
        "Transactions in database:",
        database_count,
    )


def run_idempotency_test():
    initialize_transaction_database(
        IDEMPOTENCY_DB_PATH
    )

    connection = sqlite3.connect(
        IDEMPOTENCY_DB_PATH
    )

    connection.execute(
        """
        DELETE FROM ronin_transactions
        """
    )

    connection.commit()
    connection.close()

    transactions = (
        fetch_normalized_transactions(
            max_pages=3
        )
    )

    first_insert = insert_transactions(
        IDEMPOTENCY_DB_PATH,
        transactions,
    )

    second_insert = insert_transactions(
        IDEMPOTENCY_DB_PATH,
        transactions,
    )

    connection = sqlite3.connect(
        IDEMPOTENCY_DB_PATH
    )

    cursor = connection.execute(
        """
        SELECT COUNT(*)
        FROM ronin_transactions
        """
    )

    database_count = cursor.fetchone()[0]

    connection.close()

    print(
        "\nRONIN IDEMPOTENCY TEST"
    )

    print(
        "Transactions fetched:",
        len(transactions),
    )

    print(
        "First insert:",
        first_insert,
    )

    print(
        "Second insert:",
        second_insert,
    )

    print(
        "Transactions in database:",
        database_count,
    )


def run_axieos_database_inspection():
    tables = inspect_axieos_database(
        AXIEOS_DB_PATH
    )

    print(
        "\nAXIEOS DATABASE INSPECTION"
    )

    print(
        "Database:",
        AXIEOS_DB_PATH,
    )

    print(
        "Tables:",
        len(tables),
    )

    for table in tables:
        print(
            "-",
            table,
        )


def run_raw_table_test():
    initialize_raw_api_table(
        TEST_DB_PATH
    )

    connection = sqlite3.connect(
        TEST_DB_PATH
    )

    columns = connection.execute(
        """
        PRAGMA table_info(
            ronin_api_transactions_raw
        )
        """
    ).fetchall()

    connection.close()

    print(
        "\nRONIN RAW TABLE TEST"
    )

    print(
        "Columns:",
        len(columns),
    )

    for column in columns:
        print(
            column[1]
        )


def run_raw_api_sync_test():
    initialize_raw_api_table(
        TEST_DB_PATH
    )

    connection = sqlite3.connect(
        TEST_DB_PATH
    )

    connection.execute(
        """
        DELETE FROM ronin_api_transactions_raw
        """
    )

    connection.commit()
    connection.close()

    transactions = (
        fetch_normalized_transactions(
            max_pages=3
        )
    )

    first_insert = (
        insert_raw_api_transactions(
            TEST_DB_PATH,
            transactions,
        )
    )

    second_insert = (
        insert_raw_api_transactions(
            TEST_DB_PATH,
            transactions,
        )
    )

    connection = sqlite3.connect(
        TEST_DB_PATH
    )

    database_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM ronin_api_transactions_raw
        """
    ).fetchone()[0]

    connection.close()

    print(
        "\nRONIN RAW API SYNC TEST"
    )

    print(
        "Transactions fetched:",
        len(transactions),
    )

    print(
        "First insert:",
        first_insert,
    )

    print(
        "Second insert:",
        second_insert,
    )

    print(
        "Rows in raw staging:",
        database_count,
    )


def run_token_transfer_api_test():
    response = fetch_json(
        RONIN_TOKEN_TRANSFERS_URL
    )

    transfers = response.get(
        "items",
        [],
    )

    print(
        "\nRONIN TOKEN TRANSFER API"
    )

    print(
        "Transfers:",
        len(transfers),
    )

    print(
        "Has next page:",
        response.get(
            "next_page_params"
        ) is not None,
    )

    if transfers:
        first_transfer = transfers[0]

        print(
            "\nFIRST TRANSFER FIELDS"
        )

        for key in sorted(
            first_transfer.keys()
        ):
            print(key)


def run_token_transfer_detail_test():
    response = fetch_json(
        RONIN_TOKEN_TRANSFERS_URL
    )

    transfers = response.get(
        "items",
        [],
    )

    print(
        "\nRONIN TOKEN TRANSFER DETAIL"
    )

    for index, transfer in enumerate(
        transfers[:5],
        start=1,
    ):
        token = transfer.get("token") or {}
        total = transfer.get("total") or {}

        print(
            f"\nTRANSFER {index}"
        )

        print(
            "Transaction:",
            transfer.get(
                "transaction_hash"
            ),
        )

        print(
            "Log index:",
            transfer.get(
                "log_index"
            ),
        )

        print(
            "From:",
            extract_transfer_address(
                transfer.get("from")
            ),
        )

        print(
            "To:",
            extract_transfer_address(
                transfer.get("to")
            ),
        )

        print(
            "Token type:",
            transfer.get(
                "token_type"
            ),
        )

        print(
            "Token symbol:",
            token.get("symbol"),
        )

        print(
            "Token name:",
            token.get("name"),
        )

        print(
            "Token address:",
            token.get("address"),
        )

        print(
            "Decimals:",
            token.get("decimals"),
        )

        print(
            "Total:",
            total,
        )


def run_token_transfer_normalization_test():
    response = fetch_json(
        RONIN_TOKEN_TRANSFERS_URL
    )

    transfers = response.get(
        "items",
        [],
    )

    normalized = (
        normalize_token_transfers(
            transfers
        )
    )

    print(
        "\nRONIN TRANSFER NORMALIZATION"
    )

    print(
        "Transfers:",
        len(normalized),
    )

    for transfer in normalized[:5]:
        print(
            "\n",
            transfer,
        )


def run_raw_transfer_table_test():
    initialize_raw_transfer_table(
        TEST_DB_PATH
    )

    connection = sqlite3.connect(
        TEST_DB_PATH
    )

    columns = connection.execute(
        """
        PRAGMA table_info(
            ronin_token_transfers_raw
        )
        """
    ).fetchall()

    connection.close()

    print(
        "\nRONIN RAW TRANSFER TABLE TEST"
    )

    print(
        "Columns:",
        len(columns),
    )

    for column in columns:
        print(column[1])


def run_raw_transfer_sync_test():
    initialize_raw_transfer_table(
        TEST_DB_PATH
    )

    connection = sqlite3.connect(
        TEST_DB_PATH
    )

    connection.execute(
        """
        DELETE FROM ronin_token_transfers_raw
        """
    )

    connection.commit()
    connection.close()

    response = fetch_json(
        RONIN_TOKEN_TRANSFERS_URL
    )

    raw_transfers = response.get(
        "items",
        [],
    )

    transfers = normalize_token_transfers(
        raw_transfers
    )

    first_insert = (
        insert_raw_token_transfers(
            TEST_DB_PATH,
            transfers,
        )
    )

    second_insert = (
        insert_raw_token_transfers(
            TEST_DB_PATH,
            transfers,
        )
    )

    connection = sqlite3.connect(
        TEST_DB_PATH
    )

    database_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM ronin_token_transfers_raw
        """
    ).fetchone()[0]

    connection.close()

    print(
        "\nRONIN RAW TRANSFER SYNC TEST"
    )

    print(
        "Transfers fetched:",
        len(transfers),
    )

    print(
        "First insert:",
        first_insert,
    )

    print(
        "Second insert:",
        second_insert,
    )

    print(
        "Rows in transfer staging:",
        database_count,
    )


def run_token_transfer_pagination_test():
    pages = fetch_token_transfer_pages(
        max_pages=3
    )

    raw_transfers = []

    print(
        "\nRONIN TOKEN TRANSFER PAGINATION"
    )

    for page_number, page in enumerate(
        pages,
        start=1,
    ):
        page_transfers = page.get(
            "items",
            [],
        )

        raw_transfers.extend(
            page_transfers
        )

        print(
            f"Page {page_number}: "
            f"{len(page_transfers)} transfers"
        )

    normalized = (
        normalize_token_transfers(
            raw_transfers
        )
    )

    transfer_keys = [
        transfer["transfer_key"]
        for transfer in normalized
    ]

    unique_keys = set(
        transfer_keys
    )

    duplicate_count = (
        len(transfer_keys)
        - len(unique_keys)
    )

    print(
        "Pages fetched:",
        len(pages),
    )

    print(
        "Total transfers:",
        len(normalized),
    )

    print(
        "Unique transfer keys:",
        len(unique_keys),
    )

    print(
        "Duplicates:",
        duplicate_count,
    )

    print(
        "More history available:",
        pages[-1].get(
            "next_page_params"
        ) is not None,
    )


def run_axieos_backup_test():
    backup_path = backup_axieos_database(
        AXIEOS_DB_PATH,
        AXIEOS_BACKUP_PATH,
    )

    print(
        "\nAXIEOS DATABASE BACKUP"
    )

    print(
        "Source exists:",
        AXIEOS_DB_PATH.exists(),
    )

    print(
        "Backup exists:",
        backup_path.exists(),
    )

    print(
        "Backup:",
        backup_path,
    )

    print(
        "Source size:",
        AXIEOS_DB_PATH.stat().st_size,
    )

    print(
        "Backup size:",
        backup_path.stat().st_size,
    )


def run_production_staging_sync():
    initialize_raw_api_table(
        AXIEOS_DB_PATH
    )

    initialize_raw_transfer_table(
        AXIEOS_DB_PATH
    )

    transactions = (
        fetch_normalized_transactions(
            max_pages=3
        )
    )

    transfers = (
        fetch_normalized_token_transfers(
            max_pages=3
        )
    )

    transaction_insert_1 = (
        insert_raw_api_transactions(
            AXIEOS_DB_PATH,
            transactions,
        )
    )

    transaction_insert_2 = (
        insert_raw_api_transactions(
            AXIEOS_DB_PATH,
            transactions,
        )
    )

    transfer_insert_1 = (
        insert_raw_token_transfers(
            AXIEOS_DB_PATH,
            transfers,
        )
    )

    transfer_insert_2 = (
        insert_raw_token_transfers(
            AXIEOS_DB_PATH,
            transfers,
        )
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    transaction_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM ronin_api_transactions_raw
        """
    ).fetchone()[0]

    transfer_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM ronin_token_transfers_raw
        """
    ).fetchone()[0]

    ledger_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_transactions
        """
    ).fetchone()[0]

    connection.close()

    print(
        "\nRONIN PRODUCTION STAGING SYNC"
    )

    print(
        "Transactions fetched:",
        len(transactions),
    )

    print(
        "Transaction first insert:",
        transaction_insert_1,
    )

    print(
        "Transaction second insert:",
        transaction_insert_2,
    )

    print(
        "Transactions staged:",
        transaction_count,
    )

    print(
        "Transfers fetched:",
        len(transfers),
    )

    print(
        "Transfer first insert:",
        transfer_insert_1,
    )

    print(
        "Transfer second insert:",
        transfer_insert_2,
    )

    print(
        "Transfers staged:",
        transfer_count,
    )

    print(
        "Existing ledger rows:",
        ledger_count,
    )


def run_accounting_preview_test():
    transfers = (
        fetch_normalized_token_transfers(
            max_pages=1
        )
    )

    print(
        "\nRONIN ACCOUNTING PREVIEW"
    )

    for transfer in transfers[:10]:
        preview = (
            build_accounting_transfer_preview(
                transfer
            )
        )

        print(preview)


def run_existing_ledger_format_test():
    rows = inspect_existing_ledger_format(
        AXIEOS_DB_PATH
    )

    print(
        "\nEXISTING LEDGER FORMAT"
    )

    for row in rows:
        print(row)


def run_ledger_adapter_test():
    transfers = (
        fetch_normalized_token_transfers(
            max_pages=1
        )
    )

    transactions = (
        fetch_normalized_transactions(
            max_pages=1
        )
    )

    methods_by_tx = {
        transaction["tx_hash"]:
        transaction["method"]
        for transaction in transactions
    }

    print(
        "\nRONIN LEDGER ADAPTER"
    )

    for transfer in transfers[:10]:
        ledger_row = (
            build_ledger_row_from_transfer(
                transfer,
                method=methods_by_tx.get(
                    transfer["tx_hash"]
                ),
            )
        )

        print(ledger_row)


def run_production_ledger_validation():
    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    total_rows = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_transactions
        """
    ).fetchone()[0]

    unique_source_rows = connection.execute(
        """
        SELECT COUNT(
            DISTINCT source_row_hash
        )
        FROM blockchain_transactions
        """
    ).fetchone()[0]

    duplicate_source_rows = (
        total_rows
        - unique_source_rows
    )

    legacy_rows = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_transactions
        WHERE datetime < '2026-01-01'
        """
    ).fetchone()[0]

    api_rows = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_transactions
        WHERE datetime >= '2026-01-01'
        """
    ).fetchone()[0]

    connection.close()

    print(
        "\nRONIN PRODUCTION LEDGER VALIDATION"
    )

    print(
        "Total ledger rows:",
        total_rows,
    )

    print(
        "Unique source rows:",
        unique_source_rows,
    )

    print(
        "Duplicate source rows:",
        duplicate_source_rows,
    )

    print(
        "Legacy rows:",
        legacy_rows,
    )

    print(
        "API-era rows:",
        api_rows,
    )

    print(
        "Expected total:",
        187,
    )

    print(
        "Validation:",
        (
            "PASS"
            if (
                total_rows == 187
                and unique_source_rows
                == total_rows
                and legacy_rows == 37
                and api_rows == 150
            )
            else "REVIEW"
        ),
    )


def run_ronin_sync(
    max_pages=3,
):
    print("\nAXIEOS RONIN SYNC")

    # Make sure production staging tables exist.
    initialize_raw_api_table(
        AXIEOS_DB_PATH
    )

    initialize_raw_transfer_table(
        AXIEOS_DB_PATH
    )

    # Fetch live Ronin data.
    transactions = (
        fetch_normalized_transactions(
            max_pages=max_pages
        )
    )

    transfers = (
        fetch_normalized_token_transfers(
            max_pages=max_pages
        )
    )

    # Stage raw API records.
    new_transactions = (
        insert_raw_api_transactions(
            AXIEOS_DB_PATH,
            transactions,
        )
    )

    new_transfers = (
        insert_raw_token_transfers(
            AXIEOS_DB_PATH,
            transfers,
        )
    )

    # Build accounting rows from all staged transfers.
    staged_transfers = (
        load_staged_transfers(
            AXIEOS_DB_PATH
        )
    )

    ledger_rows = []

    for transfer in staged_transfers:
        direction = (
            classify_transfer_direction(
                transfer
            )
        )

        if direction not in {
            "IN",
            "OUT",
        }:
            continue

        ledger_rows.append(
            build_ledger_row_from_transfer(
                transfer,
                method=transfer.get(
                    "method"
                ),
            )
        )

    new_ledger_rows = insert_ledger_rows(
        AXIEOS_DB_PATH,
        ledger_rows,
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    staged_transaction_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM ronin_api_transactions_raw
            """
        ).fetchone()[0]
    )

    staged_transfer_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM ronin_token_transfers_raw
            """
        ).fetchone()[0]
    )

    ledger_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_transactions
            """
        ).fetchone()[0]
    )

    connection.close()

    print(
        "Transactions fetched:",
        len(transactions),
    )

    print(
        "New transactions staged:",
        new_transactions,
    )

    print(
        "Transactions staged total:",
        staged_transaction_count,
    )

    print(
        "Transfers fetched:",
        len(transfers),
    )

    print(
        "New transfers staged:",
        new_transfers,
    )

    print(
        "Transfers staged total:",
        staged_transfer_count,
    )

    print(
        "Ledger rows prepared:",
        len(ledger_rows),
    )

    print(
        "New ledger rows:",
        new_ledger_rows,
    )

    print(
        "Ledger rows total:",
        ledger_count,
    )

    return {
        "transactions_fetched": len(
            transactions
        ),
        "new_transactions": new_transactions,
        "transfers_fetched": len(
            transfers
        ),
        "new_transfers": new_transfers,
        "new_ledger_rows": new_ledger_rows,
        "ledger_rows_total": ledger_count,
    }


def run_ronin_sync(
    max_pages=3,
):
    print("\nAXIEOS RONIN SYNC")

    initialize_raw_api_table(
        AXIEOS_DB_PATH
    )

    initialize_raw_transfer_table(
        AXIEOS_DB_PATH
    )

    transactions = (
        fetch_normalized_transactions(
            max_pages=max_pages
        )
    )

    transfers = (
        fetch_normalized_token_transfers(
            max_pages=max_pages
        )
    )

    new_transactions = (
        insert_raw_api_transactions(
            AXIEOS_DB_PATH,
            transactions,
        )
    )

    new_transfers = (
        insert_raw_token_transfers(
            AXIEOS_DB_PATH,
            transfers,
        )
    )

    staged_transfers = (
        load_staged_transfers(
            AXIEOS_DB_PATH
        )
    )

    ledger_rows = []

    for transfer in staged_transfers:
        direction = (
            classify_transfer_direction(
                transfer
            )
        )

        if direction not in {
            "IN",
            "OUT",
        }:
            continue

        ledger_rows.append(
            build_ledger_row_from_transfer(
                transfer,
                method=transfer.get(
                    "method"
                ),
            )
        )

    new_ledger_rows = insert_ledger_rows(
        AXIEOS_DB_PATH,
        ledger_rows,
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    staged_transaction_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM ronin_api_transactions_raw
            """
        ).fetchone()[0]
    )

    staged_transfer_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM ronin_token_transfers_raw
            """
        ).fetchone()[0]
    )

    ledger_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_transactions
            """
        ).fetchone()[0]
    )

    connection.close()

    print(
        "Transactions fetched:",
        len(transactions),
    )

    print(
        "New transactions staged:",
        new_transactions,
    )

    print(
        "Transactions staged total:",
        staged_transaction_count,
    )

    print(
        "Transfers fetched:",
        len(transfers),
    )

    print(
        "New transfers staged:",
        new_transfers,
    )

    print(
        "Transfers staged total:",
        staged_transfer_count,
    )

    print(
        "Ledger rows prepared:",
        len(ledger_rows),
    )

    print(
        "New ledger rows:",
        new_ledger_rows,
    )

    print(
        "Ledger rows total:",
        ledger_count,
    )

    return {
        "transactions_fetched": len(
            transactions
        ),
        "new_transactions": new_transactions,
        "transfers_fetched": len(
            transfers
        ),
        "new_transfers": new_transfers,
        "new_ledger_rows": new_ledger_rows,
        "ledger_rows_total": ledger_count,
    }


def run_ronin_sync_v02(
    max_pages=3,
):
    run_ronin_sync(
        max_pages=max_pages
    )

    initialize_classification_table(
        AXIEOS_DB_PATH
    )

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    processed = (
        store_transaction_classifications(
            AXIEOS_DB_PATH,
            transactions,
        )
    )

    validation = (
        validate_classification_storage(
            AXIEOS_DB_PATH
        )
    )

    print(
        "\nRONIN TRANSACTION CLASSIFICATION"
    )

    print(
        "Transactions classified:",
        processed,
    )

    print(
        "Classifications stored:",
        validation["stored_total"],
    )

    print(
        "Unique classified transactions:",
        validation["unique_txhashes"],
    )

    print(
        "Unknown classifications:",
        validation["unknown_total"],
    )

    print(
        "Invalid classifications:",
        validation["invalid_total"],
    )

    print(
        "Classifier version:",
        CLASSIFIER_VERSION,
    )

    print(
        "Taxonomy valid:",
        validation["taxonomy_valid"],
    )

    print(
        "Validation:",
        (
            "PASS"
            if validation["passed"]
            else "FAIL"
        ),
    )







def run_classification_taxonomy_test():
    print(
        "\nRONIN CLASSIFICATION TAXONOMY"
    )

    print(
        "Categories:",
        len(
            TRANSACTION_CLASSIFICATIONS
        ),
    )

    print(
        "Taxonomy valid:",
        validate_classification_taxonomy(),
    )

    for classification in sorted(
        TRANSACTION_CLASSIFICATIONS
    ):
        print(
            f"{classification}: "
            f"{CLASSIFICATION_DESCRIPTIONS[classification]}"
        )


def run_marketplace_classification_test():
    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    classified = []

    for transaction in transactions:
        result = (
            classify_grouped_transaction(
                transaction
            )
        )

        if result["classification"] in {
            "TOKEN_SWAP",
            "MARKETPLACE_BUY",
            "MARKETPLACE_SALE",
        }:
            classified.append(
                (
                    transaction,
                    result,
                )
            )

    print(
        "\nRONIN MARKETPLACE CLASSIFICATION"
    )

    print(
        "Transactions checked:",
        len(transactions),
    )

    print(
        "Strong classifications:",
        len(classified),
    )

    for transaction, result in (
        classified[:10]
    ):
        print(
            "\nTX:",
            transaction["txhash"],
        )

        print(
            "Classification:",
            result["classification"],
        )

        print(
            "Confidence:",
            result["confidence"],
        )

        print(
            "Reason:",
            result["reason"],
        )

        for movement in transaction[
            "movements"
        ]:
            print(movement)


def run_basic_classification_test():
    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    counts = {}

    examples = {}

    for transaction in transactions:
        result = (
            classify_grouped_transaction(
                transaction
            )
        )

        classification = result[
            "classification"
        ]

        counts[classification] = (
            counts.get(
                classification,
                0,
            )
            + 1
        )

        examples.setdefault(
            classification,
            (
                transaction,
                result,
            ),
        )

    print(
        "\nRONIN BASIC CLASSIFICATION"
    )

    print(
        "Transactions:",
        len(transactions),
    )

    print("\nCOUNTS")

    for classification in sorted(
        counts
    ):
        print(
            f"{classification}: "
            f"{counts[classification]}"
        )

    target_examples = [
        "CONSUMABLE_BURN",
        "NFT_BURN",
        "MINT_OR_CLAIM",
        "TRANSFER_IN",
        "TRANSFER_OUT",
    ]

    print("\nEXAMPLES")

    for classification in target_examples:
        if classification not in examples:
            continue

        transaction, result = (
            examples[classification]
        )

        print(
            f"\n{classification}"
        )

        print(
            "TX:",
            transaction["txhash"],
        )

        print(
            "Reason:",
            result["reason"],
        )

        for movement in transaction[
            "movements"
        ]:
            print(movement)


def run_unknown_classification_test():
    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    unknown_transactions = []

    for transaction in transactions:
        result = (
            classify_grouped_transaction(
                transaction
            )
        )

        if (
            result["classification"]
            == "UNKNOWN"
        ):
            unknown_transactions.append(
                (
                    transaction,
                    result,
                )
            )

    print(
        "\nRONIN UNKNOWN CLASSIFICATIONS"
    )

    print(
        "Unknown transactions:",
        len(unknown_transactions),
    )

    for transaction, result in (
        unknown_transactions
    ):
        print(
            "\nTX:",
            transaction["txhash"],
        )

        print(
            "Datetime:",
            transaction["datetime"],
        )

        print(
            "Method:",
            transaction["method"],
        )

        print(
            "Reason:",
            result["reason"],
        )

        print(
            "Movements:",
            len(
                transaction["movements"]
            ),
        )

        for movement in transaction[
            "movements"
        ]:
            print(movement)


def run_classification_storage_test():
    initialize_classification_table(
        AXIEOS_DB_PATH
    )

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    processed = (
        store_transaction_classifications(
            AXIEOS_DB_PATH,
            transactions,
        )
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    total = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_transaction_classifications
        """
    ).fetchone()[0]

    unknown = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_transaction_classifications
        WHERE classification = 'UNKNOWN'
        """
    ).fetchone()[0]

    counts = connection.execute(
        """
        SELECT
            classification,
            COUNT(*)
        FROM blockchain_transaction_classifications
        GROUP BY classification
        ORDER BY classification
        """
    ).fetchall()

    connection.close()

    print(
        "\nRONIN CLASSIFICATION STORAGE"
    )

    print(
        "Transactions processed:",
        processed,
    )

    print(
        "Classifications stored:",
        total,
    )

    print(
        "Unknown classifications:",
        unknown,
    )

    print(
        "Classifier version:",
        CLASSIFIER_VERSION,
    )

    print("\nCOUNTS")

    for classification, count in counts:
        print(
            f"{classification}: {count}"
        )



def run_economic_schema_test():
    sample = build_empty_economic_event(
        txhash="0xtest",
        classification="MARKETPLACE_BUY",
    )

    print(
        "\nRONIN ECONOMIC EVENT SCHEMA"
    )

    print(
        "Fields:",
        len(
            ECONOMIC_EVENT_FIELDS
        ),
    )

    print(
        "Schema valid:",
        validate_economic_event(
            sample
        ),
    )

    print(
        "Economics version:",
        ECONOMICS_VERSION,
    )

    print("\nSAMPLE EVENT")

    for key, value in sample.items():
        print(
            f"{key}: {value}"
        )


def run_marketplace_buy_economics_test():
    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    events = []

    for transaction in transactions:
        event = (
            extract_marketplace_buy_economics(
                transaction
            )
        )

        if event is not None:
            events.append(event)

    ready = [
        event
        for event in events
        if (
            event[
                "economics_status"
            ]
            == "BUY_EXTRACTED"
        )
    ]

    review = [
        event
        for event in events
        if (
            event[
                "economics_status"
            ]
            == "REVIEW"
        )
    ]

    print(
        "\nRONIN MARKETPLACE BUY ECONOMICS"
    )

    print(
        "Marketplace buys:",
        len(events),
    )

    print(
        "Successfully extracted:",
        len(ready),
    )

    print(
        "Needs review:",
        len(review),
    )

    print("\nEXAMPLES")

    for event in ready[:5]:
        print(
            "\nTX:",
            event["txhash"],
        )

        print(
            "Asset:",
            event["asset_name"],
        )

        print(
            "Quantity:",
            event["quantity"],
        )

        print(
            "Payment asset:",
            event["payment_asset"],
        )

        print(
            "WETH paid:",
            event["gross_amount"],
        )

        print(
            "Status:",
            event[
                "economics_status"
            ],
        )


def run_marketplace_sale_economics_test():
    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    events = []

    for transaction in transactions:
        event = (
            extract_marketplace_sale_economics(
                transaction
            )
        )

        if event is not None:
            events.append(event)

    ready = [
        event
        for event in events
        if (
            event[
                "economics_status"
            ]
            == "SALE_NET_EXTRACTED"
        )
    ]

    review = [
        event
        for event in events
        if (
            event[
                "economics_status"
            ]
            == "REVIEW"
        )
    ]

    print(
        "\nRONIN MARKETPLACE SALE ECONOMICS"
    )

    print(
        "Marketplace sales:",
        len(events),
    )

    print(
        "Successfully extracted:",
        len(ready),
    )

    print(
        "Needs review:",
        len(review),
    )

    print("\nEXAMPLES")

    for event in ready[:5]:
        print(
            "\nTX:",
            event["txhash"],
        )

        print(
            "Asset:",
            event["asset_name"],
        )

        print(
            "Quantity:",
            event["quantity"],
        )

        print(
            "Payment asset:",
            event["payment_asset"],
        )

        print(
            "WETH received:",
            event["net_amount"],
        )

        print(
            "Gross amount:",
            event["gross_amount"],
        )

        print(
            "Marketplace fee:",
            event["marketplace_fee"],
        )

        print(
            "Status:",
            event[
                "economics_status"
            ],
        )


def run_marketplace_fee_test():
    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    events = []

    for transaction in transactions:
        event = (
            extract_marketplace_sale_economics(
                transaction
            )
        )

        if event is None:
            continue

        event = (
            apply_marketplace_sale_fee(
                event
            )
        )

        events.append(event)

    complete = [
        event
        for event in events
        if (
            event[
                "economics_status"
            ]
            == "SALE_ECONOMICS_COMPLETE"
        )
    ]

    review = [
        event
        for event in events
        if (
            event[
                "economics_status"
            ]
            == "REVIEW"
        )
    ]

    print(
        "\nRONIN MARKETPLACE FEE ECONOMICS"
    )

    print(
        "Marketplace sales:",
        len(events),
    )

    print(
        "Economics complete:",
        len(complete),
    )

    print(
        "Needs review:",
        len(review),
    )

    print(
        "Seller fee rate:",
        MARKETPLACE_SELLER_FEE_RATE,
    )

    print("\nEXAMPLES")

    for event in complete[:5]:
        print(
            "\nTX:",
            event["txhash"],
        )

        print(
            "Asset:",
            event["asset_name"],
        )

        print(
            "Quantity:",
            event["quantity"],
        )

        print(
            "Gross sale:",
            event["gross_amount"],
        )

        print(
            "Marketplace fee:",
            event["marketplace_fee"],
        )

        print(
            "Net proceeds:",
            event["net_amount"],
        )

        print(
            "Status:",
            event[
                "economics_status"
            ],
        )


def run_economic_storage_test():
    initialize_economic_events_table(
        AXIEOS_DB_PATH
    )

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    events = (
        build_marketplace_economic_events(
            transactions
        )
    )

    processed = store_economic_events(
        AXIEOS_DB_PATH,
        events,
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    total = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_economic_events
        """
    ).fetchone()[0]

    counts = connection.execute(
        """
        SELECT
            classification,
            COUNT(*)
        FROM blockchain_economic_events
        GROUP BY classification
        ORDER BY classification
        """
    ).fetchall()

    review = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_economic_events
        WHERE economics_status = 'REVIEW'
        """
    ).fetchone()[0]

    connection.close()

    print(
        "\nRONIN ECONOMIC EVENT STORAGE"
    )

    print(
        "Events processed:",
        processed,
    )

    print(
        "Events stored:",
        total,
    )

    print(
        "Needs review:",
        review,
    )

    print(
        "Economics version:",
        ECONOMICS_VERSION,
    )

    print("\nCOUNTS")

    for classification, count in counts:
        print(
            f"{classification}: {count}"
        )


def run_asset_identifier_test():
    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    events = (
        build_marketplace_economic_events(
            transactions
        )
    )

    identified = [
        event
        for event in events
        if event[
            "asset_token_id"
        ] is not None
    ]

    missing = [
        event
        for event in events
        if event[
            "asset_token_id"
        ] is None
    ]

    multiple = [
        event
        for event in events
        if event[
            "economics_status"
        ]
        == "REVIEW_MULTIPLE_TOKEN_IDS"
    ]

    print(
        "\nRONIN ASSET IDENTIFIERS"
    )

    print(
        "Economic events:",
        len(events),
    )

    print(
        "Identifiers found:",
        len(identified),
    )

    print(
        "Identifiers missing:",
        len(missing),
    )

    print(
        "Multiple-ID review:",
        len(multiple),
    )

    print("\nEXAMPLES")

    for event in identified[:10]:
        print(
            "\nTX:",
            event["txhash"],
        )

        print(
            "Classification:",
            event["classification"],
        )

        print(
            "Asset:",
            event["asset_name"],
        )

        print(
            "Token ID:",
            event["asset_token_id"],
        )

        print(
            "Quantity:",
            event["quantity"],
        )

        print(
            "Status:",
            event[
                "economics_status"
            ],
        )


def run_axie_cost_basis_test():
    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    events = (
        build_marketplace_economic_events(
            transactions
        )
    )

    events = (
        match_axie_acquisition_costs(
            events
        )
    )

    axie_sales = [
        event
        for event in events
        if (
            event["classification"]
            == "MARKETPLACE_SALE"
            and event["asset_name"]
            == "Axie"
        )
    ]

    matched = [
        event
        for event in axie_sales
        if event[
            "economics_status"
        ] == "COST_BASIS_MATCHED"
    ]

    unknown = [
        event
        for event in axie_sales
        if event[
            "economics_status"
        ] == "UNKNOWN_COST_BASIS"
    ]

    deferred = [
        event
        for event in events
        if event[
            "economics_status"
        ]
        == "COST_BASIS_DEFERRED_INVENTORY"
    ]

    print(
        "\nRONIN AXIE COST BASIS"
    )

    print(
        "Axie sales:",
        len(axie_sales),
    )

    print(
        "Cost basis matched:",
        len(matched),
    )

    print(
        "Unknown cost basis:",
        len(unknown),
    )

    print(
        "Inventory sales deferred:",
        len(deferred),
    )

    print("\nMATCHED EXAMPLES")

    for event in matched[:10]:
        print(
            "\nTX:",
            event["txhash"],
        )

        print(
            "Axie ID:",
            event["asset_token_id"],
        )

        print(
            "Gross sale:",
            event["gross_amount"],
        )

        print(
            "Net proceeds:",
            event["net_amount"],
        )

        print(
            "Cost basis:",
            event["cost_basis"],
        )

        print(
            "Status:",
            event[
                "economics_status"
            ],
        )

    print("\nUNKNOWN EXAMPLES")

    for event in unknown[:5]:
        print(
            "\nTX:",
            event["txhash"],
        )

        print(
            "Axie ID:",
            event["asset_token_id"],
        )

        print(
            "Net proceeds:",
            event["net_amount"],
        )

        print(
            "Status:",
            event[
                "economics_status"
            ],
        )


def run_realized_pl_test():
    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    events = (
        build_marketplace_economic_events(
            transactions
        )
    )

    events = (
        match_axie_acquisition_costs(
            events
        )
    )

    events = (
        calculate_realized_pl(
            events
        )
    )

    completed = [
        event
        for event in events
        if (
            event[
                "economics_status"
            ]
            == "REALIZED_PL_COMPLETE"
        )
    ]

    total_realized_pl = sum(
        Decimal(
            event["realized_pl"]
        )
        for event in completed
    )

    axie_1429698 = next(
        (
            event
            for event in completed
            if (
                event[
                    "asset_token_id"
                ]
                == "1429698"
            )
        ),
        None,
    )

    known_trade_valid = (
        axie_1429698 is not None
        and Decimal(
            axie_1429698[
                "realized_pl"
            ]
        )
        == Decimal(
            "0.00000555"
        )
    )

    print(
        "\nRONIN REALIZED P/L"
    )

    print(
        "Completed Axie trades:",
        len(completed),
    )

    print(
        "Total realized P/L:",
        decimal_to_plain_string(
            total_realized_pl
        ),
        "WETH",
    )

    print(
        "Axie #1429698 regression:",
        (
            "PASS"
            if known_trade_valid
            else "FAIL"
        ),
    )

    print("\nTRADES")

    for event in completed:
        print(
            "\nAxie ID:",
            event["asset_token_id"],
        )

        print(
            "Gross sale:",
            event["gross_amount"],
        )

        print(
            "Marketplace fee:",
            event[
                "marketplace_fee"
            ],
        )

        print(
            "Net proceeds:",
            event["net_amount"],
        )

        print(
            "Cost basis:",
            event["cost_basis"],
        )

        print(
            "Realized P/L:",
            event["realized_pl"],
        )

        print(
            "Status:",
            event[
                "economics_status"
            ],
        )









if __name__ == "__main__":
    run_ronin_sync_v03(
        max_pages=3
    )