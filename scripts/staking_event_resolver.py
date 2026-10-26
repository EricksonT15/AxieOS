import sqlite3
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "blockchain"
    / "database"
    / "axieos.db"
)


ZERO_ADDRESS = (
    "0x0000000000000000000000000000000000000000"
)


ASSET_SYMBOLS = {
    "Axie Infinity Shard": "AXS",
    "Bonded AXS": "bAXS",
}


METHOD_EVENT_TYPES = {
    "claimReward": "CLAIM",
    "claimRewards": "CLAIM",
    "claimPendingRewards": "CLAIM",
    "stake": "STAKE",
    "unstake": "UNSTAKE",
    "restakeRewards": "RESTAKE_REWARD",
}



PROVEN_REWARD_SOURCE_ADDRESSES = {
    (
        "0x21d18ae443f86a755ba47d6241c49c5bcf070bbf"
    ): "BOUNTY",
    (
        "0x8a79d5d29208605426cabb43a4dfc4ca31baebd0"
    ): "TERRARIUMS",
}


def normalize_address(address):
    if address is None:
        return None

    return address.lower()


def connect_read_only():
    return sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )


def load_accounting_candidates(conn):
    conn.row_factory = sqlite3.Row

    return conn.execute(
        """
        SELECT
            accounting_key,
            txhash,
            datetime,
            classification,
            asset_name,
            quantity,
            direction,
            counterparty_role,
            accounting_status
        FROM blockchain_accounting_records
        WHERE asset_name IN (
            'Axie Infinity Shard',
            'Bonded AXS'
        )
          AND classification IN (
            'STAKING_OR_REWARD',
            'MINT_OR_CLAIM'
        )
          AND accounting_status = 'READY'
        ORDER BY
            datetime,
            txhash,
            accounting_key
        """
    ).fetchall()


def load_user_owned_addresses(conn):
    rows = conn.execute(
        """
        SELECT address
        FROM ronin_wallet_registry
        WHERE ownership_type = 'USER_OWNED'
        """
    ).fetchall()

    return {
        normalize_address(row[0])
        for row in rows
    }


def load_staking_addresses(conn):
    rows = conn.execute(
        """
        SELECT address
        FROM ronin_wallet_registry
        WHERE wallet_role = 'STAKING'
        """
    ).fetchall()

    return {
        normalize_address(row[0])
        for row in rows
    }


def load_blockchain_evidence(conn):
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT
            txhash,
            method,
            from_address,
            to_address,
            value_in,
            value_out,
            status
        FROM blockchain_transactions
        WHERE txhash IN (
            SELECT txhash
            FROM blockchain_accounting_records
            WHERE asset_name IN (
                'Axie Infinity Shard',
                'Bonded AXS'
            )
              AND classification IN (
                'STAKING_OR_REWARD',
                'MINT_OR_CLAIM'
            )
              AND accounting_status = 'READY'
        )
        ORDER BY
            txhash,
            id
        """
    ).fetchall()

    evidence = {}

    for row in rows:
        txhash = row["txhash"]

        if txhash not in evidence:
            evidence[txhash] = {
                "row_count": 0,
                "methods": set(),
                "legs": [],
            }

        evidence[txhash]["row_count"] += 1

        if row["method"]:
            evidence[txhash]["methods"].add(
                row["method"]
            )

        evidence[txhash]["legs"].append(
            {
                "from_address": normalize_address(
                    row["from_address"]
                ),
                "to_address": normalize_address(
                    row["to_address"]
                ),
                "value_in": row["value_in"],
                "value_out": row["value_out"],
                "status": row["status"],
            }
        )

    return evidence


def resolve_method(blockchain_evidence):
    if blockchain_evidence is None:
        return None

    methods = blockchain_evidence["methods"]

    if len(methods) != 1:
        return None

    return next(iter(methods))


def has_leg(
    blockchain_evidence,
    from_addresses=None,
    to_addresses=None,
):
    if blockchain_evidence is None:
        return False

    for leg in blockchain_evidence["legs"]:
        from_address = leg["from_address"]
        to_address = leg["to_address"]

        if (
            from_addresses is not None
            and from_address not in from_addresses
        ):
            continue

        if (
            to_addresses is not None
            and to_address not in to_addresses
        ):
            continue

        return True

    return False


def infer_event_type(
    accounting_row,
    blockchain_evidence,
    user_addresses,
    staking_addresses,
):
    token = ASSET_SYMBOLS.get(
        accounting_row["asset_name"]
    )

    direction = accounting_row["direction"]

    zero_addresses = {
        ZERO_ADDRESS,
    }

    if token == "bAXS":
        if (
            direction == "IN"
            and has_leg(
                blockchain_evidence,
                from_addresses=zero_addresses,
                to_addresses=user_addresses,
            )
        ):
            return "UNSTAKE"

        if (
            direction == "IN"
            and has_leg(
                blockchain_evidence,
                from_addresses=staking_addresses,
                to_addresses=user_addresses,
            )
        ):
            return "CLAIM"

        if (
            direction == "OUT"
            and has_leg(
                blockchain_evidence,
                from_addresses=user_addresses,
                to_addresses=zero_addresses,
            )
        ):
            return "STAKE"

    if token == "AXS":
        reward_in = has_leg(
            blockchain_evidence,
            from_addresses=staking_addresses,
            to_addresses=user_addresses,
        )

        stake_out = has_leg(
            blockchain_evidence,
            from_addresses=user_addresses,
            to_addresses=staking_addresses,
        )

        if (
            direction == "IN"
            and reward_in
            and stake_out
        ):
            return "RESTAKE_REWARD"

        if (
            direction == "IN"
            and reward_in
        ):
            return "CLAIM"

        if (
            direction == "OUT"
            and stake_out
        ):
            return "STAKE"

    return "UNRESOLVED"


def find_inbound_staking_addresses(
    blockchain_evidence,
    user_addresses,
    staking_addresses,
):
    if blockchain_evidence is None:
        return set()

    addresses = set()

    for leg in blockchain_evidence["legs"]:
        from_address = leg["from_address"]
        to_address = leg["to_address"]

        if (
            from_address in staking_addresses
            and to_address in user_addresses
        ):
            addresses.add(from_address)

    return addresses


def find_outbound_staking_addresses(
    blockchain_evidence,
    user_addresses,
    staking_addresses,
):
    if blockchain_evidence is None:
        return set()

    addresses = set()

    for leg in blockchain_evidence["legs"]:
        from_address = leg["from_address"]
        to_address = leg["to_address"]

        if (
            from_address in user_addresses
            and to_address in staking_addresses
        ):
            addresses.add(to_address)

    return addresses


def resolve_economic_source(
    event_type,
    token,
    blockchain_evidence,
    user_addresses,
    staking_addresses,
):
    if (
        token == "bAXS"
        and event_type == "CLAIM"
    ):
        addresses = find_inbound_staking_addresses(
            blockchain_evidence,
            user_addresses,
            staking_addresses,
        )

        if len(addresses) == 1:
            address = next(iter(addresses))

            source = (
                PROVEN_REWARD_SOURCE_ADDRESSES.get(
                    address
                )
            )

            if source is not None:
                return (
                    source,
                    address,
                    "PROVEN_ADDRESS",
                )

            return (
                "BAXS_STAKING_REWARD",
                address,
                "STAKING_ROLE",
            )

        return (
            "BAXS_STAKING_REWARD",
            None,
            "TOKEN_DOMAIN",
        )

    if (
        token == "AXS"
        and event_type
        in {
            "CLAIM",
            "RESTAKE_REWARD",
        }
    ):
        addresses = find_inbound_staking_addresses(
            blockchain_evidence,
            user_addresses,
            staking_addresses,
        )

        address = None

        if len(addresses) == 1:
            address = next(iter(addresses))

        return (
            "AXS_STAKING",
            address,
            "STAKING_ROLE",
        )

    if (
        token == "AXS"
        and event_type == "STAKE"
    ):
        addresses = find_outbound_staking_addresses(
            blockchain_evidence,
            user_addresses,
            staking_addresses,
        )

        address = None

        if len(addresses) == 1:
            address = next(iter(addresses))

        return (
            "AXS_STAKING",
            address,
            "STAKING_ROLE",
        )

    if (
        token == "bAXS"
        and event_type
        in {
            "STAKE",
            "UNSTAKE",
        }
    ):
        return (
            "BAXS_STAKING",
            None,
            "TOKEN_DOMAIN",
        )

    return (
        "UNRESOLVED",
        None,
        "UNRESOLVED",
    )


def normalize_event(
    accounting_row,
    blockchain_evidence,
    user_addresses,
    staking_addresses,
):
    method = resolve_method(
        blockchain_evidence
    )

    explicit_event_type = (
        METHOD_EVENT_TYPES.get(method)
    )

    if explicit_event_type is not None:
        event_type = explicit_event_type
        confidence = "HIGH"
        resolution_basis = "EXPLICIT_METHOD"

    else:
        event_type = infer_event_type(
            accounting_row,
            blockchain_evidence,
            user_addresses,
            staking_addresses,
        )

        if event_type == "UNRESOLVED":
            confidence = "UNRESOLVED"
            resolution_basis = "UNRESOLVED"
        else:
            confidence = "MEDIUM"
            resolution_basis = "FLOW_PATTERN"

    token = ASSET_SYMBOLS.get(
        accounting_row["asset_name"],
        accounting_row["asset_name"],
    )

    (
        economic_source,
        source_address,
        source_basis,
    ) = resolve_economic_source(
        event_type,
        token,
        blockchain_evidence,
        user_addresses,
        staking_addresses,
    )

    blockchain_row_count = 0

    if blockchain_evidence is not None:
        blockchain_row_count = (
            blockchain_evidence["row_count"]
        )

    return {
        "accounting_key": (
            accounting_row["accounting_key"]
        ),
        "txhash": accounting_row["txhash"],
        "datetime": accounting_row["datetime"],
        "token": token,
        "quantity": accounting_row["quantity"],
        "direction": accounting_row["direction"],
        "classification": (
            accounting_row["classification"]
        ),
        "method": method,
        "event_type": event_type,
        "confidence": confidence,
        "resolution_basis": resolution_basis,
        "economic_source": economic_source,
        "source_address": source_address,
        "source_basis": source_basis,
        "blockchain_row_count": (
            blockchain_row_count
        ),
    }


def print_event(event):
    print(
        f"{event['datetime']} | "
        f"{event['token']} | "
        f"{event['quantity']} | "
        f"{event['direction']} | "
        f"{event['event_type']} | "
        f"source={event['economic_source']} | "
        f"method={event['method']} | "
        f"confidence={event['confidence']} | "
        f"basis={event['resolution_basis']} | "
        f"source_basis={event['source_basis']} | "
        f"chain_rows={event['blockchain_row_count']}"
    )

    print(
        f"  txhash={event['txhash']}"
    )

    if event["source_address"] is not None:
        print(
            f"  source_address="
            f"{event['source_address']}"
        )


def main():
    conn = connect_read_only()

    try:
        accounting_rows = (
            load_accounting_candidates(conn)
        )

        user_addresses = (
            load_user_owned_addresses(conn)
        )

        staking_addresses = (
            load_staking_addresses(conn)
        )

        blockchain_evidence = (
            load_blockchain_evidence(conn)
        )

        events = []

        for row in accounting_rows:
            events.append(
                normalize_event(
                    row,
                    blockchain_evidence.get(
                        row["txhash"]
                    ),
                    user_addresses,
                    staking_addresses,
                )
            )

        explicit = [
            event
            for event in events
            if event["resolution_basis"]
            == "EXPLICIT_METHOD"
        ]

        inferred = [
            event
            for event in events
            if event["resolution_basis"]
            == "FLOW_PATTERN"
        ]

        unresolved = [
            event
            for event in events
            if event["event_type"]
            == "UNRESOLVED"
        ]

        multi_row = {
            event["txhash"]
            for event in events
            if event["blockchain_row_count"] > 1
        }

        print(
            "AXIEOS V0.12 STAKING EVENT RESOLVER"
        )
        print()

        print(
            "Candidate accounting rows:",
            len(events),
        )

        print(
            "Explicit-method resolved:",
            len(explicit),
        )

        print(
            "Flow-pattern inferred:",
            len(inferred),
        )

        print(
            "Unresolved:",
            len(unresolved),
        )

        print(
            "Unique txhashes with multi-row "
            "blockchain evidence:",
            len(multi_row),
        )

        print()
        print("NORMALIZED EVENTS")
        print()

        for event in events:
            print_event(event)

    finally:
        conn.close()


if __name__ == "__main__":
    main()