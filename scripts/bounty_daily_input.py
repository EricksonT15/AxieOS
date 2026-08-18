DAILY_DATE = "2026-08-18"

DAILY_OBSERVED_TOTAL_BP = 2050


DAILY_BOARD_ENTRIES = [
    {
        "task_id": "buy_any_axie",
        "catalog_id": "app_axie_buy_any_axie",
    },
    {
        "task_id": "open_1_premium_pouch",
        "catalog_id": "app_axie_open_1_premium_pouch",
    },
    {
        "task_id": "feed_1_regular_choco",
        "catalog_id": "app_axie_feed_1_regular_choco",
    },
    {
        "task_id": "release_beast_axie",
        "catalog_id": "app_axie_release_beast_axie",
    },
    {
        "task_id": "feed_5_regular_choco_evolved",
        "catalog_id": "app_axie_feed_5_regular_choco_evolved",
    },
    {
        "task_id": "open_3_regular_pouches",
        "catalog_id": "app_axie_open_3_regular_pouches",
    },
]

DAILY_INVENTORY = {
    "regular_choco": 10,
    "premium_choco": 1,
}


DAILY_REROLL_NUMBERS = {}


DAILY_REROLL_HISTORY = {
    "slot_5": {
        "starting_task": "buy_3_regular_choco",
        "rerolls_used": [1, 2, 3],
        "final_task": "feed_5_regular_choco_evolved",
    },
    "slot_6": {
        "starting_task": "craft_any_rune",
        "rerolls_used": [1, 2, 3],
        "final_task": "open_3_regular_pouches",
    },
    
}


DAILY_OTHER_SLIP_SPEND = {
    "regular_pouches": {
        "quantity": 10,
        "slips_spent": 100,
    },
    "premium_pouches": {
        "quantity": 3,
        "slips_spent": 150,
    },
}


DAILY_SLIP_BALANCE = 1712

DAILY_OBSERVED_ENDING_SLIPS = 1402


DAILY_STRATEGY = {
    "strategy_mode": "conserve",
    "minimum_reserve": 20,
}


DAILY_ASSET = {
    "class": "mech",
    "collectible": True,
    "evolved": True,
}