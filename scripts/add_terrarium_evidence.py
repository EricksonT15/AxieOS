import argparse
from datetime import datetime

from database import connect_database


COMPLETE_STATUSES = (
    "COMPLETE",
    "PARTIAL",
    "UNRESOLVED",
)


def validate_date(value):
    try:
        datetime.strptime(
            value,
            "%Y-%m-%d",
        )
    except ValueError as exc:
        raise ValueError(
            "date must use YYYY-MM-DD format."
        ) from exc


def validate_observed_datetime(value):
    if value is None:
        return

    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            "--datetime must be a valid ISO-8601 "
            "datetime/date value."
        ) from exc


def plot_has_evidence(
    flame,
    next_distribution,
    total_acquired_baxs,
):
    return any(
        value is not None
        for value in (
            flame,
            next_distribution,
            total_acquired_baxs,
        )
    )


def ranking_has_evidence(
    rank,
    global_flame,
):
    return any(
        value is not None
        for value in (
            rank,
            global_flame,
        )
    )


def validate_complete_evidence(args):
    if args.completeness_status != "COMPLETE":
        return

    required_values = {
        "global_lunium": args.global_lunium,
        "claimable_baxs": args.claimable_baxs,

        "forest_flame": args.forest_flame,
        "forest_next": args.forest_next,
        "forest_acquired": args.forest_acquired,

        "savannah1_flame": args.savannah1_flame,
        "savannah1_next": args.savannah1_next,
        "savannah1_acquired": args.savannah1_acquired,

        "savannah2_flame": args.savannah2_flame,
        "savannah2_next": args.savannah2_next,
        "savannah2_acquired": args.savannah2_acquired,

        "forest_rank": args.forest_rank,
        "forest_global_flame": (
            args.forest_global_flame
        ),

        "savannah_rank": args.savannah_rank,
        "savannah_global_flame": (
            args.savannah_global_flame
        ),
    }

    missing = [
        name
        for name, value in required_values.items()
        if value is None
    ]

    if missing:
        raise ValueError(
            "COMPLETE evidence is missing required "
            "Terrarium metrics: "
            + ", ".join(missing)
        )


def validate_partial_evidence(args):
    if args.completeness_status != "PARTIAL":
        return

    has_metric = any(
        value is not None
        for value in (
            args.global_lunium,
            args.claimable_baxs,
            args.buff_active,

            args.forest_flame,
            args.forest_next,
            args.forest_acquired,

            args.savannah1_flame,
            args.savannah1_next,
            args.savannah1_acquired,

            args.savannah2_flame,
            args.savannah2_next,
            args.savannah2_acquired,

            args.forest_rank,
            args.forest_global_flame,

            args.savannah_rank,
            args.savannah_global_flame,
        )
    )

    if not has_metric:
        raise ValueError(
            "PARTIAL evidence must contain at least "
            "one observed Terrarium metric."
        )


def validate_args(args):
    validate_date(args.date)
    validate_observed_datetime(
        args.observed_datetime
    )
    validate_complete_evidence(args)
    validate_partial_evidence(args)


def insert_plot_evidence(
    conn,
    evidence_id,
    plot_type,
    plot_number,
    flame,
    next_distribution,
    total_acquired_baxs,
    notes=None,
):
    if not plot_has_evidence(
        flame,
        next_distribution,
        total_acquired_baxs,
    ):
        return False

    conn.execute(
        """
        INSERT INTO terrarium_plot_evidence (
            terrarium_evidence_id,
            plot_type,
            plot_number,
            flame,
            next_distribution,
            total_acquired_baxs,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            evidence_id,
            plot_type,
            plot_number,
            flame,
            next_distribution,
            total_acquired_baxs,
            notes,
        ),
    )

    return True


def insert_ranking_evidence(
    conn,
    evidence_id,
    group_type,
    rank,
    global_flame,
    notes=None,
):
    if not ranking_has_evidence(
        rank,
        global_flame,
    ):
        return False

    conn.execute(
        """
        INSERT INTO terrarium_group_ranking_evidence (
            terrarium_evidence_id,
            group_type,
            rank,
            global_flame,
            notes
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            evidence_id,
            group_type,
            rank,
            global_flame,
            notes,
        ),
    )

    return True


def add_evidence(args):
    validate_args(args)

    conn = connect_database()
    conn.row_factory = None
    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    try:
        existing = conn.execute(
            """
            SELECT id
            FROM terrarium_snapshot_evidence
            WHERE session_date = ?
              AND player_id = ?
              AND snapshot_type = ?
              AND source_reference = ?
            """,
            (
                args.date,
                args.player,
                args.snapshot_type,
                args.source_reference,
            ),
        ).fetchone()

        if existing is not None:
            raise ValueError(
                "Evidence record already exists for "
                "this date/player/type/source-reference. "
                f"Existing evidence ID: {existing[0]}"
            )

        conn.execute(
            "BEGIN"
        )

        cursor = conn.execute(
            """
            INSERT INTO terrarium_snapshot_evidence (
                session_date,
                player_id,
                snapshot_type,
                observed_datetime,
                observed_time_text,
                completeness_status,
                global_lunium,
                claimable_baxs,
                buff_active,
                source,
                source_reference,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                args.date,
                args.player,
                args.snapshot_type,
                args.observed_datetime,
                args.observed_time_text,
                args.completeness_status,
                args.global_lunium,
                args.claimable_baxs,
                args.buff_active,
                args.source,
                args.source_reference,
                args.notes,
            ),
        )

        evidence_id = cursor.lastrowid

        plot_rows = 0

        plot_rows += int(
            insert_plot_evidence(
                conn=conn,
                evidence_id=evidence_id,
                plot_type="Forest",
                plot_number=1,
                flame=args.forest_flame,
                next_distribution=args.forest_next,
                total_acquired_baxs=(
                    args.forest_acquired
                ),
            )
        )

        plot_rows += int(
            insert_plot_evidence(
                conn=conn,
                evidence_id=evidence_id,
                plot_type="Savannah",
                plot_number=1,
                flame=args.savannah1_flame,
                next_distribution=(
                    args.savannah1_next
                ),
                total_acquired_baxs=(
                    args.savannah1_acquired
                ),
            )
        )

        plot_rows += int(
            insert_plot_evidence(
                conn=conn,
                evidence_id=evidence_id,
                plot_type="Savannah",
                plot_number=2,
                flame=args.savannah2_flame,
                next_distribution=(
                    args.savannah2_next
                ),
                total_acquired_baxs=(
                    args.savannah2_acquired
                ),
            )
        )

        ranking_rows = 0

        ranking_rows += int(
            insert_ranking_evidence(
                conn=conn,
                evidence_id=evidence_id,
                group_type="Forest",
                rank=args.forest_rank,
                global_flame=(
                    args.forest_global_flame
                ),
            )
        )

        ranking_rows += int(
            insert_ranking_evidence(
                conn=conn,
                evidence_id=evidence_id,
                group_type="Savannah",
                rank=args.savannah_rank,
                global_flame=(
                    args.savannah_global_flame
                ),
            )
        )

        conn.commit()

    except Exception:
        conn.rollback()
        conn.close()
        raise

    conn.close()

    print(
        "Terrarium evidence saved."
    )
    print(
        f"Evidence ID: {evidence_id}"
    )
    print(
        f"Status: {args.completeness_status}"
    )
    print(
        f"Plot evidence rows: {plot_rows}"
    )
    print(
        f"Ranking evidence rows: {ranking_rows}"
    )


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Add historical or partial Terrarium "
            "source evidence without modifying the "
            "canonical Terrarium snapshot tables."
        )
    )

    parser.add_argument(
        "date",
    )

    parser.add_argument(
        "--player",
        default="primary",
    )

    parser.add_argument(
        "--type",
        dest="snapshot_type",
        required=True,
    )

    parser.add_argument(
        "--datetime",
        dest="observed_datetime",
    )

    parser.add_argument(
        "--time-text",
        dest="observed_time_text",
    )

    parser.add_argument(
        "--status",
        dest="completeness_status",
        choices=COMPLETE_STATUSES,
        required=True,
    )

    parser.add_argument(
        "--global-lunium",
        type=int,
    )

    parser.add_argument(
        "--claimable-baxs",
    )

    buff_group = (
        parser.add_mutually_exclusive_group()
    )

    buff_group.add_argument(
        "--buff-active",
        dest="buff_active",
        action="store_const",
        const=1,
    )

    buff_group.add_argument(
        "--buff-inactive",
        dest="buff_active",
        action="store_const",
        const=0,
    )

    parser.set_defaults(
        buff_active=None,
    )

    parser.add_argument(
        "--source",
        required=True,
    )

    parser.add_argument(
        "--source-reference",
        required=True,
    )

    parser.add_argument(
        "--notes",
        default="",
    )

    parser.add_argument(
        "--forest-flame",
        type=int,
    )

    parser.add_argument(
        "--forest-next",
    )

    parser.add_argument(
        "--forest-acquired",
    )

    parser.add_argument(
        "--forest-rank",
        type=int,
    )

    parser.add_argument(
        "--forest-global-flame",
        type=int,
    )

    parser.add_argument(
        "--savannah1-flame",
        type=int,
    )

    parser.add_argument(
        "--savannah1-next",
    )

    parser.add_argument(
        "--savannah1-acquired",
    )

    parser.add_argument(
        "--savannah2-flame",
        type=int,
    )

    parser.add_argument(
        "--savannah2-next",
    )

    parser.add_argument(
        "--savannah2-acquired",
    )

    parser.add_argument(
        "--savannah-rank",
        type=int,
    )

    parser.add_argument(
        "--savannah-global-flame",
        type=int,
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    try:
        add_evidence(args)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
