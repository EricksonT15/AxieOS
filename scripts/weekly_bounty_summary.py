import argparse

from database import connect_database


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