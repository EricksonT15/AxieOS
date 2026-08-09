from database import connect_database
import argparse


def get_daily_session(conn, session_date, player_id="primary"):
    return conn.execute(
        """
        SELECT
            id,
            session_date,
            shrine_streak,
            starting_fortune_slips,
            claimed_fortune_slips,
            ending_fortune_slips
        FROM gameplay_daily_sessions
        WHERE session_date = ?
          AND player_id = ?
        """,
        (session_date, player_id),
    ).fetchone()


def get_bounty_summary(conn, daily_session_id):
    return conn.execute(
        """
        SELECT
            COUNT(*) AS final_tasks,
            SUM(reward_bp) AS total_bp,
            SUM(CAST(reward_baxs AS REAL)) AS total_baxs
        FROM bounty_board_tasks
        WHERE daily_session_id = ?
          AND selected_final = 1
        """,
        (daily_session_id,),
    ).fetchone()


def get_reroll_summary(conn, daily_session_id):
    return conn.execute(
        """
        SELECT
            COUNT(*) AS reroll_count,
            COALESCE(SUM(reroll_cost_slips), 0) AS reroll_slips
        FROM bounty_board_tasks
        WHERE daily_session_id = ?
          AND roll_number > 0
        """,
        (daily_session_id,),
    ).fetchone()

def get_final_bounty_tasks(conn, daily_session_id):
    return conn.execute(
        """
        SELECT
            task_slot,
            game,
            difficulty,
            action,
            requirement,
            reward_bp,
            reward_baxs
        FROM bounty_board_tasks
        WHERE daily_session_id = ?
          AND selected_final = 1
        ORDER BY task_slot
        """,
        (daily_session_id,),
    ).fetchall()

def get_terrarium_snapshots(conn, daily_session_id):
    return conn.execute(
        """
        SELECT
            id,
            snapshot_type,
            global_lunium,
            CAST(claimable_baxs AS REAL)
        FROM terrarium_snapshots
        WHERE daily_session_id = ?
        ORDER BY id
        """,
        (daily_session_id,),
    ).fetchall()


def get_terrarium_plot_data(conn, snapshot_id):
    return conn.execute(
        """
        SELECT
            plot_type,
            plot_number,
            flame,
            CAST(next_distribution AS REAL),
            CAST(total_acquired_baxs AS REAL)
        FROM terrarium_plot_snapshots
        WHERE terrarium_snapshot_id = ?
        ORDER BY plot_type, plot_number
        """,
        (snapshot_id,),
    ).fetchall()

def get_terrarium_rankings(conn, snapshot_id):
    return conn.execute(
        """
        SELECT
            group_type,
            rank,
            global_flame
        FROM terrarium_group_rankings
        WHERE terrarium_snapshot_id = ?
        ORDER BY group_type
        """,
        (snapshot_id,),
    ).fetchall()

def get_marketplace_axie_trades(conn, daily_session_id):
    return conn.execute(
        """
        SELECT
            buy.asset_id,
            buy.asset_name,
            buy.event_datetime AS buy_time,
            sale.event_datetime AS sale_time,
            CAST(buy.amount AS REAL) AS buy_price,
            CAST(sale.amount AS REAL) AS sale_price,
            buy.currency,

            CAST(sale.amount AS REAL)
                - CAST(buy.amount AS REAL)
                AS gross_spread,

            (
                (
                    CAST(sale.amount AS REAL)
                    - CAST(buy.amount AS REAL)
                )
                / CAST(buy.amount AS REAL)
            ) * 100 AS gross_roi,

            ROUND(
                (
                    julianday(sale.event_datetime)
                    - julianday(buy.event_datetime)
                ) * 24,
                2
            ) AS holding_hours,

            buy.related_bounty_task_id,
            buy.id AS marketplace_event_id

        FROM marketplace_events buy

        JOIN marketplace_events sale
          ON buy.asset_id = sale.asset_id

        WHERE buy.daily_session_id = ?
          AND buy.event_type = 'buy'
          AND sale.event_type = 'sale'
          AND buy.asset_type = 'Axie'

        ORDER BY buy.event_datetime
        """,
        (daily_session_id,),
    ).fetchall()

def get_bounty_task_by_id(conn, task_id):
    return conn.execute(
        """
        SELECT
            task_slot,
            requirement,
            reward_bp,
            reward_baxs
        FROM bounty_board_tasks
        WHERE id = ?
        """,
        (task_id,),
    ).fetchone()

def get_inventory_summary(conn, daily_session_id):
    return conn.execute(
        """
        SELECT
            item_name,
            SUM(quantity_change) AS balance
        FROM inventory_events
        WHERE daily_session_id = ?
        GROUP BY item_name
        ORDER BY item_name
        """,
        (daily_session_id,),
    ).fetchall()

def get_staking_reward_events(conn, daily_session_id):
    return conn.execute(
        """
        SELECT
            event_type,
            source,
            token,
            amount,
            related_bounty_task_id
        FROM staking_reward_events
        WHERE daily_session_id = ?
        ORDER BY event_datetime, id
        """,
        (daily_session_id,),
    ).fetchall()


def get_bounty_tasks_for_marketplace_event(
    conn,
    marketplace_event_id,
):
    return conn.execute(
        """
        SELECT
            bbt.task_slot,
            bbt.requirement,
            bbt.reward_bp,
            bbt.reward_baxs
        FROM marketplace_event_bounty_tasks link

        JOIN bounty_board_tasks bbt
          ON link.bounty_task_id = bbt.id

        WHERE link.marketplace_event_id = ?

        ORDER BY bbt.task_slot
        """,
        (marketplace_event_id,),
    ).fetchall()

def get_open_marketplace_positions(conn, daily_session_id):
    return conn.execute(
        """
        SELECT
            buy.id AS marketplace_event_id,
            buy.asset_id,
            buy.asset_name,
            buy.event_datetime AS buy_time,
            CAST(buy.amount AS REAL) AS buy_price,
            buy.currency,
            list.event_datetime AS list_time,
            CAST(list.amount AS REAL) AS list_price
        FROM marketplace_events buy

        LEFT JOIN marketplace_events list
          ON buy.asset_id = list.asset_id
         AND list.event_type = 'list'

        LEFT JOIN marketplace_events sale
          ON buy.asset_id = sale.asset_id
         AND sale.event_type = 'sale'

        WHERE buy.daily_session_id = ?
          AND buy.event_type = 'buy'
          AND buy.asset_type = 'Axie'
          AND sale.id IS NULL

        ORDER BY buy.event_datetime
        """,
        (daily_session_id,),
    ).fetchall()



def main():
    parser = argparse.ArgumentParser(
        description="Generate an AxieOS daily gameplay summary."
    )

    parser.add_argument(
        "date",
        help="Gameplay date in YYYY-MM-DD format.",
    )

    args = parser.parse_args()

    session_date = args.date

    conn = connect_database()

    session = get_daily_session(conn, session_date)

    if session is None:
        print(f"No gameplay session found for {session_date}.")
        conn.close()
        return

    daily_session_id = session[0]

    bounty = get_bounty_summary(conn, daily_session_id)
    rerolls = get_reroll_summary(conn, daily_session_id)
    final_tasks = get_final_bounty_tasks(conn, daily_session_id)
    terrarium_snapshots = get_terrarium_snapshots(
        conn,
        daily_session_id,
    )

    marketplace_trades = get_marketplace_axie_trades(
        conn,
        daily_session_id,
    )

    open_positions = get_open_marketplace_positions(
        conn,
        daily_session_id,
    )

    inventory_summary = get_inventory_summary(
        conn,
        daily_session_id,
    )

    staking_events = get_staking_reward_events(
        conn,
        daily_session_id,
    )

    print("=" * 60)
    print("AXIEOS DAILY GAMEPLAY SUMMARY")
    print("=" * 60)

    print()
    print(f"Date: {session[1]}")
    print(f"Shrine streak: {session[2]}")
    print(f"Starting Fortune Slips: {session[3]}")
    print(f"Claimed Fortune Slips: {session[4]}")
    print(f"Ending Fortune Slips: {session[5]}")

    print()
    print("BOUNTY BOARD")
    print("-" * 60)
    print(f"Final tasks: {bounty[0]}")
    print(f"Total BP: {bounty[1]}")
    print(f"Bonus bAXS: {bounty[2]}")
    print(f"Rerolls: {rerolls[0]}")
    print(f"Reroll slips spent: {rerolls[1]}")

    print()
    print("FINAL TASKS")
    print("-" * 60)

    for task in final_tasks:
        task_slot = task[0]
        game = task[1] or "-"
        difficulty = task[2] or "-"
        action = task[3] or "-"
        requirement = task[4] or "-"
        reward_bp = task[5] or 0
        reward_baxs = float(task[6] or 0)

        reward_text = f"{reward_bp} BP"

        if reward_baxs > 0:
            reward_text += f" + {reward_baxs:g} bAXS"

        print(
            f"{task_slot}. "
            f"[{game} / {difficulty}] "
            f"{action} — {requirement} "
            f"({reward_text})"
        )

# TERRARIUM BLOCK STARTS HERE
    if len(terrarium_snapshots) >= 2:
        morning = terrarium_snapshots[0]
        evening = terrarium_snapshots[-1]

        morning_plots = get_terrarium_plot_data(
            conn,
            morning[0],
        )

        evening_plots = get_terrarium_plot_data(
            conn,
            evening[0],
        )

        morning_rankings = get_terrarium_rankings(
            conn,
            morning[0],
        )

        evening_rankings = get_terrarium_rankings(
            conn,
            evening[0],
        )

        print()
        print("TERRARIUM")
        print("-" * 60)

        print(
            f"Global Lunium: "
            f"{morning[2]} -> {evening[2]} "
            f"({evening[2] - morning[2]:+})"
        )

        print(
            f"Claimable bAXS: "
            f"{morning[3]:.2f} -> {evening[3]:.2f} "
            f"({evening[3] - morning[3]:+.2f})"
        )

        print()
        print("PLOT CHANGES")

        morning_plot_map = {
            (row[0], row[1]): row
            for row in morning_plots
        }

        evening_plot_map = {
            (row[0], row[1]): row
            for row in evening_plots
        }

        for key in morning_plot_map:
            m = morning_plot_map[key]
            e = evening_plot_map[key]

            acquired_change = e[4] - m[4]

            print(
                f"{key[0]} #{key[1]}: "
                f"{m[4]:.2f} -> {e[4]:.2f} "
                f"({acquired_change:+.2f} bAXS)"
            )

        print()
        print("RANK CHANGES")

        morning_rank_map = {
            row[0]: row
            for row in morning_rankings
        }

        evening_rank_map = {
            row[0]: row
            for row in evening_rankings
        }

        for group_type in morning_rank_map:
            m = morning_rank_map[group_type]
            e = evening_rank_map[group_type]

            rank_change = e[1] - m[1]
            flame_change = e[2] - m[2]

            if rank_change < 0:
                rank_text = f"improved {abs(rank_change)}"
            elif rank_change > 0:
                rank_text = f"declined {rank_change}"
            else:
                rank_text = "unchanged"

            print(
                f"{group_type}: "
                f"rank {m[1]} -> {e[1]} "
                f"({rank_text}), "
                f"global flame {flame_change:+}"
            )
# TERRARIUM BLOCK ENDS HERE

    if marketplace_trades:
        print()
        print("MARKETPLACE")
        print("-" * 60)

        for trade in marketplace_trades:
            asset_id = trade[0]
            asset_name = trade[1] or "Axie"
            buy_time = trade[2]
            sale_time = trade[3]
            buy_price = trade[4]
            sale_price = trade[5]
            currency = trade[6]
            gross_spread = trade[7]
            gross_roi = trade[8]
            holding_hours = trade[9]
            bounty_task_id = trade[10]
            marketplace_event_id = trade[11]

            print(f"{asset_name} #{asset_id}")

            print(
                f"  Buy: {buy_price:.8f} {currency} "
                f"at {buy_time}"
                )

            print(
                f"  Sale: {sale_price:.8f} {currency} "
                f"at {sale_time}"
            )

            print(
                f"  Gross spread: "
                f"{gross_spread:+.8f} {currency}"
                )

            print(
                f"  Gross ROI: {gross_roi:.2f}%"
                )

            print(
                f"  Holding time: {holding_hours:.2f} hours"
                )

            linked_tasks = get_bounty_tasks_for_marketplace_event(
                conn,
                marketplace_event_id,
            )

            if linked_tasks:
                print("  Linked Bounty Tasks:")

                total_linked_bp = 0
                total_linked_baxs = 0.0

                for linked_task in linked_tasks:
                    task_slot = linked_task[0]
                    requirement = linked_task[1]
                    reward_bp = linked_task[2] or 0
                    reward_baxs = float(
                        linked_task[3] or 0
                    )

                    total_linked_bp += reward_bp
                    total_linked_baxs += reward_baxs

                    reward_text = f"{reward_bp} BP"

                    if reward_baxs > 0:
                        reward_text += (
                            f" + {reward_baxs:g} bAXS"
                        )

                    print(
                        f"    Task {task_slot}: "
                        f"{requirement} "
                        f"({reward_text})"
                    )

                if len(linked_tasks) > 1:
                    total_text = (
                        f"{total_linked_bp} BP"
                    )

                    if total_linked_baxs > 0:
                        total_text += (
                            f" + {total_linked_baxs:g} bAXS"
                        )

                    print(
                        f"  Total linked Bounty value: "
                        f"{total_text}"
                    )

            print()

    if open_positions:
        print()
        print("OPEN MARKETPLACE POSITIONS")
        print("-" * 60)

        for position in open_positions:
            marketplace_event_id = position[0]
            asset_id = position[1]
            asset_name = position[2] or "Axie"
            buy_time = position[3]
            buy_price = position[4]
            currency = position[5]
            list_time = position[6]
            list_price = position[7]

            print(f"{asset_name} #{asset_id}")

            print(
                f"  Buy: {buy_price:.8f} {currency} "
                f"at {buy_time}"
                )

            if list_price is not None:
                print(
                    f"  Listed: {list_price:.8f} {currency} "
                    f"at {list_time}"
                    )

                target_spread = list_price - buy_price
                target_roi = (
                    target_spread / buy_price
                    ) * 100

                print(
                    f"  Target gross spread: "
                    f"{target_spread:+.8f} {currency}"
                    )

                print(
                    f"  Target gross ROI: "
                    f"{target_roi:.2f}%"
                    )

                linked_tasks = get_bounty_tasks_for_marketplace_event(
                    conn,
                    marketplace_event_id,
                )

                if linked_tasks:
                    print("  Linked Bounty Tasks:")

                    total_bp = 0
                    total_baxs = 0.0

                    for task in linked_tasks:
                        task_slot = task[0]
                        requirement = task[1]
                        reward_bp = task[2] or 0
                        reward_baxs = float(task[3] or 0)

                        total_bp += reward_bp
                        total_baxs += reward_baxs

                        reward_text = f"{reward_bp} BP"

                        if reward_baxs > 0:
                            reward_text += (
                                f" + {reward_baxs:g} bAXS"
                            )

                        print(
                            f"    Task {task_slot}: "
                            f"{requirement} "
                            f"({reward_text})"
                        )

                    if len(linked_tasks) > 1:
                        total_text = f"{total_bp} BP"

                        if total_baxs > 0:
                            total_text += (
                                f" + {total_baxs:g} bAXS"
                            )

                        print(
                            f"  Total linked Bounty value: "
                            f"{total_text}"
                        )

                print()

    if inventory_summary:
        print()
        print("INVENTORY")
        print("-" * 60)

        for item_name, balance in inventory_summary:
            print(f"{item_name}: {balance}")


    if staking_events:
        print()
        print("STAKING / REWARDS")
        print("-" * 60)

        for event_type, source, token, amount, task_id in staking_events:
            print(
                f"{event_type}: {amount} {token} "
                f"({source or '-'})"
                )

            if task_id is not None:
                bounty_task = get_bounty_task_by_id(
                    conn,
                    task_id,
                    )

                if bounty_task is not None:
                    print(
                        f"  Related Bounty Task "
                        f"{bounty_task[0]}: "
                        f"{bounty_task[1]}"
                        )

    print()
    print("=" * 60)

    conn.close()

if __name__ == "__main__":
    main()