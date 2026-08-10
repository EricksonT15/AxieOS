import argparse
from datetime import date, timedelta
from database import connect_database
from statistics import median


def get_weekly_bounty_result(conn, week_end_date, player_id):
    return conn.execute(
        """
        SELECT
            week_end_date,
            final_rank,
            total_bounty_points,
            master_quest_earnings,
            baxs_reward,
            reward_status,
            claim_datetime,
            notes
        FROM weekly_bounty_results
        WHERE week_end_date = ?
          AND player_id = ?
        """,
        (week_end_date, player_id),
    ).fetchone()


def get_previous_weekly_bounty_result(
    conn,
    week_end_date,
    player_id,
):
    return conn.execute(
        """
        SELECT
            week_end_date,
            final_rank,
            total_bounty_points,
            master_quest_earnings,
            baxs_reward,
            reward_status
        FROM weekly_bounty_results
        WHERE player_id = ?
          AND week_end_date < ?
        ORDER BY week_end_date DESC
        LIMIT 1
        """,
        (player_id, week_end_date),
    ).fetchone()

def get_weekly_reroll_summary(
    conn,
    week_end_date,
    player_id,
):
    return conn.execute(
        """
        SELECT
            COUNT(*) AS reroll_count,
            COALESCE(
                SUM(task.reroll_cost_slips),
                0
            ) AS reroll_slips
        FROM bounty_board_tasks task

        JOIN gameplay_daily_sessions session
          ON session.id = task.daily_session_id

        WHERE session.player_id = ?
          AND session.session_date >= date(?, '-7 days')
          AND session.session_date < ?
          AND task.reroll_cost_slips > 0
        """,
        (
            player_id,
            week_end_date,
            week_end_date,
        ),
    ).fetchone()



def get_weekly_reroll_value(
    conn,
    week_end_date,
    player_id,
):
    return conn.execute(
        """
        WITH rerolled_slots AS (
            SELECT
                session.session_date,
                task.daily_session_id,
                task.task_slot,

                MAX(
                    CASE
                        WHEN task.roll_number = 0
                        THEN task.reward_bp
                    END
                ) AS initial_bp,

                MAX(
                    CASE
                        WHEN task.selected_final = 1
                        THEN task.reward_bp
                    END
                ) AS final_bp,

                SUM(task.reroll_cost_slips) AS slips_spent

            FROM bounty_board_tasks task

            JOIN gameplay_daily_sessions session
              ON session.id = task.daily_session_id

            WHERE session.player_id = ?
              AND session.session_date >= date(?, '-7 days')
              AND session.session_date < ?

            GROUP BY
                task.daily_session_id,
                task.task_slot

            HAVING SUM(task.reroll_cost_slips) > 0
        )

        SELECT
            COUNT(*) AS rerolled_task_slots,
            COALESCE(SUM(initial_bp), 0) AS initial_bp,
            COALESCE(SUM(final_bp), 0) AS final_bp,
            COALESCE(
                SUM(final_bp - initial_bp),
                0
            ) AS bp_gain,
            COALESCE(SUM(slips_spent), 0) AS slips_spent

        FROM rerolled_slots
        """,
        (
            player_id,
            week_end_date,
            week_end_date,
        ),
    ).fetchone()


def get_weekly_reroll_details(
    conn,
    week_end_date,
    player_id,
):
    return conn.execute(
        """
        SELECT
            session.session_date,
            task.task_slot,

            MAX(
                CASE
                    WHEN task.roll_number = 0
                    THEN task.reward_bp
                END
            ) AS initial_bp,

            MAX(
                CASE
                    WHEN task.selected_final = 1
                    THEN task.reward_bp
                END
            ) AS final_bp,

            SUM(task.reroll_cost_slips) AS slips_spent

        FROM bounty_board_tasks task

        JOIN gameplay_daily_sessions session
          ON session.id = task.daily_session_id

        WHERE session.player_id = ?
          AND session.session_date >= date(?, '-7 days')
          AND session.session_date < ?

        GROUP BY
            session.session_date,
            task.task_slot

        HAVING SUM(task.reroll_cost_slips) > 0

        ORDER BY
            session.session_date,
            task.task_slot
        """,
        (
            player_id,
            week_end_date,
            week_end_date,
        ),
    ).fetchall()



def get_weekly_reroll_transitions(
    conn,
    week_end_date,
    player_id,
):
    return conn.execute(
        """
        SELECT
            session.session_date,
            current.task_slot,
            current.roll_number,

            previous.requirement,
            previous.reward_bp,

            current.requirement,
            current.reward_bp,
            current.reroll_cost_slips

        FROM bounty_board_tasks current

        JOIN gameplay_daily_sessions session
          ON session.id = current.daily_session_id

        LEFT JOIN bounty_board_tasks previous
          ON previous.daily_session_id = current.daily_session_id
         AND previous.task_slot = current.task_slot
         AND previous.roll_number = current.roll_number - 1

        WHERE session.player_id = ?
          AND session.session_date >= date(?, '-7 days')
          AND session.session_date < ?
          AND current.reroll_cost_slips > 0

        ORDER BY
            session.session_date,
            current.task_slot,
            current.roll_number
        """,
        (
            player_id,
            week_end_date,
            week_end_date,
        ),
    ).fetchall()





def get_weekly_data_coverage(
    conn,
    week_end_date,
    player_id,
):
    return conn.execute(
        """
        SELECT
            COUNT(DISTINCT session.session_date) AS days_recorded,
            COUNT(
                DISTINCT CASE
                    WHEN task.selected_final = 1
                    THEN task.daily_session_id
                END
            ) AS bounty_days_recorded,
            COALESCE(
                SUM(
                    CASE
                        WHEN task.selected_final = 1
                        THEN task.reward_bp
                        ELSE 0
                    END
                ),
                0
            ) AS recorded_final_bp

        FROM gameplay_daily_sessions session

        LEFT JOIN bounty_board_tasks task
          ON task.daily_session_id = session.id

        WHERE session.player_id = ?
          AND session.session_date >= date(?, '-7 days')
          AND session.session_date < ?
        """,
        (
            player_id,
            week_end_date,
            week_end_date,
        ),
    ).fetchone()


def get_weekly_milestone_bp(
    conn,
    week_end_date,
    player_id,
):
    rows = conn.execute(
        """
        SELECT
            session.session_date,
            COUNT(*) AS completed_final_tasks

        FROM gameplay_daily_sessions session

        JOIN bounty_board_tasks task
          ON task.daily_session_id = session.id

        WHERE session.player_id = ?
          AND session.session_date >= date(?, '-7 days')
          AND session.session_date < ?
          AND task.selected_final = 1
          AND task.completed = 1

        GROUP BY session.session_date
        ORDER BY session.session_date
        """,
        (
            player_id,
            week_end_date,
            week_end_date,
        ),
    ).fetchall()

    total_milestone_bp = 0

    for _, completed_tasks in rows:
        if completed_tasks >= 6:
            total_milestone_bp += 550
        elif completed_tasks == 5:
            total_milestone_bp += 200
        elif completed_tasks == 4:
            total_milestone_bp += 50

    return total_milestone_bp








def get_recorded_bounty_dates(
    conn,
    week_end_date,
    player_id,
):
    return conn.execute(
        """
        SELECT DISTINCT
            session.session_date

        FROM gameplay_daily_sessions session

        JOIN bounty_board_tasks task
          ON task.daily_session_id = session.id

        WHERE session.player_id = ?
          AND session.session_date >= date(?, '-7 days')
          AND session.session_date < ?
          AND task.selected_final = 1

        ORDER BY session.session_date
        """,
        (
            player_id,
            week_end_date,
            week_end_date,
        ),
    ).fetchall()







def main():
    parser = argparse.ArgumentParser(
        description="Show an AxieOS weekly Bounty Board summary."
    )

    parser.add_argument("week_end_date")
    parser.add_argument("--player", default="primary")

    args = parser.parse_args()

    conn = connect_database()

    result = get_weekly_bounty_result(
        conn,
        args.week_end_date,
        args.player,
    )

    previous_result = get_previous_weekly_bounty_result(
        conn,
        args.week_end_date,
        args.player,
    )

    reroll_summary = get_weekly_reroll_summary(
        conn,
        args.week_end_date,
        args.player,
    )

    reroll_value = get_weekly_reroll_value(
        conn,
        args.week_end_date,
        args.player,
    )

    reroll_details = get_weekly_reroll_details(
        conn,
        args.week_end_date,
        args.player,
    )

    reroll_transitions = get_weekly_reroll_transitions(
        conn,
        args.week_end_date,
        args.player,
    )

    known_rerolls = 0
    unknown_rerolls = 0
    positive_rerolls = 0
    negative_rerolls = 0
    neutral_rerolls = 0

    known_reroll_bp_change = 0
    known_reroll_slips = 0

    for transition in reroll_transitions:
        previous_bp = transition[4]
        current_bp = transition[6]
        reroll_cost = transition[7] or 0

        if previous_bp is None or current_bp is None:
            unknown_rerolls += 1
            continue

        known_rerolls += 1

        bp_change = current_bp - previous_bp

        known_reroll_bp_change += bp_change
        known_reroll_slips += reroll_cost

        if bp_change > 0:
            positive_rerolls += 1
        elif bp_change < 0:
            negative_rerolls += 1
        else:
            neutral_rerolls += 1

    known_bp_per_slip = (
        known_reroll_bp_change / known_reroll_slips
        if known_reroll_slips > 0
        else 0
    )

    reroll_cost_stats = {}

    for transition in reroll_transitions:
        previous_bp = transition[4]
        current_bp = transition[6]
        reroll_cost = transition[7] or 0

        if (
            previous_bp is None
            or current_bp is None
            or reroll_cost <= 0
        ):
            continue

        if reroll_cost not in reroll_cost_stats:
            reroll_cost_stats[reroll_cost] = {
                "count": 0,
                "positive": 0,
                "negative": 0,
                "bp_change": 0,
            }

        stats = reroll_cost_stats[reroll_cost]

        bp_change = current_bp - previous_bp

        stats["count"] += 1
        stats["bp_change"] += bp_change

        if bp_change > 0:
            stats["positive"] += 1
        elif bp_change < 0:
            stats["negative"] += 1


    starting_bp_stats = {}

    for transition in reroll_transitions:
        previous_bp = transition[4]
        current_bp = transition[6]
        reroll_cost = transition[7] or 0

        if (
            previous_bp is None
            or current_bp is None
            or reroll_cost <= 0
        ):
            continue

        if previous_bp not in starting_bp_stats:
            starting_bp_stats[previous_bp] = {
                "count": 0,
                "positive": 0,
                "negative": 0,
                "bp_change": 0,
                "slips": 0,
                "changes": [],
                "efficiencies": [],
            }

        stats = starting_bp_stats[previous_bp]

        bp_change = current_bp - previous_bp

        stats["count"] += 1
        stats["bp_change"] += bp_change
        stats["slips"] += reroll_cost
        stats["changes"].append(bp_change)
        stats["efficiencies"].append(
            bp_change / reroll_cost
        )

        if bp_change > 0:
            stats["positive"] += 1
        elif bp_change < 0:
            stats["negative"] += 1





    (
        rerolled_task_slots,
        reroll_initial_bp,
        reroll_final_bp,
        reroll_bp_gain,
        reroll_value_slips,
    ) = reroll_value

    reroll_bp_gain_per_slip = (
        reroll_bp_gain / reroll_value_slips
        if reroll_value_slips > 0
        else 0
    )




    coverage = get_weekly_data_coverage(
        conn,
        args.week_end_date,
        args.player,
    )

    milestone_bp = get_weekly_milestone_bp(
        conn,
        args.week_end_date,
        args.player,
    )




    recorded_bounty_dates = get_recorded_bounty_dates(
        conn,
        args.week_end_date,
        args.player,
    )

    week_end = date.fromisoformat(args.week_end_date)
    week_start = week_end - timedelta(days=7)

    expected_dates = {
        (week_start + timedelta(days=offset)).isoformat()
        for offset in range(7)
    }

    recorded_dates = {
        row[0]
        for row in recorded_bounty_dates
    }

    missing_dates = sorted(
        expected_dates - recorded_dates
    )




    if result is None:
        print("No weekly Bounty result found.")
        conn.close()
        return

    (
        week_end_date,
        final_rank,
        total_bounty_points,
        master_quest_earnings,
        baxs_reward,
        reward_status,
        claim_datetime,
        notes,
    ) = result

    baxs_per_1000_bp = None

    if baxs_reward is not None and total_bounty_points:
        baxs_per_1000_bp = (
            float(baxs_reward) / total_bounty_points * 1000
        )



    print("AXIEOS WEEKLY BOUNTY SUMMARY")
    print("-" * 60)
    print(f"Week ending: {week_end_date}")
    print(f"Final rank: {final_rank}")
    print(f"Total Bounty Points: {total_bounty_points}")
    print(f"Master Quest earnings: {master_quest_earnings}")
    print(f"bAXS reward: {baxs_reward}")

    if baxs_per_1000_bp is not None:
        print(
            f"bAXS per 1,000 BP: "
            f"{baxs_per_1000_bp:.4f}"
        )

    print(f"Reward status: {reward_status}")
    print(f"Claim datetime: {claim_datetime}")

    reroll_count = reroll_summary[0] or 0
    reroll_slips = reroll_summary[1] or 0

    bp_per_reroll_slip = (
        total_bounty_points / reroll_slips
        if reroll_slips > 0
        else 0
    )

    baxs_per_reroll_slip = None

    if baxs_reward is not None and reroll_slips > 0:
        baxs_per_reroll_slip = (
            float(baxs_reward) / reroll_slips
        )


    print()
    print("WEEKLY REROLL ECONOMICS")
    print("-" * 60)
    print(f"Rerolls: {reroll_count}")
    print(f"Fortune Slips spent: {reroll_slips}")

    print(
        f"Official BP per reroll slip: "
        f"{bp_per_reroll_slip:.2f}"
    )

    if baxs_per_reroll_slip is not None:
        print(
            f"bAXS reward per reroll slip: "
            f"{baxs_per_reroll_slip:.4f}"
        )

    print()
    print("ACTUAL REROLL VALUE")
    print("-" * 60)
    print(f"Rerolled task slots: {rerolled_task_slots}")
    print(f"BP before rerolls: {reroll_initial_bp}")
    print(f"BP after rerolls: {reroll_final_bp}")
    print(f"BP gained from rerolls: {reroll_bp_gain:+d}")
    print(f"Fortune Slips used: {reroll_value_slips}")
    print(
        f"BP gained per Fortune Slip: "
        f"{reroll_bp_gain_per_slip:.2f}"
    )

    print()
    print("REROLL SLOT DETAILS")
    print("-" * 80)

    for (
        session_date,
        task_slot,
        initial_bp,
        final_bp,
        slips_spent,
    ) in reroll_details:

        initial_bp = initial_bp or 0
        final_bp = final_bp or 0
        slips_spent = slips_spent or 0

        bp_gain = final_bp - initial_bp

        bp_gain_per_slip = (
            bp_gain / slips_spent
            if slips_spent > 0
            else 0
        )

        print(
            f"{session_date} | "
            f"Task {task_slot} | "
            f"{initial_bp} -> {final_bp} BP | "
            f"{slips_spent} slips | "
            f"{bp_gain:+d} BP | "
            f"{bp_gain_per_slip:.2f} BP/slip"
        )


    print()
    print("INDIVIDUAL REROLL DECISIONS")
    print("-" * 100)

    for (
        session_date,
        task_slot,
        roll_number,
        previous_requirement,
        previous_bp,
        current_requirement,
        current_bp,
        reroll_cost,
    ) in reroll_transitions:

        previous_requirement = (
            previous_requirement or "Unknown task"
        )
        current_requirement = (
            current_requirement or "Unknown task"
        )

        print(
            f"{session_date} | "
            f"Task {task_slot} | "
            f"Roll {roll_number - 1} -> {roll_number}"
        )

        print(
            f"  FROM: {previous_requirement} "
            f"({previous_bp if previous_bp is not None else '?'} BP)"
        )

        print(
            f"  TO:   {current_requirement} "
            f"({current_bp if current_bp is not None else '?'} BP)"
        )

        if (
            previous_bp is not None
            and current_bp is not None
            and reroll_cost > 0
        ):
            bp_change = current_bp - previous_bp
            bp_per_slip = bp_change / reroll_cost

            print(
                f"  RESULT: {bp_change:+d} BP | "
                f"{reroll_cost} slips | "
                f"{bp_per_slip:+.2f} BP/slip"
            )
        else:
            print(
                f"  RESULT: BP change unknown | "
                f"{reroll_cost} slips"
            )

        print()


    print()
    print("INDIVIDUAL REROLL SUMMARY")
    print("-" * 60)

    print(f"Known reroll outcomes: {known_rerolls}")
    print(f"Unknown reroll outcomes: {unknown_rerolls}")
    print(f"Positive rerolls: {positive_rerolls}")
    print(f"Negative rerolls: {negative_rerolls}")
    print(f"Neutral rerolls: {neutral_rerolls}")

    print(
        f"Known BP change: "
        f"{known_reroll_bp_change:+d}"
    )

    print(
        f"Known Fortune Slips spent: "
        f"{known_reroll_slips}"
    )

    print(
        f"Known BP gained per Fortune Slip: "
        f"{known_bp_per_slip:.2f}"
    )


    print()
    print("REROLL PERFORMANCE BY COST")
    print("-" * 60)

    for reroll_cost in sorted(reroll_cost_stats):
        stats = reroll_cost_stats[reroll_cost]

        count = stats["count"]
        positive = stats["positive"]
        negative = stats["negative"]
        bp_change = stats["bp_change"]

        total_slips = count * reroll_cost

        positive_rate = (
            positive / count * 100
            if count > 0
            else 0
        )

        average_bp_change = (
            bp_change / count
            if count > 0
            else 0
        )

        bp_per_slip = (
            bp_change / total_slips
            if total_slips > 0
            else 0
        )

        print(
            f"{reroll_cost}-slip rerolls:"
        )
        print(f"  Known outcomes: {count}")
        print(f"  Positive: {positive}")
        print(f"  Negative: {negative}")
        print(
            f"  Positive rate: "
            f"{positive_rate:.1f}%"
        )
        print(
            f"  Total BP change: "
            f"{bp_change:+d}"
        )
        print(
            f"  Average BP change: "
            f"{average_bp_change:+.2f}"
        )
        print(
            f"  BP gained per slip: "
            f"{bp_per_slip:.2f}"
        )
        print()


    print()
    print("REROLL PERFORMANCE BY STARTING BP")
    print("-" * 60)

    for starting_bp in sorted(starting_bp_stats):
        stats = starting_bp_stats[starting_bp]

        count = stats["count"]
        positive = stats["positive"]
        negative = stats["negative"]
        bp_change = stats["bp_change"]
        slips = stats["slips"]
        changes = stats["changes"]
        efficiencies = stats["efficiencies"]

        minimum_efficiency = min(efficiencies)
        maximum_efficiency = max(efficiencies)
        median_efficiency = median(efficiencies)

        minimum_bp_change = min(changes)
        maximum_bp_change = max(changes)
        median_bp_change = median(changes)

        positive_rate = (
            positive / count * 100
            if count > 0
            else 0
        )

        average_bp_change = (
            bp_change / count
            if count > 0
            else 0
        )

        bp_per_slip = (
            bp_change / slips
            if slips > 0
            else 0
        )

        print(f"{starting_bp} BP starting tasks:")
        print(f"  Known outcomes: {count}")
        print(f"  Positive: {positive}")
        print(f"  Negative: {negative}")
        print(
            f"  Positive rate: "
            f"{positive_rate:.1f}%"
        )
        print(
            f"  Total BP change: "
            f"{bp_change:+d}"
        )
        print(
            f"  Average BP change: "
            f"{average_bp_change:+.2f}"
        )
        print(
            f"  Median BP change: "
            f"{median_bp_change:+.2f}"
        )
        print(
            f"  Min / Max BP change: "
            f"{minimum_bp_change:+d} / "
            f"{maximum_bp_change:+d}"
        )
        print(
            f"  BP gained per slip: "
            f"{bp_per_slip:.2f}"
        )
        print(
            f"  Median BP/slip: "
            f"{median_efficiency:+.2f}"
        )
        print(
            f"  Min / Max BP/slip: "
            f"{minimum_efficiency:+.2f} / "
            f"{maximum_efficiency:+.2f}"
        )
        print()







    days_recorded = coverage[0] or 0
    bounty_days_recorded = coverage[1] or 0
    recorded_final_bp = coverage[2] or 0

    print()
    print("WEEKLY DATA COVERAGE")
    print("-" * 60)
    print(f"Gameplay days recorded: {days_recorded} / 7")
    print(f"Bounty days recorded: {bounty_days_recorded} / 7")
    print(f"Final-task BP recorded: {recorded_final_bp}")

    calculated_weekly_bp = (
        recorded_final_bp + milestone_bp
    )

    bp_difference = (
        total_bounty_points - calculated_weekly_bp
    )

    print()
    print("WEEKLY BP RECONCILIATION")
    print("-" * 60)
    print(f"Final-task BP: {recorded_final_bp}")
    print(f"Milestone BP: {milestone_bp}")
    print(f"Calculated weekly BP: {calculated_weekly_bp}")
    print(f"Official weekly BP: {total_bounty_points}")
    print(f"Difference: {bp_difference:+d}")



    print(
        "Recorded Bounty dates: "
        + ", ".join(sorted(recorded_dates))
    )

    if missing_dates:
        print(
            "Missing Bounty dates: "
            + ", ".join(missing_dates)
        )
    else:
        print("Missing Bounty dates: None")


    coverage_complete = (
        bounty_days_recorded == 7
    )

    if not coverage_complete:
        print()
        print("DATA QUALITY WARNING")
        print("-" * 60)
        print(
            "Weekly Bounty economics are incomplete."
        )
        print(
            f"Only {bounty_days_recorded} of 7 "
            "Bounty days are currently recorded."
        )
        print(
            "Do not use reroll-slip efficiency metrics "
            "until the missing days are backfilled."
        )
    else:
        print()
        print("Weekly Bounty data coverage: COMPLETE")


    if notes:
        print(f"Notes: {notes}")

    if previous_result is not None:
        (
            previous_week_end_date,
            previous_rank,
            previous_points,
            previous_master_quest,
            previous_baxs_reward,
            previous_reward_status,
        ) = previous_result

        rank_improvement = previous_rank - final_rank
        points_change = total_bounty_points - previous_points
        master_quest_change = (
            master_quest_earnings - previous_master_quest
        )

        print()
        print("WEEK-OVER-WEEK COMPARISON")
        print("-" * 60)
        print(
            f"Previous week: {previous_week_end_date}"
        )

        if rank_improvement > 0:
            print(
                f"Rank: {previous_rank} -> {final_rank} "
                f"(improved by {rank_improvement})"
            )
        elif rank_improvement < 0:
            print(
                f"Rank: {previous_rank} -> {final_rank} "
                f"(worsened by {abs(rank_improvement)})"
            )
        else:
            print(
                f"Rank: {previous_rank} -> {final_rank} "
                "(no change)"
            )

        print(
            f"Bounty Points: {previous_points} -> "
            f"{total_bounty_points} "
            f"({points_change:+d})"
        )

        print(
            f"Master Quest earnings: "
            f"{previous_master_quest} -> "
            f"{master_quest_earnings} "
            f"({master_quest_change:+d})"
        )


    conn.close()


if __name__ == "__main__":
    main()