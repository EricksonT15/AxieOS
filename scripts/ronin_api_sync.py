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

ORIGINAL_RONIN_WALLET_ADDRESS = (
    "0x5c32ce3b21e786dcaf11d9c64dec31b21a2c6610"
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


RONIN_SYNC_ENDPOINTS = {
    "transactions",
    "token_transfers",
}


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
    "INTERNAL_TRANSFER",
    "TOKEN_BURN",
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
    "INTERNAL_TRANSFER": (
        "Asset movement between "
        "user-owned wallets"
    ),
    "TOKEN_BURN": (
        "Fungible or multi-token asset "
        "sent to the zero address."
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

RONIN_SYNC_VERSION = "0.4"

INTELLIGENCE_VERSION = "0.5"

RONIN_INTELLIGENCE_VERSION = "0.5"

ACCOUNTING_VERSION = "0.6"

WALLET_OWNERSHIP_TYPES = {
    "USER_OWNED",
    "EXTERNAL",
    "CONTRACT",
    "SYSTEM",
    "UNKNOWN",
}

WALLET_ROLES = {
    "PRIMARY",
    "SECONDARY",
    "MARKETPLACE",
    "STAKING",
    "DEX",
    "BURN",
    "SYSTEM",
    "UNKNOWN",
}

WALLET_RELATIONSHIP_TYPES = {
    "INTERNAL_USER_TRANSFER",
    "USER_TO_SYSTEM",
    "SYSTEM_TO_USER",
    "USER_TO_UNKNOWN",
    "UNKNOWN_TO_USER",
    "SYSTEM_TO_UNKNOWN",
    "UNKNOWN_TO_SYSTEM",
    "UNKNOWN_TO_UNKNOWN",
}

ASSET_CATEGORIES = {
    "AXIE_NFT",
    "CONSUMABLE",
    "MATERIAL",
    "FUNGIBLE_TOKEN",
    "NFT",
    "MULTI_TOKEN",
    "UNKNOWN",
}

ACCOUNTING_STATUSES = {
    "READY",
    "REVIEW",
    "NON_TAXABLE_INTERNAL",
    "INFORMATIONAL",
}

ACCOUNTING_EVENT_TYPES = {
    "ASSET_PURCHASE",
    "ASSET_SALE",
    "TOKEN_SWAP",
    "TRANSFER_IN",
    "TRANSFER_OUT",
    "INTERNAL_TRANSFER",
    "ASSET_BURN",
    "MINT_OR_CLAIM",
    "STAKING_OR_REWARD",
    "UNKNOWN",
}

ACCOUNTING_RECORD_FIELDS = {
    "accounting_key",
    "txhash",
    "datetime",
    "event_type",
    "classification",
    "asset_name",
    "asset_token_id",
    "asset_category",
    "quantity",
    "direction",
    "payment_asset",
    "gross_amount",
    "marketplace_fee",
    "net_amount",
    "cost_basis",
    "realized_pl",
    "counterparty_role",
    "is_internal_transfer",
    "accounting_status",
    "accounting_version",
}

CLASSIFICATION_TO_ACCOUNTING_EVENT = {
    "MARKETPLACE_BUY": "ASSET_PURCHASE",
    "MARKETPLACE_SALE": "ASSET_SALE",
    "TOKEN_SWAP": "TOKEN_SWAP",
    "TRANSFER_IN": "TRANSFER_IN",
    "TRANSFER_OUT": "TRANSFER_OUT",
    "INTERNAL_TRANSFER": "INTERNAL_TRANSFER",
    "CONSUMABLE_BURN": "ASSET_BURN",
    "NFT_BURN": "ASSET_BURN",
    "MINT_OR_CLAIM": "MINT_OR_CLAIM",
    "STAKING_OR_REWARD": "STAKING_OR_REWARD",
    "TOKEN_BURN": "ASSET_BURN",
    "UNKNOWN": "UNKNOWN",
}


COCOCHOCO_TOKEN_LABELS = {
    "1": "Regular CocoChoco",
    "2": "Premium CocoChoco",
}

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


def initialize_accounting_records_table(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        blockchain_accounting_records (
            accounting_key TEXT PRIMARY KEY,
            txhash TEXT NOT NULL,
            datetime TEXT,
            event_type TEXT NOT NULL,
            classification TEXT NOT NULL,
            asset_name TEXT,
            asset_token_id TEXT,
            asset_category TEXT,
            quantity TEXT,
            direction TEXT,
            payment_asset TEXT,
            gross_amount TEXT,
            marketplace_fee TEXT,
            net_amount TEXT,
            cost_basis TEXT,
            realized_pl TEXT,
            counterparty_role TEXT,
            is_internal_transfer INTEGER NOT NULL,
            accounting_status TEXT NOT NULL,
            accounting_version TEXT NOT NULL,
            updated_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_blockchain_accounting_records_txhash
        ON blockchain_accounting_records (
            txhash
        )
        """
    )

    connection.commit()
    connection.close()



def initialize_transaction_intelligence_table(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        blockchain_transaction_intelligence (
            txhash TEXT PRIMARY KEY,
            wallet_relationships_json TEXT NOT NULL,
            counterparties_json TEXT NOT NULL,
            asset_categories_json TEXT NOT NULL,
            asset_keys_json TEXT NOT NULL,
            is_internal_transfer INTEGER NOT NULL,
            intelligence_version TEXT NOT NULL,
            updated_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()



def initialize_asset_registry_table(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        ronin_asset_registry (
            asset_key TEXT PRIMARY KEY,
            token_address TEXT,
            token_id TEXT,
            token_name TEXT,
            token_symbol TEXT,
            token_type TEXT,
            decimals INTEGER,
            asset_category TEXT NOT NULL,
            source TEXT NOT NULL,
            intelligence_version TEXT NOT NULL,
            updated_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
            idx_asset_registry_address
        ON ronin_asset_registry (
            token_address
        )
        """
    )

    connection.commit()
    connection.close()


def build_asset_registry_key(
    token_address,
    token_id,
):
    normalized_address = (
        normalize_address(
            token_address
        )
    )

    token_part = (
        str(token_id)
        if token_id is not None
        else "FUNGIBLE"
    )

    return (
        f"{normalized_address}:"
        f"{token_part}"
    )


def classify_asset_category(
    token_name,
    token_type,
):
    if token_name == "Axie":
        return "AXIE_NFT"

    if (
        token_name
        == "Axie Consumable Item"
    ):
        return "CONSUMABLE"

    if token_name == "Axie Material":
        return "MATERIAL"

    if token_type == "ERC-20":
        return "FUNGIBLE_TOKEN"

    if token_type == "ERC-721":
        return "NFT"

    if token_type == "ERC-1155":
        return "MULTI_TOKEN"

    return "UNKNOWN"


def load_asset_registry_map(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT
            asset_key,
            asset_category
        FROM ronin_asset_registry
        """
    ).fetchall()

    connection.close()

    return {
        row[0]: row[1]
        for row in rows
    }


def get_transaction_asset_intelligence(
    db_path,
    txhash,
    asset_registry,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT
            token_address,
            token_id
        FROM ronin_token_transfers_raw
        WHERE tx_hash = ?
        """,
        (
            txhash,
        ),
    ).fetchall()

    connection.close()

    asset_keys = set()
    asset_categories = set()

    for token_address, token_id in rows:
        if token_address is None:
            continue

        asset_key = (
            build_asset_registry_key(
                token_address,
                token_id,
            )
        )

        asset_keys.add(
            asset_key
        )

        category = asset_registry.get(
            asset_key
        )

        if category is not None:
            asset_categories.add(
                category
            )

    return {
        "asset_keys": sorted(
            asset_keys
        ),
        "asset_categories": sorted(
            asset_categories
        ),
    }


def build_transaction_intelligence(
    db_path,
    transaction,
    asset_registry,
):
    relationships = set()
    counterparties = {}

    for movement in transaction.get(
        "movements",
        [],
    ):
        relationship_result = (
            classify_wallet_relationship(
                db_path,
                movement.get(
                    "from_address"
                ),
                movement.get(
                    "to_address"
                ),
            )
        )

        relationships.add(
            relationship_result[
                "relationship"
            ]
        )

        counterparty_address = (
            get_movement_counterparty(
                movement
            )
        )

        if counterparty_address is None:
            continue

        counterparty = (
            get_wallet_registry_entry(
                db_path,
                counterparty_address,
            )
        )

        if (
            counterparty[
                "wallet_role"
            ]
            == "UNKNOWN"
        ):
            continue

        counterparties[
            counterparty["address"]
        ] = {
            "address": (
                counterparty["address"]
            ),
            "label": (
                counterparty[
                    "wallet_label"
                ]
            ),
            "ownership_type": (
                counterparty[
                    "ownership_type"
                ]
            ),
            "role": (
                counterparty[
                    "wallet_role"
                ]
            ),
        }

    internal_result = (
        detect_internal_user_transfer(
            db_path,
            transaction,
        )
    )

    asset_result = (
        get_transaction_asset_intelligence(
            db_path,
            transaction["txhash"],
            asset_registry,
        )
    )

    return {
        "txhash": transaction[
            "txhash"
        ],
        "wallet_relationships": (
            sorted(
                relationships
            )
        ),
        "counterparties": list(
            counterparties.values()
        ),
        "asset_categories": (
            asset_result[
                "asset_categories"
            ]
        ),
        "asset_keys": (
            asset_result[
                "asset_keys"
            ]
        ),
        "is_internal_transfer": (
            internal_result[
                "is_internal_transfer"
            ]
        ),
        "intelligence_version": (
            INTELLIGENCE_VERSION
        ),
    }



def discover_assets_from_raw_transfers(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT DISTINCT
            token_address,
            token_id,
            token_name,
            token_symbol,
            token_type,
            decimals
        FROM ronin_token_transfers_raw
        WHERE token_address IS NOT NULL
        ORDER BY
            token_name,
            token_id
        """
    ).fetchall()

    connection.close()

    assets = []

    for row in rows:
        token_address = row[0]
        token_id = row[1]
        token_name = row[2]
        token_symbol = row[3]
        token_type = row[4]
        decimals = row[5]

        assets.append(
            {
                "asset_key": (
                    build_asset_registry_key(
                        token_address,
                        token_id,
                    )
                ),
                "token_address": (
                    normalize_address(
                        token_address
                    )
                ),
                "token_id": (
                    str(token_id)
                    if token_id
                    is not None
                    else None
                ),
                "token_name": token_name,
                "token_symbol": (
                    token_symbol
                ),
                "token_type": token_type,
                "decimals": decimals,
                "asset_category": (
                    classify_asset_category(
                        token_name,
                        token_type,
                    )
                ),
            }
        )

    return assets


def store_transaction_intelligence(
    db_path,
    intelligence_rows,
):
    connection = sqlite3.connect(
        db_path
    )

    processed = 0

    for row in intelligence_rows:
        connection.execute(
            """
            INSERT INTO
                blockchain_transaction_intelligence (
                    txhash,
                    wallet_relationships_json,
                    counterparties_json,
                    asset_categories_json,
                    asset_keys_json,
                    is_internal_transfer,
                    intelligence_version
                )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(txhash)
            DO UPDATE SET
                wallet_relationships_json =
                    excluded.wallet_relationships_json,
                counterparties_json =
                    excluded.counterparties_json,
                asset_categories_json =
                    excluded.asset_categories_json,
                asset_keys_json =
                    excluded.asset_keys_json,
                is_internal_transfer =
                    excluded.is_internal_transfer,
                intelligence_version =
                    excluded.intelligence_version,
                updated_at =
                    CURRENT_TIMESTAMP
            """,
            (
                row["txhash"],
                json.dumps(
                    row[
                        "wallet_relationships"
                    ],
                    sort_keys=True,
                ),
                json.dumps(
                    row["counterparties"],
                    sort_keys=True,
                ),
                json.dumps(
                    row["asset_categories"],
                    sort_keys=True,
                ),
                json.dumps(
                    row["asset_keys"],
                    sort_keys=True,
                ),
                (
                    1
                    if row[
                        "is_internal_transfer"
                    ]
                    else 0
                ),
                row[
                    "intelligence_version"
                ],
            ),
        )

        processed += 1

    connection.commit()
    connection.close()

    return processed


def store_asset_registry_entries(
    db_path,
    assets,
):
    connection = sqlite3.connect(
        db_path
    )

    processed = 0

    for asset in assets:
        connection.execute(
            """
            INSERT INTO ronin_asset_registry (
                asset_key,
                token_address,
                token_id,
                token_name,
                token_symbol,
                token_type,
                decimals,
                asset_category,
                source,
                intelligence_version
            )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?
            )
            ON CONFLICT(asset_key)
            DO UPDATE SET
                token_address =
                    excluded.token_address,
                token_id =
                    excluded.token_id,
                token_name =
                    excluded.token_name,
                token_symbol =
                    excluded.token_symbol,
                token_type =
                    excluded.token_type,
                decimals =
                    excluded.decimals,
                asset_category =
                    excluded.asset_category,
                source =
                    excluded.source,
                intelligence_version =
                    excluded.intelligence_version,
                updated_at =
                    CURRENT_TIMESTAMP
            """,
            (
                asset["asset_key"],
                asset["token_address"],
                asset["token_id"],
                asset["token_name"],
                asset["token_symbol"],
                asset["token_type"],
                asset["decimals"],
                asset["asset_category"],
                "RONIN_TOKEN_TRANSFERS",
                INTELLIGENCE_VERSION,
            ),
        )

        processed += 1

    connection.commit()
    connection.close()

    return processed






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


def initialize_ronin_sync_state_table(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        ronin_sync_state (
            endpoint TEXT PRIMARY KEY,
            newest_timestamp TEXT,
            oldest_timestamp TEXT,
            backfill_cursor_json TEXT,
            backfill_complete INTEGER NOT NULL
                DEFAULT 0,
            state_updated_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    for endpoint in sorted(
        RONIN_SYNC_ENDPOINTS
    ):
        connection.execute(
            """
            INSERT OR IGNORE INTO
                ronin_sync_state (
                    endpoint
                )
            VALUES (?)
            """,
            (
                endpoint,
            ),
        )

    connection.commit()
    connection.close()


def initialize_wallet_registry_table(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        ronin_wallet_registry (
            address TEXT PRIMARY KEY,
            wallet_label TEXT,
            ownership_type TEXT NOT NULL,
            wallet_role TEXT NOT NULL,
            source TEXT NOT NULL,
            intelligence_version TEXT NOT NULL,
            updated_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()
    connection.close()


def upsert_wallet_registry_entry(
    db_path,
    address,
    wallet_label,
    ownership_type,
    wallet_role,
    source,
):
    if ownership_type not in (
        WALLET_OWNERSHIP_TYPES
    ):
        raise ValueError(
            "Invalid ownership type: "
            f"{ownership_type}"
        )

    if wallet_role not in WALLET_ROLES:
        raise ValueError(
            "Invalid wallet role: "
            f"{wallet_role}"
        )

    normalized_address = (
        normalize_address(
            address
        )
    )

    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        INSERT INTO ronin_wallet_registry (
            address,
            wallet_label,
            ownership_type,
            wallet_role,
            source,
            intelligence_version
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(address)
        DO UPDATE SET
            wallet_label =
                excluded.wallet_label,
            ownership_type =
                excluded.ownership_type,
            wallet_role =
                excluded.wallet_role,
            source =
                excluded.source,
            intelligence_version =
                excluded.intelligence_version,
            updated_at =
                CURRENT_TIMESTAMP
        """,
        (
            normalized_address,
            wallet_label,
            ownership_type,
            wallet_role,
            source,
            INTELLIGENCE_VERSION,
        ),
    )

    connection.commit()
    connection.close()


def seed_default_wallet_registry(
    db_path,
):
    upsert_wallet_registry_entry(
        db_path=db_path,
        address=RONIN_WALLET_ADDRESS,
        wallet_label=(
            "Primary Ronin Wallet"
        ),
        ownership_type="USER_OWNED",
        wallet_role="PRIMARY",
        source="AXIEOS_CONFIG",
    )

    upsert_wallet_registry_entry(
        db_path=db_path,
        address=ORIGINAL_RONIN_WALLET_ADDRESS,
        wallet_label="Original Ronin Wallet",
        ownership_type="USER_OWNED",
        wallet_role="SECONDARY",
        source="AXIEOS_CONFIG",
    )

    upsert_wallet_registry_entry(
        db_path=db_path,
        address=ZERO_ADDRESS,
        wallet_label="Zero Address",
        ownership_type="SYSTEM",
        wallet_role="SYSTEM",
        source="AXIEOS_SYSTEM",
    )


def get_wallet_registry_entry(
    db_path,
    address,
):
    normalized_address = (
        normalize_address(
            address
        )
    )

    connection = sqlite3.connect(
        db_path
    )

    row = connection.execute(
        """
        SELECT
            address,
            wallet_label,
            ownership_type,
            wallet_role,
            source
        FROM ronin_wallet_registry
        WHERE address = ?
        """,
        (
            normalized_address,
        ),
    ).fetchone()

    connection.close()

    if row is None:
        return {
            "address": normalized_address,
            "wallet_label": None,
            "ownership_type": "UNKNOWN",
            "wallet_role": "UNKNOWN",
            "source": None,
        }

    return {
        "address": row[0],
        "wallet_label": row[1],
        "ownership_type": row[2],
        "wallet_role": row[3],
        "source": row[4],
    }


def classify_wallet_relationship(
    db_path,
    from_address,
    to_address,
):
    sender = get_wallet_registry_entry(
        db_path,
        from_address,
    )

    recipient = get_wallet_registry_entry(
        db_path,
        to_address,
    )

    sender_type = sender[
        "ownership_type"
    ]

    recipient_type = recipient[
        "ownership_type"
    ]

    if (
        sender_type == "USER_OWNED"
        and recipient_type == "USER_OWNED"
    ):
        relationship = (
            "INTERNAL_USER_TRANSFER"
        )

    elif (
        sender_type == "USER_OWNED"
        and recipient_type == "SYSTEM"
    ):
        relationship = "USER_TO_SYSTEM"

    elif (
        sender_type == "SYSTEM"
        and recipient_type == "USER_OWNED"
    ):
        relationship = "SYSTEM_TO_USER"

    elif (
        sender_type == "USER_OWNED"
        and recipient_type == "UNKNOWN"
    ):
        relationship = "USER_TO_UNKNOWN"

    elif (
        sender_type == "UNKNOWN"
        and recipient_type == "USER_OWNED"
    ):
        relationship = "UNKNOWN_TO_USER"

    elif (
        sender_type == "SYSTEM"
        and recipient_type == "UNKNOWN"
    ):
        relationship = "SYSTEM_TO_UNKNOWN"

    elif (
        sender_type == "UNKNOWN"
        and recipient_type == "SYSTEM"
    ):
        relationship = "UNKNOWN_TO_SYSTEM"

    else:
        relationship = "UNKNOWN_TO_UNKNOWN"

    return {
        "relationship": relationship,
        "from_wallet": sender,
        "to_wallet": recipient,
    }


def detect_internal_user_transfer(
    db_path,
    transaction,
):
    movements = transaction.get(
        "movements",
        [],
    )

    if not movements:
        return {
            "is_internal_transfer": False,
            "internal_movements": 0,
            "total_movements": 0,
        }

    internal_movements = 0

    for movement in movements:
        relationship = (
            classify_wallet_relationship(
                db_path,
                movement.get(
                    "from_address"
                ),
                movement.get(
                    "to_address"
                ),
            )
        )

        if (
            relationship["relationship"]
            == "INTERNAL_USER_TRANSFER"
        ):
            internal_movements += 1

    return {
        "is_internal_transfer": (
            internal_movements
            == len(movements)
        ),
        "internal_movements": (
            internal_movements
        ),
        "total_movements": (
            len(movements)
        ),
    }


def classify_transaction_with_intelligence(
    db_path,
    transaction,
):
    internal_result = (
        detect_internal_user_transfer(
            db_path,
            transaction,
        )
    )

    if internal_result[
        "is_internal_transfer"
    ]:
        return {
            "classification": (
                "INTERNAL_TRANSFER"
            ),
            "confidence": "HIGH",
            "reason": (
                "all movements are between "
                "user-owned wallets"
            ),
        }

    method = transaction.get(
        "method"
    )

    # ---------------------------------
    # Explicit staking operation
    # ---------------------------------

    if method == "stake":
        return {
            "classification": (
                "STAKING_OR_REWARD"
            ),
            "confidence": "HIGH",
            "reason": (
                "transaction method is stake"
            ),
        }

    # ---------------------------------
    # Known Axie release contract
    # ---------------------------------

    for movement in transaction.get(
        "movements",
        [],
    ):
        if (
            movement.get("asset")
            != "Axie"
        ):
            continue

        if (
            get_movement_direction(
                movement
            )
            != "OUT"
        ):
            continue

        counterparty_address = (
            get_movement_counterparty(
                movement
            )
        )

        if counterparty_address is None:
            continue

        counterparty = (
            get_wallet_registry_entry(
                db_path,
                counterparty_address,
            )
        )

        if (
            counterparty["wallet_role"]
            == "BURN"
        ):
            return {
                "classification": (
                    "NFT_BURN"
                ),
                "confidence": "HIGH",
                "reason": (
                    "Axie transferred to "
                    "a proven release contract"
                ),
            }

    # ---------------------------------
    # Known staking contract
    # Incoming OR outgoing
    # ---------------------------------

    for movement in transaction.get(
        "movements",
        [],
    ):
        direction = (
            get_movement_direction(
                movement
            )
        )

        if direction not in {
            "IN",
            "OUT",
        }:
            continue

        counterparty_address = (
            get_movement_counterparty(
                movement
            )
        )

        if counterparty_address is None:
            continue

        counterparty = (
            get_wallet_registry_entry(
                db_path,
                counterparty_address,
            )
        )

        if (
            counterparty["wallet_role"]
            == "STAKING"
        ):
            return {
                "classification": (
                    "STAKING_OR_REWARD"
                ),
                "confidence": "HIGH",
                "reason": (
                    "movement involves "
                    "a proven staking contract"
                ),
            }

    # ---------------------------------
    # Zero-address burns
    # ---------------------------------

    zero_address = normalize_address(
        ZERO_ADDRESS
    )

    for movement in transaction.get(
        "movements",
        [],
    ):
        if (
            get_movement_direction(
                movement
            )
            != "OUT"
        ):
            continue

        to_address = normalize_address(
            movement.get(
                "to_address"
            )
        )

        if to_address != zero_address:
            continue

        if (
            movement.get("asset")
            == "Axie"
        ):
            classification = (
                "NFT_BURN"
            )
        else:
            classification = (
                "TOKEN_BURN"
            )

        return {
            "classification": classification,
            "confidence": "HIGH",
            "reason": (
                "asset transferred to "
                "the zero address"
            ),
        }

    return classify_grouped_transaction(
        transaction
    )


def validate_historical_intelligence(
    db_path,
):
    transactions = (
        group_ledger_rows_by_txhash(
            db_path
        )
    )

    asset_registry = (
        load_asset_registry_map(
            db_path
        )
    )

    inconsistencies = []
    reclassification_candidates = []

    for transaction in transactions:
        base_result = (
            classify_grouped_transaction(
                transaction
            )
        )

        intelligent_result = (
            classify_transaction_with_intelligence(
                db_path,
                transaction,
            )
        )

        if (
            base_result["classification"]
            != intelligent_result[
                "classification"
            ]
        ):
            reclassification_candidates.append(
                {
                    "txhash": (
                        transaction["txhash"]
                    ),
                    "old": (
                        base_result[
                            "classification"
                        ]
                    ),
                    "new": (
                        intelligent_result[
                            "classification"
                        ]
                    ),
                }
            )

        intelligence = (
            build_transaction_intelligence(
                db_path,
                transaction,
                asset_registry,
            )
        )

        classification = (
            intelligent_result[
                "classification"
            ]
        )

        relationships = set(
            intelligence[
                "wallet_relationships"
            ]
        )

        roles = {
            counterparty["role"]
            for counterparty
            in intelligence[
                "counterparties"
            ]
        }

        issue = None

        if classification in {
            "MARKETPLACE_BUY",
            "MARKETPLACE_SALE",
        }:
            if "MARKETPLACE" not in roles:
                issue = (
                    "marketplace role missing"
                )

        elif classification == "TOKEN_SWAP":
            if "DEX" not in roles:
                issue = "DEX role missing"

        elif (
            classification
            == "STAKING_OR_REWARD"
        ):
            method = (
                transaction.get("method")
                or transaction.get(
                    "method_name"
                )
            )

            staking_methods = {
                "stake",
                "restakeRewards",
                "claimRewards",
                "claimReward",
                "claimPendingRewards",
            }

            if (
                "STAKING" not in roles
                and method
                not in staking_methods
            ):
                issue = (
                    "staking evidence missing"
                )

        elif classification == "MINT_OR_CLAIM":
            if (
                "SYSTEM_TO_USER"
                not in relationships
            ):
                issue = (
                    "system-to-user "
                    "relationship missing"
                )

        elif classification in {
            "CONSUMABLE_BURN",
            "NFT_BURN",
            "TOKEN_BURN",
        }:
            burn_evidence_valid = (
                "USER_TO_SYSTEM"
                in relationships
                or "BURN" in roles
            )

            if not burn_evidence_valid:
                issue = (
                    "burn relationship "
                    "or role missing"
                )

        elif (
            classification
            == "INTERNAL_TRANSFER"
        ):
            if not intelligence[
                "is_internal_transfer"
            ]:
                issue = (
                    "internal flag missing"
                )

        if issue is not None:
            inconsistencies.append(
                {
                    "txhash": (
                        transaction["txhash"]
                    ),
                    "classification": (
                        classification
                    ),
                    "issue": issue,
                }
            )

    return {
        "transactions": len(
            transactions
        ),
        "inconsistencies": (
            inconsistencies
        ),
        "reclassification_candidates": (
            reclassification_candidates
        ),
    }


def get_movement_counterparty(
    movement,
):
    wallet = normalize_address(
        RONIN_WALLET_ADDRESS
    )

    from_address = normalize_address(
        movement.get(
            "from_address"
        )
    )

    to_address = normalize_address(
        movement.get(
            "to_address"
        )
    )

    if from_address == wallet:
        return to_address

    if to_address == wallet:
        return from_address

    return None


def discover_high_confidence_counterparties(
    transactions,
):
    evidence = {}

    def add_evidence(
        address,
        role,
    ):
        if address is None:
            return

        if address in {
            normalize_address(
                RONIN_WALLET_ADDRESS
            ),
            normalize_address(
                ZERO_ADDRESS
            ),
        }:
            return

        if address not in evidence:
            evidence[address] = {
                "roles": set(),
                "evidence_count": 0,
            }

        evidence[address][
            "roles"
        ].add(role)

        evidence[address][
            "evidence_count"
        ] += 1

    for transaction in transactions:
        result = (
            classify_grouped_transaction(
                transaction
            )
        )

        classification = result[
            "classification"
        ]

        movements = transaction.get(
            "movements",
            [],
        )

        if classification in {
            "MARKETPLACE_BUY",
            "MARKETPLACE_SALE",
        }:
            for movement in movements:
                if (
                    movement.get("asset")
                    != "Ronin Wrapped Ether"
                ):
                    continue

                counterparty = (
                    get_movement_counterparty(
                        movement
                    )
                )

                add_evidence(
                    counterparty,
                    "MARKETPLACE",
                )

        elif classification == "TOKEN_SWAP":
            for movement in movements:
                counterparty = (
                    get_movement_counterparty(
                        movement
                    )
                )

                add_evidence(
                    counterparty,
                    "DEX",
                )

        elif (
            classification
            == "STAKING_OR_REWARD"
        ):
            for movement in movements:
                counterparty = (
                    get_movement_counterparty(
                        movement
                    )
                )

                add_evidence(
                    counterparty,
                    "STAKING",
                )

    candidates = []

    for address, details in (
        evidence.items()
    ):
        if len(
            details["roles"]
        ) != 1:
            continue

        role = next(
            iter(
                details["roles"]
            )
        )

        candidates.append(
            {
                "address": address,
                "role": role,
                "evidence_count": (
                    details[
                        "evidence_count"
                    ]
                ),
            }
        )

    return candidates


def register_discovered_counterparties(
    db_path,
    candidates,
):
    for candidate in candidates:
        role = candidate["role"]

        label = (
            f"Discovered {role.title()} "
            f"Contract"
        )

        upsert_wallet_registry_entry(
            db_path=db_path,
            address=candidate[
                "address"
            ],
            wallet_label=label,
            ownership_type="CONTRACT",
            wallet_role=role,
            source=(
                "AXIEOS_TRANSACTION_EVIDENCE"
            ),
        )




def refresh_ronin_sync_state_bounds(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    endpoint_tables = {
        "transactions": (
            "ronin_api_transactions_raw"
        ),
        "token_transfers": (
            "ronin_token_transfers_raw"
        ),
    }

    for endpoint, table_name in (
        endpoint_tables.items()
    ):
        row = connection.execute(
            f"""
            SELECT
                MAX(timestamp),
                MIN(timestamp)
            FROM {table_name}
            """
        ).fetchone()

        newest_timestamp = row[0]
        oldest_timestamp = row[1]

        connection.execute(
            """
            UPDATE ronin_sync_state
            SET
                newest_timestamp = ?,
                oldest_timestamp = ?,
                state_updated_at =
                    CURRENT_TIMESTAMP
            WHERE endpoint = ?
            """,
            (
                newest_timestamp,
                oldest_timestamp,
                endpoint,
            ),
        )

    connection.commit()
    connection.close()



def get_ronin_sync_state(
    db_path,
    endpoint,
):
    connection = sqlite3.connect(
        db_path
    )

    row = connection.execute(
        """
        SELECT
            endpoint,
            newest_timestamp,
            oldest_timestamp,
            backfill_cursor_json,
            backfill_complete
        FROM ronin_sync_state
        WHERE endpoint = ?
        """,
        (
            endpoint,
        ),
    ).fetchone()

    connection.close()

    if row is None:
        return None

    cursor = None

    if row[3]:
        cursor = json.loads(
            row[3]
        )

    return {
        "endpoint": row[0],
        "newest_timestamp": row[1],
        "oldest_timestamp": row[2],
        "backfill_cursor": cursor,
        "backfill_complete": bool(
            row[4]
        ),
    }


def ronin_timestamp_to_unix(
    timestamp,
):
    return int(
        datetime.fromisoformat(
            timestamp.replace(
                "Z",
                "+00:00",
            )
        ).timestamp()
    )


def get_legacy_csv_safety_boundary(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    transaction_oldest = (
        connection.execute(
            """
            SELECT MIN(timestamp)
            FROM ronin_api_transactions_raw
            """
        ).fetchone()[0]
    )

    transfer_oldest = (
        connection.execute(
            """
            SELECT MIN(timestamp)
            FROM ronin_token_transfers_raw
            """
        ).fetchone()[0]
    )

    candidates = [
        value
        for value in {
            transaction_oldest,
            transfer_oldest,
        }
        if value is not None
    ]

    if not candidates:
        connection.close()
        return None

    oldest_api_timestamp = min(
        candidates
    )

    oldest_api_unix = (
        ronin_timestamp_to_unix(
            oldest_api_timestamp
        )
    )

    row = connection.execute(
        """
        SELECT
            unixtimestamp,
            datetime
        FROM blockchain_transactions
        WHERE unixtimestamp < ?
        ORDER BY unixtimestamp DESC
        LIMIT 1
        """,
        (
            oldest_api_unix,
        ),
    ).fetchone()

    connection.close()

    if row is None:
        return None

    return {
        "unixtimestamp": row[0],
        "datetime": row[1],
    }


def get_oldest_staged_key(
    db_path,
    endpoint,
):
    connection = sqlite3.connect(
        db_path
    )

    if endpoint == "transactions":
        row = connection.execute(
            """
            SELECT tx_hash
            FROM ronin_api_transactions_raw
            ORDER BY
                timestamp ASC,
                block_number ASC
            LIMIT 1
            """
        ).fetchone()

    elif endpoint == "token_transfers":
        row = connection.execute(
            """
            SELECT transfer_key
            FROM ronin_token_transfers_raw
            ORDER BY
                timestamp ASC,
                block_number ASC,
                log_index ASC
            LIMIT 1
            """
        ).fetchone()

    else:
        connection.close()

        raise ValueError(
            f"Unknown endpoint: {endpoint}"
        )

    connection.close()

    if row is None:
        return None

    return row[0]


def get_backfill_url(
    endpoint,
):
    if endpoint == "transactions":
        return RONIN_TRANSACTIONS_URL

    if endpoint == "token_transfers":
        return RONIN_TOKEN_TRANSFERS_URL

    raise ValueError(
        f"Unknown endpoint: {endpoint}"
    )


def normalize_backfill_items(
    endpoint,
    response,
):
    items = response.get(
        "items",
        [],
    )

    if endpoint == "transactions":
        return normalize_transactions(
            items
        )

    if endpoint == "token_transfers":
        return normalize_token_transfers(
            items
        )

    raise ValueError(
        f"Unknown endpoint: {endpoint}"
    )


def get_backfill_item_key(
    endpoint,
    item,
):
    if endpoint == "transactions":
        return item["tx_hash"]

    if endpoint == "token_transfers":
        return item["transfer_key"]

    raise ValueError(
        f"Unknown endpoint: {endpoint}"
    )


def bootstrap_backfill_cursor(
    db_path,
    endpoint,
    max_scan_pages=100,
):
    oldest_key = get_oldest_staged_key(
        db_path,
        endpoint,
    )

    if oldest_key is None:
        return None, 0

    url = get_backfill_url(
        endpoint
    )

    response = fetch_json(
        url
    )

    pages_scanned = 0

    while response is not None:
        pages_scanned += 1

        items = normalize_backfill_items(
            endpoint,
            response,
        )

        keys = {
            get_backfill_item_key(
                endpoint,
                item,
            )
            for item in items
        }

        if oldest_key in keys:
            return (
                get_next_page_params(
                    response
                ),
                pages_scanned,
            )

        if (
            pages_scanned
            >= max_scan_pages
        ):
            raise RuntimeError(
                "Could not locate "
                "historical boundary"
            )

        next_cursor = (
            get_next_page_params(
                response
            )
        )

        if not next_cursor:
            return None, pages_scanned

        response = fetch_json(
            url,
            params=next_cursor,
        )

    return None, pages_scanned


def backfill_ronin_endpoint_batch(
    db_path,
    endpoint,
    max_pages=1,
):
    state = get_ronin_sync_state(
        db_path,
        endpoint,
    )

    if state["backfill_complete"]:
        return {
            "bootstrap_pages": 0,
            "pages_fetched": 0,
            "items_found": 0,
            "items_inserted": 0,
            "stop_reason": (
                "ALREADY_COMPLETE"
            ),
        }

    cursor = state[
        "backfill_cursor"
    ]

    bootstrap_pages = 0

    if cursor is None:
        (
            cursor,
            bootstrap_pages,
        ) = bootstrap_backfill_cursor(
            db_path,
            endpoint,
        )

    if cursor is None:
        set_ronin_backfill_complete(
            db_path,
            endpoint,
            True,
        )

        return {
            "bootstrap_pages": (
                bootstrap_pages
            ),
            "pages_fetched": 0,
            "items_found": 0,
            "items_inserted": 0,
            "stop_reason": "NO_NEXT_PAGE",
        }

    boundary = (
        get_legacy_csv_safety_boundary(
            db_path
        )
    )

    if boundary is None:
        raise RuntimeError(
            "Legacy CSV safety boundary "
            "could not be determined"
        )

    url = get_backfill_url(
        endpoint
    )

    pages_fetched = 0
    items_found = 0
    items_inserted = 0
    stop_reason = "BATCH_LIMIT"

    while pages_fetched < max_pages:
        response = fetch_json(
            url,
            params=cursor,
        )

        pages_fetched += 1

        items = normalize_backfill_items(
            endpoint,
            response,
        )

        safe_items = []
        boundary_reached = False

        for item in items:
            item_unix = (
                ronin_timestamp_to_unix(
                    item["timestamp"]
                )
            )

            if (
                item_unix
                <= boundary[
                    "unixtimestamp"
                ]
            ):
                boundary_reached = True
                break

            safe_items.append(
                item
            )

        items_found += len(
            safe_items
        )

        if endpoint == "transactions":
            inserted = (
                insert_raw_api_transactions(
                    db_path,
                    safe_items,
                )
            )

        else:
            inserted = (
                insert_raw_token_transfers(
                    db_path,
                    safe_items,
                )
            )

        items_inserted += inserted

        if boundary_reached:
            save_ronin_backfill_cursor(
                db_path,
                endpoint,
                None,
            )

            set_ronin_backfill_complete(
                db_path,
                endpoint,
                True,
            )

            stop_reason = (
                "LEGACY_CSV_BOUNDARY"
            )
            break

        next_cursor = (
            get_next_page_params(
                response
            )
        )

        if not next_cursor:
            save_ronin_backfill_cursor(
                db_path,
                endpoint,
                None,
            )

            set_ronin_backfill_complete(
                db_path,
                endpoint,
                True,
            )

            stop_reason = "NO_NEXT_PAGE"
            break

        save_ronin_backfill_cursor(
            db_path,
            endpoint,
            next_cursor,
        )

        cursor = next_cursor

    refresh_ronin_sync_state_bounds(
        db_path
    )

    return {
        "bootstrap_pages": (
            bootstrap_pages
        ),
        "pages_fetched": (
            pages_fetched
        ),
        "items_found": (
            items_found
        ),
        "items_inserted": (
            items_inserted
        ),
        "stop_reason": (
            stop_reason
        ),
    }



def save_ronin_backfill_cursor(
    db_path,
    endpoint,
    cursor,
):
    if endpoint not in RONIN_SYNC_ENDPOINTS:
        raise ValueError(
            f"Unknown Ronin endpoint: "
            f"{endpoint}"
        )

    cursor_json = None

    if cursor is not None:
        cursor_json = json.dumps(
            cursor,
            sort_keys=True,
        )

    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        UPDATE ronin_sync_state
        SET
            backfill_cursor_json = ?,
            state_updated_at =
                CURRENT_TIMESTAMP
        WHERE endpoint = ?
        """,
        (
            cursor_json,
            endpoint,
        ),
    )

    connection.commit()
    connection.close()


def set_ronin_backfill_complete(
    db_path,
    endpoint,
    complete,
):
    if endpoint not in RONIN_SYNC_ENDPOINTS:
        raise ValueError(
            f"Unknown Ronin endpoint: "
            f"{endpoint}"
        )

    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        UPDATE ronin_sync_state
        SET
            backfill_complete = ?,
            state_updated_at =
                CURRENT_TIMESTAMP
        WHERE endpoint = ?
        """,
        (
            1 if complete else 0,
            endpoint,
        ),
    )

    connection.commit()
    connection.close()

def initialize_ronin_sync_state_table(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        ronin_sync_state (
            endpoint TEXT PRIMARY KEY,
            newest_timestamp TEXT,
            oldest_timestamp TEXT,
            backfill_cursor_json TEXT,
            backfill_complete INTEGER NOT NULL
                DEFAULT 0,
            state_updated_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    for endpoint in sorted(
        RONIN_SYNC_ENDPOINTS
    ):
        connection.execute(
            """
            INSERT OR IGNORE INTO
                ronin_sync_state (
                    endpoint
                )
            VALUES (?)
            """,
            (
                endpoint,
            ),
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


def store_intelligent_transaction_classifications(
    db_path,
    transactions,
):
    connection = sqlite3.connect(
        db_path
    )

    processed = 0

    for transaction in transactions:
        result = (
            classify_transaction_with_intelligence(
                db_path,
                transaction,
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

        processed += 1

    connection.commit()
    connection.close()

    return processed






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


def build_empty_accounting_record(
    txhash,
    datetime_value,
    classification,
):
    return {
        "accounting_key": txhash,
        "txhash": txhash,
        "datetime": datetime_value,
        "event_type": "UNKNOWN",
        "classification": classification,
        "asset_name": None,
        "asset_token_id": None,
        "asset_category": None,
        "quantity": None,
        "direction": None,
        "payment_asset": None,
        "gross_amount": None,
        "marketplace_fee": None,
        "net_amount": None,
        "cost_basis": None,
        "realized_pl": None,
        "counterparty_role": None,
        "is_internal_transfer": False,
        "accounting_status": "REVIEW",
        "accounting_version": ACCOUNTING_VERSION,
    }


def validate_accounting_record(
    record,
):
    fields_valid = (
        set(record.keys())
        == ACCOUNTING_RECORD_FIELDS
    )

    status_valid = (
        record["accounting_status"]
        in ACCOUNTING_STATUSES
    )

    event_type_valid = (
        record["event_type"]
        in ACCOUNTING_EVENT_TYPES
    )

    version_valid = (
        record["accounting_version"]
        == ACCOUNTING_VERSION
    )

    return (
        fields_valid
        and status_valid
        and event_type_valid
        and version_valid
    )


def select_primary_accounting_movement(
    transaction,
    classification,
):
    movements = transaction.get(
        "movements",
        [],
    )

    if not movements:
        return None

    if classification == "MARKETPLACE_BUY":
        for movement in movements:
            if (
                movement.get("asset")
                != "Ronin Wrapped Ether"
                and get_movement_direction(
                    movement
                )
                == "IN"
            ):
                return movement

    if classification == "MARKETPLACE_SALE":
        for movement in movements:
            if (
                movement.get("asset")
                != "Ronin Wrapped Ether"
                and get_movement_direction(
                    movement
                )
                == "OUT"
            ):
                return movement

    if classification == "TOKEN_SWAP":
        for movement in movements:
            if (
                get_movement_direction(
                    movement
                )
                == "OUT"
            ):
                return movement

    if classification in {
        "TRANSFER_OUT",
        "CONSUMABLE_BURN",
        "NFT_BURN",
        "TOKEN_BURN",
    }:
        for movement in movements:
            if (
                get_movement_direction(
                    movement
                )
                == "IN"
            ):
                return movement

    if classification in {
        "TRANSFER_OUT",
        "CONSUMABLE_BURN",
        "NFT_BURN",
    }:
        for movement in movements:
            if (
                get_movement_direction(
                    movement
                )
                == "OUT"
            ):
                return movement

    for movement in movements:
        direction = (
            get_movement_direction(
                movement
            )
        )

        if direction in {
            "IN",
            "OUT",
        }:
            return movement

    return None

def find_accounting_asset_category(
    db_path,
    txhash,
    asset_name,
    direction,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT
            token_address,
            token_id,
            token_name,
            from_address,
            to_address
        FROM ronin_token_transfers_raw
        WHERE tx_hash = ?
        """,
        (
            txhash,
        ),
    ).fetchall()

    connection.close()

    wallet = normalize_address(
        RONIN_WALLET_ADDRESS
    )

    asset_registry = (
        load_asset_registry_map(
            db_path
        )
    )

    for row in rows:
        (
            token_address,
            token_id,
            token_name,
            from_address,
            to_address,
        ) = row

        if token_name != asset_name:
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

        if (
            direction == "IN"
            and to_normalized != wallet
        ):
            continue

        if (
            direction == "OUT"
            and from_normalized != wallet
        ):
            continue

        asset_key = build_asset_registry_key(
            token_address,
            token_id,
        )

        return asset_registry.get(
            asset_key
        )

    return None


def find_accounting_asset_token_id(
    db_path,
    txhash,
    asset_name,
    direction,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT
            token_id,
            token_name,
            from_address,
            to_address
        FROM ronin_token_transfers_raw
        WHERE tx_hash = ?
        ORDER BY log_index
        """,
        (
            txhash,
        ),
    ).fetchall()

    connection.close()

    wallet = normalize_address(
        RONIN_WALLET_ADDRESS
    )

    token_ids = []

    for (
        token_id,
        token_name,
        from_address,
        to_address,
    ) in rows:
        if token_name != asset_name:
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

        if (
            direction == "IN"
            and to_normalized != wallet
        ):
            continue

        if (
            direction == "OUT"
            and from_normalized != wallet
        ):
            continue

        if token_id is not None:
            token_ids.append(
                str(token_id)
            )

    token_ids = list(
        dict.fromkeys(
            token_ids
        )
    )

    if len(token_ids) == 1:
        return token_ids[0]

    if len(token_ids) > 1:
        return ",".join(
            token_ids
        )

    return None



def build_basic_accounting_record(
    db_path,
    transaction,
):
    classification_result = (
        classify_transaction_with_intelligence(
            db_path,
            transaction,
        )
    )

    classification = (
        classification_result[
            "classification"
        ]
    )

    event_type = (
        CLASSIFICATION_TO_ACCOUNTING_EVENT.get(
            classification,
            "UNKNOWN",
        )
    )

    record = build_empty_accounting_record(
        txhash=transaction["txhash"],
        datetime_value=transaction.get(
            "datetime"
        ),
        classification=classification,
    )

    record[
        "event_type"
    ] = event_type

    primary_movement = (
        select_primary_accounting_movement(
            transaction,
            classification,
        )
    )

    if primary_movement is not None:
        direction = (
            get_movement_direction(
                primary_movement
            )
        )

        record[
            "asset_name"
        ] = primary_movement.get(
            "asset"
        )

        record[
            "direction"
        ] = direction

        if direction == "IN":
            record[
                "quantity"
            ] = str(
                primary_movement.get(
                    "value_in",
                    "0",
                )
            )

        elif direction == "OUT":
            record[
                "quantity"
            ] = str(
                primary_movement.get(
                    "value_out",
                    "0",
                )
            )

        record[
            "asset_category"
        ] = find_accounting_asset_category(
            db_path,
            transaction["txhash"],
            record["asset_name"],
            direction,
        )

    intelligence = (
        build_transaction_intelligence(
            db_path,
            transaction,
            load_asset_registry_map(
                db_path
            ),
        )
    )

    record[
        "is_internal_transfer"
    ] = intelligence[
        "is_internal_transfer"
    ]

    roles = {
        counterparty["role"]
        for counterparty
        in intelligence[
            "counterparties"
        ]
    }

    if len(roles) == 1:
        record[
            "counterparty_role"
        ] = next(
            iter(roles)
        )

    if classification == "UNKNOWN":
        record[
            "accounting_status"
        ] = "REVIEW"

    elif classification == "INTERNAL_TRANSFER":
        record[
            "accounting_status"
        ] = "NON_TAXABLE_INTERNAL"

    else:
        record[
            "accounting_status"
        ] = "INFORMATIONAL"

    return record


def build_current_marketplace_economics_map(
    transactions,
):
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

    return {
        event["txhash"]: event
        for event in events
    }


def enrich_non_marketplace_accounting_record(
    db_path,
    record,
    transaction,
):
    classification = record[
        "classification"
    ]

    if classification in {
        "MARKETPLACE_BUY",
        "MARKETPLACE_SALE",
    }:
        return record

    if (
        record["asset_name"] is not None
        and record["direction"] is not None
    ):
        record[
            "asset_token_id"
        ] = find_accounting_asset_token_id(
            db_path,
            transaction["txhash"],
            record["asset_name"],
            record["direction"],
        )

    if classification == "TOKEN_SWAP":
        incoming_movements = [
            movement
            for movement
            in transaction.get(
                "movements",
                [],
            )
            if (
                get_movement_direction(
                    movement
                )
                == "IN"
            )
        ]

        if incoming_movements:
            incoming = (
                incoming_movements[0]
            )

            record[
                "payment_asset"
            ] = incoming.get(
                "asset"
            )

            record[
                "gross_amount"
            ] = str(
                incoming.get(
                    "value_in",
                    "0",
                )
            )

            record[
                "net_amount"
            ] = record[
                "gross_amount"
            ]

        # Swap cost basis / realized P&L
        # is not yet implemented.
        record[
            "accounting_status"
        ] = "REVIEW"

    elif classification in {
        "MINT_OR_CLAIM",
        "STAKING_OR_REWARD",
        "CONSUMABLE_BURN",
        "NFT_BURN",
        "TOKEN_BURN",
    }:
        if (
            record["asset_name"]
            is not None
            and record["quantity"]
            is not None
        ):
            record[
                "accounting_status"
            ] = "READY"
        else:
            record[
                "accounting_status"
            ] = "REVIEW"

    elif classification in {
        "TRANSFER_IN",
        "TRANSFER_OUT",
    }:
        # Ownership of the opposite wallet
        # is not yet proven.
        record[
            "accounting_status"
        ] = "REVIEW"

    elif classification == "UNKNOWN":
        record[
            "accounting_status"
        ] = "REVIEW"

    return record


def apply_internal_transfer_accounting_treatment(
    record,
):
    if not record[
        "is_internal_transfer"
    ]:
        return record

    record[
        "classification"
    ] = "INTERNAL_TRANSFER"

    record[
        "event_type"
    ] = "INTERNAL_TRANSFER"

    record[
        "accounting_status"
    ] = "NON_TAXABLE_INTERNAL"

    # Internal wallet movements do not
    # create proceeds or realized P/L.
    record[
        "payment_asset"
    ] = None

    record[
        "gross_amount"
    ] = None

    record[
        "marketplace_fee"
    ] = None

    record[
        "net_amount"
    ] = None

    record[
        "cost_basis"
    ] = None

    record[
        "realized_pl"
    ] = None

    return record


def build_complete_accounting_record(
    db_path,
    transaction,
    economics_map,
):
    record = (
        build_basic_accounting_record(
            db_path,
            transaction,
        )
    )

    if record["classification"] in {
        "MARKETPLACE_BUY",
        "MARKETPLACE_SALE",
    }:
        record = (
            enrich_accounting_record_with_marketplace_economics(
                record,
                economics_map,
            )
        )

    else:
        record = (
            enrich_non_marketplace_accounting_record(
                db_path,
                record,
                transaction,
            )
        )

    record = (
        apply_internal_transfer_accounting_treatment(
            record
        )
    )

    return record


def store_accounting_records(
    db_path,
    records,
):
    connection = sqlite3.connect(
        db_path
    )

    processed = 0

    for record in records:
        connection.execute(
            """
            INSERT INTO
                blockchain_accounting_records (
                    accounting_key,
                    txhash,
                    datetime,
                    event_type,
                    classification,
                    asset_name,
                    asset_token_id,
                    asset_category,
                    quantity,
                    direction,
                    payment_asset,
                    gross_amount,
                    marketplace_fee,
                    net_amount,
                    cost_basis,
                    realized_pl,
                    counterparty_role,
                    is_internal_transfer,
                    accounting_status,
                    accounting_version
                )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(accounting_key)
            DO UPDATE SET
                txhash =
                    excluded.txhash,
                datetime =
                    excluded.datetime,
                event_type =
                    excluded.event_type,
                classification =
                    excluded.classification,
                asset_name =
                    excluded.asset_name,
                asset_token_id =
                    excluded.asset_token_id,
                asset_category =
                    excluded.asset_category,
                quantity =
                    excluded.quantity,
                direction =
                    excluded.direction,
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
                counterparty_role =
                    excluded.counterparty_role,
                is_internal_transfer =
                    excluded.is_internal_transfer,
                accounting_status =
                    excluded.accounting_status,
                accounting_version =
                    excluded.accounting_version,
                updated_at =
                    CURRENT_TIMESTAMP
            """,
            (
                record[
                    "accounting_key"
                ],
                record["txhash"],
                record["datetime"],
                record["event_type"],
                record[
                    "classification"
                ],
                record["asset_name"],
                record[
                    "asset_token_id"
                ],
                record[
                    "asset_category"
                ],
                record["quantity"],
                record["direction"],
                record[
                    "payment_asset"
                ],
                record[
                    "gross_amount"
                ],
                record[
                    "marketplace_fee"
                ],
                record["net_amount"],
                record["cost_basis"],
                record["realized_pl"],
                record[
                    "counterparty_role"
                ],
                (
                    1
                    if record[
                        "is_internal_transfer"
                    ]
                    else 0
                ),
                record[
                    "accounting_status"
                ],
                record[
                    "accounting_version"
                ],
            ),
        )

        processed += 1

    connection.commit()
    connection.close()

    return processed


def validate_accounting_reconciliation(
    db_path,
):
    transactions = (
        group_ledger_rows_by_txhash(
            db_path
        )
    )

    economics_map = (
        build_current_marketplace_economics_map(
            transactions
        )
    )

    connection = sqlite3.connect(
        db_path
    )

    accounting_rows = connection.execute(
        """
        SELECT
            accounting_key,
            txhash,
            event_type,
            classification,
            accounting_status,
            realized_pl
        FROM blockchain_accounting_records
        """
    ).fetchall()

    classification_rows = (
        connection.execute(
            """
            SELECT
                txhash,
                classification
            FROM
                blockchain_transaction_classifications
            """
        ).fetchall()
    )

    connection.close()

    classification_map = {
        txhash: classification
        for txhash, classification
        in classification_rows
    }

    duplicate_keys = (
        len(accounting_rows)
        - len(
            {
                row[0]
                for row in accounting_rows
            }
        )
    )

    missing_classifications = 0
    classification_mismatches = 0
    event_type_mismatches = 0

    status_counts = {}
    event_counts = {}

    accounting_marketplace = 0

    accounting_realized_sales = 0
    accounting_realized_pl = (
        Decimal("0")
    )

    for row in accounting_rows:
        (
            accounting_key,
            txhash,
            event_type,
            classification,
            accounting_status,
            realized_pl,
        ) = row

        stored_classification = (
            classification_map.get(
                txhash
            )
        )

        if stored_classification is None:
            missing_classifications += 1

        elif (
            stored_classification
            != classification
        ):
            classification_mismatches += 1

        expected_event_type = (
            CLASSIFICATION_TO_ACCOUNTING_EVENT.get(
                classification,
                "UNKNOWN",
            )
        )

        if (
            event_type
            != expected_event_type
        ):
            event_type_mismatches += 1

        status_counts[
            accounting_status
        ] = (
            status_counts.get(
                accounting_status,
                0,
            )
            + 1
        )

        event_counts[
            event_type
        ] = (
            event_counts.get(
                event_type,
                0,
            )
            + 1
        )

        if event_type in {
            "ASSET_PURCHASE",
            "ASSET_SALE",
        }:
            accounting_marketplace += 1

        if (
            event_type == "ASSET_SALE"
            and realized_pl is not None
        ):
            accounting_realized_sales += 1

            accounting_realized_pl += (
                Decimal(
                    str(realized_pl)
                )
            )

    economics_realized_sales = 0
    economics_realized_pl = (
        Decimal("0")
    )

    for event in economics_map.values():
        realized_pl = event.get(
            "realized_pl"
        )

        if realized_pl is not None:
            economics_realized_sales += 1

            economics_realized_pl += (
                Decimal(
                    str(realized_pl)
                )
            )

    status_total = sum(
        status_counts.values()
    )

    event_total = sum(
        event_counts.values()
    )

    transaction_count_valid = (
        len(accounting_rows)
        == len(transactions)
    )

    status_total_valid = (
        status_total
        == len(accounting_rows)
    )

    event_total_valid = (
        event_total
        == len(accounting_rows)
    )

    marketplace_valid = (
        accounting_marketplace
        == len(economics_map)
    )

    realized_sales_valid = (
        accounting_realized_sales
        == economics_realized_sales
    )

    realized_pl_valid = (
        accounting_realized_pl
        == economics_realized_pl
    )

    classification_valid = (
        missing_classifications == 0
        and classification_mismatches == 0
    )

    event_mapping_valid = (
        event_type_mismatches == 0
    )

    validation = (
        transaction_count_valid
        and duplicate_keys == 0
        and status_total_valid
        and event_total_valid
        and marketplace_valid
        and realized_sales_valid
        and realized_pl_valid
        and classification_valid
        and event_mapping_valid
    )

    return {
        "transactions": len(
            transactions
        ),
        "accounting_records": len(
            accounting_rows
        ),
        "duplicate_keys": duplicate_keys,
        "missing_classifications": (
            missing_classifications
        ),
        "classification_mismatches": (
            classification_mismatches
        ),
        "event_type_mismatches": (
            event_type_mismatches
        ),
        "marketplace_records": (
            accounting_marketplace
        ),
        "economic_events": len(
            economics_map
        ),
        "realized_sales": (
            accounting_realized_sales
        ),
        "economics_realized_sales": (
            economics_realized_sales
        ),
        "realized_pl": str(
            accounting_realized_pl
        ),
        "economics_realized_pl": str(
            economics_realized_pl
        ),
        "status_counts": status_counts,
        "event_counts": event_counts,
        "validation": validation,
    }





def enrich_accounting_record_with_marketplace_economics(
    record,
    economics_map,
):
    if record["classification"] not in {
        "MARKETPLACE_BUY",
        "MARKETPLACE_SALE",
    }:
        return record

    event = economics_map.get(
        record["txhash"]
    )

    if event is None:
        record[
            "accounting_status"
        ] = "REVIEW"

        return record

    record[
        "asset_name"
    ] = event["asset_name"]

    record[
        "asset_token_id"
    ] = event["asset_token_id"]

    record[
        "quantity"
    ] = event["quantity"]

    record[
        "payment_asset"
    ] = event["payment_asset"]

    record[
        "gross_amount"
    ] = event["gross_amount"]

    record[
        "marketplace_fee"
    ] = event["marketplace_fee"]

    record[
        "net_amount"
    ] = event["net_amount"]

    record[
        "cost_basis"
    ] = event["cost_basis"]

    record[
        "realized_pl"
    ] = event["realized_pl"]

    if (
        record["classification"]
        == "MARKETPLACE_BUY"
    ):
        if (
            record["gross_amount"]
            is not None
            and record[
                "asset_token_id"
            ]
            is not None
        ):
            record[
                "accounting_status"
            ] = "READY"
        else:
            record[
                "accounting_status"
            ] = "REVIEW"

    elif (
        record["classification"]
        == "MARKETPLACE_SALE"
    ):
        if (
            record["net_amount"]
            is not None
            and record[
                "realized_pl"
            ]
            is not None
        ):
            record[
                "accounting_status"
            ] = "READY"
        else:
            record[
                "accounting_status"
            ] = "REVIEW"

    return record



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


def audit_transfer_review_counterparties(
    db_path,
):
    queue = load_accounting_review_queue(
        db_path
    )

    transfer_records = [
        record
        for record in queue
        if record["event_type"] in {
            "TRANSFER_IN",
            "TRANSFER_OUT",
        }
    ]

    connection = sqlite3.connect(
        db_path
    )

    wallet = normalize_address(
        RONIN_WALLET_ADDRESS
    )

    counterparties = {}

    for record in transfer_records:
        rows = connection.execute(
            """
            SELECT
                from_address,
                to_address
            FROM blockchain_transactions
            WHERE txhash = ?
            """,
            (
                record["txhash"],
            ),
        ).fetchall()

        addresses = set()

        for (
            from_address,
            to_address,
        ) in rows:
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

            if (
                record["event_type"]
                == "TRANSFER_IN"
                and to_normalized == wallet
                and from_normalized
                != wallet
            ):
                addresses.add(
                    from_normalized
                )

            elif (
                record["event_type"]
                == "TRANSFER_OUT"
                and from_normalized == wallet
                and to_normalized
                != wallet
            ):
                addresses.add(
                    to_normalized
                )

        for address in addresses:
            registry_entry = (
                get_wallet_registry_entry(
                    db_path,
                    address,
                )
            )

            if address not in counterparties:
                counterparties[address] = {
                    "address": address,
                    "ownership_type": (
                        registry_entry[
                            "ownership_type"
                        ]
                    ),
                    "wallet_role": (
                        registry_entry[
                            "wallet_role"
                        ]
                    ),
                    "transactions": set(),
                }

            counterparties[
                address
            ]["transactions"].add(
                record["txhash"]
            )

    connection.close()

    results = []

    for entry in counterparties.values():
        results.append(
            {
                "address": entry[
                    "address"
                ],
                "ownership_type": entry[
                    "ownership_type"
                ],
                "wallet_role": entry[
                    "wallet_role"
                ],
                "transaction_count": len(
                    entry[
                        "transactions"
                    ]
                ),
            }
        )

    results.sort(
        key=lambda item: (
            -item["transaction_count"],
            item["address"],
        )
    )

    return results


















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


def load_known_transaction_hashes(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT tx_hash
        FROM ronin_api_transactions_raw
        """
    ).fetchall()

    connection.close()

    return {
        row[0]
        for row in rows
    }


def load_known_transfer_keys(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT transfer_key
        FROM ronin_token_transfers_raw
        """
    ).fetchall()

    connection.close()

    return {
        row[0]
        for row in rows
    }


def fetch_incremental_token_transfers(
    db_path,
    max_pages=20,
):
    known_keys = (
        load_known_transfer_keys(
            db_path
        )
    )

    new_transfers = []

    response = fetch_json(
        RONIN_TOKEN_TRANSFERS_URL
    )

    pages_fetched = 0
    reached_known = False
    stop_reason = None

    while response is not None:
        pages_fetched += 1

        transfers = (
            normalize_token_transfers(
                response.get(
                    "items",
                    [],
                )
            )
        )

        for transfer in transfers:
            transfer_key = transfer[
                "transfer_key"
            ]

            if transfer_key in known_keys:
                reached_known = True
                stop_reason = (
                    "KNOWN_TRANSFER"
                )
                break

            new_transfers.append(
                transfer
            )

        if reached_known:
            break

        if pages_fetched >= max_pages:
            stop_reason = "MAX_PAGES"
            break

        next_page_params = (
            get_next_page_params(
                response
            )
        )

        if not next_page_params:
            stop_reason = "NO_NEXT_PAGE"
            break

        response = fetch_json(
            RONIN_TOKEN_TRANSFERS_URL,
            params=next_page_params,
        )

    unique_transfers = {}

    for transfer in new_transfers:
        unique_transfers[
            transfer["transfer_key"]
        ] = transfer

    return {
        "transfers": list(
            unique_transfers.values()
        ),
        "pages_fetched": (
            pages_fetched
        ),
        "known_boundary_reached": (
            reached_known
        ),
        "stop_reason": (
            stop_reason
        ),
    }




def fetch_incremental_transactions(
    db_path,
    max_pages=20,
):
    known_hashes = (
        load_known_transaction_hashes(
            db_path
        )
    )

    new_transactions = []

    response = fetch_json(
        RONIN_TRANSACTIONS_URL
    )

    pages_fetched = 0
    reached_known = False
    stop_reason = None

    while response is not None:
        pages_fetched += 1

        transactions = (
            normalize_transactions(
                response.get(
                    "items",
                    [],
                )
            )
        )

        for transaction in transactions:
            tx_hash = transaction[
                "tx_hash"
            ]

            if tx_hash in known_hashes:
                reached_known = True
                stop_reason = (
                    "KNOWN_TRANSACTION"
                )
                break

            new_transactions.append(
                transaction
            )

        if reached_known:
            break

        if pages_fetched >= max_pages:
            stop_reason = "MAX_PAGES"
            break

        next_page_params = (
            get_next_page_params(
                response
            )
        )

        if not next_page_params:
            stop_reason = "NO_NEXT_PAGE"
            break

        response = fetch_json(
            RONIN_TRANSACTIONS_URL,
            params=next_page_params,
        )

    new_transactions = (
        deduplicate_transactions(
            new_transactions
        )
    )

    return {
        "transactions": (
            new_transactions
        ),
        "pages_fetched": (
            pages_fetched
        ),
        "known_boundary_reached": (
            reached_known
        ),
        "stop_reason": (
            stop_reason
        ),
    }


def get_raw_sync_counts(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    transaction_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM ronin_api_transactions_raw
            """
        ).fetchone()[0]
    )

    transfer_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM ronin_token_transfers_raw
            """
        ).fetchone()[0]
    )

    connection.close()

    return {
        "transactions": transaction_count,
        "token_transfers": transfer_count,
    }


def get_blockchain_ledger_count(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    count = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_transactions
        """
    ).fetchone()[0]

    connection.close()

    return count


def materialize_staged_transfers_to_ledger(
    db_path,
):
    staged_transfers = (
        load_staged_transfers(
            db_path
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

        ledger_row = (
            build_ledger_row_from_transfer(
                transfer
            )
        )

        ledger_rows.append(
            ledger_row
        )

    inserted = insert_ledger_rows(
        db_path,
        ledger_rows,
    )

    return {
        "staged_transfers": len(
            staged_transfers
        ),
        "ledger_rows_prepared": len(
            ledger_rows
        ),
        "ledger_rows_inserted": (
            inserted
        ),
    }


def stage_incremental_ronin_data(
    db_path,
    max_pages=20,
):
    transaction_result = (
        fetch_incremental_transactions(
            db_path,
            max_pages=max_pages,
        )
    )

    transfer_result = (
        fetch_incremental_token_transfers(
            db_path,
            max_pages=max_pages,
        )
    )

    transactions_inserted = (
        insert_raw_api_transactions(
            db_path,
            transaction_result[
                "transactions"
            ],
        )
    )

    transfers_inserted = (
        insert_raw_token_transfers(
            db_path,
            transfer_result[
                "transfers"
            ],
        )
    )

    refresh_ronin_sync_state_bounds(
        db_path
    )

    return {
        "transactions_found": len(
            transaction_result[
                "transactions"
            ]
        ),
        "transactions_inserted": (
            transactions_inserted
        ),
        "transaction_pages": (
            transaction_result[
                "pages_fetched"
            ]
        ),
        "transaction_stop": (
            transaction_result[
                "stop_reason"
            ]
        ),
        "transfers_found": len(
            transfer_result[
                "transfers"
            ]
        ),
        "transfers_inserted": (
            transfers_inserted
        ),
        "transfer_pages": (
            transfer_result[
                "pages_fetched"
            ]
        ),
        "transfer_stop": (
            transfer_result[
                "stop_reason"
            ]
        ),
    }







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
        "claimPendingRewards",
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


def run_ronin_sync_state_test():
    initialize_ronin_sync_state_table(
        AXIEOS_DB_PATH
    )

    refresh_ronin_sync_state_bounds(
        AXIEOS_DB_PATH
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    rows = connection.execute(
        """
        SELECT
            endpoint,
            newest_timestamp,
            oldest_timestamp,
            backfill_cursor_json,
            backfill_complete
        FROM ronin_sync_state
        ORDER BY endpoint
        """
    ).fetchall()

    connection.close()

    print(
        "\nRONIN SYNC STATE"
    )

    print(
        "Endpoints:",
        len(rows),
    )

    for row in rows:
        print(
            "\nEndpoint:",
            row[0],
        )

        print(
            "Newest:",
            row[1],
        )

        print(
            "Oldest:",
            row[2],
        )

        print(
            "Backfill cursor:",
            row[3],
        )

        print(
            "Backfill complete:",
            bool(row[4]),
        )


def run_incremental_transaction_test():
    result = (
        fetch_incremental_transactions(
            AXIEOS_DB_PATH,
            max_pages=20,
        )
    )

    transactions = result[
        "transactions"
    ]

    print(
        "\nRONIN INCREMENTAL TRANSACTIONS"
    )

    print(
        "Pages fetched:",
        result[
            "pages_fetched"
        ],
    )

    print(
        "New transactions:",
        len(transactions),
    )

    print(
        "Known boundary reached:",
        result[
            "known_boundary_reached"
        ],
    )

    print(
        "Stop reason:",
        result[
            "stop_reason"
        ],
    )

    if transactions:
        print(
            "\nNEW TRANSACTIONS"
        )

        for transaction in (
            transactions[:10]
        ):
            print(
                transaction[
                    "timestamp"
                ],
                transaction[
                    "tx_hash"
                ],
            )


def run_incremental_transfer_test():
    result = (
        fetch_incremental_token_transfers(
            AXIEOS_DB_PATH,
            max_pages=20,
        )
    )

    transfers = result[
        "transfers"
    ]

    print(
        "\nRONIN INCREMENTAL TOKEN TRANSFERS"
    )

    print(
        "Pages fetched:",
        result[
            "pages_fetched"
        ],
    )

    print(
        "New transfers:",
        len(transfers),
    )

    print(
        "Known boundary reached:",
        result[
            "known_boundary_reached"
        ],
    )

    print(
        "Stop reason:",
        result[
            "stop_reason"
        ],
    )

    if transfers:
        print(
            "\nNEW TRANSFERS"
        )

        for transfer in transfers[:15]:
            print(
                transfer["timestamp"],
                transfer["tx_hash"],
                transfer["token_name"],
                transfer["token_id"],
                transfer["amount_raw"],
            )


def run_incremental_staging_test():
    initialize_ronin_sync_state_table(
        AXIEOS_DB_PATH
    )

    before = get_raw_sync_counts(
        AXIEOS_DB_PATH
    )

    result = stage_incremental_ronin_data(
        AXIEOS_DB_PATH,
        max_pages=20,
    )

    after = get_raw_sync_counts(
        AXIEOS_DB_PATH
    )

    transaction_delta = (
        after["transactions"]
        - before["transactions"]
    )

    transfer_delta = (
        after["token_transfers"]
        - before["token_transfers"]
    )

    staging_valid = (
        transaction_delta
        == result[
            "transactions_inserted"
        ]
        and transfer_delta
        == result[
            "transfers_inserted"
        ]
    )

    print(
        "\nRONIN INCREMENTAL STAGING"
    )

    print(
        "Transactions before:",
        before["transactions"],
    )

    print(
        "Transactions found:",
        result[
            "transactions_found"
        ],
    )

    print(
        "Transactions inserted:",
        result[
            "transactions_inserted"
        ],
    )

    print(
        "Transactions after:",
        after["transactions"],
    )

    print(
        "Transaction pages:",
        result[
            "transaction_pages"
        ],
    )

    print(
        "Transaction stop:",
        result[
            "transaction_stop"
        ],
    )

    print()

    print(
        "Transfers before:",
        before["token_transfers"],
    )

    print(
        "Transfers found:",
        result[
            "transfers_found"
        ],
    )

    print(
        "Transfers inserted:",
        result[
            "transfers_inserted"
        ],
    )

    print(
        "Transfers after:",
        after["token_transfers"],
    )

    print(
        "Transfer pages:",
        result[
            "transfer_pages"
        ],
    )

    print(
        "Transfer stop:",
        result[
            "transfer_stop"
        ],
    )

    print()

    print(
        "Staging validation:",
        (
            "PASS"
            if staging_valid
            else "FAIL"
        ),
    )


def run_incremental_ledger_test():
    before = (
        get_blockchain_ledger_count(
            AXIEOS_DB_PATH
        )
    )

    result = (
        materialize_staged_transfers_to_ledger(
            AXIEOS_DB_PATH
        )
    )

    after = (
        get_blockchain_ledger_count(
            AXIEOS_DB_PATH
        )
    )

    inserted_delta = (
        after - before
    )

    validation_passed = (
        inserted_delta
        == result[
            "ledger_rows_inserted"
        ]
    )

    print(
        "\nRONIN INCREMENTAL LEDGER"
    )

    print(
        "Ledger rows before:",
        before,
    )

    print(
        "Staged transfers:",
        result[
            "staged_transfers"
        ],
    )

    print(
        "Ledger rows prepared:",
        result[
            "ledger_rows_prepared"
        ],
    )

    print(
        "New ledger rows:",
        result[
            "ledger_rows_inserted"
        ],
    )

    print(
        "Ledger rows after:",
        after,
    )

    print(
        "Ledger delta:",
        inserted_delta,
    )

    print(
        "Validation:",
        (
            "PASS"
            if validation_passed
            else "FAIL"
        ),
    )


def run_backfill_cursor_state_test():
    initialize_ronin_sync_state_table(
        AXIEOS_DB_PATH
    )

    endpoint = "transactions"

    original = get_ronin_sync_state(
        AXIEOS_DB_PATH,
        endpoint,
    )

    test_cursor = {
        "index": 99,
        "hash": "0xtestcursor",
        "block_number": 123456,
        "items_count": 50,
    }

    save_ronin_backfill_cursor(
        AXIEOS_DB_PATH,
        endpoint,
        test_cursor,
    )

    set_ronin_backfill_complete(
        AXIEOS_DB_PATH,
        endpoint,
        False,
    )

    stored = get_ronin_sync_state(
        AXIEOS_DB_PATH,
        endpoint,
    )

    cursor_valid = (
        stored["backfill_cursor"]
        == test_cursor
    )

    complete_valid = (
        stored["backfill_complete"]
        is False
    )

    save_ronin_backfill_cursor(
        AXIEOS_DB_PATH,
        endpoint,
        original["backfill_cursor"],
    )

    set_ronin_backfill_complete(
        AXIEOS_DB_PATH,
        endpoint,
        original["backfill_complete"],
    )

    restored = get_ronin_sync_state(
        AXIEOS_DB_PATH,
        endpoint,
    )

    restore_valid = (
        restored["backfill_cursor"]
        == original["backfill_cursor"]
        and restored["backfill_complete"]
        == original["backfill_complete"]
    )

    print(
        "\nRONIN BACKFILL CURSOR STATE"
    )

    print(
        "Endpoint:",
        endpoint,
    )

    print(
        "Cursor round trip:",
        "PASS" if cursor_valid else "FAIL",
    )

    print(
        "Complete flag round trip:",
        "PASS" if complete_valid else "FAIL",
    )

    print(
        "Original state restored:",
        "PASS" if restore_valid else "FAIL",
    )

    print(
        "Validation:",
        (
            "PASS"
            if (
                cursor_valid
                and complete_valid
                and restore_valid
            )
            else "FAIL"
        ),
    )


def run_backfill_cursor_state_test():
    initialize_ronin_sync_state_table(
        AXIEOS_DB_PATH
    )

    endpoint = "transactions"

    original = get_ronin_sync_state(
        AXIEOS_DB_PATH,
        endpoint,
    )

    test_cursor = {
        "index": 99,
        "hash": "0xtestcursor",
        "block_number": 123456,
        "items_count": 50,
    }

    save_ronin_backfill_cursor(
        AXIEOS_DB_PATH,
        endpoint,
        test_cursor,
    )

    set_ronin_backfill_complete(
        AXIEOS_DB_PATH,
        endpoint,
        False,
    )

    stored = get_ronin_sync_state(
        AXIEOS_DB_PATH,
        endpoint,
    )

    cursor_valid = (
        stored["backfill_cursor"]
        == test_cursor
    )

    complete_valid = (
        stored["backfill_complete"]
        is False
    )

    save_ronin_backfill_cursor(
        AXIEOS_DB_PATH,
        endpoint,
        original["backfill_cursor"],
    )

    set_ronin_backfill_complete(
        AXIEOS_DB_PATH,
        endpoint,
        original["backfill_complete"],
    )

    restored = get_ronin_sync_state(
        AXIEOS_DB_PATH,
        endpoint,
    )

    restore_valid = (
        restored["backfill_cursor"]
        == original["backfill_cursor"]
        and restored["backfill_complete"]
        == original["backfill_complete"]
    )

    print(
        "\nRONIN BACKFILL CURSOR STATE"
    )

    print(
        "Endpoint:",
        endpoint,
    )

    print(
        "Cursor round trip:",
        "PASS" if cursor_valid else "FAIL",
    )

    print(
        "Complete flag round trip:",
        "PASS" if complete_valid else "FAIL",
    )

    print(
        "Original state restored:",
        "PASS" if restore_valid else "FAIL",
    )

    print(
        "Validation:",
        (
            "PASS"
            if (
                cursor_valid
                and complete_valid
                and restore_valid
            )
            else "FAIL"
        ),
    )


def run_historical_backfill_test():
    initialize_ronin_sync_state_table(
        AXIEOS_DB_PATH
    )

    boundary = (
        get_legacy_csv_safety_boundary(
            AXIEOS_DB_PATH
        )
    )

    before = get_raw_sync_counts(
        AXIEOS_DB_PATH
    )

    tx_first = (
        backfill_ronin_endpoint_batch(
            AXIEOS_DB_PATH,
            "transactions",
            max_pages=1,
        )
    )

    transfer_first = (
        backfill_ronin_endpoint_batch(
            AXIEOS_DB_PATH,
            "token_transfers",
            max_pages=1,
        )
    )

    tx_state_after_first = (
        get_ronin_sync_state(
            AXIEOS_DB_PATH,
            "transactions",
        )
    )

    transfer_state_after_first = (
        get_ronin_sync_state(
            AXIEOS_DB_PATH,
            "token_transfers",
        )
    )

    tx_second = (
        backfill_ronin_endpoint_batch(
            AXIEOS_DB_PATH,
            "transactions",
            max_pages=1,
        )
    )

    transfer_second = (
        backfill_ronin_endpoint_batch(
            AXIEOS_DB_PATH,
            "token_transfers",
            max_pages=1,
        )
    )

    after = get_raw_sync_counts(
        AXIEOS_DB_PATH
    )

    expected_tx_inserted = (
        tx_first["items_inserted"]
        + tx_second["items_inserted"]
    )

    expected_transfer_inserted = (
        transfer_first[
            "items_inserted"
        ]
        + transfer_second[
            "items_inserted"
        ]
    )

    tx_delta = (
        after["transactions"]
        - before["transactions"]
    )

    transfer_delta = (
        after["token_transfers"]
        - before["token_transfers"]
    )

    tx_resume_valid = (
        tx_state_after_first[
            "backfill_complete"
        ]
        or tx_second[
            "bootstrap_pages"
        ] == 0
    )

    transfer_resume_valid = (
        transfer_state_after_first[
            "backfill_complete"
        ]
        or transfer_second[
            "bootstrap_pages"
        ] == 0
    )

    validation = (
        boundary is not None
        and tx_delta
        == expected_tx_inserted
        and transfer_delta
        == expected_transfer_inserted
        and tx_resume_valid
        and transfer_resume_valid
    )

    print(
        "\nRONIN HISTORICAL BACKFILL"
    )

    print(
        "Legacy safety boundary:",
        boundary["datetime"],
    )

    print(
        "\nTRANSACTIONS — FIRST BATCH"
    )

    for key, value in (
        tx_first.items()
    ):
        print(
            f"{key}: {value}"
        )

    print(
        "\nTRANSACTIONS — SECOND BATCH"
    )

    for key, value in (
        tx_second.items()
    ):
        print(
            f"{key}: {value}"
        )

    print(
        "\nTOKEN TRANSFERS — FIRST BATCH"
    )

    for key, value in (
        transfer_first.items()
    ):
        print(
            f"{key}: {value}"
        )

    print(
        "\nTOKEN TRANSFERS — SECOND BATCH"
    )

    for key, value in (
        transfer_second.items()
    ):
        print(
            f"{key}: {value}"
        )

    print(
        "\nTransaction rows added:",
        tx_delta,
    )

    print(
        "Transfer rows added:",
        transfer_delta,
    )

    print(
        "Transaction resume:",
        (
            "PASS"
            if tx_resume_valid
            else "FAIL"
        ),
    )

    print(
        "Transfer resume:",
        (
            "PASS"
            if transfer_resume_valid
            else "FAIL"
        ),
    )

    print(
        "Validation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def run_ronin_sync_v04(
    incremental_max_pages=20,
    backfill_pages=1,
):
    print(
        "\nAXIEOS RONIN SYNC V0.4"
    )

    initialize_ronin_sync_state_table(
        AXIEOS_DB_PATH
    )

    initialize_raw_api_table(
        AXIEOS_DB_PATH
    )

    initialize_raw_transfer_table(
        AXIEOS_DB_PATH
    )

    initialize_classification_table(
        AXIEOS_DB_PATH
    )

    initialize_economic_events_table(
        AXIEOS_DB_PATH
    )

    # ---------------------------------
    # Incremental newest activity
    # ---------------------------------

    incremental_before = (
        get_raw_sync_counts(
            AXIEOS_DB_PATH
        )
    )

    incremental = (
        stage_incremental_ronin_data(
            AXIEOS_DB_PATH,
            max_pages=incremental_max_pages,
        )
    )

    incremental_after = (
        get_raw_sync_counts(
            AXIEOS_DB_PATH
        )
    )

    # ---------------------------------
    # Controlled historical backfill
    # ---------------------------------

    tx_backfill = (
        backfill_ronin_endpoint_batch(
            AXIEOS_DB_PATH,
            "transactions",
            max_pages=backfill_pages,
        )
    )

    transfer_backfill = (
        backfill_ronin_endpoint_batch(
            AXIEOS_DB_PATH,
            "token_transfers",
            max_pages=backfill_pages,
        )
    )

    # ---------------------------------
    # Materialize transfers to ledger
    # ---------------------------------

    ledger_before = (
        get_blockchain_ledger_count(
            AXIEOS_DB_PATH
        )
    )

    ledger_result = (
        materialize_staged_transfers_to_ledger(
            AXIEOS_DB_PATH
        )
    )

    ledger_after = (
        get_blockchain_ledger_count(
            AXIEOS_DB_PATH
        )
    )

    # ---------------------------------
    # Classification
    # ---------------------------------

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    classification_processed = (
        store_transaction_classifications(
            AXIEOS_DB_PATH,
            transactions,
        )
    )

    classification_validation = (
        validate_classification_storage(
            AXIEOS_DB_PATH
        )
    )

    # ---------------------------------
    # Economics
    # ---------------------------------

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

    economics_processed = (
        store_economic_events(
            AXIEOS_DB_PATH,
            events,
        )
    )

    economics_validation = (
        validate_economic_events_storage(
            AXIEOS_DB_PATH,
            events,
        )
    )

    # ---------------------------------
    # Refresh persistent state
    # ---------------------------------

    refresh_ronin_sync_state_bounds(
        AXIEOS_DB_PATH
    )

    tx_state = get_ronin_sync_state(
        AXIEOS_DB_PATH,
        "transactions",
    )

    transfer_state = (
        get_ronin_sync_state(
            AXIEOS_DB_PATH,
            "token_transfers",
        )
    )

    # ---------------------------------
    # Final V0.4 validation
    # ---------------------------------

    incremental_valid = (
        incremental[
            "transaction_stop"
        ]
        in {
            "KNOWN_TRANSACTION",
            "NO_NEXT_PAGE",
        }
        and incremental[
            "transfer_stop"
        ]
        in {
            "KNOWN_TRANSFER",
            "NO_NEXT_PAGE",
        }
    )

    ledger_valid = (
        ledger_after
        - ledger_before
        == ledger_result[
            "ledger_rows_inserted"
        ]
    )

    backfill_valid = (
        tx_backfill[
            "stop_reason"
        ]
        in {
            "BATCH_LIMIT",
            "LEGACY_CSV_BOUNDARY",
            "NO_NEXT_PAGE",
            "ALREADY_COMPLETE",
        }
        and transfer_backfill[
            "stop_reason"
        ]
        in {
            "BATCH_LIMIT",
            "LEGACY_CSV_BOUNDARY",
            "NO_NEXT_PAGE",
            "ALREADY_COMPLETE",
        }
    )

    state_valid = (
        tx_state is not None
        and transfer_state is not None
    )

    final_passed = (
        incremental_valid
        and ledger_valid
        and backfill_valid
        and state_valid
        and classification_validation[
            "passed"
        ]
        and economics_validation[
            "passed"
        ]
    )




    # ---------------------------------
    # Output
    # ---------------------------------

    print(
        "\nINCREMENTAL SYNC"
    )

    print(
        "Transactions before:",
        incremental_before[
            "transactions"
        ],
    )

    print(
        "Transactions found:",
        incremental[
            "transactions_found"
        ],
    )

    print(
        "Transactions inserted:",
        incremental[
            "transactions_inserted"
        ],
    )

    print(
        "Transactions after:",
        incremental_after[
            "transactions"
        ],
    )

    print(
        "Transaction pages:",
        incremental[
            "transaction_pages"
        ],
    )

    print(
        "Transaction stop:",
        incremental[
            "transaction_stop"
        ],
    )

    print(
        "Transfers before:",
        incremental_before[
            "token_transfers"
        ],
    )

    print(
        "Transfers found:",
        incremental[
            "transfers_found"
        ],
    )

    print(
        "Transfers inserted:",
        incremental[
            "transfers_inserted"
        ],
    )

    print(
        "Transfers after:",
        incremental_after[
            "token_transfers"
        ],
    )

    print(
        "Transfer pages:",
        incremental[
            "transfer_pages"
        ],
    )

    print(
        "Transfer stop:",
        incremental[
            "transfer_stop"
        ],
    )

    print(
        "\nHISTORICAL BACKFILL"
    )

    print(
        "Transaction backfill inserted:",
        tx_backfill[
            "items_inserted"
        ],
    )

    print(
        "Transaction backfill stop:",
        tx_backfill[
            "stop_reason"
        ],
    )

    print(
        "Transfer backfill inserted:",
        transfer_backfill[
            "items_inserted"
        ],
    )

    print(
        "Transfer backfill stop:",
        transfer_backfill[
            "stop_reason"
        ],
    )

    print(
        "\nLEDGER"
    )

    print(
        "Ledger rows before:",
        ledger_before,
    )

    print(
        "New ledger rows:",
        ledger_result[
            "ledger_rows_inserted"
        ],
    )

    print(
        "Ledger rows after:",
        ledger_after,
    )

    print(
        "\nCLASSIFICATION"
    )

    print(
        "Transactions classified:",
        classification_processed,
    )

    print(
        "Unknown classifications:",
        classification_validation[
            "unknown_total"
        ],
    )

    print(
        "Classification validation:",
        (
            "PASS"
            if classification_validation[
                "passed"
            ]
            else "FAIL"
        ),
    )

    print(
        "\nECONOMICS"
    )

    print(
        "Economic events processed:",
        economics_processed,
    )

    print(
        "Realized Axie trades:",
        economics_validation[
            "realized_total"
        ],
    )

    print(
        "Economics validation:",
        (
            "PASS"
            if economics_validation[
                "passed"
            ]
            else "FAIL"
        ),
    )

    print(
        "\nSYNC STATE"
    )

    print(
        "Transactions oldest:",
        tx_state[
            "oldest_timestamp"
        ],
    )

    print(
        "Transactions newest:",
        tx_state[
            "newest_timestamp"
        ],
    )

    print(
        "Transactions backfill complete:",
        tx_state[
            "backfill_complete"
        ],
    )

    print(
        "Transfers oldest:",
        transfer_state[
            "oldest_timestamp"
        ],
    )

    print(
        "Transfers newest:",
        transfer_state[
            "newest_timestamp"
        ],
    )

    print(
        "Transfers backfill complete:",
        transfer_state[
            "backfill_complete"
        ],
    )

    print(
        "\nRONIN V0.4 VALIDATION"
    )

    print(
        "Incremental sync:",
        (
            "PASS"
            if incremental_valid
            else "FAIL"
        ),
    )

    print(
        "Historical backfill:",
        (
            "PASS"
            if backfill_valid
            else "FAIL"
        ),
    )

    print(
        "Ledger:",
        (
            "PASS"
            if ledger_valid
            else "FAIL"
        ),
    )

    print(
        "Persistent state:",
        (
            "PASS"
            if state_valid
            else "FAIL"
        ),
    )

    print(
        "Sync version:",
        RONIN_SYNC_VERSION,
    )

    print(
        "Validation:",
        (
            "PASS"
            if final_passed
            else "FAIL"
        ),
    )


def run_wallet_registry_test():
    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    rows = connection.execute(
        """
        SELECT
            address,
            wallet_label,
            ownership_type,
            wallet_role,
            source,
            intelligence_version
        FROM ronin_wallet_registry
        ORDER BY wallet_label
        """
    ).fetchall()

    connection.close()

    valid = all(
        row[2] in WALLET_OWNERSHIP_TYPES
        and row[3] in WALLET_ROLES
        and row[5] == INTELLIGENCE_VERSION
        for row in rows
    )

    print(
        "\nRONIN WALLET REGISTRY"
    )

    print(
        "Wallets registered:",
        len(rows),
    )

    print(
        "Intelligence version:",
        INTELLIGENCE_VERSION,
    )

    print(
        "Registry validation:",
        (
            "PASS"
            if valid
            else "FAIL"
        ),
    )

    print("\nWALLETS")

    for row in rows:
        print(
            "\nLabel:",
            row[1],
        )

        print(
            "Ownership:",
            row[2],
        )

        print(
            "Role:",
            row[3],
        )

        print(
            "Source:",
            row[4],
        )

def run_wallet_relationship_test():
    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    unknown_address = (
        "0x1111111111111111111111111111111111111111"
    )

    tests = [
        (
            "Primary to zero",
            RONIN_WALLET_ADDRESS,
            ZERO_ADDRESS,
            "USER_TO_SYSTEM",
        ),
        (
            "Zero to primary",
            ZERO_ADDRESS,
            RONIN_WALLET_ADDRESS,
            "SYSTEM_TO_USER",
        ),
        (
            "Primary to unknown",
            RONIN_WALLET_ADDRESS,
            unknown_address,
            "USER_TO_UNKNOWN",
        ),
        (
            "Unknown to primary",
            unknown_address,
            RONIN_WALLET_ADDRESS,
            "UNKNOWN_TO_USER",
        ),
        (
            "Primary to primary",
            RONIN_WALLET_ADDRESS,
            RONIN_WALLET_ADDRESS,
            "INTERNAL_USER_TRANSFER",
        ),
    ]

    passed = 0

    print(
        "\nRONIN WALLET RELATIONSHIPS"
    )

    for (
        label,
        from_address,
        to_address,
        expected,
    ) in tests:
        result = classify_wallet_relationship(
            AXIEOS_DB_PATH,
            from_address,
            to_address,
        )

        actual = result[
            "relationship"
        ]

        valid = (
            actual == expected
        )

        if valid:
            passed += 1

        print(
            f"\n{label}"
        )

        print(
            "Expected:",
            expected,
        )

        print(
            "Actual:",
            actual,
        )

        print(
            "Result:",
            (
                "PASS"
                if valid
                else "FAIL"
            ),
        )

    print(
        "\nTests passed:",
        f"{passed}/{len(tests)}",
    )

    print(
        "Validation:",
        (
            "PASS"
            if passed == len(tests)
            else "FAIL"
        ),
    )


def run_internal_transfer_test():
    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    test_secondary_address = (
        "0x2222222222222222222222222222222222222222"
    )

    unknown_address = (
        "0x1111111111111111111111111111111111111111"
    )

    upsert_wallet_registry_entry(
        db_path=AXIEOS_DB_PATH,
        address=test_secondary_address,
        wallet_label=(
            "Task 71 Test Wallet"
        ),
        ownership_type="USER_OWNED",
        wallet_role="SECONDARY",
        source="TEST",
    )

    internal_transaction = {
        "movements": [
            {
                "from_address": (
                    RONIN_WALLET_ADDRESS
                ),
                "to_address": (
                    test_secondary_address
                ),
                "asset": (
                    "Ronin Wrapped Ether"
                ),
                "value_in": "0",
                "value_out": "1",
            }
        ]
    }

    external_transaction = {
        "movements": [
            {
                "from_address": (
                    RONIN_WALLET_ADDRESS
                ),
                "to_address": (
                    unknown_address
                ),
                "asset": (
                    "Ronin Wrapped Ether"
                ),
                "value_in": "0",
                "value_out": "1",
            }
        ]
    }

    internal_result = (
        detect_internal_user_transfer(
            AXIEOS_DB_PATH,
            internal_transaction,
        )
    )

    external_result = (
        detect_internal_user_transfer(
            AXIEOS_DB_PATH,
            external_transaction,
        )
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    connection.execute(
        """
        DELETE FROM ronin_wallet_registry
        WHERE address = ?
        """,
        (
            normalize_address(
                test_secondary_address
            ),
        ),
    )

    connection.commit()
    connection.close()

    test_entry = get_wallet_registry_entry(
        AXIEOS_DB_PATH,
        test_secondary_address,
    )

    cleanup_valid = (
        test_entry["ownership_type"]
        == "UNKNOWN"
    )

    validation = (
        internal_result[
            "is_internal_transfer"
        ]
        is True
        and external_result[
            "is_internal_transfer"
        ]
        is False
        and cleanup_valid
    )

    print(
        "\nRONIN INTERNAL TRANSFER DETECTION"
    )

    print(
        "Owned to owned:",
        internal_result[
            "is_internal_transfer"
        ],
    )

    print(
        "Owned to unknown:",
        external_result[
            "is_internal_transfer"
        ],
    )

    print(
        "Test wallet cleanup:",
        (
            "PASS"
            if cleanup_valid
            else "FAIL"
        ),
    )

    print(
        "Validation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )

    
def run_counterparty_discovery_test():
    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    candidates = (
        discover_high_confidence_counterparties(
            transactions
        )
    )

    register_discovered_counterparties(
        AXIEOS_DB_PATH,
        candidates,
    )

    role_counts = {}

    for candidate in candidates:
        role = candidate["role"]

        role_counts[role] = (
            role_counts.get(
                role,
                0,
            )
            + 1
        )

    expected_roles = {
        "MARKETPLACE",
        "DEX",
        "STAKING",
    }

    roles_found = set(
        role_counts
    )

    validation = (
        expected_roles
        <= roles_found
    )

    print(
        "\nRONIN COUNTERPARTY DISCOVERY"
    )

    print(
        "Transactions analyzed:",
        len(transactions),
    )

    print(
        "High-confidence counterparties:",
        len(candidates),
    )

    print("\nROLE COUNTS")

    for role in sorted(
        role_counts
    ):
        print(
            f"{role}: "
            f"{role_counts[role]}"
        )

    print("\nCOUNTERPARTIES")

    for candidate in sorted(
        candidates,
        key=lambda item: (
            item["role"],
            -item[
                "evidence_count"
            ],
        ),
    ):
        print(
            "\nRole:",
            candidate["role"],
        )

        print(
            "Address:",
            candidate["address"],
        )

        print(
            "Evidence:",
            candidate[
                "evidence_count"
            ],
        )

    print(
        "\nRequired roles found:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )

    print(
        "Validation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def run_asset_registry_test():
    initialize_asset_registry_table(
        AXIEOS_DB_PATH
    )

    assets = (
        discover_assets_from_raw_transfers(
            AXIEOS_DB_PATH
        )
    )

    processed = (
        store_asset_registry_entries(
            AXIEOS_DB_PATH,
            assets,
        )
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    total = connection.execute(
        """
        SELECT COUNT(*)
        FROM ronin_asset_registry
        """
    ).fetchone()[0]

    unique_keys = connection.execute(
        """
        SELECT COUNT(
            DISTINCT asset_key
        )
        FROM ronin_asset_registry
        """
    ).fetchone()[0]

    category_counts = (
        connection.execute(
            """
            SELECT
                asset_category,
                COUNT(*)
            FROM ronin_asset_registry
            GROUP BY asset_category
            ORDER BY asset_category
            """
        ).fetchall()
    )

    examples = connection.execute(
        """
        SELECT
            token_name,
            token_symbol,
            token_type,
            token_id,
            asset_category
        FROM ronin_asset_registry
        ORDER BY
            token_name,
            token_id
        LIMIT 15
        """
    ).fetchall()

    invalid = connection.execute(
        """
        SELECT
            asset_category
        FROM ronin_asset_registry
        """
    ).fetchall()

    connection.close()

    invalid_count = sum(
        1
        for row in invalid
        if row[0]
        not in ASSET_CATEGORIES
    )

    validation = (
        processed > 0
        and total == unique_keys
        and invalid_count == 0
    )

    print(
        "\nRONIN ASSET REGISTRY"
    )

    print(
        "Assets discovered:",
        len(assets),
    )

    print(
        "Assets processed:",
        processed,
    )

    print(
        "Assets stored:",
        total,
    )

    print(
        "Unique asset keys:",
        unique_keys,
    )

    print(
        "Invalid categories:",
        invalid_count,
    )

    print(
        "Intelligence version:",
        INTELLIGENCE_VERSION,
    )

    print("\nCATEGORY COUNTS")

    for category, count in (
        category_counts
    ):
        print(
            f"{category}: {count}"
        )

    print("\nEXAMPLES")

    for row in examples:
        print(
            "\nName:",
            row[0],
        )

        print(
            "Symbol:",
            row[1],
        )

        print(
            "Type:",
            row[2],
        )

        print(
            "Token ID:",
            row[3],
        )

        print(
            "Category:",
            row[4],
        )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_transaction_intelligence_test():
    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_asset_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_transaction_intelligence_table(
        AXIEOS_DB_PATH
    )

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    counterparties = (
        discover_high_confidence_counterparties(
            transactions
        )
    )

    register_discovered_counterparties(
        AXIEOS_DB_PATH,
        counterparties,
    )

    assets = (
        discover_assets_from_raw_transfers(
            AXIEOS_DB_PATH
        )
    )

    store_asset_registry_entries(
        AXIEOS_DB_PATH,
        assets,
    )

    asset_registry = (
        load_asset_registry_map(
            AXIEOS_DB_PATH
        )
    )

    intelligence_rows = []

    for transaction in transactions:
        intelligence_rows.append(
            build_transaction_intelligence(
                AXIEOS_DB_PATH,
                transaction,
                asset_registry,
            )
        )

    processed = (
        store_transaction_intelligence(
            AXIEOS_DB_PATH,
            intelligence_rows,
        )
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    total = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_transaction_intelligence
        """
    ).fetchone()[0]

    unique_txhashes = connection.execute(
        """
        SELECT COUNT(DISTINCT txhash)
        FROM blockchain_transaction_intelligence
        """
    ).fetchone()[0]

    internal_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_transaction_intelligence
        WHERE is_internal_transfer = 1
        """
    ).fetchone()[0]

    with_counterparty = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_transaction_intelligence
            WHERE counterparties_json != '[]'
            """
        ).fetchone()[0]
    )

    with_assets = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_transaction_intelligence
        WHERE asset_categories_json != '[]'
        """
    ).fetchone()[0]

    invalid_version = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_transaction_intelligence
        WHERE intelligence_version != ?
        """,
        (
            INTELLIGENCE_VERSION,
        ),
    ).fetchone()[0]

    examples = connection.execute(
        """
        SELECT
            txhash,
            wallet_relationships_json,
            counterparties_json,
            asset_categories_json,
            is_internal_transfer
        FROM blockchain_transaction_intelligence
        WHERE
            counterparties_json != '[]'
            OR asset_categories_json != '[]'
        LIMIT 10
        """
    ).fetchall()

    connection.close()

    validation = (
        processed == len(transactions)
        and total == len(transactions)
        and unique_txhashes == total
        and invalid_version == 0
    )

    print(
        "\nRONIN TRANSACTION INTELLIGENCE"
    )

    print(
        "Transactions analyzed:",
        len(transactions),
    )

    print(
        "Intelligence processed:",
        processed,
    )

    print(
        "Intelligence stored:",
        total,
    )

    print(
        "Unique txhashes:",
        unique_txhashes,
    )

    print(
        "Internal transfers:",
        internal_count,
    )

    print(
        "Known counterparties:",
        with_counterparty,
    )

    print(
        "Transactions with asset intelligence:",
        with_assets,
    )

    print(
        "Invalid versions:",
        invalid_version,
    )

    print(
        "Intelligence version:",
        INTELLIGENCE_VERSION,
    )

    print("\nEXAMPLES")

    for row in examples:
        print(
            "\nTX:",
            row[0],
        )

        print(
            "Relationships:",
            row[1],
        )

        print(
            "Counterparties:",
            row[2],
        )

        print(
            "Asset categories:",
            row[3],
        )

        print(
            "Internal:",
            bool(row[4]),
        )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def run_historical_intelligence_validation_test():
    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_asset_registry_table(
        AXIEOS_DB_PATH
    )

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    counterparties = (
        discover_high_confidence_counterparties(
            transactions
        )
    )

    register_discovered_counterparties(
        AXIEOS_DB_PATH,
        counterparties,
    )

    assets = (
        discover_assets_from_raw_transfers(
            AXIEOS_DB_PATH
        )
    )

    store_asset_registry_entries(
        AXIEOS_DB_PATH,
        assets,
    )

    result = (
        validate_historical_intelligence(
            AXIEOS_DB_PATH
        )
    )

    zero_entry = (
        get_wallet_registry_entry(
            AXIEOS_DB_PATH,
            ZERO_ADDRESS,
        )
    )

    zero_role_valid = (
        zero_entry["wallet_role"]
        == "SYSTEM"
    )

    taxonomy_valid = (
        validate_classification_taxonomy()
    )

    # Synthetic internal-transfer
    # regression test.
    test_secondary = (
        "0x2222222222222222222222222222222222222222"
    )

    upsert_wallet_registry_entry(
        db_path=AXIEOS_DB_PATH,
        address=test_secondary,
        wallet_label=(
            "Task 75 Test Wallet"
        ),
        ownership_type="USER_OWNED",
        wallet_role="SECONDARY",
        source="TEST",
    )

    synthetic_transaction = {
        "txhash": "0xtask75internal",
        "movements": [
            {
                "from_address": (
                    RONIN_WALLET_ADDRESS
                ),
                "to_address": (
                    test_secondary
                ),
                "asset": (
                    "Ronin Wrapped Ether"
                ),
                "value_in": "0",
                "value_out": "1",
            }
        ],
    }

    synthetic_result = (
        classify_transaction_with_intelligence(
            AXIEOS_DB_PATH,
            synthetic_transaction,
        )
    )

    internal_valid = (
        synthetic_result[
            "classification"
        ]
        == "INTERNAL_TRANSFER"
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    connection.execute(
        """
        DELETE FROM ronin_wallet_registry
        WHERE address = ?
        """,
        (
            normalize_address(
                test_secondary
            ),
        ),
    )

    connection.commit()
    connection.close()

    validation = (
        zero_role_valid
        and taxonomy_valid
        and internal_valid
        and len(
            result["inconsistencies"]
        )
        == 0
    )

    print(
        "\nRONIN HISTORICAL INTELLIGENCE VALIDATION"
    )

    print(
        "Transactions checked:",
        result["transactions"],
    )

    print(
        "Historical inconsistencies:",
        len(
            result["inconsistencies"]
        ),
    )

    print(
        "Reclassification candidates:",
        len(
            result[
                "reclassification_candidates"
            ]
        ),
    )

    print(
        "Zero address role:",
        zero_entry["wallet_role"],
    )

    print(
        "Zero address semantics:",
        (
            "PASS"
            if zero_role_valid
            else "FAIL"
        ),
    )

    print(
        "Internal-transfer regression:",
        (
            "PASS"
            if internal_valid
            else "FAIL"
        ),
    )

    print(
        "Taxonomy validation:",
        (
            "PASS"
            if taxonomy_valid
            else "FAIL"
        ),
    )

    if result["inconsistencies"]:
        print(
            "\nINCONSISTENCIES"
        )

        for item in result[
            "inconsistencies"
        ][:10]:
            print(item)

    if result[
        "reclassification_candidates"
    ]:
        print(
            "\nRECLASSIFICATION CANDIDATES"
        )

        for item in result[
            "reclassification_candidates"
        ][:10]:
            print(item)

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def run_ronin_sync_v05(
    incremental_max_pages=20,
    backfill_pages=1,
):
    # Run the complete proven V0.4 pipeline first.
    run_ronin_sync_v04(
        incremental_max_pages=(
            incremental_max_pages
        ),
        backfill_pages=backfill_pages,
    )

    print(
        "\nAXIEOS ASSET & WALLET "
        "INTELLIGENCE V0.5"
    )

    # ---------------------------------
    # Initialize intelligence tables
    # ---------------------------------

    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_asset_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_transaction_intelligence_table(
        AXIEOS_DB_PATH
    )

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    # ---------------------------------
    # Current grouped transactions
    # ---------------------------------

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    # ---------------------------------
    # Counterparty intelligence
    # ---------------------------------

    counterparties = (
        discover_high_confidence_counterparties(
            transactions
        )
    )

    register_discovered_counterparties(
        AXIEOS_DB_PATH,
        counterparties,
    )

    # ---------------------------------
    # Asset intelligence
    # ---------------------------------

    assets = (
        discover_assets_from_raw_transfers(
            AXIEOS_DB_PATH
        )
    )

    assets_processed = (
        store_asset_registry_entries(
            AXIEOS_DB_PATH,
            assets,
        )
    )

    asset_registry = (
        load_asset_registry_map(
            AXIEOS_DB_PATH
        )
    )

    # ---------------------------------
    # Intelligence-aware classification
    # ---------------------------------

    classifications_processed = (
        store_intelligent_transaction_classifications(
            AXIEOS_DB_PATH,
            transactions,
        )
    )

    classification_validation = (
        validate_classification_storage(
            AXIEOS_DB_PATH
        )
    )

    # ---------------------------------
    # Transaction intelligence
    # ---------------------------------

    intelligence_rows = []

    for transaction in transactions:
        intelligence_rows.append(
            build_transaction_intelligence(
                AXIEOS_DB_PATH,
                transaction,
                asset_registry,
            )
        )

    intelligence_processed = (
        store_transaction_intelligence(
            AXIEOS_DB_PATH,
            intelligence_rows,
        )
    )

    # ---------------------------------
    # Historical consistency
    # ---------------------------------

    historical_validation = (
        validate_historical_intelligence(
            AXIEOS_DB_PATH
        )
    )

    # ---------------------------------
    # Database validation
    # ---------------------------------

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    wallet_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM ronin_wallet_registry
        """
    ).fetchone()[0]

    asset_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM ronin_asset_registry
        """
    ).fetchone()[0]

    intelligence_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_transaction_intelligence
            """
        ).fetchone()[0]
    )

    unique_intelligence = (
        connection.execute(
            """
            SELECT COUNT(DISTINCT txhash)
            FROM blockchain_transaction_intelligence
            """
        ).fetchone()[0]
    )

    invalid_asset_categories = (
        connection.execute(
            """
            SELECT asset_category
            FROM ronin_asset_registry
            """
        ).fetchall()
    )

    invalid_intelligence_versions = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_transaction_intelligence
            WHERE intelligence_version != ?
            """,
            (
                INTELLIGENCE_VERSION,
            ),
        ).fetchone()[0]
    )

    internal_intelligence_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_transaction_intelligence
            WHERE is_internal_transfer = 1
            """
        ).fetchone()[0]
    )

    internal_classification_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_transaction_classifications
            WHERE classification =
                'INTERNAL_TRANSFER'
            """
        ).fetchone()[0]
    )

    connection.close()

    invalid_asset_count = sum(
        1
        for row in invalid_asset_categories
        if row[0] not in ASSET_CATEGORIES
    )

    zero_entry = get_wallet_registry_entry(
        AXIEOS_DB_PATH,
        ZERO_ADDRESS,
    )

    zero_valid = (
        zero_entry["wallet_role"]
        == "SYSTEM"
    )

    intelligence_count_valid = (
        intelligence_count
        == len(transactions)
        == unique_intelligence
    )

    internal_consistency = (
        internal_intelligence_count
        == internal_classification_count
    )

    historical_valid = (
        len(
            historical_validation[
                "inconsistencies"
            ]
        )
        == 0
    )

    final_passed = (
        wallet_count >= 2
        and asset_count > 0
        and assets_processed > 0
        and intelligence_count_valid
        and classifications_processed
        == len(transactions)
        and intelligence_processed
        == len(transactions)
        and invalid_asset_count == 0
        and invalid_intelligence_versions == 0
        and zero_valid
        and internal_consistency
        and historical_valid
        and classification_validation[
            "passed"
        ]
        and validate_classification_taxonomy()
    )

    print(
        "\nWALLET INTELLIGENCE"
    )

    print(
        "Registered wallets:",
        wallet_count,
    )

    print(
        "Discovered counterparties:",
        len(counterparties),
    )

    print(
        "Zero address role:",
        zero_entry["wallet_role"],
    )

    print(
        "\nASSET INTELLIGENCE"
    )

    print(
        "Assets discovered:",
        len(assets),
    )

    print(
        "Assets stored:",
        asset_count,
    )

    print(
        "Invalid asset categories:",
        invalid_asset_count,
    )

    print(
        "\nTRANSACTION INTELLIGENCE"
    )

    print(
        "Transactions:",
        len(transactions),
    )

    print(
        "Classifications processed:",
        classifications_processed,
    )

    print(
        "Intelligence processed:",
        intelligence_processed,
    )

    print(
        "Intelligence stored:",
        intelligence_count,
    )

    print(
        "Unique intelligence txhashes:",
        unique_intelligence,
    )

    print(
        "Internal transfers:",
        internal_intelligence_count,
    )

    print(
        "Internal classifications:",
        internal_classification_count,
    )

    print(
        "Historical inconsistencies:",
        len(
            historical_validation[
                "inconsistencies"
            ]
        ),
    )

    print(
        "\nRONIN V0.5 VALIDATION"
    )

    print(
        "Wallet registry:",
        (
            "PASS"
            if wallet_count >= 2
            and zero_valid
            else "FAIL"
        ),
    )

    print(
        "Asset registry:",
        (
            "PASS"
            if (
                asset_count > 0
                and invalid_asset_count == 0
            )
            else "FAIL"
        ),
    )

    print(
        "Classification:",
        (
            "PASS"
            if classification_validation[
                "passed"
            ]
            else "FAIL"
        ),
    )

    print(
        "Transaction intelligence:",
        (
            "PASS"
            if (
                intelligence_count_valid
                and invalid_intelligence_versions
                == 0
            )
            else "FAIL"
        ),
    )

    print(
        "Internal-transfer consistency:",
        (
            "PASS"
            if internal_consistency
            else "FAIL"
        ),
    )

    print(
        "Historical consistency:",
        (
            "PASS"
            if historical_valid
            else "FAIL"
        ),
    )

    print(
        "Intelligence version:",
        RONIN_INTELLIGENCE_VERSION,
    )

    print(
        "Validation:",
        (
            "PASS"
            if final_passed
            else "FAIL"
        ),
    )


def run_accounting_schema_test():
    sample = build_empty_accounting_record(
        txhash="0xtestaccounting",
        datetime_value=(
            "2026-08-21 00:00:00"
        ),
        classification=(
            "MARKETPLACE_BUY"
        ),
    )

    validation = (
        validate_accounting_record(
            sample
        )
    )

    print(
        "\nRONIN ACCOUNTING RECORD SCHEMA"
    )

    print(
        "Fields:",
        len(
            ACCOUNTING_RECORD_FIELDS
        ),
    )

    print(
        "Statuses:",
        len(
            ACCOUNTING_STATUSES
        ),
    )

    print(
        "Event types:",
        len(
            ACCOUNTING_EVENT_TYPES
        ),
    )

    print(
        "Accounting version:",
        ACCOUNTING_VERSION,
    )

    print(
        "Schema validation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )

    print(
        "\nSAMPLE RECORD"
    )

    for key, value in sample.items():
        print(
            f"{key}: {value}"
        )


def run_basic_accounting_records_test():
    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_asset_registry_table(
        AXIEOS_DB_PATH
    )

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    counterparties = (
        discover_high_confidence_counterparties(
            transactions
        )
    )

    register_discovered_counterparties(
        AXIEOS_DB_PATH,
        counterparties,
    )

    assets = (
        discover_assets_from_raw_transfers(
            AXIEOS_DB_PATH
        )
    )

    store_asset_registry_entries(
        AXIEOS_DB_PATH,
        assets,
    )

    records = []

    invalid_records = []

    for transaction in transactions:
        record = (
            build_basic_accounting_record(
                AXIEOS_DB_PATH,
                transaction,
            )
        )

        records.append(record)

        if not validate_accounting_record(
            record
        ):
            invalid_records.append(
                record
            )

    event_counts = {}

    status_counts = {}

    for record in records:
        event_type = record[
            "event_type"
        ]

        status = record[
            "accounting_status"
        ]

        event_counts[event_type] = (
            event_counts.get(
                event_type,
                0,
            )
            + 1
        )

        status_counts[status] = (
            status_counts.get(
                status,
                0,
            )
            + 1
        )

    print(
        "\nRONIN BASIC ACCOUNTING RECORDS"
    )

    print(
        "Transactions:",
        len(transactions),
    )

    print(
        "Accounting records:",
        len(records),
    )

    print(
        "Invalid records:",
        len(invalid_records),
    )

    print("\nEVENT TYPES")

    for event_type in sorted(
        event_counts
    ):
        print(
            f"{event_type}: "
            f"{event_counts[event_type]}"
        )

    print("\nSTATUSES")

    for status in sorted(
        status_counts
    ):
        print(
            f"{status}: "
            f"{status_counts[status]}"
        )

    print("\nEXAMPLES")

    for record in records[:10]:
        print(
            "\nTX:",
            record["txhash"],
        )

        print(
            "Event:",
            record["event_type"],
        )

        print(
            "Classification:",
            record["classification"],
        )

        print(
            "Asset:",
            record["asset_name"],
        )

        print(
            "Category:",
            record["asset_category"],
        )

        print(
            "Quantity:",
            record["quantity"],
        )

        print(
            "Direction:",
            record["direction"],
        )

        print(
            "Counterparty:",
            record[
                "counterparty_role"
            ],
        )

        print(
            "Status:",
            record[
                "accounting_status"
            ],
        )

    print(
        "\nValidation:",
        (
            "PASS"
            if (
                len(records)
                == len(transactions)
                and len(
                    invalid_records
                )
                == 0
            )
            else "FAIL"
        ),
    )


def run_marketplace_accounting_test():
    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_asset_registry_table(
        AXIEOS_DB_PATH
    )

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    counterparties = (
        discover_high_confidence_counterparties(
            transactions
        )
    )

    register_discovered_counterparties(
        AXIEOS_DB_PATH,
        counterparties,
    )

    assets = (
        discover_assets_from_raw_transfers(
            AXIEOS_DB_PATH
        )
    )

    store_asset_registry_entries(
        AXIEOS_DB_PATH,
        assets,
    )

    economics_map = (
        build_current_marketplace_economics_map(
            transactions
        )
    )

    records = []

    for transaction in transactions:
        record = (
            build_basic_accounting_record(
                AXIEOS_DB_PATH,
                transaction,
            )
        )

        record = (
            enrich_accounting_record_with_marketplace_economics(
                record,
                economics_map,
            )
        )

        if record["event_type"] in {
            "ASSET_PURCHASE",
            "ASSET_SALE",
        }:
            records.append(record)

    purchases = [
        record
        for record in records
        if record["event_type"]
        == "ASSET_PURCHASE"
    ]

    sales = [
        record
        for record in records
        if record["event_type"]
        == "ASSET_SALE"
    ]

    ready_purchases = [
        record
        for record in purchases
        if record[
            "accounting_status"
        ] == "READY"
    ]

    ready_sales = [
        record
        for record in sales
        if record[
            "accounting_status"
        ] == "READY"
    ]

    review_sales = [
        record
        for record in sales
        if record[
            "accounting_status"
        ] == "REVIEW"
    ]

    missing_economics = [
        record
        for record in records
        if record["txhash"]
        not in economics_map
    ]

    invalid_records = [
        record
        for record in records
        if not validate_accounting_record(
            record
        )
    ]

    regression = next(
        (
            record
            for record in sales
            if record[
                "asset_token_id"
            ]
            == "1429698"
        ),
        None,
    )

    regression_valid = (
        regression is not None
        and regression[
            "gross_amount"
        ] == "0.00034"
        and regression[
            "marketplace_fee"
        ] == "0.00001445"
        and regression[
            "net_amount"
        ] == "0.00032555"
        and regression[
            "cost_basis"
        ] == "0.00032"
        and regression[
            "realized_pl"
        ] == "0.00000555"
        and regression[
            "accounting_status"
        ] == "READY"
    )

    validation = (
        len(records)
        == len(economics_map)
        and len(
            missing_economics
        )
        == 0
        and len(
            invalid_records
        )
        == 0
        and regression_valid
    )

    print(
        "\nRONIN MARKETPLACE ACCOUNTING"
    )

    print(
        "Marketplace records:",
        len(records),
    )

    print(
        "Purchases:",
        len(purchases),
    )

    print(
        "Sales:",
        len(sales),
    )

    print(
        "Ready purchases:",
        len(ready_purchases),
    )

    print(
        "Ready sales:",
        len(ready_sales),
    )

    print(
        "Sales needing review:",
        len(review_sales),
    )

    print(
        "Missing economics:",
        len(missing_economics),
    )

    print(
        "Invalid records:",
        len(invalid_records),
    )

    print(
        "Axie #1429698 regression:",
        (
            "PASS"
            if regression_valid
            else "FAIL"
        ),
    )

    print("\nREADY SALE EXAMPLES")

    for record in ready_sales[:10]:
        print(
            "\nTX:",
            record["txhash"],
        )

        print(
            "Asset:",
            record["asset_name"],
        )

        print(
            "Token ID:",
            record[
                "asset_token_id"
            ],
        )

        print(
            "Gross:",
            record["gross_amount"],
        )

        print(
            "Fee:",
            record[
                "marketplace_fee"
            ],
        )

        print(
            "Net:",
            record["net_amount"],
        )

        print(
            "Cost basis:",
            record["cost_basis"],
        )

        print(
            "Realized P/L:",
            record["realized_pl"],
        )

        print(
            "Status:",
            record[
                "accounting_status"
            ],
        )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def run_non_marketplace_accounting_test():
    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_asset_registry_table(
        AXIEOS_DB_PATH
    )

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    counterparties = (
        discover_high_confidence_counterparties(
            transactions
        )
    )

    register_discovered_counterparties(
        AXIEOS_DB_PATH,
        counterparties,
    )

    assets = (
        discover_assets_from_raw_transfers(
            AXIEOS_DB_PATH
        )
    )

    store_asset_registry_entries(
        AXIEOS_DB_PATH,
        assets,
    )

    records = []

    for transaction in transactions:
        record = (
            build_basic_accounting_record(
                AXIEOS_DB_PATH,
                transaction,
            )
        )

        if record["classification"] in {
            "MARKETPLACE_BUY",
            "MARKETPLACE_SALE",
        }:
            continue

        record = (
            enrich_non_marketplace_accounting_record(
                AXIEOS_DB_PATH,
                record,
                transaction,
            )
        )

        records.append(record)

    event_counts = {}
    status_counts = {}

    invalid_records = []

    for record in records:
        event_counts[
            record["event_type"]
        ] = (
            event_counts.get(
                record["event_type"],
                0,
            )
            + 1
        )

        status_counts[
            record["accounting_status"]
        ] = (
            status_counts.get(
                record[
                    "accounting_status"
                ],
                0,
            )
            + 1
        )

        if not validate_accounting_record(
            record
        ):
            invalid_records.append(
                record
            )

    swaps = [
        record
        for record in records
        if record["event_type"]
        == "TOKEN_SWAP"
    ]

    swap_structure_valid = all(
        record["asset_name"]
        is not None
        and record["quantity"]
        is not None
        and record["payment_asset"]
        is not None
        and record["gross_amount"]
        is not None
        and record[
            "accounting_status"
        ]
        == "REVIEW"
        for record in swaps
    )

    ready_operational = [
        record
        for record in records
        if record["event_type"] in {
            "MINT_OR_CLAIM",
            "STAKING_OR_REWARD",
            "ASSET_BURN",
        }
        and record[
            "accounting_status"
        ]
        == "READY"
    ]

    transfer_records = [
        record
        for record in records
        if record["event_type"] in {
            "TRANSFER_IN",
            "TRANSFER_OUT",
        }
    ]

    transfer_review_valid = all(
        record["accounting_status"]
        == "REVIEW"
        for record in transfer_records
    )

    validation = (
        len(invalid_records) == 0
        and swap_structure_valid
        and transfer_review_valid
    )

    print(
        "\nRONIN NON-MARKETPLACE ACCOUNTING"
    )

    print(
        "Records:",
        len(records),
    )

    print(
        "Invalid records:",
        len(invalid_records),
    )

    print(
        "Operational events READY:",
        len(ready_operational),
    )

    print(
        "Transfers under review:",
        len(transfer_records),
    )

    print(
        "Swap structure:",
        (
            "PASS"
            if swap_structure_valid
            else "FAIL"
        ),
    )

    print(
        "Transfer review policy:",
        (
            "PASS"
            if transfer_review_valid
            else "FAIL"
        ),
    )

    print("\nEVENT TYPES")

    for event_type in sorted(
        event_counts
    ):
        print(
            f"{event_type}: "
            f"{event_counts[event_type]}"
        )

    print("\nSTATUSES")

    for status in sorted(
        status_counts
    ):
        print(
            f"{status}: "
            f"{status_counts[status]}"
        )

    print("\nSWAP EXAMPLES")

    for record in swaps[:5]:
        print(
            "\nTX:",
            record["txhash"],
        )

        print(
            "Asset OUT:",
            record["asset_name"],
        )

        print(
            "Quantity OUT:",
            record["quantity"],
        )

        print(
            "Asset IN:",
            record["payment_asset"],
        )

        print(
            "Quantity IN:",
            record["gross_amount"],
        )

        print(
            "Status:",
            record[
                "accounting_status"
            ],
        )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def run_internal_transfer_accounting_test():
    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_asset_registry_table(
        AXIEOS_DB_PATH
    )

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    test_secondary = (
        "0x2222222222222222222222222222222222222222"
    )

    upsert_wallet_registry_entry(
        db_path=AXIEOS_DB_PATH,
        address=test_secondary,
        wallet_label=(
            "Task 81 Test Wallet"
        ),
        ownership_type="USER_OWNED",
        wallet_role="SECONDARY",
        source="TEST",
    )

    synthetic_transaction = {
        "txhash": (
            "0xtask81internal"
        ),
        "datetime": (
            "2026-08-21 00:00:00"
        ),
        "movements": [
            {
                "from_address": (
                    RONIN_WALLET_ADDRESS
                ),
                "to_address": (
                    test_secondary
                ),
                "asset": (
                    "Ronin Wrapped Ether"
                ),
                "value_in": "0",
                "value_out": "1",
            }
        ],
    }

    record = (
        build_basic_accounting_record(
            AXIEOS_DB_PATH,
            synthetic_transaction,
        )
    )

    record = (
        enrich_non_marketplace_accounting_record(
            AXIEOS_DB_PATH,
            record,
            synthetic_transaction,
        )
    )

    record = (
        apply_internal_transfer_accounting_treatment(
            record
        )
    )

    current_transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    historical_internal = 0
    false_positive_internal = 0

    for transaction in current_transactions:
        historical_record = (
            build_basic_accounting_record(
                AXIEOS_DB_PATH,
                transaction,
            )
        )

        historical_record = (
            apply_internal_transfer_accounting_treatment(
                historical_record
            )
        )

        if historical_record[
            "is_internal_transfer"
        ]:
            historical_internal += 1

            if (
                historical_record[
                    "accounting_status"
                ]
                != "NON_TAXABLE_INTERNAL"
            ):
                false_positive_internal += 1

    synthetic_valid = (
        record["classification"]
        == "INTERNAL_TRANSFER"
        and record["event_type"]
        == "INTERNAL_TRANSFER"
        and record[
            "is_internal_transfer"
        ]
        is True
        and record[
            "accounting_status"
        ]
        == "NON_TAXABLE_INTERNAL"
        and record[
            "gross_amount"
        ]
        is None
        and record[
            "net_amount"
        ]
        is None
        and record[
            "realized_pl"
        ]
        is None
        and validate_accounting_record(
            record
        )
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    connection.execute(
        """
        DELETE FROM ronin_wallet_registry
        WHERE address = ?
        """,
        (
            normalize_address(
                test_secondary
            ),
        ),
    )

    connection.commit()
    connection.close()

    cleanup_entry = (
        get_wallet_registry_entry(
            AXIEOS_DB_PATH,
            test_secondary,
        )
    )

    cleanup_valid = (
        cleanup_entry[
            "ownership_type"
        ]
        == "UNKNOWN"
    )

    validation = (
        synthetic_valid
        and false_positive_internal
        == 0
        and cleanup_valid
    )

    print(
        "\nRONIN INTERNAL-TRANSFER ACCOUNTING"
    )

    print(
        "Historical transactions:",
        len(current_transactions),
    )

    print(
        "Historical internal transfers:",
        historical_internal,
    )

    print(
        "Internal treatment errors:",
        false_positive_internal,
    )

    print(
        "Synthetic internal transfer:",
        (
            "PASS"
            if synthetic_valid
            else "FAIL"
        ),
    )

    print(
        "Test wallet cleanup:",
        (
            "PASS"
            if cleanup_valid
            else "FAIL"
        ),
    )

    print(
        "\nSYNTHETIC RECORD"
    )

    print(
        "Classification:",
        record["classification"],
    )

    print(
        "Event:",
        record["event_type"],
    )

    print(
        "Asset:",
        record["asset_name"],
    )

    print(
        "Quantity:",
        record["quantity"],
    )

    print(
        "Direction:",
        record["direction"],
    )

    print(
        "Internal:",
        record[
            "is_internal_transfer"
        ],
    )

    print(
        "Counterparty:",
        record[
            "counterparty_role"
        ],
    )

    print(
        "Gross:",
        record["gross_amount"],
    )

    print(
        "Net:",
        record["net_amount"],
    )

    print(
        "Realized P/L:",
        record["realized_pl"],
    )

    print(
        "Status:",
        record[
            "accounting_status"
        ],
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_accounting_persistence_test():
    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_asset_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_accounting_records_table(
        AXIEOS_DB_PATH
    )

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    counterparties = (
        discover_high_confidence_counterparties(
            transactions
        )
    )

    register_discovered_counterparties(
        AXIEOS_DB_PATH,
        counterparties,
    )

    assets = (
        discover_assets_from_raw_transfers(
            AXIEOS_DB_PATH
        )
    )

    store_asset_registry_entries(
        AXIEOS_DB_PATH,
        assets,
    )

    economics_map = (
        build_current_marketplace_economics_map(
            transactions
        )
    )

    records = []

    invalid_records = []

    for transaction in transactions:
        record = (
            build_complete_accounting_record(
                AXIEOS_DB_PATH,
                transaction,
                economics_map,
            )
        )

        records.append(record)

        if not validate_accounting_record(
            record
        ):
            invalid_records.append(
                record
            )

    # -----------------------------
    # First write
    # -----------------------------

    first_processed = (
        store_accounting_records(
            AXIEOS_DB_PATH,
            records,
        )
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    first_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_accounting_records
        """
    ).fetchone()[0]

    connection.close()

    # -----------------------------
    # Second write
    # -----------------------------

    second_processed = (
        store_accounting_records(
            AXIEOS_DB_PATH,
            records,
        )
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    second_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_accounting_records
        """
    ).fetchone()[0]

    unique_keys = connection.execute(
        """
        SELECT COUNT(
            DISTINCT accounting_key
        )
        FROM blockchain_accounting_records
        """
    ).fetchone()[0]

    invalid_versions = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE accounting_version != ?
            """,
            (
                ACCOUNTING_VERSION,
            ),
        ).fetchone()[0]
    )

    ready_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_accounting_records
        WHERE accounting_status = 'READY'
        """
    ).fetchone()[0]

    review_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_accounting_records
        WHERE accounting_status = 'REVIEW'
        """
    ).fetchone()[0]

    internal_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_accounting_records
        WHERE accounting_status =
            'NON_TAXABLE_INTERNAL'
        """
    ).fetchone()[0]

    informational_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE accounting_status =
                'INFORMATIONAL'
            """
        ).fetchone()[0]
    )

    connection.close()

    idempotency_valid = (
        first_count
        == second_count
        == unique_keys
        == len(records)
    )

    validation = (
        len(invalid_records) == 0
        and first_processed
        == len(records)
        and second_processed
        == len(records)
        and idempotency_valid
        and invalid_versions == 0
    )

    print(
        "\nRONIN ACCOUNTING PERSISTENCE"
    )

    print(
        "Transactions:",
        len(transactions),
    )

    print(
        "Accounting records built:",
        len(records),
    )

    print(
        "Invalid records:",
        len(invalid_records),
    )

    print(
        "First write processed:",
        first_processed,
    )

    print(
        "Rows after first write:",
        first_count,
    )

    print(
        "Second write processed:",
        second_processed,
    )

    print(
        "Rows after second write:",
        second_count,
    )

    print(
        "Unique accounting keys:",
        unique_keys,
    )

    print(
        "Invalid versions:",
        invalid_versions,
    )

    print(
        "\nACCOUNTING STATUS"
    )

    print(
        "READY:",
        ready_count,
    )

    print(
        "REVIEW:",
        review_count,
    )

    print(
        "NON_TAXABLE_INTERNAL:",
        internal_count,
    )

    print(
        "INFORMATIONAL:",
        informational_count,
    )

    print(
        "\nIdempotency:",
        (
            "PASS"
            if idempotency_valid
            else "FAIL"
        ),
    )

    print(
        "Validation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def run_accounting_reconciliation_test():
    result = (
        validate_accounting_reconciliation(
            AXIEOS_DB_PATH
        )
    )

    print(
        "\nRONIN ACCOUNTING RECONCILIATION"
    )

    print(
        "Blockchain transactions:",
        result["transactions"],
    )

    print(
        "Accounting records:",
        result[
            "accounting_records"
        ],
    )

    print(
        "Duplicate accounting keys:",
        result["duplicate_keys"],
    )

    print(
        "Missing classifications:",
        result[
            "missing_classifications"
        ],
    )

    print(
        "Classification mismatches:",
        result[
            "classification_mismatches"
        ],
    )

    print(
        "Event type mismatches:",
        result[
            "event_type_mismatches"
        ],
    )

    print(
        "\nMARKETPLACE RECONCILIATION"
    )

    print(
        "Marketplace accounting records:",
        result[
            "marketplace_records"
        ],
    )

    print(
        "Economic events:",
        result[
            "economic_events"
        ],
    )

    print(
        "Accounting realized sales:",
        result[
            "realized_sales"
        ],
    )

    print(
        "Economics realized sales:",
        result[
            "economics_realized_sales"
        ],
    )

    print(
        "Accounting realized P/L:",
        result[
            "realized_pl"
        ],
        "WETH",
    )

    print(
        "Economics realized P/L:",
        result[
            "economics_realized_pl"
        ],
        "WETH",
    )

    print(
        "\nACCOUNTING STATUS"
    )

    for status in sorted(
        result["status_counts"]
    ):
        print(
            f"{status}: "
            f"{result['status_counts'][status]}"
        )

    print(
        "\nACCOUNTING EVENT TYPES"
    )

    for event_type in sorted(
        result["event_counts"]
    ):
        print(
            f"{event_type}: "
            f"{result['event_counts'][event_type]}"
        )

    print(
        "\nValidation:",
        (
            "PASS"
            if result["validation"]
            else "FAIL"
        ),
    )


def run_ronin_sync_v06(
    incremental_max_pages=20,
    backfill_pages=1,
):
    # ---------------------------------
    # Run the complete V0.5 pipeline
    # ---------------------------------

    run_ronin_sync_v05(
        incremental_max_pages=(
            incremental_max_pages
        ),
        backfill_pages=backfill_pages,
    )

    print(
        "\nAXIEOS AUTOMATED "
        "ACCOUNTING PIPELINE V0.6"
    )

    # ---------------------------------
    # Accounting table
    # ---------------------------------

    initialize_accounting_records_table(
        AXIEOS_DB_PATH
    )

    # ---------------------------------
    # Current blockchain transactions
    # ---------------------------------

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    # ---------------------------------
    # Marketplace economics
    # ---------------------------------

    economics_map = (
        build_current_marketplace_economics_map(
            transactions
        )
    )

    # ---------------------------------
    # Build accounting records
    # ---------------------------------

    records = []
    invalid_records = []

    for transaction in transactions:
        record = (
            build_complete_accounting_record(
                AXIEOS_DB_PATH,
                transaction,
                economics_map,
            )
        )

        records.append(record)

        if not validate_accounting_record(
            record
        ):
            invalid_records.append(
                record
            )

    # ---------------------------------
    # Persist accounting records
    # ---------------------------------

    records_processed = (
        store_accounting_records(
            AXIEOS_DB_PATH,
            records,
        )
    )

    # ---------------------------------
    # Reconciliation
    # ---------------------------------

    reconciliation = (
        validate_accounting_reconciliation(
            AXIEOS_DB_PATH
        )
    )

    # ---------------------------------
    # Database validation
    # ---------------------------------

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    accounting_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            """
        ).fetchone()[0]
    )

    unique_accounting_keys = (
        connection.execute(
            """
            SELECT COUNT(
                DISTINCT accounting_key
            )
            FROM blockchain_accounting_records
            """
        ).fetchone()[0]
    )

    invalid_versions = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE accounting_version != ?
            """,
            (
                ACCOUNTING_VERSION,
            ),
        ).fetchone()[0]
    )

    ready_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE accounting_status =
                'READY'
            """
        ).fetchone()[0]
    )

    review_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE accounting_status =
                'REVIEW'
            """
        ).fetchone()[0]
    )

    internal_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE accounting_status =
                'NON_TAXABLE_INTERNAL'
            """
        ).fetchone()[0]
    )

    informational_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE accounting_status =
                'INFORMATIONAL'
            """
        ).fetchone()[0]
    )

    connection.close()

    # ---------------------------------
    # Validation rules
    # ---------------------------------

    record_count_valid = (
        accounting_count
        == unique_accounting_keys
        == len(transactions)
        == len(records)
    )

    processing_valid = (
        records_processed
        == len(records)
    )

    schema_valid = (
        len(invalid_records)
        == 0
    )

    version_valid = (
        invalid_versions == 0
    )

    status_total_valid = (
        (
            ready_count
            + review_count
            + internal_count
            + informational_count
        )
        == accounting_count
    )

    reconciliation_valid = (
        reconciliation[
            "validation"
        ]
    )

    final_passed = (
        record_count_valid
        and processing_valid
        and schema_valid
        and version_valid
        and status_total_valid
        and reconciliation_valid
    )

    # ---------------------------------
    # Output
    # ---------------------------------

    print(
        "\nACCOUNTING RECORDS"
    )

    print(
        "Blockchain transactions:",
        len(transactions),
    )

    print(
        "Records built:",
        len(records),
    )

    print(
        "Records processed:",
        records_processed,
    )

    print(
        "Records stored:",
        accounting_count,
    )

    print(
        "Unique accounting keys:",
        unique_accounting_keys,
    )

    print(
        "Invalid records:",
        len(invalid_records),
    )

    print(
        "Invalid versions:",
        invalid_versions,
    )

    print(
        "\nACCOUNTING STATUS"
    )

    print(
        "READY:",
        ready_count,
    )

    print(
        "REVIEW:",
        review_count,
    )

    print(
        "NON_TAXABLE_INTERNAL:",
        internal_count,
    )

    print(
        "INFORMATIONAL:",
        informational_count,
    )

    print(
        "\nACCOUNTING RECONCILIATION"
    )

    print(
        "Marketplace records:",
        reconciliation[
            "marketplace_records"
        ],
    )

    print(
        "Economic events:",
        reconciliation[
            "economic_events"
        ],
    )

    print(
        "Realized sales:",
        reconciliation[
            "realized_sales"
        ],
    )

    print(
        "Realized P/L:",
        reconciliation[
            "realized_pl"
        ],
        "WETH",
    )

    print(
        "Duplicate keys:",
        reconciliation[
            "duplicate_keys"
        ],
    )

    print(
        "Missing classifications:",
        reconciliation[
            "missing_classifications"
        ],
    )

    print(
        "Classification mismatches:",
        reconciliation[
            "classification_mismatches"
        ],
    )

    print(
        "Event type mismatches:",
        reconciliation[
            "event_type_mismatches"
        ],
    )

    print(
        "\nRONIN V0.6 VALIDATION"
    )

    print(
        "Accounting schema:",
        (
            "PASS"
            if schema_valid
            else "FAIL"
        ),
    )

    print(
        "Accounting persistence:",
        (
            "PASS"
            if (
                record_count_valid
                and processing_valid
            )
            else "FAIL"
        ),
    )

    print(
        "Accounting version:",
        (
            "PASS"
            if version_valid
            else "FAIL"
        ),
    )

    print(
        "Status reconciliation:",
        (
            "PASS"
            if status_total_valid
            else "FAIL"
        ),
    )

    print(
        "Economic reconciliation:",
        (
            "PASS"
            if reconciliation_valid
            else "FAIL"
        ),
    )

    print(
        "Pipeline version:",
        ACCOUNTING_VERSION,
    )

    print(
        "Validation:",
        (
            "PASS"
            if final_passed
            else "FAIL"
        ),
    )


def run_accounting_review_queue_test():
    queue = (
        load_accounting_review_queue(
            AXIEOS_DB_PATH
        )
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    total_records = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_accounting_records
        """
    ).fetchone()[0]

    review_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM blockchain_accounting_records
        WHERE accounting_status = 'REVIEW'
        """
    ).fetchone()[0]

    connection.close()

    event_counts = {}

    invalid_queue_rows = []

    for record in queue:
        event_type = record[
            "event_type"
        ]

        event_counts[event_type] = (
            event_counts.get(
                event_type,
                0,
            )
            + 1
        )

        if (
            record[
                "accounting_status"
            ]
            != "REVIEW"
        ):
            invalid_queue_rows.append(
                record
            )

    queue_count_valid = (
        len(queue)
        == review_count
    )

    validation = (
        queue_count_valid
        and len(
            invalid_queue_rows
        )
        == 0
    )

    print(
        "\nAXIEOS ACCOUNTING REVIEW QUEUE"
    )

    print(
        "Total accounting records:",
        total_records,
    )

    print(
        "Database REVIEW records:",
        review_count,
    )

    print(
        "Review queue records:",
        len(queue),
    )

    print(
        "Invalid queue rows:",
        len(invalid_queue_rows),
    )

    print(
        "\nREVIEW BREAKDOWN"
    )

    for event_type in sorted(
        event_counts
    ):
        print(
            f"{event_type}: "
            f"{event_counts[event_type]}"
        )

    print(
        "\nREVIEW EXAMPLES"
    )

    for record in queue[:10]:
        print(
            "\nTX:",
            record["txhash"],
        )

        print(
            "Date:",
            record["datetime"],
        )

        print(
            "Event:",
            record["event_type"],
        )

        print(
            "Classification:",
            record[
                "classification"
            ],
        )

        print(
            "Asset:",
            record["asset_name"],
        )

        print(
            "Token ID:",
            record[
                "asset_token_id"
            ],
        )

        print(
            "Quantity:",
            record["quantity"],
        )

        print(
            "Direction:",
            record["direction"],
        )

        print(
            "Counterparty:",
            record[
                "counterparty_role"
            ],
        )

        print(
            "Cost basis:",
            record["cost_basis"],
        )

        print(
            "Realized P/L:",
            record["realized_pl"],
        )

        print(
            "Status:",
            record[
                "accounting_status"
            ],
        )

    print(
        "\nQueue count:",
        (
            "PASS"
            if queue_count_valid
            else "FAIL"
        ),
    )

    print(
        "Validation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


ACCOUNTING_REVIEW_REASON_CODES = {
    "MISSING_COST_BASIS",
    "MISSING_REALIZED_PL",
    "TRANSFER_OWNERSHIP_UNRESOLVED",
    "SWAP_COST_BASIS_PENDING",
    "UNRESOLVED_CLASSIFICATION",
    "UNSPECIFIED_REVIEW_REASON",
}




def load_accounting_review_queue(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT
            accounting_key,
            txhash,
            datetime,
            event_type,
            classification,
            asset_name,
            asset_token_id,
            quantity,
            direction,
            payment_asset,
            gross_amount,
            marketplace_fee,
            net_amount,
            cost_basis,
            realized_pl,
            counterparty_role,
            accounting_status
        FROM blockchain_accounting_records
        WHERE accounting_status = 'REVIEW'
        ORDER BY datetime, txhash
        """
    ).fetchall()

    connection.close()

    queue = []

    for row in rows:
        queue.append(
            {
                "accounting_key": row[0],
                "txhash": row[1],
                "datetime": row[2],
                "event_type": row[3],
                "classification": row[4],
                "asset_name": row[5],
                "asset_token_id": row[6],
                "quantity": row[7],
                "direction": row[8],
                "payment_asset": row[9],
                "gross_amount": row[10],
                "marketplace_fee": row[11],
                "net_amount": row[12],
                "cost_basis": row[13],
                "realized_pl": row[14],
                "counterparty_role": row[15],
                "accounting_status": row[16],
            }
        )

    return queue


def explain_accounting_review_record(
    record,
):
    event_type = record[
        "event_type"
    ]

    # ---------------------------------
    # Marketplace sale
    # ---------------------------------

    if event_type == "ASSET_SALE":
        if record["cost_basis"] is None:
            return {
                "reason_code": (
                    "MISSING_COST_BASIS"
                ),
                "reason": (
                    "Sale proceeds are known, "
                    "but the acquisition cost "
                    "has not been proven."
                ),
            }

        if record["realized_pl"] is None:
            return {
                "reason_code": (
                    "MISSING_REALIZED_PL"
                ),
                "reason": (
                    "Cost basis exists, but "
                    "realized profit or loss "
                    "has not been calculated."
                ),
            }

    # ---------------------------------
    # Transfers
    # ---------------------------------

    if event_type in {
        "TRANSFER_IN",
        "TRANSFER_OUT",
    }:
        return {
            "reason_code": (
                "TRANSFER_OWNERSHIP_UNRESOLVED"
            ),
            "reason": (
                "The ownership or accounting "
                "purpose of the opposite wallet "
                "has not been verified."
            ),
        }

    # ---------------------------------
    # Token swaps
    # ---------------------------------

    if event_type == "TOKEN_SWAP":
        return {
            "reason_code": (
                "SWAP_COST_BASIS_PENDING"
            ),
            "reason": (
                "Both sides of the swap are "
                "known, but cost-basis and "
                "realized P/L treatment is "
                "not yet implemented."
            ),
        }

    # ---------------------------------
    # Unknown transactions
    # ---------------------------------

    if event_type == "UNKNOWN":
        return {
            "reason_code": (
                "UNRESOLVED_CLASSIFICATION"
            ),
            "reason": (
                "The transaction does not yet "
                "match a supported accounting "
                "classification."
            ),
        }

    # ---------------------------------
    # Safety fallback
    # ---------------------------------

    return {
        "reason_code": (
            "UNSPECIFIED_REVIEW_REASON"
        ),
        "reason": (
            "The accounting record is marked "
            "for review, but no specific review "
            "rule currently explains why."
        ),
    }


def enrich_accounting_review_queue(
    queue,
):
    enriched_queue = []

    for record in queue:
        enriched = dict(
            record
        )

        explanation = (
            explain_accounting_review_record(
                record
            )
        )

        enriched[
            "review_reason_code"
        ] = explanation[
            "reason_code"
        ]

        enriched[
            "review_reason"
        ] = explanation[
            "reason"
        ]

        enriched_queue.append(
            enriched
        )

    return enriched_queue


def run_accounting_review_reason_test():
    queue = (
        load_accounting_review_queue(
            AXIEOS_DB_PATH
        )
    )

    enriched_queue = (
        enrich_accounting_review_queue(
            queue
        )
    )

    reason_counts = {}

    invalid_reason_codes = []
    unexplained_records = []

    for record in enriched_queue:
        reason_code = record[
            "review_reason_code"
        ]

        reason_counts[
            reason_code
        ] = (
            reason_counts.get(
                reason_code,
                0,
            )
            + 1
        )

        if (
            reason_code
            not in ACCOUNTING_REVIEW_REASON_CODES
        ):
            invalid_reason_codes.append(
                record
            )

        if (
            reason_code
            == "UNSPECIFIED_REVIEW_REASON"
        ):
            unexplained_records.append(
                record
            )

    queue_count_valid = (
        len(enriched_queue)
        == len(queue)
    )

    validation = (
        queue_count_valid
        and len(
            invalid_reason_codes
        )
        == 0
        and len(
            unexplained_records
        )
        == 0
    )

    print(
        "\nAXIEOS ACCOUNTING REVIEW REASONS"
    )

    print(
        "Review records:",
        len(queue),
    )

    print(
        "Explained records:",
        len(enriched_queue),
    )

    print(
        "Invalid reason codes:",
        len(
            invalid_reason_codes
        ),
    )

    print(
        "Unexplained records:",
        len(
            unexplained_records
        ),
    )

    print(
        "\nREASON BREAKDOWN"
    )

    for reason_code in sorted(
        reason_counts
    ):
        print(
            f"{reason_code}: "
            f"{reason_counts[reason_code]}"
        )

    print(
        "\nREVIEW EXAMPLES"
    )

    for record in enriched_queue[:10]:
        print(
            "\nTX:",
            record["txhash"],
        )

        print(
            "Date:",
            record["datetime"],
        )

        print(
            "Event:",
            record["event_type"],
        )

        print(
            "Asset:",
            record["asset_name"],
        )

        print(
            "Reason code:",
            record[
                "review_reason_code"
            ],
        )

        print(
            "Reason:",
            record[
                "review_reason"
            ],
        )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_transfer_counterparty_resolution_test():
    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_asset_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_accounting_records_table(
        AXIEOS_DB_PATH
    )

    # ---------------------------------
    # Queue before ownership update
    # ---------------------------------

    before_queue = (
        load_accounting_review_queue(
            AXIEOS_DB_PATH
        )
    )

    transfer_reviews_before = sum(
        1
        for record in before_queue
        if record["event_type"] in {
            "TRANSFER_IN",
            "TRANSFER_OUT",
        }
    )

    # ---------------------------------
    # Register known owned wallets
    # ---------------------------------

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    original_wallet_entry = (
        get_wallet_registry_entry(
            AXIEOS_DB_PATH,
            ORIGINAL_RONIN_WALLET_ADDRESS,
        )
    )

    # ---------------------------------
    # Rebuild intelligence dependencies
    # ---------------------------------

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    counterparties = (
        discover_high_confidence_counterparties(
            transactions
        )
    )

    register_discovered_counterparties(
        AXIEOS_DB_PATH,
        counterparties,
    )

    assets = (
        discover_assets_from_raw_transfers(
            AXIEOS_DB_PATH
        )
    )

    store_asset_registry_entries(
        AXIEOS_DB_PATH,
        assets,
    )

    economics_map = (
        build_current_marketplace_economics_map(
            transactions
        )
    )

    # ---------------------------------
    # Rebuild accounting records
    # ---------------------------------

    records = []

    for transaction in transactions:
        record = (
            build_complete_accounting_record(
                AXIEOS_DB_PATH,
                transaction,
                economics_map,
            )
        )

        records.append(record)

    store_accounting_records(
        AXIEOS_DB_PATH,
        records,
    )

    # ---------------------------------
    # Audit after rebuild
    # ---------------------------------

    after_queue = (
        load_accounting_review_queue(
            AXIEOS_DB_PATH
        )
    )

    transfer_reviews_after = sum(
        1
        for record in after_queue
        if record["event_type"] in {
            "TRANSFER_IN",
            "TRANSFER_OUT",
        }
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    internal_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE accounting_status =
                'NON_TAXABLE_INTERNAL'
            """
        ).fetchone()[0]
    )

    connection.close()

    counterparty_audit = (
        audit_transfer_review_counterparties(
            AXIEOS_DB_PATH
        )
    )

    unresolved_counterparties = [
        entry
        for entry in counterparty_audit
        if entry["ownership_type"]
        == "UNKNOWN"
    ]

    original_wallet_valid = (
        original_wallet_entry[
            "ownership_type"
        ]
        == "USER_OWNED"
        and original_wallet_entry[
            "wallet_role"
        ]
        == "SECONDARY"
    )

    validation = (
        original_wallet_valid
        and transfer_reviews_after
        <= transfer_reviews_before
    )

    print(
        "\nAXIEOS TRANSFER COUNTERPARTY RESOLUTION"
    )

    print(
        "Transactions:",
        len(transactions),
    )

    print(
        "Original wallet ownership:",
        original_wallet_entry[
            "ownership_type"
        ],
    )

    print(
        "Original wallet role:",
        original_wallet_entry[
            "wallet_role"
        ],
    )

    print(
        "Transfer reviews before:",
        transfer_reviews_before,
    )

    print(
        "Transfer reviews after:",
        transfer_reviews_after,
    )

    print(
        "Internal transfers:",
        internal_count,
    )

    print(
        "Remaining counterparties:",
        len(counterparty_audit),
    )

    print(
        "Unresolved counterparties:",
        len(
            unresolved_counterparties
        ),
    )

    print(
        "\nTOP UNRESOLVED COUNTERPARTIES"
    )

    for entry in (
        unresolved_counterparties[:15]
    ):
        print(
            "\nAddress:",
            entry["address"],
        )

        print(
            "Transactions:",
            entry[
                "transaction_count"
            ],
        )

        print(
            "Ownership:",
            entry[
                "ownership_type"
            ],
        )

        print(
            "Role:",
            entry["wallet_role"],
        )

    print(
        "\nKnown owned-wallet registration:",
        (
            "PASS"
            if original_wallet_valid
            else "FAIL"
        ),
    )

    print(
        "Validation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def discover_release_contracts(
    transactions,
):
    candidates = {}

    for transaction in transactions:
        if (
            transaction.get("method")
            != "requestReleaseAxie"
        ):
            continue

        for movement in transaction.get(
            "movements",
            [],
        ):
            if (
                movement.get("asset")
                != "Axie"
            ):
                continue

            if (
                get_movement_direction(
                    movement
                )
                != "OUT"
            ):
                continue

            address = (
                get_movement_counterparty(
                    movement
                )
            )

            if address is None:
                continue

            address = normalize_address(
                address
            )

            candidates[address] = (
                candidates.get(
                    address,
                    0,
                )
                + 1
            )

    return candidates


def register_release_contracts(
    db_path,
    candidates,
):
    registered = 0

    for address, evidence in (
        candidates.items()
    ):
        existing = (
            get_wallet_registry_entry(
                db_path,
                address,
            )
        )

        # Never overwrite a wallet
        # already proven user-owned.
        if (
            existing["ownership_type"]
            == "USER_OWNED"
        ):
            continue

        upsert_wallet_registry_entry(
            db_path=db_path,
            address=address,
            wallet_label=(
                "Axie Release Contract"
            ),
            ownership_type="CONTRACT",
            wallet_role="BURN",
            source=(
                "AXIEOS_TRANSACTION_EVIDENCE"
            ),
        )

        registered += 1

    return registered


def build_unresolved_counterparty_history(
    db_path,
):
    audit = (
        audit_transfer_review_counterparties(
            db_path
        )
    )

    unresolved = [
        entry
        for entry in audit
        if entry["ownership_type"]
        == "UNKNOWN"
    ]

    queue = (
        load_accounting_review_queue(
            db_path
        )
    )

    transfer_records = [
        record
        for record in queue
        if record["event_type"] in {
            "TRANSFER_IN",
            "TRANSFER_OUT",
        }
    ]

    wallet = normalize_address(
        RONIN_WALLET_ADDRESS
    )

    connection = sqlite3.connect(
        db_path
    )

    results = []

    for counterparty in unresolved:
        address = counterparty[
            "address"
        ]

        tx_details = []

        for record in transfer_records:
            rows = connection.execute(
                """
                SELECT
                    txhash,
                    datetime,
                    from_address,
                    to_address,
                    method,
                    token_collectibles,
                    value_in,
                    value_out
                FROM blockchain_transactions
                WHERE txhash = ?
                """,
                (
                    record["txhash"],
                ),
            ).fetchall()

            matched = False

            for row in rows:
                (
                    txhash,
                    datetime_value,
                    from_address,
                    to_address,
                    method,
                    asset,
                    value_in,
                    value_out,
                ) = row

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

                if (
                    from_normalized
                    == address
                    and to_normalized
                    == wallet
                ):
                    direction = "IN"
                    quantity = value_in
                    matched = True

                elif (
                    from_normalized
                    == wallet
                    and to_normalized
                    == address
                ):
                    direction = "OUT"
                    quantity = value_out
                    matched = True

                else:
                    continue

                tx_details.append(
                    {
                        "txhash": txhash,
                        "datetime": datetime_value,
                        "direction": direction,
                        "method": method,
                        "asset": asset,
                        "quantity": quantity,
                    }
                )

            if matched:
                continue

        txhashes = {
            detail["txhash"]
            for detail in tx_details
        }

        directions = {}

        assets = {}

        for detail in tx_details:
            direction = detail[
                "direction"
            ]

            directions[direction] = (
                directions.get(
                    direction,
                    0,
                )
                + 1
            )

            asset = detail[
                "asset"
            ]

            if asset is not None:
                assets[asset] = (
                    assets.get(
                        asset,
                        0,
                    )
                    + 1
                )

        dates = [
            detail["datetime"]
            for detail in tx_details
            if detail["datetime"]
            is not None
        ]

        results.append(
            {
                "address": address,
                "transaction_count": len(
                    txhashes
                ),
                "movement_count": len(
                    tx_details
                ),
                "first_date": (
                    min(dates)
                    if dates
                    else None
                ),
                "last_date": (
                    max(dates)
                    if dates
                    else None
                ),
                "directions": directions,
                "assets": assets,
                "examples": tx_details[:5],
            }
        )

    connection.close()

    results.sort(
        key=lambda item: (
            -item[
                "transaction_count"
            ],
            item["address"],
        )
    )

    return results


def run_unresolved_counterparty_history_test():
    results = (
        build_unresolved_counterparty_history(
            AXIEOS_DB_PATH
        )
    )

    print(
        "\nAXIEOS UNRESOLVED COUNTERPARTY HISTORY"
    )

    print(
        "Unresolved counterparties:",
        len(results),
    )

    total_transactions = sum(
        item["transaction_count"]
        for item in results
    )

    print(
        "Counterparty transaction links:",
        total_transactions,
    )

    print(
        "\nTOP COUNTERPARTIES"
    )

    for item in results[:15]:
        print(
            "\nAddress:",
            item["address"],
        )

        print(
            "Transactions:",
            item[
                "transaction_count"
            ],
        )

        print(
            "Movements:",
            item[
                "movement_count"
            ],
        )

        print(
            "First:",
            item["first_date"],
        )

        print(
            "Last:",
            item["last_date"],
        )

        print(
            "Directions:",
            item["directions"],
        )

        print(
            "Assets:",
            item["assets"],
        )

        print(
            "Examples:"
        )

        for example in item[
            "examples"
        ]:
            print(
                " ",
                example[
                    "datetime"
                ],
                example[
                    "direction"
                ],
                example[
                    "asset"
                ],
                example[
                    "quantity"
                ],
                example[
                    "method"
                ],
                example[
                    "txhash"
                ],
            )

    validation = (
        len(results) > 0
        and all(
            item[
                "transaction_count"
            ]
            > 0
            for item in results
        )
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def run_protocol_transfer_resolution_test():
    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_asset_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_accounting_records_table(
        AXIEOS_DB_PATH
    )

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    before_queue = (
        load_accounting_review_queue(
            AXIEOS_DB_PATH
        )
    )

    transfers_before = sum(
        1
        for record in before_queue
        if record["event_type"] in {
            "TRANSFER_IN",
            "TRANSFER_OUT",
        }
    )

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    release_candidates = (
        discover_release_contracts(
            transactions
        )
    )

    release_registered = (
        register_release_contracts(
            AXIEOS_DB_PATH,
            release_candidates,
        )
    )

    counterparties = (
        discover_high_confidence_counterparties(
            transactions
        )
    )

    register_discovered_counterparties(
        AXIEOS_DB_PATH,
        counterparties,
    )

    assets = (
        discover_assets_from_raw_transfers(
            AXIEOS_DB_PATH
        )
    )

    store_asset_registry_entries(
        AXIEOS_DB_PATH,
        assets,
    )

    # Keep persistent classification
    # synchronized with the new rules.
    store_intelligent_transaction_classifications(
        AXIEOS_DB_PATH,
        transactions,
    )

    economics_map = (
        build_current_marketplace_economics_map(
            transactions
        )
    )

    records = []

    for transaction in transactions:
        records.append(
            build_complete_accounting_record(
                AXIEOS_DB_PATH,
                transaction,
                economics_map,
            )
        )

    store_accounting_records(
        AXIEOS_DB_PATH,
        records,
    )

    after_queue = (
        load_accounting_review_queue(
            AXIEOS_DB_PATH
        )
    )

    transfers_after = sum(
        1
        for record in after_queue
        if record["event_type"] in {
            "TRANSFER_IN",
            "TRANSFER_OUT",
        }
    )

    burn_records = sum(
        1
        for record in records
        if (
            record["event_type"]
            == "ASSET_BURN"
            and record[
                "accounting_status"
            ]
            == "READY"
        )
    )

    staking_records = sum(
        1
        for record in records
        if (
            record["event_type"]
            == "STAKING_OR_REWARD"
            and record[
                "accounting_status"
            ]
            == "READY"
        )
    )

    resolved = (
        transfers_before
        - transfers_after
    )

    validation = (
        release_registered > 0
        and resolved > 0
        and transfers_after
        < transfers_before
    )

    print(
        "\nAXIEOS PROTOCOL TRANSFER RESOLUTION"
    )

    print(
        "Transactions:",
        len(transactions),
    )

    print(
        "Release contracts discovered:",
        len(release_candidates),
    )

    print(
        "Release contracts registered:",
        release_registered,
    )

    print(
        "Transfer reviews before:",
        transfers_before,
    )

    print(
        "Transfer reviews after:",
        transfers_after,
    )

    print(
        "Transfer reviews resolved:",
        resolved,
    )

    print(
        "READY burn records:",
        burn_records,
    )

    print(
        "READY staking/reward records:",
        staking_records,
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def run_staking_role_resolution_test():
    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_asset_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_accounting_records_table(
        AXIEOS_DB_PATH
    )

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    before_queue = (
        load_accounting_review_queue(
            AXIEOS_DB_PATH
        )
    )

    transfers_before = sum(
        1
        for record in before_queue
        if record["event_type"] in {
            "TRANSFER_IN",
            "TRANSFER_OUT",
        }
    )

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    release_candidates = (
        discover_release_contracts(
            transactions
        )
    )

    register_release_contracts(
        AXIEOS_DB_PATH,
        release_candidates,
    )

    # First pass discovers the known
    # staking contract from explicit
    # staking/reward transactions.
    counterparties = (
        discover_high_confidence_counterparties(
            transactions
        )
    )

    register_discovered_counterparties(
        AXIEOS_DB_PATH,
        counterparties,
    )

    # Reclassify now that wallet roles
    # are known.
    store_intelligent_transaction_classifications(
        AXIEOS_DB_PATH,
        transactions,
    )

    assets = (
        discover_assets_from_raw_transfers(
            AXIEOS_DB_PATH
        )
    )

    store_asset_registry_entries(
        AXIEOS_DB_PATH,
        assets,
    )

    economics_map = (
        build_current_marketplace_economics_map(
            transactions
        )
    )

    records = []

    for transaction in transactions:
        records.append(
            build_complete_accounting_record(
                AXIEOS_DB_PATH,
                transaction,
                economics_map,
            )
        )

    store_accounting_records(
        AXIEOS_DB_PATH,
        records,
    )

    after_queue = (
        load_accounting_review_queue(
            AXIEOS_DB_PATH
        )
    )

    transfers_after = sum(
        1
        for record in after_queue
        if record["event_type"] in {
            "TRANSFER_IN",
            "TRANSFER_OUT",
        }
    )

    staking_ready = sum(
        1
        for record in records
        if (
            record["event_type"]
            == "STAKING_OR_REWARD"
            and record[
                "accounting_status"
            ]
            == "READY"
        )
    )

    resolved = (
        transfers_before
        - transfers_after
    )

    validation = (
        transfers_after
        <= transfers_before
        and staking_ready > 0
    )

    print(
        "\nAXIEOS STAKING ROLE RESOLUTION"
    )

    print(
        "Transactions:",
        len(transactions),
    )

    print(
        "Transfer reviews before:",
        transfers_before,
    )

    print(
        "Transfer reviews after:",
        transfers_after,
    )

    print(
        "Additional transfers resolved:",
        resolved,
    )

    print(
        "READY staking/reward records:",
        staking_ready,
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def audit_remaining_transfer_roles(
    db_path,
):
    queue = (
        load_accounting_review_queue(
            db_path
        )
    )

    transfer_records = [
        record
        for record in queue
        if record["event_type"] in {
            "TRANSFER_IN",
            "TRANSFER_OUT",
        }
    ]

    wallet = normalize_address(
        RONIN_WALLET_ADDRESS
    )

    connection = sqlite3.connect(
        db_path
    )

    results = []

    for record in transfer_records:
        rows = connection.execute(
            """
            SELECT
                from_address,
                to_address
            FROM blockchain_transactions
            WHERE txhash = ?
            """,
            (
                record["txhash"],
            ),
        ).fetchall()

        addresses = set()

        for (
            from_address,
            to_address,
        ) in rows:
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

            if (
                record["event_type"]
                == "TRANSFER_IN"
                and to_normalized == wallet
                and from_normalized != wallet
            ):
                addresses.add(
                    from_normalized
                )

            elif (
                record["event_type"]
                == "TRANSFER_OUT"
                and from_normalized == wallet
                and to_normalized != wallet
            ):
                addresses.add(
                    to_normalized
                )

        counterparties = []

        for address in sorted(
            addresses
        ):
            entry = (
                get_wallet_registry_entry(
                    db_path,
                    address,
                )
            )

            counterparties.append(
                {
                    "address": address,
                    "ownership_type": (
                        entry[
                            "ownership_type"
                        ]
                    ),
                    "wallet_role": (
                        entry[
                            "wallet_role"
                        ]
                    ),
                }
            )

        ownership_types = {
            item["ownership_type"]
            for item in counterparties
        }

        roles = {
            item["wallet_role"]
            for item in counterparties
        }

        if not counterparties:
            bucket = "NO_COUNTERPARTY"

        elif (
            "USER_OWNED"
            in ownership_types
        ):
            bucket = "USER_OWNED"

        elif (
            ownership_types
            == {"UNKNOWN"}
        ):
            bucket = "UNKNOWN_ONLY"

        elif (
            "UNKNOWN"
            in ownership_types
        ):
            bucket = "MIXED"

        else:
            bucket = "KNOWN_ROLE"

        results.append(
            {
                "txhash": record[
                    "txhash"
                ],
                "datetime": record[
                    "datetime"
                ],
                "event_type": record[
                    "event_type"
                ],
                "asset_name": record[
                    "asset_name"
                ],
                "quantity": record[
                    "quantity"
                ],
                "direction": record[
                    "direction"
                ],
                "bucket": bucket,
                "roles": sorted(
                    roles
                ),
                "counterparties": (
                    counterparties
                ),
            }
        )

    connection.close()

    return results


def run_remaining_transfer_role_audit_test():
    results = (
        audit_remaining_transfer_roles(
            AXIEOS_DB_PATH
        )
    )

    bucket_counts = {}
    role_counts = {}

    for item in results:
        bucket = item["bucket"]

        bucket_counts[bucket] = (
            bucket_counts.get(
                bucket,
                0,
            )
            + 1
        )

        for role in item["roles"]:
            role_counts[role] = (
                role_counts.get(
                    role,
                    0,
                )
                + 1
            )

    known_role_records = [
        item
        for item in results
        if item["bucket"]
        in {
            "KNOWN_ROLE",
            "MIXED",
            "USER_OWNED",
        }
    ]

    no_counterparty_records = [
        item
        for item in results
        if item["bucket"]
        == "NO_COUNTERPARTY"
    ]

    validation = (
        sum(
            bucket_counts.values()
        )
        == len(results)
    )

    print(
        "\nAXIEOS REMAINING TRANSFER ROLE AUDIT"
    )

    print(
        "Remaining transfer reviews:",
        len(results),
    )

    print(
        "\nBUCKETS"
    )

    for bucket in sorted(
        bucket_counts
    ):
        print(
            f"{bucket}: "
            f"{bucket_counts[bucket]}"
        )

    print(
        "\nREGISTERED ROLE COUNTS"
    )

    for role in sorted(
        role_counts
    ):
        print(
            f"{role}: "
            f"{role_counts[role]}"
        )

    print(
        "\nKNOWN-ROLE TRANSFERS"
    )

    for item in (
        known_role_records[:20]
    ):
        print(
            "\nTX:",
            item["txhash"],
        )

        print(
            "Date:",
            item["datetime"],
        )

        print(
            "Event:",
            item["event_type"],
        )

        print(
            "Asset:",
            item["asset_name"],
        )

        print(
            "Quantity:",
            item["quantity"],
        )

        print(
            "Direction:",
            item["direction"],
        )

        print(
            "Bucket:",
            item["bucket"],
        )

        print(
            "Roles:",
            item["roles"],
        )

        for counterparty in item[
            "counterparties"
        ]:
            print(
                "Counterparty:",
                counterparty[
                    "address"
                ],
                counterparty[
                    "ownership_type"
                ],
                counterparty[
                    "wallet_role"
                ],
            )

    if no_counterparty_records:
        print(
            "\nNO-COUNTERPARTY TRANSFERS"
        )

        for item in (
            no_counterparty_records[:10]
        ):
            print(
                "\nTX:",
                item["txhash"],
            )

            print(
                "Date:",
                item["datetime"],
            )

            print(
                "Event:",
                item["event_type"],
            )

            print(
                "Asset:",
                item["asset_name"],
            )

            print(
                "Direction:",
                item["direction"],
            )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def run_known_role_transaction_bundle_audit():
    audit = (
        audit_remaining_transfer_roles(
            AXIEOS_DB_PATH
        )
    )

    known_role_records = [
        item
        for item in audit
        if item["bucket"]
        == "KNOWN_ROLE"
    ]

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    valid_bundles = 0

    print(
        "\nAXIEOS KNOWN-ROLE TRANSACTION BUNDLES"
    )

    print(
        "Known-role transfer reviews:",
        len(known_role_records),
    )

    for item in known_role_records:
        txhash = item["txhash"]

        classification_row = (
            connection.execute(
                """
                SELECT
                    classification,
                    confidence,
                    reason
                FROM blockchain_transaction_classifications
                WHERE txhash = ?
                """,
                (
                    txhash,
                ),
            ).fetchone()
        )

        movement_rows = (
            connection.execute(
                """
                SELECT
                    datetime,
                    method,
                    token_collectibles,
                    value_in,
                    value_out,
                    from_address,
                    to_address
                FROM blockchain_transactions
                WHERE txhash = ?
                ORDER BY id
                """,
                (
                    txhash,
                ),
            ).fetchall()
        )

        if movement_rows:
            valid_bundles += 1

        print(
            "\n--------------------------------"
        )

        print(
            "TX:",
            txhash,
        )

        print(
            "Date:",
            item["datetime"],
        )

        print(
            "Current accounting event:",
            item["event_type"],
        )

        print(
            "Primary asset:",
            item["asset_name"],
        )

        print(
            "Registered roles:",
            item["roles"],
        )

        if classification_row:
            print(
                "Stored classification:",
                classification_row[0],
            )

            print(
                "Confidence:",
                classification_row[1],
            )

            print(
                "Reason:",
                classification_row[2],
            )

        print(
            "Movement rows:",
            len(movement_rows),
        )

        print(
            "MOVEMENTS"
        )

        for row in movement_rows:
            (
                datetime_value,
                method,
                asset,
                value_in,
                value_out,
                from_address,
                to_address,
            ) = row

            from_entry = (
                get_wallet_registry_entry(
                    AXIEOS_DB_PATH,
                    from_address,
                )
            )

            to_entry = (
                get_wallet_registry_entry(
                    AXIEOS_DB_PATH,
                    to_address,
                )
            )

            print(
                "\n  Method:",
                method,
            )

            print(
                "  Asset:",
                asset,
            )

            print(
                "  Value IN:",
                value_in,
            )

            print(
                "  Value OUT:",
                value_out,
            )

            print(
                "  From:",
                from_address,
            )

            print(
                "  From ownership:",
                from_entry[
                    "ownership_type"
                ],
            )

            print(
                "  From role:",
                from_entry[
                    "wallet_role"
                ],
            )

            print(
                "  To:",
                to_address,
            )

            print(
                "  To ownership:",
                to_entry[
                    "ownership_type"
                ],
            )

            print(
                "  To role:",
                to_entry[
                    "wallet_role"
                ],
            )

    connection.close()

    validation = (
        valid_bundles
        == len(known_role_records)
    )

    print(
        "\nBundles inspected:",
        valid_bundles,
    )

    print(
        "Validation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def run_known_role_resolution_test():
    initialize_wallet_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_asset_registry_table(
        AXIEOS_DB_PATH
    )

    initialize_accounting_records_table(
        AXIEOS_DB_PATH
    )

    seed_default_wallet_registry(
        AXIEOS_DB_PATH
    )

    before_queue = (
        load_accounting_review_queue(
            AXIEOS_DB_PATH
        )
    )

    transfers_before = sum(
        1
        for record in before_queue
        if record["event_type"] in {
            "TRANSFER_IN",
            "TRANSFER_OUT",
        }
    )

    transactions = (
        group_ledger_rows_by_txhash(
            AXIEOS_DB_PATH
        )
    )

    release_candidates = (
        discover_release_contracts(
            transactions
        )
    )

    register_release_contracts(
        AXIEOS_DB_PATH,
        release_candidates,
    )

    counterparties = (
        discover_high_confidence_counterparties(
            transactions
        )
    )

    register_discovered_counterparties(
        AXIEOS_DB_PATH,
        counterparties,
    )

    store_intelligent_transaction_classifications(
        AXIEOS_DB_PATH,
        transactions,
    )

    assets = (
        discover_assets_from_raw_transfers(
            AXIEOS_DB_PATH
        )
    )

    store_asset_registry_entries(
        AXIEOS_DB_PATH,
        assets,
    )

    economics_map = (
        build_current_marketplace_economics_map(
            transactions
        )
    )

    records = []

    for transaction in transactions:
        records.append(
            build_complete_accounting_record(
                AXIEOS_DB_PATH,
                transaction,
                economics_map,
            )
        )

    store_accounting_records(
        AXIEOS_DB_PATH,
        records,
    )

    after_queue = (
        load_accounting_review_queue(
            AXIEOS_DB_PATH
        )
    )

    transfers_after = sum(
        1
        for record in after_queue
        if record["event_type"] in {
            "TRANSFER_IN",
            "TRANSFER_OUT",
        }
    )

    remaining_role_audit = (
        audit_remaining_transfer_roles(
            AXIEOS_DB_PATH
        )
    )

    known_role_remaining = sum(
        1
        for item
        in remaining_role_audit
        if item["bucket"]
        == "KNOWN_ROLE"
    )

    token_burn_ready = sum(
        1
        for record in records
        if (
            record["classification"]
            == "TOKEN_BURN"
            and record[
                "accounting_status"
            ]
            == "READY"
        )
    )

    staking_ready = sum(
        1
        for record in records
        if (
            record["classification"]
            == "STAKING_OR_REWARD"
            and record[
                "accounting_status"
            ]
            == "READY"
        )
    )

    resolved = (
        transfers_before
        - transfers_after
    )

    validation = (
        resolved > 0
        and known_role_remaining == 0
        and transfers_after
        < transfers_before
    )

    print(
        "\nAXIEOS KNOWN-ROLE RESOLUTION"
    )

    print(
        "Transactions:",
        len(transactions),
    )

    print(
        "Transfer reviews before:",
        transfers_before,
    )

    print(
        "Transfer reviews after:",
        transfers_after,
    )

    print(
        "Transfers resolved:",
        resolved,
    )

    print(
        "Known-role transfers remaining:",
        known_role_remaining,
    )

    print(
        "READY token burns:",
        token_burn_ready,
    )

    print(
        "READY staking/reward records:",
        staking_ready,
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def audit_missing_cost_basis_sales(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    sales = connection.execute(
        """
        SELECT
            txhash,
            datetime,
            asset_name,
            asset_token_id,
            quantity,
            gross_amount,
            net_amount,
            cost_basis,
            realized_pl
        FROM blockchain_accounting_records
        WHERE event_type = 'ASSET_SALE'
          AND accounting_status = 'REVIEW'
          AND cost_basis IS NULL
        ORDER BY datetime, txhash
        """
    ).fetchall()

    results = []

    for sale in sales:
        (
            txhash,
            datetime_value,
            asset_name,
            asset_token_id,
            quantity,
            gross_amount,
            net_amount,
            cost_basis,
            realized_pl,
        ) = sale

        candidates = []

        if asset_token_id is not None:
            candidate_rows = connection.execute(
                """
                SELECT
                    txhash,
                    datetime,
                    event_type,
                    asset_name,
                    asset_token_id,
                    quantity,
                    gross_amount,
                    accounting_status
                FROM blockchain_accounting_records
                WHERE asset_token_id = ?
                  AND datetime < ?
                  AND event_type IN (
                      'ASSET_PURCHASE',
                      'TRANSFER_IN',
                      'MINT_OR_CLAIM'
                  )
                ORDER BY datetime DESC
                """,
                (
                    asset_token_id,
                    datetime_value,
                ),
            ).fetchall()

            for candidate in candidate_rows:
                candidates.append(
                    {
                        "txhash": candidate[0],
                        "datetime": candidate[1],
                        "event_type": candidate[2],
                        "asset_name": candidate[3],
                        "asset_token_id": candidate[4],
                        "quantity": candidate[5],
                        "gross_amount": candidate[6],
                        "accounting_status": candidate[7],
                    }
                )

        if asset_token_id is None:
            evidence_status = (
                "MISSING_TOKEN_ID"
            )

        elif any(
            candidate["event_type"]
            == "ASSET_PURCHASE"
            for candidate in candidates
        ):
            evidence_status = (
                "PRIOR_PURCHASE_FOUND"
            )

        elif candidates:
            evidence_status = (
                "PRIOR_INBOUND_FOUND"
            )

        else:
            evidence_status = (
                "NO_PRIOR_EVIDENCE"
            )

        results.append(
            {
                "txhash": txhash,
                "datetime": datetime_value,
                "asset_name": asset_name,
                "asset_token_id": asset_token_id,
                "quantity": quantity,
                "gross_amount": gross_amount,
                "net_amount": net_amount,
                "evidence_status": (
                    evidence_status
                ),
                "candidates": candidates,
            }
        )

    connection.close()

    return results


COST_BASIS_METHOD_CANDIDATES = {
    "EXACT_NFT_PURCHASE",
    "INVENTORY_POOL_REQUIRED",
    "NFT_INBOUND_BASIS_REVIEW",
    "NO_PRIOR_EVIDENCE",
    "UNRESOLVED_METHOD",
}


def classify_missing_cost_basis_methods(
    db_path,
):
    audit_results = (
        audit_missing_cost_basis_sales(
            db_path
        )
    )

    audit_map = {
        item["txhash"]: item
        for item in audit_results
    }

    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT
            txhash,
            datetime,
            asset_name,
            asset_token_id,
            asset_category,
            quantity,
            net_amount
        FROM blockchain_accounting_records
        WHERE event_type = 'ASSET_SALE'
          AND accounting_status = 'REVIEW'
          AND cost_basis IS NULL
        ORDER BY datetime, txhash
        """
    ).fetchall()

    connection.close()

    results = []

    inventory_categories = {
        "CONSUMABLE",
        "MATERIAL",
        "MULTI_TOKEN",
        "FUNGIBLE_TOKEN",
    }

    for row in rows:
        (
            txhash,
            datetime_value,
            asset_name,
            asset_token_id,
            asset_category,
            quantity,
            net_amount,
        ) = row

        audit_item = audit_map.get(
            txhash
        )

        if audit_item is None:
            evidence_status = (
                "NO_PRIOR_EVIDENCE"
            )
        else:
            evidence_status = (
                audit_item[
                    "evidence_status"
                ]
            )

        is_axie_nft = (
            asset_name == "Axie"
            or asset_category
            == "AXIE_NFT"
        )

        is_inventory_asset = (
            asset_category
            in inventory_categories
            or asset_name
            in {
                "Axie Consumable Item",
                "Axie Material",
            }
        )

        if evidence_status == (
            "NO_PRIOR_EVIDENCE"
        ):
            method = (
                "NO_PRIOR_EVIDENCE"
            )

        elif is_axie_nft:
            if evidence_status == (
                "PRIOR_PURCHASE_FOUND"
            ):
                method = (
                    "EXACT_NFT_PURCHASE"
                )
            else:
                method = (
                    "NFT_INBOUND_BASIS_REVIEW"
                )

        elif is_inventory_asset:
            method = (
                "INVENTORY_POOL_REQUIRED"
            )

        else:
            method = (
                "UNRESOLVED_METHOD"
            )

        results.append(
            {
                "txhash": txhash,
                "datetime": datetime_value,
                "asset_name": asset_name,
                "asset_token_id": (
                    asset_token_id
                ),
                "asset_category": (
                    asset_category
                ),
                "quantity": quantity,
                "net_amount": net_amount,
                "evidence_status": (
                    evidence_status
                ),
                "cost_basis_method": (
                    method
                ),
            }
        )

    return results


def run_cost_basis_method_audit_test():
    results = (
        classify_missing_cost_basis_methods(
            AXIEOS_DB_PATH
        )
    )

    method_counts = {}
    category_counts = {}
    asset_counts = {}

    invalid_methods = []

    for item in results:
        method = item[
            "cost_basis_method"
        ]

        method_counts[method] = (
            method_counts.get(
                method,
                0,
            )
            + 1
        )

        category = (
            item["asset_category"]
            or "NONE"
        )

        category_counts[category] = (
            category_counts.get(
                category,
                0,
            )
            + 1
        )

        asset = (
            item["asset_name"]
            or "NONE"
        )

        asset_counts[asset] = (
            asset_counts.get(
                asset,
                0,
            )
            + 1
        )

        if (
            method
            not in COST_BASIS_METHOD_CANDIDATES
        ):
            invalid_methods.append(
                item
            )

    validation = (
        len(results) > 0
        and len(
            invalid_methods
        )
        == 0
        and sum(
            method_counts.values()
        )
        == len(results)
    )

    print(
        "\nAXIEOS COST BASIS METHOD AUDIT"
    )

    print(
        "Sales needing cost basis:",
        len(results),
    )

    print(
        "Invalid methods:",
        len(invalid_methods),
    )

    print(
        "\nMETHOD BREAKDOWN"
    )

    for method in sorted(
        method_counts
    ):
        print(
            f"{method}: "
            f"{method_counts[method]}"
        )

    print(
        "\nASSET CATEGORIES"
    )

    for category in sorted(
        category_counts
    ):
        print(
            f"{category}: "
            f"{category_counts[category]}"
        )

    print(
        "\nASSETS"
    )

    for asset in sorted(
        asset_counts
    ):
        print(
            f"{asset}: "
            f"{asset_counts[asset]}"
        )

    print(
        "\nINVENTORY COST-BASIS EXAMPLES"
    )

    inventory_records = [
        item
        for item in results
        if item[
            "cost_basis_method"
        ]
        == "INVENTORY_POOL_REQUIRED"
    ]

    for item in (
        inventory_records[:15]
    ):
        print(
            "\nTX:",
            item["txhash"],
        )

        print(
            "Date:",
            item["datetime"],
        )

        print(
            "Asset:",
            item["asset_name"],
        )

        print(
            "Token ID:",
            item[
                "asset_token_id"
            ],
        )

        print(
            "Category:",
            item[
                "asset_category"
            ],
        )

        print(
            "Quantity sold:",
            item["quantity"],
        )

        print(
            "Evidence:",
            item[
                "evidence_status"
            ],
        )

        print(
            "Method:",
            item[
                "cost_basis_method"
            ],
        )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def build_cocochoco_fifo_inventory_audit(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT
            txhash,
            datetime,
            event_type,
            classification,
            asset_token_id,
            quantity,
            direction,
            gross_amount,
            accounting_status
        FROM blockchain_accounting_records
        WHERE asset_name =
            'Axie Consumable Item'
          AND asset_token_id IN (
              '1',
              '2'
          )
        ORDER BY
            datetime,
            txhash
        """
    ).fetchall()

    connection.close()

    pools = {
        "1": [],
        "2": [],
    }

    results = []

    for row in rows:
        (
            txhash,
            datetime_value,
            event_type,
            classification,
            token_id,
            quantity_value,
            direction,
            gross_amount,
            accounting_status,
        ) = row

        token_id = str(
            token_id
        )

        quantity = Decimal(
            str(quantity_value)
        )

        if quantity <= 0:
            continue

        label = (
            COCOCHOCO_TOKEN_LABELS.get(
                token_id,
                "Unknown CocoChoco",
            )
        )

        # -----------------------------
        # Inventory acquisition
        # -----------------------------

        if direction == "IN":
            if (
                event_type
                == "ASSET_PURCHASE"
                and gross_amount
                is not None
            ):
                total_cost = Decimal(
                    str(gross_amount)
                )

                unit_cost = (
                    total_cost
                    / quantity
                )

                basis_status = (
                    "KNOWN_WETH"
                )

            else:
                total_cost = None
                unit_cost = None
                basis_status = (
                    "UNKNOWN_BASIS"
                )

            pools[token_id].append(
                {
                    "txhash": txhash,
                    "datetime": (
                        datetime_value
                    ),
                    "event_type": (
                        event_type
                    ),
                    "quantity_original": (
                        quantity
                    ),
                    "quantity_remaining": (
                        quantity
                    ),
                    "total_cost": (
                        total_cost
                    ),
                    "unit_cost": (
                        unit_cost
                    ),
                    "basis_status": (
                        basis_status
                    ),
                }
            )

            results.append(
                {
                    "txhash": txhash,
                    "datetime": (
                        datetime_value
                    ),
                    "token_id": token_id,
                    "label": label,
                    "movement": "IN",
                    "event_type": (
                        event_type
                    ),
                    "quantity": quantity,
                    "basis_status": (
                        basis_status
                    ),
                    "fifo_cost_basis": (
                        None
                    ),
                    "inventory_shortage": (
                        Decimal("0")
                    ),
                    "segments": [],
                }
            )

            continue

        # -----------------------------
        # Inventory disposition
        # -----------------------------

        if direction != "OUT":
            continue

        quantity_needed = quantity
        segments = []

        fifo_cost_basis = Decimal(
            "0"
        )

        unknown_basis_quantity = Decimal(
            "0"
        )

        for lot in pools[token_id]:
            if quantity_needed <= 0:
                break

            available = lot[
                "quantity_remaining"
            ]

            if available <= 0:
                continue

            consumed = min(
                available,
                quantity_needed,
            )

            lot[
                "quantity_remaining"
            ] -= consumed

            quantity_needed -= (
                consumed
            )

            if (
                lot["unit_cost"]
                is not None
            ):
                segment_cost = (
                    consumed
                    * lot["unit_cost"]
                )

                fifo_cost_basis += (
                    segment_cost
                )

            else:
                segment_cost = None

                unknown_basis_quantity += (
                    consumed
                )

            segments.append(
                {
                    "source_txhash": (
                        lot["txhash"]
                    ),
                    "source_event": (
                        lot["event_type"]
                    ),
                    "quantity": consumed,
                    "basis_status": (
                        lot[
                            "basis_status"
                        ]
                    ),
                    "unit_cost": (
                        lot["unit_cost"]
                    ),
                    "segment_cost": (
                        segment_cost
                    ),
                }
            )

        shortage = quantity_needed

        if shortage > 0:
            basis_status = (
                "INSUFFICIENT_HISTORY"
            )

            final_cost_basis = None

        elif (
            unknown_basis_quantity
            > 0
        ):
            basis_status = (
                "MIXED_OR_UNKNOWN_BASIS"
            )

            final_cost_basis = None

        else:
            basis_status = (
                "FULLY_KNOWN_WETH"
            )

            final_cost_basis = (
                fifo_cost_basis
            )

        results.append(
            {
                "txhash": txhash,
                "datetime": (
                    datetime_value
                ),
                "token_id": token_id,
                "label": label,
                "movement": "OUT",
                "event_type": (
                    event_type
                ),
                "quantity": quantity,
                "basis_status": (
                    basis_status
                ),
                "fifo_cost_basis": (
                    final_cost_basis
                ),
                "inventory_shortage": (
                    shortage
                ),
                "segments": segments,
            }
        )

    remaining_inventory = {}

    for token_id, lots in (
        pools.items()
    ):
        remaining_inventory[
            token_id
        ] = sum(
            (
                lot[
                    "quantity_remaining"
                ]
                for lot in lots
            ),
            Decimal("0"),
        )

    return {
        "movements": results,
        "remaining_inventory": (
            remaining_inventory
        ),
    }


def build_cocochoco_fifo_cost_basis_map(
    db_path,
):
    audit = (
        build_cocochoco_fifo_inventory_audit(
            db_path
        )
    )

    cost_basis_map = {}

    for item in audit["movements"]:
        if (
            item["event_type"]
            != "ASSET_SALE"
        ):
            continue

        if (
            item["basis_status"]
            != "FULLY_KNOWN_WETH"
        ):
            continue

        if (
            item["fifo_cost_basis"]
            is None
        ):
            continue

        cost_basis_map[
            item["txhash"]
        ] = {
            "txhash": item[
                "txhash"
            ],
            "token_id": item[
                "token_id"
            ],
            "label": item[
                "label"
            ],
            "quantity": item[
                "quantity"
            ],
            "cost_basis": item[
                "fifo_cost_basis"
            ],
        }

    return cost_basis_map


def apply_cocochoco_fifo_cost_basis(
    db_path,
):
    cost_basis_map = (
        build_cocochoco_fifo_cost_basis_map(
            db_path
        )
    )

    connection = sqlite3.connect(
        db_path
    )

    processed = 0
    skipped = 0
    realized_pl_total = Decimal(
        "0"
    )

    for txhash, basis_item in (
        cost_basis_map.items()
    ):
        row = connection.execute(
            """
            SELECT
                net_amount
            FROM blockchain_accounting_records
            WHERE txhash = ?
              AND event_type =
                  'ASSET_SALE'
            """,
            (
                txhash,
            ),
        ).fetchone()

        if (
            row is None
            or row[0] is None
        ):
            skipped += 1
            continue

        net_amount = Decimal(
            str(row[0])
        )

        cost_basis = Decimal(
            str(
                basis_item[
                    "cost_basis"
                ]
            )
        )

        realized_pl = (
            net_amount
            - cost_basis
        )

        connection.execute(
            """
            UPDATE blockchain_accounting_records
            SET
                cost_basis = ?,
                realized_pl = ?,
                accounting_status =
                    'READY',
                updated_at =
                    CURRENT_TIMESTAMP
            WHERE txhash = ?
              AND event_type =
                  'ASSET_SALE'
            """,
            (
                str(cost_basis),
                str(realized_pl),
                txhash,
            ),
        )

        realized_pl_total += (
            realized_pl
        )

        processed += 1

    connection.commit()
    connection.close()

    return {
        "candidates": len(
            cost_basis_map
        ),
        "processed": processed,
        "skipped": skipped,
        "realized_pl_total": (
            realized_pl_total
        ),
    }


def run_cocochoco_fifo_cost_basis_test():
    before_audit = (
        build_cocochoco_fifo_inventory_audit(
            AXIEOS_DB_PATH
        )
    )

    fully_known_before = [
        item
        for item
        in before_audit[
            "movements"
        ]
        if (
            item["event_type"]
            == "ASSET_SALE"
            and item[
                "basis_status"
            ]
            == "FULLY_KNOWN_WETH"
        )
    ]

    unresolved_before = [
        item
        for item
        in before_audit[
            "movements"
        ]
        if (
            item["event_type"]
            == "ASSET_SALE"
            and item[
                "basis_status"
            ]
            in {
                "MIXED_OR_UNKNOWN_BASIS",
                "INSUFFICIENT_HISTORY",
            }
        )
    ]

    result = (
        apply_cocochoco_fifo_cost_basis(
            AXIEOS_DB_PATH
        )
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    resolved_rows = (
        connection.execute(
            """
            SELECT
                txhash,
                asset_token_id,
                quantity,
                net_amount,
                cost_basis,
                realized_pl,
                accounting_status
            FROM blockchain_accounting_records
            WHERE event_type =
                'ASSET_SALE'
              AND asset_name =
                'Axie Consumable Item'
              AND asset_token_id
                  IN ('1', '2')
              AND cost_basis
                  IS NOT NULL
            """
        ).fetchall()
    )

    remaining_review = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE event_type =
                'ASSET_SALE'
              AND asset_name =
                'Axie Consumable Item'
              AND asset_token_id
                  IN ('1', '2')
              AND accounting_status =
                  'REVIEW'
              AND cost_basis
                  IS NULL
            """
        ).fetchone()[0]
    )

    regression = (
        connection.execute(
            """
            SELECT
                net_amount,
                cost_basis,
                realized_pl,
                accounting_status
            FROM blockchain_accounting_records
            WHERE txhash = ?
            """,
            (
                "0x9234deddf489357df0003aba68cf0e341247e9f19fb1819e6e815b45c8b41f0b",
            ),
        ).fetchone()
    )

    connection.close()

    regression_valid = (
        regression is not None
        and Decimal(
            str(regression[0])
        )
        == Decimal(
            "0.00018730232"
        )
        and Decimal(
            str(regression[1])
        )
        == Decimal(
            "0.000195617"
        )
        and Decimal(
            str(regression[2])
        )
        == Decimal(
            "-0.00000831468"
        )
        and regression[3]
        == "READY"
    )

    unresolved_preserved = (
        remaining_review
        == len(
            unresolved_before
        )
    )

    validation = (
        result["candidates"]
        == len(
            fully_known_before
        )
        and result["processed"]
        == len(
            fully_known_before
        )
        and result["skipped"]
        == 0
        and unresolved_preserved
        and regression_valid
    )

    print(
        "\nAXIEOS COCOCHOCO FIFO COST BASIS"
    )

    print(
        "Fully-known sales:",
        len(
            fully_known_before
        ),
    )

    print(
        "Cost-basis candidates:",
        result[
            "candidates"
        ],
    )

    print(
        "Sales updated:",
        result[
            "processed"
        ],
    )

    print(
        "Skipped:",
        result[
            "skipped"
        ],
    )

    print(
        "CocoChoco sales still REVIEW:",
        remaining_review,
    )

    print(
        "FIFO realized P/L total:",
        result[
            "realized_pl_total"
        ],
        "WETH",
    )

    print(
        "Premium CocoChoco regression:",
        (
            "PASS"
            if regression_valid
            else "FAIL"
        ),
    )

    print(
        "Unknown-basis sales preserved:",
        (
            "PASS"
            if unresolved_preserved
            else "FAIL"
        ),
    )

    print(
        "\nRESOLVED SALE EXAMPLES"
    )

    for row in resolved_rows[:10]:
        (
            txhash,
            token_id,
            quantity,
            net_amount,
            cost_basis,
            realized_pl,
            status,
        ) = row

        print(
            "\nTX:",
            txhash,
        )

        print(
            "Asset:",
            COCOCHOCO_TOKEN_LABELS.get(
                str(token_id),
                "Unknown",
            ),
        )

        print(
            "Quantity:",
            quantity,
        )

        print(
            "Net proceeds:",
            net_amount,
        )

        print(
            "FIFO cost basis:",
            cost_basis,
        )

        print(
            "Realized P/L:",
            realized_pl,
        )

        print(
            "Status:",
            status,
        )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def audit_unresolved_axie_sale_origins(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    sales = connection.execute(
        """
        SELECT
            txhash,
            datetime,
            asset_token_id,
            quantity,
            gross_amount,
            net_amount
        FROM blockchain_accounting_records
        WHERE event_type = 'ASSET_SALE'
          AND asset_name = 'Axie'
          AND accounting_status = 'REVIEW'
          AND cost_basis IS NULL
        ORDER BY datetime, txhash
        """
    ).fetchall()

    wallet = normalize_address(
        RONIN_WALLET_ADDRESS
    )

    results = []

    for sale in sales:
        (
            sale_txhash,
            sale_datetime,
            token_id,
            quantity,
            gross_amount,
            net_amount,
        ) = sale

        raw_rows = connection.execute(
            """
            SELECT
                tx_hash,
                timestamp,
                from_address,
                to_address,
                token_id,
                amount_raw
            FROM ronin_token_transfers_raw
            WHERE token_name = 'Axie'
              AND token_id = ?
            ORDER BY timestamp, tx_hash
            """,
            (
                str(token_id),
            ),
        ).fetchall()

        raw_history = []

        for raw_row in raw_rows:
            (
                txhash,
                timestamp,
                from_address,
                to_address,
                raw_token_id,
                amount_raw,
            ) = raw_row

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

            if (
                to_normalized == wallet
                and from_normalized != wallet
            ):
                direction = "IN"
                counterparty_address = (
                    from_normalized
                )

            elif (
                from_normalized == wallet
                and to_normalized != wallet
            ):
                direction = "OUT"
                counterparty_address = (
                    to_normalized
                )

            else:
                direction = "OTHER"
                counterparty_address = None

            if counterparty_address is not None:
                registry = (
                    get_wallet_registry_entry(
                        db_path,
                        counterparty_address,
                    )
                )

                ownership_type = (
                    registry[
                        "ownership_type"
                    ]
                )

                wallet_role = (
                    registry[
                        "wallet_role"
                    ]
                )

            else:
                ownership_type = None
                wallet_role = None

            raw_history.append(
                {
                    "txhash": txhash,
                    "timestamp": timestamp,
                    "direction": direction,
                    "from_address": (
                        from_normalized
                    ),
                    "to_address": (
                        to_normalized
                    ),
                    "counterparty": (
                        counterparty_address
                    ),
                    "ownership_type": (
                        ownership_type
                    ),
                    "wallet_role": (
                        wallet_role
                    ),
                }
            )

        prior_accounting = (
            connection.execute(
                """
                SELECT
                    txhash,
                    datetime,
                    event_type,
                    classification,
                    gross_amount,
                    accounting_status
                FROM blockchain_accounting_records
                WHERE asset_token_id = ?
                  AND datetime < ?
                  AND txhash != ?
                ORDER BY datetime DESC
                """,
                (
                    str(token_id),
                    sale_datetime,
                    sale_txhash,
                ),
            ).fetchall()
        )

        inbound_rows = [
            item
            for item in raw_history
            if (
                item["direction"]
                == "IN"
                and item["txhash"]
                != sale_txhash
            )
        ]

        owned_inbound = [
            item
            for item in inbound_rows
            if item[
                "ownership_type"
            ]
            == "USER_OWNED"
        ]

        if owned_inbound:
            origin_status = (
                "OWNED_WALLET_INBOUND"
            )

        elif inbound_rows:
            origin_status = (
                "EXTERNAL_OR_UNKNOWN_INBOUND"
            )

        elif prior_accounting:
            origin_status = (
                "ACCOUNTING_EVIDENCE_ONLY"
            )

        else:
            origin_status = (
                "NO_ORIGIN_EVIDENCE"
            )

        results.append(
            {
                "sale_txhash": (
                    sale_txhash
                ),
                "sale_datetime": (
                    sale_datetime
                ),
                "token_id": str(
                    token_id
                ),
                "quantity": quantity,
                "gross_amount": (
                    gross_amount
                ),
                "net_amount": (
                    net_amount
                ),
                "origin_status": (
                    origin_status
                ),
                "raw_history": (
                    raw_history
                ),
                "prior_accounting": (
                    prior_accounting
                ),
            }
        )

    connection.close()

    return results


def run_unresolved_axie_origin_audit_test():
    results = (
        audit_unresolved_axie_sale_origins(
            AXIEOS_DB_PATH
        )
    )

    status_counts = {}

    for item in results:
        status = item[
            "origin_status"
        ]

        status_counts[status] = (
            status_counts.get(
                status,
                0,
            )
            + 1
        )

    validation = (
        len(results) > 0
        and sum(
            status_counts.values()
        )
        == len(results)
    )

    print(
        "\nAXIEOS UNRESOLVED AXIE ORIGIN AUDIT"
    )

    print(
        "Axie sales needing basis:",
        len(results),
    )

    print(
        "\nORIGIN BREAKDOWN"
    )

    for status in sorted(
        status_counts
    ):
        print(
            f"{status}: "
            f"{status_counts[status]}"
        )

    print(
        "\nAXIE SALE ORIGINS"
    )

    for item in results:
        print(
            "\n------------------------------"
        )

        print(
            "Axie ID:",
            item["token_id"],
        )

        print(
            "Sale TX:",
            item[
                "sale_txhash"
            ],
        )

        print(
            "Sale date:",
            item[
                "sale_datetime"
            ],
        )

        print(
            "Net proceeds:",
            item[
                "net_amount"
            ],
        )

        print(
            "Origin status:",
            item[
                "origin_status"
            ],
        )

        print(
            "Raw token history:",
            len(
                item[
                    "raw_history"
                ]
            ),
        )

        for history in item[
            "raw_history"
        ]:
            print(
                " ",
                history[
                    "timestamp"
                ],
                history[
                    "direction"
                ],
                "Counterparty:",
                history[
                    "counterparty"
                ],
                "Ownership:",
                history[
                    "ownership_type"
                ],
                "Role:",
                history[
                    "wallet_role"
                ],
                "TX:",
                history[
                    "txhash"
                ],
            )

        print(
            "Prior accounting records:",
            len(
                item[
                    "prior_accounting"
                ]
            ),
        )

        for prior in item[
            "prior_accounting"
        ][:5]:
            print(
                " ",
                prior[1],
                prior[2],
                prior[3],
                "Gross:",
                prior[4],
                "Status:",
                prior[5],
                "TX:",
                prior[0],
            )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


COST_BASIS_REVIEW_REASON_CODES = {
    "COCOCHOCO_MIXED_OR_UNKNOWN_BASIS",
    "COCOCHOCO_INSUFFICIENT_HISTORY",
    "AXIE_UNKNOWN_INBOUND_BASIS",
    "AXIE_NO_ORIGIN_EVIDENCE",
}


def build_remaining_cost_basis_review_queue(
    db_path,
):
    queue = []

    # ---------------------------------
    # CocoChoco unresolved sales
    # ---------------------------------

    fifo_result = (
        build_cocochoco_fifo_inventory_audit(
            db_path
        )
    )

    for item in fifo_result[
        "movements"
    ]:
        if (
            item["event_type"]
            != "ASSET_SALE"
        ):
            continue

        if (
            item["basis_status"]
            == "MIXED_OR_UNKNOWN_BASIS"
        ):
            reason_code = (
                "COCOCHOCO_MIXED_OR_UNKNOWN_BASIS"
            )

            reason = (
                "FIFO inventory includes one "
                "or more units whose historical "
                "WETH acquisition basis is unknown."
            )

        elif (
            item["basis_status"]
            == "INSUFFICIENT_HISTORY"
        ):
            reason_code = (
                "COCOCHOCO_INSUFFICIENT_HISTORY"
            )

            reason = (
                "Available transaction history "
                "does not contain enough prior "
                "inventory to support this sale."
            )

        else:
            continue

        queue.append(
            {
                "txhash": item["txhash"],
                "asset_type": "COCOCHOCO",
                "asset_name": item["label"],
                "token_id": item["token_id"],
                "quantity": str(
                    item["quantity"]
                ),
                "reason_code": (
                    reason_code
                ),
                "reason": reason,
            }
        )

    # ---------------------------------
    # Axie unresolved sales
    # ---------------------------------

    axie_results = (
        audit_unresolved_axie_sale_origins(
            db_path
        )
    )

    for item in axie_results:
        if (
            item["origin_status"]
            == "EXTERNAL_OR_UNKNOWN_INBOUND"
        ):
            reason_code = (
                "AXIE_UNKNOWN_INBOUND_BASIS"
            )

            reason = (
                "The Axie entered from an "
                "unverified external or unknown "
                "wallet, so acquisition cost "
                "cannot yet be proven."
            )

        elif (
            item["origin_status"]
            == "NO_ORIGIN_EVIDENCE"
        ):
            reason_code = (
                "AXIE_NO_ORIGIN_EVIDENCE"
            )

            reason = (
                "No earlier acquisition or inbound "
                "record is available in the current "
                "AxieOS history."
            )

        else:
            continue

        queue.append(
            {
                "txhash": item[
                    "sale_txhash"
                ],
                "asset_type": "AXIE",
                "asset_name": "Axie",
                "token_id": item[
                    "token_id"
                ],
                "quantity": str(
                    item["quantity"]
                ),
                "reason_code": (
                    reason_code
                ),
                "reason": reason,
            }
        )

    queue.sort(
        key=lambda item: (
            item["asset_type"],
            item["token_id"],
            item["txhash"],
        )
    )

    return queue


def run_final_cost_basis_review_test():
    queue = (
        build_remaining_cost_basis_review_queue(
            AXIEOS_DB_PATH
        )
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    unresolved_sales_db = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE event_type = 'ASSET_SALE'
              AND accounting_status = 'REVIEW'
              AND cost_basis IS NULL
            """
        ).fetchone()[0]
    )

    resolved_cocochoco = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE event_type = 'ASSET_SALE'
              AND asset_name =
                  'Axie Consumable Item'
              AND asset_token_id
                  IN ('1', '2')
              AND accounting_status = 'READY'
              AND cost_basis IS NOT NULL
            """
        ).fetchone()[0]
    )

    connection.close()

    reason_counts = {}
    asset_type_counts = {}

    invalid_reason_codes = []

    for item in queue:
        reason_code = item[
            "reason_code"
        ]

        reason_counts[
            reason_code
        ] = (
            reason_counts.get(
                reason_code,
                0,
            )
            + 1
        )

        asset_type = item[
            "asset_type"
        ]

        asset_type_counts[
            asset_type
        ] = (
            asset_type_counts.get(
                asset_type,
                0,
            )
            + 1
        )

        if (
            reason_code
            not in COST_BASIS_REVIEW_REASON_CODES
        ):
            invalid_reason_codes.append(
                item
            )

    unique_txhashes = {
        item["txhash"]
        for item in queue
    }

    unique_valid = (
        len(unique_txhashes)
        == len(queue)
    )

    queue_count_valid = (
        len(queue)
        == unresolved_sales_db
    )

    validation = (
        queue_count_valid
        and unique_valid
        and len(
            invalid_reason_codes
        )
        == 0
        and resolved_cocochoco
        >= 18
    )

    print(
        "\nAXIEOS FINAL COST BASIS REVIEW"
    )

    print(
        "Unresolved sales in database:",
        unresolved_sales_db,
    )

    print(
        "Cost-basis review queue:",
        len(queue),
    )

    print(
        "Resolved CocoChoco sales:",
        resolved_cocochoco,
    )

    print(
        "Unique review txhashes:",
        len(unique_txhashes),
    )

    print(
        "Invalid reason codes:",
        len(
            invalid_reason_codes
        ),
    )

    print(
        "\nASSET TYPES"
    )

    for asset_type in sorted(
        asset_type_counts
    ):
        print(
            f"{asset_type}: "
            f"{asset_type_counts[asset_type]}"
        )

    print(
        "\nREASON BREAKDOWN"
    )

    for reason_code in sorted(
        reason_counts
    ):
        print(
            f"{reason_code}: "
            f"{reason_counts[reason_code]}"
        )

    print(
        "\nAXIE REVIEW ITEMS"
    )

    axie_items = [
        item
        for item in queue
        if item["asset_type"]
        == "AXIE"
    ]

    for item in axie_items:
        print(
            "\nAxie ID:",
            item["token_id"],
        )

        print(
            "Sale TX:",
            item["txhash"],
        )

        print(
            "Reason:",
            item["reason_code"],
        )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def audit_token_swap_accounting(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    swaps = connection.execute(
        """
        SELECT
            txhash,
            datetime,
            asset_name,
            quantity,
            payment_asset,
            gross_amount,
            net_amount,
            cost_basis,
            realized_pl,
            accounting_status
        FROM blockchain_accounting_records
        WHERE event_type = 'TOKEN_SWAP'
        ORDER BY datetime, txhash
        """
    ).fetchall()

    results = []

    for swap in swaps:
        (
            txhash,
            datetime_value,
            asset_name,
            quantity,
            payment_asset,
            gross_amount,
            net_amount,
            cost_basis,
            realized_pl,
            accounting_status,
        ) = swap

        prior_rows = connection.execute(
            """
            SELECT
                txhash,
                datetime,
                event_type,
                classification,
                quantity,
                direction,
                gross_amount,
                cost_basis,
                accounting_status
            FROM blockchain_accounting_records
            WHERE asset_name = ?
              AND datetime < ?
              AND txhash != ?
            ORDER BY datetime, txhash
            """,
            (
                asset_name,
                datetime_value,
                txhash,
            ),
        ).fetchall()

        inbound_rows = [
            row
            for row in prior_rows
            if row[5] == "IN"
        ]

        purchased_rows = [
            row
            for row in inbound_rows
            if (
                row[2]
                == "ASSET_PURCHASE"
                and row[6]
                is not None
            )
        ]

        basis_rows = [
            row
            for row in inbound_rows
            if row[7] is not None
        ]

        reward_rows = [
            row
            for row in inbound_rows
            if row[2] in {
                "MINT_OR_CLAIM",
                "STAKING_OR_REWARD",
            }
        ]

        transfer_rows = [
            row
            for row in inbound_rows
            if row[2]
            == "TRANSFER_IN"
        ]

        if basis_rows:
            basis_status = (
                "PRIOR_BASIS_RECORDS_EXIST"
            )

        elif purchased_rows:
            basis_status = (
                "PRIOR_PURCHASE_VALUE_EXISTS"
            )

        elif reward_rows:
            basis_status = (
                "REWARD_OR_CLAIM_BASIS_UNRESOLVED"
            )

        elif transfer_rows:
            basis_status = (
                "TRANSFER_BASIS_UNRESOLVED"
            )

        else:
            basis_status = (
                "NO_PRIOR_BASIS_EVIDENCE"
            )

        results.append(
            {
                "txhash": txhash,
                "datetime": datetime_value,
                "asset_out": asset_name,
                "quantity_out": quantity,
                "asset_in": payment_asset,
                "quantity_in": gross_amount,
                "current_cost_basis": (
                    cost_basis
                ),
                "current_realized_pl": (
                    realized_pl
                ),
                "current_status": (
                    accounting_status
                ),
                "basis_status": (
                    basis_status
                ),
                "prior_inbound_count": len(
                    inbound_rows
                ),
                "prior_reward_count": len(
                    reward_rows
                ),
                "prior_transfer_count": len(
                    transfer_rows
                ),
                "prior_purchase_count": len(
                    purchased_rows
                ),
                "prior_basis_count": len(
                    basis_rows
                ),
                "prior_examples": (
                    inbound_rows[-10:]
                ),
            }
        )

    connection.close()

    return results


def run_token_swap_accounting_audit_test():
    results = (
        audit_token_swap_accounting(
            AXIEOS_DB_PATH
        )
    )

    status_counts = {}

    for item in results:
        status = item[
            "basis_status"
        ]

        status_counts[status] = (
            status_counts.get(
                status,
                0,
            )
            + 1
        )

    unresolved = [
        item
        for item in results
        if item[
            "current_cost_basis"
        ]
        is None
    ]

    review_preserved = all(
        item[
            "current_status"
        ]
        == "REVIEW"
        for item in unresolved
    )

    validation = (
        len(results) > 0
        and review_preserved
        and sum(
            status_counts.values()
        )
        == len(results)
    )

    print(
        "\nAXIEOS TOKEN SWAP ACCOUNTING AUDIT"
    )

    print(
        "Token swaps:",
        len(results),
    )

    print(
        "Swaps without cost basis:",
        len(unresolved),
    )

    print(
        "\nBASIS STATUS"
    )

    for status in sorted(
        status_counts
    ):
        print(
            f"{status}: "
            f"{status_counts[status]}"
        )

    print(
        "\nSWAP DETAILS"
    )

    for item in results:
        print(
            "\n------------------------------"
        )

        print(
            "TX:",
            item["txhash"],
        )

        print(
            "Date:",
            item["datetime"],
        )

        print(
            "Asset OUT:",
            item["asset_out"],
        )

        print(
            "Quantity OUT:",
            item["quantity_out"],
        )

        print(
            "Asset IN:",
            item["asset_in"],
        )

        print(
            "Quantity IN:",
            item["quantity_in"],
        )

        print(
            "Basis status:",
            item["basis_status"],
        )

        print(
            "Prior inbound records:",
            item[
                "prior_inbound_count"
            ],
        )

        print(
            "Prior reward/claim:",
            item[
                "prior_reward_count"
            ],
        )

        print(
            "Prior transfers:",
            item[
                "prior_transfer_count"
            ],
        )

        print(
            "Prior purchases:",
            item[
                "prior_purchase_count"
            ],
        )

        print(
            "Prior records with basis:",
            item[
                "prior_basis_count"
            ],
        )

        print(
            "Accounting status:",
            item[
                "current_status"
            ],
        )

        print(
            "PRIOR INBOUND EXAMPLES"
        )

        for prior in item[
            "prior_examples"
        ]:
            print(
                " ",
                prior[1],
                prior[2],
                prior[3],
                "Qty:",
                prior[4],
                "Gross:",
                prior[6],
                "Basis:",
                prior[7],
                "TX:",
                prior[0],
            )

    print(
        "\nReview preservation:",
        (
            "PASS"
            if review_preserved
            else "FAIL"
        ),
    )

    print(
        "Validation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def build_accounting_summary(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    total_records = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            """
        ).fetchone()[0]
    )

    status_rows = (
        connection.execute(
            """
            SELECT
                accounting_status,
                COUNT(*)
            FROM blockchain_accounting_records
            GROUP BY accounting_status
            ORDER BY accounting_status
            """
        ).fetchall()
    )

    event_rows = (
        connection.execute(
            """
            SELECT
                event_type,
                COUNT(*)
            FROM blockchain_accounting_records
            GROUP BY event_type
            ORDER BY event_type
            """
        ).fetchall()
    )

    event_status_rows = (
        connection.execute(
            """
            SELECT
                event_type,
                accounting_status,
                COUNT(*)
            FROM blockchain_accounting_records
            GROUP BY
                event_type,
                accounting_status
            ORDER BY
                event_type,
                accounting_status
            """
        ).fetchall()
    )

    version_rows = (
        connection.execute(
            """
            SELECT
                accounting_version,
                COUNT(*)
            FROM blockchain_accounting_records
            GROUP BY accounting_version
            ORDER BY accounting_version
            """
        ).fetchall()
    )

    realized_rows = (
        connection.execute(
            """
            SELECT
                event_type,
                COUNT(*),
                SUM(realized_pl)
            FROM blockchain_accounting_records
            WHERE realized_pl IS NOT NULL
            GROUP BY event_type
            ORDER BY event_type
            """
        ).fetchall()
    )

    cost_basis_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE cost_basis IS NOT NULL
            """
        ).fetchone()[0]
    )

    realized_pl_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE realized_pl IS NOT NULL
            """
        ).fetchone()[0]
    )

    review_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE accounting_status = 'REVIEW'
            """
        ).fetchone()[0]
    )

    connection.close()

    return {
        "total_records": total_records,
        "status_rows": status_rows,
        "event_rows": event_rows,
        "event_status_rows": (
            event_status_rows
        ),
        "version_rows": version_rows,
        "realized_rows": realized_rows,
        "cost_basis_count": (
            cost_basis_count
        ),
        "realized_pl_count": (
            realized_pl_count
        ),
        "review_count": review_count,
    }



def run_accounting_summary_test():
    summary = (
        build_accounting_summary(
            AXIEOS_DB_PATH
        )
    )

    status_total = sum(
        row[1]
        for row in summary[
            "status_rows"
        ]
    )

    event_total = sum(
        row[1]
        for row in summary[
            "event_rows"
        ]
    )

    event_status_total = sum(
        row[2]
        for row in summary[
            "event_status_rows"
        ]
    )

    version_total = sum(
        row[1]
        for row in summary[
            "version_rows"
        ]
    )

    validation = (
        status_total
        == summary["total_records"]
        and event_total
        == summary["total_records"]
        and event_status_total
        == summary["total_records"]
        and version_total
        == summary["total_records"]
    )

    print(
        "\nAXIEOS ACCOUNTING SUMMARY"
    )

    print(
        "Total accounting records:",
        summary["total_records"],
    )

    print(
        "Records with cost basis:",
        summary[
            "cost_basis_count"
        ],
    )

    print(
        "Records with realized P/L:",
        summary[
            "realized_pl_count"
        ],
    )

    print(
        "Records still REVIEW:",
        summary[
            "review_count"
        ],
    )

    print(
        "\nSTATUS BREAKDOWN"
    )

    for status, count in (
        summary["status_rows"]
    ):
        print(
            f"{status}: {count}"
        )

    print(
        "\nEVENT BREAKDOWN"
    )

    for event_type, count in (
        summary["event_rows"]
    ):
        print(
            f"{event_type}: {count}"
        )

    print(
        "\nEVENT / STATUS MATRIX"
    )

    for (
        event_type,
        status,
        count,
    ) in summary[
        "event_status_rows"
    ]:
        print(
            f"{event_type} / "
            f"{status}: "
            f"{count}"
        )

    print(
        "\nACCOUNTING VERSIONS"
    )

    for version, count in (
        summary["version_rows"]
    ):
        print(
            f"{version}: {count}"
        )

    print(
        "\nREALIZED P/L RECORDS"
    )

    for (
        event_type,
        count,
        realized_total,
    ) in summary[
        "realized_rows"
    ]:
        print(
            f"{event_type}: "
            f"{count} records, "
            f"{realized_total} WETH"
        )

    print(
        "\nRECONCILIATION"
    )

    print(
        "Status total:",
        status_total,
    )

    print(
        "Event total:",
        event_total,
    )

    print(
        "Event/status total:",
        event_status_total,
    )

    print(
        "Version total:",
        version_total,
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def build_realized_pl_marketplace_report(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    purchase_rows = connection.execute(
        """
        SELECT
            txhash,
            datetime,
            asset_name,
            asset_token_id,
            quantity,
            gross_amount,
            accounting_status
        FROM blockchain_accounting_records
        WHERE event_type = 'ASSET_PURCHASE'
        ORDER BY datetime, txhash
        """
    ).fetchall()

    sale_rows = connection.execute(
        """
        SELECT
            txhash,
            datetime,
            asset_name,
            asset_token_id,
            quantity,
            gross_amount,
            marketplace_fee,
            net_amount,
            cost_basis,
            realized_pl,
            accounting_status
        FROM blockchain_accounting_records
        WHERE event_type = 'ASSET_SALE'
        ORDER BY datetime, txhash
        """
    ).fetchall()

    connection.close()

    realized_sales = [
        row
        for row in sale_rows
        if (
            row[10] == "READY"
            and row[8] is not None
            and row[9] is not None
        )
    ]

    unresolved_sales = [
        row
        for row in sale_rows
        if row[10] == "REVIEW"
    ]

    def decimal_sum(
        rows,
        index,
    ):
        total = Decimal("0")

        for row in rows:
            if row[index] is None:
                continue

            total += Decimal(
                str(row[index])
            )

        return total

    gross_sales = decimal_sum(
        realized_sales,
        5,
    )

    marketplace_fees = decimal_sum(
        realized_sales,
        6,
    )

    net_sales = decimal_sum(
        realized_sales,
        7,
    )

    cost_basis = decimal_sum(
        realized_sales,
        8,
    )

    realized_pl = decimal_sum(
        realized_sales,
        9,
    )

    purchase_total = decimal_sum(
        purchase_rows,
        5,
    )

    asset_summary = {}

    for row in realized_sales:
        asset_name = (
            row[2]
            or "UNKNOWN"
        )

        if asset_name == (
            "Axie Consumable Item"
        ):
            token_id = str(
                row[3]
            )

            asset_name = (
                COCOCHOCO_TOKEN_LABELS.get(
                    token_id,
                    asset_name,
                )
            )

        summary = asset_summary.setdefault(
            asset_name,
            {
                "sales": 0,
                "quantity": Decimal("0"),
                "gross": Decimal("0"),
                "fees": Decimal("0"),
                "net": Decimal("0"),
                "cost_basis": Decimal("0"),
                "realized_pl": Decimal("0"),
            },
        )

        summary["sales"] += 1

        if row[4] is not None:
            summary[
                "quantity"
            ] += Decimal(
                str(row[4])
            )

        if row[5] is not None:
            summary[
                "gross"
            ] += Decimal(
                str(row[5])
            )

        if row[6] is not None:
            summary[
                "fees"
            ] += Decimal(
                str(row[6])
            )

        if row[7] is not None:
            summary[
                "net"
            ] += Decimal(
                str(row[7])
            )

        if row[8] is not None:
            summary[
                "cost_basis"
            ] += Decimal(
                str(row[8])
            )

        if row[9] is not None:
            summary[
                "realized_pl"
            ] += Decimal(
                str(row[9])
            )

    return {
        "purchases": purchase_rows,
        "sales": sale_rows,
        "realized_sales": realized_sales,
        "unresolved_sales": unresolved_sales,
        "purchase_total": purchase_total,
        "gross_sales": gross_sales,
        "marketplace_fees": marketplace_fees,
        "net_sales": net_sales,
        "cost_basis": cost_basis,
        "realized_pl": realized_pl,
        "asset_summary": asset_summary,
    }


def run_realized_pl_marketplace_report_test():
    report = (
        build_realized_pl_marketplace_report(
            AXIEOS_DB_PATH
        )
    )

    realized_sales = report[
        "realized_sales"
    ]

    unresolved_sales = report[
        "unresolved_sales"
    ]

    gross_sales = report[
        "gross_sales"
    ]

    marketplace_fees = report[
        "marketplace_fees"
    ]

    net_sales = report[
        "net_sales"
    ]

    cost_basis = report[
        "cost_basis"
    ]

    realized_pl = report[
        "realized_pl"
    ]

    net_reconciliation = (
        gross_sales
        - marketplace_fees
    )

    pl_reconciliation = (
        net_sales
        - cost_basis
    )

    net_valid = (
        net_reconciliation
        == net_sales
    )

    pl_valid = (
        pl_reconciliation
        == realized_pl
    )

    sale_count_valid = (
        len(realized_sales)
        + len(unresolved_sales)
        == len(
            report["sales"]
        )
    )

    validation = (
        len(
            report["purchases"]
        )
        > 0
        and len(
            report["sales"]
        )
        > 0
        and sale_count_valid
        and net_valid
        and pl_valid
    )

    print(
        "\nAXIEOS REALIZED P/L "
        "AND MARKETPLACE REPORT"
    )

    print(
        "Marketplace purchases:",
        len(
            report["purchases"]
        ),
    )

    print(
        "Marketplace sales:",
        len(
            report["sales"]
        ),
    )

    print(
        "Sales with realized P/L:",
        len(realized_sales),
    )

    print(
        "Sales still unresolved:",
        len(unresolved_sales),
    )

    print(
        "\nPURCHASE ECONOMICS"
    )

    print(
        "Total recorded purchase cost:",
        report[
            "purchase_total"
        ],
        "WETH",
    )

    print(
        "\nREALIZED SALE ECONOMICS"
    )

    print(
        "Gross sales:",
        gross_sales,
        "WETH",
    )

    print(
        "Marketplace fees:",
        marketplace_fees,
        "WETH",
    )

    print(
        "Net proceeds:",
        net_sales,
        "WETH",
    )

    print(
        "Cost basis:",
        cost_basis,
        "WETH",
    )

    print(
        "Realized P/L:",
        realized_pl,
        "WETH",
    )

    if cost_basis != 0:
        realized_roi = (
            realized_pl
            / cost_basis
            * Decimal("100")
        )

        print(
            "Realized ROI:",
            realized_roi,
            "%",
        )

    print(
        "\nREALIZED P/L BY ASSET"
    )

    for asset_name in sorted(
        report[
            "asset_summary"
        ]
    ):
        summary = report[
            "asset_summary"
        ][asset_name]

        print(
            "\nAsset:",
            asset_name,
        )

        print(
            "Sales:",
            summary["sales"],
        )

        print(
            "Quantity:",
            summary["quantity"],
        )

        print(
            "Gross:",
            summary["gross"],
            "WETH",
        )

        print(
            "Fees:",
            summary["fees"],
            "WETH",
        )

        print(
            "Net:",
            summary["net"],
            "WETH",
        )

        print(
            "Cost basis:",
            summary[
                "cost_basis"
            ],
            "WETH",
        )

        print(
            "Realized P/L:",
            summary[
                "realized_pl"
            ],
            "WETH",
        )

        if (
            summary[
                "cost_basis"
            ]
            != 0
        ):
            roi = (
                summary[
                    "realized_pl"
                ]
                / summary[
                    "cost_basis"
                ]
                * Decimal("100")
            )

            print(
                "ROI:",
                roi,
                "%",
            )

    print(
        "\nRECONCILIATION"
    )

    print(
        "Gross - fees = net:",
        (
            "PASS"
            if net_valid
            else "FAIL"
        ),
    )

    print(
        "Net - basis = P/L:",
        (
            "PASS"
            if pl_valid
            else "FAIL"
        ),
    )

    print(
        "Sale count:",
        (
            "PASS"
            if sale_count_valid
            else "FAIL"
        ),
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


RONIN_PIPELINE_VERSION_V07 = "0.7"



def validate_v07_accounting_pipeline(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    total_records = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            """
        ).fetchone()[0]
    )

    review_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE accounting_status = 'REVIEW'
            """
        ).fetchone()[0]
    )

    sale_review_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE event_type = 'ASSET_SALE'
              AND accounting_status = 'REVIEW'
              AND cost_basis IS NULL
            """
        ).fetchone()[0]
    )

    realized_sale_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE event_type = 'ASSET_SALE'
              AND accounting_status = 'READY'
              AND cost_basis IS NOT NULL
              AND realized_pl IS NOT NULL
            """
        ).fetchone()[0]
    )

    ready_sales_missing_basis = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE event_type = 'ASSET_SALE'
              AND accounting_status = 'READY'
              AND (
                  cost_basis IS NULL
                  OR realized_pl IS NULL
              )
            """
        ).fetchone()[0]
    )

    review_sales_with_basis = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE event_type = 'ASSET_SALE'
              AND accounting_status = 'REVIEW'
              AND (
                  cost_basis IS NOT NULL
                  OR realized_pl IS NOT NULL
              )
            """
        ).fetchone()[0]
    )

    token_swap_total = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE event_type = 'TOKEN_SWAP'
            """
        ).fetchone()[0]
    )

    token_swap_review = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE event_type = 'TOKEN_SWAP'
              AND accounting_status = 'REVIEW'
            """
        ).fetchone()[0]
    )

    cocochoco_resolved = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM blockchain_accounting_records
            WHERE event_type = 'ASSET_SALE'
              AND asset_name =
                  'Axie Consumable Item'
              AND asset_token_id
                  IN ('1', '2')
              AND accounting_status = 'READY'
              AND cost_basis IS NOT NULL
              AND realized_pl IS NOT NULL
            """
        ).fetchone()[0]
    )

    version_rows = (
        connection.execute(
            """
            SELECT
                accounting_version,
                COUNT(*)
            FROM blockchain_accounting_records
            GROUP BY accounting_version
            ORDER BY accounting_version
            """
        ).fetchall()
    )

    connection.close()

    review_queue = (
        load_accounting_review_queue(
            db_path
        )
    )

    cost_basis_queue = (
        build_remaining_cost_basis_review_queue(
            db_path
        )
    )

    report = (
        build_realized_pl_marketplace_report(
            db_path
        )
    )

    review_queue_valid = (
        len(review_queue)
        == review_count
    )

    cost_basis_queue_valid = (
        len(cost_basis_queue)
        == sale_review_count
    )

    ready_sale_integrity = (
        ready_sales_missing_basis
        == 0
    )

    review_sale_integrity = (
        review_sales_with_basis
        == 0
    )

    swap_integrity = (
        token_swap_total
        == token_swap_review
    )

    net_reconciliation = (
        report["gross_sales"]
        - report["marketplace_fees"]
        == report["net_sales"]
    )

    pl_reconciliation = (
        report["net_sales"]
        - report["cost_basis"]
        == report["realized_pl"]
    )

    realized_count_valid = (
        realized_sale_count
        == len(
            report["realized_sales"]
        )
    )

    validation = (
        total_records > 0
        and review_queue_valid
        and cost_basis_queue_valid
        and ready_sale_integrity
        and review_sale_integrity
        and swap_integrity
        and net_reconciliation
        and pl_reconciliation
        and realized_count_valid
    )

    return {
        "total_records": total_records,
        "review_count": review_count,
        "sale_review_count": (
            sale_review_count
        ),
        "realized_sale_count": (
            realized_sale_count
        ),
        "cocochoco_resolved": (
            cocochoco_resolved
        ),
        "token_swap_total": (
            token_swap_total
        ),
        "version_rows": version_rows,
        "review_queue_valid": (
            review_queue_valid
        ),
        "cost_basis_queue_valid": (
            cost_basis_queue_valid
        ),
        "ready_sale_integrity": (
            ready_sale_integrity
        ),
        "review_sale_integrity": (
            review_sale_integrity
        ),
        "swap_integrity": (
            swap_integrity
        ),
        "net_reconciliation": (
            net_reconciliation
        ),
        "pl_reconciliation": (
            pl_reconciliation
        ),
        "realized_count_valid": (
            realized_count_valid
        ),
        "realized_pl": report[
            "realized_pl"
        ],
        "validation": validation,
    }


def run_ronin_sync_v07():
    print(
        "\n================================"
    )

    print(
        "AXIEOS RONIN PIPELINE V0.7"
    )

    print(
        "================================"
    )

    # Run the complete V0.6 ingestion,
    # intelligence, economics, and
    # accounting pipeline first.
    run_ronin_sync_v06()

    # V0.7 accounting-review treatment.
    fifo_result = (
        apply_cocochoco_fifo_cost_basis(
            AXIEOS_DB_PATH
        )
    )

    validation = (
        validate_v07_accounting_pipeline(
            AXIEOS_DB_PATH
        )
    )

    print(
        "\nAXIEOS RONIN V0.7 VALIDATION"
    )

    print(
        "Pipeline version:",
        RONIN_PIPELINE_VERSION_V07,
    )

    print(
        "Total accounting records:",
        validation[
            "total_records"
        ],
    )

    print(
        "Accounting REVIEW records:",
        validation[
            "review_count"
        ],
    )

    print(
        "Unresolved sale basis:",
        validation[
            "sale_review_count"
        ],
    )

    print(
        "Realized sales:",
        validation[
            "realized_sale_count"
        ],
    )

    print(
        "Resolved CocoChoco sales:",
        validation[
            "cocochoco_resolved"
        ],
    )

    print(
        "CocoChoco FIFO candidates:",
        fifo_result[
            "candidates"
        ],
    )

    print(
        "CocoChoco FIFO applied:",
        fifo_result[
            "processed"
        ],
    )

    print(
        "Token swaps:",
        validation[
            "token_swap_total"
        ],
    )

    print(
        "Realized P/L:",
        validation[
            "realized_pl"
        ],
        "WETH",
    )

    print(
        "\nACCOUNTING VERSIONS"
    )

    for version, count in (
        validation[
            "version_rows"
        ]
    ):
        print(
            f"{version}: {count}"
        )

    print(
        "\nV0.7 INTEGRITY CHECKS"
    )

    print(
        "Review queue reconciliation:",
        (
            "PASS"
            if validation[
                "review_queue_valid"
            ]
            else "FAIL"
        ),
    )

    print(
        "Cost-basis queue reconciliation:",
        (
            "PASS"
            if validation[
                "cost_basis_queue_valid"
            ]
            else "FAIL"
        ),
    )

    print(
        "READY sale basis integrity:",
        (
            "PASS"
            if validation[
                "ready_sale_integrity"
            ]
            else "FAIL"
        ),
    )

    print(
        "REVIEW sale preservation:",
        (
            "PASS"
            if validation[
                "review_sale_integrity"
            ]
            else "FAIL"
        ),
    )

    print(
        "Swap review preservation:",
        (
            "PASS"
            if validation[
                "swap_integrity"
            ]
            else "FAIL"
        ),
    )

    print(
        "Marketplace net reconciliation:",
        (
            "PASS"
            if validation[
                "net_reconciliation"
            ]
            else "FAIL"
        ),
    )

    print(
        "Realized P/L reconciliation:",
        (
            "PASS"
            if validation[
                "pl_reconciliation"
            ]
            else "FAIL"
        ),
    )

    print(
        "Realized sale count:",
        (
            "PASS"
            if validation[
                "realized_count_valid"
            ]
            else "FAIL"
        ),
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation[
                "validation"
            ]
            else "FAIL"
        ),
    )




def run_cocochoco_fifo_inventory_audit_test():
    result = (
        build_cocochoco_fifo_inventory_audit(
            AXIEOS_DB_PATH
        )
    )

    movements = result[
        "movements"
    ]

    sales = [
        item
        for item in movements
        if item["event_type"]
        == "ASSET_SALE"
    ]

    fully_known_sales = [
        item
        for item in sales
        if item["basis_status"]
        == "FULLY_KNOWN_WETH"
    ]

    unknown_basis_sales = [
        item
        for item in sales
        if item["basis_status"]
        == "MIXED_OR_UNKNOWN_BASIS"
    ]

    insufficient_sales = [
        item
        for item in sales
        if item["basis_status"]
        == "INSUFFICIENT_HISTORY"
    ]

    token_counts = {}

    for item in movements:
        label = item[
            "label"
        ]

        token_counts[label] = (
            token_counts.get(
                label,
                0,
            )
            + 1
        )

    validation = (
        len(sales) > 0
        and (
            len(fully_known_sales)
            + len(unknown_basis_sales)
            + len(insufficient_sales)
        )
        == len(sales)
    )

    print(
        "\nAXIEOS COCOCHOCO FIFO INVENTORY AUDIT"
    )

    print(
        "Inventory movements:",
        len(movements),
    )

    print(
        "Consumable sales:",
        len(sales),
    )

    print(
        "Sales with fully known basis:",
        len(
            fully_known_sales
        ),
    )

    print(
        "Sales with mixed/unknown basis:",
        len(
            unknown_basis_sales
        ),
    )

    print(
        "Sales with insufficient history:",
        len(
            insufficient_sales
        ),
    )

    print(
        "\nMOVEMENTS BY ASSET"
    )

    for label in sorted(
        token_counts
    ):
        print(
            f"{label}: "
            f"{token_counts[label]}"
        )

    print(
        "\nREMAINING INVENTORY"
    )

    for token_id in (
        "1",
        "2",
    ):
        print(
            COCOCHOCO_TOKEN_LABELS[
                token_id
            ],
            ":",
            result[
                "remaining_inventory"
            ][token_id],
        )

    print(
        "\nFULLY-KNOWN SALE EXAMPLES"
    )

    for item in (
        fully_known_sales[:10]
    ):
        print(
            "\nTX:",
            item["txhash"],
        )

        print(
            "Date:",
            item["datetime"],
        )

        print(
            "Asset:",
            item["label"],
        )

        print(
            "Quantity:",
            item["quantity"],
        )

        print(
            "FIFO cost basis:",
            item[
                "fifo_cost_basis"
            ],
            "WETH",
        )

        print(
            "Segments:",
            len(
                item["segments"]
            ),
        )

    print(
        "\nUNKNOWN-BASIS SALE EXAMPLES"
    )

    for item in (
        unknown_basis_sales[:10]
    ):
        print(
            "\nTX:",
            item["txhash"],
        )

        print(
            "Date:",
            item["datetime"],
        )

        print(
            "Asset:",
            item["label"],
        )

        print(
            "Quantity:",
            item["quantity"],
        )

        print(
            "Status:",
            item["basis_status"],
        )

        for segment in (
            item["segments"][:5]
        ):
            print(
                " Segment:",
                segment[
                    "quantity"
                ],
                segment[
                    "basis_status"
                ],
                segment[
                    "source_event"
                ],
                segment[
                    "source_txhash"
                ],
            )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )


def run_missing_cost_basis_audit_test():
    results = (
        audit_missing_cost_basis_sales(
            AXIEOS_DB_PATH
        )
    )

    status_counts = {}

    for item in results:
        status = item[
            "evidence_status"
        ]

        status_counts[status] = (
            status_counts.get(
                status,
                0,
            )
            + 1
        )

    prior_purchase_records = [
        item
        for item in results
        if item["evidence_status"]
        == "PRIOR_PURCHASE_FOUND"
    ]

    prior_inbound_records = [
        item
        for item in results
        if item["evidence_status"]
        == "PRIOR_INBOUND_FOUND"
    ]

    missing_token_ids = [
        item
        for item in results
        if item["evidence_status"]
        == "MISSING_TOKEN_ID"
    ]

    validation = (
        sum(
            status_counts.values()
        )
        == len(results)
    )

    print(
        "\nAXIEOS MISSING COST BASIS AUDIT"
    )

    print(
        "Sales needing cost basis:",
        len(results),
    )

    print(
        "Prior purchases found:",
        len(
            prior_purchase_records
        ),
    )

    print(
        "Prior inbound evidence found:",
        len(
            prior_inbound_records
        ),
    )

    print(
        "Missing token IDs:",
        len(
            missing_token_ids
        ),
    )

    print(
        "\nEVIDENCE BREAKDOWN"
    )

    for status in sorted(
        status_counts
    ):
        print(
            f"{status}: "
            f"{status_counts[status]}"
        )

    print(
        "\nRECOVERABLE EXAMPLES"
    )

    recoverable = (
        prior_purchase_records
        + prior_inbound_records
    )

    for item in recoverable[:15]:
        print(
            "\nSALE TX:",
            item["txhash"],
        )

        print(
            "Sale date:",
            item["datetime"],
        )

        print(
            "Asset:",
            item["asset_name"],
        )

        print(
            "Token ID:",
            item[
                "asset_token_id"
            ],
        )

        print(
            "Net proceeds:",
            item["net_amount"],
        )

        print(
            "Evidence:",
            item[
                "evidence_status"
            ],
        )

        for candidate in (
            item["candidates"][:5]
        ):
            print(
                " Candidate:",
                candidate[
                    "datetime"
                ],
                candidate[
                    "event_type"
                ],
                candidate[
                    "gross_amount"
                ],
                candidate[
                    "txhash"
                ],
            )

    print(
        "\nMISSING-ID EXAMPLES"
    )

    for item in missing_token_ids[:10]:
        print(
            "\nTX:",
            item["txhash"],
        )

        print(
            "Date:",
            item["datetime"],
        )

        print(
            "Asset:",
            item["asset_name"],
        )

        print(
            "Net proceeds:",
            item["net_amount"],
        )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )




if __name__ == "__main__":
    run_ronin_sync_v07()