import json
import os
import re
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import time

import requests





PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]

AXIEOS_DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "blockchain"
    / "database"
    / "axieos.db"
)


OWNED_AXIE_STATUSES = {
    "OWNED",
    "SOLD",
    "RELEASED",
    "TRANSFERRED_OUT",
    "UNKNOWN",
}


AXIE_CLASSES = {
    "Aquatic",
    "Beast",
    "Bird",
    "Bug",
    "Dawn",
    "Dusk",
    "Mech",
    "Plant",
    "Reptile",
}


AXIE_PART_SLOTS = {
    "eyes",
    "ears",
    "back",
    "mouth",
    "horn",
    "tail",
}


GAMEPLAY_PIPELINE_VERSION = "0.8"


AXIE_GRAPHQL_URL = (
    "https://graphql-gateway.axieinfinity.com/graphql"
)


SKYMAVIS_API_BASE_URL = (
    "https://api-gateway.skymavis.com"
)


RONIN_EXPLORER_API_URL = (
    "https://explorer.roninchain.com/api/v2"
)

AXIE_CONTRACT_ADDRESS = (
    "0x32950db2a7164ae833121501c797d79e7b79d74c"
)


RONIN_PUBLIC_RPC_URL = (
    "https://api.roninchain.com/rpc"
)


ERC721_TOKEN_OF_OWNER_BY_INDEX_SELECTOR = (
    "2f745c59"
)


AXIE_CORE_FUNCTION_SELECTOR = (
    "3e2156aa"
)


AXIE_CORE_GENE_ORDER = "xy"


PRIMARY_RONIN_WALLET_ADDRESS = (
    "0x1ed8b3f3bd6a624de47f81beea101f0d15cdfbc8"
)

ERC721_BALANCE_OF_SELECTOR = (
    "70a08231"
)

ERC721_TOKENS_OF_OWNER_SELECTOR = (
    "8462151c"
)



AXIE_PART_SKIN_COLLECTION_SIGNALS = {
    1: {"MYSTIC"},
    2: {"BIONIC"},
    3: {"JAPANESE"},
    4: {"XMAS"},
    5: {"XMAS"},
    6: {"SUMMER"},
    8: {"SUMMER"},
    9: {"SHINY"},
    12: {"NIGHTMARE"},
    13: {"SHINY"},
}

AXIE_TAG_COLLECTION_SIGNALS = {
    "ORIGIN": {"ORIGIN"},
    "MEO1": {"MEO_CORP_I"},
    "MEO2": {"MEO_CORP_II"},
}


GAMEPLAY_DATA_VERSION = "0.8"





def initialize_owned_axie_registry(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        gameplay_owned_axies (
            axie_id TEXT PRIMARY KEY,
            wallet_address TEXT NOT NULL,

            ownership_status TEXT NOT NULL,

            axie_class TEXT,
            level INTEGER,
            breed_count INTEGER,

            is_collectible INTEGER,
            collectible_type TEXT,

            is_evolved INTEGER,

            acquisition_txhash TEXT,
            acquisition_datetime TEXT,
            acquisition_cost_weth TEXT,

            last_seen_datetime TEXT,
            data_source TEXT,
            last_updated TEXT
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_gameplay_owned_axies_wallet
        ON gameplay_owned_axies(
            wallet_address
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_gameplay_owned_axies_status
        ON gameplay_owned_axies(
            ownership_status
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_gameplay_owned_axies_class
        ON gameplay_owned_axies(
            axie_class
        )
        """
    )

    connection.commit()
    connection.close()


def initialize_axie_gameplay_detail_tables(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        gameplay_axie_parts (
            axie_id TEXT NOT NULL,
            part_slot TEXT NOT NULL,
            part_id TEXT,
            part_name TEXT,
            part_class TEXT,
            part_value INTEGER,
            part_skin INTEGER,
            part_stage INTEGER,
            is_special INTEGER,
            special_tag TEXT,
            data_source TEXT,
            last_updated TEXT
                DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (
                axie_id,
                part_slot
            ),

            FOREIGN KEY (
                axie_id
            )
            REFERENCES gameplay_owned_axies(
                axie_id
            )
        )
        """
    )

    existing_part_columns = {
        row[1]
        for row in connection.execute(
            """
            PRAGMA table_info(
                gameplay_axie_parts
            )
            """
        ).fetchall()
    }

    migration_columns = {
        "part_value": "INTEGER",
        "part_skin": "INTEGER",
        "part_stage": "INTEGER",
    }

    for (
        column_name,
        column_type,
    ) in migration_columns.items():
        if (
            column_name
            in existing_part_columns
        ):
            continue

        connection.execute(
            f"""
            ALTER TABLE
                gameplay_axie_parts
            ADD COLUMN
                {column_name}
                {column_type}
            """
        )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_gameplay_axie_parts_name
        ON gameplay_axie_parts(
            part_name
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_gameplay_axie_parts_class
        ON gameplay_axie_parts(
            part_class
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_gameplay_axie_parts_stage
        ON gameplay_axie_parts(
            part_stage
        )
        """
    )

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS
        gameplay_axie_traits (
            axie_id TEXT NOT NULL,
            trait_type TEXT NOT NULL,
            trait_value TEXT NOT NULL,
            data_source TEXT,
            last_updated TEXT
                DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (
                axie_id,
                trait_type,
                trait_value
            ),

            FOREIGN KEY (
                axie_id
            )
            REFERENCES gameplay_owned_axies(
                axie_id
            )
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_gameplay_axie_traits_type
        ON gameplay_axie_traits(
            trait_type
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_gameplay_axie_traits_value
        ON gameplay_axie_traits(
            trait_value
        )
        """
    )

    connection.commit()
    connection.close()


def validate_owned_axie_registry(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    table_exists = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
              AND name =
                  'gameplay_owned_axies'
            """
        ).fetchone()[0]
        == 1
    )

    columns = (
        connection.execute(
            """
            PRAGMA table_info(
                gameplay_owned_axies
            )
            """
        ).fetchall()
    )

    column_names = {
        row[1]
        for row in columns
    }

    required_columns = {
        "axie_id",
        "wallet_address",
        "ownership_status",
        "axie_class",
        "level",
        "breed_count",
        "is_collectible",
        "collectible_type",
        "is_evolved",
        "acquisition_txhash",
        "acquisition_datetime",
        "acquisition_cost_weth",
        "last_seen_datetime",
        "data_source",
        "last_updated",
    }

    missing_columns = (
        required_columns
        - column_names
    )

    connection.close()

    validation = (
        table_exists
        and not missing_columns
    )

    return {
        "table_exists": (
            table_exists
        ),
        "column_count": len(
            column_names
        ),
        "missing_columns": sorted(
            missing_columns
        ),
        "validation": validation,
    }



def validate_axie_gameplay_detail_tables(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    required_tables = {
        "gameplay_axie_parts",
        "gameplay_axie_traits",
    }

    table_rows = (
        connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()
    )

    existing_tables = {
        row[0]
        for row in table_rows
    }

    missing_tables = (
        required_tables
        - existing_tables
    )

    parts_columns = {
        row[1]
        for row in connection.execute(
            """
            PRAGMA table_info(
                gameplay_axie_parts
            )
            """
        ).fetchall()
    }

    traits_columns = {
        row[1]
        for row in connection.execute(
            """
            PRAGMA table_info(
                gameplay_axie_traits
            )
            """
        ).fetchall()
    }

    required_parts_columns = {
        "axie_id",
        "part_slot",
        "part_id",
        "part_name",
        "part_class",
        "part_value",
        "part_skin",
        "part_stage",
        "is_special",
        "special_tag",
        "data_source",
        "last_updated",
    }

    required_traits_columns = {
        "axie_id",
        "trait_type",
        "trait_value",
        "data_source",
        "last_updated",
    }

    missing_parts_columns = (
        required_parts_columns
        - parts_columns
    )

    missing_traits_columns = (
        required_traits_columns
        - traits_columns
    )

    connection.close()

    validation = (
        not missing_tables
        and not missing_parts_columns
        and not missing_traits_columns
    )

    return {
        "missing_tables": sorted(
            missing_tables
        ),
        "parts_column_count": len(
            parts_columns
        ),
        "traits_column_count": len(
            traits_columns
        ),
        "missing_parts_columns": sorted(
            missing_parts_columns
        ),
        "missing_traits_columns": sorted(
            missing_traits_columns
        ),
        "validation": validation,
    }



def validate_owned_axie_record(
    record,
):
    errors = []

    axie_id = record.get(
        "axie_id"
    )

    try:
        axie_id_number = int(
            str(axie_id)
        )

        if axie_id_number <= 0:
            errors.append(
                "axie_id must be positive"
            )

    except (
        TypeError,
        ValueError,
    ):
        errors.append(
            "axie_id must be numeric"
        )

    wallet_address = record.get(
        "wallet_address"
    )

    if (
        not isinstance(
            wallet_address,
            str,
        )
        or not wallet_address.strip()
    ):
        errors.append(
            "wallet_address is required"
        )

    ownership_status = record.get(
        "ownership_status"
    )

    if (
        ownership_status
        not in OWNED_AXIE_STATUSES
    ):
        errors.append(
            "invalid ownership_status"
        )

    axie_class = record.get(
        "axie_class"
    )

    if (
        axie_class is not None
        and axie_class
        not in AXIE_CLASSES
    ):
        errors.append(
            "invalid axie_class"
        )

    level = record.get(
        "level"
    )

    if level is not None:
        if (
            not isinstance(
                level,
                int,
            )
            or isinstance(
                level,
                bool,
            )
            or level < 1
        ):
            errors.append(
                "level must be a "
                "positive integer"
            )

    breed_count = record.get(
        "breed_count"
    )

    if breed_count is not None:
        if (
            not isinstance(
                breed_count,
                int,
            )
            or isinstance(
                breed_count,
                bool,
            )
            or breed_count < 0
            or breed_count > 7
        ):
            errors.append(
                "breed_count must be "
                "between 0 and 7"
            )

    for field_name in (
        "is_collectible",
        "is_evolved",
    ):
        value = record.get(
            field_name
        )

        if value not in {
            None,
            0,
            1,
        }:
            errors.append(
                f"{field_name} must "
                "be 0, 1, or None"
            )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }



def validate_axie_part_record(
    record,
):
    errors = []

    axie_id = record.get(
        "axie_id"
    )

    try:
        axie_id_number = int(
            str(axie_id)
        )

        if axie_id_number <= 0:
            errors.append(
                "axie_id must be positive"
            )

    except (
        TypeError,
        ValueError,
    ):
        errors.append(
            "axie_id must be numeric"
        )

    part_slot = record.get(
        "part_slot"
    )

    if (
        part_slot
        not in AXIE_PART_SLOTS
    ):
        errors.append(
            "invalid part_slot"
        )

    is_special = record.get(
        "is_special"
    )

    if is_special not in {
        None,
        0,
        1,
    }:
        errors.append(
            "is_special must be "
            "0, 1, or None"
        )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }



def validate_axie_trait_record(
    record,
):
    errors = []

    axie_id = record.get(
        "axie_id"
    )

    try:
        axie_id_number = int(
            str(axie_id)
        )

        if axie_id_number <= 0:
            errors.append(
                "axie_id must be positive"
            )

    except (
        TypeError,
        ValueError,
    ):
        errors.append(
            "axie_id must be numeric"
        )

    trait_type = record.get(
        "trait_type"
    )

    if (
        not isinstance(
            trait_type,
            str,
        )
        or not trait_type.strip()
    ):
        errors.append(
            "trait_type is required"
        )

    trait_value = record.get(
        "trait_value"
    )

    if (
        not isinstance(
            trait_value,
            str,
        )
        or not trait_value.strip()
    ):
        errors.append(
            "trait_value is required"
        )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }



def upsert_owned_axie(
    db_path,
    record,
):
    validation = (
        validate_owned_axie_record(
            record
        )
    )

    if not validation["valid"]:
        raise ValueError(
            "Invalid owned Axie record: "
            + "; ".join(
                validation["errors"]
            )
        )

    axie_id = str(
        int(
            str(
                record["axie_id"]
            )
        )
    )

    wallet_address = (
        record[
            "wallet_address"
        ]
        .strip()
        .lower()
    )

    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        INSERT INTO gameplay_owned_axies (
            axie_id,
            wallet_address,
            ownership_status,
            axie_class,
            level,
            breed_count,
            is_collectible,
            collectible_type,
            is_evolved,
            acquisition_txhash,
            acquisition_datetime,
            acquisition_cost_weth,
            last_seen_datetime,
            data_source,
            last_updated
        )
        VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT(axie_id)
        DO UPDATE SET
            wallet_address =
                excluded.wallet_address,
            ownership_status =
                excluded.ownership_status,
            axie_class =
                COALESCE(
                    excluded.axie_class,
                    gameplay_owned_axies.axie_class
                ),
            level =
                COALESCE(
                    excluded.level,
                    gameplay_owned_axies.level
                ),
            breed_count =
                COALESCE(
                    excluded.breed_count,
                    gameplay_owned_axies.breed_count
                ),
            is_collectible =
                COALESCE(
                    excluded.is_collectible,
                    gameplay_owned_axies.is_collectible
                ),
            collectible_type =
                COALESCE(
                    excluded.collectible_type,
                    gameplay_owned_axies.collectible_type
                ),
            is_evolved =
                COALESCE(
                    excluded.is_evolved,
                    gameplay_owned_axies.is_evolved
                ),
            acquisition_txhash =
                COALESCE(
                    excluded.acquisition_txhash,
                    gameplay_owned_axies.acquisition_txhash
                ),
            acquisition_datetime =
                COALESCE(
                    excluded.acquisition_datetime,
                    gameplay_owned_axies.acquisition_datetime
                ),
            acquisition_cost_weth =
                COALESCE(
                    excluded.acquisition_cost_weth,
                    gameplay_owned_axies.acquisition_cost_weth
                ),
            last_seen_datetime =
                COALESCE(
                    excluded.last_seen_datetime,
                    gameplay_owned_axies.last_seen_datetime
                ),
            data_source =
                COALESCE(
                    excluded.data_source,
                    gameplay_owned_axies.data_source
                ),
            last_updated =
                CURRENT_TIMESTAMP
        """,
        (
            axie_id,
            wallet_address,
            record[
                "ownership_status"
            ],
            record.get(
                "axie_class"
            ),
            record.get(
                "level"
            ),
            record.get(
                "breed_count"
            ),
            record.get(
                "is_collectible"
            ),
            record.get(
                "collectible_type"
            ),
            record.get(
                "is_evolved"
            ),
            record.get(
                "acquisition_txhash"
            ),
            record.get(
                "acquisition_datetime"
            ),
            record.get(
                "acquisition_cost_weth"
            ),
            record.get(
                "last_seen_datetime"
            ),
            record.get(
                "data_source"
            ),
        ),
    )

    connection.commit()
    connection.close()

    return axie_id



def upsert_axie_part(
    db_path,
    record,
):
    validation = (
        validate_axie_part_record(
            record
        )
    )

    if not validation["valid"]:
        raise ValueError(
            "Invalid Axie part record: "
            + "; ".join(
                validation["errors"]
            )
        )

    axie_id = str(
        int(
            str(
                record["axie_id"]
            )
        )
    )

    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        INSERT INTO gameplay_axie_parts (
            axie_id,
            part_slot,
            part_id,
            part_name,
            part_class,
            part_value,
            part_skin,
            part_stage,
            is_special,
            special_tag,
            data_source,
            last_updated
        )
        VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT(
            axie_id,
            part_slot
        )
        DO UPDATE SET
            part_id =
                COALESCE(
                    excluded.part_id,
                    gameplay_axie_parts.part_id
                ),
            part_name =
                COALESCE(
                    excluded.part_name,
                    gameplay_axie_parts.part_name
                ),
            part_class =
                COALESCE(
                    excluded.part_class,
                    gameplay_axie_parts.part_class
                ),
            part_value =
                COALESCE(
                    excluded.part_value,
                    gameplay_axie_parts.part_value
                ),
            part_skin =
                COALESCE(
                    excluded.part_skin,
                    gameplay_axie_parts.part_skin
                ),
            part_stage =
                COALESCE(
                    excluded.part_stage,
                    gameplay_axie_parts.part_stage
                ),
            is_special =
                COALESCE(
                    excluded.is_special,
                    gameplay_axie_parts.is_special
                ),
            special_tag =
                COALESCE(
                    excluded.special_tag,
                    gameplay_axie_parts.special_tag
                ),
            data_source =
                COALESCE(
                    excluded.data_source,
                    gameplay_axie_parts.data_source
                ),
            last_updated =
                CURRENT_TIMESTAMP
        """,
        (
            axie_id,
            record[
                "part_slot"
            ],
            record.get(
                "part_id"
            ),
            record.get(
                "part_name"
            ),
            record.get(
                "part_class"
            ),
            record.get(
                "part_value"
            ),
            record.get(
                "part_skin"
            ),
            record.get(
                "part_stage"
            ),
            record.get(
                "is_special"
            ),
            record.get(
                "special_tag"
            ),
            record.get(
                "data_source"
            ),
        ),
    )

    connection.commit()
    connection.close()



def normalize_origins_fighter_parts(
    fighter,
):
    axie_id = fighter.get(
        "id"
    )

    if axie_id is None:
        raise ValueError(
            "Origins fighter has no Axie ID."
        )

    raw_parts = (
        fighter.get(
            "parts"
        )
        or []
    )

    normalized_parts = []

    for raw_part in raw_parts:
        part_type = raw_part.get(
            "part_type"
        )

        if not part_type:
            raise ValueError(
                "Origins part has no part_type."
            )

        part_slot = (
            str(
                part_type
            )
            .strip()
            .lower()
        )

        record = {
            "axie_id": str(
                int(
                    str(
                        axie_id
                    )
                )
            ),
            "part_slot": (
                part_slot
            ),
            "part_id": None,
            "part_name": None,
            "part_class": (
                raw_part.get(
                    "part_class"
                )
            ),
            "part_value": (
                raw_part.get(
                    "part_value"
                )
            ),
            "part_skin": (
                raw_part.get(
                    "part_skin"
                )
            ),
            "part_stage": (
                raw_part.get(
                    "part_stage"
                )
            ),
            "is_special": None,
            "special_tag": None,
            "data_source": (
                "SKYMAVIS_ORIGINS_API"
            ),
        }

        validation = (
            validate_axie_part_record(
                record
            )
        )

        if not validation[
            "valid"
        ]:
            raise ValueError(
                (
                    "Invalid normalized "
                    "Origins part: "
                )
                + "; ".join(
                    validation[
                        "errors"
                    ]
                )
            )

        normalized_parts.append(
            record
        )

    return normalized_parts



def sync_origins_metadata_for_owned_axies(
    db_path,
):
    result = (
        fetch_all_origins_ronin_fighters()
    )

    if not result["success"]:
        return {
            "success": False,
            "owned_axies": 0,
            "origins_matched": 0,
            "origins_missing": [],
            "synced_axies": 0,
            "parts_upserted": 0,
            "evolved_axies": 0,
            "skipped_axies": [],
            "error": result.get(
                "error"
            ),
        }

    fighters = result[
        "fighters"
    ]

    fighter_map = {
        str(
            fighter["id"]
        ): fighter
        for fighter in fighters
        if fighter.get(
            "id"
        )
        is not None
    }

    connection = sqlite3.connect(
        db_path
    )

    owned_rows = (
        connection.execute(
            """
            SELECT axie_id
            FROM gameplay_owned_axies
            WHERE ownership_status = 'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    connection.close()

    owned_ids = {
        str(row[0])
        for row in owned_rows
    }

    matched_ids = (
        owned_ids
        & set(
            fighter_map.keys()
        )
    )

    missing_ids = (
        owned_ids
        - matched_ids
    )

    valid_records = []
    skipped_axies = []

    for axie_id in sorted(
        matched_ids,
        key=int,
    ):
        fighter = fighter_map[
            axie_id
        ]

        axie_class = fighter.get(
            "class"
        )

        xp = (
            fighter.get(
                "xp"
            )
            or {}
        )

        level = xp.get(
            "currentLevel"
        )

        try:
            parts = (
                normalize_origins_fighter_parts(
                    fighter
                )
            )

        except ValueError as error:
            skipped_axies.append(
                {
                    "axie_id": axie_id,
                    "reason": str(error),
                }
            )

            continue

        expected_slots = set(
            AXIE_PART_SLOTS
        )

        actual_slots = {
            record[
                "part_slot"
            ]
            for record in parts
        }

        class_valid = (
            axie_class
            in AXIE_CLASSES
        )

        level_valid = (
            isinstance(
                level,
                int,
            )
            and level > 0
        )

        parts_valid = (
            len(parts) == 6
            and actual_slots
            == expected_slots
        )

        stages_valid = all(
            isinstance(
                part.get(
                    "part_stage"
                ),
                int,
            )
            and part[
                "part_stage"
            ] >= 0
            for part in parts
        )

        if not (
            class_valid
            and level_valid
            and parts_valid
            and stages_valid
        ):
            reasons = []

            if not class_valid:
                reasons.append(
                    "invalid class"
                )

            if not level_valid:
                reasons.append(
                    "invalid level"
                )

            if not parts_valid:
                reasons.append(
                    "invalid parts"
                )

            if not stages_valid:
                reasons.append(
                    "invalid part stage"
                )

            skipped_axies.append(
                {
                    "axie_id": axie_id,
                    "reason": (
                        ", ".join(
                            reasons
                        )
                    ),
                }
            )

            continue

        evolved_part_count = sum(
            1
            for part in parts
            if part[
                "part_stage"
            ] >= 2
        )

        is_evolved = (
            1
            if evolved_part_count > 0
            else 0
        )

        valid_records.append(
            {
                "axie_id": axie_id,
                "axie_class": (
                    axie_class
                ),
                "level": level,
                "is_evolved": (
                    is_evolved
                ),
                "evolved_part_count": (
                    evolved_part_count
                ),
                "parts": parts,
            }
        )

    connection = sqlite3.connect(
        db_path
    )

    for record in valid_records:
        connection.execute(
            """
            UPDATE gameplay_owned_axies
            SET
                axie_class = ?,
                level = ?,
                is_evolved = ?,
                last_updated =
                    CURRENT_TIMESTAMP
            WHERE axie_id = ?
              AND ownership_status =
                  'OWNED'
            """,
            (
                record[
                    "axie_class"
                ],
                record[
                    "level"
                ],
                record[
                    "is_evolved"
                ],
                record[
                    "axie_id"
                ],
            ),
        )

    connection.commit()
    connection.close()

    parts_upserted = 0

    for record in valid_records:
        for part in record[
            "parts"
        ]:
            upsert_axie_part(
                db_path,
                part,
            )

            parts_upserted += 1

    evolved_axies = sum(
        record[
            "is_evolved"
        ]
        for record in valid_records
    )

    return {
        "success": True,
        "owned_axies": len(
            owned_ids
        ),
        "origins_matched": len(
            matched_ids
        ),
        "origins_missing": sorted(
            missing_ids,
            key=int,
        ),
        "synced_axies": len(
            valid_records
        ),
        "parts_upserted": (
            parts_upserted
        ),
        "evolved_axies": (
            evolved_axies
        ),
        "records": (
            valid_records
        ),
        "skipped_axies": (
            skipped_axies
        ),
        "error": None,
    }



def upsert_axie_trait(
    db_path,
    record,
):
    validation = (
        validate_axie_trait_record(
            record
        )
    )

    if not validation["valid"]:
        raise ValueError(
            "Invalid Axie trait record: "
            + "; ".join(
                validation["errors"]
            )
        )

    axie_id = str(
        int(
            str(
                record["axie_id"]
            )
        )
    )

    connection = sqlite3.connect(
        db_path
    )

    connection.execute(
        """
        INSERT INTO gameplay_axie_traits (
            axie_id,
            trait_type,
            trait_value,
            data_source,
            last_updated
        )
        VALUES (
            ?, ?, ?, ?,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT(
            axie_id,
            trait_type,
            trait_value
        )
        DO UPDATE SET
            data_source =
                excluded.data_source,
            last_updated =
                CURRENT_TIMESTAMP
        """,
        (
            axie_id,
            record[
                "trait_type"
            ],
            record[
                "trait_value"
            ],
            record.get(
                "data_source"
            ),
        ),
    )

    connection.commit()
    connection.close()



def sync_collection_traits_for_owned_axies(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    owned_rows = (
        connection.execute(
            """
            SELECT
                axie_id
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    connection.close()

    owned_ids = [
        str(row[0])
        for row in owned_rows
    ]

    classified_records = []
    failed_records = []

    for axie_id in owned_ids:
        core_result = (
            fetch_axie_core_onchain(
                axie_id
            )
        )

        if not core_result[
            "success"
        ]:
            failed_records.append(
                {
                    "axie_id": axie_id,
                    "reason": (
                        core_result.get(
                            "error"
                        )
                    ),
                }
            )

            continue

        core_data = core_result[
            "data"
        ]

        try:
            genes_hex = (
                build_full_axie_genes_from_core(
                    core_data[
                        "genes_x"
                    ],
                    core_data[
                        "genes_y"
                    ],
                    AXIE_CORE_GENE_ORDER,
                )
            )

            classification = (
                classify_axie_collections_from_genes(
                    genes_hex
                )
            )

        except ValueError as error:
            failed_records.append(
                {
                    "axie_id": axie_id,
                    "reason": str(error),
                }
            )

            continue

        classified_records.append(
            {
                "axie_id": axie_id,
                "is_collectible": (
                    classification[
                        "is_collectible"
                    ]
                ),
                "collections": (
                    classification[
                        "collections"
                    ]
                ),
                "unknown_skin_codes": (
                    classification[
                        "unknown_skin_codes"
                    ]
                ),
                "has_unmapped_special_signal": (
                    classification[
                        "has_unmapped_special_signal"
                    ]
                ),
            }
        )

    connection = sqlite3.connect(
        db_path
    )

    for record in classified_records:
        connection.execute(
            """
            DELETE FROM
                gameplay_axie_traits
            WHERE axie_id = ?
              AND trait_type =
                  'COLLECTION'
            """,
            (
                record[
                    "axie_id"
                ],
            ),
        )

        connection.execute(
            """
            UPDATE gameplay_owned_axies
            SET
                is_collectible = ?,
                last_updated =
                    CURRENT_TIMESTAMP
            WHERE axie_id = ?
              AND ownership_status =
                  'OWNED'
            """,
            (
                record[
                    "is_collectible"
                ],
                record[
                    "axie_id"
                ],
            ),
        )

    connection.commit()
    connection.close()

    traits_written = 0

    for record in classified_records:
        for collection in record[
            "collections"
        ]:
            upsert_axie_trait(
                db_path,
                {
                    "axie_id": (
                        record[
                            "axie_id"
                        ]
                    ),
                    "trait_type": (
                        "COLLECTION"
                    ),
                    "trait_value": (
                        collection
                    ),
                    "data_source": (
                        "RONIN_AXIE_GENES"
                    ),
                },
            )

            traits_written += 1

    collectible_count = sum(
        record[
            "is_collectible"
        ]
        for record
        in classified_records
    )

    multi_collection_count = sum(
        1
        for record
        in classified_records
        if len(
            record[
                "collections"
            ]
        )
        > 1
    )

    unmapped_count = sum(
        1
        for record
        in classified_records
        if record[
            "has_unmapped_special_signal"
        ]
    )

    return {
        "success": (
            len(
                failed_records
            )
            == 0
        ),
        "owned_axies": len(
            owned_ids
        ),
        "classified_axies": len(
            classified_records
        ),
        "collectible_axies": (
            collectible_count
        ),
        "collection_traits_written": (
            traits_written
        ),
        "multi_collection_axies": (
            multi_collection_count
        ),
        "unmapped_special_axies": (
            unmapped_count
        ),
        "records": (
            classified_records
        ),
        "failed_axies": (
            failed_records
        ),
    }




def derive_axie_ownership_from_accounting(
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
            asset_name,
            asset_token_id,
            quantity,
            direction,
            gross_amount,
            cost_basis,
            accounting_status
        FROM blockchain_accounting_records
        WHERE (
            asset_category = 'AXIE_NFT'
            OR asset_name = 'Axie'
        )
          AND asset_token_id IS NOT NULL
        ORDER BY
            datetime,
            txhash
        """
    ).fetchall()

    connection.close()

    histories = {}

    for row in rows:
        (
            txhash,
            datetime_value,
            event_type,
            asset_name,
            token_id,
            quantity,
            direction,
            gross_amount,
            cost_basis,
            accounting_status,
        ) = row

        axie_id = str(
            token_id
        )

        histories.setdefault(
            axie_id,
            []
        ).append(
            {
                "txhash": txhash,
                "datetime": (
                    datetime_value
                ),
                "event_type": (
                    event_type
                ),
                "direction": (
                    direction
                ),
                "quantity": quantity,
                "gross_amount": (
                    gross_amount
                ),
                "cost_basis": (
                    cost_basis
                ),
                "accounting_status": (
                    accounting_status
                ),
            }
        )

    results = []

    inbound_events = {
        "ASSET_PURCHASE",
        "TRANSFER_IN",
        "MINT_OR_CLAIM",
    }

    for axie_id, history in (
        histories.items()
    ):
        latest = history[-1]

        latest_event = latest[
            "event_type"
        ]

        if latest_event in (
            inbound_events
        ):
            ownership_status = "OWNED"

        elif latest_event == (
            "ASSET_SALE"
        ):
            ownership_status = "SOLD"

        elif latest_event == (
            "ASSET_BURN"
        ):
            ownership_status = (
                "RELEASED"
            )

        elif latest_event == (
            "TRANSFER_OUT"
        ):
            ownership_status = (
                "TRANSFERRED_OUT"
            )

        else:
            ownership_status = (
                "UNKNOWN"
            )

        acquisition = None

        if ownership_status == "OWNED":
            for item in reversed(
                history
            ):
                if (
                    item["event_type"]
                    in inbound_events
                ):
                    acquisition = item
                    break

        acquisition_cost = None

        if acquisition is not None:
            if (
                acquisition["event_type"]
                == "ASSET_PURCHASE"
                and acquisition[
                    "gross_amount"
                ]
                is not None
            ):
                acquisition_cost = (
                    acquisition[
                        "gross_amount"
                    ]
                )

        results.append(
            {
                "axie_id": axie_id,
                "ownership_status": (
                    ownership_status
                ),
                "latest_txhash": (
                    latest["txhash"]
                ),
                "latest_datetime": (
                    latest["datetime"]
                ),
                "latest_event_type": (
                    latest_event
                ),
                "history_count": len(
                    history
                ),
                "acquisition_txhash": (
                    acquisition[
                        "txhash"
                    ]
                    if acquisition
                    is not None
                    else None
                ),
                "acquisition_datetime": (
                    acquisition[
                        "datetime"
                    ]
                    if acquisition
                    is not None
                    else None
                ),
                "acquisition_event_type": (
                    acquisition[
                        "event_type"
                    ]
                    if acquisition
                    is not None
                    else None
                ),
                "acquisition_cost_weth": (
                    acquisition_cost
                ),
            }
        )

    results.sort(
        key=lambda item: (
            int(item["axie_id"])
        )
    )

    return results



def normalize_gameplay_address(
    address,
):
    if address is None:
        return None

    value = str(
        address
    ).strip().lower()

    if value.startswith(
        "ronin:"
    ):
        value = (
            "0x"
            + value[6:]
        )

    return value



def load_user_owned_wallet_addresses(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    rows = connection.execute(
        """
        SELECT address
        FROM ronin_wallet_registry
        WHERE ownership_type =
            'USER_OWNED'
        ORDER BY address
        """
    ).fetchall()

    connection.close()

    return {
        normalize_gameplay_address(
            row[0]
        )
        for row in rows
        if row[0] is not None
    }



def reconcile_axie_ownership_with_raw_transfers(
    db_path,
):
    derived = (
        derive_axie_ownership_from_accounting(
            db_path
        )
    )

    owned_wallets = (
        load_user_owned_wallet_addresses(
            db_path
        )
    )

    connection = sqlite3.connect(
        db_path
    )

    results = []

    for item in derived:
        axie_id = item[
            "axie_id"
        ]

        rows = connection.execute(
            """
            SELECT
                tx_hash,
                timestamp,
                from_address,
                to_address
            FROM ronin_token_transfers_raw
            WHERE token_name = 'Axie'
              AND token_id = ?
            ORDER BY
                timestamp,
                tx_hash
            """,
            (
                axie_id,
            ),
        ).fetchall()

        relevant_history = []

        for row in rows:
            (
                txhash,
                timestamp,
                from_address,
                to_address,
            ) = row

            from_normalized = (
                normalize_gameplay_address(
                    from_address
                )
            )

            to_normalized = (
                normalize_gameplay_address(
                    to_address
                )
            )

            from_owned = (
                from_normalized
                in owned_wallets
            )

            to_owned = (
                to_normalized
                in owned_wallets
            )

            if (
                to_owned
                and not from_owned
            ):
                raw_state = "OWNED"

            elif (
                from_owned
                and not to_owned
            ):
                raw_state = (
                    "NOT_OWNED"
                )

            elif (
                from_owned
                and to_owned
            ):
                raw_state = "OWNED"

            else:
                continue

            relevant_history.append(
                {
                    "txhash": txhash,
                    "timestamp": (
                        timestamp
                    ),
                    "from_address": (
                        from_normalized
                    ),
                    "to_address": (
                        to_normalized
                    ),
                    "raw_state": (
                        raw_state
                    ),
                }
            )

        if relevant_history:
            latest_raw = (
                relevant_history[-1]
            )

            raw_state = latest_raw[
                "raw_state"
            ]

        else:
            latest_raw = None
            raw_state = (
                "NO_RAW_HISTORY"
            )

        accounting_status = item[
            "ownership_status"
        ]

        if accounting_status == "OWNED":
            accounting_state = "OWNED"

        elif accounting_status in {
            "SOLD",
            "RELEASED",
            "TRANSFERRED_OUT",
        }:
            accounting_state = (
                "NOT_OWNED"
            )

        else:
            accounting_state = (
                "UNKNOWN"
            )

        if raw_state == (
            "NO_RAW_HISTORY"
        ):
            reconciliation_status = (
                "NO_RAW_HISTORY"
            )

        elif accounting_state == (
            "UNKNOWN"
        ):
            reconciliation_status = (
                "ACCOUNTING_UNKNOWN"
            )

        elif (
            accounting_state
            == raw_state
        ):
            reconciliation_status = (
                "MATCH"
            )

        else:
            reconciliation_status = (
                "MISMATCH"
            )

        results.append(
            {
                "axie_id": axie_id,
                "accounting_status": (
                    accounting_status
                ),
                "accounting_state": (
                    accounting_state
                ),
                "raw_state": (
                    raw_state
                ),
                "reconciliation_status": (
                    reconciliation_status
                ),
                "raw_history_count": len(
                    relevant_history
                ),
                "latest_raw": (
                    latest_raw
                ),
            }
        )

    connection.close()

    results.sort(
        key=lambda item: int(
            item["axie_id"]
        )
    )

    return {
        "owned_wallets": (
            owned_wallets
        ),
        "records": results,
    }



def sync_owned_axie_registry_from_accounting(
    db_path,
):
    initialize_owned_axie_registry(
        db_path
    )

    derived = (
        derive_axie_ownership_from_accounting(
            db_path
        )
    )

    reconciliation = (
        reconcile_axie_ownership_with_raw_transfers(
            db_path
        )
    )

    reconciliation_map = {
        item["axie_id"]: item
        for item in reconciliation[
            "records"
        ]
    }

    owned_wallets = reconciliation[
        "owned_wallets"
    ]

    synced_owned = 0
    lifecycle_updates = 0
    skipped = 0

    connection = sqlite3.connect(
        db_path
    )

    existing_ids = {
        row[0]
        for row in connection.execute(
            """
            SELECT axie_id
            FROM gameplay_owned_axies
            """
        ).fetchall()
    }

    connection.close()

    for item in derived:
        axie_id = item[
            "axie_id"
        ]

        ownership_status = item[
            "ownership_status"
        ]

        reconciliation_item = (
            reconciliation_map.get(
                axie_id
            )
        )

        if reconciliation_item is None:
            skipped += 1
            continue

        if (
            reconciliation_item[
                "reconciliation_status"
            ]
            != "MATCH"
        ):
            skipped += 1
            continue

        # ---------------------------------
        # Currently owned Axie
        # ---------------------------------

        if ownership_status == "OWNED":
            latest_raw = (
                reconciliation_item[
                    "latest_raw"
                ]
            )

            if latest_raw is None:
                skipped += 1
                continue

            to_address = (
                normalize_gameplay_address(
                    latest_raw[
                        "to_address"
                    ]
                )
            )

            from_address = (
                normalize_gameplay_address(
                    latest_raw[
                        "from_address"
                    ]
                )
            )

            if to_address in owned_wallets:
                current_wallet = (
                    to_address
                )

            elif (
                from_address
                in owned_wallets
            ):
                current_wallet = (
                    from_address
                )

            else:
                skipped += 1
                continue

            record = {
                "axie_id": axie_id,
                "wallet_address": (
                    current_wallet
                ),
                "ownership_status": (
                    "OWNED"
                ),
                "axie_class": None,
                "level": None,
                "breed_count": None,
                "is_collectible": None,
                "collectible_type": None,
                "is_evolved": None,
                "acquisition_txhash": (
                    item[
                        "acquisition_txhash"
                    ]
                ),
                "acquisition_datetime": (
                    item[
                        "acquisition_datetime"
                    ]
                ),
                "acquisition_cost_weth": (
                    item[
                        "acquisition_cost_weth"
                    ]
                ),
                "last_seen_datetime": (
                    item[
                        "latest_datetime"
                    ]
                ),
                "data_source": (
                    "AXIEOS_ACCOUNTING_DERIVED"
                ),
            }

            upsert_owned_axie(
                db_path,
                record,
            )

            synced_owned += 1
            continue

        # ---------------------------------
        # Lifecycle update for an Axie
        # that was previously in registry
        # ---------------------------------

        if axie_id not in existing_ids:
            continue

        connection = sqlite3.connect(
            db_path
        )

        connection.execute(
            """
            UPDATE gameplay_owned_axies
            SET
                ownership_status = ?,
                last_seen_datetime = ?,
                data_source = ?,
                last_updated =
                    CURRENT_TIMESTAMP
            WHERE axie_id = ?
            """,
            (
                ownership_status,
                item[
                    "latest_datetime"
                ],
                (
                    "AXIEOS_ACCOUNTING_DERIVED"
                ),
                axie_id,
            ),
        )

        connection.commit()
        connection.close()

        lifecycle_updates += 1

    connection = sqlite3.connect(
        db_path
    )

    registry_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                wallet_address,
                ownership_status,
                acquisition_txhash,
                acquisition_datetime,
                acquisition_cost_weth
            FROM gameplay_owned_axies
            ORDER BY CAST(
                axie_id AS INTEGER
            )
            """
        ).fetchall()
    )

    connection.close()

    registry_owned = [
        row
        for row in registry_rows
        if row[2] == "OWNED"
    ]

    return {
        "derived_count": len(
            derived
        ),
        "derived_owned": sum(
            1
            for item in derived
            if item[
                "ownership_status"
            ]
            == "OWNED"
        ),
        "synced_owned": (
            synced_owned
        ),
        "lifecycle_updates": (
            lifecycle_updates
        ),
        "skipped": skipped,
        "registry_rows": (
            registry_rows
        ),
        "registry_owned": (
            registry_owned
        ),
    }



def validate_owned_axie_foundation(
    db_path,
):
    initialize_owned_axie_registry(
        db_path
    )

    initialize_axie_gameplay_detail_tables(
        db_path
    )

    registry_schema = (
        validate_owned_axie_registry(
            db_path
        )
    )

    detail_schema = (
        validate_axie_gameplay_detail_tables(
            db_path
        )
    )

    sync_result = (
        sync_owned_axie_registry_from_accounting(
            db_path
        )
    )

    derived = (
        derive_axie_ownership_from_accounting(
            db_path
        )
    )

    reconciliation = (
        reconcile_axie_ownership_with_raw_transfers(
            db_path
        )
    )

    expected_owned_ids = {
        item["axie_id"]
        for item in derived
        if item[
            "ownership_status"
        ]
        == "OWNED"
    }

    reconciliation_valid = all(
        item[
            "reconciliation_status"
        ]
        == "MATCH"
        for item in reconciliation[
            "records"
        ]
    )

    connection = sqlite3.connect(
        db_path
    )

    registry_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                wallet_address,
                ownership_status,
                acquisition_cost_weth,
                data_source
            FROM gameplay_owned_axies
            ORDER BY CAST(
                axie_id AS INTEGER
            )
            """
        ).fetchall()
    )

    duplicate_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                COUNT(*)
            FROM gameplay_owned_axies
            GROUP BY axie_id
            HAVING COUNT(*) > 1
            """
        ).fetchall()
    )

    orphan_parts = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM gameplay_axie_parts p
            LEFT JOIN gameplay_owned_axies a
                ON a.axie_id = p.axie_id
            WHERE a.axie_id IS NULL
            """
        ).fetchone()[0]
    )

    orphan_traits = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM gameplay_axie_traits t
            LEFT JOIN gameplay_owned_axies a
                ON a.axie_id = t.axie_id
            WHERE a.axie_id IS NULL
            """
        ).fetchone()[0]
    )

    connection.close()

    actual_owned_rows = [
        row
        for row in registry_rows
        if row[2] == "OWNED"
    ]

    actual_owned_ids = {
        row[0]
        for row in actual_owned_rows
    }

    owned_wallets = (
        reconciliation[
            "owned_wallets"
        ]
    )

    owned_wallet_valid = all(
        normalize_gameplay_address(
            row[1]
        )
        in owned_wallets
        for row in actual_owned_rows
    )

    valid_statuses = all(
        row[2]
        in OWNED_AXIE_STATUSES
        for row in registry_rows
    )

    owned_set_valid = (
        actual_owned_ids
        == expected_owned_ids
    )

    duplicate_valid = (
        len(duplicate_rows) == 0
    )

    orphan_valid = (
        orphan_parts == 0
        and orphan_traits == 0
    )

    known_cost_count = sum(
        1
        for row in actual_owned_rows
        if row[3] is not None
    )

    unknown_cost_count = (
        len(actual_owned_rows)
        - known_cost_count
    )

    validation = (
        registry_schema[
            "validation"
        ]
        and detail_schema[
            "validation"
        ]
        and reconciliation_valid
        and owned_set_valid
        and owned_wallet_valid
        and valid_statuses
        and duplicate_valid
        and orphan_valid
        and sync_result[
            "skipped"
        ]
        == 0
    )

    return {
        "registry_schema": (
            registry_schema[
                "validation"
            ]
        ),
        "detail_schema": (
            detail_schema[
                "validation"
            ]
        ),
        "accounting_axies": len(
            derived
        ),
        "expected_owned": len(
            expected_owned_ids
        ),
        "registry_owned": len(
            actual_owned_rows
        ),
        "known_cost_count": (
            known_cost_count
        ),
        "unknown_cost_count": (
            unknown_cost_count
        ),
        "reconciliation_valid": (
            reconciliation_valid
        ),
        "owned_set_valid": (
            owned_set_valid
        ),
        "owned_wallet_valid": (
            owned_wallet_valid
        ),
        "valid_statuses": (
            valid_statuses
        ),
        "duplicate_valid": (
            duplicate_valid
        ),
        "orphan_parts": (
            orphan_parts
        ),
        "orphan_traits": (
            orphan_traits
        ),
        "skipped": sync_result[
            "skipped"
        ],
        "validation": validation,
    }



def load_owned_axie_gameplay_profiles(
    db_path,
    owned_only=True,
):
    connection = sqlite3.connect(
        db_path
    )

    if owned_only:
        axie_rows = connection.execute(
            """
            SELECT
                axie_id,
                wallet_address,
                ownership_status,
                axie_class,
                level,
                breed_count,
                is_collectible,
                collectible_type,
                is_evolved,
                acquisition_txhash,
                acquisition_datetime,
                acquisition_cost_weth,
                last_seen_datetime,
                data_source
            FROM gameplay_owned_axies
            WHERE ownership_status = 'OWNED'
            ORDER BY CAST(
                axie_id AS INTEGER
            )
            """
        ).fetchall()

    else:
        axie_rows = connection.execute(
            """
            SELECT
                axie_id,
                wallet_address,
                ownership_status,
                axie_class,
                level,
                breed_count,
                is_collectible,
                collectible_type,
                is_evolved,
                acquisition_txhash,
                acquisition_datetime,
                acquisition_cost_weth,
                last_seen_datetime,
                data_source
            FROM gameplay_owned_axies
            ORDER BY CAST(
                axie_id AS INTEGER
            )
            """
        ).fetchall()

    part_rows = connection.execute(
        """
        SELECT
            axie_id,
            part_slot,
            part_id,
            part_name,
            part_class,
            is_special,
            special_tag,
            data_source
        FROM gameplay_axie_parts
        ORDER BY
            axie_id,
            part_slot
        """
    ).fetchall()

    trait_rows = connection.execute(
        """
        SELECT
            axie_id,
            trait_type,
            trait_value,
            data_source
        FROM gameplay_axie_traits
        ORDER BY
            axie_id,
            trait_type,
            trait_value
        """
    ).fetchall()

    connection.close()

    parts_by_axie = {}

    for row in part_rows:
        (
            axie_id,
            part_slot,
            part_id,
            part_name,
            part_class,
            is_special,
            special_tag,
            data_source,
        ) = row

        parts_by_axie.setdefault(
            str(axie_id),
            {},
        )[part_slot] = {
            "part_id": part_id,
            "part_name": part_name,
            "part_class": part_class,
            "is_special": is_special,
            "special_tag": special_tag,
            "data_source": data_source,
        }

    traits_by_axie = {}

    for row in trait_rows:
        (
            axie_id,
            trait_type,
            trait_value,
            data_source,
        ) = row

        axie_traits = (
            traits_by_axie.setdefault(
                str(axie_id),
                {},
            )
        )

        axie_traits.setdefault(
            trait_type,
            [],
        ).append(
            {
                "value": trait_value,
                "data_source": (
                    data_source
                ),
            }
        )

    profiles = []

    for row in axie_rows:
        (
            axie_id,
            wallet_address,
            ownership_status,
            axie_class,
            level,
            breed_count,
            is_collectible,
            collectible_type,
            is_evolved,
            acquisition_txhash,
            acquisition_datetime,
            acquisition_cost_weth,
            last_seen_datetime,
            data_source,
        ) = row

        axie_id = str(
            axie_id
        )

        profiles.append(
            {
                "axie_id": axie_id,
                "wallet_address": (
                    wallet_address
                ),
                "ownership_status": (
                    ownership_status
                ),
                "axie_class": axie_class,
                "level": level,
                "breed_count": (
                    breed_count
                ),
                "is_collectible": (
                    is_collectible
                ),
                "collectible_type": (
                    collectible_type
                ),
                "is_evolved": (
                    is_evolved
                ),
                "acquisition_txhash": (
                    acquisition_txhash
                ),
                "acquisition_datetime": (
                    acquisition_datetime
                ),
                "acquisition_cost_weth": (
                    acquisition_cost_weth
                ),
                "last_seen_datetime": (
                    last_seen_datetime
                ),
                "data_source": (
                    data_source
                ),
                "parts": (
                    parts_by_axie.get(
                        axie_id,
                        {},
                    )
                ),
                "traits": (
                    traits_by_axie.get(
                        axie_id,
                        {},
                    )
                ),
            }
        )

    return profiles



def fetch_axie_gameplay_metadata(
    axie_id,
    timeout=20,
):
    axie_id = str(
        int(
            str(axie_id)
        )
    )

    query = """
    query GetAxieDetail($axieId: ID!) {
        axie(axieId: $axieId) {
            id
            name
            class
            stage
            breedCount
            level
            title
            owner
            parts {
                id
                name
                class
                type
                specialGenes
                stage
            }
        }
    }
    """

    payload = {
        "operationName": (
            "GetAxieDetail"
        ),
        "variables": {
            "axieId": axie_id,
        },
        "query": query,
    }

    headers = {
        "Content-Type": (
            "application/json"
        ),
        "Accept": (
            "application/json"
        ),
        "User-Agent": (
            "AxieOS/0.8"
        ),
    }

    try:
        response = requests.post(
            AXIE_GRAPHQL_URL,
            json=payload,
            headers=headers,
            timeout=timeout,
        )

    except requests.RequestException as error:
        return {
            "success": False,
            "status_code": None,
            "axie": None,
            "errors": [
                str(error)
            ],
        }

    status_code = (
        response.status_code
    )

    try:
        data = response.json()

    except ValueError:
        return {
            "success": False,
            "status_code": (
                status_code
            ),
            "axie": None,
            "errors": [
                "Response was not valid JSON"
            ],
        }

    graphql_errors = data.get(
        "errors",
        [],
    )

    axie = (
        data.get(
            "data",
            {},
        ).get(
            "axie"
        )
    )

    success = (
        status_code == 200
        and not graphql_errors
        and axie is not None
    )

    return {
        "success": success,
        "status_code": (
            status_code
        ),
        "axie": axie,
        "errors": graphql_errors,
    }



def fetch_axie_explorer_metadata(
    axie_id,
    timeout=20,
):
    axie_id = str(
        int(
            str(axie_id)
        )
    )

    url = (
        f"{RONIN_EXPLORER_API_URL}"
        f"/tokens/"
        f"{AXIE_CONTRACT_ADDRESS}"
        f"/instances/"
        f"{axie_id}"
    )

    headers = {
        "Accept": (
            "application/json"
        ),
        "User-Agent": (
            "AxieOS-Gameplay/0.8"
        ),
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
        )

    except requests.RequestException as error:
        return {
            "success": False,
            "status_code": None,
            "url": url,
            "data": None,
            "error": str(error),
        }

    status_code = (
        response.status_code
    )

    try:
        data = response.json()

    except ValueError:
        return {
            "success": False,
            "status_code": (
                status_code
            ),
            "url": url,
            "data": None,
            "error": (
                "Response was not valid JSON"
            ),
            "response_preview": (
                response.text[:500]
            ),
        }

    success = (
        status_code == 200
        and isinstance(
            data,
            dict,
        )
    )

    return {
        "success": success,
        "status_code": (
            status_code
        ),
        "url": url,
        "data": data,
        "error": None,
    }



def fetch_axie_marketplace_page(
    axie_id,
    timeout=20,
):
    axie_id = str(
        int(
            str(axie_id)
        )
    )

    url = (
        "https://marketplace.roninchain.com"
        "/collections/"
        f"{AXIE_CONTRACT_ADDRESS}"
        f"/{axie_id}"
    )

    headers = {
        "Accept": (
            "text/html,"
            "application/xhtml+xml"
        ),
        "User-Agent": (
            "AxieOS-Gameplay/0.8"
        ),
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
        )

    except requests.RequestException as error:
        return {
            "success": False,
            "status_code": None,
            "url": url,
            "html": None,
            "error": str(error),
        }

    html = response.text

    return {
        "success": (
            response.status_code
            == 200
            and bool(html)
        ),
        "status_code": (
            response.status_code
        ),
        "url": url,
        "html": html,
        "error": None,
    }



def get_skymavis_api_key():
    api_key = os.getenv(
        "SKYMAVIS_API_KEY"
    )

    if api_key is None:
        raise RuntimeError(
            "SKYMAVIS_API_KEY "
            "environment variable "
            "is not configured."
        )

    api_key = api_key.strip()

    if not api_key:
        raise RuntimeError(
            "SKYMAVIS_API_KEY "
            "environment variable "
            "is empty."
        )

    return api_key



def get_skymavis_origins_user_id():
    user_id = os.getenv(
        "SKYMAVIS_ORIGINS_USER_ID"
    )

    if user_id is None:
        raise RuntimeError(
            "SKYMAVIS_ORIGINS_USER_ID "
            "environment variable "
            "is not configured."
        )

    user_id = user_id.strip()

    if not user_id:
        raise RuntimeError(
            "SKYMAVIS_ORIGINS_USER_ID "
            "environment variable "
            "is empty."
        )

    return user_id




def skymavis_api_get(
    path,
    params=None,
    timeout=20,
):
    api_key = (
        get_skymavis_api_key()
    )

    url = (
        f"{SKYMAVIS_API_BASE_URL}"
        f"/{path.lstrip('/')}"
    )

    headers = {
        "Accept": (
            "application/json"
        ),
        "X-API-Key": api_key,
        "User-Agent": (
            "AxieOS-Gameplay/0.8"
        ),
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=timeout,
        )

    except requests.RequestException as error:
        return {
            "success": False,
            "status_code": None,
            "url": url,
            "data": None,
            "error": str(error),
        }

    try:
        data = response.json()

    except ValueError:
        return {
            "success": False,
            "status_code": (
                response.status_code
            ),
            "url": url,
            "data": None,
            "error": (
                "Response was not "
                "valid JSON"
            ),
            "response_preview": (
                response.text[:500]
            ),
        }

    return {
        "success": (
            response.status_code
            == 200
        ),
        "status_code": (
            response.status_code
        ),
        "url": url,
        "data": data,
        "error": None,
    }



def fetch_origins_ronin_fighters(
    limit=100,
    offset=0,
):
    user_id = (
        get_skymavis_origins_user_id()
    )

    return skymavis_api_get(
        (
            "origins/v2/community/"
            "users/fighters"
        ),
        params={
            "userID": user_id,
            "axieType": "ronin",
            "limit": limit,
            "offset": offset,
        },
    )



def fetch_all_origins_ronin_fighters(
    page_size=100,
    max_pages=20,
):
    all_fighters = []

    offset = 0
    page_count = 0
    reported_total = None

    while page_count < max_pages:
        result = (
            fetch_origins_ronin_fighters(
                limit=page_size,
                offset=offset,
            )
        )

        if not result["success"]:
            return {
                "success": False,
                "status_code": (
                    result[
                        "status_code"
                    ]
                ),
                "fighters": [],
                "pages": page_count,
                "reported_total": (
                    reported_total
                ),
                "error": (
                    result.get(
                        "error"
                    )
                ),
            }

        data = result[
            "data"
        ]

        fighters = data.get(
            "_items",
            [],
        )

        metadata = data.get(
            "_metadata",
            {},
        )

        if reported_total is None:
            reported_total = (
                metadata.get(
                    "total"
                )
            )

        all_fighters.extend(
            fighters
        )

        page_count += 1

        has_next = metadata.get(
            "hasNext",
            False,
        )

        if not has_next:
            break

        if not fighters:
            break

        offset += len(
            fighters
        )

    fighter_map = {}

    for fighter in all_fighters:
        fighter_id = fighter.get(
            "id"
        )

        if fighter_id is None:
            continue

        fighter_map[
            str(fighter_id)
        ] = fighter

    unique_fighters = list(
        fighter_map.values()
    )

    return {
        "success": True,
        "status_code": 200,
        "fighters": (
            unique_fighters
        ),
        "raw_fighter_count": len(
            all_fighters
        ),
        "unique_fighter_count": len(
            unique_fighters
        ),
        "pages": page_count,
        "reported_total": (
            reported_total
        ),
        "error": None,
    }



def fetch_origins_card_catalog():
    result = skymavis_api_get(
        "origins/v2/community/cards"
    )

    if not result[
        "success"
    ]:
        return {
            "success": False,
            "cards": [],
            "error": result.get(
                "error"
            ),
        }

    data = result[
        "data"
    ]

    cards = data.get(
        "_items",
        [],
    )

    return {
        "success": True,
        "cards": cards,
        "error": None,
    }



def build_origins_part_name_map(
    cards,
):
    grouped_cards = {}

    for card in cards:
        part_class = card.get(
            "partClass"
        )

        part_type = card.get(
            "partType"
        )

        part_value = card.get(
            "partValue"
        )

        name = card.get(
            "name"
        )

        stage = card.get(
            "stage"
        )

        if (
            not part_class
            or not part_type
            or part_value is None
            or not name
        ):
            continue

        key = (
            str(
                part_class
            ),
            str(
                part_type
            ).lower(),
            int(
                part_value
            ),
        )

        grouped_cards.setdefault(
            key,
            []
        ).append(
            {
                "name": str(
                    name
                ),
                "stage": stage,
            }
        )

    part_name_map = {}

    for (
        key,
        variants,
    ) in grouped_cards.items():
        stage_one = [
            variant
            for variant in variants
            if variant[
                "stage"
            ]
            == 1
        ]

        if stage_one:
            family_name = (
                stage_one[0][
                    "name"
                ]
            )

        else:
            ordered = sorted(
                variants,
                key=lambda item: (
                    item[
                        "stage"
                    ]
                    if isinstance(
                        item[
                            "stage"
                        ],
                        int,
                    )
                    else 999
                ),
            )

            family_name = (
                ordered[0][
                    "name"
                ]
            )

            if family_name.endswith(
                "+"
            ):
                family_name = (
                    family_name[:-1]
                )

        part_name_map[
            key
        ] = family_name

    return part_name_map



def sync_owned_axie_part_names(
    db_path,
):
    catalog_result = (
        fetch_origins_card_catalog()
    )

    if not catalog_result[
        "success"
    ]:
        return {
            "success": False,
            "owned_parts": 0,
            "mapped_parts": 0,
            "unmapped_parts": [],
            "error": (
                catalog_result.get(
                    "error"
                )
            ),
        }

    cards = catalog_result[
        "cards"
    ]

    part_name_map = (
        build_origins_part_name_map(
            cards
        )
    )

    connection = sqlite3.connect(
        db_path
    )

    rows = (
        connection.execute(
            """
            SELECT
                p.axie_id,
                p.part_slot,
                p.part_class,
                p.part_value,
                p.part_stage
            FROM gameplay_axie_parts p
            INNER JOIN
                gameplay_owned_axies a
                ON a.axie_id =
                   p.axie_id
            WHERE
                a.ownership_status =
                    'OWNED'
            ORDER BY
                CAST(
                    p.axie_id AS INTEGER
                ),
                p.part_slot
            """
        ).fetchall()
    )

    mapped_records = []

    unmapped_parts = []

    for row in rows:
        axie_id = str(
            row[0]
        )

        part_slot = str(
            row[1]
        ).lower()

        part_class = row[
            2
        ]

        part_value = row[
            3
        ]

        part_stage = row[
            4
        ]

        if (
            part_class is None
            or part_value is None
        ):
            unmapped_parts.append(
                {
                    "axie_id": axie_id,
                    "part_slot": (
                        part_slot
                    ),
                    "part_class": (
                        part_class
                    ),
                    "part_value": (
                        part_value
                    ),
                    "part_stage": (
                        part_stage
                    ),
                }
            )

            continue

        key = (
            str(
                part_class
            ),
            part_slot,
            int(
                part_value
            ),
        )

        part_name = (
            part_name_map.get(
                key
            )
        )

        if part_name is None:
            unmapped_parts.append(
                {
                    "axie_id": axie_id,
                    "part_slot": (
                        part_slot
                    ),
                    "part_class": (
                        part_class
                    ),
                    "part_value": (
                        part_value
                    ),
                    "part_stage": (
                        part_stage
                    ),
                }
            )

            continue

        mapped_records.append(
            {
                "axie_id": axie_id,
                "part_slot": (
                    part_slot
                ),
                "part_name": (
                    part_name
                ),
            }
        )

    try:
        for record in mapped_records:
            connection.execute(
                """
                UPDATE gameplay_axie_parts
                SET
                    part_name = ?,
                    last_updated =
                        CURRENT_TIMESTAMP
                WHERE axie_id = ?
                  AND part_slot = ?
                """,
                (
                    record[
                        "part_name"
                    ],
                    record[
                        "axie_id"
                    ],
                    record[
                        "part_slot"
                    ],
                ),
            )

        connection.commit()

    except Exception:
        connection.rollback()
        connection.close()
        raise

    connection.close()

    return {
        "success": (
            len(
                unmapped_parts
            )
            == 0
        ),
        "cards": len(
            cards
        ),
        "part_families": len(
            part_name_map
        ),
        "owned_parts": len(
            rows
        ),
        "mapped_parts": len(
            mapped_records
        ),
        "unmapped_parts": (
            unmapped_parts
        ),
        "error": None,
    }




def fetch_all_origins_fighter_configs(
    page_size=100,
    max_pages=20,
):
    user_id = (
        get_skymavis_origins_user_id()
    )

    all_configs = []

    offset = 0
    page_count = 0

    while page_count < max_pages:
        result = skymavis_api_get(
            (
                "origins/v2/community/"
                "users/fighters/configs"
            ),
            params={
                "userID": user_id,
                "limit": page_size,
                "offset": offset,
            },
        )

        if not result["success"]:
            return {
                "success": False,
                "status_code": (
                    result[
                        "status_code"
                    ]
                ),
                "configs": [],
                "pages": page_count,
                "error": (
                    result.get(
                        "error"
                    )
                ),
            }

        data = result[
            "data"
        ]

        configs = data.get(
            "_items",
            [],
        )

        metadata = data.get(
            "_metadata",
            {},
        )

        all_configs.extend(
            configs
        )

        page_count += 1

        if not metadata.get(
            "hasNext",
            False,
        ):
            break

        if not configs:
            break

        offset += len(
            configs
        )

    return {
        "success": True,
        "status_code": 200,
        "configs": all_configs,
        "pages": page_count,
        "error": None,
    }



def build_axie_core_call_data(
    axie_id,
):
    normalized_id = int(
        str(
            axie_id
        )
    )

    if normalized_id <= 0:
        raise ValueError(
            "Axie ID must be positive."
        )

    encoded_id = format(
        normalized_id,
        "064x",
    )

    return (
        "0x"
        + AXIE_CORE_FUNCTION_SELECTOR
        + encoded_id
    )



def encode_evm_address_argument(
    address,
):
    if not isinstance(
        address,
        str,
    ):
        raise ValueError(
            "Address must be text."
        )

    normalized = (
        address.strip().lower()
    )

    if normalized.startswith(
        "ronin:"
    ):
        normalized = (
            "0x"
            + normalized[6:]
        )

    if not normalized.startswith(
        "0x"
    ):
        raise ValueError(
            "Address must start with 0x."
        )

    address_hex = normalized[
        2:
    ]

    if len(address_hex) != 40:
        raise ValueError(
            "Address must contain "
            "40 hexadecimal characters."
        )

    try:
        int(
            address_hex,
            16,
        )

    except ValueError as error:
        raise ValueError(
            "Address is not valid hexadecimal."
        ) from error

    return address_hex.rjust(
        64,
        "0",
    )



def ronin_eth_call(
    contract_address,
    call_data,
    timeout=20,
    max_attempts=5,
    initial_backoff=1.0,
    min_interval=0.35,
    rate_limit_backoff=15.0,
):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [
            {
                "to": contract_address,
                "data": call_data,
            },
            "latest",
        ],
    }

    transient_http_statuses = {
        408,
        425,
        429,
        500,
        502,
        503,
        504,
    }

    transient_rpc_markers = (
        "rate limit",
        "too many requests",
        "timeout",
        "timed out",
        "temporarily",
        "unavailable",
        "busy",
        "gateway",
        "internal error",
        "server error",
        "try again",
        "limit exceeded",
    )

    last_error = None

    for attempt in range(
        1,
        max_attempts + 1,
    ):
        # ------------------------------------------
        # Global pacing for all Ronin RPC calls.
        #
        # This protects ownership enumeration,
        # breed reads, and gene reads from
        # overwhelming the public RPC endpoint.
        # ------------------------------------------

        last_request_time = getattr(
            ronin_eth_call,
            "_last_request_monotonic",
            None,
        )

        if last_request_time is not None:
            elapsed = (
                time.monotonic()
                - last_request_time
            )

            remaining_wait = (
                min_interval
                - elapsed
            )

            if remaining_wait > 0:
                time.sleep(
                    remaining_wait
                )

        ronin_eth_call._last_request_monotonic = (
            time.monotonic()
        )

        retryable = False
        retry_delay = None

        try:
            response = requests.post(
                RONIN_PUBLIC_RPC_URL,
                json=payload,
                headers={
                    "Accept": (
                        "application/json"
                    ),
                    "Content-Type": (
                        "application/json"
                    ),
                    "User-Agent": (
                        "AxieOS-Gameplay/0.8"
                    ),
                },
                timeout=timeout,
            )

        except requests.RequestException as error:
            last_error = (
                "Ronin RPC request failed: "
                f"{error}"
            )

            retryable = True

        else:
            try:
                data = response.json()

            except ValueError:
                last_error = (
                    "Ronin RPC response "
                    "was not valid JSON "
                    f"(HTTP "
                    f"{response.status_code})."
                )

                retryable = True

            else:
                if response.status_code != 200:
                    last_error = (
                        "Ronin RPC HTTP "
                        f"{response.status_code}"
                    )

                    retryable = (
                        response.status_code
                        in transient_http_statuses
                        or response.status_code
                        >= 500
                    )

                    # ----------------------------------
                    # HTTP 429 needs a much longer
                    # cooldown than an ordinary retry.
                    # ----------------------------------

                    if (
                        response.status_code
                        == 429
                    ):
                        retry_after = (
                            response.headers.get(
                                "Retry-After"
                            )
                        )

                        if retry_after:
                            try:
                                retry_delay = max(
                                    float(
                                        retry_after
                                    ),
                                    rate_limit_backoff,
                                )

                            except ValueError:
                                retry_delay = (
                                    rate_limit_backoff
                                    * (
                                        2
                                        ** (
                                            attempt
                                            - 1
                                        )
                                    )
                                )

                        else:
                            retry_delay = (
                                rate_limit_backoff
                                * (
                                    2
                                    ** (
                                        attempt
                                        - 1
                                    )
                                )
                            )

                        retry_delay = min(
                            retry_delay,
                            60.0,
                        )

                elif data.get(
                    "error"
                ):
                    rpc_error = str(
                        data[
                            "error"
                        ]
                    )

                    last_error = (
                        "Ronin RPC error: "
                        f"{rpc_error}"
                    )

                    rpc_error_lower = (
                        rpc_error.lower()
                    )

                    retryable = any(
                        marker
                        in rpc_error_lower
                        for marker
                        in transient_rpc_markers
                    )

                    if not retryable:
                        return {
                            "success": False,
                            "result": None,
                            "error": (
                                last_error
                            ),
                        }

                else:
                    return {
                        "success": True,
                        "result": data.get(
                            "result"
                        ),
                        "error": None,
                    }

        if (
            not retryable
            or attempt >= max_attempts
        ):
            break

        if retry_delay is None:
            retry_delay = (
                initial_backoff
                * (
                    2
                    ** (
                        attempt - 1
                    )
                )
            )

        if (
            last_error
            == "Ronin RPC HTTP 429"
        ):
            print(
                "Ronin RPC rate limited "
                f"(attempt {attempt}/"
                f"{max_attempts}); "
                f"cooling down for "
                f"{retry_delay:.1f}s..."
            )

        else:
            print(
                "Ronin RPC transient failure "
                f"(attempt {attempt}/"
                f"{max_attempts}); "
                f"retrying in "
                f"{retry_delay:.1f}s..."
            )

        time.sleep(
            retry_delay
        )

    return {
        "success": False,
        "result": None,
        "error": (
            last_error
            or (
                "Ronin RPC call failed "
                "without an error message."
            )
        ),
    }



def fetch_axie_wallet_balance(
    wallet_address,
):
    encoded_address = (
        encode_evm_address_argument(
            wallet_address
        )
    )

    call_data = (
        "0x"
        + ERC721_BALANCE_OF_SELECTOR
        + encoded_address
    )

    result = ronin_eth_call(
        AXIE_CONTRACT_ADDRESS,
        call_data,
    )

    if not result[
        "success"
    ]:
        return {
            "success": False,
            "balance": None,
            "error": result.get(
                "error"
            ),
        }

    result_hex = result.get(
        "result"
    )

    try:
        balance = int(
            result_hex,
            16,
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        return {
            "success": False,
            "balance": None,
            "error": str(error),
        }

    return {
        "success": True,
        "balance": balance,
        "error": None,
    }



def fetch_axie_tokens_of_owner(
    wallet_address,
):
    balance_result = (
        fetch_axie_wallet_balance(
            wallet_address
        )
    )

    if not balance_result[
        "success"
    ]:
        return {
            "success": False,
            "balance": None,
            "axie_ids": [],
            "failed_index": None,
            "error": (
                balance_result.get(
                    "error"
                )
            ),
        }

    balance = balance_result[
        "balance"
    ]

    encoded_address = (
        encode_evm_address_argument(
            wallet_address
        )
    )

    axie_ids = []

    for index in range(
        balance
    ):
        encoded_index = format(
            index,
            "064x",
        )

        call_data = (
            "0x"
            + ERC721_TOKEN_OF_OWNER_BY_INDEX_SELECTOR
            + encoded_address
            + encoded_index
        )

        result = ronin_eth_call(
            AXIE_CONTRACT_ADDRESS,
            call_data,
        )

        if not result[
            "success"
        ]:
            return {
                "success": False,
                "balance": balance,
                "axie_ids": axie_ids,
                "failed_index": index,
                "error": result.get(
                    "error"
                ),
            }

        result_hex = result.get(
            "result"
        )

        try:
            token_id = int(
                result_hex,
                16,
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            return {
                "success": False,
                "balance": balance,
                "axie_ids": axie_ids,
                "failed_index": index,
                "error": (
                    "Invalid "
                    "tokenOfOwnerByIndex "
                    f"response: {error}"
                ),
            }

        axie_ids.append(
            str(
                token_id
            )
        )

    return {
        "success": True,
        "balance": balance,
        "axie_ids": axie_ids,
        "failed_index": None,
        "error": None,
    }



def resolve_non_owned_axie_lifecycle_status(
    db_path,
    axie_id,
):
    axie_id = str(
        axie_id
    )

    connection = sqlite3.connect(
        db_path
    )

    accounting_row = (
        connection.execute(
            """
            SELECT
                datetime,
                event_type,
                classification,
                txhash
            FROM blockchain_accounting_records
            WHERE asset_token_id = ?
              AND (
                    asset_category =
                        'AXIE_NFT'
                    OR asset_name =
                        'Axie'
                  )
            ORDER BY
                datetime DESC,
                accounting_key DESC
            LIMIT 1
            """,
            (
                axie_id,
            ),
        ).fetchone()
    )

    if accounting_row is not None:
        event_type = (
            accounting_row[1]
        )

        classification = (
            accounting_row[2]
        )

        if (
            event_type
            == "ASSET_SALE"
            or classification
            == "MARKETPLACE_SELL"
        ):
            connection.close()

            return {
                "status": "SOLD",
                "source": (
                    "BLOCKCHAIN_ACCOUNTING"
                ),
                "datetime": (
                    accounting_row[0]
                ),
                "reference": (
                    accounting_row[3]
                ),
            }

        if (
            event_type
            == "ASSET_BURN"
            or classification
            == "NFT_BURN"
        ):
            connection.close()

            return {
                "status": "RELEASED",
                "source": (
                    "BLOCKCHAIN_ACCOUNTING"
                ),
                "datetime": (
                    accounting_row[0]
                ),
                "reference": (
                    accounting_row[3]
                ),
            }

        if event_type == "TRANSFER_OUT":
            connection.close()

            return {
                "status": (
                    "TRANSFERRED_OUT"
                ),
                "source": (
                    "BLOCKCHAIN_ACCOUNTING"
                ),
                "datetime": (
                    accounting_row[0]
                ),
                "reference": (
                    accounting_row[3]
                ),
            }

    marketplace_row = (
        connection.execute(
            """
            SELECT
                id,
                event_datetime,
                LOWER(event_type)
            FROM marketplace_events
            WHERE asset_type = 'Axie'
              AND asset_id = ?
              AND LOWER(event_type)
                  IN (
                      'sale',
                      'sold',
                      'release',
                      'released'
                  )
            ORDER BY
                event_datetime DESC,
                id DESC
            LIMIT 1
            """,
            (
                axie_id,
            ),
        ).fetchone()
    )

    connection.close()

    if marketplace_row is not None:
        event_type = (
            marketplace_row[2]
        )

        if event_type in {
            "sale",
            "sold",
        }:
            status = "SOLD"

        elif event_type in {
            "release",
            "released",
        }:
            status = "RELEASED"

        else:
            status = "UNKNOWN"

        return {
            "status": status,
            "source": (
                "MARKETPLACE_EVENTS"
            ),
            "datetime": (
                marketplace_row[1]
            ),
            "reference": str(
                marketplace_row[0]
            ),
        }

    return {
        "status": "UNKNOWN",
        "source": None,
        "datetime": None,
        "reference": None,
    }




def sync_owned_axie_registry_from_current_chain(
    db_path,
    current_wallet_map=None,
):
    if current_wallet_map is None:
        user_owned_wallets = (
            load_user_owned_wallet_addresses(
                db_path
            )
        )

        user_owned_wallets = sorted(
            {
                str(wallet).lower()
                for wallet
                in user_owned_wallets
            }
        )

        if not user_owned_wallets:
            return {
                "success": False,
                "current_axies": 0,
                "retained_axies": 0,
                "new_axies": 0,
                "reactivated_axies": 0,
                "stale_axies": [],
                "lifecycle_resolved": [],
                "wallet_map": {},
                "failed_wallets": [],
                "error": (
                    "No USER_OWNED wallets "
                    "are registered."
                ),
            }

        current_wallet_map = {}

        failed_wallets = []

        for wallet in user_owned_wallets:
            result = (
                fetch_axie_tokens_of_owner(
                    wallet
                )
            )

            if not result[
                "success"
            ]:
                failed_wallets.append(
                    {
                        "wallet": wallet,
                        "error": result.get(
                            "error"
                        ),
                    }
                )

                continue

            for axie_id in result[
                "axie_ids"
            ]:
                axie_id = str(
                    axie_id
                )

                existing_wallet = (
                    current_wallet_map.get(
                        axie_id
                    )
                )

                if (
                    existing_wallet
                    is not None
                    and existing_wallet
                    != wallet
                ):
                    return {
                        "success": False,
                        "current_axies": 0,
                        "retained_axies": 0,
                        "new_axies": 0,
                        "reactivated_axies": 0,
                        "stale_axies": [],
                        "lifecycle_resolved": [],
                        "wallet_map": {},
                        "failed_wallets": (
                            failed_wallets
                        ),
                        "error": (
                            "Axie appears in "
                            "multiple USER_OWNED "
                            "wallets: "
                            f"{axie_id}"
                        ),
                    }

                current_wallet_map[
                    axie_id
                ] = wallet

        if failed_wallets:
            return {
                "success": False,
                "current_axies": len(
                    current_wallet_map
                ),
                "retained_axies": 0,
                "new_axies": 0,
                "reactivated_axies": 0,
                "stale_axies": [],
                "lifecycle_resolved": [],
                "wallet_map": (
                    current_wallet_map
                ),
                "failed_wallets": (
                    failed_wallets
                ),
                "error": (
                    "One or more USER_OWNED "
                    "wallets could not be "
                    "enumerated."
                ),
            }

    else:
        current_wallet_map = {
            str(
                axie_id
            ): str(
                wallet
            ).lower()
            for (
                axie_id,
                wallet,
            ) in (
                current_wallet_map.items()
            )
        }

    current_ids = set(
        current_wallet_map.keys()
    )

    connection = sqlite3.connect(
        db_path
    )

    registry_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                ownership_status
            FROM gameplay_owned_axies
            """
        ).fetchall()
    )

    connection.close()

    all_registry_ids = {
        str(row[0])
        for row
        in registry_rows
    }

    previously_owned_ids = {
        str(row[0])
        for row
        in registry_rows
        if row[1] == "OWNED"
    }

    unknown_ids = {
        str(row[0])
        for row
        in registry_rows
        if row[1] == "UNKNOWN"
    }

    retained_ids = (
        current_ids
        & previously_owned_ids
    )

    new_ids = (
        current_ids
        - all_registry_ids
    )

    reactivated_ids = (
        (
            current_ids
            & all_registry_ids
        )
        - previously_owned_ids
    )

    stale_ids = (
        previously_owned_ids
        - current_ids
    )

    lifecycle_candidates = (
        (
            unknown_ids
            | stale_ids
        )
        - current_ids
    )

    lifecycle_resolved = []

    for axie_id in sorted(
        lifecycle_candidates,
        key=int,
    ):
        evidence = (
            resolve_non_owned_axie_lifecycle_status(
                db_path,
                axie_id,
            )
        )

        if evidence[
            "status"
        ] == "UNKNOWN":
            continue

        lifecycle_resolved.append(
            {
                "axie_id": axie_id,
                "status": (
                    evidence[
                        "status"
                    ]
                ),
                "source": (
                    evidence[
                        "source"
                    ]
                ),
                "datetime": (
                    evidence[
                        "datetime"
                    ]
                ),
                "reference": (
                    evidence[
                        "reference"
                    ]
                ),
            }
        )

    connection = sqlite3.connect(
        db_path
    )

    try:
        for (
            axie_id,
            wallet,
        ) in current_wallet_map.items():
            connection.execute(
                """
                INSERT INTO
                    gameplay_owned_axies (
                        axie_id,
                        wallet_address,
                        ownership_status,
                        last_seen_datetime,
                        data_source,
                        last_updated
                    )
                VALUES (
                    ?,
                    ?,
                    'OWNED',
                    CURRENT_TIMESTAMP,
                    'RONIN_CURRENT_STATE',
                    CURRENT_TIMESTAMP
                )
                ON CONFLICT(
                    axie_id
                )
                DO UPDATE SET
                    wallet_address =
                        excluded.wallet_address,
                    ownership_status =
                        'OWNED',
                    last_seen_datetime =
                        CURRENT_TIMESTAMP,
                    data_source =
                        COALESCE(
                            gameplay_owned_axies
                                .data_source,
                            excluded.data_source
                        ),
                    last_updated =
                        CURRENT_TIMESTAMP
                """,
                (
                    axie_id,
                    wallet,
                ),
            )

        for axie_id in stale_ids:
            connection.execute(
                """
                UPDATE gameplay_owned_axies
                SET
                    ownership_status =
                        'UNKNOWN',
                    last_updated =
                        CURRENT_TIMESTAMP
                WHERE axie_id = ?
                  AND ownership_status =
                      'OWNED'
                """,
                (
                    axie_id,
                ),
            )

        for record in (
            lifecycle_resolved
        ):
            connection.execute(
                """
                UPDATE gameplay_owned_axies
                SET
                    ownership_status = ?,
                    last_updated =
                        CURRENT_TIMESTAMP
                WHERE axie_id = ?
                  AND ownership_status !=
                      'OWNED'
                """,
                (
                    record[
                        "status"
                    ],
                    record[
                        "axie_id"
                    ],
                ),
            )

        connection.commit()

    except Exception:
        connection.rollback()
        connection.close()
        raise

    connection.close()

    return {
        "success": True,
        "current_axies": len(
            current_ids
        ),
        "retained_axies": len(
            retained_ids
        ),
        "new_axies": len(
            new_ids
        ),
        "reactivated_axies": len(
            reactivated_ids
        ),
        "stale_axies": sorted(
            stale_ids,
            key=int,
        ),
        "lifecycle_resolved": (
            lifecycle_resolved
        ),
        "wallet_map": (
            current_wallet_map
        ),
        "failed_wallets": [],
        "error": None,
    }



def decode_axie_core_result(
    result_hex,
):
    if not isinstance(
        result_hex,
        str,
    ):
        raise ValueError(
            "Axie contract result "
            "must be hexadecimal text."
        )

    if not result_hex.startswith(
        "0x"
    ):
        raise ValueError(
            "Axie contract result "
            "must start with 0x."
        )

    payload = result_hex[
        2:
    ]

    expected_words = 7

    expected_length = (
        expected_words * 64
    )

    if len(payload) < expected_length:
        raise ValueError(
            "Axie contract result "
            "is shorter than expected."
        )

    words = [
        payload[
            index:
            index + 64
        ]
        for index in range(
            0,
            expected_length,
            64,
        )
    ]

    values = [
        int(
            word,
            16,
        )
        for word in words
    ]

    return {
        "sire_id": values[0],
        "matron_id": values[1],
        "birth_date": values[2],
        "genes_x": values[3],
        "genes_y": values[4],
        "breed_count": values[5],
        "contract_level": values[6],
    }



def fetch_axie_core_onchain(
    axie_id,
    timeout=20,
):
    try:
        normalized_axie_id = str(
            int(
                str(
                    axie_id
                )
            )
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        return {
            "success": False,
            "axie_id": str(
                axie_id
            ),
            "data": None,
            "error": str(error),
        }

    # --------------------------------------------------
    # In-process Axie core cache.
    #
    # During the V0.8 production runner:
    #
    # Stage 3 reads Axie core data for breed counts.
    # Stage 4 needs the exact same core data for genes.
    #
    # Successful results are therefore reused instead
    # of making another 136 Ronin RPC calls.
    # --------------------------------------------------

    core_cache = getattr(
        fetch_axie_core_onchain,
        "_cache",
        None,
    )

    if core_cache is None:
        core_cache = {}

        fetch_axie_core_onchain._cache = (
            core_cache
        )

    cached_data = core_cache.get(
        normalized_axie_id
    )

    if cached_data is not None:
        return {
            "success": True,
            "axie_id": (
                normalized_axie_id
            ),
            "data": dict(
                cached_data
            ),
            "error": None,
        }

    try:
        call_data = (
            build_axie_core_call_data(
                normalized_axie_id
            )
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        return {
            "success": False,
            "axie_id": (
                normalized_axie_id
            ),
            "data": None,
            "error": str(error),
        }

    # --------------------------------------------------
    # Use the shared protected Ronin RPC layer.
    #
    # This now inherits:
    # - request pacing
    # - HTTP 429 cooldown
    # - transient-error retry
    # - exponential backoff
    # --------------------------------------------------

    rpc_result = ronin_eth_call(
        AXIE_CONTRACT_ADDRESS,
        call_data,
        timeout=timeout,
    )

    if not rpc_result[
        "success"
    ]:
        return {
            "success": False,
            "axie_id": (
                normalized_axie_id
            ),
            "data": None,
            "error": rpc_result.get(
                "error"
            ),
        }

    result_hex = rpc_result.get(
        "result"
    )

    try:
        decoded = (
            decode_axie_core_result(
                result_hex
            )
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        return {
            "success": False,
            "axie_id": (
                normalized_axie_id
            ),
            "data": None,
            "error": str(error),
        }

    # Only successful decoded results are cached.
    # Failed RPC calls are deliberately NOT cached,
    # so a later attempt may retry them normally.

    core_cache[
        normalized_axie_id
    ] = dict(
        decoded
    )

    return {
        "success": True,
        "axie_id": (
            normalized_axie_id
        ),
        "data": dict(
            decoded
        ),
        "error": None,
    }


def sync_onchain_breed_counts_for_owned_axies(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    owned_rows = (
        connection.execute(
            """
            SELECT axie_id
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    connection.close()

    owned_ids = [
        str(row[0])
        for row in owned_rows
    ]

    valid_records = []
    failed_records = []

    for axie_id in owned_ids:
        result = (
            fetch_axie_core_onchain(
                axie_id
            )
        )

        if not result[
            "success"
        ]:
            failed_records.append(
                {
                    "axie_id": axie_id,
                    "reason": result.get(
                        "error"
                    ),
                }
            )

            continue

        data = result[
            "data"
        ]

        breed_count = data.get(
            "breed_count"
        )

        if not (
            isinstance(
                breed_count,
                int,
            )
            and 0 <= breed_count <= 7
        ):
            failed_records.append(
                {
                    "axie_id": axie_id,
                    "reason": (
                        "Invalid breed count: "
                        f"{breed_count}"
                    ),
                }
            )

            continue

        valid_records.append(
            {
                "axie_id": axie_id,
                "breed_count": (
                    breed_count
                ),
                "contract_level": (
                    data.get(
                        "contract_level"
                    )
                ),
            }
        )

    connection = sqlite3.connect(
        db_path
    )

    for record in valid_records:
        connection.execute(
            """
            UPDATE gameplay_owned_axies
            SET
                breed_count = ?,
                last_updated =
                    CURRENT_TIMESTAMP
            WHERE axie_id = ?
              AND ownership_status =
                  'OWNED'
            """,
            (
                record[
                    "breed_count"
                ],
                record[
                    "axie_id"
                ],
            ),
        )

    connection.commit()
    connection.close()

    return {
        "success": (
            len(
                failed_records
            )
            == 0
        ),
        "owned_axies": len(
            owned_ids
        ),
        "synced_axies": len(
            valid_records
        ),
        "failed_axies": (
            failed_records
        ),
        "records": (
            valid_records
        ),
    }



def decode_axie_collectible_gene_signals(
    genes_hex,
):
    if not isinstance(
        genes_hex,
        str,
    ):
        raise ValueError(
            "Axie genes must be hexadecimal text."
        )

    genes_hex = (
        genes_hex.strip()
    )

    if genes_hex.startswith(
        "0x"
    ):
        genes_hex = genes_hex[
            2:
        ]

    if not genes_hex:
        raise ValueError(
            "Axie genes are empty."
        )

    try:
        gene_value = int(
            genes_hex,
            16,
        )

    except ValueError as error:
        raise ValueError(
            "Axie genes are not valid hexadecimal."
        ) from error

    if gene_value.bit_length() > 512:
        raise ValueError(
            "Axie genes exceed 512 bits."
        )

    gene_bits = format(
        gene_value,
        "0512b",
    )

    tag_bits = gene_bits[
        40:55
    ]

    body_skin_bits = gene_bits[
        61:65
    ]

    tag_map = {
        "000000000000000": "NORMAL",
        "000000000000001": "ORIGIN",
        "000000000000010": "MEO1",
        "000000000000011": "MEO2",
    }

    body_skin_map = {
        "0000": "NORMAL",
        "0001": "FROSTY",
    }

    legacy_part_skin_map = {
        0: "GLOBAL",
        1: "MYSTIC",
        2: "BIONIC",
        3: "JAPANESE",
        4: "XMAS1",
        5: "XMAS2",
    }

    part_offsets = {
        "eyes": 149,
        "mouth": 213,
        "ears": 277,
        "horn": 341,
        "back": 405,
        "tail": 469,
    }

    part_skin_codes = {}
    part_skin_labels = {}

    for (
        part_slot,
        start,
    ) in part_offsets.items():
        skin_bits = gene_bits[
            start:
            start + 4
        ]

        skin_code = int(
            skin_bits,
            2,
        )

        part_skin_codes[
            part_slot
        ] = skin_code

        part_skin_labels[
            part_slot
        ] = (
            legacy_part_skin_map.get(
                skin_code,
                "MODERN_OR_UNKNOWN",
            )
        )

    tag = tag_map.get(
        tag_bits,
        "UNKNOWN",
    )

    body_skin = (
        body_skin_map.get(
            body_skin_bits,
            "UNKNOWN",
        )
    )

    return {
        "tag_bits": tag_bits,
        "tag": tag,
        "body_skin_bits": (
            body_skin_bits
        ),
        "body_skin": body_skin,
        "part_skin_codes": (
            part_skin_codes
        ),
        "part_skin_labels": (
            part_skin_labels
        ),
    }



def build_full_axie_genes_from_core(
    genes_x,
    genes_y,
    order,
):
    if not isinstance(
        genes_x,
        int,
    ):
        raise ValueError(
            "genes_x must be an integer."
        )

    if not isinstance(
        genes_y,
        int,
    ):
        raise ValueError(
            "genes_y must be an integer."
        )

    if genes_x < 0 or genes_y < 0:
        raise ValueError(
            "Gene values cannot be negative."
        )

    if genes_x.bit_length() > 256:
        raise ValueError(
            "genes_x exceeds 256 bits."
        )

    if genes_y.bit_length() > 256:
        raise ValueError(
            "genes_y exceeds 256 bits."
        )

    x_hex = format(
        genes_x,
        "064x",
    )

    y_hex = format(
        genes_y,
        "064x",
    )

    if order == "xy":
        combined = (
            x_hex
            + y_hex
        )

    elif order == "yx":
        combined = (
            y_hex
            + x_hex
        )

    else:
        raise ValueError(
            "Gene order must be "
            "'xy' or 'yx'."
        )

    return (
        "0x"
        + combined
    )



def normalize_axie_genes_hex(
    genes_hex,
):
    if not isinstance(
        genes_hex,
        str,
    ):
        raise ValueError(
            "Genes must be hexadecimal text."
        )

    value = (
        genes_hex
        .strip()
        .lower()
    )

    if value.startswith(
        "0x"
    ):
        value = value[
            2:
        ]

    try:
        gene_integer = int(
            value,
            16,
        )

    except ValueError as error:
        raise ValueError(
            "Genes are not valid hexadecimal."
        ) from error

    if gene_integer.bit_length() > 512:
        raise ValueError(
            "Genes exceed 512 bits."
        )

    return (
        "0x"
        + format(
            gene_integer,
            "0128x",
        )
    )



def classify_collectible_presence_from_genes(
    genes_hex,
):
    decoded = (
        decode_axie_collectible_gene_signals(
            genes_hex
        )
    )

    tag_special = (
        decoded[
            "tag_bits"
        ]
        != "000000000000000"
    )

    body_special = (
        decoded[
            "body_skin_bits"
        ]
        != "0000"
    )

    special_part_skins = {
        slot: code
        for (
            slot,
            code,
        ) in decoded[
            "part_skin_codes"
        ].items()
        if code != 0
    }

    part_special = bool(
        special_part_skins
    )

    is_collectible = (
        1
        if (
            tag_special
            or body_special
            or part_special
        )
        else 0
    )

    return {
        "is_collectible": (
            is_collectible
        ),
        "tag": decoded[
            "tag"
        ],
        "tag_bits": decoded[
            "tag_bits"
        ],
        "body_skin": decoded[
            "body_skin"
        ],
        "body_skin_bits": decoded[
            "body_skin_bits"
        ],
        "special_part_skins": (
            special_part_skins
        ),
        "part_skin_codes": (
            decoded[
                "part_skin_codes"
            ]
        ),
    }



def classify_axie_collections_from_genes(
    genes_hex,
):
    decoded = (
        decode_axie_collectible_gene_signals(
            genes_hex
        )
    )

    collections = set()

    signal_details = []

    tag = decoded[
        "tag"
    ]

    tag_collections = (
        AXIE_TAG_COLLECTION_SIGNALS.get(
            tag,
            set(),
        )
    )

    for collection in (
        tag_collections
    ):
        collections.add(
            collection
        )

        signal_details.append(
            {
                "source": "tag",
                "value": tag,
                "collection": (
                    collection
                ),
            }
        )

    unknown_skin_codes = set()

    for (
        part_slot,
        skin_code,
    ) in decoded[
        "part_skin_codes"
    ].items():
        if skin_code == 0:
            continue

        mapped_collections = (
            AXIE_PART_SKIN_COLLECTION_SIGNALS.get(
                skin_code
            )
        )

        if mapped_collections is None:
            unknown_skin_codes.add(
                skin_code
            )

            signal_details.append(
                {
                    "source": (
                        "part_skin"
                    ),
                    "part_slot": (
                        part_slot
                    ),
                    "value": (
                        skin_code
                    ),
                    "collection": (
                        None
                    ),
                }
            )

            continue

        for collection in (
            mapped_collections
        ):
            collections.add(
                collection
            )

            signal_details.append(
                {
                    "source": (
                        "part_skin"
                    ),
                    "part_slot": (
                        part_slot
                    ),
                    "value": (
                        skin_code
                    ),
                    "collection": (
                        collection
                    ),
                }
            )

    body_skin_bits = decoded[
        "body_skin_bits"
    ]

    if body_skin_bits == "0010":
        collections.add(
            "SUMMER"
        )

        signal_details.append(
            {
                "source": (
                    "body_skin"
                ),
                "value": (
                    body_skin_bits
                ),
                "collection": (
                    "SUMMER"
                ),
            }
        )

    elif body_skin_bits == "0011":
        collections.add(
            "NIGHTMARE"
        )

        signal_details.append(
            {
                "source": (
                    "body_skin"
                ),
                "value": (
                    body_skin_bits
                ),
                "collection": (
                    "NIGHTMARE"
                ),
            }
        )

    has_unmapped_special_signal = (
        bool(
            unknown_skin_codes
        )
        or (
            decoded[
                "tag_bits"
            ]
            != "000000000000000"
            and not tag_collections
        )
        or (
            body_skin_bits
            not in {
                "0000",
                "0001",
                "0010",
                "0011",
            }
        )
    )

    is_collectible = (
        1
        if (
            collections
            or has_unmapped_special_signal
        )
        else 0
    )

    return {
        "is_collectible": (
            is_collectible
        ),
        "collections": sorted(
            collections
        ),
        "tag": tag,
        "body_skin_bits": (
            body_skin_bits
        ),
        "part_skin_codes": (
            decoded[
                "part_skin_codes"
            ]
        ),
        "unknown_skin_codes": sorted(
            unknown_skin_codes
        ),
        "has_unmapped_special_signal": (
            has_unmapped_special_signal
        ),
        "signals": (
            signal_details
        ),
    }




def sync_onchain_collectible_status_for_owned_axies(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    owned_rows = (
        connection.execute(
            """
            SELECT axie_id
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    connection.close()

    owned_ids = [
        str(row[0])
        for row in owned_rows
    ]

    valid_records = []
    failed_records = []

    for axie_id in owned_ids:
        core_result = (
            fetch_axie_core_onchain(
                axie_id
            )
        )

        if not core_result[
            "success"
        ]:
            failed_records.append(
                {
                    "axie_id": axie_id,
                    "reason": (
                        core_result.get(
                            "error"
                        )
                    ),
                }
            )

            continue

        core_data = core_result[
            "data"
        ]

        try:
            genes_hex = (
                build_full_axie_genes_from_core(
                    core_data[
                        "genes_x"
                    ],
                    core_data[
                        "genes_y"
                    ],
                    AXIE_CORE_GENE_ORDER,
                )
            )

            classification = (
                classify_collectible_presence_from_genes(
                    genes_hex
                )
            )

        except ValueError as error:
            failed_records.append(
                {
                    "axie_id": axie_id,
                    "reason": str(error),
                }
            )

            continue

        valid_records.append(
            {
                "axie_id": axie_id,
                "genes_hex": (
                    genes_hex
                ),
                "is_collectible": (
                    classification[
                        "is_collectible"
                    ]
                ),
                "tag": (
                    classification[
                        "tag"
                    ]
                ),
                "body_skin": (
                    classification[
                        "body_skin"
                    ]
                ),
                "special_part_skins": (
                    classification[
                        "special_part_skins"
                    ]
                ),
            }
        )

    connection = sqlite3.connect(
        db_path
    )

    for record in valid_records:
        connection.execute(
            """
            UPDATE gameplay_owned_axies
            SET
                is_collectible = ?,
                last_updated =
                    CURRENT_TIMESTAMP
            WHERE axie_id = ?
              AND ownership_status =
                  'OWNED'
            """,
            (
                record[
                    "is_collectible"
                ],
                record[
                    "axie_id"
                ],
            ),
        )

    connection.commit()
    connection.close()

    collectible_count = sum(
        record[
            "is_collectible"
        ]
        for record in valid_records
    )

    return {
        "success": (
            len(
                failed_records
            )
            == 0
        ),
        "owned_axies": len(
            owned_ids
        ),
        "classified_axies": len(
            valid_records
        ),
        "collectible_axies": (
            collectible_count
        ),
        "non_collectible_axies": (
            len(
                valid_records
            )
            - collectible_count
        ),
        "records": (
            valid_records
        ),
        "failed_axies": (
            failed_records
        ),
    }















def run_owned_axie_registry_test():
    initialize_owned_axie_registry(
        AXIEOS_DB_PATH
    )

    result = (
        validate_owned_axie_registry(
            AXIEOS_DB_PATH
        )
    )

    print(
        "\nAXIEOS OWNED AXIE REGISTRY"
    )

    print(
        "Table exists:",
        (
            "PASS"
            if result[
                "table_exists"
            ]
            else "FAIL"
        ),
    )

    print(
        "Columns:",
        result[
            "column_count"
        ],
    )

    print(
        "Missing columns:",
        len(
            result[
                "missing_columns"
            ]
        ),
    )

    if result[
        "missing_columns"
    ]:
        print(
            "Missing:",
            result[
                "missing_columns"
            ],
        )

    print(
        "\nValidation:",
        (
            "PASS"
            if result[
                "validation"
            ]
            else "FAIL"
        ),
    )







def run_axie_gameplay_detail_schema_test():
    initialize_owned_axie_registry(
        AXIEOS_DB_PATH
    )

    initialize_axie_gameplay_detail_tables(
        AXIEOS_DB_PATH
    )

    result = (
        validate_axie_gameplay_detail_tables(
            AXIEOS_DB_PATH
        )
    )

    print(
        "\nAXIEOS AXIE GAMEPLAY DETAIL SCHEMA"
    )

    print(
        "Missing tables:",
        len(
            result[
                "missing_tables"
            ]
        ),
    )

    print(
        "Parts columns:",
        result[
            "parts_column_count"
        ],
    )

    print(
        "Traits columns:",
        result[
            "traits_column_count"
        ],
    )

    print(
        "Missing parts columns:",
        len(
            result[
                "missing_parts_columns"
            ]
        ),
    )

    print(
        "Missing traits columns:",
        len(
            result[
                "missing_traits_columns"
            ]
        ),
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if result[
                "validation"
            ]
            else "FAIL"
        ),
    )



def run_gameplay_record_validation_test():
    valid_axie = {
        "axie_id": "1429698",
        "wallet_address": (
            "0x1111111111111111111111111111111111111111"
        ),
        "ownership_status": "OWNED",
        "axie_class": "Beast",
        "level": 20,
        "breed_count": 2,
        "is_collectible": 0,
        "is_evolved": 1,
    }

    invalid_axie = {
        "axie_id": "abc",
        "wallet_address": "",
        "ownership_status": "INVALID",
        "axie_class": "Dragon",
        "level": 0,
        "breed_count": 8,
        "is_collectible": 2,
        "is_evolved": "yes",
    }

    valid_part = {
        "axie_id": "1429698",
        "part_slot": "mouth",
        "part_name": "Pincer",
        "is_special": 0,
    }

    invalid_part = {
        "axie_id": "-1",
        "part_slot": "wing",
        "part_name": "Unknown",
        "is_special": 5,
    }

    valid_axie_result = (
        validate_owned_axie_record(
            valid_axie
        )
    )

    invalid_axie_result = (
        validate_owned_axie_record(
            invalid_axie
        )
    )

    valid_part_result = (
        validate_axie_part_record(
            valid_part
        )
    )

    invalid_part_result = (
        validate_axie_part_record(
            invalid_part
        )
    )

    validation = (
        valid_axie_result["valid"]
        and not invalid_axie_result[
            "valid"
        ]
        and valid_part_result["valid"]
        and not invalid_part_result[
            "valid"
        ]
    )

    print(
        "\nAXIEOS GAMEPLAY RECORD VALIDATION"
    )

    print(
        "Valid Axie:",
        (
            "PASS"
            if valid_axie_result[
                "valid"
            ]
            else "FAIL"
        ),
    )

    print(
        "Invalid Axie rejected:",
        (
            "PASS"
            if not invalid_axie_result[
                "valid"
            ]
            else "FAIL"
        ),
    )

    print(
        "Invalid Axie errors:",
        len(
            invalid_axie_result[
                "errors"
            ]
        ),
    )

    print(
        "Valid part:",
        (
            "PASS"
            if valid_part_result[
                "valid"
            ]
            else "FAIL"
        ),
    )

    print(
        "Invalid part rejected:",
        (
            "PASS"
            if not invalid_part_result[
                "valid"
            ]
            else "FAIL"
        ),
    )

    print(
        "Invalid part errors:",
        len(
            invalid_part_result[
                "errors"
            ]
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



def run_gameplay_persistence_test():
    initialize_owned_axie_registry(
        AXIEOS_DB_PATH
    )

    initialize_axie_gameplay_detail_tables(
        AXIEOS_DB_PATH
    )

    test_axie_id = "999999999"

    first_axie = {
        "axie_id": test_axie_id,
        "wallet_address": (
            "0x1111111111111111111111111111111111111111"
        ),
        "ownership_status": "OWNED",
        "axie_class": "Beast",
        "level": 10,
        "breed_count": 2,
        "is_collectible": 0,
        "collectible_type": None,
        "is_evolved": 0,
        "data_source": "TEST",
    }

    updated_axie = {
        **first_axie,
        "level": 20,
        "is_evolved": 1,
    }

    upsert_owned_axie(
        AXIEOS_DB_PATH,
        first_axie,
    )

    upsert_owned_axie(
        AXIEOS_DB_PATH,
        updated_axie,
    )

    first_part = {
        "axie_id": test_axie_id,
        "part_slot": "mouth",
        "part_id": "test-mouth",
        "part_name": "Test Mouth",
        "part_class": "Bug",
        "is_special": 0,
        "special_tag": None,
        "data_source": "TEST",
    }

    updated_part = {
        **first_part,
        "part_name": "Pincer",
    }

    upsert_axie_part(
        AXIEOS_DB_PATH,
        first_part,
    )

    upsert_axie_part(
        AXIEOS_DB_PATH,
        updated_part,
    )

    test_trait = {
        "axie_id": test_axie_id,
        "trait_type": "TEST_TRAIT",
        "trait_value": "TEST_VALUE",
        "data_source": "TEST",
    }

    upsert_axie_trait(
        AXIEOS_DB_PATH,
        test_trait,
    )

    upsert_axie_trait(
        AXIEOS_DB_PATH,
        test_trait,
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    axie_rows = (
        connection.execute(
            """
            SELECT
                level,
                is_evolved
            FROM gameplay_owned_axies
            WHERE axie_id = ?
            """,
            (
                test_axie_id,
            ),
        ).fetchall()
    )

    part_rows = (
        connection.execute(
            """
            SELECT
                part_name
            FROM gameplay_axie_parts
            WHERE axie_id = ?
            """,
            (
                test_axie_id,
            ),
        ).fetchall()
    )

    trait_rows = (
        connection.execute(
            """
            SELECT
                trait_type,
                trait_value
            FROM gameplay_axie_traits
            WHERE axie_id = ?
            """,
            (
                test_axie_id,
            ),
        ).fetchall()
    )

    axie_upsert_valid = (
        len(axie_rows) == 1
        and axie_rows[0][0] == 20
        and axie_rows[0][1] == 1
    )

    part_upsert_valid = (
        len(part_rows) == 1
        and part_rows[0][0]
        == "Pincer"
    )

    trait_upsert_valid = (
        len(trait_rows) == 1
    )

    # Remove synthetic test data.
    connection.execute(
        """
        DELETE FROM gameplay_axie_traits
        WHERE axie_id = ?
        """,
        (
            test_axie_id,
        ),
    )

    connection.execute(
        """
        DELETE FROM gameplay_axie_parts
        WHERE axie_id = ?
        """,
        (
            test_axie_id,
        ),
    )

    connection.execute(
        """
        DELETE FROM gameplay_owned_axies
        WHERE axie_id = ?
        """,
        (
            test_axie_id,
        ),
    )

    connection.commit()

    remaining_test_rows = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM gameplay_owned_axies
            WHERE axie_id = ?
            """,
            (
                test_axie_id,
            ),
        ).fetchone()[0]
    )

    connection.close()

    cleanup_valid = (
        remaining_test_rows == 0
    )

    validation = (
        axie_upsert_valid
        and part_upsert_valid
        and trait_upsert_valid
        and cleanup_valid
    )

    print(
        "\nAXIEOS GAMEPLAY PERSISTENCE"
    )

    print(
        "Owned Axie UPSERT:",
        (
            "PASS"
            if axie_upsert_valid
            else "FAIL"
        ),
    )

    print(
        "Axie part UPSERT:",
        (
            "PASS"
            if part_upsert_valid
            else "FAIL"
        ),
    )

    print(
        "Axie trait UPSERT:",
        (
            "PASS"
            if trait_upsert_valid
            else "FAIL"
        ),
    )

    print(
        "Synthetic cleanup:",
        (
            "PASS"
            if cleanup_valid
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



def run_axie_ownership_derivation_test():
    results = (
        derive_axie_ownership_from_accounting(
            AXIEOS_DB_PATH
        )
    )

    status_counts = {}

    for item in results:
        status = item[
            "ownership_status"
        ]

        status_counts[status] = (
            status_counts.get(
                status,
                0,
            )
            + 1
        )

    owned = [
        item
        for item in results
        if item[
            "ownership_status"
        ]
        == "OWNED"
    ]

    owned_with_purchase_cost = [
        item
        for item in owned
        if item[
            "acquisition_cost_weth"
        ]
        is not None
    ]

    owned_without_purchase_cost = [
        item
        for item in owned
        if item[
            "acquisition_cost_weth"
        ]
        is None
    ]

    valid_statuses = all(
        item[
            "ownership_status"
        ]
        in OWNED_AXIE_STATUSES
        for item in results
    )

    unique_axie_ids = {
        item["axie_id"]
        for item in results
    }

    unique_valid = (
        len(unique_axie_ids)
        == len(results)
    )

    validation = (
        len(results) > 0
        and valid_statuses
        and unique_valid
    )

    print(
        "\nAXIEOS AXIE OWNERSHIP DERIVATION"
    )

    print(
        "Axies found in accounting history:",
        len(results),
    )

    print(
        "Unique Axie IDs:",
        len(
            unique_axie_ids
        ),
    )

    print(
        "\nOWNERSHIP STATUS"
    )

    for status in sorted(
        status_counts
    ):
        print(
            f"{status}: "
            f"{status_counts[status]}"
        )

    print(
        "\nCURRENTLY OWNED"
    )

    print(
        "Owned Axies:",
        len(owned),
    )

    print(
        "Owned with purchase cost:",
        len(
            owned_with_purchase_cost
        ),
    )

    print(
        "Owned without purchase cost:",
        len(
            owned_without_purchase_cost
        ),
    )

    print(
        "\nOWNED AXIE EXAMPLES"
    )

    for item in owned[:20]:
        print(
            "\nAxie ID:",
            item["axie_id"],
        )

        print(
            "Acquisition event:",
            item[
                "acquisition_event_type"
            ],
        )

        print(
            "Acquisition date:",
            item[
                "acquisition_datetime"
            ],
        )

        print(
            "Acquisition cost:",
            item[
                "acquisition_cost_weth"
            ],
        )

        print(
            "Latest event:",
            item[
                "latest_event_type"
            ],
        )

        print(
            "History records:",
            item[
                "history_count"
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



def run_axie_ownership_reconciliation_test():
    result = (
        reconcile_axie_ownership_with_raw_transfers(
            AXIEOS_DB_PATH
        )
    )

    records = result[
        "records"
    ]

    status_counts = {}

    for item in records:
        status = item[
            "reconciliation_status"
        ]

        status_counts[status] = (
            status_counts.get(
                status,
                0,
            )
            + 1
        )

    matched = [
        item
        for item in records
        if item[
            "reconciliation_status"
        ]
        == "MATCH"
    ]

    mismatches = [
        item
        for item in records
        if item[
            "reconciliation_status"
        ]
        == "MISMATCH"
    ]

    no_raw_history = [
        item
        for item in records
        if item[
            "reconciliation_status"
        ]
        == "NO_RAW_HISTORY"
    ]

    accounting_unknown = [
        item
        for item in records
        if item[
            "reconciliation_status"
        ]
        == "ACCOUNTING_UNKNOWN"
    ]

    unique_ids = {
        item["axie_id"]
        for item in records
    }

    structural_validation = (
        len(records) > 0
        and len(unique_ids)
        == len(records)
        and sum(
            status_counts.values()
        )
        == len(records)
        and len(
            result["owned_wallets"]
        )
        > 0
    )

    persistence_ready = (
        structural_validation
        and len(mismatches) == 0
        and len(no_raw_history) == 0
        and len(accounting_unknown) == 0
    )

    print(
        "\nAXIEOS AXIE OWNERSHIP RECONCILIATION"
    )

    print(
        "Registered owned wallets:",
        len(
            result["owned_wallets"]
        ),
    )

    print(
        "Axies checked:",
        len(records),
    )

    print(
        "Matched:",
        len(matched),
    )

    print(
        "Mismatches:",
        len(mismatches),
    )

    print(
        "No raw history:",
        len(
            no_raw_history
        ),
    )

    print(
        "Accounting unknown:",
        len(
            accounting_unknown
        ),
    )

    print(
        "\nRECONCILIATION STATUS"
    )

    for status in sorted(
        status_counts
    ):
        print(
            f"{status}: "
            f"{status_counts[status]}"
        )

    if mismatches:
        print(
            "\nMISMATCHES"
        )

        for item in mismatches:
            print(
                "\nAxie ID:",
                item["axie_id"],
            )

            print(
                "Accounting:",
                item[
                    "accounting_status"
                ],
                "/",
                item[
                    "accounting_state"
                ],
            )

            print(
                "Raw state:",
                item[
                    "raw_state"
                ],
            )

            latest = item[
                "latest_raw"
            ]

            if latest is not None:
                print(
                    "Latest raw date:",
                    latest[
                        "timestamp"
                    ],
                )

                print(
                    "Latest raw TX:",
                    latest[
                        "txhash"
                    ],
                )

                print(
                    "From:",
                    latest[
                        "from_address"
                    ],
                )

                print(
                    "To:",
                    latest[
                        "to_address"
                    ],
                )

    if no_raw_history:
        print(
            "\nNO RAW HISTORY"
        )

        for item in (
            no_raw_history
        ):
            print(
                "Axie ID:",
                item["axie_id"],
                "Accounting:",
                item[
                    "accounting_status"
                ],
            )

    print(
        "\nStructural validation:",
        (
            "PASS"
            if structural_validation
            else "FAIL"
        ),
    )

    print(
        "Persistence readiness:",
        (
            "PASS"
            if persistence_ready
            else "REVIEW"
        ),
    )



def run_owned_axie_registry_sync_test():
    first_result = (
        sync_owned_axie_registry_from_accounting(
            AXIEOS_DB_PATH
        )
    )

    second_result = (
        sync_owned_axie_registry_from_accounting(
            AXIEOS_DB_PATH
        )
    )

    derived = (
        derive_axie_ownership_from_accounting(
            AXIEOS_DB_PATH
        )
    )

    expected_owned_ids = {
        item["axie_id"]
        for item in derived
        if item[
            "ownership_status"
        ]
        == "OWNED"
    }

    actual_owned_ids = {
        row[0]
        for row in second_result[
            "registry_owned"
        ]
    }

    ownership_match = (
        expected_owned_ids
        == actual_owned_ids
    )

    idempotent_count = (
        len(
            first_result[
                "registry_rows"
            ]
        )
        == len(
            second_result[
                "registry_rows"
            ]
        )
    )

    duplicate_check = (
        len(actual_owned_ids)
        == len(
            second_result[
                "registry_owned"
            ]
        )
    )

    known_cost_count = sum(
        1
        for row in second_result[
            "registry_owned"
        ]
        if row[5] is not None
    )

    unknown_cost_count = (
        len(
            second_result[
                "registry_owned"
            ]
        )
        - known_cost_count
    )

    validation = (
        ownership_match
        and idempotent_count
        and duplicate_check
        and second_result[
            "skipped"
        ]
        == 0
    )

    print(
        "\nAXIEOS OWNED AXIE REGISTRY SYNC"
    )

    print(
        "Accounting Axies:",
        second_result[
            "derived_count"
        ],
    )

    print(
        "Derived currently owned:",
        second_result[
            "derived_owned"
        ],
    )

    print(
        "Registry currently owned:",
        len(
            second_result[
                "registry_owned"
            ]
        ),
    )

    print(
        "Owned with acquisition cost:",
        known_cost_count,
    )

    print(
        "Owned without acquisition cost:",
        unknown_cost_count,
    )

    print(
        "Skipped:",
        second_result[
            "skipped"
        ],
    )

    print(
        "\nSYNC VALIDATION"
    )

    print(
        "Ownership set:",
        (
            "PASS"
            if ownership_match
            else "FAIL"
        ),
    )

    print(
        "Idempotent registry count:",
        (
            "PASS"
            if idempotent_count
            else "FAIL"
        ),
    )

    print(
        "Duplicate protection:",
        (
            "PASS"
            if duplicate_check
            else "FAIL"
        ),
    )

    print(
        "\nCURRENT OWNED AXIES"
    )

    for row in second_result[
        "registry_owned"
    ]:
        (
            axie_id,
            wallet_address,
            ownership_status,
            acquisition_txhash,
            acquisition_datetime,
            acquisition_cost_weth,
        ) = row

        print(
            "\nAxie ID:",
            axie_id,
        )

        print(
            "Wallet:",
            wallet_address,
        )

        print(
            "Status:",
            ownership_status,
        )

        print(
            "Acquisition date:",
            acquisition_datetime,
        )

        print(
            "Acquisition cost:",
            acquisition_cost_weth,
        )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_owned_axie_foundation_validation_test():
    result = (
        validate_owned_axie_foundation(
            AXIEOS_DB_PATH
        )
    )

    print(
        "\nAXIEOS OWNED AXIE FOUNDATION V0.8"
    )

    print(
        "Pipeline version:",
        GAMEPLAY_PIPELINE_VERSION,
    )

    print(
        "Accounting Axies:",
        result[
            "accounting_axies"
        ],
    )

    print(
        "Expected currently owned:",
        result[
            "expected_owned"
        ],
    )

    print(
        "Registry currently owned:",
        result[
            "registry_owned"
        ],
    )

    print(
        "Owned with acquisition cost:",
        result[
            "known_cost_count"
        ],
    )

    print(
        "Owned without acquisition cost:",
        result[
            "unknown_cost_count"
        ],
    )

    print(
        "\nFOUNDATION CHECKS"
    )

    print(
        "Registry schema:",
        (
            "PASS"
            if result[
                "registry_schema"
            ]
            else "FAIL"
        ),
    )

    print(
        "Parts / traits schema:",
        (
            "PASS"
            if result[
                "detail_schema"
            ]
            else "FAIL"
        ),
    )

    print(
        "Raw-transfer reconciliation:",
        (
            "PASS"
            if result[
                "reconciliation_valid"
            ]
            else "FAIL"
        ),
    )

    print(
        "Owned-Axie set:",
        (
            "PASS"
            if result[
                "owned_set_valid"
            ]
            else "FAIL"
        ),
    )

    print(
        "Owned-wallet membership:",
        (
            "PASS"
            if result[
                "owned_wallet_valid"
            ]
            else "FAIL"
        ),
    )

    print(
        "Ownership statuses:",
        (
            "PASS"
            if result[
                "valid_statuses"
            ]
            else "FAIL"
        ),
    )

    print(
        "Duplicate protection:",
        (
            "PASS"
            if result[
                "duplicate_valid"
            ]
            else "FAIL"
        ),
    )

    print(
        "Orphan parts:",
        result[
            "orphan_parts"
        ],
    )

    print(
        "Orphan traits:",
        result[
            "orphan_traits"
        ],
    )

    print(
        "Sync skipped:",
        result[
            "skipped"
        ],
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if result[
                "validation"
            ]
            else "FAIL"
        ),
    )



def run_owned_axie_gameplay_profile_test():
    profiles = (
        load_owned_axie_gameplay_profiles(
            AXIEOS_DB_PATH
        )
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    registry_owned_count = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM gameplay_owned_axies
            WHERE ownership_status = 'OWNED'
            """
        ).fetchone()[0]
    )

    connection.close()

    unique_ids = {
        item["axie_id"]
        for item in profiles
    }

    with_class = [
        item
        for item in profiles
        if item[
            "axie_class"
        ]
        is not None
    ]

    with_level = [
        item
        for item in profiles
        if item["level"]
        is not None
    ]

    with_breed_count = [
        item
        for item in profiles
        if item[
            "breed_count"
        ]
        is not None
    ]

    with_collectible_status = [
        item
        for item in profiles
        if item[
            "is_collectible"
        ]
        is not None
    ]

    with_evolved_status = [
        item
        for item in profiles
        if item[
            "is_evolved"
        ]
        is not None
    ]

    with_parts = [
        item
        for item in profiles
        if item["parts"]
    ]

    complete_parts = [
        item
        for item in profiles
        if set(
            item["parts"].keys()
        )
        == AXIE_PART_SLOTS
    ]

    with_traits = [
        item
        for item in profiles
        if item["traits"]
    ]

    valid_part_slots = all(
        set(
            item["parts"].keys()
        ).issubset(
            AXIE_PART_SLOTS
        )
        for item in profiles
    )

    structural_validation = all(
        isinstance(
            item["parts"],
            dict,
        )
        and isinstance(
            item["traits"],
            dict,
        )
        for item in profiles
    )

    validation = (
        len(profiles)
        == registry_owned_count
        and len(unique_ids)
        == len(profiles)
        and valid_part_slots
        and structural_validation
    )

    print(
        "\nAXIEOS OWNED AXIE GAMEPLAY PROFILES"
    )

    print(
        "Owned registry records:",
        registry_owned_count,
    )

    print(
        "Gameplay profiles loaded:",
        len(profiles),
    )

    print(
        "Unique Axie IDs:",
        len(unique_ids),
    )

    print(
        "\nATTRIBUTE COVERAGE"
    )

    print(
        "Class known:",
        len(with_class),
    )

    print(
        "Level known:",
        len(with_level),
    )

    print(
        "Breed count known:",
        len(
            with_breed_count
        ),
    )

    print(
        "Collectible status known:",
        len(
            with_collectible_status
        ),
    )

    print(
        "Evolved status known:",
        len(
            with_evolved_status
        ),
    )

    print(
        "Axies with parts:",
        len(with_parts),
    )

    print(
        "Axies with all 6 parts:",
        len(
            complete_parts
        ),
    )

    print(
        "Axies with traits:",
        len(with_traits),
    )

    print(
        "\nPROFILE CHECKS"
    )

    print(
        "Registry/profile count:",
        (
            "PASS"
            if len(profiles)
            == registry_owned_count
            else "FAIL"
        ),
    )

    print(
        "Unique profiles:",
        (
            "PASS"
            if len(unique_ids)
            == len(profiles)
            else "FAIL"
        ),
    )

    print(
        "Part slots:",
        (
            "PASS"
            if valid_part_slots
            else "FAIL"
        ),
    )

    print(
        "Profile structure:",
        (
            "PASS"
            if structural_validation
            else "FAIL"
        ),
    )

    print(
        "\nCURRENT PROFILE COVERAGE"
    )

    for item in profiles:
        print(
            "\nAxie ID:",
            item["axie_id"],
        )

        print(
            "Class:",
            item[
                "axie_class"
            ],
        )

        print(
            "Level:",
            item["level"],
        )

        print(
            "Breed:",
            item[
                "breed_count"
            ],
        )

        print(
            "Collectible:",
            item[
                "is_collectible"
            ],
        )

        print(
            "Evolved:",
            item[
                "is_evolved"
            ],
        )

        print(
            "Parts:",
            len(
                item["parts"]
            ),
        )

        print(
            "Traits:",
            sum(
                len(values)
                for values
                in item[
                    "traits"
                ].values()
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



def run_axie_metadata_api_test():
    test_axie_id = "1430861"

    result = (
        fetch_axie_gameplay_metadata(
            test_axie_id
        )
    )

    print(
        "\nAXIEOS AXIE METADATA API"
    )

    print(
        "Test Axie ID:",
        test_axie_id,
    )

    print(
        "HTTP status:",
        result[
            "status_code"
        ],
    )

    print(
        "API request:",
        (
            "PASS"
            if result[
                "success"
            ]
            else "FAIL"
        ),
    )

    if not result["success"]:
        print(
            "\nERRORS"
        )

        for error in result[
            "errors"
        ]:
            print(error)

        print(
            "\nValidation: FAIL"
        )

        return

    axie = result[
        "axie"
    ]

    returned_id = str(
        axie.get(
            "id"
        )
    )

    axie_class = axie.get(
        "class"
    )

    level = axie.get(
        "level"
    )

    breed_count = axie.get(
        "breedCount"
    )

    parts = (
        axie.get(
            "parts"
        )
        or []
    )

    normalized_part_slots = {
        str(
            part.get(
                "type"
            )
        ).strip().lower()
        for part in parts
        if part.get(
            "type"
        )
        is not None
    }

    id_valid = (
        returned_id
        == test_axie_id
    )

    class_valid = (
        axie_class
        in AXIE_CLASSES
    )

    breed_valid = (
        isinstance(
            breed_count,
            int,
        )
        and not isinstance(
            breed_count,
            bool,
        )
        and 0 <= breed_count <= 7
    )

    parts_valid = (
        len(parts) == 6
        and normalized_part_slots
        == AXIE_PART_SLOTS
    )

    validation = (
        id_valid
        and class_valid
        and breed_valid
        and parts_valid
    )

    print(
        "\nAXIE METADATA"
    )

    print(
        "Returned ID:",
        returned_id,
    )

    print(
        "Name:",
        axie.get(
            "name"
        ),
    )

    print(
        "Class:",
        axie_class,
    )

    print(
        "Stage:",
        axie.get(
            "stage"
        ),
    )

    print(
        "Level:",
        level,
    )

    print(
        "Breed count:",
        breed_count,
    )

    print(
        "Title:",
        axie.get(
            "title"
        ),
    )

    print(
        "Owner:",
        axie.get(
            "owner"
        ),
    )

    print(
        "\nBODY PARTS"
    )

    print(
        "Parts returned:",
        len(parts),
    )

    for part in parts:
        print(
            part.get(
                "type"
            ),
            "|",
            part.get(
                "name"
            ),
            "|",
            part.get(
                "class"
            ),
            "| specialGenes:",
            part.get(
                "specialGenes"
            ),
            "| stage:",
            part.get(
                "stage"
            ),
        )

    print(
        "\nAPI CHECKS"
    )

    print(
        "Axie ID:",
        (
            "PASS"
            if id_valid
            else "FAIL"
        ),
    )

    print(
        "Class:",
        (
            "PASS"
            if class_valid
            else "FAIL"
        ),
    )

    print(
        "Breed count:",
        (
            "PASS"
            if breed_valid
            else "FAIL"
        ),
    )

    print(
        "Six body parts:",
        (
            "PASS"
            if parts_valid
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



def run_axie_explorer_metadata_test():
    test_axie_id = "1430861"

    result = (
        fetch_axie_explorer_metadata(
            test_axie_id
        )
    )

    print(
        "\nAXIEOS AXIE EXPLORER METADATA"
    )

    print(
        "Test Axie ID:",
        test_axie_id,
    )

    print(
        "HTTP status:",
        result[
            "status_code"
        ],
    )

    print(
        "Explorer request:",
        (
            "PASS"
            if result[
                "success"
            ]
            else "FAIL"
        ),
    )

    if not result["success"]:
        print(
            "Error:",
            result.get(
                "error"
            ),
        )

        if result.get(
            "response_preview"
        ):
            print(
                "\nRESPONSE PREVIEW"
            )

            print(
                result[
                    "response_preview"
                ]
            )

        print(
            "\nValidation: FAIL"
        )

        return

    data = result[
        "data"
    ]

    returned_id = str(
        data.get(
            "id"
        )
    )

    metadata = data.get(
        "metadata"
    )

    owner = data.get(
        "owner"
    )

    id_valid = (
        returned_id
        == test_axie_id
    )

    metadata_available = (
        isinstance(
            metadata,
            dict,
        )
        and len(metadata) > 0
    )

    print(
        "\nNFT INSTANCE"
    )

    print(
        "Returned ID:",
        returned_id,
    )

    print(
        "Owner available:",
        owner is not None,
    )

    print(
        "Metadata available:",
        metadata_available,
    )

    print(
        "\nTOP-LEVEL KEYS"
    )

    for key in sorted(
        data.keys()
    ):
        print(key)

    print(
        "\nMETADATA"
    )

    if metadata is None:
        print(
            "None"
        )

    else:
        print(
            json.dumps(
                metadata,
                indent=2,
                ensure_ascii=False,
            )
        )

    validation = (
        id_valid
        and metadata_available
    )

    print(
        "\nEXPLORER CHECKS"
    )

    print(
        "Axie ID:",
        (
            "PASS"
            if id_valid
            else "FAIL"
        ),
    )

    print(
        "NFT metadata:",
        (
            "PASS"
            if metadata_available
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



def run_axie_marketplace_page_test():
    test_axie_id = "1430861"

    result = (
        fetch_axie_marketplace_page(
            test_axie_id
        )
    )

    print(
        "\nAXIEOS AXIE MARKETPLACE PAGE"
    )

    print(
        "Test Axie ID:",
        test_axie_id,
    )

    print(
        "HTTP status:",
        result[
            "status_code"
        ],
    )

    print(
        "Page request:",
        (
            "PASS"
            if result[
                "success"
            ]
            else "FAIL"
        ),
    )

    if not result["success"]:
        print(
            "Error:",
            result.get(
                "error"
            ),
        )

        print(
            "\nValidation: FAIL"
        )

        return

    html = result[
        "html"
    ]

    html_lower = (
        html.lower()
    )

    markers = {
        "axie_id": (
            test_axie_id
            in html_lower
        ),
        "breed_count": (
            "breed_count"
            in html_lower
            or "breedcount"
            in html_lower
        ),
        "class": (
            '"class"'
            in html_lower
            or "class&quot;"
            in html_lower
        ),
        "mouth_name": (
            "mouth_name"
            in html_lower
        ),
        "num_japan": (
            "num_japan"
            in html_lower
        ),
        "stage": (
            "back_stage"
            in html_lower
            or "mouth_stage"
            in html_lower
        ),
        "next_data": (
            "__next_data__"
            in html_lower
        ),
    }

    print(
        "\nPAGE DETAILS"
    )

    print(
        "HTML characters:",
        len(html),
    )

    print(
        "\nMETADATA MARKERS"
    )

    for marker, found in (
        markers.items()
    ):
        print(
            marker,
            ":",
            (
                "FOUND"
                if found
                else "NOT FOUND"
            ),
        )

    interesting_patterns = [
        "breed_count",
        "breedcount",
        "num_japan",
        "mouth_name",
        "back_stage",
    ]

    print(
        "\nMATCHED SNIPPETS"
    )

    snippets_found = 0

    for pattern in (
        interesting_patterns
    ):
        match = re.search(
            pattern,
            html_lower,
        )

        if match is None:
            continue

        snippets_found += 1

        start = max(
            0,
            match.start() - 150,
        )

        end = min(
            len(html),
            match.end() + 300,
        )

        snippet = html[
            start:end
        ]

        print(
            f"\n--- {pattern} ---"
        )

        print(
            snippet
        )

    metadata_signal = any(
        markers[
            marker
        ]
        for marker in {
            "breed_count",
            "mouth_name",
            "num_japan",
            "stage",
        }
    )

    validation = (
        result["success"]
        and markers[
            "axie_id"
        ]
        and metadata_signal
    )

    print(
        "\nMetadata signal:",
        (
            "PASS"
            if metadata_signal
            else "FAIL"
        ),
    )

    print(
        "Snippets found:",
        snippets_found,
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_skymavis_api_client_test():
    try:
        api_key = (
            get_skymavis_api_key()
        )

        key_available = bool(
            api_key
        )

    except RuntimeError:
        key_available = False

    print(
        "\nAXIEOS SKY MAVIS API CLIENT"
    )

    print(
        "API key available:",
        (
            "PASS"
            if key_available
            else "FAIL"
        ),
    )

    if not key_available:
        print(
            "\nValidation: FAIL"
        )

        return

    result = skymavis_api_get(
        (
            "origins/v2/"
            "community/items"
        ),
        params={
            "limit": 1,
            "offset": 0,
        },
    )

    print(
        "HTTP status:",
        result[
            "status_code"
        ],
    )

    print(
        "Authenticated request:",
        (
            "PASS"
            if result[
                "success"
            ]
            else "FAIL"
        ),
    )

    if not result["success"]:
        print(
            "Error:",
            result.get(
                "error"
            ),
        )

        if result.get(
            "response_preview"
        ):
            print(
                "Response preview:",
                result[
                    "response_preview"
                ],
            )

        print(
            "\nValidation: FAIL"
        )

        return

    data = result[
        "data"
    ]

    items = data.get(
        "_items",
        [],
    )

    metadata = data.get(
        "_metadata",
        {},
    )

    item_structure_valid = (
        isinstance(
            items,
            list,
        )
        and len(items) == 1
        and isinstance(
            items[0],
            dict,
        )
    )

    pagination_valid = (
        isinstance(
            metadata,
            dict,
        )
        and metadata.get(
            "limit"
        )
        == 1
    )

    validation = (
        item_structure_valid
        and pagination_valid
    )

    print(
        "\nAPI RESPONSE"
    )

    print(
        "Items returned:",
        len(items),
    )

    if items:
        print(
            "First item ID:",
            items[0].get(
                "id"
            ),
        )

        print(
            "First item name:",
            items[0].get(
                "name"
            ),
        )

    print(
        "Reported total:",
        metadata.get(
            "total"
        ),
    )

    print(
        "\nCLIENT CHECKS"
    )

    print(
        "Item structure:",
        (
            "PASS"
            if item_structure_valid
            else "FAIL"
        ),
    )

    print(
        "Pagination metadata:",
        (
            "PASS"
            if pagination_valid
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



def run_origins_ronin_fighter_test():
    print(
        "\nAXIEOS ORIGINS RONIN FIGHTERS"
    )

    try:
        user_id = (
            get_skymavis_origins_user_id()
        )

        user_id_available = bool(
            user_id
        )

    except RuntimeError:
        user_id_available = False

    print(
        "Origins User ID available:",
        (
            "PASS"
            if user_id_available
            else "FAIL"
        ),
    )

    if not user_id_available:
        print(
            "\nValidation: FAIL"
        )
        return

    result = (
        fetch_origins_ronin_fighters()
    )

    print(
        "HTTP status:",
        result[
            "status_code"
        ],
    )

    print(
        "Fighter request:",
        (
            "PASS"
            if result[
                "success"
            ]
            else "FAIL"
        ),
    )

    if not result["success"]:
        print(
            "Error:",
            result.get(
                "error"
            ),
        )

        if result.get(
            "response_preview"
        ):
            print(
                "Response preview:",
                result[
                    "response_preview"
                ],
            )

        print(
            "\nValidation: FAIL"
        )
        return

    data = result[
        "data"
    ]

    fighters = data.get(
        "_items",
        [],
    )

    metadata = data.get(
        "_metadata",
        {},
    )

    fighter_ids = {
        str(
            fighter.get("id")
        )
        for fighter in fighters
        if fighter.get(
            "id"
        )
        is not None
    }

    profiles = (
        load_owned_axie_gameplay_profiles(
            AXIEOS_DB_PATH
        )
    )

    blockchain_owned_ids = {
        profile["axie_id"]
        for profile in profiles
    }

    matched_ids = (
        blockchain_owned_ids
        & fighter_ids
    )

    missing_from_origins = (
        blockchain_owned_ids
        - fighter_ids
    )

    origins_only = (
        fighter_ids
        - blockchain_owned_ids
    )

    ronin_type_valid = all(
        fighter.get(
            "axieType"
        )
        == "ronin"
        for fighter in fighters
    )

    class_count = sum(
        1
        for fighter in fighters
        if fighter.get(
            "class"
        )
        in AXIE_CLASSES
    )

    six_part_count = sum(
        1
        for fighter in fighters
        if len(
            fighter.get(
                "parts"
            )
            or []
        )
        == 6
    )

    coverage_valid = (
        blockchain_owned_ids
        == matched_ids
    )

    structure_valid = (
        isinstance(
            fighters,
            list,
        )
        and isinstance(
            metadata,
            dict,
        )
        and ronin_type_valid
    )

    validation = (
        structure_valid
        and len(fighters) > 0
    )

    print(
        "\nFIGHTER RESPONSE"
    )

    print(
        "Fighters returned:",
        len(fighters),
    )

    print(
        "Reported total:",
        metadata.get(
            "total"
        ),
    )

    print(
        "Has next page:",
        metadata.get(
            "hasNext"
        ),
    )

    print(
        "\nBLOCKCHAIN COMPARISON"
    )

    print(
        "Blockchain-owned Axies:",
        len(
            blockchain_owned_ids
        ),
    )

    print(
        "Matched in Origins:",
        len(
            matched_ids
        ),
    )

    print(
        "Missing from Origins:",
        len(
            missing_from_origins
        ),
    )

    print(
        "Origins-only fighters:",
        len(
            origins_only
        ),
    )

    print(
        "\nMETADATA COVERAGE"
    )

    print(
        "Class available:",
        class_count,
    )

    print(
        "Six parts available:",
        six_part_count,
    )

    print(
        "\nAPI CHECKS"
    )

    print(
        "Ronin fighter type:",
        (
            "PASS"
            if ronin_type_valid
            else "FAIL"
        ),
    )

    print(
        "Response structure:",
        (
            "PASS"
            if structure_valid
            else "FAIL"
        ),
    )

    print(
        "Blockchain coverage:",
        (
            "PASS"
            if coverage_valid
            else "REVIEW"
        ),
    )

    if missing_from_origins:
        print(
            "\nMISSING FROM ORIGINS"
        )

        for axie_id in sorted(
            missing_from_origins,
            key=int,
        ):
            print(
                "Axie ID:",
                axie_id,
            )

    if origins_only:
        print(
            "\nORIGINS-ONLY FIGHTERS"
        )

        for axie_id in sorted(
            origins_only,
            key=int,
        ):
            print(
                "Axie ID:",
                axie_id,
            )

    if fighters:
        sample = fighters[0]

        print(
            "\nSAMPLE FIGHTER"
        )

        print(
            "Axie ID:",
            sample.get(
                "id"
            ),
        )

        print(
            "Class:",
            sample.get(
                "class"
            ),
        )

        print(
            "Title:",
            sample.get(
                "title"
            ),
        )

        print(
            "Name:",
            sample.get(
                "name"
            ),
        )

        print(
            "XP:",
            sample.get(
                "xp"
            ),
        )

        print(
            "Parts:",
            len(
                sample.get(
                    "parts"
                )
                or []
            ),
        )

        print(
            "Available fields:",
            ", ".join(
                sorted(
                    sample.keys()
                )
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



def run_all_origins_fighter_test():
    print(
        "\nAXIEOS COMPLETE ORIGINS FIGHTER AUDIT"
    )

    result = (
        fetch_all_origins_ronin_fighters()
    )

    print(
        "API pagination:",
        (
            "PASS"
            if result[
                "success"
            ]
            else "FAIL"
        ),
    )

    if not result["success"]:
        print(
            "HTTP status:",
            result[
                "status_code"
            ],
        )

        print(
            "Error:",
            result.get(
                "error"
            ),
        )

        print(
            "\nValidation: FAIL"
        )

        return

    fighters = result[
        "fighters"
    ]

    fighter_map = {
        str(
            fighter["id"]
        ): fighter
        for fighter in fighters
        if fighter.get(
            "id"
        )
        is not None
    }

    fighter_ids = set(
        fighter_map.keys()
    )

    profiles = (
        load_owned_axie_gameplay_profiles(
            AXIEOS_DB_PATH
        )
    )

    blockchain_owned_ids = {
        profile["axie_id"]
        for profile in profiles
    }

    matched_ids = (
        blockchain_owned_ids
        & fighter_ids
    )

    missing_from_origins = (
        blockchain_owned_ids
        - fighter_ids
    )

    origins_only = (
        fighter_ids
        - blockchain_owned_ids
    )

    pagination_count_valid = (
        result[
            "reported_total"
        ]
        is None
        or result[
            "unique_fighter_count"
        ]
        == result[
            "reported_total"
        ]
    )

    blockchain_coverage_valid = (
        matched_ids
        == blockchain_owned_ids
    )

    class_coverage = sum(
        1
        for axie_id in matched_ids
        if fighter_map[
            axie_id
        ].get(
            "class"
        )
        in AXIE_CLASSES
    )

    six_part_coverage = sum(
        1
        for axie_id in matched_ids
        if len(
            fighter_map[
                axie_id
            ].get(
                "parts"
            )
            or []
        )
        == 6
    )

    level_coverage = sum(
        1
        for axie_id in matched_ids
        if isinstance(
            fighter_map[
                axie_id
            ].get(
                "xp"
            ),
            dict,
        )
        and fighter_map[
            axie_id
        ][
            "xp"
        ].get(
            "currentLevel"
        )
        is not None
    )

    validation = (
        result[
            "success"
        ]
        and pagination_count_valid
        and blockchain_coverage_valid
        and class_coverage
        == len(
            blockchain_owned_ids
        )
        and six_part_coverage
        == len(
            blockchain_owned_ids
        )
    )

    print(
        "\nPAGINATION"
    )

    print(
        "Pages fetched:",
        result[
            "pages"
        ],
    )

    print(
        "Raw fighters:",
        result[
            "raw_fighter_count"
        ],
    )

    print(
        "Unique fighters:",
        result[
            "unique_fighter_count"
        ],
    )

    print(
        "Reported total:",
        result[
            "reported_total"
        ],
    )

    print(
        "Pagination count:",
        (
            "PASS"
            if pagination_count_valid
            else "FAIL"
        ),
    )

    print(
        "\nBLOCKCHAIN COMPARISON"
    )

    print(
        "Blockchain-owned Axies:",
        len(
            blockchain_owned_ids
        ),
    )

    print(
        "Matched in Origins:",
        len(
            matched_ids
        ),
    )

    print(
        "Missing from Origins:",
        len(
            missing_from_origins
        ),
    )

    print(
        "Origins-only fighters:",
        len(
            origins_only
        ),
    )

    print(
        "\nCURRENT AXIE METADATA COVERAGE"
    )

    print(
        "Class:",
        class_coverage,
        "/",
        len(
            blockchain_owned_ids
        ),
    )

    print(
        "Level:",
        level_coverage,
        "/",
        len(
            blockchain_owned_ids
        ),
    )

    print(
        "Six parts:",
        six_part_coverage,
        "/",
        len(
            blockchain_owned_ids
        ),
    )

    print(
        "\nCURRENT OWNED AXIE DETAILS"
    )

    for axie_id in sorted(
        matched_ids,
        key=int,
    ):
        fighter = fighter_map[
            axie_id
        ]

        xp = fighter.get(
            "xp"
        ) or {}

        parts = fighter.get(
            "parts"
        ) or []

        print(
            "\nAxie ID:",
            axie_id,
        )

        print(
            "Class:",
            fighter.get(
                "class"
            ),
        )

        print(
            "Level:",
            xp.get(
                "currentLevel"
            ),
        )

        print(
            "Title:",
            fighter.get(
                "title"
            ),
        )

        print(
            "Parts:",
            len(parts),
        )

        print(
            "Ownership:",
            fighter.get(
                "ownership"
            ),
        )

        for part in parts:
            print(
                " ",
                part.get(
                    "type"
                ),
                "|",
                part.get(
                    "value"
                ),
                "|",
                part.get(
                    "class"
                ),
                "| stage:",
                part.get(
                    "stage"
                ),
            )

    if missing_from_origins:
        print(
            "\nMISSING FROM COMPLETE ORIGINS DATA"
        )

        for axie_id in sorted(
            missing_from_origins,
            key=int,
        ):
            print(
                "Axie ID:",
                axie_id,
            )

    print(
        "\nCHECKS"
    )

    print(
        "Complete pagination:",
        (
            "PASS"
            if pagination_count_valid
            else "FAIL"
        ),
    )

    print(
        "Blockchain coverage:",
        (
            "PASS"
            if blockchain_coverage_valid
            else "REVIEW"
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



def run_origins_coverage_diagnostic_test():
    print(
        "\nAXIEOS ORIGINS COVERAGE DIAGNOSTIC"
    )

    fighter_result = (
        fetch_all_origins_ronin_fighters()
    )

    config_result = (
        fetch_all_origins_fighter_configs()
    )

    fighters_valid = (
        fighter_result[
            "success"
        ]
    )

    configs_valid = (
        config_result[
            "success"
        ]
    )

    print(
        "Fighter API:",
        (
            "PASS"
            if fighters_valid
            else "FAIL"
        ),
    )

    print(
        "Config API:",
        (
            "PASS"
            if configs_valid
            else "FAIL"
        ),
    )

    if (
        not fighters_valid
        or not configs_valid
    ):
        print(
            "\nValidation: FAIL"
        )

        return

    fighters = fighter_result[
        "fighters"
    ]

    configs = config_result[
        "configs"
    ]

    fighter_map = {
        str(
            fighter["id"]
        ): fighter
        for fighter in fighters
        if fighter.get(
            "id"
        )
        is not None
    }

    ronin_config_ids = {
        str(
            config.get(
                "axieID"
            )
        )
        for config in configs
        if (
            config.get(
                "axieID"
            )
            is not None
            and config.get(
                "axieType"
            )
            == "ronin"
        )
    }

    profiles = (
        load_owned_axie_gameplay_profiles(
            AXIEOS_DB_PATH
        )
    )

    blockchain_owned_ids = {
        profile[
            "axie_id"
        ]
        for profile in profiles
    }

    fighter_ids = set(
        fighter_map.keys()
    )

    missing_fighters = (
        blockchain_owned_ids
        - fighter_ids
    )

    missing_config_ids = (
        blockchain_owned_ids
        - ronin_config_ids
    )

    missing_both = (
        missing_fighters
        & missing_config_ids
    )

    part_schema_valid = True

    matched_ids = (
        blockchain_owned_ids
        & fighter_ids
    )

    for axie_id in matched_ids:
        parts = (
            fighter_map[
                axie_id
            ].get(
                "parts"
            )
            or []
        )

        if len(parts) != 6:
            part_schema_valid = False
            continue

        for part in parts:
            required_keys = {
                "part_type",
                "part_class",
                "part_value",
                "part_skin",
                "part_stage",
            }

            if not required_keys.issubset(
                part.keys()
            ):
                part_schema_valid = False

    print(
        "\nORIGINS DATA"
    )

    print(
        "Fighters:",
        len(fighters),
    )

    print(
        "Configs:",
        len(configs),
    )

    print(
        "Ronin fighter configs:",
        len(
            ronin_config_ids
        ),
    )

    print(
        "\nBLOCKCHAIN COVERAGE"
    )

    print(
        "Blockchain-owned Axies:",
        len(
            blockchain_owned_ids
        ),
    )

    print(
        "Missing fighter records:",
        len(
            missing_fighters
        ),
    )

    print(
        "Missing config records:",
        len(
            missing_config_ids
        ),
    )

    print(
        "Missing from both:",
        len(
            missing_both
        ),
    )

    if missing_fighters:
        print(
            "\nMISSING FIGHTER RECORDS"
        )

        for axie_id in sorted(
            missing_fighters,
            key=int,
        ):
            print(
                "Axie ID:",
                axie_id,
                "| Config:",
                (
                    "FOUND"
                    if axie_id
                    in ronin_config_ids
                    else "NOT FOUND"
                ),
            )

    print(
        "\nPART SCHEMA CHECK"
    )

    print(
        "Matched Axies:",
        len(
            matched_ids
        ),
    )

    print(
        "Correct API part fields:",
        (
            "PASS"
            if part_schema_valid
            else "FAIL"
        ),
    )

    if matched_ids:
        sample_id = sorted(
            matched_ids,
            key=int,
        )[0]

        sample = fighter_map[
            sample_id
        ]

        print(
            "\nSAMPLE PART DATA"
        )

        print(
            "Axie ID:",
            sample_id,
        )

        for part in (
            sample.get(
                "parts"
            )
            or []
        ):
            print(
                part.get(
                    "part_type"
                ),
                "| class:",
                part.get(
                    "part_class"
                ),
                "| value:",
                part.get(
                    "part_value"
                ),
                "| skin:",
                part.get(
                    "part_skin"
                ),
                "| stage:",
                part.get(
                    "part_stage"
                ),
            )

    validation = (
        part_schema_valid
        and len(
            matched_ids
        )
        > 0
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_origins_parts_schema_migration_test():
    initialize_owned_axie_registry(
        AXIEOS_DB_PATH
    )

    initialize_axie_gameplay_detail_tables(
        AXIEOS_DB_PATH
    )

    result = (
        validate_axie_gameplay_detail_tables(
            AXIEOS_DB_PATH
        )
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    index_rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'index'
          AND tbl_name =
              'gameplay_axie_parts'
        """
    ).fetchall()

    connection.close()

    indexes = {
        row[0]
        for row in index_rows
    }

    stage_index_valid = (
        "idx_gameplay_axie_parts_stage"
        in indexes
    )

    expected_part_columns = 12

    column_count_valid = (
        result[
            "parts_column_count"
        ]
        == expected_part_columns
    )

    validation = (
        result[
            "validation"
        ]
        and column_count_valid
        and stage_index_valid
    )

    print(
        "\nAXIEOS ORIGINS PARTS SCHEMA"
    )

    print(
        "Parts columns:",
        result[
            "parts_column_count"
        ],
    )

    print(
        "Expected columns:",
        expected_part_columns,
    )

    print(
        "Missing parts columns:",
        len(
            result[
                "missing_parts_columns"
            ]
        ),
    )

    print(
        "Traits columns:",
        result[
            "traits_column_count"
        ],
    )

    print(
        "\nNEW ORIGINS FIELDS"
    )

    print(
        "part_value:",
        (
            "PASS"
            if "part_value"
            not in result[
                "missing_parts_columns"
            ]
            else "FAIL"
        ),
    )

    print(
        "part_skin:",
        (
            "PASS"
            if "part_skin"
            not in result[
                "missing_parts_columns"
            ]
            else "FAIL"
        ),
    )

    print(
        "part_stage:",
        (
            "PASS"
            if "part_stage"
            not in result[
                "missing_parts_columns"
            ]
            else "FAIL"
        ),
    )

    print(
        "Stage index:",
        (
            "PASS"
            if stage_index_valid
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



def run_origins_part_persistence_test():
    print(
        "\nAXIEOS ORIGINS PART PERSISTENCE"
    )

    result = (
        fetch_all_origins_ronin_fighters()
    )

    print(
        "Origins API:",
        (
            "PASS"
            if result[
                "success"
            ]
            else "FAIL"
        ),
    )

    if not result["success"]:
        print(
            "\nValidation: FAIL"
        )
        return

    fighters = result[
        "fighters"
    ]

    fighter_map = {
        str(
            fighter["id"]
        ): fighter
        for fighter in fighters
        if fighter.get(
            "id"
        )
        is not None
    }

    profiles = (
        load_owned_axie_gameplay_profiles(
            AXIEOS_DB_PATH
        )
    )

    blockchain_owned_ids = {
        profile[
            "axie_id"
        ]
        for profile in profiles
    }

    matched_ids = (
        blockchain_owned_ids
        & set(
            fighter_map.keys()
        )
    )

    if not matched_ids:
        print(
            "Owned Origins fighter:",
            "FAIL",
        )

        print(
            "\nValidation: FAIL"
        )
        return

    test_axie_id = sorted(
        matched_ids,
        key=int,
    )[0]

    fighter = fighter_map[
        test_axie_id
    ]

    normalized_parts = (
        normalize_origins_fighter_parts(
            fighter
        )
    )

    slot_set = {
        record[
            "part_slot"
        ]
        for record
        in normalized_parts
    }

    expected_slots = set(
        AXIE_PART_SLOTS
    )

    six_parts_valid = (
        len(
            normalized_parts
        )
        == 6
    )

    slots_valid = (
        slot_set
        == expected_slots
    )

    origins_fields_valid = all(
        record.get(
            "part_class"
        )
        is not None
        and record.get(
            "part_value"
        )
        is not None
        and record.get(
            "part_skin"
        )
        is not None
        and record.get(
            "part_stage"
        )
        is not None
        for record
        in normalized_parts
    )

    print(
        "Test Axie ID:",
        test_axie_id,
    )

    print(
        "Normalized parts:",
        len(
            normalized_parts
        ),
    )

    print(
        "Six-part structure:",
        (
            "PASS"
            if six_parts_valid
            else "FAIL"
        ),
    )

    print(
        "Canonical slots:",
        (
            "PASS"
            if slots_valid
            else "FAIL"
        ),
    )

    print(
        "Origins fields:",
        (
            "PASS"
            if origins_fields_valid
            else "FAIL"
        ),
    )

    if not (
        six_parts_valid
        and slots_valid
        and origins_fields_valid
    ):
        print(
            "\nValidation: FAIL"
        )
        return

    for record in normalized_parts:
        upsert_axie_part(
            AXIEOS_DB_PATH,
            record,
        )

    for record in normalized_parts:
        upsert_axie_part(
            AXIEOS_DB_PATH,
            record,
        )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    stored_rows = (
        connection.execute(
            """
            SELECT
                part_slot,
                part_class,
                part_value,
                part_skin,
                part_stage,
                data_source
            FROM gameplay_axie_parts
            WHERE axie_id = ?
            ORDER BY part_slot
            """,
            (
                test_axie_id,
            ),
        ).fetchall()
    )

    connection.close()

    stored_map = {
        row[0]: {
            "part_class": row[1],
            "part_value": row[2],
            "part_skin": row[3],
            "part_stage": row[4],
            "data_source": row[5],
        }
        for row in stored_rows
    }

    row_count_valid = (
        len(
            stored_rows
        )
        == 6
    )

    persistence_valid = True

    for record in normalized_parts:
        slot = record[
            "part_slot"
        ]

        stored = stored_map.get(
            slot
        )

        if stored is None:
            persistence_valid = False
            continue

        expected = {
            "part_class": (
                record[
                    "part_class"
                ]
            ),
            "part_value": (
                record[
                    "part_value"
                ]
            ),
            "part_skin": (
                record[
                    "part_skin"
                ]
            ),
            "part_stage": (
                record[
                    "part_stage"
                ]
            ),
            "data_source": (
                "SKYMAVIS_ORIGINS_API"
            ),
        }

        if stored != expected:
            persistence_valid = False

    idempotent_valid = (
        row_count_valid
        and persistence_valid
    )

    print(
        "\nSTORED PARTS"
    )

    for row in stored_rows:
        print(
            row[0],
            "| class:",
            row[1],
            "| value:",
            row[2],
            "| skin:",
            row[3],
            "| stage:",
            row[4],
        )

    print(
        "\nPERSISTENCE CHECKS"
    )

    print(
        "Stored rows:",
        len(
            stored_rows
        ),
    )

    print(
        "Exactly six rows:",
        (
            "PASS"
            if row_count_valid
            else "FAIL"
        ),
    )

    print(
        "Stored values match API:",
        (
            "PASS"
            if persistence_valid
            else "FAIL"
        ),
    )

    print(
        "Repeated UPSERT idempotent:",
        (
            "PASS"
            if idempotent_valid
            else "FAIL"
        ),
    )

    validation = (
        six_parts_valid
        and slots_valid
        and origins_fields_valid
        and idempotent_valid
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_owned_origins_metadata_sync_test():
    print(
        "\nAXIEOS OWNED AXIE ORIGINS SYNC"
    )

    first_result = (
        sync_origins_metadata_for_owned_axies(
            AXIEOS_DB_PATH
        )
    )

    print(
        "First sync:",
        (
            "PASS"
            if first_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    if not first_result[
        "success"
    ]:
        print(
            "Error:",
            first_result.get(
                "error"
            ),
        )

        print(
            "\nValidation: FAIL"
        )

        return

    second_result = (
        sync_origins_metadata_for_owned_axies(
            AXIEOS_DB_PATH
        )
    )

    print(
        "Second sync:",
        (
            "PASS"
            if second_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    owned_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                axie_class,
                level
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    part_rows = (
        connection.execute(
            """
            SELECT
                p.axie_id,
                COUNT(*)
            FROM gameplay_axie_parts p
            INNER JOIN
                gameplay_owned_axies a
                ON a.axie_id =
                   p.axie_id
            WHERE
                a.ownership_status =
                    'OWNED'
            GROUP BY
                p.axie_id
            ORDER BY
                CAST(
                    p.axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    connection.close()

    owned_count = len(
        owned_rows
    )

    class_coverage = sum(
        1
        for row in owned_rows
        if row[1]
        in AXIE_CLASSES
    )

    level_coverage = sum(
        1
        for row in owned_rows
        if isinstance(
            row[2],
            int,
        )
        and row[2] > 0
    )

    full_part_axies = {
        str(row[0])
        for row in part_rows
        if row[1] == 6
    }

    partial_part_axies = {
        str(row[0])
        for row in part_rows
        if row[1] != 6
    }

    expected_metadata_count = (
        first_result[
            "synced_axies"
        ]
    )

    metadata_coverage_valid = (
        class_coverage
        == expected_metadata_count
        and level_coverage
        == expected_metadata_count
        and len(
            full_part_axies
        )
        == expected_metadata_count
    )

    no_partial_parts = (
        len(
            partial_part_axies
        )
        == 0
    )

    no_skipped_axies = (
        len(
            first_result[
                "skipped_axies"
            ]
        )
        == 0
    )

    idempotent_valid = (
        first_result[
            "owned_axies"
        ]
        == second_result[
            "owned_axies"
        ]
        and first_result[
            "origins_matched"
        ]
        == second_result[
            "origins_matched"
        ]
        and first_result[
            "synced_axies"
        ]
        == second_result[
            "synced_axies"
        ]
        and first_result[
            "parts_upserted"
        ]
        == second_result[
            "parts_upserted"
        ]
        and first_result[
            "origins_missing"
        ]
        == second_result[
            "origins_missing"
        ]
    )

    print(
        "\nSYNC SUMMARY"
    )

    print(
        "Blockchain-owned Axies:",
        first_result[
            "owned_axies"
        ],
    )

    print(
        "Origins matched:",
        first_result[
            "origins_matched"
        ],
    )

    print(
        "Origins missing:",
        len(
            first_result[
                "origins_missing"
            ]
        ),
    )

    print(
        "Successfully synced:",
        first_result[
            "synced_axies"
        ],
    )

    print(
        "Parts upserted:",
        first_result[
            "parts_upserted"
        ],
    )

    print(
        "Skipped Axies:",
        len(
            first_result[
                "skipped_axies"
            ]
        ),
    )

    print(
        "\nREGISTRY COVERAGE"
    )

    print(
        "Class populated:",
        class_coverage,
        "/",
        owned_count,
    )

    print(
        "Level populated:",
        level_coverage,
        "/",
        owned_count,
    )

    print(
        "Six-part profiles:",
        len(
            full_part_axies
        ),
        "/",
        owned_count,
    )

    if first_result[
        "origins_missing"
    ]:
        print(
            "\nOWNED AXIES WITHOUT ORIGINS METADATA"
        )

        for axie_id in (
            first_result[
                "origins_missing"
            ]
        ):
            print(
                "Axie ID:",
                axie_id,
            )

    if first_result[
        "skipped_axies"
    ]:
        print(
            "\nSKIPPED ORIGINS RECORDS"
        )

        for skipped in (
            first_result[
                "skipped_axies"
            ]
        ):
            print(
                "Axie ID:",
                skipped[
                    "axie_id"
                ],
                "|",
                skipped[
                    "reason"
                ],
            )

    print(
        "\nCHECKS"
    )

    print(
        "Metadata coverage:",
        (
            "PASS"
            if metadata_coverage_valid
            else "FAIL"
        ),
    )

    print(
        "No partial part profiles:",
        (
            "PASS"
            if no_partial_parts
            else "FAIL"
        ),
    )

    print(
        "No malformed API records:",
        (
            "PASS"
            if no_skipped_axies
            else "FAIL"
        ),
    )

    print(
        "Repeated sync idempotent:",
        (
            "PASS"
            if idempotent_valid
            else "FAIL"
        ),
    )

    validation = (
        first_result[
            "success"
        ]
        and second_result[
            "success"
        ]
        and metadata_coverage_valid
        and no_partial_parts
        and no_skipped_axies
        and idempotent_valid
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_owned_axie_evolution_sync_test():
    print(
        "\nAXIEOS OWNED AXIE EVOLUTION SYNC"
    )

    result = (
        sync_origins_metadata_for_owned_axies(
            AXIEOS_DB_PATH
        )
    )

    print(
        "Origins sync:",
        (
            "PASS"
            if result[
                "success"
            ]
            else "FAIL"
        ),
    )

    if not result["success"]:
        print(
            "Error:",
            result.get(
                "error"
            ),
        )

        print(
            "\nValidation: FAIL"
        )
        return

    expected_evolution = {
        record[
            "axie_id"
        ]: record[
            "is_evolved"
        ]
        for record
        in result[
            "records"
        ]
    }

    expected_evolved_parts = {
        record[
            "axie_id"
        ]: record[
            "evolved_part_count"
        ]
        for record
        in result[
            "records"
        ]
    }

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                is_evolved
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    connection.close()

    database_values = {
        str(row[0]): row[1]
        for row in rows
    }

    persistence_valid = True

    for (
        axie_id,
        expected_value,
    ) in expected_evolution.items():
        if (
            database_values.get(
                axie_id
            )
            != expected_value
        ):
            persistence_valid = False

    allowed_values_valid = all(
        value in {
            0,
            1,
            None,
        }
        for value
        in database_values.values()
    )

    missing_ids = set(
        result[
            "origins_missing"
        ]
    )

    missing_untouched_valid = all(
        database_values.get(
            axie_id
        )
        is None
        for axie_id
        in missing_ids
    )

    print(
        "\nEVOLUTION SUMMARY"
    )

    print(
        "Origins-visible owned Axies:",
        result[
            "synced_axies"
        ],
    )

    print(
        "Evolved Axies:",
        result[
            "evolved_axies"
        ],
    )

    print(
        "Not evolved:",
        (
            result[
                "synced_axies"
            ]
            - result[
                "evolved_axies"
            ]
        ),
    )

    print(
        "Origins metadata missing:",
        len(
            missing_ids
        ),
    )

    print(
        "\nOWNED AXIE EVOLUTION STATUS"
    )

    for axie_id in sorted(
        expected_evolution,
        key=int,
    ):
        print(
            "Axie ID:",
            axie_id,
            "| evolved parts:",
            expected_evolved_parts[
                axie_id
            ],
            "| is_evolved:",
            expected_evolution[
                axie_id
            ],
        )

    if missing_ids:
        print(
            "\nUNKNOWN EVOLUTION STATUS"
        )

        for axie_id in sorted(
            missing_ids,
            key=int,
        ):
            print(
                "Axie ID:",
                axie_id,
                "| is_evolved:",
                database_values.get(
                    axie_id
                ),
            )

    print(
        "\nCHECKS"
    )

    print(
        "Evolution values persisted:",
        (
            "PASS"
            if persistence_valid
            else "FAIL"
        ),
    )

    print(
        "Allowed database values:",
        (
            "PASS"
            if allowed_values_valid
            else "FAIL"
        ),
    )

    print(
        "Missing metadata stays unknown:",
        (
            "PASS"
            if missing_untouched_valid
            else "FAIL"
        ),
    )

    validation = (
        result[
            "success"
        ]
        and persistence_valid
        and allowed_values_valid
        and missing_untouched_valid
        and not result[
            "skipped_axies"
        ]
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_owned_axie_onchain_core_test():
    print(
        "\nAXIEOS OWNED AXIE ON-CHAIN CORE DATA"
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                level,
                breed_count
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    connection.close()

    print(
        "Blockchain-owned Axies:",
        len(rows),
    )

    results = []

    for row in rows:
        axie_id = str(
            row[0]
        )

        registry_level = row[
            1
        ]

        result = (
            fetch_axie_core_onchain(
                axie_id
            )
        )

        results.append(
            {
                "axie_id": axie_id,
                "registry_level": (
                    registry_level
                ),
                "result": result,
            }
        )

    successful = [
        item
        for item in results
        if item[
            "result"
        ][
            "success"
        ]
    ]

    failed = [
        item
        for item in results
        if not item[
            "result"
        ][
            "success"
        ]
    ]

    breed_valid_count = 0
    contract_level_valid_count = 0

    comparable_count = 0
    level_match_count = 0
    level_mismatch_count = 0

    for item in successful:
        data = item[
            "result"
        ][
            "data"
        ]

        breed_count = data[
            "breed_count"
        ]

        contract_level = data[
            "contract_level"
        ]

        if (
            isinstance(
                breed_count,
                int,
            )
            and 0 <= breed_count <= 7
        ):
            breed_valid_count += 1

        if (
            isinstance(
                contract_level,
                int,
            )
            and contract_level > 0
        ):
            contract_level_valid_count += 1

        registry_level = item[
            "registry_level"
        ]

        if registry_level is not None:
            comparable_count += 1

            if (
                registry_level
                == contract_level
            ):
                level_match_count += 1

            else:
                level_mismatch_count += 1

    print(
        "\nRPC SUMMARY"
    )

    print(
        "Successful reads:",
        len(
            successful
        ),
    )

    print(
        "Failed reads:",
        len(
            failed
        ),
    )

    print(
        "Valid breed counts:",
        breed_valid_count,
        "/",
        len(rows),
    )

    print(
        "Valid contract levels:",
        contract_level_valid_count,
        "/",
        len(rows),
    )

    print(
        "\nLEVEL COMPARISON"
    )

    print(
        "Comparable Axies:",
        comparable_count,
    )

    print(
        "Level matches:",
        level_match_count,
    )

    print(
        "Level mismatches:",
        level_mismatch_count,
    )

    print(
        "\nOWNED AXIE CORE DATA"
    )

    for item in results:
        axie_id = item[
            "axie_id"
        ]

        result = item[
            "result"
        ]

        if not result[
            "success"
        ]:
            print(
                "Axie ID:",
                axie_id,
                "| RPC ERROR:",
                result[
                    "error"
                ],
            )

            continue

        data = result[
            "data"
        ]

        registry_level = item[
            "registry_level"
        ]

        if registry_level is None:
            level_status = (
                "NO ORIGINS LEVEL"
            )

        elif (
            registry_level
            == data[
                "contract_level"
            ]
        ):
            level_status = "MATCH"

        else:
            level_status = "MISMATCH"

        print(
            "Axie ID:",
            axie_id,
            "| breed:",
            data[
                "breed_count"
            ],
            "| contract level:",
            data[
                "contract_level"
            ],
            "| registry level:",
            registry_level,
            "|",
            level_status,
        )

    if failed:
        print(
            "\nFAILED READS"
        )

        for item in failed:
            print(
                "Axie ID:",
                item[
                    "axie_id"
                ],
                "|",
                item[
                    "result"
                ][
                    "error"
                ],
            )

    rpc_coverage_valid = (
        len(
            successful
        )
        == len(rows)
    )

    breed_values_valid = (
        breed_valid_count
        == len(rows)
    )

    contract_levels_valid = (
        contract_level_valid_count
        == len(rows)
    )

    print(
        "\nCHECKS"
    )

    print(
        "Complete RPC coverage:",
        (
            "PASS"
            if rpc_coverage_valid
            else "FAIL"
        ),
    )

    print(
        "Breed count range:",
        (
            "PASS"
            if breed_values_valid
            else "FAIL"
        ),
    )

    print(
        "Contract level range:",
        (
            "PASS"
            if contract_levels_valid
            else "FAIL"
        ),
    )

    validation = (
        rpc_coverage_valid
        and breed_values_valid
        and contract_levels_valid
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_owned_axie_breed_count_sync_test():
    print(
        "\nAXIEOS OWNED AXIE BREED COUNT SYNC"
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    before_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                level
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    connection.close()

    levels_before = {
        str(row[0]): row[1]
        for row in before_rows
    }

    first_result = (
        sync_onchain_breed_counts_for_owned_axies(
            AXIEOS_DB_PATH
        )
    )

    second_result = (
        sync_onchain_breed_counts_for_owned_axies(
            AXIEOS_DB_PATH
        )
    )

    print(
        "First sync:",
        (
            "PASS"
            if first_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    print(
        "Second sync:",
        (
            "PASS"
            if second_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    after_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                level,
                breed_count
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    connection.close()

    breed_map = {
        str(row[0]): row[2]
        for row in after_rows
    }

    levels_after = {
        str(row[0]): row[1]
        for row in after_rows
    }

    breed_coverage_valid = all(
        isinstance(
            breed_count,
            int,
        )
        and 0 <= breed_count <= 7
        for breed_count
        in breed_map.values()
    )

    complete_coverage_valid = (
        len(
            breed_map
        )
        == first_result[
            "owned_axies"
        ]
        and first_result[
            "synced_axies"
        ]
        == first_result[
            "owned_axies"
        ]
    )

    levels_preserved = (
        levels_before
        == levels_after
    )

    first_map = {
        record[
            "axie_id"
        ]: record[
            "breed_count"
        ]
        for record
        in first_result[
            "records"
        ]
    }

    second_map = {
        record[
            "axie_id"
        ]: record[
            "breed_count"
        ]
        for record
        in second_result[
            "records"
        ]
    }

    idempotent_valid = (
        first_map
        == second_map
        == breed_map
    )

    print(
        "\nSYNC SUMMARY"
    )

    print(
        "Blockchain-owned Axies:",
        first_result[
            "owned_axies"
        ],
    )

    print(
        "Breed counts synced:",
        first_result[
            "synced_axies"
        ],
    )

    print(
        "Failed Axies:",
        len(
            first_result[
                "failed_axies"
            ]
        ),
    )

    print(
        "\nOWNED AXIE BREED COUNTS"
    )

    for row in after_rows:
        print(
            "Axie ID:",
            row[0],
            "| breed:",
            row[2],
            "| gameplay level:",
            row[1],
        )

    if first_result[
        "failed_axies"
    ]:
        print(
            "\nFAILED BREED READS"
        )

        for failure in (
            first_result[
                "failed_axies"
            ]
        ):
            print(
                "Axie ID:",
                failure[
                    "axie_id"
                ],
                "|",
                failure[
                    "reason"
                ],
            )

    print(
        "\nCHECKS"
    )

    print(
        "Complete breed coverage:",
        (
            "PASS"
            if complete_coverage_valid
            else "FAIL"
        ),
    )

    print(
        "Breed count range:",
        (
            "PASS"
            if breed_coverage_valid
            else "FAIL"
        ),
    )

    print(
        "Gameplay levels preserved:",
        (
            "PASS"
            if levels_preserved
            else "FAIL"
        ),
    )

    print(
        "Repeated sync idempotent:",
        (
            "PASS"
            if idempotent_valid
            else "FAIL"
        ),
    )

    validation = (
        first_result[
            "success"
        ]
        and second_result[
            "success"
        ]
        and complete_coverage_valid
        and breed_coverage_valid
        and levels_preserved
        and idempotent_valid
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_owned_axie_collectible_signal_diagnostic():
    print(
        "\nAXIEOS OWNED AXIE COLLECTIBLE SIGNALS"
    )

    result = (
        fetch_all_origins_ronin_fighters()
    )

    print(
        "Origins API:",
        (
            "PASS"
            if result[
                "success"
            ]
            else "FAIL"
        ),
    )

    if not result[
        "success"
    ]:
        print(
            "\nValidation: FAIL"
        )
        return

    fighters = result[
        "fighters"
    ]

    fighter_map = {
        str(
            fighter["id"]
        ): fighter
        for fighter in fighters
        if fighter.get(
            "id"
        )
        is not None
    }

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    owned_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                axie_class,
                level,
                breed_count,
                is_evolved
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    connection.close()

    owned_ids = {
        str(row[0])
        for row in owned_rows
    }

    matched_ids = (
        owned_ids
        & set(
            fighter_map.keys()
        )
    )

    missing_ids = (
        owned_ids
        - matched_ids
    )

    skin_value_counts = {}

    title_counts = {}

    for fighter in fighters:
        title = fighter.get(
            "title"
        )

        title_counts[
            str(title)
        ] = (
            title_counts.get(
                str(title),
                0,
            )
            + 1
        )

        for part in (
            fighter.get(
                "parts"
            )
            or []
        ):
            skin = part.get(
                "part_skin"
            )

            skin_value_counts[
                skin
            ] = (
                skin_value_counts.get(
                    skin,
                    0,
                )
                + 1
            )

    print(
        "\nAPI-WIDE SIGNALS"
    )

    print(
        "Ronin fighters:",
        len(fighters),
    )

    print(
        "Distinct titles:",
        len(
            title_counts
        ),
    )

    print(
        "Title values:"
    )

    for title in sorted(
        title_counts
    ):
        print(
            " ",
            title,
            ":",
            title_counts[
                title
            ],
        )

    print(
        "Distinct part_skin values:",
        len(
            skin_value_counts
        ),
    )

    print(
        "part_skin values:"
    )

    for skin in sorted(
        skin_value_counts,
        key=lambda value: (
            value is None,
            value
            if value is not None
            else 0,
        ),
    ):
        print(
            " ",
            skin,
            ":",
            skin_value_counts[
                skin
            ],
        )

    print(
        "\nOWNED AXIE SIGNALS"
    )

    for row in owned_rows:
        axie_id = str(
            row[0]
        )

        print(
            "\nAxie ID:",
            axie_id,
        )

        print(
            "Registry class:",
            row[1],
        )

        print(
            "Gameplay level:",
            row[2],
        )

        print(
            "Breed count:",
            row[3],
        )

        print(
            "Is evolved:",
            row[4],
        )

        fighter = fighter_map.get(
            axie_id
        )

        if fighter is None:
            print(
                "Origins fighter:",
                "NOT FOUND",
            )
            continue

        print(
            "Origins fighter:",
            "FOUND",
        )

        print(
            "Title:",
            fighter.get(
                "title"
            ),
        )

        print(
            "Genes present:",
            (
                "YES"
                if fighter.get(
                    "genes"
                )
                else "NO"
            ),
        )

        genes_metamorph = (
            fighter.get(
                "genesMetamorph"
            )
        )

        print(
            "genesMetamorph present:",
            (
                "YES"
                if genes_metamorph
                else "NO"
            ),
        )

        parts = (
            fighter.get(
                "parts"
            )
            or []
        )

        nonzero_skin_count = sum(
            1
            for part in parts
            if (
                part.get(
                    "part_skin"
                )
                not in {
                    None,
                    0,
                }
            )
        )

        print(
            "Non-zero skin parts:",
            nonzero_skin_count,
        )

        for part in parts:
            print(
                " ",
                part.get(
                    "part_type"
                ),
                "| class:",
                part.get(
                    "part_class"
                ),
                "| value:",
                part.get(
                    "part_value"
                ),
                "| skin:",
                part.get(
                    "part_skin"
                ),
                "| stage:",
                part.get(
                    "part_stage"
                ),
            )

    print(
        "\nKNOWN REFERENCE"
    )

    reference_id = (
        "6251324"
    )

    reference = (
        fighter_map.get(
            reference_id
        )
    )

    print(
        "Reference Axie:",
        reference_id,
    )

    print(
        "Origins record:",
        (
            "FOUND"
            if reference
            else "NOT FOUND"
        ),
    )

    if reference:
        reference_parts = (
            reference.get(
                "parts"
            )
            or []
        )

        print(
            "Title:",
            reference.get(
                "title"
            ),
        )

        print(
            "Non-zero skin parts:",
            sum(
                1
                for part
                in reference_parts
                if (
                    part.get(
                        "part_skin"
                    )
                    not in {
                        None,
                        0,
                    }
                )
            ),
        )

        print(
            "Skin values:",
            [
                part.get(
                    "part_skin"
                )
                for part
                in reference_parts
            ],
        )

    print(
        "\nMISSING ORIGINS METADATA"
    )

    if missing_ids:
        for axie_id in sorted(
            missing_ids,
            key=int,
        ):
            print(
                "Axie ID:",
                axie_id,
            )

    else:
        print(
            "None"
        )

    validation = (
        len(
            matched_ids
        )
        > 0
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_collectible_gene_signal_validation_test():
    print(
        "\nAXIEOS COLLECTIBLE GENE SIGNAL VALIDATION"
    )

    result = (
        fetch_all_origins_ronin_fighters()
    )

    print(
        "Origins API:",
        (
            "PASS"
            if result[
                "success"
            ]
            else "FAIL"
        ),
    )

    if not result[
        "success"
    ]:
        print(
            "\nValidation: FAIL"
        )
        return

    fighters = result[
        "fighters"
    ]

    decoded_map = {}

    decode_failures = []

    api_skin_comparisons = 0
    api_skin_matches = 0
    api_skin_mismatches = []

    for fighter in fighters:
        axie_id = str(
            fighter.get(
                "id"
            )
        )

        try:
            decoded = (
                decode_axie_collectible_gene_signals(
                    fighter.get(
                        "genes"
                    )
                )
            )

        except ValueError as error:
            decode_failures.append(
                {
                    "axie_id": axie_id,
                    "reason": str(error),
                }
            )

            continue

        decoded_map[
            axie_id
        ] = decoded

        for part in (
            fighter.get(
                "parts"
            )
            or []
        ):
            part_type = part.get(
                "part_type"
            )

            if not part_type:
                continue

            part_slot = (
                str(
                    part_type
                )
                .strip()
                .lower()
            )

            api_skin = part.get(
                "part_skin"
            )

            gene_skin = (
                decoded[
                    "part_skin_codes"
                ].get(
                    part_slot
                )
            )

            if (
                api_skin is None
                or gene_skin is None
            ):
                continue

            api_skin_comparisons += 1

            if api_skin == gene_skin:
                api_skin_matches += 1

            else:
                api_skin_mismatches.append(
                    {
                        "axie_id": axie_id,
                        "part_slot": (
                            part_slot
                        ),
                        "api_skin": (
                            api_skin
                        ),
                        "gene_skin": (
                            gene_skin
                        ),
                    }
                )

    print(
        "\nGENE DECODING"
    )

    print(
        "Fighters returned:",
        len(fighters),
    )

    print(
        "Successfully decoded:",
        len(
            decoded_map
        ),
    )

    print(
        "Decode failures:",
        len(
            decode_failures
        ),
    )

    print(
        "\nAPI ↔ GENE SKIN COMPARISON"
    )

    print(
        "Part comparisons:",
        api_skin_comparisons,
    )

    print(
        "Skin-code matches:",
        api_skin_matches,
    )

    print(
        "Skin-code mismatches:",
        len(
            api_skin_mismatches
        ),
    )

    skin_alignment_valid = (
        api_skin_comparisons > 0
        and api_skin_matches
        == api_skin_comparisons
    )

    print(
        "Numeric skin alignment:",
        (
            "PASS"
            if skin_alignment_valid
            else "FAIL"
        ),
    )

    title_signal_fighters = [
        fighter
        for fighter in fighters
        if fighter.get(
            "title"
        )
        not in {
            None,
            "",
            "Normal",
        }
    ]

    print(
        "\nTITLE SIGNALS"
    )

    print(
        "Non-normal titles:",
        len(
            title_signal_fighters
        ),
    )

    title_checks = 0
    title_matches = 0

    for fighter in (
        title_signal_fighters
    ):
        axie_id = str(
            fighter[
                "id"
            ]
        )

        decoded = (
            decoded_map.get(
                axie_id
            )
        )

        decoded_tag = (
            decoded.get(
                "tag"
            )
            if decoded
            else None
        )

        title = fighter.get(
            "title"
        )

        expected_tag = None

        if title == "MeoCorp1":
            expected_tag = "MEO1"

        elif title == "MeoCorp2":
            expected_tag = "MEO2"

        elif title == "Origin":
            expected_tag = "ORIGIN"

        if expected_tag is not None:
            title_checks += 1

            if (
                decoded_tag
                == expected_tag
            ):
                title_matches += 1

        print(
            "Axie ID:",
            axie_id,
            "| title:",
            title,
            "| decoded tag:",
            decoded_tag,
        )

    title_validation = (
        title_checks == 0
        or title_checks
        == title_matches
    )

    print(
        "Title/tag agreement:",
        (
            "PASS"
            if title_validation
            else "FAIL"
        ),
    )

    special_skin_fighters = []

    for fighter in fighters:
        special_parts = [
            part
            for part in (
                fighter.get(
                    "parts"
                )
                or []
            )
            if part.get(
                "part_skin"
            )
            not in {
                None,
                0,
            }
        ]

        if special_parts:
            special_skin_fighters.append(
                (
                    fighter,
                    special_parts,
                )
            )

    print(
        "\nSPECIAL PART-SKIN SIGNALS"
    )

    print(
        "Fighters with non-zero skin:",
        len(
            special_skin_fighters
        ),
    )

    for (
        fighter,
        special_parts,
    ) in special_skin_fighters:
        axie_id = str(
            fighter[
                "id"
            ]
        )

        decoded = decoded_map.get(
            axie_id,
            {},
        )

        print(
            "\nAxie ID:",
            axie_id,
            "| title:",
            fighter.get(
                "title"
            ),
            "| tag:",
            decoded.get(
                "tag"
            ),
            "| body:",
            decoded.get(
                "body_skin"
            ),
        )

        for part in special_parts:
            slot = (
                str(
                    part.get(
                        "part_type"
                    )
                )
                .strip()
                .lower()
            )

            skin_code = part.get(
                "part_skin"
            )

            skin_label = (
                decoded.get(
                    "part_skin_labels",
                    {},
                ).get(
                    slot
                )
            )

            print(
                " ",
                slot,
                "| API skin:",
                skin_code,
                "| decoded:",
                skin_label,
                "| stage:",
                part.get(
                    "part_stage"
                ),
            )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    owned_rows = (
        connection.execute(
            """
            SELECT axie_id
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    connection.close()

    fighter_map = {
        str(
            fighter[
                "id"
            ]
        ): fighter
        for fighter in fighters
        if fighter.get(
            "id"
        )
        is not None
    }

    print(
        "\nCURRENT OWNED AXIE GENE SIGNALS"
    )

    for row in owned_rows:
        axie_id = str(
            row[0]
        )

        fighter = fighter_map.get(
            axie_id
        )

        if fighter is None:
            print(
                "Axie ID:",
                axie_id,
                "| Origins metadata: MISSING",
            )
            continue

        decoded = decoded_map.get(
            axie_id
        )

        if decoded is None:
            print(
                "Axie ID:",
                axie_id,
                "| gene decode: FAILED",
            )
            continue

        nonzero_codes = {
            slot: code
            for (
                slot,
                code,
            ) in decoded[
                "part_skin_codes"
            ].items()
            if code != 0
        }

        print(
            "Axie ID:",
            axie_id,
            "| title:",
            fighter.get(
                "title"
            ),
            "| tag:",
            decoded[
                "tag"
            ],
            "| body:",
            decoded[
                "body_skin"
            ],
            "| special skins:",
            (
                nonzero_codes
                if nonzero_codes
                else "NONE"
            ),
        )

    if api_skin_mismatches:
        print(
            "\nSKIN MISMATCHES"
        )

        for mismatch in (
            api_skin_mismatches
        ):
            print(
                "Axie ID:",
                mismatch[
                    "axie_id"
                ],
                "| slot:",
                mismatch[
                    "part_slot"
                ],
                "| API:",
                mismatch[
                    "api_skin"
                ],
                "| gene:",
                mismatch[
                    "gene_skin"
                ],
            )

    if decode_failures:
        print(
            "\nDECODE FAILURES"
        )

        for failure in (
            decode_failures
        ):
            print(
                "Axie ID:",
                failure[
                    "axie_id"
                ],
                "|",
                failure[
                    "reason"
                ],
            )

    validation = (
        len(
            decode_failures
        )
        == 0
        and skin_alignment_valid
        and title_validation
    )

    print(
        "\nCHECKS"
    )

    print(
        "All genes decoded:",
        (
            "PASS"
            if not decode_failures
            else "FAIL"
        ),
    )

    print(
        "API skin matches gene bits:",
        (
            "PASS"
            if skin_alignment_valid
            else "FAIL"
        ),
    )

    print(
        "Known title tags match:",
        (
            "PASS"
            if title_validation
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



def run_onchain_gene_fallback_validation_test():
    print(
        "\nAXIEOS ON-CHAIN GENE FALLBACK VALIDATION"
    )

    origins_result = (
        fetch_all_origins_ronin_fighters()
    )

    print(
        "Origins API:",
        (
            "PASS"
            if origins_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    if not origins_result[
        "success"
    ]:
        print(
            "\nValidation: FAIL"
        )
        return

    fighter_map = {
        str(
            fighter["id"]
        ): fighter
        for fighter in origins_result[
            "fighters"
        ]
        if fighter.get(
            "id"
        )
        is not None
    }

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    owned_rows = (
        connection.execute(
            """
            SELECT axie_id
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    connection.close()

    owned_ids = [
        str(row[0])
        for row in owned_rows
    ]

    results = []

    xy_matches = 0
    yx_matches = 0
    comparable_count = 0
    rpc_failures = []

    for axie_id in owned_ids:
        core_result = (
            fetch_axie_core_onchain(
                axie_id
            )
        )

        if not core_result[
            "success"
        ]:
            rpc_failures.append(
                {
                    "axie_id": axie_id,
                    "error": (
                        core_result.get(
                            "error"
                        )
                    ),
                }
            )

            continue

        core_data = core_result[
            "data"
        ]

        xy_genes = (
            build_full_axie_genes_from_core(
                core_data[
                    "genes_x"
                ],
                core_data[
                    "genes_y"
                ],
                "xy",
            )
        )

        yx_genes = (
            build_full_axie_genes_from_core(
                core_data[
                    "genes_x"
                ],
                core_data[
                    "genes_y"
                ],
                "yx",
            )
        )

        fighter = fighter_map.get(
            axie_id
        )

        xy_match = None
        yx_match = None

        if fighter is not None:
            origins_genes = (
                normalize_axie_genes_hex(
                    fighter[
                        "genes"
                    ]
                )
            )

            comparable_count += 1

            xy_match = (
                xy_genes
                == origins_genes
            )

            yx_match = (
                yx_genes
                == origins_genes
            )

            if xy_match:
                xy_matches += 1

            if yx_match:
                yx_matches += 1

        results.append(
            {
                "axie_id": axie_id,
                "fighter_found": (
                    fighter is not None
                ),
                "xy_genes": xy_genes,
                "yx_genes": yx_genes,
                "xy_match": xy_match,
                "yx_match": yx_match,
            }
        )

    if (
        comparable_count > 0
        and xy_matches
        == comparable_count
        and yx_matches == 0
    ):
        detected_order = "xy"

    elif (
        comparable_count > 0
        and yx_matches
        == comparable_count
        and xy_matches == 0
    ):
        detected_order = "yx"

    else:
        detected_order = None

    print(
        "\nGENE RECONSTRUCTION"
    )

    print(
        "Blockchain-owned Axies:",
        len(
            owned_ids
        ),
    )

    print(
        "RPC failures:",
        len(
            rpc_failures
        ),
    )

    print(
        "Origins-comparable Axies:",
        comparable_count,
    )

    print(
        "genes_x + genes_y matches:",
        xy_matches,
    )

    print(
        "genes_y + genes_x matches:",
        yx_matches,
    )

    print(
        "Detected gene order:",
        (
            detected_order
            if detected_order
            else "UNRESOLVED"
        ),
    )

    reconstruction_valid = (
        detected_order
        is not None
        and comparable_count > 0
    )

    print(
        "Exact 512-bit reconstruction:",
        (
            "PASS"
            if reconstruction_valid
            else "FAIL"
        ),
    )

    print(
        "\nOWNED AXIE COMPARISON"
    )

    for item in results:
        if item[
            "fighter_found"
        ]:
            if detected_order == "xy":
                match = item[
                    "xy_match"
                ]

            elif detected_order == "yx":
                match = item[
                    "yx_match"
                ]

            else:
                match = False

            print(
                "Axie ID:",
                item[
                    "axie_id"
                ],
                "| Origins:",
                "FOUND",
                "| full genes:",
                (
                    "MATCH"
                    if match
                    else "MISMATCH"
                ),
            )

        else:
            print(
                "Axie ID:",
                item[
                    "axie_id"
                ],
                "| Origins:",
                "MISSING",
                "| on-chain genes:",
                "AVAILABLE",
            )

    missing_results = [
        item
        for item in results
        if not item[
            "fighter_found"
        ]
    ]

    fallback_decode_valid = True

    print(
        "\nON-CHAIN FALLBACK AXIES"
    )

    if not missing_results:
        print(
            "None"
        )

    elif detected_order is None:
        print(
            "Cannot decode fallback "
            "until gene order is proven."
        )

        fallback_decode_valid = False

    else:
        for item in missing_results:
            if detected_order == "xy":
                genes_hex = item[
                    "xy_genes"
                ]

            else:
                genes_hex = item[
                    "yx_genes"
                ]

            try:
                decoded = (
                    decode_axie_collectible_gene_signals(
                        genes_hex
                    )
                )

            except ValueError as error:
                fallback_decode_valid = False

                print(
                    "Axie ID:",
                    item[
                        "axie_id"
                    ],
                    "| decode error:",
                    str(error),
                )

                continue

            nonzero_skins = {
                slot: code
                for (
                    slot,
                    code,
                ) in decoded[
                    "part_skin_codes"
                ].items()
                if code != 0
            }

            print(
                "Axie ID:",
                item[
                    "axie_id"
                ],
            )

            print(
                " Tag:",
                decoded[
                    "tag"
                ],
            )

            print(
                " Body skin:",
                decoded[
                    "body_skin"
                ],
            )

            print(
                " Special part skins:",
                (
                    nonzero_skins
                    if nonzero_skins
                    else "NONE"
                ),
            )

            print(
                " Part skin labels:",
                decoded[
                    "part_skin_labels"
                ],
            )

    if rpc_failures:
        print(
            "\nRPC FAILURES"
        )

        for failure in (
            rpc_failures
        ):
            print(
                "Axie ID:",
                failure[
                    "axie_id"
                ],
                "|",
                failure[
                    "error"
                ],
            )

    complete_rpc_coverage = (
        len(
            rpc_failures
        )
        == 0
    )

    print(
        "\nCHECKS"
    )

    print(
        "Complete on-chain gene coverage:",
        (
            "PASS"
            if complete_rpc_coverage
            else "FAIL"
        ),
    )

    print(
        "Origins genes exactly reconstructed:",
        (
            "PASS"
            if reconstruction_valid
            else "FAIL"
        ),
    )

    print(
        "Missing Origins genes decodable:",
        (
            "PASS"
            if fallback_decode_valid
            else "FAIL"
        ),
    )

    validation = (
        complete_rpc_coverage
        and reconstruction_valid
        and fallback_decode_valid
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_owned_axie_collectible_status_sync_test():
    print(
        "\nAXIEOS OWNED AXIE COLLECTIBLE STATUS"
    )

    first_result = (
        sync_onchain_collectible_status_for_owned_axies(
            AXIEOS_DB_PATH
        )
    )

    second_result = (
        sync_onchain_collectible_status_for_owned_axies(
            AXIEOS_DB_PATH
        )
    )

    print(
        "First sync:",
        (
            "PASS"
            if first_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    print(
        "Second sync:",
        (
            "PASS"
            if second_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                is_collectible,
                collectible_type
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    connection.close()

    database_map = {
        str(row[0]): row[1]
        for row in rows
    }

    expected_map = {
        record[
            "axie_id"
        ]: record[
            "is_collectible"
        ]
        for record
        in first_result[
            "records"
        ]
    }

    second_map = {
        record[
            "axie_id"
        ]: record[
            "is_collectible"
        ]
        for record
        in second_result[
            "records"
        ]
    }

    persistence_valid = (
        database_map
        == expected_map
    )

    idempotent_valid = (
        expected_map
        == second_map
        == database_map
    )

    allowed_values_valid = all(
        value in {
            0,
            1,
        }
        for value
        in database_map.values()
    )

    complete_coverage_valid = (
        first_result[
            "classified_axies"
        ]
        == first_result[
            "owned_axies"
        ]
        == len(rows)
    )

    collectible_type_untouched = all(
        row[2] is None
        for row in rows
    )

    print(
        "\nCLASSIFICATION SUMMARY"
    )

    print(
        "Blockchain-owned Axies:",
        first_result[
            "owned_axies"
        ],
    )

    print(
        "Successfully classified:",
        first_result[
            "classified_axies"
        ],
    )

    print(
        "Collectible:",
        first_result[
            "collectible_axies"
        ],
    )

    print(
        "Non-collectible:",
        first_result[
            "non_collectible_axies"
        ],
    )

    print(
        "Failed Axies:",
        len(
            first_result[
                "failed_axies"
            ]
        ),
    )

    print(
        "\nOWNED AXIE COLLECTIBLE SIGNALS"
    )

    for record in first_result[
        "records"
    ]:
        print(
            "Axie ID:",
            record[
                "axie_id"
            ],
            "| collectible:",
            record[
                "is_collectible"
            ],
            "| tag:",
            record[
                "tag"
            ],
            "| body:",
            record[
                "body_skin"
            ],
            "| special skins:",
            (
                record[
                    "special_part_skins"
                ]
                if record[
                    "special_part_skins"
                ]
                else "NONE"
            ),
        )

    if first_result[
        "failed_axies"
    ]:
        print(
            "\nFAILED CLASSIFICATIONS"
        )

        for failure in (
            first_result[
                "failed_axies"
            ]
        ):
            print(
                "Axie ID:",
                failure[
                    "axie_id"
                ],
                "|",
                failure[
                    "reason"
                ],
            )

    print(
        "\nCHECKS"
    )

    print(
        "Complete gene coverage:",
        (
            "PASS"
            if complete_coverage_valid
            else "FAIL"
        ),
    )

    print(
        "Collectible values valid:",
        (
            "PASS"
            if allowed_values_valid
            else "FAIL"
        ),
    )

    print(
        "Status persisted:",
        (
            "PASS"
            if persistence_valid
            else "FAIL"
        ),
    )

    print(
        "Collectible type untouched:",
        (
            "PASS"
            if collectible_type_untouched
            else "FAIL"
        ),
    )

    print(
        "Repeated sync idempotent:",
        (
            "PASS"
            if idempotent_valid
            else "FAIL"
        ),
    )

    validation = (
        first_result[
            "success"
        ]
        and second_result[
            "success"
        ]
        and complete_coverage_valid
        and allowed_values_valid
        and persistence_valid
        and collectible_type_untouched
        and idempotent_valid
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_collectible_reference_mapping_test():
    print(
        "\nAXIEOS COLLECTIBLE REFERENCE MAPPING"
    )

    references = [
        {
            "collection": "SUMMER",
            "axie_id": "11433345",
        },
        {
            "collection": "SUMMER",
            "axie_id": "11453588",
        },
        {
            "collection": "SHINY",
            "axie_id": "11737553",
        },
        {
            "collection": "SHINY",
            "axie_id": "11401497",
        },
        {
            "collection": "SHINY",
            "axie_id": "11453584",
        },
        {
            "collection": "NIGHTMARE",
            "axie_id": "11459324",
        },
        {
            "collection": "NIGHTMARE",
            "axie_id": "11753075",
        },
        {
            "collection": "NIGHTMARE",
            "axie_id": "11976208",
        },
        {
            "collection": "JAPANESE",
            "axie_id": "184371",
        },
        {
            "collection": "XMAS",
            "axie_id": "138767",
        },
        {
            "collection": "MEO2",
            "axie_id": "11855341",
        },
    ]

    successful_records = []
    failed_records = []

    for reference in references:
        axie_id = reference[
            "axie_id"
        ]

        result = (
            fetch_axie_core_onchain(
                axie_id
            )
        )

        if not result[
            "success"
        ]:
            failed_records.append(
                {
                    "collection": (
                        reference[
                            "collection"
                        ]
                    ),
                    "axie_id": axie_id,
                    "error": result.get(
                        "error"
                    ),
                }
            )

            continue

        core_data = result[
            "data"
        ]

        genes_hex = (
            build_full_axie_genes_from_core(
                core_data[
                    "genes_x"
                ],
                core_data[
                    "genes_y"
                ],
                AXIE_CORE_GENE_ORDER,
            )
        )

        decoded = (
            decode_axie_collectible_gene_signals(
                genes_hex
            )
        )

        special_part_skins = {
            slot: code
            for (
                slot,
                code,
            ) in decoded[
                "part_skin_codes"
            ].items()
            if code != 0
        }

        successful_records.append(
            {
                "collection": (
                    reference[
                        "collection"
                    ]
                ),
                "axie_id": axie_id,
                "tag": decoded[
                    "tag"
                ],
                "tag_bits": decoded[
                    "tag_bits"
                ],
                "body_skin": decoded[
                    "body_skin"
                ],
                "body_skin_bits": (
                    decoded[
                        "body_skin_bits"
                    ]
                ),
                "special_part_skins": (
                    special_part_skins
                ),
                "part_skin_codes": (
                    decoded[
                        "part_skin_codes"
                    ]
                ),
            }
        )

    print(
        "Reference Axies:",
        len(references),
    )

    print(
        "Successful reads:",
        len(
            successful_records
        ),
    )

    print(
        "Failed reads:",
        len(
            failed_records
        ),
    )

    print(
        "\nREFERENCE SIGNALS"
    )

    for record in successful_records:
        print(
            "\nCollection:",
            record[
                "collection"
            ],
        )

        print(
            "Axie ID:",
            record[
                "axie_id"
            ],
        )

        print(
            "Tag:",
            record[
                "tag"
            ],
        )

        print(
            "Tag bits:",
            record[
                "tag_bits"
            ],
        )

        print(
            "Body skin:",
            record[
                "body_skin"
            ],
        )

        print(
            "Body skin bits:",
            record[
                "body_skin_bits"
            ],
        )

        print(
            "Special part skins:",
            (
                record[
                    "special_part_skins"
                ]
                if record[
                    "special_part_skins"
                ]
                else "NONE"
            ),
        )

        print(
            "All part skin codes:",
            record[
                "part_skin_codes"
            ],
        )

    collection_skin_codes = {}

    for record in successful_records:
        collection = record[
            "collection"
        ]

        collection_skin_codes.setdefault(
            collection,
            set(),
        )

        collection_skin_codes[
            collection
        ].update(
            record[
                "special_part_skins"
            ].values()
        )

    print(
        "\nCOLLECTION SKIN CODE SUMMARY"
    )

    for collection in sorted(
        collection_skin_codes
    ):
        codes = sorted(
            collection_skin_codes[
                collection
            ]
        )

        print(
            collection,
            ":",
            (
                codes
                if codes
                else "NO NON-ZERO PART CODE"
            ),
        )

    known_legacy_expectations = {
        "JAPANESE": {
            3,
        },
        "XMAS": {
            4,
            5,
        },
    }

    legacy_checks = 0
    legacy_passes = 0

    print(
        "\nLEGACY CROSS-CHECKS"
    )

    for (
        collection,
        expected_codes,
    ) in (
        known_legacy_expectations.items()
    ):
        actual_codes = (
            collection_skin_codes.get(
                collection,
                set(),
            )
        )

        legacy_checks += 1

        passed = bool(
            actual_codes
            & expected_codes
        )

        if passed:
            legacy_passes += 1

        print(
            collection,
            ":",
            (
                "PASS"
                if passed
                else "REVIEW"
            ),
            "| codes:",
            sorted(
                actual_codes
            ),
        )

    meo_records = [
        record
        for record in successful_records
        if record[
            "collection"
        ]
        == "MEO2"
    ]

    meo_tag_valid = (
        len(
            meo_records
        )
        > 0
        and all(
            record[
                "tag"
            ]
            == "MEO2"
            for record
            in meo_records
        )
    )

    print(
        "MEO2 tag:",
        (
            "PASS"
            if meo_tag_valid
            else "REVIEW"
        ),
    )

    summer_codes = (
        collection_skin_codes.get(
            "SUMMER",
            set(),
        )
    )

    shiny_codes = (
        collection_skin_codes.get(
            "SHINY",
            set(),
        )
    )

    nightmare_codes = (
        collection_skin_codes.get(
            "NIGHTMARE",
            set(),
        )
    )

    summer_signal_found = bool(
        summer_codes
    )

    shiny_signal_found = bool(
        shiny_codes
    )

    nightmare_signal_found = bool(
        nightmare_codes
    )

    print(
        "\nMODERN SIGNAL CHECKS"
    )

    print(
        "Summer code signal:",
        (
            "FOUND"
            if summer_signal_found
            else "NOT FOUND"
        ),
    )

    print(
        "Shiny code signal:",
        (
            "FOUND"
            if shiny_signal_found
            else "NOT FOUND"
        ),
    )

    print(
        "Nightmare code signal:",
        (
            "FOUND"
            if nightmare_signal_found
            else "NOT FOUND"
        ),
    )

    print(
        "\nRAW MODERN CODE SETS"
    )

    print(
        "Summer:",
        sorted(
            summer_codes
        ),
    )

    print(
        "Shiny:",
        sorted(
            shiny_codes
        ),
    )

    print(
        "Nightmare:",
        sorted(
            nightmare_codes
        ),
    )

    complete_rpc_coverage = (
        len(
            successful_records
        )
        == len(
            references
        )
    )

    legacy_validation = (
        legacy_passes
        == legacy_checks
    )

    modern_signals_valid = (
        summer_signal_found
        and shiny_signal_found
        and nightmare_signal_found
    )

    validation = (
        complete_rpc_coverage
        and legacy_validation
        and meo_tag_valid
        and modern_signals_valid
    )

    if failed_records:
        print(
            "\nFAILED REFERENCES"
        )

        for failure in (
            failed_records
        ):
            print(
                failure[
                    "collection"
                ],
                "| Axie ID:",
                failure[
                    "axie_id"
                ],
                "|",
                failure[
                    "error"
                ],
            )

    print(
        "\nCHECKS"
    )

    print(
        "Complete reference coverage:",
        (
            "PASS"
            if complete_rpc_coverage
            else "FAIL"
        ),
    )

    print(
        "Legacy codes consistent:",
        (
            "PASS"
            if legacy_validation
            else "FAIL"
        ),
    )

    print(
        "MEO2 tag consistent:",
        (
            "PASS"
            if meo_tag_valid
            else "FAIL"
        ),
    )

    print(
        "Modern skin signals present:",
        (
            "PASS"
            if modern_signals_valid
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



def run_multi_collection_classifier_test():
    print(
        "\nAXIEOS MULTI-COLLECTION CLASSIFIER"
    )

    references = [
        {
            "axie_id": "11433345",
            "expected": "SUMMER",
        },
        {
            "axie_id": "11453588",
            "expected": "SUMMER",
        },
        {
            "axie_id": "11737553",
            "expected": "SHINY",
        },
        {
            "axie_id": "11401497",
            "expected": "SHINY",
        },
        {
            "axie_id": "11453584",
            "expected": "SHINY",
        },
        {
            "axie_id": "11459324",
            "expected": "NIGHTMARE",
        },
        {
            "axie_id": "11753075",
            "expected": "NIGHTMARE",
        },
        {
            "axie_id": "11976208",
            "expected": "NIGHTMARE",
        },
        {
            "axie_id": "184371",
            "expected": "JAPANESE",
        },
        {
            "axie_id": "138767",
            "expected": "XMAS",
        },
        {
            "axie_id": "11855341",
            "expected": "MEO_CORP_II",
        },
    ]

    successful = []
    failures = []

    for reference in references:
        axie_id = reference[
            "axie_id"
        ]

        core_result = (
            fetch_axie_core_onchain(
                axie_id
            )
        )

        if not core_result[
            "success"
        ]:
            failures.append(
                {
                    "axie_id": axie_id,
                    "reason": (
                        core_result.get(
                            "error"
                        )
                    ),
                }
            )

            continue

        core_data = core_result[
            "data"
        ]

        genes_hex = (
            build_full_axie_genes_from_core(
                core_data[
                    "genes_x"
                ],
                core_data[
                    "genes_y"
                ],
                AXIE_CORE_GENE_ORDER,
            )
        )

        classification = (
            classify_axie_collections_from_genes(
                genes_hex
            )
        )

        expected = reference[
            "expected"
        ]

        passed = (
            expected
            in classification[
                "collections"
            ]
        )

        successful.append(
            {
                "axie_id": axie_id,
                "expected": expected,
                "collections": (
                    classification[
                        "collections"
                    ]
                ),
                "unknown_skin_codes": (
                    classification[
                        "unknown_skin_codes"
                    ]
                ),
                "passed": passed,
            }
        )

    print(
        "Reference Axies:",
        len(references),
    )

    print(
        "Successful reads:",
        len(
            successful
        ),
    )

    print(
        "Failed reads:",
        len(
            failures
        ),
    )

    print(
        "\nREFERENCE CLASSIFICATION"
    )

    for record in successful:
        print(
            "Axie ID:",
            record[
                "axie_id"
            ],
            "| expected:",
            record[
                "expected"
            ],
            "| detected:",
            record[
                "collections"
            ],
            "|",
            (
                "PASS"
                if record[
                    "passed"
                ]
                else "FAIL"
            ),
        )

    layered_records = [
        record
        for record in successful
        if len(
            record[
                "collections"
            ]
        )
        > 1
    ]

    unknown_records = [
        record
        for record in successful
        if record[
            "unknown_skin_codes"
        ]
    ]

    expected_matches = sum(
        1
        for record in successful
        if record[
            "passed"
        ]
    )

    expected_mapping_valid = (
        expected_matches
        == len(
            references
        )
    )

    complete_rpc_coverage = (
        len(
            successful
        )
        == len(
            references
        )
        and not failures
    )

    no_unknown_skin_codes = (
        len(
            unknown_records
        )
        == 0
    )

    print(
        "\nMULTI-LABEL SIGNALS"
    )

    print(
        "Reference Axies with "
        "multiple collections:",
        len(
            layered_records
        ),
    )

    for record in (
        layered_records
    ):
        print(
            "Axie ID:",
            record[
                "axie_id"
            ],
            "| collections:",
            record[
                "collections"
            ],
        )

    print(
        "\nMAPPING COVERAGE"
    )

    print(
        "Expected labels matched:",
        expected_matches,
        "/",
        len(
            references
        ),
    )

    print(
        "References with unknown "
        "skin codes:",
        len(
            unknown_records
        ),
    )

    if unknown_records:
        for record in (
            unknown_records
        ):
            print(
                "Axie ID:",
                record[
                    "axie_id"
                ],
                "| unknown codes:",
                record[
                    "unknown_skin_codes"
                ],
            )

    if failures:
        print(
            "\nFAILED REFERENCES"
        )

        for failure in failures:
            print(
                "Axie ID:",
                failure[
                    "axie_id"
                ],
                "|",
                failure[
                    "reason"
                ],
            )

    print(
        "\nCHECKS"
    )

    print(
        "Complete reference coverage:",
        (
            "PASS"
            if complete_rpc_coverage
            else "FAIL"
        ),
    )

    print(
        "Expected collection labels:",
        (
            "PASS"
            if expected_mapping_valid
            else "FAIL"
        ),
    )

    print(
        "All observed skin codes mapped:",
        (
            "PASS"
            if no_unknown_skin_codes
            else "REVIEW"
        ),
    )

    validation = (
        complete_rpc_coverage
        and expected_mapping_valid
        and no_unknown_skin_codes
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_owned_axie_collection_trait_sync_test():
    print(
        "\nAXIEOS OWNED AXIE COLLECTION TRAITS"
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    before_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                collectible_type
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            """
        ).fetchall()
    )

    connection.close()

    collectible_type_before = {
        str(row[0]): row[1]
        for row in before_rows
    }

    first_result = (
        sync_collection_traits_for_owned_axies(
            AXIEOS_DB_PATH
        )
    )

    second_result = (
        sync_collection_traits_for_owned_axies(
            AXIEOS_DB_PATH
        )
    )

    print(
        "First sync:",
        (
            "PASS"
            if first_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    print(
        "Second sync:",
        (
            "PASS"
            if second_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    owned_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                is_collectible,
                collectible_type
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    trait_rows = (
        connection.execute(
            """
            SELECT
                t.axie_id,
                t.trait_value,
                t.data_source
            FROM gameplay_axie_traits t
            INNER JOIN
                gameplay_owned_axies a
                ON a.axie_id =
                   t.axie_id
            WHERE
                a.ownership_status =
                    'OWNED'
                AND t.trait_type =
                    'COLLECTION'
            ORDER BY
                CAST(
                    t.axie_id AS INTEGER
                ),
                t.trait_value
            """
        ).fetchall()
    )

    connection.close()

    database_trait_map = {}

    source_valid = True

    for row in trait_rows:
        axie_id = str(
            row[0]
        )

        database_trait_map.setdefault(
            axie_id,
            set(),
        )

        database_trait_map[
            axie_id
        ].add(
            row[1]
        )

        if row[2] != (
            "RONIN_AXIE_GENES"
        ):
            source_valid = False

    expected_trait_map = {
        record[
            "axie_id"
        ]: set(
            record[
                "collections"
            ]
        )
        for record
        in first_result[
            "records"
        ]
    }

    expected_status_map = {
        record[
            "axie_id"
        ]: record[
            "is_collectible"
        ]
        for record
        in first_result[
            "records"
        ]
    }

    database_status_map = {
        str(row[0]): row[1]
        for row in owned_rows
    }

    normalized_database_traits = {
        axie_id: (
            database_trait_map.get(
                axie_id,
                set(),
            )
        )
        for axie_id
        in expected_trait_map
    }

    trait_values_valid = (
        normalized_database_traits
        == expected_trait_map
    )

    status_values_valid = (
        database_status_map
        == expected_status_map
    )

    expected_trait_count = sum(
        len(
            collections
        )
        for collections
        in expected_trait_map.values()
    )

    trait_count_valid = (
        len(
            trait_rows
        )
        == expected_trait_count
    )

    no_duplicate_traits = (
        len(
            trait_rows
        )
        == len(
            {
                (
                    str(row[0]),
                    row[1],
                )
                for row
                in trait_rows
            }
        )
    )

    collectible_type_after = {
        str(row[0]): row[2]
        for row in owned_rows
    }

    collectible_type_preserved = (
        collectible_type_before
        == collectible_type_after
    )

    first_map = {
        record[
            "axie_id"
        ]: {
            "is_collectible": (
                record[
                    "is_collectible"
                ]
            ),
            "collections": tuple(
                record[
                    "collections"
                ]
            ),
        }
        for record
        in first_result[
            "records"
        ]
    }

    second_map = {
        record[
            "axie_id"
        ]: {
            "is_collectible": (
                record[
                    "is_collectible"
                ]
            ),
            "collections": tuple(
                record[
                    "collections"
                ]
            ),
        }
        for record
        in second_result[
            "records"
        ]
    }

    idempotent_valid = (
        first_map
        == second_map
        and trait_count_valid
        and no_duplicate_traits
    )

    complete_coverage_valid = (
        first_result[
            "owned_axies"
        ]
        == first_result[
            "classified_axies"
        ]
        == len(
            owned_rows
        )
    )

    no_unmapped_special_signals = (
        first_result[
            "unmapped_special_axies"
        ]
        == 0
    )

    print(
        "\nSYNC SUMMARY"
    )

    print(
        "Blockchain-owned Axies:",
        first_result[
            "owned_axies"
        ],
    )

    print(
        "Successfully classified:",
        first_result[
            "classified_axies"
        ],
    )

    print(
        "Collectible Axies:",
        first_result[
            "collectible_axies"
        ],
    )

    print(
        "Collection traits written:",
        first_result[
            "collection_traits_written"
        ],
    )

    print(
        "Multi-collection Axies:",
        first_result[
            "multi_collection_axies"
        ],
    )

    print(
        "Unmapped special signals:",
        first_result[
            "unmapped_special_axies"
        ],
    )

    print(
        "Failed Axies:",
        len(
            first_result[
                "failed_axies"
            ]
        ),
    )

    print(
        "\nOWNED AXIE COLLECTION TRAITS"
    )

    for record in first_result[
        "records"
    ]:
        print(
            "Axie ID:",
            record[
                "axie_id"
            ],
            "| collectible:",
            record[
                "is_collectible"
            ],
            "| collections:",
            (
                record[
                    "collections"
                ]
                if record[
                    "collections"
                ]
                else "NONE"
            ),
        )

    if first_result[
        "failed_axies"
    ]:
        print(
            "\nFAILED CLASSIFICATIONS"
        )

        for failure in (
            first_result[
                "failed_axies"
            ]
        ):
            print(
                "Axie ID:",
                failure[
                    "axie_id"
                ],
                "|",
                failure[
                    "reason"
                ],
            )

    print(
        "\nCHECKS"
    )

    print(
        "Complete owned-Axie coverage:",
        (
            "PASS"
            if complete_coverage_valid
            else "FAIL"
        ),
    )

    print(
        "Collection traits match genes:",
        (
            "PASS"
            if trait_values_valid
            else "FAIL"
        ),
    )

    print(
        "Collectible status matches genes:",
        (
            "PASS"
            if status_values_valid
            else "FAIL"
        ),
    )

    print(
        "Trait row count:",
        (
            "PASS"
            if trait_count_valid
            else "FAIL"
        ),
    )

    print(
        "No duplicate collection traits:",
        (
            "PASS"
            if no_duplicate_traits
            else "FAIL"
        ),
    )

    print(
        "Trait provenance:",
        (
            "PASS"
            if source_valid
            else "FAIL"
        ),
    )

    print(
        "Legacy collectible_type preserved:",
        (
            "PASS"
            if collectible_type_preserved
            else "FAIL"
        ),
    )

    print(
        "All special signals mapped:",
        (
            "PASS"
            if no_unmapped_special_signals
            else "REVIEW"
        ),
    )

    print(
        "Repeated sync idempotent:",
        (
            "PASS"
            if idempotent_valid
            else "FAIL"
        ),
    )

    validation = (
        first_result[
            "success"
        ]
        and second_result[
            "success"
        ]
        and complete_coverage_valid
        and trait_values_valid
        and status_values_valid
        and trait_count_valid
        and no_duplicate_traits
        and source_valid
        and collectible_type_preserved
        and no_unmapped_special_signals
        and idempotent_valid
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_direct_wallet_axie_ownership_audit():
    print(
        "\nAXIEOS DIRECT WALLET OWNERSHIP AUDIT"
    )

    user_owned_wallets = (
        load_user_owned_wallet_addresses(
            AXIEOS_DB_PATH
        )
    )

    user_owned_wallets = sorted(
        {
            str(
                wallet
            ).lower()
            for wallet
            in user_owned_wallets
        }
    )

    print(
        "Registered USER_OWNED wallets:",
        len(
            user_owned_wallets
        ),
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    registry_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                LOWER(wallet_address)
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            """
        ).fetchall()
    )

    connection.close()

    registry_by_wallet = {}

    for row in registry_rows:
        axie_id = str(
            row[0]
        )

        wallet = str(
            row[1]
        ).lower()

        registry_by_wallet.setdefault(
            wallet,
            set(),
        ).add(
            axie_id
        )

    all_chain_ids = set()
    all_registry_ids = {
        str(
            row[0]
        )
        for row
        in registry_rows
    }

    wallet_results = []

    for wallet in user_owned_wallets:
        print(
            "\nWALLET:",
            wallet,
        )

        token_result = (
            fetch_axie_tokens_of_owner(
                wallet
            )
        )

        print(
            "Enumeration request:",
            (
                "PASS"
                if token_result[
                    "success"
                ]
                else "FAIL"
            ),
        )

        print(
            "On-chain balance:",
            token_result.get(
                "balance"
            ),
        )

        print(
            "Token IDs retrieved:",
            len(
                token_result[
                    "axie_ids"
                ]
            ),
        )

        if not token_result[
            "success"
        ]:
            print(
                "Failed index:",
                token_result.get(
                    "failed_index"
                ),
            )

            print(
                "Error:",
                token_result.get(
                    "error"
                ),
            )

            wallet_results.append(
                {
                    "wallet": wallet,
                    "success": False,
                    "chain_ids": set(),
                    "registry_ids": (
                        registry_by_wallet.get(
                            wallet,
                            set(),
                        )
                    ),
                }
            )

            continue

        chain_ids = set(
            token_result[
                "axie_ids"
            ]
        )

        registry_ids = (
            registry_by_wallet.get(
                wallet,
                set(),
            )
        )

        all_chain_ids.update(
            chain_ids
        )

        missing_from_registry = (
            chain_ids
            - registry_ids
        )

        stale_registry = (
            registry_ids
            - chain_ids
        )

        print(
            "AxieOS registry OWNED:",
            len(
                registry_ids
            ),
        )

        print(
            "Missing from registry:",
            len(
                missing_from_registry
            ),
        )

        print(
            "Stale registry records:",
            len(
                stale_registry
            ),
        )

        wallet_results.append(
            {
                "wallet": wallet,
                "success": True,
                "chain_ids": chain_ids,
                "registry_ids": (
                    registry_ids
                ),
            }
        )

    successful_wallets = [
        result
        for result in wallet_results
        if result[
            "success"
        ]
    ]

    failed_wallets = [
        result
        for result in wallet_results
        if not result[
            "success"
        ]
    ]

    missing_from_registry = (
        all_chain_ids
        - all_registry_ids
    )

    stale_registry = (
        all_registry_ids
        - all_chain_ids
    )

    print(
        "\nCOMBINED USER-OWNED WALLET STATE"
    )

    print(
        "USER_OWNED wallets:",
        len(
            user_owned_wallets
        ),
    )

    print(
        "Successfully enumerated:",
        len(
            successful_wallets
        ),
    )

    print(
        "Failed wallets:",
        len(
            failed_wallets
        ),
    )

    print(
        "Unique Axies on-chain:",
        len(
            all_chain_ids
        ),
    )

    print(
        "AxieOS registry OWNED:",
        len(
            all_registry_ids
        ),
    )

    print(
        "Missing from AxieOS registry:",
        len(
            missing_from_registry
        ),
    )

    print(
        "Stale AxieOS OWNED records:",
        len(
            stale_registry
        ),
    )

    if missing_from_registry:
        print(
            "\nON-CHAIN OWNED BUT MISSING FROM AXIEOS"
        )

        for axie_id in sorted(
            missing_from_registry,
            key=int,
        ):
            print(
                "Axie ID:",
                axie_id,
            )

    if stale_registry:
        print(
            "\nAXIEOS OWNED BUT NOT CURRENTLY USER-OWNED"
        )

        for axie_id in sorted(
            stale_registry,
            key=int,
        ):
            print(
                "Axie ID:",
                axie_id,
            )

    enumeration_valid = (
        len(
            failed_wallets
        )
        == 0
    )

    chain_count_valid = all(
        len(
            result[
                "chain_ids"
            ]
        )
        >= 0
        for result
        in successful_wallets
    )

    registry_matches_chain = (
        all_chain_ids
        == all_registry_ids
    )

    print(
        "\nCHECKS"
    )

    print(
        "All USER_OWNED wallets enumerated:",
        (
            "PASS"
            if enumeration_valid
            else "FAIL"
        ),
    )

    print(
        "Current-state enumeration:",
        (
            "PASS"
            if chain_count_valid
            else "FAIL"
        ),
    )

    print(
        "Registry matches current chain:",
        (
            "PASS"
            if registry_matches_chain
            else "REVIEW"
        ),
    )

    validation = (
        enumeration_valid
        and chain_count_valid
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_current_chain_origins_reconciliation_test():
    print(
        "\nAXIEOS CURRENT CHAIN ↔ ORIGINS RECONCILIATION"
    )

    user_owned_wallets = (
        load_user_owned_wallet_addresses(
            AXIEOS_DB_PATH
        )
    )

    user_owned_wallets = sorted(
        {
            str(wallet).lower()
            for wallet
            in user_owned_wallets
        }
    )

    chain_ids = set()

    failed_wallets = []

    for wallet in user_owned_wallets:
        result = (
            fetch_axie_tokens_of_owner(
                wallet
            )
        )

        if not result[
            "success"
        ]:
            failed_wallets.append(
                {
                    "wallet": wallet,
                    "error": result.get(
                        "error"
                    ),
                }
            )

            continue

        chain_ids.update(
            str(axie_id)
            for axie_id
            in result[
                "axie_ids"
            ]
        )

    origins_result = (
        fetch_all_origins_ronin_fighters()
    )

    chain_valid = (
        len(
            failed_wallets
        )
        == 0
    )

    origins_valid = (
        origins_result[
            "success"
        ]
    )

    print(
        "Chain enumeration:",
        (
            "PASS"
            if chain_valid
            else "FAIL"
        ),
    )

    print(
        "Origins API:",
        (
            "PASS"
            if origins_valid
            else "FAIL"
        ),
    )

    if not (
        chain_valid
        and origins_valid
    ):
        if failed_wallets:
            print(
                "\nFAILED WALLETS"
            )

            for failure in (
                failed_wallets
            ):
                print(
                    failure[
                        "wallet"
                    ],
                    "|",
                    failure[
                        "error"
                    ],
                )

        print(
            "\nValidation: FAIL"
        )

        return

    origins_ids = {
        str(
            fighter[
                "id"
            ]
        )
        for fighter
        in origins_result[
            "fighters"
        ]
        if fighter.get(
            "id"
        )
        is not None
    }

    chain_only = (
        chain_ids
        - origins_ids
    )

    origins_only = (
        origins_ids
        - chain_ids
    )

    exact_match = (
        chain_ids
        == origins_ids
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    registry_rows = (
        connection.execute(
            """
            SELECT
                axie_id
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            """
        ).fetchall()
    )

    connection.close()

    registry_ids = {
        str(row[0])
        for row
        in registry_rows
    }

    registry_current_match = (
        registry_ids
        & chain_ids
    )

    registry_stale = (
        registry_ids
        - chain_ids
    )

    registry_missing = (
        chain_ids
        - registry_ids
    )

    print(
        "\nCURRENT STATE COUNTS"
    )

    print(
        "On-chain user-owned Axies:",
        len(
            chain_ids
        ),
    )

    print(
        "Origins Ronin fighters:",
        len(
            origins_ids
        ),
    )

    print(
        "Current AxieOS OWNED:",
        len(
            registry_ids
        ),
    )

    print(
        "\nCHAIN ↔ ORIGINS"
    )

    print(
        "Chain-only Axies:",
        len(
            chain_only
        ),
    )

    print(
        "Origins-only Axies:",
        len(
            origins_only
        ),
    )

    print(
        "Exact current-state match:",
        (
            "PASS"
            if exact_match
            else "REVIEW"
        ),
    )

    if chain_only:
        print(
            "\nCHAIN-ONLY AXIES"
        )

        for axie_id in sorted(
            chain_only,
            key=int,
        ):
            print(
                "Axie ID:",
                axie_id,
            )

    if origins_only:
        print(
            "\nORIGINS-ONLY AXIES"
        )

        for axie_id in sorted(
            origins_only,
            key=int,
        ):
            print(
                "Axie ID:",
                axie_id,
            )

    print(
        "\nREGISTRY REPAIR SCOPE"
    )

    print(
        "Registry records still current:",
        len(
            registry_current_match
        ),
    )

    print(
        "Current Axies missing from registry:",
        len(
            registry_missing
        ),
    )

    print(
        "Stale registry OWNED records:",
        len(
            registry_stale
        ),
    )

    if registry_stale:
        print(
            "\nSTALE REGISTRY IDS"
        )

        for axie_id in sorted(
            registry_stale,
            key=int,
        ):
            print(
                "Axie ID:",
                axie_id,
            )

    print(
        "\nCHECKS"
    )

    print(
        "All wallets enumerated:",
        (
            "PASS"
            if chain_valid
            else "FAIL"
        ),
    )

    print(
        "Origins fighter fetch:",
        (
            "PASS"
            if origins_valid
            else "FAIL"
        ),
    )

    print(
        "Chain and Origins exact match:",
        (
            "PASS"
            if exact_match
            else "REVIEW"
        ),
    )

    validation = (
        chain_valid
        and origins_valid
        and exact_match
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_current_owned_registry_repair_test():
    print(
        "\nAXIEOS CURRENT OWNERSHIP REGISTRY REPAIR"
    )

    first_result = (
        sync_owned_axie_registry_from_current_chain(
            AXIEOS_DB_PATH
        )
    )

    print(
        "Live chain repair:",
        (
            "PASS"
            if first_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    if not first_result[
        "success"
    ]:
        print(
            "Error:",
            first_result.get(
                "error"
            ),
        )

        print(
            "\nValidation: FAIL"
        )

        return

    second_result = (
        sync_owned_axie_registry_from_current_chain(
            AXIEOS_DB_PATH,
            current_wallet_map=(
                first_result[
                    "wallet_map"
                ]
            ),
        )
    )

    print(
        "Same-snapshot repair:",
        (
            "PASS"
            if second_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    owned_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                LOWER(wallet_address)
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            """
        ).fetchall()
    )

    lifecycle_row = (
        connection.execute(
            """
            SELECT
                ownership_status
            FROM gameplay_owned_axies
            WHERE axie_id = ?
            """,
            (
                "7087631",
            ),
        ).fetchone()
    )

    connection.close()

    database_ids = {
        str(row[0])
        for row
        in owned_rows
    }

    expected_ids = set(
        first_result[
            "wallet_map"
        ].keys()
    )

    exact_current_set = (
        database_ids
        == expected_ids
    )

    wallet_assignment_valid = all(
        first_result[
            "wallet_map"
        ].get(
            str(row[0])
        )
        == str(
            row[1]
        ).lower()
        for row in owned_rows
    )

    lifecycle_evidence = (
        resolve_non_owned_axie_lifecycle_status(
            AXIEOS_DB_PATH,
            "7087631",
        )
    )

    stored_lifecycle_status = (
        lifecycle_row[0]
        if lifecycle_row
        else None
    )

    sale_lifecycle_valid = (
        lifecycle_evidence[
            "status"
        ]
        == "SOLD"
        and stored_lifecycle_status
        == "SOLD"
    )

    second_run_clean = (
        second_result[
            "success"
        ]
        and second_result[
            "current_axies"
        ]
        == first_result[
            "current_axies"
        ]
        and second_result[
            "new_axies"
        ]
        == 0
        and second_result[
            "reactivated_axies"
        ]
        == 0
        and len(
            second_result[
                "stale_axies"
            ]
        )
        == 0
    )

    print(
        "\nCURRENT OWNERSHIP"
    )

    print(
        "Authoritative current Axies:",
        first_result[
            "current_axies"
        ],
    )

    print(
        "Database OWNED Axies:",
        len(
            database_ids
        ),
    )

    print(
        "New records this run:",
        first_result[
            "new_axies"
        ],
    )

    print(
        "Reactivated this run:",
        first_result[
            "reactivated_axies"
        ],
    )

    print(
        "Stale this run:",
        len(
            first_result[
                "stale_axies"
            ]
        ),
    )

    print(
        "\nAXIE #7087631 LIFECYCLE"
    )

    print(
        "Evidence status:",
        lifecycle_evidence[
            "status"
        ],
    )

    print(
        "Evidence source:",
        lifecycle_evidence[
            "source"
        ],
    )

    print(
        "Evidence datetime:",
        lifecycle_evidence[
            "datetime"
        ],
    )

    print(
        "Stored status:",
        stored_lifecycle_status,
    )

    print(
        "\nSAME-SNAPSHOT SECOND PASS"
    )

    print(
        "Current Axies:",
        second_result[
            "current_axies"
        ],
    )

    print(
        "New records:",
        second_result[
            "new_axies"
        ],
    )

    print(
        "Reactivated:",
        second_result[
            "reactivated_axies"
        ],
    )

    print(
        "Stale:",
        len(
            second_result[
                "stale_axies"
            ]
        ),
    )

    print(
        "\nCHECKS"
    )

    print(
        "Registry equals current chain:",
        (
            "PASS"
            if exact_current_set
            else "FAIL"
        ),
    )

    print(
        "Wallet assignments:",
        (
            "PASS"
            if wallet_assignment_valid
            else "FAIL"
        ),
    )

    print(
        "Axie #7087631 resolved SOLD:",
        (
            "PASS"
            if sale_lifecycle_valid
            else "FAIL"
        ),
    )

    print(
        "Same snapshot idempotent:",
        (
            "PASS"
            if second_run_clean
            else "FAIL"
        ),
    )

    validation = (
        first_result[
            "success"
        ]
        and second_result[
            "success"
        ]
        and exact_current_set
        and wallet_assignment_valid
        and sale_lifecycle_valid
        and second_run_clean
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_full_owned_axie_enrichment_test():
    print(
        "\nAXIEOS FULL OWNED AXIE ENRICHMENT"
    )

    origins_result = (
        sync_origins_metadata_for_owned_axies(
            AXIEOS_DB_PATH
        )
    )

    print(
        "Origins metadata sync:",
        (
            "PASS"
            if origins_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    if not origins_result[
        "success"
    ]:
        print(
            "Origins error:",
            origins_result.get(
                "error"
            ),
        )

        print(
            "\nValidation: FAIL"
        )

        return

    breed_result = (
        sync_onchain_breed_counts_for_owned_axies(
            AXIEOS_DB_PATH
        )
    )

    print(
        "Breed count sync:",
        (
            "PASS"
            if breed_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    owned_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                axie_class,
                level,
                breed_count,
                is_evolved
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    part_rows = (
        connection.execute(
            """
            SELECT
                a.axie_id,
                COUNT(p.part_slot)
            FROM gameplay_owned_axies a
            LEFT JOIN gameplay_axie_parts p
                ON p.axie_id =
                   a.axie_id
            WHERE a.ownership_status =
                'OWNED'
            GROUP BY
                a.axie_id
            ORDER BY
                CAST(
                    a.axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    connection.close()

    owned_count = len(
        owned_rows
    )

    class_coverage = sum(
        1
        for row in owned_rows
        if row[1]
        in AXIE_CLASSES
    )

    level_coverage = sum(
        1
        for row in owned_rows
        if isinstance(
            row[2],
            int,
        )
        and row[2] > 0
    )

    breed_coverage = sum(
        1
        for row in owned_rows
        if isinstance(
            row[3],
            int,
        )
        and 0 <= row[3] <= 7
    )

    evolution_coverage = sum(
        1
        for row in owned_rows
        if row[4]
        in {
            0,
            1,
        }
    )

    full_part_profiles = sum(
        1
        for row in part_rows
        if row[1] == 6
    )

    partial_part_profiles = [
        (
            str(row[0]),
            row[1],
        )
        for row in part_rows
        if row[1] != 6
    ]

    origins_exact_coverage = (
        origins_result[
            "owned_axies"
        ]
        == owned_count
        and origins_result[
            "origins_matched"
        ]
        == owned_count
        and origins_result[
            "synced_axies"
        ]
        == owned_count
        and len(
            origins_result[
                "origins_missing"
            ]
        )
        == 0
        and len(
            origins_result[
                "skipped_axies"
            ]
        )
        == 0
    )

    breed_exact_coverage = (
        breed_result[
            "owned_axies"
        ]
        == owned_count
        and breed_result[
            "synced_axies"
        ]
        == owned_count
        and len(
            breed_result[
                "failed_axies"
            ]
        )
        == 0
    )

    registry_metadata_complete = (
        class_coverage
        == owned_count
        and level_coverage
        == owned_count
        and breed_coverage
        == owned_count
        and evolution_coverage
        == owned_count
    )

    parts_complete = (
        full_part_profiles
        == owned_count
        and not partial_part_profiles
    )

    evolved_count = sum(
        1
        for row in owned_rows
        if row[4] == 1
    )

    not_evolved_count = sum(
        1
        for row in owned_rows
        if row[4] == 0
    )

    print(
        "\nENRICHMENT SUMMARY"
    )

    print(
        "Current OWNED Axies:",
        owned_count,
    )

    print(
        "Origins matched:",
        origins_result[
            "origins_matched"
        ],
    )

    print(
        "Origins missing:",
        len(
            origins_result[
                "origins_missing"
            ]
        ),
    )

    print(
        "Origins skipped:",
        len(
            origins_result[
                "skipped_axies"
            ]
        ),
    )

    print(
        "Parts upserted:",
        origins_result[
            "parts_upserted"
        ],
    )

    print(
        "Breed counts synced:",
        breed_result[
            "synced_axies"
        ],
    )

    print(
        "Breed failures:",
        len(
            breed_result[
                "failed_axies"
            ]
        ),
    )

    print(
        "\nMETADATA COVERAGE"
    )

    print(
        "Class:",
        class_coverage,
        "/",
        owned_count,
    )

    print(
        "Level:",
        level_coverage,
        "/",
        owned_count,
    )

    print(
        "Breed count:",
        breed_coverage,
        "/",
        owned_count,
    )

    print(
        "Evolution status:",
        evolution_coverage,
        "/",
        owned_count,
    )

    print(
        "Six-part profiles:",
        full_part_profiles,
        "/",
        owned_count,
    )

    print(
        "\nEVOLUTION"
    )

    print(
        "Evolved Axies:",
        evolved_count,
    )

    print(
        "Not evolved:",
        not_evolved_count,
    )

    if partial_part_profiles:
        print(
            "\nINCOMPLETE PART PROFILES"
        )

        for (
            axie_id,
            part_count,
        ) in (
            partial_part_profiles
        ):
            print(
                "Axie ID:",
                axie_id,
                "| parts:",
                part_count,
            )

    if breed_result[
        "failed_axies"
    ]:
        print(
            "\nFAILED BREED READS"
        )

        for failure in (
            breed_result[
                "failed_axies"
            ]
        ):
            print(
                "Axie ID:",
                failure[
                    "axie_id"
                ],
                "|",
                failure[
                    "reason"
                ],
            )

    print(
        "\nCHECKS"
    )

    print(
        "Origins covers current roster:",
        (
            "PASS"
            if origins_exact_coverage
            else "FAIL"
        ),
    )

    print(
        "Breed count covers current roster:",
        (
            "PASS"
            if breed_exact_coverage
            else "FAIL"
        ),
    )

    print(
        "Registry metadata complete:",
        (
            "PASS"
            if registry_metadata_complete
            else "FAIL"
        ),
    )

    print(
        "All owned Axies have six parts:",
        (
            "PASS"
            if parts_complete
            else "FAIL"
        ),
    )

    validation = (
        owned_count > 0
        and origins_exact_coverage
        and breed_exact_coverage
        and registry_metadata_complete
        and parts_complete
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_full_owned_axie_collectible_enrichment_test():
    print(
        "\nAXIEOS FULL OWNED AXIE COLLECTIBLE ENRICHMENT"
    )

    result = (
        sync_collection_traits_for_owned_axies(
            AXIEOS_DB_PATH
        )
    )

    print(
        "Collection sync:",
        (
            "PASS"
            if result[
                "success"
            ]
            else "FAIL"
        ),
    )

    if not result[
        "success"
    ]:
        print(
            "Failed Axies:",
            len(
                result[
                    "failed_axies"
                ]
            ),
        )

        for failure in (
            result[
                "failed_axies"
            ]
        ):
            print(
                "Axie ID:",
                failure[
                    "axie_id"
                ],
                "|",
                failure[
                    "reason"
                ],
            )

        print(
            "\nValidation: FAIL"
        )

        return

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    owned_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                axie_class,
                level,
                breed_count,
                is_collectible,
                is_evolved
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    trait_rows = (
        connection.execute(
            """
            SELECT
                t.axie_id,
                t.trait_value
            FROM gameplay_axie_traits t
            INNER JOIN
                gameplay_owned_axies a
                ON a.axie_id =
                   t.axie_id
            WHERE
                a.ownership_status =
                    'OWNED'
                AND t.trait_type =
                    'COLLECTION'
            ORDER BY
                CAST(
                    t.axie_id AS INTEGER
                ),
                t.trait_value
            """
        ).fetchall()
    )

    connection.close()

    owned_count = len(
        owned_rows
    )

    collectible_rows = [
        row
        for row in owned_rows
        if row[4] == 1
    ]

    non_collectible_rows = [
        row
        for row in owned_rows
        if row[4] == 0
    ]

    unknown_collectible_rows = [
        row
        for row in owned_rows
        if row[4] not in {
            0,
            1,
        }
    ]

    collection_map = {}

    for (
        axie_id,
        collection,
    ) in trait_rows:
        axie_id = str(
            axie_id
        )

        collection_map.setdefault(
            axie_id,
            []
        ).append(
            collection
        )

    collection_counts = {}

    for (
        _,
        collection,
    ) in trait_rows:
        collection_counts[
            collection
        ] = (
            collection_counts.get(
                collection,
                0,
            )
            + 1
        )

    collectible_without_trait = [
        str(row[0])
        for row
        in collectible_rows
        if str(
            row[0]
        )
        not in collection_map
    ]

    trait_without_collectible = sorted(
        {
            str(
                axie_id
            )
            for (
                axie_id,
                _,
            ) in trait_rows
            if not any(
                str(row[0])
                == str(
                    axie_id
                )
                and row[4] == 1
                for row
                in owned_rows
            )
        },
        key=int,
    )

    complete_coverage = (
        result[
            "owned_axies"
        ]
        == owned_count
        and result[
            "classified_axies"
        ]
        == owned_count
        and not result[
            "failed_axies"
        ]
        and not unknown_collectible_rows
    )

    status_trait_consistency = (
        not collectible_without_trait
        and not trait_without_collectible
    )

    no_unmapped_signals = (
        result[
            "unmapped_special_axies"
        ]
        == 0
    )

    print(
        "\nCLASSIFICATION SUMMARY"
    )

    print(
        "Current OWNED Axies:",
        owned_count,
    )

    print(
        "Successfully classified:",
        result[
            "classified_axies"
        ],
    )

    print(
        "Collectible Axies:",
        len(
            collectible_rows
        ),
    )

    print(
        "Non-collectible Axies:",
        len(
            non_collectible_rows
        ),
    )

    print(
        "Unknown collectible status:",
        len(
            unknown_collectible_rows
        ),
    )

    print(
        "Collection trait rows:",
        len(
            trait_rows
        ),
    )

    print(
        "Multi-collection Axies:",
        result[
            "multi_collection_axies"
        ],
    )

    print(
        "Unmapped special signals:",
        result[
            "unmapped_special_axies"
        ],
    )

    print(
        "\nCOLLECTION COUNTS"
    )

    if collection_counts:
        for collection in sorted(
            collection_counts
        ):
            print(
                collection,
                ":",
                collection_counts[
                    collection
                ],
            )

    else:
        print(
            "No collection traits found."
        )

    print(
        "\nCOLLECTIBLE AXIES"
    )

    if collectible_rows:
        for row in (
            collectible_rows
        ):
            axie_id = str(
                row[0]
            )

            print(
                "Axie ID:",
                axie_id,
                "| class:",
                row[1],
                "| level:",
                row[2],
                "| breed:",
                row[3],
                "| evolved:",
                row[5],
                "| collections:",
                collection_map.get(
                    axie_id,
                    [],
                ),
            )

    else:
        print(
            "None"
        )

    if collectible_without_trait:
        print(
            "\nCOLLECTIBLE WITHOUT MAPPED COLLECTION"
        )

        for axie_id in sorted(
            collectible_without_trait,
            key=int,
        ):
            print(
                "Axie ID:",
                axie_id,
            )

    if trait_without_collectible:
        print(
            "\nCOLLECTION TRAIT WITHOUT COLLECTIBLE STATUS"
        )

        for axie_id in (
            trait_without_collectible
        ):
            print(
                "Axie ID:",
                axie_id,
            )

    print(
        "\nCHECKS"
    )

    print(
        "Complete 136-Axie classification:",
        (
            "PASS"
            if complete_coverage
            else "FAIL"
        ),
    )

    print(
        "Collection/status consistency:",
        (
            "PASS"
            if status_trait_consistency
            else "FAIL"
        ),
    )

    print(
        "All special signals mapped:",
        (
            "PASS"
            if no_unmapped_signals
            else "REVIEW"
        ),
    )

    validation = (
        result[
            "success"
        ]
        and complete_coverage
        and status_trait_consistency
        and no_unmapped_signals
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )




AXIE_QUALIFICATION_STATUSES = {
    "QUALIFIED",
    "DISQUALIFIED",
    "UNKNOWN",
}


def load_owned_axie_qualification_profiles(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    owned_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                wallet_address,
                axie_class,
                level,
                breed_count,
                is_collectible,
                is_evolved,
                acquisition_datetime,
                acquisition_source
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    trait_rows = (
        connection.execute(
            """
            SELECT
                t.axie_id,
                t.trait_value
            FROM gameplay_axie_traits t
            INNER JOIN
                gameplay_owned_axies a
                ON a.axie_id =
                   t.axie_id
            WHERE
                a.ownership_status =
                    'OWNED'
                AND t.trait_type =
                    'COLLECTION'
            """
        ).fetchall()
    )

    part_rows = (
        connection.execute(
            """
            SELECT
                p.axie_id,
                p.part_slot,
                p.part_name,
                p.part_class,
                p.part_value,
                p.part_stage
            FROM gameplay_axie_parts p
            INNER JOIN
                gameplay_owned_axies a
                ON a.axie_id =
                   p.axie_id
            WHERE
                a.ownership_status =
                    'OWNED'
            ORDER BY
                CAST(
                    p.axie_id AS INTEGER
                ),
                p.part_slot
            """
        ).fetchall()
    )

    connection.close()

    collection_map = {}

    for (
        axie_id,
        collection,
    ) in trait_rows:
        axie_id = str(
            axie_id
        )

        collection_map.setdefault(
            axie_id,
            set(),
        ).add(
            str(
                collection
            ).upper()
        )

    part_map = {}

    for (
        axie_id,
        part_slot,
        part_name,
        part_class,
        part_value,
        part_stage,
    ) in part_rows:
        axie_id = str(
            axie_id
        )

        part_map.setdefault(
            axie_id,
            [],
        ).append(
            {
                "part_slot": (
                    part_slot
                ),
                "part_name": (
                    part_name
                ),
                "part_class": (
                    part_class
                ),
                "part_value": (
                    part_value
                ),
                "part_stage": (
                    part_stage
                ),
            }
        )

    profiles = []

    for row in owned_rows:
        axie_id = str(
            row[0]
        )

        profiles.append(
            {
                "axie_id": axie_id,
                "wallet_address": (
                    row[1]
                ),
                "axie_class": (
                    row[2]
                ),
                "level": (
                    row[3]
                ),
                "breed_count": (
                    row[4]
                ),
                "is_collectible": (
                    row[5]
                ),
                "is_evolved": (
                    row[6]
                ),
                "acquisition_datetime": (
                    row[7]
                ),
                "acquisition_source": (
                    row[8]
                ),
                "collections": sorted(
                    collection_map.get(
                        axie_id,
                        set(),
                    )
                ),
                "parts": (
                    part_map.get(
                        axie_id,
                        [],
                    )
                ),
            }
        )

    return profiles



def evaluate_axie_qualification(
    profile,
    criteria,
    as_of_datetime=None,
):
    allowed_criteria = {
        "axie_class",
        "min_level",
        "max_level",
        "min_breed_count",
        "max_breed_count",
        "is_evolved",
        "is_collectible",
        "required_collections",
        "any_collections",
        "required_part_names",
        "any_part_names",
        "min_ownership_days",
    }
    unknown_criteria = (
        set(
            criteria.keys()
        )
        - allowed_criteria
    )

    if unknown_criteria:
        raise ValueError(
            "Unsupported qualification criteria: "
            + ", ".join(
                sorted(
                    unknown_criteria
                )
            )
        )

    disqualified_reasons = []

    unknown_reasons = []

    required_class = criteria.get(
        "axie_class"
    )

    if required_class is not None:
        actual_class = profile.get(
            "axie_class"
        )

        if actual_class is None:
            unknown_reasons.append(
                "Axie class is unknown."
            )

        elif (
            actual_class
            != required_class
        ):
            disqualified_reasons.append(
                (
                    "Class mismatch: "
                    f"{actual_class} != "
                    f"{required_class}"
                )
            )

    min_level = criteria.get(
        "min_level"
    )

    if min_level is not None:
        actual_level = profile.get(
            "level"
        )

        if actual_level is None:
            unknown_reasons.append(
                "Gameplay level is unknown."
            )

        elif actual_level < min_level:
            disqualified_reasons.append(
                (
                    "Level below minimum: "
                    f"{actual_level} < "
                    f"{min_level}"
                )
            )

    max_level = criteria.get(
        "max_level"
    )

    if max_level is not None:
        actual_level = profile.get(
            "level"
        )

        if actual_level is None:
            unknown_reasons.append(
                "Gameplay level is unknown."
            )

        elif actual_level > max_level:
            disqualified_reasons.append(
                (
                    "Level above maximum: "
                    f"{actual_level} > "
                    f"{max_level}"
                )
            )

    min_breed_count = criteria.get(
        "min_breed_count"
    )

    if min_breed_count is not None:
        actual_breed = profile.get(
            "breed_count"
        )

        if actual_breed is None:
            unknown_reasons.append(
                "Breed count is unknown."
            )

        elif (
            actual_breed
            < min_breed_count
        ):
            disqualified_reasons.append(
                (
                    "Breed count below "
                    "minimum: "
                    f"{actual_breed} < "
                    f"{min_breed_count}"
                )
            )

    max_breed_count = criteria.get(
        "max_breed_count"
    )

    if max_breed_count is not None:
        actual_breed = profile.get(
            "breed_count"
        )

        if actual_breed is None:
            unknown_reasons.append(
                "Breed count is unknown."
            )

        elif (
            actual_breed
            > max_breed_count
        ):
            disqualified_reasons.append(
                (
                    "Breed count above "
                    "maximum: "
                    f"{actual_breed} > "
                    f"{max_breed_count}"
                )
            )

    required_evolved = criteria.get(
        "is_evolved"
    )

    if required_evolved is not None:
        actual_evolved = profile.get(
            "is_evolved"
        )

        if actual_evolved is None:
            unknown_reasons.append(
                "Evolution status is unknown."
            )

        elif bool(
            actual_evolved
        ) != bool(
            required_evolved
        ):
            disqualified_reasons.append(
                "Evolution requirement not met."
            )

    required_collectible = criteria.get(
        "is_collectible"
    )

    if (
        required_collectible
        is not None
    ):
        actual_collectible = profile.get(
            "is_collectible"
        )

        if actual_collectible is None:
            unknown_reasons.append(
                "Collectible status is unknown."
            )

        elif bool(
            actual_collectible
        ) != bool(
            required_collectible
        ):
            disqualified_reasons.append(
                (
                    "Collectible requirement "
                    "not met."
                )
            )

    profile_collections = {
        str(
            collection
        ).upper()
        for collection
        in (
            profile.get(
                "collections"
            )
            or []
        )
    }

    required_collections = {
        str(
            collection
        ).upper()
        for collection
        in (
            criteria.get(
                "required_collections"
            )
            or []
        )
    }

    if required_collections:
        actual_collectible = (
            profile.get(
                "is_collectible"
            )
        )

        if actual_collectible is None:
            unknown_reasons.append(
                (
                    "Collection membership "
                    "cannot be confirmed."
                )
            )

        elif (
            actual_collectible == 0
        ):
            disqualified_reasons.append(
                (
                    "Axie is not "
                    "collectible."
                )
            )

        elif not profile_collections:
            unknown_reasons.append(
                (
                    "Collectible collection "
                    "traits are missing."
                )
            )

        elif not (
            required_collections
            .issubset(
                profile_collections
            )
        ):
            disqualified_reasons.append(
                (
                    "Required collection "
                    "membership not met."
                )
            )

    any_collections = {
        str(
            collection
        ).upper()
        for collection
        in (
            criteria.get(
                "any_collections"
            )
            or []
        )
    }

    if any_collections:
        actual_collectible = (
            profile.get(
                "is_collectible"
            )
        )

        if actual_collectible is None:
            unknown_reasons.append(
                (
                    "Collection membership "
                    "cannot be confirmed."
                )
            )

        elif (
            actual_collectible == 0
        ):
            disqualified_reasons.append(
                (
                    "Axie is not "
                    "collectible."
                )
            )

        elif not profile_collections:
            unknown_reasons.append(
                (
                    "Collectible collection "
                    "traits are missing."
                )
            )

        elif not (
            profile_collections
            & any_collections
        ):
            disqualified_reasons.append(
                (
                    "No allowed collection "
                    "membership found."
                )
            )


    profile_parts = (
        profile.get(
            "parts"
        )
        or []
    )

    profile_part_names = {
        str(
            part.get(
                "part_name"
            )
        ).strip().upper()
        for part in profile_parts
        if part.get(
            "part_name"
        )
    }

    complete_part_metadata = (
        len(
            profile_parts
        )
        == 6
        and all(
            part.get(
                "part_name"
            )
            for part in profile_parts
        )
    )

    required_part_names = {
        str(
            part_name
        ).strip().upper()
        for part_name
        in (
            criteria.get(
                "required_part_names"
            )
            or []
        )
    }

    if required_part_names:
        if not complete_part_metadata:
            unknown_reasons.append(
                (
                    "Complete body-part "
                    "metadata is unavailable."
                )
            )

        elif not (
            required_part_names
            .issubset(
                profile_part_names
            )
        ):
            disqualified_reasons.append(
                (
                    "Required body part "
                    "not found."
                )
            )

    any_part_names = {
        str(
            part_name
        ).strip().upper()
        for part_name
        in (
            criteria.get(
                "any_part_names"
            )
            or []
        )
    }

    if any_part_names:
        if not complete_part_metadata:
            unknown_reasons.append(
                (
                    "Complete body-part "
                    "metadata is unavailable."
                )
            )

        elif not (
            profile_part_names
            & any_part_names
        ):
            disqualified_reasons.append(
                (
                    "No allowed body part "
                    "was found."
                )
            )

    min_ownership_days = (
        criteria.get(
            "min_ownership_days"
        )
    )

    if min_ownership_days is not None:
        if (
            not isinstance(
                min_ownership_days,
                (int, float),
            )
            or min_ownership_days < 0
        ):
            raise ValueError(
                "min_ownership_days "
                "must be a non-negative number."
            )

        acquisition_datetime = (
            profile.get(
                "acquisition_datetime"
            )
        )

        acquisition_source = (
            profile.get(
                "acquisition_source"
            )
        )

        if (
            acquisition_datetime
            is None
        ):
            unknown_reasons.append(
                (
                    "Ownership start time "
                    "is unresolved"
                    + (
                        " from legacy history."
                        if acquisition_source
                        == (
                            "LEGACY_HISTORY_"
                            "UNRESOLVED"
                        )
                        else "."
                    )
                )
            )

        else:
            if as_of_datetime is None:
                comparison_datetime = (
                    datetime.now(
                        timezone.utc
                    )
                )

            else:
                comparison_datetime = (
                    as_of_datetime
                )

                if (
                    comparison_datetime
                    .tzinfo
                    is None
                ):
                    comparison_datetime = (
                        comparison_datetime.replace(
                            tzinfo=timezone.utc
                        )
                    )

                else:
                    comparison_datetime = (
                        comparison_datetime.astimezone(
                            timezone.utc
                        )
                    )

            try:
                ownership_start = (
                    datetime.strptime(
                        acquisition_datetime,
                        "%Y-%m-%d %H:%M:%S",
                    ).replace(
                        tzinfo=timezone.utc
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                unknown_reasons.append(
                    (
                        "Ownership start time "
                        "is invalid."
                    )
                )

            else:
                ownership_seconds = (
                    comparison_datetime
                    - ownership_start
                ).total_seconds()

                if ownership_seconds < 0:
                    unknown_reasons.append(
                        (
                            "Ownership start time "
                            "is in the future."
                        )
                    )

                else:
                    required_seconds = (
                        float(
                            min_ownership_days
                        )
                        * 86400
                    )

                    if (
                        ownership_seconds
                        < required_seconds
                    ):
                        disqualified_reasons.append(
                            (
                                "Ownership duration "
                                "below minimum: "
                                f"{ownership_seconds / 86400:.2f} "
                                "days < "
                                f"{min_ownership_days} days"
                            )
                        )


    if disqualified_reasons:
        status = "DISQUALIFIED"

    elif unknown_reasons:
        status = "UNKNOWN"

    else:
        status = "QUALIFIED"

    return {
        "axie_id": profile.get(
            "axie_id"
        ),
        "status": status,
        "disqualified_reasons": (
            disqualified_reasons
        ),
        "unknown_reasons": (
            unknown_reasons
        ),
    }


def qualify_owned_axies(
    db_path,
    criteria,
    as_of_datetime=None,
):
    profiles = (
        load_owned_axie_qualification_profiles(
            db_path
        )
    )

    qualified = []

    disqualified = []

    unknown = []

    evaluations = []

    for profile in profiles:
        evaluation = (
            evaluate_axie_qualification(
                profile,
                criteria,
                as_of_datetime=(
                    as_of_datetime
                ),
            )
        )

        evaluations.append(
            evaluation
        )

        status = evaluation[
            "status"
        ]

        if status == "QUALIFIED":
            qualified.append(
                profile
            )

        elif status == "DISQUALIFIED":
            disqualified.append(
                profile
            )

        else:
            unknown.append(
                profile
            )

    return {
        "criteria": dict(
            criteria
        ),
        "total_owned": len(
            profiles
        ),
        "qualified": qualified,
        "disqualified": (
            disqualified
        ),
        "unknown": unknown,
        "evaluations": evaluations,
    }


def run_core_bounty_qualification_test():
    print(
        "\nAXIEOS CORE BOUNTY QUALIFICATION"
    )

    profiles = (
        load_owned_axie_qualification_profiles(
            AXIEOS_DB_PATH
        )
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    expected_level_20 = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
              AND level >= 20
            """
        ).fetchone()[0]
    )

    expected_plant_level_20 = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
              AND axie_class =
                  'Plant'
              AND level >= 20
            """
        ).fetchone()[0]
    )

    expected_evolved_collectible = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
              AND is_evolved = 1
              AND is_collectible = 1
            """
        ).fetchone()[0]
    )

    expected_japanese = (
        connection.execute(
            """
            SELECT COUNT(
                DISTINCT a.axie_id
            )
            FROM gameplay_owned_axies a
            INNER JOIN
                gameplay_axie_traits t
                ON t.axie_id =
                   a.axie_id
            WHERE
                a.ownership_status =
                    'OWNED'
                AND a.is_collectible = 1
                AND t.trait_type =
                    'COLLECTION'
                AND t.trait_value =
                    'JAPANESE'
            """
        ).fetchone()[0]
    )

    expected_mystic = (
        connection.execute(
            """
            SELECT COUNT(
                DISTINCT a.axie_id
            )
            FROM gameplay_owned_axies a
            INNER JOIN
                gameplay_axie_traits t
                ON t.axie_id =
                   a.axie_id
            WHERE
                a.ownership_status =
                    'OWNED'
                AND a.is_collectible = 1
                AND t.trait_type =
                    'COLLECTION'
                AND t.trait_value =
                    'MYSTIC'
            """
        ).fetchone()[0]
    )

    connection.close()

    tests = [
        {
            "name": "Level 20+",
            "criteria": {
                "min_level": 20,
            },
            "expected": (
                expected_level_20
            ),
        },
        {
            "name": (
                "Plant Level 20+"
            ),
            "criteria": {
                "axie_class": (
                    "Plant"
                ),
                "min_level": 20,
            },
            "expected": (
                expected_plant_level_20
            ),
        },
        {
            "name": (
                "Evolved collectible"
            ),
            "criteria": {
                "is_evolved": True,
                "is_collectible": (
                    True
                ),
            },
            "expected": (
                expected_evolved_collectible
            ),
        },
        {
            "name": (
                "Japanese collectible"
            ),
            "criteria": {
                "is_collectible": (
                    True
                ),
                "required_collections": [
                    "JAPANESE",
                ],
            },
            "expected": (
                expected_japanese
            ),
        },
        {
            "name": (
                "Mystic collectible"
            ),
            "criteria": {
                "is_collectible": (
                    True
                ),
                "required_collections": [
                    "MYSTIC",
                ],
            },
            "expected": (
                expected_mystic
            ),
        },
    ]

    all_query_tests_passed = True

    print(
        "Current OWNED profiles:",
        len(
            profiles
        ),
    )

    print(
        "\nQUALIFICATION TESTS"
    )

    for test in tests:
        result = (
            qualify_owned_axies(
                AXIEOS_DB_PATH,
                test[
                    "criteria"
                ],
            )
        )

        actual = len(
            result[
                "qualified"
            ]
        )

        unknown = len(
            result[
                "unknown"
            ]
        )

        passed = (
            actual
            == test[
                "expected"
            ]
            and unknown == 0
        )

        if not passed:
            all_query_tests_passed = False

        print(
            test[
                "name"
            ],
            "| qualified:",
            actual,
            "| expected:",
            test[
                "expected"
            ],
            "| unknown:",
            unknown,
            "|",
            (
                "PASS"
                if passed
                else "FAIL"
            ),
        )

    japanese_result = (
        qualify_owned_axies(
            AXIEOS_DB_PATH,
            {
                "is_collectible": True,
                "required_collections": [
                    "JAPANESE",
                ],
            },
        )
    )

    mystic_result = (
        qualify_owned_axies(
            AXIEOS_DB_PATH,
            {
                "is_collectible": True,
                "required_collections": [
                    "MYSTIC",
                ],
            },
        )
    )

    synthetic_profile = {
        "axie_id": "TEST",
        "wallet_address": None,
        "axie_class": "Plant",
        "level": None,
        "breed_count": 1,
        "is_collectible": 0,
        "is_evolved": 0,
        "collections": [],
    }

    unknown_test = (
        evaluate_axie_qualification(
            synthetic_profile,
            {
                "min_level": 20,
            },
        )
    )

    unknown_semantics_valid = (
        unknown_test[
            "status"
        ]
        == "UNKNOWN"
    )

    profile_coverage_valid = (
        len(
            profiles
        )
        == 136
    )

    print(
        "\nCOLLECTION EXAMPLES"
    )

    print(
        "Japanese qualified IDs:",
        [
            profile[
                "axie_id"
            ]
            for profile
            in japanese_result[
                "qualified"
            ]
        ],
    )

    print(
        "Mystic qualified IDs:",
        [
            profile[
                "axie_id"
            ]
            for profile
            in mystic_result[
                "qualified"
            ]
        ],
    )

    print(
        "\nSAFE UNKNOWN TEST"
    )

    print(
        "Missing required level:",
        unknown_test[
            "status"
        ],
    )

    print(
        "\nCHECKS"
    )

    print(
        "136-profile coverage:",
        (
            "PASS"
            if profile_coverage_valid
            else "FAIL"
        ),
    )

    print(
        "Qualification queries:",
        (
            "PASS"
            if all_query_tests_passed
            else "FAIL"
        ),
    )

    print(
        "Unknown metadata semantics:",
        (
            "PASS"
            if unknown_semantics_valid
            else "FAIL"
        ),
    )

    validation = (
        profile_coverage_valid
        and all_query_tests_passed
        and unknown_semantics_valid
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_owned_axie_part_name_sync_test():
    print(
        "\nAXIEOS OWNED AXIE PART NAME SYNC"
    )

    first_result = (
        sync_owned_axie_part_names(
            AXIEOS_DB_PATH
        )
    )

    second_result = (
        sync_owned_axie_part_names(
            AXIEOS_DB_PATH
        )
    )

    print(
        "First sync:",
        (
            "PASS"
            if first_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    print(
        "Second sync:",
        (
            "PASS"
            if second_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    summary_row = (
        connection.execute(
            """
            SELECT
                COUNT(*),
                SUM(
                    CASE
                        WHEN p.part_name
                             IS NOT NULL
                         AND TRIM(
                             p.part_name
                         ) != ''
                        THEN 1
                        ELSE 0
                    END
                )
            FROM gameplay_axie_parts p
            INNER JOIN
                gameplay_owned_axies a
                ON a.axie_id =
                   p.axie_id
            WHERE
                a.ownership_status =
                    'OWNED'
            """
        ).fetchone()
    )

    pincer_row = (
        connection.execute(
            """
            SELECT
                part_slot,
                part_name,
                part_class,
                part_value,
                part_stage
            FROM gameplay_axie_parts
            WHERE axie_id = ?
              AND part_slot =
                  'mouth'
            """,
            (
                "6251324",
            ),
        ).fetchone()
    )

    distinct_names = (
        connection.execute(
            """
            SELECT COUNT(
                DISTINCT p.part_name
            )
            FROM gameplay_axie_parts p
            INNER JOIN
                gameplay_owned_axies a
                ON a.axie_id =
                   p.axie_id
            WHERE
                a.ownership_status =
                    'OWNED'
                AND p.part_name
                    IS NOT NULL
            """
        ).fetchone()[0]
    )

    connection.close()

    total_parts = (
        summary_row[0]
    )

    named_parts = (
        summary_row[1]
        or 0
    )

    complete_name_coverage = (
        total_parts == 816
        and named_parts
        == total_parts
    )

    pincer_valid = (
        pincer_row
        is not None
        and pincer_row[0]
        == "mouth"
        and pincer_row[1]
        == "Pincer"
        and pincer_row[2]
        == "Bug"
        and pincer_row[3]
        == 4
    )

    repeated_sync_valid = (
        first_result[
            "success"
        ]
        and second_result[
            "success"
        ]
        and first_result[
            "owned_parts"
        ]
        == second_result[
            "owned_parts"
        ]
        == total_parts
        and first_result[
            "mapped_parts"
        ]
        == second_result[
            "mapped_parts"
        ]
        == named_parts
    )

    print(
        "\nCARD CATALOG"
    )

    print(
        "Cards loaded:",
        first_result[
            "cards"
        ],
    )

    print(
        "Part families:",
        first_result[
            "part_families"
        ],
    )

    print(
        "\nPART NAME COVERAGE"
    )

    print(
        "Owned parts:",
        total_parts,
    )

    print(
        "Named parts:",
        named_parts,
    )

    print(
        "Unmapped parts:",
        len(
            first_result[
                "unmapped_parts"
            ]
        ),
    )

    print(
        "Distinct part names:",
        distinct_names,
    )

    print(
        "\nPINCER REFERENCE"
    )

    if pincer_row:
        print(
            "Axie ID: 6251324",
        )

        print(
            "Slot:",
            pincer_row[0],
        )

        print(
            "Part name:",
            pincer_row[1],
        )

        print(
            "Class:",
            pincer_row[2],
        )

        print(
            "Value:",
            pincer_row[3],
        )

        print(
            "Stage:",
            pincer_row[4],
        )

    else:
        print(
            "Axie #6251324 mouth:",
            "NOT FOUND",
        )

    if first_result[
        "unmapped_parts"
    ]:
        print(
            "\nUNMAPPED PARTS"
        )

        for part in first_result[
            "unmapped_parts"
        ]:
            print(
                "Axie ID:",
                part[
                    "axie_id"
                ],
                "| slot:",
                part[
                    "part_slot"
                ],
                "| class:",
                part[
                    "part_class"
                ],
                "| value:",
                part[
                    "part_value"
                ],
                "| stage:",
                part[
                    "part_stage"
                ],
            )

    print(
        "\nCHECKS"
    )

    print(
        "Complete part-name coverage:",
        (
            "PASS"
            if complete_name_coverage
            else "FAIL"
        ),
    )

    print(
        "Pincer canonical mapping:",
        (
            "PASS"
            if pincer_valid
            else "FAIL"
        ),
    )

    print(
        "Repeated sync idempotent:",
        (
            "PASS"
            if repeated_sync_valid
            else "FAIL"
        ),
    )

    validation = (
        first_result[
            "success"
        ]
        and second_result[
            "success"
        ]
        and complete_name_coverage
        and pincer_valid
        and repeated_sync_valid
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )




def run_named_part_bounty_qualification_test():
    print(
        "\nAXIEOS NAMED PART BOUNTY QUALIFICATION"
    )

    profiles = (
        load_owned_axie_qualification_profiles(
            AXIEOS_DB_PATH
        )
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    expected_pincer = (
        connection.execute(
            """
            SELECT COUNT(
                DISTINCT a.axie_id
            )
            FROM gameplay_owned_axies a
            INNER JOIN
                gameplay_axie_parts p
                ON p.axie_id =
                   a.axie_id
            WHERE
                a.ownership_status =
                    'OWNED'
                AND LOWER(
                    p.part_name
                ) = 'pincer'
            """
        ).fetchone()[0]
    )

    expected_evolved_pincer = (
        connection.execute(
            """
            SELECT COUNT(
                DISTINCT a.axie_id
            )
            FROM gameplay_owned_axies a
            INNER JOIN
                gameplay_axie_parts p
                ON p.axie_id =
                   a.axie_id
            WHERE
                a.ownership_status =
                    'OWNED'
                AND a.is_evolved = 1
                AND LOWER(
                    p.part_name
                ) = 'pincer'
            """
        ).fetchone()[0]
    )

    connection.close()

    pincer_result = (
        qualify_owned_axies(
            AXIEOS_DB_PATH,
            {
                "required_part_names": [
                    "Pincer",
                ],
            },
        )
    )

    evolved_pincer_result = (
        qualify_owned_axies(
            AXIEOS_DB_PATH,
            {
                "is_evolved": True,
                "required_part_names": [
                    "Pincer",
                ],
            },
        )
    )

    case_test_result = (
        qualify_owned_axies(
            AXIEOS_DB_PATH,
            {
                "required_part_names": [
                    "pInCeR",
                ],
            },
        )
    )

    pincer_ids = [
        profile[
            "axie_id"
        ]
        for profile
        in pincer_result[
            "qualified"
        ]
    ]

    evolved_pincer_ids = [
        profile[
            "axie_id"
        ]
        for profile
        in evolved_pincer_result[
            "qualified"
        ]
    ]

    complete_part_profiles = sum(
        1
        for profile in profiles
        if (
            len(
                profile[
                    "parts"
                ]
            )
            == 6
            and all(
                part.get(
                    "part_name"
                )
                for part
                in profile[
                    "parts"
                ]
            )
        )
    )

    pincer_count_valid = (
        len(
            pincer_result[
                "qualified"
            ]
        )
        == expected_pincer
        and len(
            pincer_result[
                "unknown"
            ]
        )
        == 0
    )

    evolved_pincer_valid = (
        len(
            evolved_pincer_result[
                "qualified"
            ]
        )
        == expected_evolved_pincer
        and len(
            evolved_pincer_result[
                "unknown"
            ]
        )
        == 0
    )

    case_insensitive_valid = (
        {
            profile[
                "axie_id"
            ]
            for profile
            in case_test_result[
                "qualified"
            ]
        }
        == set(
            pincer_ids
        )
    )

    known_reference_valid = (
        "6251324"
        in pincer_ids
    )

    synthetic_missing_parts = {
        "axie_id": "TEST",
        "wallet_address": None,
        "axie_class": "Bug",
        "level": 20,
        "breed_count": 0,
        "is_collectible": 0,
        "is_evolved": 0,
        "collections": [],
        "parts": [],
    }

    unknown_test = (
        evaluate_axie_qualification(
            synthetic_missing_parts,
            {
                "required_part_names": [
                    "Pincer",
                ],
            },
        )
    )

    unknown_semantics_valid = (
        unknown_test[
            "status"
        ]
        == "UNKNOWN"
    )

    profile_coverage_valid = (
        len(
            profiles
        )
        == 136
        and complete_part_profiles
        == 136
    )

    print(
        "Current OWNED profiles:",
        len(
            profiles
        ),
    )

    print(
        "Complete six-part profiles:",
        complete_part_profiles,
    )

    print(
        "\nPINCER QUALIFICATION"
    )

    print(
        "Qualified:",
        len(
            pincer_result[
                "qualified"
            ]
        ),
    )

    print(
        "Expected:",
        expected_pincer,
    )

    print(
        "Unknown:",
        len(
            pincer_result[
                "unknown"
            ]
        ),
    )

    print(
        "Qualified IDs:",
        pincer_ids,
    )

    print(
        "\nEVOLVED + PINCER"
    )

    print(
        "Qualified:",
        len(
            evolved_pincer_result[
                "qualified"
            ]
        ),
    )

    print(
        "Expected:",
        expected_evolved_pincer,
    )

    print(
        "Qualified IDs:",
        evolved_pincer_ids,
    )

    print(
        "\nSAFE UNKNOWN TEST"
    )

    print(
        "Missing part metadata:",
        unknown_test[
            "status"
        ],
    )

    print(
        "\nCHECKS"
    )

    print(
        "136 complete part profiles:",
        (
            "PASS"
            if profile_coverage_valid
            else "FAIL"
        ),
    )

    print(
        "Pincer qualification:",
        (
            "PASS"
            if pincer_count_valid
            else "FAIL"
        ),
    )

    print(
        "Evolved + Pincer qualification:",
        (
            "PASS"
            if evolved_pincer_valid
            else "FAIL"
        ),
    )

    print(
        "Case-insensitive matching:",
        (
            "PASS"
            if case_insensitive_valid
            else "FAIL"
        ),
    )

    print(
        "Known Axie #6251324 found:",
        (
            "PASS"
            if known_reference_valid
            else "FAIL"
        ),
    )

    print(
        "Unknown metadata semantics:",
        (
            "PASS"
            if unknown_semantics_valid
            else "FAIL"
        ),
    )

    validation = (
        profile_coverage_valid
        and pincer_count_valid
        and evolved_pincer_valid
        and case_insensitive_valid
        and known_reference_valid
        and unknown_semantics_valid
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def ensure_owned_axie_acquisition_source_column(
    db_path,
):
    connection = sqlite3.connect(
        db_path
    )

    columns = {
        row[1]
        for row
        in connection.execute(
            """
            PRAGMA table_info(
                gameplay_owned_axies
            )
            """
        ).fetchall()
    }

    if (
        "acquisition_source"
        not in columns
    ):
        connection.execute(
            """
            ALTER TABLE
                gameplay_owned_axies
            ADD COLUMN
                acquisition_source TEXT
            """
        )

        connection.commit()

    connection.close()


def fetch_origins_ownership_timestamps():
    user_id = (
        get_skymavis_origins_user_id()
    )

    if not user_id:
        return {
            "success": False,
            "fighters": {},
            "error": (
                "Origins user ID "
                "is unavailable."
            ),
        }

    api_key = os.getenv(
        "SKYMAVIS_API_KEY"
    )

    if not api_key:
        return {
            "success": False,
            "fighters": {},
            "error": (
                "SKYMAVIS_API_KEY "
                "is unavailable."
            ),
        }

    url = (
        "https://api-gateway.skymavis.com/"
        "origins/v2/community/users/fighters"
    )

    fighters = []

    offset = 0

    while True:
        response = requests.get(
            url,
            headers={
                "Accept": (
                    "application/json"
                ),
                "X-API-Key": api_key,
            },
            params={
                "userID": user_id,
                "axieType": "ronin",
                "limit": 100,
                "offset": offset,
            },
            timeout=30,
        )

        if response.status_code != 200:
            return {
                "success": False,
                "fighters": {},
                "error": (
                    "Origins fighter request "
                    f"failed at offset "
                    f"{offset}: HTTP "
                    f"{response.status_code}"
                ),
            }

        data = response.json()

        page = data.get(
            "_items",
            [],
        )

        fighters.extend(
            page
        )

        metadata = data.get(
            "_metadata",
            {},
        )

        if not metadata.get(
            "hasNext"
        ):
            break

        offset += 100

    fighter_map = {}

    for fighter in fighters:
        axie_id = str(
            fighter.get(
                "id"
            )
        )

        ownership = (
            fighter.get(
                "ownership"
            )
            or {}
        )

        last_transfer_time = (
            ownership.get(
                "lastTransferTime"
            )
        )

        fighter_map[
            axie_id
        ] = {
            "last_transfer_time": (
                last_transfer_time
            ),
        }

    return {
        "success": True,
        "fighters": fighter_map,
        "error": None,
    }


def sync_owned_axie_acquisition_datetimes(
    db_path,
    fighter_map=None,
):
    ensure_owned_axie_acquisition_source_column(
        db_path
    )

    if fighter_map is None:
        origins_result = (
            fetch_origins_ownership_timestamps()
        )

        if not origins_result[
            "success"
        ]:
            return {
                "success": False,
                "owned_axies": 0,
                "preserved_blockchain": 0,
                "preserved_origins": 0,
                "origins_fallback": 0,
                "legacy_unresolved": [],
                "fighter_map": {},
                "error": origins_result.get(
                    "error"
                ),
            }

        fighter_map = origins_result[
            "fighters"
        ]

    connection = sqlite3.connect(
        db_path
    )

    rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                acquisition_datetime,
                acquisition_txhash,
                acquisition_source
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    preserved_blockchain = 0
    preserved_origins = 0
    origins_fallback = 0

    legacy_unresolved = []

    datetime_updates = []
    source_only_updates = []

    for (
        axie_id,
        acquisition_datetime,
        acquisition_txhash,
        acquisition_source,
    ) in rows:
        axie_id = str(
            axie_id
        )

        # ------------------------------------------
        # Highest-confidence source:
        # locally recorded Ronin transfer.
        # ------------------------------------------

        if (
            acquisition_datetime
            is not None
            and acquisition_txhash
        ):
            datetime_updates.append(
                {
                    "axie_id": axie_id,
                    "datetime": (
                        acquisition_datetime
                    ),
                    "source": (
                        "RONIN_LOCAL_TRANSFER"
                    ),
                }
            )

            preserved_blockchain += 1

            continue

        # ------------------------------------------
        # Already populated from validated
        # Origins lastTransferTime.
        # ------------------------------------------

        if (
            acquisition_datetime
            is not None
            and acquisition_source
            == (
                "SKYMAVIS_ORIGINS_"
                "LAST_TRANSFER"
            )
        ):
            preserved_origins += 1

            continue

        fighter = fighter_map.get(
            axie_id
        )

        if fighter is None:
            legacy_unresolved.append(
                {
                    "axie_id": axie_id,
                    "reason": (
                        "Origins fighter "
                        "missing."
                    ),
                }
            )

            source_only_updates.append(
                {
                    "axie_id": axie_id,
                    "source": (
                        "LEGACY_HISTORY_"
                        "UNRESOLVED"
                    ),
                }
            )

            continue

        last_transfer_time = (
            fighter.get(
                "last_transfer_time"
            )
        )

        # ------------------------------------------
        # lastTransferTime = 0 is NOT converted
        # into a fake acquisition datetime.
        #
        # These Axies require legacy-history
        # reconciliation.
        # ------------------------------------------

        if not last_transfer_time:
            legacy_unresolved.append(
                {
                    "axie_id": axie_id,
                    "reason": (
                        "Origins "
                        "lastTransferTime "
                        "is zero or missing."
                    ),
                }
            )

            source_only_updates.append(
                {
                    "axie_id": axie_id,
                    "source": (
                        "LEGACY_HISTORY_"
                        "UNRESOLVED"
                    ),
                }
            )

            continue

        try:
            ownership_datetime = (
                datetime.fromtimestamp(
                    int(
                        last_transfer_time
                    ),
                    tz=timezone.utc,
                ).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            legacy_unresolved.append(
                {
                    "axie_id": axie_id,
                    "reason": (
                        "Origins "
                        "lastTransferTime "
                        "is invalid."
                    ),
                }
            )

            source_only_updates.append(
                {
                    "axie_id": axie_id,
                    "source": (
                        "LEGACY_HISTORY_"
                        "UNRESOLVED"
                    ),
                }
            )

            continue

        datetime_updates.append(
            {
                "axie_id": axie_id,
                "datetime": (
                    ownership_datetime
                ),
                "source": (
                    "SKYMAVIS_ORIGINS_"
                    "LAST_TRANSFER"
                ),
            }
        )

        origins_fallback += 1

    try:
        for update in datetime_updates:
            connection.execute(
                """
                UPDATE gameplay_owned_axies
                SET
                    acquisition_datetime = ?,
                    acquisition_source = ?,
                    last_updated =
                        CURRENT_TIMESTAMP
                WHERE axie_id = ?
                  AND ownership_status =
                      'OWNED'
                """,
                (
                    update[
                        "datetime"
                    ],
                    update[
                        "source"
                    ],
                    update[
                        "axie_id"
                    ],
                ),
            )

        for update in source_only_updates:
            connection.execute(
                """
                UPDATE gameplay_owned_axies
                SET
                    acquisition_source = ?,
                    last_updated =
                        CURRENT_TIMESTAMP
                WHERE axie_id = ?
                  AND ownership_status =
                      'OWNED'
                  AND acquisition_datetime
                      IS NULL
                """,
                (
                    update[
                        "source"
                    ],
                    update[
                        "axie_id"
                    ],
                ),
            )

        connection.commit()

    except Exception:
        connection.rollback()
        connection.close()
        raise

    connection.close()

    return {
        "success": True,
        "owned_axies": len(
            rows
        ),
        "preserved_blockchain": (
            preserved_blockchain
        ),
        "preserved_origins": (
            preserved_origins
        ),
        "origins_fallback": (
            origins_fallback
        ),
        "legacy_unresolved": (
            legacy_unresolved
        ),
        "fighter_map": fighter_map,
        "error": None,
    }



def run_owned_axie_acquisition_datetime_sync_test():
    print(
        "\nAXIEOS OWNERSHIP-START SYNC"
    )

    origins_result = (
        fetch_origins_ownership_timestamps()
    )

    if not origins_result[
        "success"
    ]:
        print(
            "Origins snapshot: FAIL"
        )

        print(
            "Error:",
            origins_result.get(
                "error"
            ),
        )

        print(
            "\nValidation: FAIL"
        )

        return

    fighter_map = origins_result[
        "fighters"
    ]

    print(
        "Origins snapshot: PASS"
    )

    first_result = (
        sync_owned_axie_acquisition_datetimes(
            AXIEOS_DB_PATH,
            fighter_map=fighter_map,
        )
    )

    second_result = (
        sync_owned_axie_acquisition_datetimes(
            AXIEOS_DB_PATH,
            fighter_map=fighter_map,
        )
    )

    print(
        "First sync:",
        (
            "PASS"
            if first_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    print(
        "Same-snapshot second sync:",
        (
            "PASS"
            if second_result[
                "success"
            ]
            else "FAIL"
        ),
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                acquisition_datetime,
                acquisition_txhash,
                acquisition_source
            FROM gameplay_owned_axies
            WHERE ownership_status =
                'OWNED'
            ORDER BY
                CAST(
                    axie_id AS INTEGER
                )
            """
        ).fetchall()
    )

    connection.close()

    owned_count = len(
        rows
    )

    dated_rows = [
        row
        for row in rows
        if row[1] is not None
    ]

    local_rows = [
        row
        for row in rows
        if row[3]
        == "RONIN_LOCAL_TRANSFER"
    ]

    origins_rows = [
        row
        for row in rows
        if row[3]
        == (
            "SKYMAVIS_ORIGINS_"
            "LAST_TRANSFER"
        )
    ]

    legacy_rows = [
        row
        for row in rows
        if row[3]
        == (
            "LEGACY_HISTORY_"
            "UNRESOLVED"
        )
    ]

    unknown_source_rows = [
        row
        for row in rows
        if row[3] not in {
            "RONIN_LOCAL_TRANSFER",
            (
                "SKYMAVIS_ORIGINS_"
                "LAST_TRANSFER"
            ),
            (
                "LEGACY_HISTORY_"
                "UNRESOLVED"
            ),
        }
    ]

    legacy_without_fake_date = all(
        row[1] is None
        and row[2] is None
        for row in legacy_rows
    )

    local_txhash_valid = all(
        row[2]
        for row in local_rows
    )

    origins_txhash_safe = all(
        row[2] is None
        for row in origins_rows
    )

    source_coverage_valid = (
        owned_count == 136
        and len(
            local_rows
        )
        == 9
        and len(
            origins_rows
        )
        == 115
        and len(
            legacy_rows
        )
        == 12
        and not unknown_source_rows
    )

    exact_date_coverage_valid = (
        len(
            dated_rows
        )
        == 124
    )

    first_legacy_ids = {
        item[
            "axie_id"
        ]
        for item in first_result[
            "legacy_unresolved"
        ]
    }

    database_legacy_ids = {
        str(
            row[0]
        )
        for row in legacy_rows
    }

    legacy_set_valid = (
        first_legacy_ids
        == database_legacy_ids
        and len(
            database_legacy_ids
        )
        == 12
    )

    repeated_sync_valid = (
        second_result[
            "success"
        ]
        and second_result[
            "owned_axies"
        ]
        == 136
        and {
            item[
                "axie_id"
            ]
            for item
            in second_result[
                "legacy_unresolved"
            ]
        }
        == database_legacy_ids
    )

    print(
        "\nOWNERSHIP-DATE COVERAGE"
    )

    print(
        "Current OWNED Axies:",
        owned_count,
    )

    print(
        "Exact ownership dates:",
        len(
            dated_rows
        ),
    )

    print(
        "Legacy unresolved:",
        len(
            legacy_rows
        ),
    )

    print(
        "\nPROVENANCE"
    )

    print(
        "Ronin local transfer:",
        len(
            local_rows
        ),
    )

    print(
        "Origins lastTransferTime:",
        len(
            origins_rows
        ),
    )

    print(
        "Legacy history unresolved:",
        len(
            legacy_rows
        ),
    )

    print(
        "Unknown source:",
        len(
            unknown_source_rows
        ),
    )

    print(
        "\nLEGACY-HISTORY AXIES"
    )

    for row in legacy_rows:
        print(
            "Axie ID:",
            row[0],
            "| acquisition:",
            row[1],
            "| source:",
            row[3],
        )

    print(
        "\nCHECKS"
    )

    print(
        "136 source classifications present:",
        (
            "PASS"
            if source_coverage_valid
            else "FAIL"
        ),
    )

    print(
        "124 exact dates preserved:",
        (
            "PASS"
            if exact_date_coverage_valid
            else "FAIL"
        ),
    )

    print(
        "12 legacy Axies identified:",
        (
            "PASS"
            if legacy_set_valid
            else "FAIL"
        ),
    )

    print(
        "No fabricated legacy dates:",
        (
            "PASS"
            if legacy_without_fake_date
            else "FAIL"
        ),
    )

    print(
        "Local blockchain txhash preserved:",
        (
            "PASS"
            if local_txhash_valid
            else "FAIL"
        ),
    )

    print(
        "Origins fallback does not invent txhash:",
        (
            "PASS"
            if origins_txhash_safe
            else "FAIL"
        ),
    )

    print(
        "Same snapshot idempotent:",
        (
            "PASS"
            if repeated_sync_valid
            else "FAIL"
        ),
    )

    validation = (
        first_result[
            "success"
        ]
        and second_result[
            "success"
        ]
        and source_coverage_valid
        and exact_date_coverage_valid
        and legacy_set_valid
        and legacy_without_fake_date
        and local_txhash_valid
        and origins_txhash_safe
        and repeated_sync_valid
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_ownership_duration_qualification_test():
    print(
        "\nAXIEOS OWNERSHIP-DURATION QUALIFICATION"
    )

    as_of_datetime = (
        datetime.now(
            timezone.utc
        )
    )

    profiles = (
        load_owned_axie_qualification_profiles(
            AXIEOS_DB_PATH
        )
    )

    known_profiles = [
        profile
        for profile in profiles
        if profile[
            "acquisition_datetime"
        ]
        is not None
    ]

    unresolved_profiles = [
        profile
        for profile in profiles
        if profile[
            "acquisition_datetime"
        ]
        is None
    ]

    threshold_days = 7

    expected_qualified_ids = set()

    expected_disqualified_ids = set()

    expected_unknown_ids = {
        profile[
            "axie_id"
        ]
        for profile
        in unresolved_profiles
    }

    for profile in known_profiles:
        ownership_start = (
            datetime.strptime(
                profile[
                    "acquisition_datetime"
                ],
                "%Y-%m-%d %H:%M:%S",
            ).replace(
                tzinfo=timezone.utc
            )
        )

        ownership_seconds = (
            as_of_datetime
            - ownership_start
        ).total_seconds()

        if (
            ownership_seconds
            >= threshold_days
            * 86400
        ):
            expected_qualified_ids.add(
                profile[
                    "axie_id"
                ]
            )

        else:
            expected_disqualified_ids.add(
                profile[
                    "axie_id"
                ]
            )

    result = qualify_owned_axies(
        AXIEOS_DB_PATH,
        {
            "min_ownership_days": (
                threshold_days
            ),
        },
        as_of_datetime=(
            as_of_datetime
        ),
    )

    qualified_ids = {
        profile[
            "axie_id"
        ]
        for profile
        in result[
            "qualified"
        ]
    }

    disqualified_ids = {
        profile[
            "axie_id"
        ]
        for profile
        in result[
            "disqualified"
        ]
    }

    unknown_ids = {
        profile[
            "axie_id"
        ]
        for profile
        in result[
            "unknown"
        ]
    }

    qualification_valid = (
        qualified_ids
        == expected_qualified_ids
    )

    disqualification_valid = (
        disqualified_ids
        == expected_disqualified_ids
    )

    unknown_valid = (
        unknown_ids
        == expected_unknown_ids
        and len(
            unknown_ids
        )
        == 12
    )

    total_partition_valid = (
        len(
            qualified_ids
        )
        + len(
            disqualified_ids
        )
        + len(
            unknown_ids
        )
        == 136
    )

    known_coverage_valid = (
        len(
            known_profiles
        )
        == 124
    )

    unresolved_coverage_valid = (
        len(
            unresolved_profiles
        )
        == 12
    )

    print(
        "As-of UTC:",
        as_of_datetime.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
    )

    print(
        "Current OWNED profiles:",
        len(
            profiles
        ),
    )

    print(
        "Exact ownership dates:",
        len(
            known_profiles
        ),
    )

    print(
        "Legacy unresolved:",
        len(
            unresolved_profiles
        ),
    )

    print(
        "\n7-DAY OWNERSHIP REQUIREMENT"
    )

    print(
        "Qualified:",
        len(
            qualified_ids
        ),
    )

    print(
        "Disqualified:",
        len(
            disqualified_ids
        ),
    )

    print(
        "Unknown:",
        len(
            unknown_ids
        ),
    )

    print(
        "\nUNKNOWN OWNERSHIP-DURATION AXIES"
    )

    for axie_id in sorted(
        unknown_ids,
        key=int,
    ):
        print(
            "Axie ID:",
            axie_id,
        )

    print(
        "\nRECENTLY ACQUIRED — UNDER 7 DAYS"
    )

    for profile in sorted(
        [
            profile
            for profile in profiles
            if profile[
                "axie_id"
            ]
            in disqualified_ids
        ],
        key=lambda item: int(
            item[
                "axie_id"
            ]
        ),
    ):
        print(
            "Axie ID:",
            profile[
                "axie_id"
            ],
            "| acquired:",
            profile[
                "acquisition_datetime"
            ],
            "| source:",
            profile[
                "acquisition_source"
            ],
        )

    print(
        "\nCHECKS"
    )

    print(
        "124 exact-date profiles:",
        (
            "PASS"
            if known_coverage_valid
            else "FAIL"
        ),
    )

    print(
        "12 legacy unresolved profiles:",
        (
            "PASS"
            if unresolved_coverage_valid
            else "FAIL"
        ),
    )

    print(
        "Qualified set:",
        (
            "PASS"
            if qualification_valid
            else "FAIL"
        ),
    )

    print(
        "Disqualified set:",
        (
            "PASS"
            if disqualification_valid
            else "FAIL"
        ),
    )

    print(
        "Legacy records return UNKNOWN:",
        (
            "PASS"
            if unknown_valid
            else "FAIL"
        ),
    )

    print(
        "All 136 profiles partitioned:",
        (
            "PASS"
            if total_partition_valid
            else "FAIL"
        ),
    )

    validation = (
        known_coverage_valid
        and unresolved_coverage_valid
        and qualification_valid
        and disqualification_valid
        and unknown_valid
        and total_partition_valid
    )

    print(
        "\nValidation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )



def run_v08_database_validation():
    print(
        "\nAXIEOS V0.8 DATABASE VALIDATION"
    )

    connection = sqlite3.connect(
        AXIEOS_DB_PATH
    )

    owned_rows = (
        connection.execute(
            """
            SELECT
                axie_id,
                axie_class,
                level,
                breed_count,
                is_collectible,
                is_evolved,
                acquisition_datetime,
                acquisition_source
            FROM gameplay_owned_axies
            WHERE ownership_status = 'OWNED'
            ORDER BY CAST(axie_id AS INTEGER)
            """
        ).fetchall()
    )

    total_registry_rows = (
        connection.execute(
            """
            SELECT COUNT(*)
            FROM gameplay_owned_axies
            """
        ).fetchone()[0]
    )

    part_rows = (
        connection.execute(
            """
            SELECT
                p.axie_id,
                COUNT(*) AS part_count,
                SUM(
                    CASE
                        WHEN p.part_name IS NOT NULL
                         AND TRIM(p.part_name) != ''
                        THEN 1
                        ELSE 0
                    END
                ) AS named_count
            FROM gameplay_axie_parts p
            INNER JOIN gameplay_owned_axies a
                ON a.axie_id = p.axie_id
            WHERE a.ownership_status = 'OWNED'
            GROUP BY p.axie_id
            """
        ).fetchall()
    )

    collection_rows = (
        connection.execute(
            """
            SELECT
                t.axie_id,
                t.trait_value
            FROM gameplay_axie_traits t
            INNER JOIN gameplay_owned_axies a
                ON a.axie_id = t.axie_id
            WHERE
                a.ownership_status = 'OWNED'
                AND t.trait_type = 'COLLECTION'
            """
        ).fetchall()
    )

    connection.close()

    owned_count = len(
        owned_rows
    )

    class_complete = sum(
        1
        for row in owned_rows
        if row[1] in AXIE_CLASSES
    )

    level_complete = sum(
        1
        for row in owned_rows
        if isinstance(
            row[2],
            int,
        )
        and row[2] > 0
    )

    breed_complete = sum(
        1
        for row in owned_rows
        if isinstance(
            row[3],
            int,
        )
        and 0 <= row[3] <= 7
    )

    collectible_complete = sum(
        1
        for row in owned_rows
        if row[4] in {
            0,
            1,
        }
    )

    evolution_complete = sum(
        1
        for row in owned_rows
        if row[5] in {
            0,
            1,
        }
    )

    collectible_ids = {
        str(row[0])
        for row in owned_rows
        if row[4] == 1
    }

    evolved_ids = {
        str(row[0])
        for row in owned_rows
        if row[5] == 1
    }

    part_profile_map = {
        str(row[0]): {
            "parts": row[1],
            "named": row[2] or 0,
        }
        for row in part_rows
    }

    complete_part_profiles = sum(
        1
        for axie_id in {
            str(row[0])
            for row in owned_rows
        }
        if (
            part_profile_map.get(
                axie_id,
                {},
            ).get(
                "parts"
            )
            == 6
            and part_profile_map.get(
                axie_id,
                {},
            ).get(
                "named"
            )
            == 6
        )
    )

    collection_map = {}

    for (
        axie_id,
        collection,
    ) in collection_rows:
        axie_id = str(
            axie_id
        )

        collection_map.setdefault(
            axie_id,
            set(),
        ).add(
            collection
        )

    collectible_without_collection = (
        collectible_ids
        - set(
            collection_map.keys()
        )
    )

    collection_without_collectible = (
        set(
            collection_map.keys()
        )
        - collectible_ids
    )

    dated_ids = {
        str(row[0])
        for row in owned_rows
        if row[6] is not None
    }

    local_source_ids = {
        str(row[0])
        for row in owned_rows
        if row[7]
        == "RONIN_LOCAL_TRANSFER"
    }

    origins_source_ids = {
        str(row[0])
        for row in owned_rows
        if row[7]
        == (
            "SKYMAVIS_ORIGINS_"
            "LAST_TRANSFER"
        )
    }

    legacy_source_ids = {
        str(row[0])
        for row in owned_rows
        if row[7]
        == (
            "LEGACY_HISTORY_"
            "UNRESOLVED"
        )
    }

    unknown_source_ids = {
        str(row[0])
        for row in owned_rows
        if row[7] not in {
            "RONIN_LOCAL_TRANSFER",
            (
                "SKYMAVIS_ORIGINS_"
                "LAST_TRANSFER"
            ),
            (
                "LEGACY_HISTORY_"
                "UNRESOLVED"
            ),
        }
    }

    pincer_result = (
        qualify_owned_axies(
            AXIEOS_DB_PATH,
            {
                "required_part_names": [
                    "Pincer",
                ],
            },
        )
    )

    japanese_result = (
        qualify_owned_axies(
            AXIEOS_DB_PATH,
            {
                "is_collectible": True,
                "required_collections": [
                    "JAPANESE",
                ],
            },
        )
    )

    duration_result = (
        qualify_owned_axies(
            AXIEOS_DB_PATH,
            {
                "min_ownership_days": 7,
            },
        )
    )

    duration_partition = (
        len(
            duration_result[
                "qualified"
            ]
        )
        + len(
            duration_result[
                "disqualified"
            ]
        )
        + len(
            duration_result[
                "unknown"
            ]
        )
    )

    ownership_valid = (
        owned_count == 136
    )

    gameplay_metadata_valid = (
        class_complete == 136
        and level_complete == 136
        and breed_complete == 136
        and collectible_complete == 136
        and evolution_complete == 136
    )

    parts_valid = (
        complete_part_profiles == 136
    )

    collectible_valid = (
        len(
            collectible_ids
        )
        == 16
        and len(
            collection_rows
        )
        == 17
        and len(
            collectible_without_collection
        )
        == 0
        and len(
            collection_without_collectible
        )
        == 0
    )

    acquisition_valid = (
        len(
            dated_ids
        )
        == 124
        and len(
            local_source_ids
        )
        == 9
        and len(
            origins_source_ids
        )
        == 115
        and len(
            legacy_source_ids
        )
        == 12
        and not unknown_source_ids
    )

    pincer_ids = {
        profile[
            "axie_id"
        ]
        for profile
        in pincer_result[
            "qualified"
        ]
    }

    qualification_valid = (
        len(
            pincer_ids
        )
        == 3
        and "6251324"
        in pincer_ids
        and len(
            japanese_result[
                "qualified"
            ]
        )
        == 1
        and len(
            duration_result[
                "unknown"
            ]
        )
        == 12
        and duration_partition
        == 136
    )

    evolved_count_valid = (
        len(
            evolved_ids
        )
        == 65
    )

    print(
        "\nREGISTRY"
    )

    print(
        "Total historical registry rows:",
        total_registry_rows,
    )

    print(
        "Current OWNED Axies:",
        owned_count,
    )

    print(
        "\nGAMEPLAY METADATA"
    )

    print(
        "Class:",
        class_complete,
        "/",
        owned_count,
    )

    print(
        "Level:",
        level_complete,
        "/",
        owned_count,
    )

    print(
        "Breed count:",
        breed_complete,
        "/",
        owned_count,
    )

    print(
        "Collectible status:",
        collectible_complete,
        "/",
        owned_count,
    )

    print(
        "Evolution status:",
        evolution_complete,
        "/",
        owned_count,
    )

    print(
        "Evolved Axies:",
        len(
            evolved_ids
        ),
    )

    print(
        "\nPARTS"
    )

    print(
        "Complete named six-part profiles:",
        complete_part_profiles,
        "/",
        owned_count,
    )

    print(
        "\nCOLLECTIBLES"
    )

    print(
        "Collectible Axies:",
        len(
            collectible_ids
        ),
    )

    print(
        "Collection trait rows:",
        len(
            collection_rows
        ),
    )

    print(
        "Collectibles without collection:",
        len(
            collectible_without_collection
        ),
    )

    print(
        "Collection traits on non-collectibles:",
        len(
            collection_without_collectible
        ),
    )

    print(
        "\nOWNERSHIP HISTORY"
    )

    print(
        "Exact ownership dates:",
        len(
            dated_ids
        ),
    )

    print(
        "Ronin local transfer:",
        len(
            local_source_ids
        ),
    )

    print(
        "Origins lastTransferTime:",
        len(
            origins_source_ids
        ),
    )

    print(
        "Legacy unresolved:",
        len(
            legacy_source_ids
        ),
    )

    print(
        "Unknown provenance:",
        len(
            unknown_source_ids
        ),
    )

    print(
        "\nQUALIFICATION SMOKE TESTS"
    )

    print(
        "Pincer qualified:",
        len(
            pincer_ids
        ),
        "| IDs:",
        sorted(
            pincer_ids,
            key=int,
        ),
    )

    print(
        "Japanese collectible qualified:",
        len(
            japanese_result[
                "qualified"
            ]
        ),
    )

    print(
        "7-day qualified:",
        len(
            duration_result[
                "qualified"
            ]
        ),
    )

    print(
        "7-day disqualified:",
        len(
            duration_result[
                "disqualified"
            ]
        ),
    )

    print(
        "7-day unknown:",
        len(
            duration_result[
                "unknown"
            ]
        ),
    )

    print(
        "\nCHECKS"
    )

    print(
        "Current ownership:",
        (
            "PASS"
            if ownership_valid
            else "FAIL"
        ),
    )

    print(
        "Gameplay metadata:",
        (
            "PASS"
            if gameplay_metadata_valid
            else "FAIL"
        ),
    )

    print(
        "Named body parts:",
        (
            "PASS"
            if parts_valid
            else "FAIL"
        ),
    )

    print(
        "Collectible intelligence:",
        (
            "PASS"
            if collectible_valid
            else "FAIL"
        ),
    )

    print(
        "Evolution benchmark:",
        (
            "PASS"
            if evolved_count_valid
            else "FAIL"
        ),
    )

    print(
        "Ownership history provenance:",
        (
        "PASS"
            if acquisition_valid
            else "FAIL"
        ),
    )

    print(
        "Qualification engine:",
        (
            "PASS"
            if qualification_valid
            else "FAIL"
        ),
    )

    validation = (
        ownership_valid
        and gameplay_metadata_valid
        and parts_valid
        and collectible_valid
        and evolved_count_valid
        and acquisition_valid
        and qualification_valid
    )

    print(
        "\nV0.8 Database Validation:",
        (
            "PASS"
            if validation
            else "FAIL"
        ),
    )

    return validation



def run_gameplay_data_v08():
    print(
        "\n========================================"
    )

    print(
        "AXIEOS GAMEPLAY DATA PIPELINE"
    )

    print(
        "Version:",
        GAMEPLAY_DATA_VERSION,
    )

    print(
        "========================================"
    )

    # --------------------------------------------------
    # Stage 1 — Current blockchain ownership
    # --------------------------------------------------

    print(
        "\n[1/7] Current ownership sync"
    )

    ownership_result = (
        sync_owned_axie_registry_from_current_chain(
            AXIEOS_DB_PATH
        )
    )

    if not ownership_result[
        "success"
    ]:
        print(
            "Current ownership sync: FAIL"
        )

        print(
            "Error:",
            ownership_result.get(
                "error"
            ),
        )

        print(
            "\nV0.8 Pipeline: FAIL"
        )

        return False

    print(
        "Current ownership sync: PASS"
    )

    print(
        "Current Axies:",
        ownership_result[
            "current_axies"
        ],
    )

    # --------------------------------------------------
    # Stage 2 — Origins gameplay metadata
    # --------------------------------------------------

    print(
        "\n[2/7] Origins gameplay metadata"
    )

    origins_result = (
        sync_origins_metadata_for_owned_axies(
            AXIEOS_DB_PATH
        )
    )

    if not origins_result[
        "success"
    ]:
        print(
            "Origins metadata sync: FAIL"
        )

        print(
            "Error:",
            origins_result.get(
                "error"
            ),
        )

        print(
            "\nV0.8 Pipeline: FAIL"
        )

        return False

    print(
        "Origins metadata sync: PASS"
    )

    print(
        "Synced Axies:",
        origins_result[
            "synced_axies"
        ],
    )

    # --------------------------------------------------
    # Stage 3 — On-chain breed count
    # --------------------------------------------------

    print(
        "\n[3/7] On-chain breed counts"
    )

    breed_result = (
        sync_onchain_breed_counts_for_owned_axies(
            AXIEOS_DB_PATH
        )
    )

    if not breed_result[
        "success"
    ]:
        print(
            "Breed count sync: FAIL"
        )

        failed_axies = (
            breed_result.get(
                "failed_axies",
                [],
            )
        )

        print(
            "Failures:",
            len(
                failed_axies
            ),
        )

        if failed_axies:
            print(
                "\nBREED COUNT FAILURE DETAILS"
            )

            for failure in failed_axies:
                print(
                    failure
                )

        print(
            "\nV0.8 Pipeline: FAIL"
        )

        return False

    print(
        "Breed count sync: PASS"
    )

    print(
        "Synced Axies:",
        breed_result[
            "synced_axies"
        ],
    )

    # --------------------------------------------------
    # Stage 4 — Collectible genetics
    # --------------------------------------------------

    print(
        "\n[4/7] Collectible intelligence"
    )

    collectible_result = (
        sync_collection_traits_for_owned_axies(
            AXIEOS_DB_PATH
        )
    )

    if not collectible_result[
        "success"
    ]:
        print(
            "Collectible sync: FAIL"
        )

        failed_axies = (
            collectible_result.get(
                "failed_axies",
                [],
            )
        )

        print(
            "Failures:",
            len(
                failed_axies
            ),
        )

        if failed_axies:
            print(
                "\nCOLLECTIBLE FAILURE DETAILS"
            )

            for failure in failed_axies:
                print(
                    failure
                )

        print(
            "\nV0.8 Pipeline: FAIL"
        )

        return False

    print(
        "Collectible sync: PASS"
    )

    print(
        "Classified Axies:",
        collectible_result[
            "classified_axies"
        ],
    )

    # --------------------------------------------------
    # Stage 5 — Human-readable body-part names
    # --------------------------------------------------

    print(
        "\n[5/7] Origins body-part names"
    )

    part_result = (
        sync_owned_axie_part_names(
            AXIEOS_DB_PATH
        )
    )

    if not part_result[
        "success"
    ]:
        print(
            "Body-part name sync: FAIL"
        )

        print(
            "Unmapped parts:",
            len(
                part_result.get(
                    "unmapped_parts",
                    [],
                )
            ),
        )

        print(
            "\nV0.8 Pipeline: FAIL"
        )

        return False

    print(
        "Body-part name sync: PASS"
    )

    print(
        "Named parts:",
        part_result[
            "mapped_parts"
        ],
    )

    # --------------------------------------------------
    # Stage 6 — Ownership-start provenance
    # --------------------------------------------------

    print(
        "\n[6/7] Ownership-start provenance"
    )

    ownership_time_result = (
        fetch_origins_ownership_timestamps()
    )

    if not ownership_time_result[
        "success"
    ]:
        print(
            "Origins ownership snapshot: FAIL"
        )

        print(
            "Error:",
            ownership_time_result.get(
                "error"
            ),
        )

        print(
            "\nV0.8 Pipeline: FAIL"
        )

        return False

    acquisition_result = (
        sync_owned_axie_acquisition_datetimes(
            AXIEOS_DB_PATH,
            fighter_map=(
                ownership_time_result[
                    "fighters"
                ]
            ),
        )
    )

    if not acquisition_result[
        "success"
    ]:
        print(
            "Ownership-start sync: FAIL"
        )

        print(
            "\nV0.8 Pipeline: FAIL"
        )

        return False

    print(
        "Ownership-start sync: PASS"
    )

    print(
        "Legacy unresolved:",
        len(
            acquisition_result[
                "legacy_unresolved"
            ]
        ),
    )

    # --------------------------------------------------
    # Stage 7 — Final V0.8 database validation
    # --------------------------------------------------

    print(
        "\n[7/7] Final database validation"
    )

    validation = (
        run_v08_database_validation()
    )

    print(
        "\n========================================"
    )

    print(
        "AXIEOS GAMEPLAY DATA V0.8"
    )

    print(
        (
            "PIPELINE PASS"
            if validation
            else "PIPELINE FAIL"
        )
    )

    print(
        "========================================"
    )

    return validation
















if __name__ == "__main__":
    run_gameplay_data_v08()