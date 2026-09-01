from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import sqlite3


MARKETPLACE_INVENTORY_MODEL_VERSION = "0.10"

POSITION_OPEN_OWNED = "OPEN_OWNED"
POSITION_CLOSED_SOLD = "CLOSED_SOLD"
POSITION_CLOSED_RELEASED = "CLOSED_RELEASED"
POSITION_REVIEW_OWNERSHIP_UNRESOLVED = (
    "REVIEW_OWNERSHIP_UNRESOLVED"
)
POSITION_REVIEW_REPEAT_ACQUISITION = (
    "REVIEW_REPEAT_ACQUISITION"
)

QUALITY_READY = "READY"
QUALITY_REVIEW = "REVIEW"


LISTING_STATUS_RECORDED_UNVERIFIED = (
    "LISTING_RECORDED_UNVERIFIED"
)
LISTING_STATUS_UNKNOWN = "UNKNOWN"
LISTING_STATUS_CLOSED_POSITION = (
    "CLOSED_POSITION"
)


SALE_STATUS_CONFIRMED = "SOLD_CONFIRMED"
SALE_STATUS_RECORDED_UNVERIFIED = (
    "SALE_RECORDED_UNVERIFIED"
)
SALE_STATUS_NO_EVIDENCE = (
    "NO_SALE_EVIDENCE"
)
SALE_STATUS_NOT_APPLICABLE_RELEASED = (
    "NOT_APPLICABLE_RELEASED"
)
SALE_STATUS_REVIEW_MULTIPLE = (
    "REVIEW_MULTIPLE_SALES"
)


REALIZED_STATUS_READY = "REALIZED_READY"
REALIZED_STATUS_REVIEW = "REALIZED_REVIEW"
REALIZED_STATUS_NOT_APPLICABLE = (
    "REALIZED_NOT_APPLICABLE"
)
REALIZED_STATUS_UNAVAILABLE = (
    "REALIZED_UNAVAILABLE"
)

UNREALIZED_STATUS_UNAVAILABLE_NO_MARKET_PRICE = (
    "UNREALIZED_UNAVAILABLE_NO_MARKET_PRICE"
)
UNREALIZED_STATUS_NOT_APPLICABLE = (
    "UNREALIZED_NOT_APPLICABLE"
)

HOLDING_STATUS_READY = "HOLDING_READY"
HOLDING_STATUS_REVIEW = "HOLDING_REVIEW"
HOLDING_STATUS_UNAVAILABLE = "HOLDING_UNAVAILABLE"

ASSUMED_MARKETPLACE_FEE_RATE = Decimal(
    "0.0425"
)

RESALE_STATUS_READY = "RESALE_READY"
RESALE_STATUS_REVIEW = "RESALE_REVIEW"
RESALE_STATUS_UNAVAILABLE_NO_COST = (
    "RESALE_UNAVAILABLE_NO_COST"
)
RESALE_STATUS_NOT_APPLICABLE = (
    "RESALE_NOT_APPLICABLE"
)

RELEASE_ANALYSIS_READY = (
    "RELEASE_ANALYSIS_READY"
)

RELEASE_ANALYSIS_REVIEW_PROTECTED = (
    "RELEASE_REVIEW_PROTECTED_ATTRIBUTE"
)

RELEASE_ANALYSIS_REVIEW_NO_COST = (
    "RELEASE_REVIEW_NO_COST_BASIS"
)

RELEASE_ANALYSIS_REVIEW_MISSING_INPUTS = (
    "RELEASE_REVIEW_MISSING_INPUTS"
)

RELEASE_ANALYSIS_NOT_APPLICABLE = (
    "RELEASE_NOT_APPLICABLE"
)

RELEASE_ECONOMICS_UNAVAILABLE = (
    "RELEASE_ECONOMICS_UNAVAILABLE_NO_RECOVERY_MODEL"
)

RELEASE_ECONOMICS_NOT_APPLICABLE = (
    "RELEASE_ECONOMICS_NOT_APPLICABLE"
)

MARKETPLACE_STRATEGY_HOLD_PROTECTED = (
    "STRATEGY_HOLD_PROTECTED"
)

MARKETPLACE_STRATEGY_REVIEW_EXIT_OPTIONS = (
    "STRATEGY_REVIEW_EXIT_OPTIONS"
)

MARKETPLACE_STRATEGY_HOLD_INSUFFICIENT_DATA = (
    "STRATEGY_HOLD_INSUFFICIENT_DATA"
)

MARKETPLACE_STRATEGY_NOT_APPLICABLE = (
    "STRATEGY_NOT_APPLICABLE"
)

MARKETPLACE_ACTION_HOLD = "HOLD"
MARKETPLACE_ACTION_REVIEW = "REVIEW"
MARKETPLACE_ACTION_NONE = "NONE"


DEFAULT_DB_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "blockchain"
    / "database"
    / "axieos.db"
)


def connect_inventory_database(
    db_path=DEFAULT_DB_PATH,
):
    connection = sqlite3.connect(
        str(db_path)
    )
    connection.row_factory = sqlite3.Row
    return connection


def load_canonical_axie_ids(
    connection,
):
    rows = connection.execute(
        """
        SELECT asset_id
        FROM (
            SELECT
                axie_id AS asset_id
            FROM gameplay_owned_axies
            WHERE axie_id IS NOT NULL

            UNION

            SELECT
                asset_token_id AS asset_id
            FROM blockchain_accounting_records
            WHERE asset_name = 'Axie'
              AND asset_token_id IS NOT NULL

            UNION

            SELECT
                asset_id
            FROM marketplace_events
            WHERE asset_type = 'Axie'
              AND asset_id IS NOT NULL
        )
        ORDER BY
            CAST(asset_id AS INTEGER),
            asset_id
        """
    ).fetchall()

    return [
        row["asset_id"]
        for row in rows
    ]



def load_marketplace_axie_events(
    connection,
    asset_id,
):
    return connection.execute(
        """
        SELECT
            id,
            event_datetime,
            event_type,
            amount,
            currency,
            notes
        FROM marketplace_events
        WHERE asset_type = 'Axie'
          AND asset_id = ?
        ORDER BY event_datetime, id
        """,
        (asset_id,),
    ).fetchall()


def load_accounting_axie_events(
    connection,
    asset_id,
):
    return connection.execute(
        """
        SELECT
            txhash,
            datetime,
            event_type,
            classification,
            payment_asset,
            gross_amount,
            marketplace_fee,
            net_amount,
            cost_basis,
            realized_pl,
            accounting_status
        FROM blockchain_accounting_records
        WHERE asset_name = 'Axie'
          AND asset_token_id = ?
        ORDER BY datetime, txhash
        """,
        (asset_id,),
    ).fetchall()


def load_gameplay_axie_record(
    connection,
    asset_id,
):
    return connection.execute(
        """
        SELECT
            axie_id,
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
            acquisition_source
        FROM gameplay_owned_axies
        WHERE axie_id = ?
        """,
        (asset_id,),
    ).fetchone()



def resolve_ownership_start_evidence(
    marketplace_events,
    accounting_events,
    gameplay_record,
):
    accounting_purchases = (
        find_accounting_events(
            accounting_events,
            "ASSET_PURCHASE",
        )
    )

    accounting_transfers = (
        find_accounting_events(
            accounting_events,
            "TRANSFER_IN",
        )
    )

    marketplace_buys = [
        event
        for event in marketplace_events
        if event["event_type"] == "buy"
    ]

    if len(accounting_purchases) == 1:
        purchase = accounting_purchases[0]

        return {
            "ownership_start_datetime": (
                purchase["datetime"]
            ),
            "ownership_start_source": (
                "ACCOUNTING_ASSET_PURCHASE"
            ),
            "ownership_start_quality": (
                QUALITY_READY
            ),
        }

    if gameplay_record is not None:
        ownership_datetime = (
            gameplay_record[
                "acquisition_datetime"
            ]
        )

        ownership_source = (
            gameplay_record[
                "acquisition_source"
            ]
            or "GAMEPLAY_OWNERSHIP_HISTORY"
        )

        if ownership_datetime is not None:
            return {
                "ownership_start_datetime": (
                    ownership_datetime
                ),
                "ownership_start_source": (
                    ownership_source
                ),
                "ownership_start_quality": (
                    QUALITY_READY
                ),
            }

    if len(accounting_transfers) == 1:
        transfer = accounting_transfers[0]

        return {
            "ownership_start_datetime": (
                transfer["datetime"]
            ),
            "ownership_start_source": (
                "ACCOUNTING_TRANSFER_IN"
            ),
            "ownership_start_quality": (
                QUALITY_READY
            ),
        }

    if marketplace_buys:
        buy = marketplace_buys[0]

        return {
            "ownership_start_datetime": (
                buy["event_datetime"]
            ),
            "ownership_start_source": (
                "LEGACY_MARKETPLACE_BUY"
            ),
            "ownership_start_quality": (
                QUALITY_REVIEW
            ),
        }

    return {
        "ownership_start_datetime": None,
        "ownership_start_source": "UNRESOLVED",
        "ownership_start_quality": QUALITY_REVIEW,
    }



def count_marketplace_event(
    events,
    event_type,
):
    return sum(
        1
        for event in events
        if event["event_type"] == event_type
    )


def count_accounting_event(
    events,
    event_type,
):
    return sum(
        1
        for event in events
        if event["event_type"] == event_type
    )


def find_accounting_events(
    events,
    event_type,
):
    return [
        event
        for event in events
        if event["event_type"] == event_type
    ]


def has_ready_accounting_event(
    events,
    event_type,
):
    return any(
        event["event_type"] == event_type
        and event["accounting_status"] == "READY"
        for event in events
    )



def resolve_acquisition_evidence(
    marketplace_events,
    accounting_events,
):
    accounting_purchases = (
        find_accounting_events(
            accounting_events,
            "ASSET_PURCHASE",
        )
    )

    marketplace_buys = [
        event
        for event in marketplace_events
        if event["event_type"] == "buy"
    ]

    if len(accounting_purchases) == 1:
        purchase = accounting_purchases[0]

        payment_asset = (
            purchase["payment_asset"]
        )

        if (
            payment_asset
            == "Ronin Wrapped Ether"
        ):
            payment_asset = "WETH"

        quality = (
            QUALITY_READY
            if (
                purchase[
                    "accounting_status"
                ] == "READY"
                and purchase[
                    "gross_amount"
                ] is not None
            )
            else QUALITY_REVIEW
        )

        return {
            "acquisition_txhash": (
                purchase["txhash"]
            ),
            "acquisition_datetime": (
                purchase["datetime"]
            ),
            "acquisition_cost": (
                purchase["gross_amount"]
            ),
            "acquisition_currency": (
                payment_asset
            ),
            "acquisition_source": (
                "ACCOUNTING_ASSET_PURCHASE"
            ),
            "acquisition_quality": quality,
        }

    if len(accounting_purchases) > 1:
        return {
            "acquisition_txhash": None,
            "acquisition_datetime": None,
            "acquisition_cost": None,
            "acquisition_currency": None,
            "acquisition_source": (
                "MULTIPLE_ACCOUNTING_PURCHASES"
            ),
            "acquisition_quality": QUALITY_REVIEW,
        }

    if marketplace_buys:
        buy = marketplace_buys[0]

        return {
            "acquisition_txhash": None,
            "acquisition_datetime": (
                buy["event_datetime"]
            ),
            "acquisition_cost": (
                buy["amount"]
            ),
            "acquisition_currency": (
                buy["currency"]
            ),
            "acquisition_source": (
                "LEGACY_MARKETPLACE_BUY"
            ),
            "acquisition_quality": QUALITY_REVIEW,
        }

    return {
        "acquisition_txhash": None,
        "acquisition_datetime": None,
        "acquisition_cost": None,
        "acquisition_currency": None,
        "acquisition_source": "UNRESOLVED",
        "acquisition_quality": QUALITY_REVIEW,
    }



def resolve_listing_evidence(
    marketplace_events,
    position_status,
):
    listing_events = [
        event
        for event in marketplace_events
        if event["event_type"] == "list"
    ]

    if not listing_events:
        return {
            "listing_status": (
                LISTING_STATUS_CLOSED_POSITION
                if position_status
                in {
                    POSITION_CLOSED_SOLD,
                    POSITION_CLOSED_RELEASED,
                }
                else LISTING_STATUS_UNKNOWN
            ),
            "last_listing_datetime": None,
            "last_listing_price": None,
            "last_listing_currency": None,
            "listing_source": "NONE",
            "listing_quality": QUALITY_REVIEW,
        }

    latest_listing = listing_events[-1]

    if position_status in {
        POSITION_CLOSED_SOLD,
        POSITION_CLOSED_RELEASED,
    }:
        listing_status = (
            LISTING_STATUS_CLOSED_POSITION
        )
    else:
        listing_status = (
            LISTING_STATUS_RECORDED_UNVERIFIED
        )

    return {
        "listing_status": listing_status,
        "last_listing_datetime": (
            latest_listing[
                "event_datetime"
            ]
        ),
        "last_listing_price": (
            latest_listing["amount"]
        ),
        "last_listing_currency": (
            latest_listing["currency"]
        ),
        "listing_source": (
            "LEGACY_MARKETPLACE_LIST"
        ),
        "listing_quality": QUALITY_REVIEW,
    }



def resolve_sale_evidence(
    marketplace_events,
    accounting_events,
    position_status,
):
    accounting_sales = (
        find_accounting_events(
            accounting_events,
            "ASSET_SALE",
        )
    )

    marketplace_sales = [
        event
        for event in marketplace_events
        if event["event_type"] == "sale"
    ]

    if len(accounting_sales) == 1:
        sale = accounting_sales[0]

        return {
            "sale_status": (
                SALE_STATUS_CONFIRMED
            ),
            "sale_datetime": (
                sale["datetime"]
            ),
            "sale_txhash": (
                sale["txhash"]
            ),
            "sale_source": (
                "ACCOUNTING_ASSET_SALE"
            ),
            "sale_quality": QUALITY_READY,
        }

    if len(accounting_sales) > 1:
        sale = accounting_sales[-1]

        return {
            "sale_status": (
                SALE_STATUS_REVIEW_MULTIPLE
            ),
            "sale_datetime": (
                sale["datetime"]
            ),
            "sale_txhash": (
                sale["txhash"]
            ),
            "sale_source": (
                "MULTIPLE_ACCOUNTING_SALES"
            ),
            "sale_quality": QUALITY_REVIEW,
        }

    if marketplace_sales:
        sale = marketplace_sales[-1]

        return {
            "sale_status": (
                SALE_STATUS_RECORDED_UNVERIFIED
            ),
            "sale_datetime": (
                sale["event_datetime"]
            ),
            "sale_txhash": None,
            "sale_source": (
                "LEGACY_MARKETPLACE_SALE"
            ),
            "sale_quality": QUALITY_REVIEW,
        }

    if (
        position_status
        == POSITION_CLOSED_RELEASED
    ):
        return {
            "sale_status": (
                SALE_STATUS_NOT_APPLICABLE_RELEASED
            ),
            "sale_datetime": None,
            "sale_txhash": None,
            "sale_source": "NONE",
            "sale_quality": QUALITY_READY,
        }

    return {
        "sale_status": (
            SALE_STATUS_NO_EVIDENCE
        ),
        "sale_datetime": None,
        "sale_txhash": None,
        "sale_source": "NONE",
        "sale_quality": QUALITY_REVIEW,
    }



def decimal_or_none(
    value,
):
    if value is None:
        return None

    try:
        return Decimal(str(value))
    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):
        return None


def resolve_realized_economics(
    accounting_events,
    position_status,
):
    if (
        position_status
        != POSITION_CLOSED_SOLD
    ):
        return {
            "realized_status": (
                REALIZED_STATUS_NOT_APPLICABLE
            ),
            "gross_sale": None,
            "marketplace_fee": None,
            "net_proceeds": None,
            "cost_basis": None,
            "realized_pl": None,
            "realized_roi": None,
            "realized_source": "NONE",
            "realized_quality": QUALITY_READY,
        }

    accounting_sales = (
        find_accounting_events(
            accounting_events,
            "ASSET_SALE",
        )
    )

    if len(accounting_sales) != 1:
        return {
            "realized_status": (
                REALIZED_STATUS_UNAVAILABLE
            ),
            "gross_sale": None,
            "marketplace_fee": None,
            "net_proceeds": None,
            "cost_basis": None,
            "realized_pl": None,
            "realized_roi": None,
            "realized_source": (
                "ACCOUNTING_SALE_UNRESOLVED"
            ),
            "realized_quality": QUALITY_REVIEW,
        }

    sale = accounting_sales[0]

    gross_sale = decimal_or_none(
        sale["gross_amount"]
    )
    marketplace_fee = decimal_or_none(
        sale["marketplace_fee"]
    )
    net_proceeds = decimal_or_none(
        sale["net_amount"]
    )
    cost_basis = decimal_or_none(
        sale["cost_basis"]
    )
    realized_pl = decimal_or_none(
        sale["realized_pl"]
    )

    realized_roi = None

    if (
        realized_pl is not None
        and cost_basis is not None
        and cost_basis != Decimal("0")
    ):
        realized_roi = (
            realized_pl
            / cost_basis
        )

    complete = all(
        value is not None
        for value in (
            gross_sale,
            marketplace_fee,
            net_proceeds,
            cost_basis,
            realized_pl,
            realized_roi,
        )
    )

    return {
        "realized_status": (
            REALIZED_STATUS_READY
            if complete
            else REALIZED_STATUS_REVIEW
        ),
        "gross_sale": gross_sale,
        "marketplace_fee": marketplace_fee,
        "net_proceeds": net_proceeds,
        "cost_basis": cost_basis,
        "realized_pl": realized_pl,
        "realized_roi": realized_roi,
        "realized_source": (
            "BLOCKCHAIN_ACCOUNTING_RECORD"
        ),
        "realized_quality": (
            QUALITY_READY
            if complete
            else QUALITY_REVIEW
        ),
    }



def resolve_unrealized_economics(
    position_status,
):
    if (
        position_status
        != POSITION_OPEN_OWNED
    ):
        return {
            "unrealized_status": (
                UNREALIZED_STATUS_NOT_APPLICABLE
            ),
            "current_market_value": None,
            "unrealized_pl": None,
            "unrealized_roi": None,
            "unrealized_source": "NONE",
            "unrealized_quality": QUALITY_READY,
        }

    return {
        "unrealized_status": (
            UNREALIZED_STATUS_UNAVAILABLE_NO_MARKET_PRICE
        ),
        "current_market_value": None,
        "unrealized_pl": None,
        "unrealized_roi": None,
        "unrealized_source": (
            "NO_LIVE_MARKET_PRICE_SOURCE"
        ),
        "unrealized_quality": QUALITY_REVIEW,
    }



def parse_canonical_datetime(
    value,
):
    if value is None:
        return None

    try:
        parsed = datetime.fromisoformat(
            str(value).replace(
                "Z",
                "+00:00",
            )
        )
    except ValueError:
        return None

    if parsed.tzinfo is not None:
        parsed = (
            parsed
            .astimezone(timezone.utc)
            .replace(tzinfo=None)
        )

    return parsed


def resolve_release_evidence(
    marketplace_events,
    accounting_events,
):
    accounting_burns = (
        find_accounting_events(
            accounting_events,
            "ASSET_BURN",
        )
    )

    if len(accounting_burns) == 1:
        burn = accounting_burns[0]

        return {
            "release_datetime": (
                burn["datetime"]
            ),
            "release_source": (
                "ACCOUNTING_ASSET_BURN"
            ),
            "release_quality": (
                QUALITY_READY
            ),
        }

    marketplace_releases = [
        event
        for event in marketplace_events
        if event["event_type"] == "release"
    ]

    if marketplace_releases:
        release = marketplace_releases[-1]

        return {
            "release_datetime": (
                release["event_datetime"]
            ),
            "release_source": (
                "LEGACY_MARKETPLACE_RELEASE"
            ),
            "release_quality": (
                QUALITY_REVIEW
            ),
        }

    return {
        "release_datetime": None,
        "release_source": "NONE",
        "release_quality": QUALITY_REVIEW,
    }


def resolve_holding_period(
    position_status,
    ownership_start,
    sale,
    release,
    as_of_datetime,
):
    start_datetime = parse_canonical_datetime(
        ownership_start[
            "ownership_start_datetime"
        ]
    )

    start_quality = ownership_start[
        "ownership_start_quality"
    ]

    if start_datetime is None:
        return {
            "holding_status": (
                HOLDING_STATUS_UNAVAILABLE
            ),
            "holding_start_datetime": None,
            "holding_end_datetime": None,
            "holding_seconds": None,
            "holding_days": None,
            "holding_quality": QUALITY_REVIEW,
        }

    if position_status == POSITION_OPEN_OWNED:
        end_datetime = as_of_datetime
        end_quality = QUALITY_READY

    elif position_status == POSITION_CLOSED_SOLD:
        end_datetime = parse_canonical_datetime(
            sale["sale_datetime"]
        )
        end_quality = sale["sale_quality"]

    elif (
        position_status
        == POSITION_CLOSED_RELEASED
    ):
        end_datetime = parse_canonical_datetime(
            release["release_datetime"]
        )
        end_quality = release[
            "release_quality"
        ]

    else:
        return {
            "holding_status": (
                HOLDING_STATUS_UNAVAILABLE
            ),
            "holding_start_datetime": (
                start_datetime
            ),
            "holding_end_datetime": None,
            "holding_seconds": None,
            "holding_days": None,
            "holding_quality": QUALITY_REVIEW,
        }

    if end_datetime is None:
        return {
            "holding_status": (
                HOLDING_STATUS_UNAVAILABLE
            ),
            "holding_start_datetime": (
                start_datetime
            ),
            "holding_end_datetime": None,
            "holding_seconds": None,
            "holding_days": None,
            "holding_quality": QUALITY_REVIEW,
        }

    if (
        start_quality != QUALITY_READY
        or end_quality != QUALITY_READY
    ):
        return {
            "holding_status": (
                HOLDING_STATUS_REVIEW
            ),
            "holding_start_datetime": (
                start_datetime
            ),
            "holding_end_datetime": (
                end_datetime
            ),
            "holding_seconds": None,
            "holding_days": None,
            "holding_quality": QUALITY_REVIEW,
        }

    holding_seconds = (
        end_datetime - start_datetime
    ).total_seconds()

    if holding_seconds < 0:
        return {
            "holding_status": (
                HOLDING_STATUS_REVIEW
            ),
            "holding_start_datetime": (
                start_datetime
            ),
            "holding_end_datetime": (
                end_datetime
            ),
            "holding_seconds": None,
            "holding_days": None,
            "holding_quality": QUALITY_REVIEW,
        }

    return {
        "holding_status": (
            HOLDING_STATUS_READY
        ),
        "holding_start_datetime": (
            start_datetime
        ),
        "holding_end_datetime": (
            end_datetime
        ),
        "holding_seconds": (
            holding_seconds
        ),
        "holding_days": (
            holding_seconds
            / 86400
        ),
        "holding_quality": QUALITY_READY,
    }



def resolve_resale_break_even(
    position_status,
    acquisition,
):
    if (
        position_status
        != POSITION_OPEN_OWNED
    ):
        return {
            "resale_status": (
                RESALE_STATUS_NOT_APPLICABLE
            ),
            "resale_fee_rate_assumption": (
                ASSUMED_MARKETPLACE_FEE_RATE
            ),
            "break_even_gross_price": None,
            "break_even_fee": None,
            "break_even_net_proceeds": None,
            "break_even_currency": None,
            "resale_source": "NONE",
            "resale_quality": QUALITY_READY,
        }

    acquisition_cost = decimal_or_none(
        acquisition[
            "acquisition_cost"
        ]
    )

    acquisition_currency = (
        acquisition[
            "acquisition_currency"
        ]
    )

    if acquisition_cost is None:
        return {
            "resale_status": (
                RESALE_STATUS_UNAVAILABLE_NO_COST
            ),
            "resale_fee_rate_assumption": (
                ASSUMED_MARKETPLACE_FEE_RATE
            ),
            "break_even_gross_price": None,
            "break_even_fee": None,
            "break_even_net_proceeds": None,
            "break_even_currency": None,
            "resale_source": (
                "NO_PROVEN_ACQUISITION_COST"
            ),
            "resale_quality": QUALITY_REVIEW,
        }

    net_fraction = (
        Decimal("1")
        - ASSUMED_MARKETPLACE_FEE_RATE
    )

    break_even_gross_price = (
        acquisition_cost
        / net_fraction
    )

    break_even_fee = (
        break_even_gross_price
        * ASSUMED_MARKETPLACE_FEE_RATE
    )

    break_even_net_proceeds = (
        break_even_gross_price
        - break_even_fee
    )

    quality = (
        QUALITY_READY
        if (
            acquisition[
                "acquisition_quality"
            ] == QUALITY_READY
        )
        else QUALITY_REVIEW
    )

    return {
        "resale_status": (
            RESALE_STATUS_READY
            if quality == QUALITY_READY
            else RESALE_STATUS_REVIEW
        ),
        "resale_fee_rate_assumption": (
            ASSUMED_MARKETPLACE_FEE_RATE
        ),
        "break_even_gross_price": (
            break_even_gross_price
        ),
        "break_even_fee": (
            break_even_fee
        ),
        "break_even_net_proceeds": (
            break_even_net_proceeds
        ),
        "break_even_currency": (
            acquisition_currency
        ),
        "resale_source": (
            "HISTORICAL_AXIE_SALE_FEE_4_25_PERCENT"
        ),
        "resale_quality": quality,
    }



def resolve_release_candidate_economics(
    position_status,
    gameplay_record,
    acquisition,
):
    if gameplay_record is not None:
        axie_class = (
            gameplay_record["axie_class"]
        )

        level = (
            gameplay_record["level"]
        )

        breed_count = (
            gameplay_record["breed_count"]
        )

        is_collectible = (
            gameplay_record["is_collectible"]
        )

        collectible_type = (
            gameplay_record["collectible_type"]
        )

        is_evolved = (
            gameplay_record["is_evolved"]
        )
    else:
        axie_class = None
        level = None
        breed_count = None
        is_collectible = None
        collectible_type = None
        is_evolved = None

    protected_attribute = None

    if (
        is_collectible is not None
        and is_evolved is not None
    ):
        protected_attribute = (
            is_collectible == 1
            or is_evolved == 1
        )

    acquisition_cost = decimal_or_none(
        acquisition["acquisition_cost"]
    )

    acquisition_quality = (
        acquisition["acquisition_quality"]
    )

    proven_capital_at_risk = None

    if (
        position_status
        == POSITION_OPEN_OWNED
        and acquisition_cost is not None
        and acquisition_quality
        == QUALITY_READY
    ):
        proven_capital_at_risk = (
            acquisition_cost
        )

    if (
        position_status
        != POSITION_OPEN_OWNED
    ):
        return {
            "release_analysis_status": (
                RELEASE_ANALYSIS_NOT_APPLICABLE
            ),
            "release_candidate_class": (
                axie_class
            ),
            "release_candidate_level": (
                level
            ),
            "release_candidate_breed_count": (
                breed_count
            ),
            "release_candidate_is_collectible": (
                is_collectible
            ),
            "release_candidate_collectible_type": (
                collectible_type
            ),
            "release_candidate_is_evolved": (
                is_evolved
            ),
            "release_protected_attribute": (
                protected_attribute
            ),
            "release_capital_at_risk_weth": None,
            "release_expected_recovery_weth": None,
            "release_expected_pl_weth": None,
            "release_economics_status": (
                RELEASE_ECONOMICS_NOT_APPLICABLE
            ),
            "release_analysis_source": (
                "POSITION_NOT_OPEN_OWNED"
            ),
            "release_analysis_quality": (
                QUALITY_READY
            ),
        }

    required_inputs_present = (
        gameplay_record is not None
        and level is not None
        and breed_count is not None
        and is_collectible is not None
        and is_evolved is not None
    )

    if not required_inputs_present:
        analysis_status = (
            RELEASE_ANALYSIS_REVIEW_MISSING_INPUTS
        )

        analysis_source = (
            "MISSING_GAMEPLAY_RELEASE_INPUTS"
        )

        analysis_quality = (
            QUALITY_REVIEW
        )

    elif protected_attribute:
        analysis_status = (
            RELEASE_ANALYSIS_REVIEW_PROTECTED
        )

        analysis_source = (
            "COLLECTIBLE_OR_EVOLVED_SAFEGUARD"
        )

        analysis_quality = (
            QUALITY_REVIEW
        )

    elif proven_capital_at_risk is None:
        analysis_status = (
            RELEASE_ANALYSIS_REVIEW_NO_COST
        )

        analysis_source = (
            "NO_PROVEN_ACQUISITION_BASIS"
        )

        analysis_quality = (
            QUALITY_REVIEW
        )

    else:
        analysis_status = (
            RELEASE_ANALYSIS_READY
        )

        analysis_source = (
            "GAMEPLAY_INPUTS_AND_PROVEN_COST_BASIS"
        )

        analysis_quality = (
            QUALITY_READY
        )

    return {
        "release_analysis_status": (
            analysis_status
        ),
        "release_candidate_class": (
            axie_class
        ),
        "release_candidate_level": (
            level
        ),
        "release_candidate_breed_count": (
            breed_count
        ),
        "release_candidate_is_collectible": (
            is_collectible
        ),
        "release_candidate_collectible_type": (
            collectible_type
        ),
        "release_candidate_is_evolved": (
            is_evolved
        ),
        "release_protected_attribute": (
            protected_attribute
        ),
        "release_capital_at_risk_weth": (
            proven_capital_at_risk
        ),
        "release_expected_recovery_weth": None,
        "release_expected_pl_weth": None,
        "release_economics_status": (
            RELEASE_ECONOMICS_UNAVAILABLE
        ),
        "release_analysis_source": (
            analysis_source
        ),
        "release_analysis_quality": (
            analysis_quality
        ),
    }


def summarize_capital_utilization(
    inventory,
):
    open_rows = [
        row
        for row in inventory
        if (
            row["position_status"]
            == POSITION_OPEN_OWNED
        )
    ]

    proven_rows = [
        row
        for row in open_rows
        if (
            row["acquisition_cost"]
            is not None
            and row["acquisition_quality"]
            == QUALITY_READY
        )
    ]

    open_count = len(open_rows)
    proven_count = len(proven_rows)

    coverage_ratio = (
        Decimal(proven_count)
        / Decimal(open_count)
        if open_count
        else Decimal("0")
    )

    proven_open_capital = sum(
        (
            decimal_or_none(
                row["acquisition_cost"]
            )
            for row in proven_rows
        ),
        Decimal("0"),
    )

    holding_rows = [
        row
        for row in proven_rows
        if (
            row["holding_days"]
            is not None
        )
    ]

    capital_days = sum(
        (
            decimal_or_none(
                row["acquisition_cost"]
            )
            * Decimal(
                str(row["holding_days"])
            )
            for row in holding_rows
        ),
        Decimal("0"),
    )

    capital_weighted_age_days = (
        capital_days
        / proven_open_capital
        if (
            proven_open_capital
            != Decimal("0")
            and len(holding_rows)
            == proven_count
        )
        else None
    )

    protected_capital = sum(
        (
            decimal_or_none(
                row["acquisition_cost"]
            )
            for row in proven_rows
            if (
                row[
                    "release_protected_attribute"
                ] is True
            )
        ),
        Decimal("0"),
    )

    release_ready_capital = sum(
        (
            decimal_or_none(
                row["acquisition_cost"]
            )
            for row in proven_rows
            if (
                row["release_analysis_status"]
                == RELEASE_ANALYSIS_READY
            )
        ),
        Decimal("0"),
    )

    protected_capital_ratio = (
        protected_capital
        / proven_open_capital
        if proven_open_capital
        != Decimal("0")
        else None
    )

    release_ready_capital_ratio = (
        release_ready_capital
        / proven_open_capital
        if proven_open_capital
        != Decimal("0")
        else None
    )

    return {
        "capital_coverage_status": (
            "PARTIAL_COVERAGE"
            if proven_count < open_count
            else "FULL_COVERAGE"
        ),
        "open_position_count": (
            open_count
        ),
        "proven_cost_position_count": (
            proven_count
        ),
        "cost_basis_coverage_ratio": (
            coverage_ratio
        ),
        "proven_open_capital_weth": (
            proven_open_capital
        ),
        "capital_days_weth": (
            capital_days
        ),
        "capital_weighted_age_days": (
            capital_weighted_age_days
        ),
        "protected_capital_weth": (
            protected_capital
        ),
        "protected_capital_ratio": (
            protected_capital_ratio
        ),
        "release_ready_capital_weth": (
            release_ready_capital
        ),
        "release_ready_capital_ratio": (
            release_ready_capital_ratio
        ),
    }



def resolve_marketplace_strategy(
    position_status,
    resale,
    release_analysis,
):
    if (
        position_status
        != POSITION_OPEN_OWNED
    ):
        return {
            "marketplace_strategy_status": (
                MARKETPLACE_STRATEGY_NOT_APPLICABLE
            ),
            "marketplace_strategy_action": (
                MARKETPLACE_ACTION_NONE
            ),
            "marketplace_strategy_reason": (
                "POSITION_NOT_OPEN_OWNED"
            ),
            "marketplace_strategy_requires_live_price": (
                False
            ),
            "marketplace_strategy_requires_release_recovery_model": (
                False
            ),
            "marketplace_strategy_quality": (
                QUALITY_READY
            ),
        }

    if (
        release_analysis[
            "release_protected_attribute"
        ] is True
    ):
        return {
            "marketplace_strategy_status": (
                MARKETPLACE_STRATEGY_HOLD_PROTECTED
            ),
            "marketplace_strategy_action": (
                MARKETPLACE_ACTION_HOLD
            ),
            "marketplace_strategy_reason": (
                "COLLECTIBLE_OR_EVOLVED_SAFEGUARD"
            ),
            "marketplace_strategy_requires_live_price": (
                False
            ),
            "marketplace_strategy_requires_release_recovery_model": (
                False
            ),
            "marketplace_strategy_quality": (
                QUALITY_READY
            ),
        }

    if (
        resale["resale_status"]
        == RESALE_STATUS_READY
        and release_analysis[
            "release_analysis_status"
        ] == RELEASE_ANALYSIS_READY
    ):
        return {
            "marketplace_strategy_status": (
                MARKETPLACE_STRATEGY_REVIEW_EXIT_OPTIONS
            ),
            "marketplace_strategy_action": (
                MARKETPLACE_ACTION_REVIEW
            ),
            "marketplace_strategy_reason": (
                "RESALE_BREAK_EVEN_AND_RELEASE_INPUTS_AVAILABLE"
            ),
            "marketplace_strategy_requires_live_price": (
                True
            ),
            "marketplace_strategy_requires_release_recovery_model": (
                True
            ),
            "marketplace_strategy_quality": (
                QUALITY_REVIEW
            ),
        }

    if (
        release_analysis[
            "release_analysis_status"
        ] == RELEASE_ANALYSIS_REVIEW_MISSING_INPUTS
    ):
        reason = (
            "MISSING_GAMEPLAY_RELEASE_INPUTS"
        )

    elif (
        resale["resale_status"]
        == RESALE_STATUS_UNAVAILABLE_NO_COST
        or release_analysis[
            "release_analysis_status"
        ] == RELEASE_ANALYSIS_REVIEW_NO_COST
    ):
        reason = (
            "NO_PROVEN_ACQUISITION_BASIS"
        )

    else:
        reason = (
            "INSUFFICIENT_MARKETPLACE_DECISION_DATA"
        )

    return {
        "marketplace_strategy_status": (
            MARKETPLACE_STRATEGY_HOLD_INSUFFICIENT_DATA
        ),
        "marketplace_strategy_action": (
            MARKETPLACE_ACTION_HOLD
        ),
        "marketplace_strategy_reason": (
            reason
        ),
        "marketplace_strategy_requires_live_price": (
            False
        ),
        "marketplace_strategy_requires_release_recovery_model": (
            False
        ),
        "marketplace_strategy_quality": (
            QUALITY_REVIEW
        ),
    }




def resolve_current_position_status(
    marketplace_events,
    accounting_events,
    gameplay_record,
):
    marketplace_buy_count = (
        count_marketplace_event(
            marketplace_events,
            "buy",
        )
    )

    accounting_purchase_count = (
        count_accounting_event(
            accounting_events,
            "ASSET_PURCHASE",
        )
    )

    if (
        marketplace_buy_count > 1
        or accounting_purchase_count > 1
    ):
        return (
            POSITION_REVIEW_REPEAT_ACQUISITION,
            "REPEAT_ACQUISITION_REQUIRES_POSITION_CYCLES",
        )

    if find_accounting_events(
        accounting_events,
        "ASSET_SALE",
    ):
        return (
            POSITION_CLOSED_SOLD,
            "ACCOUNTING_ASSET_SALE",
        )

    if find_accounting_events(
        accounting_events,
        "ASSET_BURN",
    ):
        return (
            POSITION_CLOSED_RELEASED,
            "ACCOUNTING_ASSET_BURN",
        )

    if count_marketplace_event(
        marketplace_events,
        "sale",
    ):
        return (
            POSITION_CLOSED_SOLD,
            "MARKETPLACE_SALE",
        )

    if count_marketplace_event(
        marketplace_events,
        "release",
    ):
        return (
            POSITION_CLOSED_RELEASED,
            "MARKETPLACE_RELEASE",
        )

    if (
        gameplay_record is not None
        and gameplay_record[
            "ownership_status"
        ] == "OWNED"
    ):
        return (
            POSITION_OPEN_OWNED,
            "GAMEPLAY_OWNERSHIP",
        )

    return (
        POSITION_REVIEW_OWNERSHIP_UNRESOLVED,
        "UNRESOLVED",
    )


def resolve_position_data_quality(
    position_status,
    accounting_events,
    gameplay_record,
):
    if position_status == POSITION_CLOSED_SOLD:
        if has_ready_accounting_event(
            accounting_events,
            "ASSET_SALE",
        ):
            return QUALITY_READY

        return QUALITY_REVIEW

    if (
        position_status
        == POSITION_CLOSED_RELEASED
    ):
        if has_ready_accounting_event(
            accounting_events,
            "ASSET_BURN",
        ):
            return QUALITY_READY

        return QUALITY_REVIEW

    if position_status == POSITION_OPEN_OWNED:
        if (
            gameplay_record is not None
            and gameplay_record[
                "ownership_status"
            ] == "OWNED"
            and has_ready_accounting_event(
                accounting_events,
                "ASSET_PURCHASE",
            )
        ):
            return QUALITY_READY

        return QUALITY_REVIEW

    return QUALITY_REVIEW


def build_current_marketplace_axie_inventory(
    connection,
    as_of_datetime=None,
):
    if as_of_datetime is None:
        as_of_datetime = (
            datetime.now(timezone.utc)
            .replace(tzinfo=None)
        )

    inventory = []

    for asset_id in load_canonical_axie_ids(
    connection
    ):
        marketplace_events = (
            load_marketplace_axie_events(
                connection,
                asset_id,
            )
        )

        accounting_events = (
            load_accounting_axie_events(
                connection,
                asset_id,
            )
        )

        gameplay_record = (
            load_gameplay_axie_record(
                connection,
                asset_id,
            )
        )

        (
            position_status,
            status_source,
        ) = resolve_current_position_status(
            marketplace_events,
            accounting_events,
            gameplay_record,
        )

        listing = resolve_listing_evidence(
            marketplace_events,
            position_status,
        )

        sale = resolve_sale_evidence(
            marketplace_events,
            accounting_events,
            position_status,
        )

        realized = resolve_realized_economics(
            accounting_events,
            position_status,
        )

        unrealized = resolve_unrealized_economics(
            position_status,
        )

        data_quality = (
            resolve_position_data_quality(
                position_status,
                accounting_events,
                gameplay_record,
            )
        )

        acquisition = (
            resolve_acquisition_evidence(
                marketplace_events,
                accounting_events,
            )
        )

        ownership_start = (
            resolve_ownership_start_evidence(
                marketplace_events,
                accounting_events,
                gameplay_record,
            )
        )

        release = resolve_release_evidence(
            marketplace_events,
            accounting_events,
        )

        holding = resolve_holding_period(
            position_status,
            ownership_start,
            sale,
            release,
            as_of_datetime,
        )


        resale = resolve_resale_break_even(
            position_status,
            acquisition,
        )

        release_analysis = (
            resolve_release_candidate_economics(
                position_status,
                gameplay_record,
                acquisition,
            )
        )

        marketplace_strategy = (
            resolve_marketplace_strategy(
                position_status,
                resale,
                release_analysis,
            )
        )


        inventory.append(
            {
                "asset_id": asset_id,
                "listing_status": (
                    listing["listing_status"]
                ),
                "last_listing_datetime": (
                    listing[
                        "last_listing_datetime"
                    ]
                ),
                "last_listing_price": (
                    listing["last_listing_price"]
                ),
                "last_listing_currency": (
                    listing[
                        "last_listing_currency"
                    ]
                ),
                "listing_source": (
                    listing["listing_source"]
                ),
                "listing_quality": (
                    listing["listing_quality"]
                ),
                "sale_status": (
                    sale["sale_status"]
                ),
                "sale_datetime": (
                    sale["sale_datetime"]
                ),
                "sale_txhash": (
                    sale["sale_txhash"]
                ),
                "sale_source": (
                    sale["sale_source"]
                ),
                "sale_quality": (
                    sale["sale_quality"]
                ),

                "realized_status": (
                    realized["realized_status"]
                ),
                "gross_sale": (
                    realized["gross_sale"]
                ),
                "marketplace_fee": (
                    realized["marketplace_fee"]
                ),
                "net_proceeds": (
                    realized["net_proceeds"]
                ),
                "cost_basis": (
                    realized["cost_basis"]
                ),
                "realized_pl": (
                    realized["realized_pl"]
                ),
                "realized_roi": (
                    realized["realized_roi"]
                ),
                "realized_source": (
                    realized["realized_source"]
                ),
                "realized_quality": (
                    realized["realized_quality"]
                ),
                "unrealized_status": (
                    unrealized["unrealized_status"]
                ),
                "current_market_value": (
                    unrealized[
                        "current_market_value"
                    ]
                ),
                "unrealized_pl": (
                    unrealized["unrealized_pl"]
                ),
                "unrealized_roi": (
                    unrealized["unrealized_roi"]
                ),
                "unrealized_source": (
                    unrealized["unrealized_source"]
                ),
                "unrealized_quality": (
                    unrealized["unrealized_quality"]
                ),

                "release_datetime": (
                    release["release_datetime"]
                ),
                "release_source": (
                    release["release_source"]
                ),
                "release_quality": (
                    release["release_quality"]
                ),
                "holding_status": (
                    holding["holding_status"]
                ),
                "holding_start_datetime": (
                    holding[
                        "holding_start_datetime"
                    ]
                ),
                "holding_end_datetime": (
                    holding[
                        "holding_end_datetime"
                    ]
                ),
                "holding_seconds": (
                    holding["holding_seconds"]
                ),
                "holding_days": (
                    holding["holding_days"]
                ),
                "holding_quality": (
                    holding["holding_quality"]
                ),

                "resale_status": (
                    resale["resale_status"]
                ),
                "resale_fee_rate_assumption": (
                    resale[
                        "resale_fee_rate_assumption"
                    ]
                ),
                "break_even_gross_price": (
                    resale[
                        "break_even_gross_price"
                    ]
                ),
                "break_even_fee": (
                    resale["break_even_fee"]
                ),
                "break_even_net_proceeds": (
                    resale[
                        "break_even_net_proceeds"
                    ]
                ),
                "break_even_currency": (
                    resale["break_even_currency"]
                ),
                "resale_source": (
                    resale["resale_source"]
                ),
                "resale_quality": (
                    resale["resale_quality"]
                ),


                "release_analysis_status": (
                    release_analysis[
                        "release_analysis_status"
                    ]
                ),
                "release_candidate_class": (
                    release_analysis[
                        "release_candidate_class"
                    ]
                ),
                "release_candidate_level": (
                    release_analysis[
                        "release_candidate_level"
                    ]
                ),
                "release_candidate_breed_count": (
                    release_analysis[
                        "release_candidate_breed_count"
                    ]
                ),
                "release_candidate_is_collectible": (
                    release_analysis[
                        "release_candidate_is_collectible"
                    ]
                ),
                "release_candidate_collectible_type": (
                    release_analysis[
                        "release_candidate_collectible_type"
                    ]
                ),
                "release_candidate_is_evolved": (
                    release_analysis[
                        "release_candidate_is_evolved"
                    ]
                ),
                "release_protected_attribute": (
                    release_analysis[
                        "release_protected_attribute"
                    ]
                ),
                "release_capital_at_risk_weth": (
                    release_analysis[
                        "release_capital_at_risk_weth"
                    ]
                ),
                "release_expected_recovery_weth": (
                    release_analysis[
                        "release_expected_recovery_weth"
                    ]
                ),
                "release_expected_pl_weth": (
                    release_analysis[
                        "release_expected_pl_weth"
                    ]
                ),
                "release_economics_status": (
                    release_analysis[
                        "release_economics_status"
                    ]
                ),
                "release_analysis_source": (
                    release_analysis[
                        "release_analysis_source"
                    ]
                ),
                "release_analysis_quality": (
                    release_analysis[
                        "release_analysis_quality"
                    ]
                ),

                "marketplace_strategy_status": (
                    marketplace_strategy[
                        "marketplace_strategy_status"
                    ]
                ),
                "marketplace_strategy_action": (
                    marketplace_strategy[
                        "marketplace_strategy_action"
                    ]
                ),
                "marketplace_strategy_reason": (
                    marketplace_strategy[
                        "marketplace_strategy_reason"
                    ]
                ),
                "marketplace_strategy_requires_live_price": (
                    marketplace_strategy[
                        "marketplace_strategy_requires_live_price"
                    ]
                ),
                "marketplace_strategy_requires_release_recovery_model": (
                    marketplace_strategy[
                        "marketplace_strategy_requires_release_recovery_model"
                    ]
                ),
                "marketplace_strategy_quality": (
                    marketplace_strategy[
                        "marketplace_strategy_quality"
                    ]
                ),


                "ownership_start_datetime": (
                    ownership_start[
                        "ownership_start_datetime"
                    ]
                ),
                "ownership_start_source": (
                    ownership_start[
                        "ownership_start_source"
                    ]
                ),
                "ownership_start_quality": (
                    ownership_start[
                        "ownership_start_quality"
                    ]
                ),
                "acquisition_txhash": (
                    acquisition[
                        "acquisition_txhash"
                    ]
                ),
                "acquisition_datetime": (
                    acquisition[
                        "acquisition_datetime"
                    ]
                ),
                "acquisition_cost": (
                    acquisition[
                        "acquisition_cost"
                    ]
                ),
                "acquisition_currency": (
                    acquisition[
                        "acquisition_currency"
                    ]
                ),
                "acquisition_source": (
                    acquisition[
                        "acquisition_source"
                    ]
                ),
                "acquisition_quality": (
                    acquisition[
                        "acquisition_quality"
                    ]
                ),
                "position_status": (
                    position_status
                ),
                "status_source": status_source,
                "ownership_status": (
                    gameplay_record[
                        "ownership_status"
                    ]
                    if gameplay_record
                    is not None
                    else None
                ),
                "marketplace_buy_count": (
                    count_marketplace_event(
                        marketplace_events,
                        "buy",
                    )
                ),
                "marketplace_list_count": (
                    count_marketplace_event(
                        marketplace_events,
                        "list",
                    )
                ),
                "marketplace_sale_count": (
                    count_marketplace_event(
                        marketplace_events,
                        "sale",
                    )
                ),
                "marketplace_release_count": (
                    count_marketplace_event(
                        marketplace_events,
                        "release",
                    )
                ),
                "accounting_purchase_count": (
                    count_accounting_event(
                        accounting_events,
                        "ASSET_PURCHASE",
                    )
                ),
                "accounting_sale_count": (
                    count_accounting_event(
                        accounting_events,
                        "ASSET_SALE",
                    )
                ),
                "accounting_burn_count": (
                    count_accounting_event(
                        accounting_events,
                        "ASSET_BURN",
                    )
                ),
                "data_quality": data_quality,
                "model_version": (
                    MARKETPLACE_INVENTORY_MODEL_VERSION
                ),
            }
        )

    return inventory



def validate_current_marketplace_axie_inventory(
    inventory,
):
    errors = []

    asset_ids = [
        row["asset_id"]
        for row in inventory
    ]

    if len(asset_ids) != len(set(asset_ids)):
        errors.append(
            "DUPLICATE_ASSET_IDS"
        )

    valid_position_statuses = {
        POSITION_OPEN_OWNED,
        POSITION_CLOSED_SOLD,
        POSITION_CLOSED_RELEASED,
        POSITION_REVIEW_OWNERSHIP_UNRESOLVED,
        POSITION_REVIEW_REPEAT_ACQUISITION,
    }

    valid_listing_statuses = {
        LISTING_STATUS_RECORDED_UNVERIFIED,
        LISTING_STATUS_UNKNOWN,
        LISTING_STATUS_CLOSED_POSITION,
    }

    valid_sale_statuses = {
        SALE_STATUS_CONFIRMED,
        SALE_STATUS_RECORDED_UNVERIFIED,
        SALE_STATUS_NO_EVIDENCE,
        SALE_STATUS_NOT_APPLICABLE_RELEASED,
        SALE_STATUS_REVIEW_MULTIPLE,
    }

    for row in inventory:
        asset_id = row["asset_id"]
        position_status = (
            row["position_status"]
        )
        listing_status = (
            row["listing_status"]
        )
        sale_status = (
            row["sale_status"]
        )

        if not asset_id:
            errors.append(
                "MISSING_ASSET_ID"
            )
            continue

        if (
            position_status
            not in valid_position_statuses
        ):
            errors.append(
                f"{asset_id}:INVALID_POSITION_STATUS"
            )
            continue

        if (
            listing_status
            not in valid_listing_statuses
        ):
            errors.append(
                f"{asset_id}:INVALID_LISTING_STATUS"
            )

        if (
            sale_status
            not in valid_sale_statuses
        ):
            errors.append(
                f"{asset_id}:INVALID_SALE_STATUS"
            )

        if (
            position_status
            == POSITION_OPEN_OWNED
            and row["ownership_status"]
            != "OWNED"
        ):
            errors.append(
                f"{asset_id}:OPEN_NOT_CONFIRMED_OWNED"
            )

        if (
            position_status
            == POSITION_CLOSED_SOLD
            and row["accounting_sale_count"] == 0
            and row["marketplace_sale_count"] == 0
        ):
            errors.append(
                f"{asset_id}:SOLD_WITHOUT_SALE_EVIDENCE"
            )

        if (
            position_status
            == POSITION_CLOSED_RELEASED
            and row["accounting_burn_count"] == 0
            and row["marketplace_release_count"] == 0
        ):
            errors.append(
                f"{asset_id}:RELEASED_WITHOUT_RELEASE_EVIDENCE"
            )

        if (
            position_status
            == POSITION_REVIEW_REPEAT_ACQUISITION
            and row["marketplace_buy_count"] <= 1
            and row["accounting_purchase_count"] <= 1
        ):
            errors.append(
                f"{asset_id}:REPEAT_ACQUISITION_NOT_PROVEN"
            )

        if (
            row["ownership_start_quality"]
            == QUALITY_READY
            and row["ownership_start_datetime"]
            is None
        ):
            errors.append(
                f"{asset_id}:READY_OWNERSHIP_WITHOUT_DATETIME"
            )

        if (
            row["ownership_start_quality"]
            == QUALITY_READY
            and row["ownership_start_source"]
            == "UNRESOLVED"
        ):
            errors.append(
                f"{asset_id}:READY_OWNERSHIP_UNRESOLVED_SOURCE"
            )

        if (
            row["acquisition_quality"]
            == QUALITY_READY
        ):
            if (
                row["acquisition_source"]
                != "ACCOUNTING_ASSET_PURCHASE"
            ):
                errors.append(
                    f"{asset_id}:READY_ACQUISITION_BAD_SOURCE"
                )

            if (
                row["acquisition_txhash"]
                is None
            ):
                errors.append(
                    f"{asset_id}:READY_ACQUISITION_NO_TXHASH"
                )

            if (
                row["acquisition_datetime"]
                is None
            ):
                errors.append(
                    f"{asset_id}:READY_ACQUISITION_NO_DATETIME"
                )

            if (
                row["acquisition_cost"]
                is None
            ):
                errors.append(
                    f"{asset_id}:READY_ACQUISITION_NO_COST"
                )

            if (
                row["acquisition_currency"]
                is None
            ):
                errors.append(
                    f"{asset_id}:READY_ACQUISITION_NO_CURRENCY"
                )

        if (
            row["acquisition_cost"] is not None
            and row["acquisition_currency"] is None
        ):
            errors.append(
                f"{asset_id}:COST_WITHOUT_CURRENCY"
            )

        if (
            row["acquisition_cost"] is not None
            and row["acquisition_datetime"] is None
        ):
            errors.append(
                f"{asset_id}:COST_WITHOUT_DATETIME"
            )

        if (
            row["acquisition_source"]
            == "UNRESOLVED"
            and row["acquisition_cost"]
            is not None
        ):
            errors.append(
                f"{asset_id}:UNRESOLVED_SOURCE_WITH_COST"
            )

        if (
            listing_status
            == LISTING_STATUS_RECORDED_UNVERIFIED
        ):
            if (
                position_status
                != POSITION_OPEN_OWNED
            ):
                errors.append(
                    f"{asset_id}:UNVERIFIED_LISTING_NOT_OPEN"
                )

            if (
                row["last_listing_datetime"]
                is None
            ):
                errors.append(
                    f"{asset_id}:LISTING_WITHOUT_DATETIME"
                )

            if (
                row["last_listing_price"]
                is None
            ):
                errors.append(
                    f"{asset_id}:LISTING_WITHOUT_PRICE"
                )

            if (
                row["listing_source"]
                != "LEGACY_MARKETPLACE_LIST"
            ):
                errors.append(
                    f"{asset_id}:LISTING_BAD_SOURCE"
                )

        if (
            listing_status
            == LISTING_STATUS_UNKNOWN
            and row["last_listing_datetime"]
            is not None
        ):
            errors.append(
                f"{asset_id}:UNKNOWN_LISTING_WITH_HISTORY"
            )

        if (
            position_status
            in {
                POSITION_CLOSED_SOLD,
                POSITION_CLOSED_RELEASED,
            }
            and listing_status
            != LISTING_STATUS_CLOSED_POSITION
        ):
            errors.append(
                f"{asset_id}:CLOSED_POSITION_BAD_LISTING_STATUS"
            )

        if (
            sale_status
            == SALE_STATUS_CONFIRMED
        ):
            if (
                position_status
                != POSITION_CLOSED_SOLD
            ):
                errors.append(
                    f"{asset_id}:CONFIRMED_SALE_NOT_CLOSED_SOLD"
                )

            if (
                row["sale_datetime"]
                is None
            ):
                errors.append(
                    f"{asset_id}:CONFIRMED_SALE_NO_DATETIME"
                )

            if (
                row["sale_txhash"]
                is None
            ):
                errors.append(
                    f"{asset_id}:CONFIRMED_SALE_NO_TXHASH"
                )

            if (
                row["sale_source"]
                != "ACCOUNTING_ASSET_SALE"
            ):
                errors.append(
                    f"{asset_id}:CONFIRMED_SALE_BAD_SOURCE"
                )

            if (
                row["sale_quality"]
                != QUALITY_READY
            ):
                errors.append(
                    f"{asset_id}:CONFIRMED_SALE_NOT_READY"
                )

        if (
            sale_status
            == SALE_STATUS_RECORDED_UNVERIFIED
        ):
            if (
                position_status
                != POSITION_CLOSED_SOLD
            ):
                errors.append(
                    f"{asset_id}:LEGACY_SALE_NOT_CLOSED_SOLD"
                )

            if (
                row["sale_datetime"]
                is None
            ):
                errors.append(
                    f"{asset_id}:LEGACY_SALE_NO_DATETIME"
                )

            if (
                row["sale_source"]
                != "LEGACY_MARKETPLACE_SALE"
            ):
                errors.append(
                    f"{asset_id}:LEGACY_SALE_BAD_SOURCE"
                )

            if (
                row["sale_quality"]
                != QUALITY_REVIEW
            ):
                errors.append(
                    f"{asset_id}:LEGACY_SALE_NOT_REVIEW"
                )

        if (
            sale_status
            == SALE_STATUS_NOT_APPLICABLE_RELEASED
        ):
            if (
                position_status
                != POSITION_CLOSED_RELEASED
            ):
                errors.append(
                    f"{asset_id}:SALE_NA_NOT_RELEASED"
                )

            if (
                row["sale_datetime"]
                is not None
                or row["sale_txhash"]
                is not None
            ):
                errors.append(
                    f"{asset_id}:RELEASED_HAS_SALE_FIELDS"
                )

        if (
            position_status
            == POSITION_CLOSED_SOLD
            and sale_status
            == SALE_STATUS_NO_EVIDENCE
        ):
            errors.append(
                f"{asset_id}:CLOSED_SOLD_NO_SALE_STATUS"
            )

        if (
            position_status
            == POSITION_OPEN_OWNED
            and sale_status
            != SALE_STATUS_NO_EVIDENCE
        ):
            errors.append(
                f"{asset_id}:OPEN_POSITION_HAS_SALE_STATUS"
            )

        if (
            row["realized_status"]
            == REALIZED_STATUS_READY
        ):
            if (
                position_status
                != POSITION_CLOSED_SOLD
            ):
                errors.append(
                    f"{asset_id}:REALIZED_READY_NOT_SOLD"
                )

            for field in (
                "gross_sale",
                "marketplace_fee",
                "net_proceeds",
                "cost_basis",
                "realized_pl",
                "realized_roi",
            ):
                if row[field] is None:
                    errors.append(
                        f"{asset_id}:REALIZED_READY_MISSING_{field.upper()}"
                    )

            if (
                row["realized_source"]
                != "BLOCKCHAIN_ACCOUNTING_RECORD"
            ):
                errors.append(
                    f"{asset_id}:REALIZED_READY_BAD_SOURCE"
                )

            if (
                row["realized_quality"]
                != QUALITY_READY
            ):
                errors.append(
                    f"{asset_id}:REALIZED_READY_BAD_QUALITY"
                )

        if (
            row["realized_status"]
            == REALIZED_STATUS_NOT_APPLICABLE
            and position_status
            == POSITION_CLOSED_SOLD
        ):
            errors.append(
                f"{asset_id}:SOLD_REALIZED_NOT_APPLICABLE"
            )

        if (
            position_status
            != POSITION_CLOSED_SOLD
            and row["realized_pl"]
            is not None
        ):
            errors.append(
                f"{asset_id}:NON_SOLD_HAS_REALIZED_PL"
            )

        if (
            position_status
            == POSITION_OPEN_OWNED
        ):
            if (
                row["unrealized_status"]
                != UNREALIZED_STATUS_UNAVAILABLE_NO_MARKET_PRICE
            ):
                errors.append(
                    f"{asset_id}:OPEN_BAD_UNREALIZED_STATUS"
                )

            if (
                row["unrealized_source"]
                != "NO_LIVE_MARKET_PRICE_SOURCE"
            ):
                errors.append(
                    f"{asset_id}:OPEN_BAD_UNREALIZED_SOURCE"
                )

            if (
                row["current_market_value"]
                is not None
            ):
                errors.append(
                    f"{asset_id}:OPEN_HAS_UNPROVEN_MARKET_VALUE"
                )

            if (
                row["unrealized_pl"]
                is not None
            ):
                errors.append(
                    f"{asset_id}:OPEN_HAS_UNPROVEN_UNREALIZED_PL"
                )

            if (
                row["unrealized_roi"]
                is not None
            ):
                errors.append(
                    f"{asset_id}:OPEN_HAS_UNPROVEN_UNREALIZED_ROI"
                )

        if (
            position_status
            in {
                POSITION_CLOSED_SOLD,
                POSITION_CLOSED_RELEASED,
            }
            and row["unrealized_status"]
            != UNREALIZED_STATUS_NOT_APPLICABLE
        ):
            errors.append(
                f"{asset_id}:CLOSED_BAD_UNREALIZED_STATUS"
            )


        if (
            row["holding_status"]
            == HOLDING_STATUS_READY
        ):
            if (
                row["holding_quality"]
                != QUALITY_READY
            ):
                errors.append(
                    f"{asset_id}:HOLDING_READY_BAD_QUALITY"
                )

            if (
                row["holding_start_datetime"]
                is None
            ):
                errors.append(
                    f"{asset_id}:HOLDING_READY_NO_START"
                )

            if (
                row["holding_end_datetime"]
                is None
            ):
                errors.append(
                    f"{asset_id}:HOLDING_READY_NO_END"
                )

            if (
                row["holding_seconds"]
                is None
            ):
                errors.append(
                    f"{asset_id}:HOLDING_READY_NO_SECONDS"
                )

            if (
                row["holding_days"]
                is None
            ):
                errors.append(
                    f"{asset_id}:HOLDING_READY_NO_DAYS"
                )

            if (
                row["holding_seconds"]
                is not None
                and row["holding_seconds"] < 0
            ):
                errors.append(
                    f"{asset_id}:NEGATIVE_HOLDING_SECONDS"
                )

            if (
                row["holding_days"]
                is not None
                and row["holding_days"] < 0
            ):
                errors.append(
                    f"{asset_id}:NEGATIVE_HOLDING_DAYS"
                )

        if (
            row["holding_status"]
            == HOLDING_STATUS_REVIEW
        ):
            if (
                row["holding_quality"]
                != QUALITY_REVIEW
            ):
                errors.append(
                    f"{asset_id}:HOLDING_REVIEW_BAD_QUALITY"
                )

            if (
                row["holding_seconds"]
                is not None
                or row["holding_days"]
                is not None
            ):
                errors.append(
                    f"{asset_id}:REVIEW_HAS_NUMERIC_HOLDING"
                )

        if (
            row["holding_status"]
            == HOLDING_STATUS_UNAVAILABLE
        ):
            if (
                row["holding_quality"]
                != QUALITY_REVIEW
            ):
                errors.append(
                    f"{asset_id}:HOLDING_UNAVAILABLE_BAD_QUALITY"
                )

            if (
                row["holding_seconds"]
                is not None
                or row["holding_days"]
                is not None
            ):
                errors.append(
                    f"{asset_id}:UNAVAILABLE_HAS_NUMERIC_HOLDING"
                )

        if (
            row["holding_seconds"]
            is not None
            and row["holding_days"]
            is not None
        ):
            expected_days = (
                row["holding_seconds"]
                / 86400
            )

            if (
                abs(
                    expected_days
                    - row["holding_days"]
                )
                > 1e-9
            ):
                errors.append(
                    f"{asset_id}:HOLDING_UNIT_MISMATCH"
                )

        if (
            row["resale_fee_rate_assumption"]
            != ASSUMED_MARKETPLACE_FEE_RATE
        ):
            errors.append(
                f"{asset_id}:RESALE_FEE_ASSUMPTION_MISMATCH"
            )

        if (
            row["resale_status"]
            == RESALE_STATUS_READY
        ):
            if (
                position_status
                != POSITION_OPEN_OWNED
            ):
                errors.append(
                    f"{asset_id}:RESALE_READY_NOT_OPEN"
                )

            if (
                row["resale_quality"]
                != QUALITY_READY
            ):
                errors.append(
                    f"{asset_id}:RESALE_READY_BAD_QUALITY"
                )

            if (
                row["break_even_gross_price"]
                is None
                or row["break_even_fee"]
                is None
                or row["break_even_net_proceeds"]
                is None
                or row["break_even_currency"]
                is None
            ):
                errors.append(
                    f"{asset_id}:RESALE_READY_MISSING_FIELDS"
                )

            if (
                row["acquisition_cost"]
                is None
            ):
                errors.append(
                    f"{asset_id}:RESALE_READY_NO_ACQUISITION_COST"
                )

            if (
                row["acquisition_quality"]
                != QUALITY_READY
            ):
                errors.append(
                    f"{asset_id}:RESALE_READY_BAD_ACQUISITION"
                )

            if (
                row["resale_source"]
                != "HISTORICAL_AXIE_SALE_FEE_4_25_PERCENT"
            ):
                errors.append(
                    f"{asset_id}:RESALE_READY_BAD_SOURCE"
                )

            if (
                row["break_even_net_proceeds"]
                is not None
                and row["acquisition_cost"]
                is not None
            ):
                acquisition_cost = (
                    decimal_or_none(
                        row["acquisition_cost"]
                    )
                )

                if (
                    acquisition_cost is None
                    or abs(
                        row[
                            "break_even_net_proceeds"
                        ]
                        - acquisition_cost
                    )
                    > Decimal("0.000000000000000001")
                ):
                    errors.append(
                        f"{asset_id}:BREAK_EVEN_NET_MISMATCH"
                    )

            if (
                row["break_even_gross_price"]
                is not None
                and row["break_even_fee"]
                is not None
                and row["break_even_net_proceeds"]
                is not None
            ):
                calculated_net = (
                    row["break_even_gross_price"]
                    - row["break_even_fee"]
                )

                if (
                    abs(
                        calculated_net
                        - row[
                            "break_even_net_proceeds"
                        ]
                    )
                    > Decimal("0.000000000000000001")
                ):
                    errors.append(
                        f"{asset_id}:BREAK_EVEN_ARITHMETIC_MISMATCH"
                    )

        if (
            row["resale_status"]
            == RESALE_STATUS_UNAVAILABLE_NO_COST
        ):
            if (
                position_status
                != POSITION_OPEN_OWNED
            ):
                errors.append(
                    f"{asset_id}:NO_COST_RESALE_NOT_OPEN"
                )

            if (
                row["acquisition_cost"]
                is not None
            ):
                errors.append(
                    f"{asset_id}:NO_COST_RESALE_HAS_COST"
                )

            if any(
                row[field] is not None
                for field in (
                    "break_even_gross_price",
                    "break_even_fee",
                    "break_even_net_proceeds",
                    "break_even_currency",
                )
            ):
                errors.append(
                    f"{asset_id}:NO_COST_RESALE_HAS_BREAK_EVEN"
                )

        if (
            row["resale_status"]
            == RESALE_STATUS_NOT_APPLICABLE
        ):
            if (
                position_status
                == POSITION_OPEN_OWNED
            ):
                errors.append(
                    f"{asset_id}:OPEN_RESALE_NOT_APPLICABLE"
                )

            if any(
                row[field] is not None
                for field in (
                    "break_even_gross_price",
                    "break_even_fee",
                    "break_even_net_proceeds",
                    "break_even_currency",
                )
            ):
                errors.append(
                    f"{asset_id}:CLOSED_HAS_BREAK_EVEN"
                )


        valid_release_analysis_statuses = {
            RELEASE_ANALYSIS_READY,
            RELEASE_ANALYSIS_REVIEW_PROTECTED,
            RELEASE_ANALYSIS_REVIEW_NO_COST,
            RELEASE_ANALYSIS_REVIEW_MISSING_INPUTS,
            RELEASE_ANALYSIS_NOT_APPLICABLE,
        }

        if (
            row["release_analysis_status"]
            not in valid_release_analysis_statuses
        ):
            errors.append(
                f"{asset_id}:INVALID_RELEASE_ANALYSIS_STATUS"
            )

        if (
            row["position_status"]
            != POSITION_OPEN_OWNED
        ):
            if (
                row["release_analysis_status"]
                != RELEASE_ANALYSIS_NOT_APPLICABLE
            ):
                errors.append(
                    f"{asset_id}:CLOSED_RELEASE_ANALYSIS_APPLICABLE"
                )

            if (
                row["release_economics_status"]
                != RELEASE_ECONOMICS_NOT_APPLICABLE
            ):
                errors.append(
                    f"{asset_id}:CLOSED_RELEASE_ECONOMICS_APPLICABLE"
                )

            if (
                row["release_capital_at_risk_weth"]
                is not None
            ):
                errors.append(
                    f"{asset_id}:CLOSED_HAS_RELEASE_CAPITAL_AT_RISK"
                )

        if (
            row["position_status"]
            == POSITION_OPEN_OWNED
        ):
            if (
                row["release_economics_status"]
                != RELEASE_ECONOMICS_UNAVAILABLE
            ):
                errors.append(
                    f"{asset_id}:OPEN_RELEASE_ECONOMICS_BAD_STATUS"
                )

            if (
                row["release_analysis_status"]
                == RELEASE_ANALYSIS_NOT_APPLICABLE
            ):
                errors.append(
                    f"{asset_id}:OPEN_RELEASE_NOT_APPLICABLE"
                )

        if (
            row["release_analysis_status"]
            == RELEASE_ANALYSIS_READY
        ):
            if (
                row["position_status"]
                != POSITION_OPEN_OWNED
            ):
                errors.append(
                    f"{asset_id}:RELEASE_READY_NOT_OPEN"
                )

            if (
                row["release_analysis_quality"]
                != QUALITY_READY
            ):
                errors.append(
                    f"{asset_id}:RELEASE_READY_BAD_QUALITY"
                )

            if (
                row["release_protected_attribute"]
                is not False
            ):
                errors.append(
                    f"{asset_id}:RELEASE_READY_PROTECTED"
                )

            if (
                row["release_candidate_level"]
                is None
                or row[
                    "release_candidate_breed_count"
                ] is None
            ):
                errors.append(
                    f"{asset_id}:RELEASE_READY_MISSING_INPUTS"
                )

            if (
                row["release_capital_at_risk_weth"]
                is None
            ):
                errors.append(
                    f"{asset_id}:RELEASE_READY_NO_CAPITAL_BASIS"
                )

            if (
                row["acquisition_quality"]
                != QUALITY_READY
            ):
                errors.append(
                    f"{asset_id}:RELEASE_READY_BAD_ACQUISITION"
                )

        if (
            row["release_analysis_status"]
            == RELEASE_ANALYSIS_REVIEW_PROTECTED
        ):
            if (
                row["position_status"]
                != POSITION_OPEN_OWNED
            ):
                errors.append(
                    f"{asset_id}:PROTECTED_RELEASE_NOT_OPEN"
                )

            if (
                row["release_protected_attribute"]
                is not True
            ):
                errors.append(
                    f"{asset_id}:PROTECTED_RELEASE_FLAG_MISMATCH"
                )

            if (
                row["release_analysis_quality"]
                != QUALITY_REVIEW
            ):
                errors.append(
                    f"{asset_id}:PROTECTED_RELEASE_BAD_QUALITY"
                )

        if (
            row["release_analysis_status"]
            == RELEASE_ANALYSIS_REVIEW_NO_COST
        ):
            if (
                row["position_status"]
                != POSITION_OPEN_OWNED
            ):
                errors.append(
                    f"{asset_id}:NO_COST_RELEASE_NOT_OPEN"
                )

            if (
                row["release_protected_attribute"]
                is not False
            ):
                errors.append(
                    f"{asset_id}:NO_COST_RELEASE_PROTECTED"
                )

            if (
                row["release_capital_at_risk_weth"]
                is not None
            ):
                errors.append(
                    f"{asset_id}:NO_COST_RELEASE_HAS_CAPITAL"
                )

            if (
                row["release_analysis_quality"]
                != QUALITY_REVIEW
            ):
                errors.append(
                    f"{asset_id}:NO_COST_RELEASE_BAD_QUALITY"
                )

        if (
            row["release_analysis_status"]
            == RELEASE_ANALYSIS_REVIEW_MISSING_INPUTS
        ):
            if (
                row["position_status"]
                != POSITION_OPEN_OWNED
            ):
                errors.append(
                    f"{asset_id}:MISSING_INPUT_RELEASE_NOT_OPEN"
                )

            if (
                row["release_analysis_quality"]
                != QUALITY_REVIEW
            ):
                errors.append(
                    f"{asset_id}:MISSING_INPUT_RELEASE_BAD_QUALITY"
                )

        if (
            row["release_capital_at_risk_weth"]
            is not None
        ):
            acquisition_cost = decimal_or_none(
                row["acquisition_cost"]
            )

            if (
                acquisition_cost is None
                or row["acquisition_quality"]
                != QUALITY_READY
            ):
                errors.append(
                    f"{asset_id}:RELEASE_CAPITAL_WITHOUT_PROVEN_COST"
                )

            elif (
                row["release_capital_at_risk_weth"]
                != acquisition_cost
            ):
                errors.append(
                    f"{asset_id}:RELEASE_CAPITAL_COST_MISMATCH"
                )

        if (
            row["release_expected_recovery_weth"]
            is not None
        ):
            errors.append(
                f"{asset_id}:UNSUPPORTED_RELEASE_RECOVERY_VALUE"
            )

        if (
            row["release_expected_pl_weth"]
            is not None
        ):
            errors.append(
                f"{asset_id}:UNSUPPORTED_RELEASE_PL_VALUE"
            )


        valid_strategy_statuses = {
            MARKETPLACE_STRATEGY_HOLD_PROTECTED,
            MARKETPLACE_STRATEGY_REVIEW_EXIT_OPTIONS,
            MARKETPLACE_STRATEGY_HOLD_INSUFFICIENT_DATA,
            MARKETPLACE_STRATEGY_NOT_APPLICABLE,
        }

        valid_strategy_actions = {
            MARKETPLACE_ACTION_HOLD,
            MARKETPLACE_ACTION_REVIEW,
            MARKETPLACE_ACTION_NONE,
        }

        strategy_status = (
            row["marketplace_strategy_status"]
        )

        strategy_action = (
            row["marketplace_strategy_action"]
        )

        if (
            strategy_status
            not in valid_strategy_statuses
        ):
            errors.append(
                f"{asset_id}:INVALID_MARKETPLACE_STRATEGY_STATUS"
            )

        if (
            strategy_action
            not in valid_strategy_actions
        ):
            errors.append(
                f"{asset_id}:INVALID_MARKETPLACE_STRATEGY_ACTION"
            )

        if (
            strategy_status
            == MARKETPLACE_STRATEGY_NOT_APPLICABLE
        ):
            if (
                position_status
                == POSITION_OPEN_OWNED
            ):
                errors.append(
                    f"{asset_id}:OPEN_STRATEGY_NOT_APPLICABLE"
                )

            if (
                strategy_action
                != MARKETPLACE_ACTION_NONE
            ):
                errors.append(
                    f"{asset_id}:NOT_APPLICABLE_ACTION_MISMATCH"
                )

            if (
                row["marketplace_strategy_quality"]
                != QUALITY_READY
            ):
                errors.append(
                    f"{asset_id}:NOT_APPLICABLE_STRATEGY_BAD_QUALITY"
                )

            if (
                row[
                    "marketplace_strategy_requires_live_price"
                ]
                is not False
            ):
                errors.append(
                    f"{asset_id}:CLOSED_STRATEGY_REQUIRES_PRICE"
                )

            if (
                row[
                    "marketplace_strategy_requires_release_recovery_model"
                ]
                is not False
            ):
                errors.append(
                    f"{asset_id}:CLOSED_STRATEGY_REQUIRES_RECOVERY"
                )

        if (
            strategy_status
            == MARKETPLACE_STRATEGY_HOLD_PROTECTED
        ):
            if (
                position_status
                != POSITION_OPEN_OWNED
            ):
                errors.append(
                    f"{asset_id}:PROTECTED_STRATEGY_NOT_OPEN"
                )

            if (
                strategy_action
                != MARKETPLACE_ACTION_HOLD
            ):
                errors.append(
                    f"{asset_id}:PROTECTED_STRATEGY_NOT_HOLD"
                )

            if (
                row[
                    "release_protected_attribute"
                ]
                is not True
            ):
                errors.append(
                    f"{asset_id}:PROTECTED_STRATEGY_FLAG_MISMATCH"
                )

            if (
                row["marketplace_strategy_quality"]
                != QUALITY_READY
            ):
                errors.append(
                    f"{asset_id}:PROTECTED_STRATEGY_BAD_QUALITY"
                )

            if (
                row["marketplace_strategy_reason"]
                != "COLLECTIBLE_OR_EVOLVED_SAFEGUARD"
            ):
                errors.append(
                    f"{asset_id}:PROTECTED_STRATEGY_BAD_REASON"
                )

        if (
            strategy_status
            == MARKETPLACE_STRATEGY_REVIEW_EXIT_OPTIONS
        ):
            if (
                position_status
                != POSITION_OPEN_OWNED
            ):
                errors.append(
                    f"{asset_id}:EXIT_REVIEW_NOT_OPEN"
                )

            if (
                strategy_action
                != MARKETPLACE_ACTION_REVIEW
            ):
                errors.append(
                    f"{asset_id}:EXIT_REVIEW_ACTION_MISMATCH"
                )

            if (
                row["resale_status"]
                != RESALE_STATUS_READY
            ):
                errors.append(
                    f"{asset_id}:EXIT_REVIEW_RESALE_NOT_READY"
                )

            if (
                row["release_analysis_status"]
                != RELEASE_ANALYSIS_READY
            ):
                errors.append(
                    f"{asset_id}:EXIT_REVIEW_RELEASE_NOT_READY"
                )

            if (
                row[
                    "release_protected_attribute"
                ]
                is not False
            ):
                errors.append(
                    f"{asset_id}:EXIT_REVIEW_PROTECTED"
                )

            if (
                row["break_even_gross_price"]
                is None
            ):
                errors.append(
                    f"{asset_id}:EXIT_REVIEW_NO_BREAK_EVEN"
                )

            if (
                row[
                    "release_capital_at_risk_weth"
                ]
                is None
            ):
                errors.append(
                    f"{asset_id}:EXIT_REVIEW_NO_CAPITAL_BASIS"
                )

            if (
                row[
                    "marketplace_strategy_requires_live_price"
                ]
                is not True
            ):
                errors.append(
                    f"{asset_id}:EXIT_REVIEW_PRICE_FLAG_MISSING"
                )

            if (
                row[
                    "marketplace_strategy_requires_release_recovery_model"
                ]
                is not True
            ):
                errors.append(
                    f"{asset_id}:EXIT_REVIEW_RECOVERY_FLAG_MISSING"
                )

            if (
                row["marketplace_strategy_quality"]
                != QUALITY_REVIEW
            ):
                errors.append(
                    f"{asset_id}:EXIT_REVIEW_BAD_QUALITY"
                )

        if (
            strategy_status
            == MARKETPLACE_STRATEGY_HOLD_INSUFFICIENT_DATA
        ):
            if (
                position_status
                != POSITION_OPEN_OWNED
            ):
                errors.append(
                    f"{asset_id}:INSUFFICIENT_STRATEGY_NOT_OPEN"
                )

            if (
                strategy_action
                != MARKETPLACE_ACTION_HOLD
            ):
                errors.append(
                    f"{asset_id}:INSUFFICIENT_STRATEGY_NOT_HOLD"
                )

            if (
                row[
                    "release_protected_attribute"
                ]
                is True
            ):
                errors.append(
                    f"{asset_id}:INSUFFICIENT_STRATEGY_PROTECTED"
                )

            if (
                row["marketplace_strategy_quality"]
                != QUALITY_REVIEW
            ):
                errors.append(
                    f"{asset_id}:INSUFFICIENT_STRATEGY_BAD_QUALITY"
                )

            if (
                row[
                    "marketplace_strategy_requires_live_price"
                ]
                is not False
            ):
                errors.append(
                    f"{asset_id}:INSUFFICIENT_STRATEGY_PRICE_FLAG"
                )

            if (
                row[
                    "marketplace_strategy_requires_release_recovery_model"
                ]
                is not False
            ):
                errors.append(
                    f"{asset_id}:INSUFFICIENT_STRATEGY_RECOVERY_FLAG"
                )



        if (
            row["model_version"]
            != MARKETPLACE_INVENTORY_MODEL_VERSION
        ):
            errors.append(
                f"{asset_id}:MODEL_VERSION_MISMATCH"
            )

    capital = summarize_capital_utilization(
        inventory
    )

    open_count = (
        capital["open_position_count"]
    )

    proven_count = (
        capital["proven_cost_position_count"]
    )

    if proven_count > open_count:
        errors.append(
            "CAPITAL_PROVEN_COUNT_EXCEEDS_OPEN_COUNT"
        )

    expected_coverage_ratio = (
        Decimal(proven_count)
        / Decimal(open_count)
        if open_count
        else Decimal("0")
    )

    if (
        capital["cost_basis_coverage_ratio"]
        != expected_coverage_ratio
    ):
        errors.append(
            "CAPITAL_COVERAGE_RATIO_MISMATCH"
        )

    expected_coverage_status = (
        "PARTIAL_COVERAGE"
        if proven_count < open_count
        else "FULL_COVERAGE"
    )

    if (
        capital["capital_coverage_status"]
        != expected_coverage_status
    ):
        errors.append(
            "CAPITAL_COVERAGE_STATUS_MISMATCH"
        )

    proven_open_capital = (
        capital["proven_open_capital_weth"]
    )

    protected_capital = (
        capital["protected_capital_weth"]
    )

    release_ready_capital = (
        capital["release_ready_capital_weth"]
    )

    capital_days = (
        capital["capital_days_weth"]
    )

    weighted_age = (
        capital["capital_weighted_age_days"]
    )

    for metric_name, metric_value in (
        (
            "PROVEN_OPEN_CAPITAL",
            proven_open_capital,
        ),
        (
            "PROTECTED_CAPITAL",
            protected_capital,
        ),
        (
            "RELEASE_READY_CAPITAL",
            release_ready_capital,
        ),
        (
            "CAPITAL_DAYS",
            capital_days,
        ),
    ):
        if metric_value < Decimal("0"):
            errors.append(
                f"{metric_name}_NEGATIVE"
            )

    if (
        protected_capital
        > proven_open_capital
    ):
        errors.append(
            "PROTECTED_CAPITAL_EXCEEDS_PROVEN_CAPITAL"
        )

    if (
        release_ready_capital
        > proven_open_capital
    ):
        errors.append(
            "RELEASE_READY_CAPITAL_EXCEEDS_PROVEN_CAPITAL"
        )

    classified_capital = (
        protected_capital
        + release_ready_capital
    )

    if (
        classified_capital
        > proven_open_capital
    ):
        errors.append(
            "CLASSIFIED_CAPITAL_EXCEEDS_PROVEN_CAPITAL"
        )

    proven_rows = [
        row
        for row in inventory
        if (
            row["position_status"]
            == POSITION_OPEN_OWNED
            and row["acquisition_cost"]
            is not None
            and row["acquisition_quality"]
            == QUALITY_READY
        )
    ]

    classified_rows = [
        row
        for row in proven_rows
        if (
            row["release_analysis_status"]
            in {
                RELEASE_ANALYSIS_READY,
                RELEASE_ANALYSIS_REVIEW_PROTECTED,
            }
        )
    ]

    if (
        len(classified_rows)
        == len(proven_rows)
        and classified_capital
        != proven_open_capital
    ):
        errors.append(
            "CLASSIFIED_CAPITAL_RECONCILIATION_MISMATCH"
        )

    if proven_open_capital == Decimal("0"):
        if weighted_age is not None:
            errors.append(
                "ZERO_CAPITAL_HAS_WEIGHTED_AGE"
            )

    else:
        holding_rows = [
            row
            for row in proven_rows
            if row["holding_days"] is not None
        ]

        if (
            len(holding_rows)
            == len(proven_rows)
        ):
            expected_weighted_age = (
                capital_days
                / proven_open_capital
            )

            if weighted_age is None:
                errors.append(
                    "CAPITAL_WEIGHTED_AGE_MISSING"
                )

            elif (
                abs(
                    weighted_age
                    - expected_weighted_age
                )
                > Decimal(
                    "0.000000000000000001"
                )
            ):
                errors.append(
                    "CAPITAL_WEIGHTED_AGE_MISMATCH"
                )

        elif weighted_age is not None:
            errors.append(
                "INCOMPLETE_HOLDING_COVERAGE_HAS_WEIGHTED_AGE"
            )

    protected_ratio = (
        capital["protected_capital_ratio"]
    )

    release_ready_ratio = (
        capital["release_ready_capital_ratio"]
    )

    if proven_open_capital != Decimal("0"):
        expected_protected_ratio = (
            protected_capital
            / proven_open_capital
        )

        expected_release_ready_ratio = (
            release_ready_capital
            / proven_open_capital
        )

        if (
            protected_ratio
            != expected_protected_ratio
        ):
            errors.append(
                "PROTECTED_CAPITAL_RATIO_MISMATCH"
            )

        if (
            release_ready_ratio
            != expected_release_ready_ratio
        ):
            errors.append(
                "RELEASE_READY_CAPITAL_RATIO_MISMATCH"
            )

    return {
        "status": (
            "PASS"
            if not errors
            else "FAIL"
        ),
        "inventory_count": len(inventory),
        "unique_asset_count": len(
            set(asset_ids)
        ),
        "error_count": len(errors),
        "errors": errors,
    }



def print_current_inventory_report(
    inventory,
):
    print("=" * 100)
    print(
        "AXIEOS V0.10 — CURRENT MARKETPLACE "
        "AXIE INVENTORY"
    )
    print("=" * 100)

    print(
        "Model version:",
        MARKETPLACE_INVENTORY_MODEL_VERSION,
    )
    print(
        "Canonical Axies:",
        len(inventory),
    )

    print()
    print("POSITION STATUS COUNTS")
    print("-" * 100)

    status_counts = Counter(
        row["position_status"]
        for row in inventory
    )

    for status in sorted(status_counts):
        print(
            f"{status}: "
            f"{status_counts[status]}"
        )

    print()
    print("DATA QUALITY COUNTS")
    print("-" * 100)

    quality_counts = Counter(
        row["data_quality"]
        for row in inventory
    )

    for quality in sorted(quality_counts):
        print(
            f"{quality}: "
            f"{quality_counts[quality]}"
        )

    print()
    print("OWNERSHIP START EVIDENCE")
    print("-" * 100)

    ownership_start_quality_counts = Counter(
        row["ownership_start_quality"]
        for row in inventory
    )

    for quality in sorted(
        ownership_start_quality_counts
    ):
        print(
            f"{quality}: "
            f"{ownership_start_quality_counts[quality]}"
        )

    known_ownership_start_count = sum(
        1
        for row in inventory
        if row[
            "ownership_start_datetime"
        ] is not None
    )

    print(
        "Known ownership start datetime:",
        known_ownership_start_count,
    )




    print()
    print("ACQUISITION EVIDENCE")
    print("-" * 100)

    acquisition_quality_counts = Counter(
        row["acquisition_quality"]
        for row in inventory
    )

    for quality in sorted(
        acquisition_quality_counts
    ):
        print(
            f"{quality}: "
            f"{acquisition_quality_counts[quality]}"
        )

    known_cost_count = sum(
        1
        for row in inventory
        if row["acquisition_cost"] is not None
    )

    known_datetime_count = sum(
        1
        for row in inventory
        if row[
            "acquisition_datetime"
        ] is not None
    )

    known_txhash_count = sum(
        1
        for row in inventory
        if row[
            "acquisition_txhash"
        ] is not None
    )

    print(
        "Known acquisition cost:",
        known_cost_count,
    )
    print(
        "Known acquisition datetime:",
        known_datetime_count,
    )
    print(
        "Known acquisition txhash:",
        known_txhash_count,
    )




    print()
    print("LISTING EVIDENCE")
    print("-" * 100)

    listing_status_counts = Counter(
        row["listing_status"]
        for row in inventory
    )

    for status in sorted(
        listing_status_counts
    ):
        print(
            f"{status}: "
            f"{listing_status_counts[status]}"
        )

    listing_history_count = sum(
        1
        for row in inventory
        if row[
            "last_listing_datetime"
        ] is not None
    )

    print(
        "Positions with listing history:",
        listing_history_count,
    )




    print()
    print("SALE EVIDENCE")
    print("-" * 100)

    sale_status_counts = Counter(
        row["sale_status"]
        for row in inventory
    )

    for status in sorted(
        sale_status_counts
    ):
        print(
            f"{status}: "
            f"{sale_status_counts[status]}"
        )

    known_sale_datetime_count = sum(
        1
        for row in inventory
        if row["sale_datetime"] is not None
    )

    known_sale_txhash_count = sum(
        1
        for row in inventory
        if row["sale_txhash"] is not None
    )

    print(
        "Known sale datetime:",
        known_sale_datetime_count,
    )
    print(
        "Known sale txhash:",
        known_sale_txhash_count,
    )




    print()
    print("REALIZED ECONOMICS")
    print("-" * 100)

    realized_status_counts = Counter(
        row["realized_status"]
        for row in inventory
    )

    for status in sorted(
        realized_status_counts
    ):
        print(
            f"{status}: "
            f"{realized_status_counts[status]}"
        )

    realized_roi_count = sum(
        1
        for row in inventory
        if row["realized_roi"] is not None
    )

    realized_pl_count = sum(
        1
        for row in inventory
        if row["realized_pl"] is not None
    )

    print(
        "Positions with realized P/L:",
        realized_pl_count,
    )
    print(
        "Positions with realized ROI:",
        realized_roi_count,
    )





    print()
    print("UNREALIZED ECONOMICS")
    print("-" * 100)

    unrealized_status_counts = Counter(
        row["unrealized_status"]
        for row in inventory
    )

    for status in sorted(
        unrealized_status_counts
    ):
        print(
            f"{status}: "
            f"{unrealized_status_counts[status]}"
        )

    market_value_count = sum(
        1
        for row in inventory
        if row[
            "current_market_value"
        ] is not None
    )

    unrealized_pl_count = sum(
        1
        for row in inventory
        if row["unrealized_pl"] is not None
    )

    print(
        "Positions with current market value:",
        market_value_count,
    )
    print(
        "Positions with unrealized P/L:",
        unrealized_pl_count,
    )




    print()
    print("HOLDING PERIOD ANALYTICS")
    print("-" * 100)

    holding_status_counts = Counter(
        row["holding_status"]
        for row in inventory
    )

    for status in sorted(
        holding_status_counts
    ):
        print(
            f"{status}: "
            f"{holding_status_counts[status]}"
        )

    known_holding_count = sum(
        1
        for row in inventory
        if row["holding_days"] is not None
    )

    print(
        "Positions with computed holding period:",
        known_holding_count,
    )

    ready_holding_days = [
        row["holding_days"]
        for row in inventory
        if (
            row["holding_status"]
            == HOLDING_STATUS_READY
            and row["holding_days"] is not None
        )
    ]

    if ready_holding_days:
        print(
            "Average holding days:",
            round(
                sum(ready_holding_days)
                / len(ready_holding_days),
                2,
            ),
        )

        print(
            "Shortest holding days:",
            round(
                min(ready_holding_days),
                2,
            ),
        )

        print(
            "Longest holding days:",
            round(
                max(ready_holding_days),
                2,
            ),
        )



    print()
    print("RESALE / BREAK-EVEN ANALYTICS")
    print("-" * 100)

    resale_status_counts = Counter(
        row["resale_status"]
        for row in inventory
    )

    for status in sorted(
        resale_status_counts
    ):
        print(
            f"{status}: "
            f"{resale_status_counts[status]}"
        )

    break_even_count = sum(
        1
        for row in inventory
        if row[
            "break_even_gross_price"
        ] is not None
    )

    print(
        "Fee-rate assumption:",
        ASSUMED_MARKETPLACE_FEE_RATE
        * Decimal("100"),
        "%",
    )

    print(
        "Open positions with break-even:",
        break_even_count,
    )



    print()
    print("RELEASE-CANDIDATE ECONOMICS")
    print("-" * 100)

    release_status_counts = Counter(
        row["release_analysis_status"]
        for row in inventory
    )

    for status in sorted(
        release_status_counts
    ):
        print(
            f"{status}: "
            f"{release_status_counts[status]}"
        )

    protected_count = sum(
        1
        for row in inventory
        if (
            row["position_status"]
            == POSITION_OPEN_OWNED
            and row[
                "release_protected_attribute"
            ] is True
        )
    )

    capital_rows = [
        row
        for row in inventory
        if (
            row[
                "release_capital_at_risk_weth"
            ] is not None
        )
    ]

    total_capital_at_risk = sum(
        (
            row[
                "release_capital_at_risk_weth"
            ]
            for row in capital_rows
        ),
        Decimal("0"),
    )

    print(
        "Open protected-attribute Axies:",
        protected_count,
    )

    print(
        "Open positions with proven capital basis:",
        len(capital_rows),
    )

    print(
        "Total proven capital at risk:",
        total_capital_at_risk,
        "WETH",
    )

    print(
        "Expected recovery values:",
        sum(
            1
            for row in inventory
            if row[
                "release_expected_recovery_weth"
            ] is not None
        ),
    )

    print(
        "Expected release P/L values:",
        sum(
            1
            for row in inventory
            if row[
                "release_expected_pl_weth"
            ] is not None
        ),
    )



    capital = summarize_capital_utilization(
        inventory
    )

    print()
    print("CAPITAL UTILIZATION")
    print("-" * 100)

    print(
        "Coverage status:",
        capital["capital_coverage_status"],
    )

    print(
        "Open positions:",
        capital["open_position_count"],
    )

    print(
        "Open positions with proven cost:",
        capital["proven_cost_position_count"],
    )

    print(
        "Cost-basis coverage:",
        (
            capital["cost_basis_coverage_ratio"]
            * Decimal("100")
        ),
        "%",
    )

    print(
        "Proven open capital:",
        capital["proven_open_capital_weth"],
        "WETH",
    )

    print(
        "Capital-days exposure:",
        capital["capital_days_weth"],
        "WETH-days",
    )

    print(
        "Capital-weighted average age:",
        capital["capital_weighted_age_days"],
        "days",
    )

    print(
        "Protected-attribute capital:",
        capital["protected_capital_weth"],
        "WETH",
    )

    print(
        "Protected capital share:",
        (
            capital["protected_capital_ratio"]
            * Decimal("100")
            if capital[
                "protected_capital_ratio"
            ] is not None
            else None
        ),
        "%",
    )

    print(
        "Release-analysis-ready capital:",
        capital[
            "release_ready_capital_weth"
        ],
        "WETH",
    )

    print(
        "Release-analysis-ready share:",
        (
            capital[
                "release_ready_capital_ratio"
            ]
            * Decimal("100")
            if capital[
                "release_ready_capital_ratio"
            ] is not None
            else None
        ),
        "%",
    )



    print()
    print("MARKETPLACE STRATEGY")
    print("-" * 100)

    strategy_status_counts = Counter(
        row["marketplace_strategy_status"]
        for row in inventory
    )

    for status in sorted(
        strategy_status_counts
    ):
        print(
            f"{status}: "
            f"{strategy_status_counts[status]}"
        )

    strategy_action_counts = Counter(
        row["marketplace_strategy_action"]
        for row in inventory
    )

    print()
    print("Strategy actions:")

    for action in sorted(
        strategy_action_counts
    ):
        print(
            f"  {action}: "
            f"{strategy_action_counts[action]}"
        )

    exit_review_rows = [
        row
        for row in inventory
        if (
            row["marketplace_strategy_status"]
            == MARKETPLACE_STRATEGY_REVIEW_EXIT_OPTIONS
        )
    ]

    exit_review_capital = sum(
        (
            decimal_or_none(
                row["acquisition_cost"]
            )
            for row in exit_review_rows
        ),
        Decimal("0"),
    )

    print(
        "Exit-option reviews:",
        len(exit_review_rows),
    )

    print(
        "Capital represented by exit reviews:",
        exit_review_capital,
        "WETH",
    )

    print(
        "Automatic SELL decisions:",
        0,
    )

    print(
        "Automatic RELEASE decisions:",
        0,
    )




    print()
    print("POSITION DETAILS")
    print("-" * 100)

    for row in inventory:
        print(
            f"Axie #{row['asset_id']} | "
            f"{row['position_status']} | "
            f"source={row['status_source']} | "
            f"ownership="
            f"{row['ownership_status']} | "
            f"quality={row['data_quality']}"
        )


def main():
    connection = (
        connect_inventory_database()
    )

    try:
        inventory = (
            build_current_marketplace_axie_inventory(
                connection
            )
        )

        validation = (
            validate_current_marketplace_axie_inventory(
                inventory
            )
        )

        print_current_inventory_report(
            inventory
        )

        print()
        print("INVENTORY VALIDATION")
        print("-" * 100)
        print(
            "Status:",
            validation["status"],
        )
        print(
            "Inventory count:",
            validation["inventory_count"],
        )
        print(
            "Unique assets:",
            validation["unique_asset_count"],
        )
        print(
            "Errors:",
            validation["error_count"],
        )

        for error in validation["errors"]:
            print(
                " -",
                error,
            )

    finally:
        connection.close()


if __name__ == "__main__":
    main()