import sqlite3
from pathlib import Path


# ============================================================
# AXIEOS - NIGHTMARE ACQUISITION-COST RECOVERY
# ============================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "blockchain" / "database" / "axieos.db"

STATUS_COST_RECOVERED = "COST_RECOVERED"
STATUS_COST_REVIEW = "COST_REVIEW"
STATUS_COST_NOT_RECOVERED = "COST_NOT_RECOVERED"
STATUS_HISTORY_UNRESOLVED = "HISTORY_UNRESOLVED"


def connect_read_only():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH.resolve()}"
        )

    db_uri = DB_PATH.resolve().as_uri() + "?mode=ro"

    conn = sqlite3.connect(
        db_uri,
        uri=True,
    )
    conn.row_factory = sqlite3.Row

    return conn


def load_owned_nightmares(cur):
    return cur.execute(
        """
        SELECT DISTINCT
            o.axie_id,
            o.axie_class,
            o.level,
            o.breed_count,
            o.acquisition_txhash,
            o.acquisition_datetime,
            o.acquisition_cost_weth,
            o.acquisition_source,
            o.wallet_address
        FROM gameplay_owned_axies o
        JOIN gameplay_axie_traits t
            ON t.axie_id = o.axie_id
        WHERE UPPER(o.ownership_status) = 'OWNED'
          AND UPPER(COALESCE(t.trait_type, '')) = 'COLLECTION'
          AND UPPER(COALESCE(t.trait_value, '')) = 'NIGHTMARE'
        ORDER BY CAST(o.axie_id AS INTEGER)
        """
    ).fetchall()


def load_accounting_matches(cur, axie_id):
    return cur.execute(
        """
        SELECT
            accounting_key,
            txhash,
            datetime,
            event_type,
            classification,
            asset_name,
            asset_token_id,
            asset_category,
            direction,
            payment_asset,
            gross_amount,
            marketplace_fee,
            net_amount,
            cost_basis,
            realized_pl,
            is_internal_transfer,
            accounting_status,
            accounting_version
        FROM blockchain_accounting_records
        WHERE CAST(asset_token_id AS TEXT) = ?
        ORDER BY datetime, accounting_key
        """,
        (str(axie_id),),
    ).fetchall()


def load_marketplace_matches(cur, axie_id):
    return cur.execute(
        """
        SELECT
            id,
            event_datetime,
            event_type,
            asset_type,
            asset_id,
            asset_name,
            quantity,
            amount,
            currency,
            related_bounty_task_id,
            notes
        FROM marketplace_events
        WHERE CAST(asset_id AS TEXT) = ?
        ORDER BY event_datetime, id
        """,
        (str(axie_id),),
    ).fetchall()


def load_blockchain_txhash_matches(cur, txhash):
    if not txhash:
        return []

    return cur.execute(
        """
        SELECT
            id,
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
            status
        FROM blockchain_transactions
        WHERE LOWER(COALESCE(txhash, '')) = LOWER(?)
        ORDER BY id
        """,
        (txhash,),
    ).fetchall()


def load_blockchain_axie_candidates(cur, axie_id):
    pattern = f"%{axie_id}%"

    return cur.execute(
        """
        SELECT
            id,
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
            status
        FROM blockchain_transactions
        WHERE CAST(COALESCE(token_collectibles, '') AS TEXT) LIKE ?
        ORDER BY datetime, id
        """,
        (pattern,),
    ).fetchall()


def classify_cost_status(
    axie,
    accounting_matches,
    marketplace_matches,
    blockchain_tx_matches,
    blockchain_axie_candidates,
):
    stored_cost = axie["acquisition_cost_weth"]
    ownership_start = axie["acquisition_datetime"]

    if stored_cost not in (None, ""):
        return STATUS_COST_RECOVERED

    candidate_evidence_count = (
        len(accounting_matches)
        + len(marketplace_matches)
        + len(blockchain_tx_matches)
        + len(blockchain_axie_candidates)
    )

    if candidate_evidence_count > 0:
        return STATUS_COST_REVIEW

    if ownership_start:
        return STATUS_COST_NOT_RECOVERED

    return STATUS_HISTORY_UNRESOLVED


def build_recovery_record(cur, axie):
    axie_id = str(axie["axie_id"])

    accounting_matches = load_accounting_matches(
        cur,
        axie_id,
    )

    marketplace_matches = load_marketplace_matches(
        cur,
        axie_id,
    )

    blockchain_tx_matches = load_blockchain_txhash_matches(
        cur,
        axie["acquisition_txhash"],
    )

    blockchain_axie_candidates = load_blockchain_axie_candidates(
        cur,
        axie_id,
    )

    status = classify_cost_status(
        axie=axie,
        accounting_matches=accounting_matches,
        marketplace_matches=marketplace_matches,
        blockchain_tx_matches=blockchain_tx_matches,
        blockchain_axie_candidates=blockchain_axie_candidates,
    )

    return {
        "axie_id": axie_id,
        "axie_class": axie["axie_class"],
        "level": axie["level"],
        "breed_count": axie["breed_count"],
        "ownership_start": axie["acquisition_datetime"],
        "ownership_source": axie["acquisition_source"],
        "stored_cost_weth": axie["acquisition_cost_weth"],
        "stored_txhash": axie["acquisition_txhash"],
        "accounting_matches": accounting_matches,
        "marketplace_matches": marketplace_matches,
        "blockchain_tx_matches": blockchain_tx_matches,
        "blockchain_axie_candidates": blockchain_axie_candidates,
        "status": status,
    }


def print_candidate_rows(title, rows):
    if not rows:
        return

    print()
    print(f"  {title}")

    for index, row in enumerate(rows, start=1):
        print(f"    Candidate {index}")

        for key in row.keys():
            value = row[key]

            if value not in (None, ""):
                print(f"      {key}: {value}")


def print_recovery_detail(record):
    print()
    print("-" * 110)

    print(f"Axie #{record['axie_id']}")
    print(f"  Class:                    {record['axie_class']}")
    print(f"  Level:                    {record['level']}")
    print(f"  Breed:                    {record['breed_count']}")
    print(f"  Ownership Start:          {record['ownership_start']}")
    print(f"  Ownership Source:         {record['ownership_source']}")
    print(f"  Stored Cost WETH:         {record['stored_cost_weth']}")
    print(f"  Stored Acquisition TX:    {record['stored_txhash']}")
    print(
        "  Accounting Matches:       "
        f"{len(record['accounting_matches'])}"
    )
    print(
        "  Marketplace Matches:      "
        f"{len(record['marketplace_matches'])}"
    )
    print(
        "  Blockchain TX Matches:    "
        f"{len(record['blockchain_tx_matches'])}"
    )
    print(
        "  Blockchain ID Candidates: "
        f"{len(record['blockchain_axie_candidates'])}"
    )
    print(f"  Final Status:              {record['status']}")

    print_candidate_rows(
        "ACCOUNTING EVIDENCE",
        record["accounting_matches"],
    )

    print_candidate_rows(
        "MARKETPLACE EVIDENCE",
        record["marketplace_matches"],
    )

    print_candidate_rows(
        "BLOCKCHAIN TXHASH EVIDENCE",
        record["blockchain_tx_matches"],
    )

    print_candidate_rows(
        "BLOCKCHAIN AXIE-ID CANDIDATES",
        record["blockchain_axie_candidates"],
    )


def print_summary(records):
    status_counts = {}

    for record in records:
        status = record["status"]

        status_counts[status] = (
            status_counts.get(status, 0) + 1
        )

    print()
    print("=" * 110)
    print("NIGHTMARE ACQUISITION-COST RECOVERY SUMMARY")
    print("=" * 110)

    print(f"Nightmare Axies checked:       {len(records)}")
    print(
        "Costs recovered:              "
        f"{status_counts.get(STATUS_COST_RECOVERED, 0)}"
    )
    print(
        "Cost evidence requiring review:"
        f" {status_counts.get(STATUS_COST_REVIEW, 0)}"
    )
    print(
        "Cost not recovered:           "
        f"{status_counts.get(STATUS_COST_NOT_RECOVERED, 0)}"
    )
    print(
        "Ownership history unresolved: "
        f"{status_counts.get(STATUS_HISTORY_UNRESOLVED, 0)}"
    )

    print()
    print(
        f"{'AXIE ID':<12}"
        f"{'OWNERSHIP START':<22}"
        f"{'COST WETH':<18}"
        f"{'STATUS'}"
    )
    print("-" * 110)

    for record in records:
        ownership_start = (
            record["ownership_start"]
            if record["ownership_start"]
            else "UNKNOWN"
        )

        stored_cost = (
            record["stored_cost_weth"]
            if record["stored_cost_weth"] not in (None, "")
            else "NONE"
        )

        print(
            f"{record['axie_id']:<12}"
            f"{ownership_start:<22}"
            f"{stored_cost:<18}"
            f"{record['status']}"
        )

    unresolved_cost_count = sum(
        1
        for record in records
        if record["status"]
        != STATUS_COST_RECOVERED
    )

    print()
    print("=" * 110)
    print("RECOVERY CONCLUSION")
    print("=" * 110)

    if unresolved_cost_count == 0:
        print(
            "All currently owned Nightmare Axies have "
            "evidence-backed acquisition cost."
        )
    else:
        print(
            f"{unresolved_cost_count} Nightmare Axie(s) still lack "
            "evidence-backed acquisition cost."
        )
        print()
        print(
            "Local AxieOS evidence is insufficient to assign "
            "a defensible purchase basis to those positions."
        )
        print()
        print(
            "Do not infer acquisition cost from ownership-start "
            "timestamps, progression expenses, accessories, or "
            "unrelated marketplace activity."
        )
        print()
        print(
            "Further recovery requires external historical "
            "Ronin / Sky Mavis transaction or marketplace evidence."
        )


def main():
    print("=" * 110)
    print("AXIEOS - NIGHTMARE ACQUISITION-COST RECOVERY")
    print("=" * 110)

    conn = connect_read_only()

    try:
        cur = conn.cursor()

        nightmares = load_owned_nightmares(cur)

        print(
            f"\nNightmare Axies currently owned: "
            f"{len(nightmares)}"
        )

        records = []

        for axie in nightmares:
            record = build_recovery_record(
                cur,
                axie,
            )

            records.append(record)

            print_recovery_detail(record)

        print_summary(records)

    finally:
        conn.close()

    print()
    print("=" * 110)
    print("DONE")
    print("=" * 110)


if __name__ == "__main__":
    main()