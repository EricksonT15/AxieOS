import argparse

from database import connect_database


def get_daily_session_id(conn, session_date, player_id):
    row = conn.execute(
        """
        SELECT id
        FROM gameplay_daily_sessions
        WHERE session_date = ?
          AND player_id = ?
        """,
        (session_date, player_id),
    ).fetchone()

    if row is None:
        raise ValueError(
            f"No gameplay session found for {session_date}. "
            "Create the daily session first."
        )

    return row[0]


def upsert_bounty_task(
    session_date,
    player_id,
    task_slot,
    roll_number,
    game,
    difficulty,
    action,
    requirement,
    reward_bp,
    reward_baxs,
    reroll_cost,
    completed,
    selected_final,
    notes,
):
    conn = connect_database()

    daily_session_id = get_daily_session_id(
        conn,
        session_date,
        player_id,
    )

    conn.execute(
        """
        INSERT INTO bounty_board_tasks (
            daily_session_id,
            task_slot,
            roll_number,
            game,
            difficulty,
            action,
            requirement,
            reward_bp,
            reward_baxs,
            reroll_cost_slips,
            completed,
            selected_final,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(
            daily_session_id,
            task_slot,
            roll_number
        )
        DO UPDATE SET
            game = excluded.game,
            difficulty = excluded.difficulty,
            action = excluded.action,
            requirement = excluded.requirement,
            reward_bp = excluded.reward_bp,
            reward_baxs = excluded.reward_baxs,
            reroll_cost_slips = excluded.reroll_cost_slips,
            completed = excluded.completed,
            selected_final = excluded.selected_final,
            notes = excluded.notes
        """,
        (
            daily_session_id,
            task_slot,
            roll_number,
            game,
            difficulty,
            action,
            requirement,
            reward_bp,
            reward_baxs,
            reroll_cost,
            completed,
            selected_final,
            notes,
        ),
    )

    conn.commit()

    row = conn.execute(
        """
        SELECT
            id,
            task_slot,
            roll_number,
            requirement,
            reward_bp,
            reward_baxs,
            completed,
            selected_final
        FROM bounty_board_tasks
        WHERE daily_session_id = ?
          AND task_slot = ?
          AND roll_number = ?
        """,
        (
            daily_session_id,
            task_slot,
            roll_number,
        ),
    ).fetchone()

    conn.close()

    return row


def main():
    parser = argparse.ArgumentParser(
        description="Add or update an AxieOS Bounty Board task."
    )

    parser.add_argument("date")
    parser.add_argument("task_slot", type=int)

    parser.add_argument("--player", default="primary")
    parser.add_argument("--roll", type=int, default=0)
    parser.add_argument("--game", default="")
    parser.add_argument("--difficulty", default="")
    parser.add_argument("--action", default="")
    parser.add_argument("--requirement", required=True)

    parser.add_argument("--bp", type=int, default=0)
    parser.add_argument("--baxs", default="0")
    parser.add_argument("--reroll-cost", type=int, default=0)

    parser.add_argument(
        "--completed",
        action="store_true",
    )

    parser.add_argument(
        "--final",
        action="store_true",
    )

    parser.add_argument("--notes", default="")

    args = parser.parse_args()

    row = upsert_bounty_task(
        args.date,
        args.player,
        args.task_slot,
        args.roll,
        args.game,
        args.difficulty,
        args.action,
        args.requirement,
        args.bp,
        args.baxs,
        args.reroll_cost,
        int(args.completed),
        int(args.final),
        args.notes,
    )

    print("Bounty task saved.")
    print(row)


if __name__ == "__main__":
    main()