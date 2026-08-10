from database import connect_database


def create_gameplay_schema():
    conn = connect_database()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gameplay_daily_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            session_date TEXT NOT NULL,
            player_id TEXT NOT NULL DEFAULT 'primary',

            shrine_streak INTEGER,

            starting_fortune_slips INTEGER,
            claimed_fortune_slips INTEGER DEFAULT 0,
            ending_fortune_slips INTEGER,

            notes TEXT,

            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(session_date, player_id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bounty_board_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            daily_session_id INTEGER NOT NULL,
            task_slot INTEGER NOT NULL,
            roll_number INTEGER NOT NULL DEFAULT 0,

            game TEXT,
            difficulty TEXT,
            action TEXT,
            requirement TEXT,

            reward_bp INTEGER DEFAULT 0,
            reward_baxs TEXT DEFAULT '0',

            reroll_cost_slips INTEGER DEFAULT 0,

            completed INTEGER NOT NULL DEFAULT 0,
            selected_final INTEGER NOT NULL DEFAULT 0,

            notes TEXT,

            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (daily_session_id)
                REFERENCES gameplay_daily_sessions(id),

            UNIQUE(daily_session_id, task_slot, roll_number)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS terrarium_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            daily_session_id INTEGER NOT NULL,

            snapshot_datetime TEXT NOT NULL,
            snapshot_type TEXT,

            global_lunium INTEGER,
            claimable_baxs TEXT,

            buff_active INTEGER NOT NULL DEFAULT 1,
            buff_activation_time TEXT,
            estimated_unbuffed_hours TEXT DEFAULT '0',

            notes TEXT,

            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (daily_session_id)
                REFERENCES gameplay_daily_sessions(id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS terrarium_plot_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            terrarium_snapshot_id INTEGER NOT NULL,

            plot_type TEXT NOT NULL,
            plot_number INTEGER NOT NULL,

            flame INTEGER,
            next_distribution TEXT,
            total_acquired_baxs TEXT,

            notes TEXT,

            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (terrarium_snapshot_id)
                REFERENCES terrarium_snapshots(id),

            UNIQUE(
                terrarium_snapshot_id,
                plot_type,
                plot_number
            )
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS terrarium_group_rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            terrarium_snapshot_id INTEGER NOT NULL,

            group_type TEXT NOT NULL,

            rank INTEGER,
            global_flame INTEGER,

            notes TEXT,

            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (terrarium_snapshot_id)
                REFERENCES terrarium_snapshots(id),

            UNIQUE(
                terrarium_snapshot_id,
                group_type
            )
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS marketplace_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            daily_session_id INTEGER,

            event_datetime TEXT NOT NULL,
            event_type TEXT NOT NULL,

            asset_type TEXT NOT NULL,
            asset_id TEXT,
            asset_name TEXT,

            quantity INTEGER NOT NULL DEFAULT 1,

            amount TEXT,
            currency TEXT,

            related_bounty_task_id INTEGER,

            notes TEXT,

            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (daily_session_id)
                REFERENCES gameplay_daily_sessions(id),

            FOREIGN KEY (related_bounty_task_id)
                REFERENCES bounty_board_tasks(id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            daily_session_id INTEGER,

            event_datetime TEXT NOT NULL,

            item_type TEXT NOT NULL,
            item_name TEXT NOT NULL,

            event_type TEXT NOT NULL,
            quantity_change INTEGER NOT NULL,

            related_bounty_task_id INTEGER,
            related_marketplace_event_id INTEGER,

            notes TEXT,

            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (daily_session_id)
                REFERENCES gameplay_daily_sessions(id),

            FOREIGN KEY (related_bounty_task_id)
                REFERENCES bounty_board_tasks(id),

            FOREIGN KEY (related_marketplace_event_id)
                REFERENCES marketplace_events(id)
        )
        """
    )



    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_event_bounty_tasks (
            inventory_event_id INTEGER NOT NULL,
            bounty_task_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (
                inventory_event_id,
                bounty_task_id
            ),

            FOREIGN KEY (inventory_event_id)
                REFERENCES inventory_events(id)
                ON DELETE CASCADE,

            FOREIGN KEY (bounty_task_id)
                REFERENCES bounty_board_tasks(id)
                ON DELETE CASCADE
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pouch_opening_events (
            id INTEGER PRIMARY KEY,
            daily_session_id INTEGER NOT NULL,

            event_datetime TEXT,

            pouch_type TEXT NOT NULL,
            quantity_opened INTEGER NOT NULL,
            slips_spent INTEGER NOT NULL,

            request_tx_hash TEXT,
            fulfillment_tx_hash TEXT,

            upfront_ron TEXT,
            user_tx_fee_ron TEXT,
            refund_ron TEXT,
            net_ron_cost TEXT,

            notes TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (daily_session_id)
                REFERENCES gameplay_daily_sessions(id)
                ON DELETE CASCADE
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pouch_reward_items (
            id INTEGER PRIMARY KEY,
            pouch_opening_event_id INTEGER NOT NULL,

            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,

            notes TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (pouch_opening_event_id)
                REFERENCES pouch_opening_events(id)
                ON DELETE CASCADE
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS weekly_bounty_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT NOT NULL DEFAULT 'primary',
            week_end_date TEXT NOT NULL,
            final_rank INTEGER,
            total_bounty_points INTEGER,
            master_quest_earnings INTEGER DEFAULT 0,
            baxs_reward TEXT,
            reward_status TEXT,
            claim_datetime TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(player_id, week_end_date)
        )
        """
    )





    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS staking_reward_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            daily_session_id INTEGER,

            event_datetime TEXT NOT NULL,

            event_type TEXT NOT NULL,
            source TEXT,

            token TEXT NOT NULL,
            amount TEXT NOT NULL,

            related_bounty_task_id INTEGER,

            notes TEXT,

            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (daily_session_id)
                REFERENCES gameplay_daily_sessions(id),

            FOREIGN KEY (related_bounty_task_id)
                REFERENCES bounty_board_tasks(id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS marketplace_event_bounty_tasks (
            marketplace_event_id INTEGER NOT NULL,
            bounty_task_id INTEGER NOT NULL,

            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            PRIMARY KEY (
                marketplace_event_id,
                bounty_task_id
            ),

            FOREIGN KEY (marketplace_event_id)
                REFERENCES marketplace_events(id)
                ON DELETE CASCADE,

            FOREIGN KEY (bounty_task_id)
                REFERENCES bounty_board_tasks(id)
                ON DELETE CASCADE
        )
        """
    )

    conn.execute(
        """
        INSERT OR IGNORE INTO marketplace_event_bounty_tasks (
            marketplace_event_id,
            bounty_task_id
        )
        SELECT
            id,
            related_bounty_task_id
        FROM marketplace_events
        WHERE related_bounty_task_id IS NOT NULL
        """
    )

    conn.commit()
    conn.close()

    print("Gameplay schema created successfully.")
    print("Created/verified table: gameplay_daily_sessions")
    print("Created/verified table: bounty_board_tasks")
    print("Created/verified table: terrarium_snapshots")
    print("Created/verified table: terrarium_plot_snapshots")
    print("Created/verified table: terrarium_group_rankings")
    print("Created/verified table: marketplace_events")
    print("Created/verified table: inventory_events")
    print("Created/verified table: inventory_event_bounty_tasks")
    print("Created/verified table: pouch_opening_events")
    print("Created/verified table: pouch_reward_items")
    print("Created/verified table: weekly_bounty_results")
    print("Created/verified table: staking_reward_events")
    print(
        "Created/verified table: marketplace_event_bounty_tasks"
    )
    
    


if __name__ == "__main__":
    create_gameplay_schema()