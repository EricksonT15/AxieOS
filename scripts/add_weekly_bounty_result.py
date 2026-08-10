import argparse

from database import connect_database


def add_weekly_bounty_result(
    conn,
    week_end_date,
    player_id,
    final_rank,
    total_bounty_points,
    master_quest_earnings,
    baxs_reward,
    reward_status,
    claim_datetime,
    notes,
):
    conn.execute(
        """
        INSERT INTO weekly_bounty_results (
            player_id,
            week_end_date,
            final_rank,
            total_bounty_points,
            master_quest_earnings,
            baxs_reward,
            reward_status,
            claim_datetime,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(player_id, week_end_date)
        DO UPDATE SET
            final_rank = excluded.final_rank,
            total_bounty_points = excluded.total_bounty_points,
            master_quest_earnings = excluded.master_quest_earnings,
            baxs_reward = excluded.baxs_reward,
            reward_status = excluded.reward_status,
            claim_datetime = excluded.claim_datetime,
            notes = excluded.notes,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            player_id,
            week_end_date,
            final_rank,
            total_bounty_points,
            master_quest_earnings,
            baxs_reward,
            reward_status,
            claim_datetime,
            notes,
        ),
    )

    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Add or update an AxieOS weekly Bounty Board result."
    )

    parser.add_argument("week_end_date")
    parser.add_argument("--player", default="primary")
    parser.add_argument("--rank", type=int)
    parser.add_argument("--points", type=int)
    parser.add_argument("--master-quest", type=int, default=0)
    parser.add_argument("--baxs-reward")
    parser.add_argument("--reward-status")
    parser.add_argument("--claim-datetime")
    parser.add_argument("--notes")

    args = parser.parse_args()

    conn = connect_database()

    add_weekly_bounty_result(
        conn=conn,
        week_end_date=args.week_end_date,
        player_id=args.player,
        final_rank=args.rank,
        total_bounty_points=args.points,
        master_quest_earnings=args.master_quest,
        baxs_reward=args.baxs_reward,
        reward_status=args.reward_status,
        claim_datetime=args.claim_datetime,
        notes=args.notes,
    )

    print("Weekly Bounty result saved.")
    print(f"Week ending: {args.week_end_date}")
    print(f"Rank: {args.rank}")
    print(f"Points: {args.points}")
    print(f"Master Quest earnings: {args.master_quest}")
    print(f"bAXS reward: {args.baxs_reward}")
    print(f"Reward status: {args.reward_status}")

    conn.close()


if __name__ == "__main__":
    main()