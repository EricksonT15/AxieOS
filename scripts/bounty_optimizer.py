import json
import re

from datetime import datetime

from database import connect_database


from bounty_daily_input import (
    DAILY_DATE,
    DAILY_OBSERVED_TOTAL_BP,
    DAILY_BOARD_ENTRIES,
    DAILY_INVENTORY,
    DAILY_REROLL_NUMBERS,
    DAILY_STRATEGY_MODE,
    DAILY_MINIMUM_RESERVE,
    DAILY_SLIP_BALANCE,
    DAILY_REROLL_HISTORY,
    DAILY_OTHER_SLIP_SPEND,
    DAILY_OBSERVED_ENDING_SLIPS,
)


REROLL_TIERS = {
    1: {
        "cost": 10,
        "basic": 0.35,
        "intermediate": 0.50,
        "advanced": 0.13,
        "master": 0.02,
    },
    2: {
        "cost": 10,
        "basic": 0.35,
        "intermediate": 0.50,
        "advanced": 0.13,
        "master": 0.02,
    },
    3: {
        "cost": 10,
        "basic": 0.35,
        "intermediate": 0.50,
        "advanced": 0.13,
        "master": 0.02,
    },
    4: {
        "cost": 20,
        "basic": 0.20,
        "intermediate": 0.60,
        "advanced": 0.17,
        "master": 0.03,
    },
    5: {
        "cost": 20,
        "basic": 0.20,
        "intermediate": 0.60,
        "advanced": 0.17,
        "master": 0.03,
    },
    6: {
        "cost": 20,
        "basic": 0.20,
        "intermediate": 0.60,
        "advanced": 0.17,
        "master": 0.03,
    },
    7: {
        "cost": 30,
        "basic": 0.00,
        "intermediate": 0.60,
        "advanced": 0.36,
        "master": 0.04,
    },
    8: {
        "cost": 30,
        "basic": 0.00,
        "intermediate": 0.60,
        "advanced": 0.36,
        "master": 0.04,
    },
    9: {
        "cost": 100,
        "basic": 0.00,
        "intermediate": 0.00,
        "advanced": 0.92,
        "master": 0.08,
    },
    10: {
        "cost": 100,
        "basic": 0.00,
        "intermediate": 0.00,
        "advanced": 0.92,
        "master": 0.08,
    },
}


ACTION_COST_CLASSES = {
    "buy": "capital_required",
    "feed": "inventory_consumption",
    "open": "slips_and_vrf",
    "release": "asset_destroying",
    "spend": "resource_spend",
    "craft": "resource_spend",
    "use": "resource_spend",
    "evolve": "resource_spend",
    "ascend": "resource_spend",
    "play": "gameplay_time",
    "win": "gameplay_time",
    "defeat": "gameplay_time",
    "explore": "gameplay_time",
    "reach": "gameplay_time",
}


AVOIDED_GAMES = {
    "axie den of mysteries",
}


STRATEGY_MODES = {
    "conserve",
    "rank_push",
    "master_chase",
}


STRATEGY_MODE_ALIASES = {
    "Conserve": "conserve",
    "Rank Push": "rank_push",
    "Master Chase": "master_chase",
}

RANK_PUSH_RESERVE_FACTOR = 0.5


RANK_BONUS_TIERS = [
    (1, 1, 160),
    (2, 2, 120),
    (3, 3, 100),
    (4, 5, 60),
    (6, 10, 50),
    (11, 20, 30),
    (21, 50, 20),
    (51, 100, 15),
    (101, 200, 12),
    (201, 500, 8),
    (501, 1000, 6),
    (1001, 3000, 3),
]





BOUNTY_TASK_CATALOG = {
    "app_axie_buy_any_axie": {
        "game": "app.axie",
        "difficulty": "intermediate",
        "reward_bp": 200,
        "action": "buy",
        "target": "axie",
        "quantity": 1,
        "target_filters": {},
    },

    "app_axie_buy_random_class_axie": {
        "game": "app.axie",
        "difficulty": "intermediate",
        "reward_bp": 220,
        "action": "buy",
        "target": "axie",
        "quantity": 1,
        "target_filters": {
            "class": "$random_class",
        },
    },

    "app_axie_feed_10_choco_any_axie": {
        "game": "app.axie",
        "difficulty": "intermediate",
        "reward_bp": 150,
        "action": "feed",
        "target": "axie",
        "quantity": 10,
        "resource": "regular_choco",
        "target_filters": {},
    },

    "app_axie_feed_10_choco_random_class": {
        "game": "app.axie",
        "difficulty": "intermediate",
        "reward_bp": 160,
        "action": "feed",
        "target": "axie",
        "quantity": 10,
        "resource": "regular_choco",
        "target_filters": {
            "class": "$random_class",
        },
    },

    "app_axie_feed_premium_collectible": {
        "game": "app.axie",
        "difficulty": "advanced",
        "reward_bp": 600,
        "action": "feed",
        "target": "axie",
        "quantity": 1,
        "resource": "premium_choco",
        "target_filters": {
            "collectible": True,
        },
    },

    "app_axie_feed_premium_evolved": {
        "game": "app.axie",
        "difficulty": "advanced",
        "reward_bp": 650,
        "action": "feed",
        "target": "axie",
        "quantity": 1,
        "resource": "premium_choco",
        "target_filters": {
            "evolved": True,
        },
    },

    # ========================================================
    # V0.9 — Parameterized Axie Bounty Definitions
    # ========================================================

    "app_axie_buy_class_with_part": {
        "game": "app.axie",
        "difficulty": "advanced",
        "reward_bp": 650,
        "action": "buy",
        "target": "axie",
        "quantity": 1,
        "target_filters": {
            "class": "$random_class",
            "required_part_names": (
                "$required_part_name"
            ),
        },
    },

    "app_axie_buy_evolved_axie": {
        "game": "app.axie",
        "difficulty": "advanced",
        "reward_bp": 670,
        "action": "buy",
        "target": "axie",
        "quantity": 1,
        "target_filters": {
            "evolved": True,
        },
    },

    "app_axie_feed_premium_collection": {
        "game": "app.axie",
        "difficulty": "advanced",
        "reward_bp": 650,
        "action": "feed",
        "target": "axie",
        "quantity": 1,
        "resource": "premium_choco",
        "target_filters": {
            "required_collections": (
                "$collection"
            ),
        },
    },

    "app_axie_feed_5_regular_choco_min_level": {
        "game": "app.axie",
        "difficulty": "intermediate",
        "reward_bp": 200,
        "action": "feed",
        "target": "axie",
        "quantity": 5,
        "resource": "regular_choco",
        "target_filters": {
            "min_level": "$min_level",
        },
    },

    "app_axie_release_any_axie": {
        "game": "app.axie",
        "difficulty": "advanced",
        "reward_bp": 620,
        "action": "release",
        "target": "axie",
        "quantity": 1,
        "target_filters": {},
    },

    "app_axie_release_random_class_axie": {
        "game": "app.axie",
        "difficulty": "advanced",
        "reward_bp": 650,
        "action": "release",
        "target": "axie",
        "quantity": 1,
        "target_filters": {
            "class": "$random_class",
        },
    },

    "app_axie_evolve_any_axie": {
        "game": "app.axie",
        "difficulty": "advanced",
        "reward_bp": 1600,
        "action": "evolve",
        "target": "axie",
        "quantity": 1,
        "target_filters": {},
    },

    "app_axie_ascend_min_level_axie": {
        "game": "app.axie",
        "difficulty": "advanced",
        "reward_bp": 1450,
        "action": "ascend",
        "target": "axie",
        "quantity": 1,
        "target_filters": {
            "min_level": "$min_level",
        },
    },

    "origins_win_vs_3_beast_bird_mech": {
        "game": "axie origins",
        "difficulty": "advanced",
        "reward_bp": 400,
        "action": "win",
        "target": "battle",
        "quantity": 1,
        "target_filters": {
            "opponent_axie_count": 3,
            "opponent_classes": [
                "beast",
                "bird",
                "mech",
            ],
        },
    },

    "axie_quest_harvest_5": {
        "game": "axie quest",
        "difficulty": "basic",
        "reward_bp": 20,
        "action": "harvest",
        "target": "wild_exploration",
        "quantity": 5,
        "target_filters": {},
    },

    "den_defeat_20_enemies": {
        "game": "axie den of mysteries",
        "difficulty": "advanced",
        "reward_bp": 400,
        "action": "defeat",
        "target": "enemy",
        "quantity": 20,
        "target_filters": {},
    },

    "app_axie_open_1_premium_pouch": {
        "game": "app.axie",
        "difficulty": "intermediate",
        "reward_bp": 150,
        "action": "open",
        "target": "premium_pouch",
        "quantity": 1,
        "resource": "premium_pouch",
        "target_filters": {},
    },

    "app_axie_feed_1_regular_choco": {
        "game": "app.axie",
        "difficulty": "basic",
        "reward_bp": 25,
        "action": "feed",
        "target": "axie",
        "quantity": 1,
        "resource": "regular_choco",
        "keep_override": True,
        "target_filters": {},
    },

    "app_axie_release_beast_axie": {
        "game": "app.axie",
        "difficulty": "advanced",
        "reward_bp": 650,
        "action": "release",
        "target": "axie",
        "quantity": 1,
        "target_filters": {
            "class": "beast",
        },
    },

    "app_axie_buy_3_regular_choco": {
        "game": "app.axie",
        "difficulty": "basic",
        "reward_bp": 40,
        "action": "buy",
        "target": "regular_choco",
        "quantity": 3,
        "resource": "regular_choco",
        "target_filters": {},
    },

    "origins_craft_any_rune": {
        "game": "axie origins",
        "difficulty": "basic",
        "reward_bp": 12,
        "action": "craft",
        "target": "rune",
        "quantity": 1,
        "target_filters": {},
    },

    "app_axie_feed_5_regular_choco_evolved": {
        "game": "app.axie",
        "difficulty": "intermediate",
        "reward_bp": 200,
        "action": "feed",
        "target": "axie",
        "quantity": 5,
        "resource": "regular_choco",
        "target_filters": {
            "evolved": True,
        },
    },

    "app_axie_open_3_regular_pouches": {
        "game": "app.axie",
        "difficulty": "intermediate",
        "reward_bp": 150,
        "action": "open",
        "target": "regular_pouch",
        "quantity": 3,
        "resource": "regular_pouch",
        "target_filters": {},
    },



}



def normalize_bounty_task_name(
    task_name,
):
    if not isinstance(task_name, str):
        raise ValueError(
            "Bounty task name must be a string."
        )

    normalized = " ".join(
        task_name.strip().split()
    ).casefold()

    if not normalized:
        raise ValueError(
            "Bounty task name cannot be empty."
        )

    return normalized

# ============================================================
# V0.9 — Historical Bounty Task Compatibility
# ============================================================

HISTORICAL_BOUNTY_TASK_ALIASES = {
    # --------------------------------------------------------
    # App.Axie — Premium Pouches
    # --------------------------------------------------------
    "Open 3 Premium Pouches": (
        "historical_app_axie_open_3_premium_pouches"
    ),

    # --------------------------------------------------------
    # App.Axie — Premium Choco purchases
    # --------------------------------------------------------
    "Buy 1 Premium Choco": (
        "historical_app_axie_buy_1_premium_choco"
    ),
    "1 Premium Choco": (
        "historical_app_axie_buy_1_premium_choco"
    ),

    "Buy 3 Premium Choco": (
        "historical_app_axie_buy_3_premium_choco"
    ),
    "3 Premium Choco": (
        "historical_app_axie_buy_3_premium_choco"
    ),

    "Buy 4 Premium Choco": (
        "historical_app_axie_buy_4_premium_choco"
    ),
    "4 Premium Choco": (
        "historical_app_axie_buy_4_premium_choco"
    ),

    # --------------------------------------------------------
    # App.Axie — Regular Choco purchases
    # --------------------------------------------------------
    "Buy 15 Choco": (
        "historical_app_axie_buy_15_regular_choco"
    ),
    "Buy 15 Regular Choco": (
        "historical_app_axie_buy_15_regular_choco"
    ),
    "15 Choco": (
        "historical_app_axie_buy_15_regular_choco"
    ),
    "15 Regular Choco": (
        "historical_app_axie_buy_15_regular_choco"
    ),

    # --------------------------------------------------------
    # App.Axie — Premium Choco collectible feed
    # Existing semantic equivalent:
    # app_axie_feed_premium_collectible
    # --------------------------------------------------------
    "Feed 1 Premium Choco to any Collectible Axie": (
        "app_axie_feed_premium_collectible"
    ),
    "Feed 1 Premium Choco to any Collectible Axie you own": (
        "app_axie_feed_premium_collectible"
    ),
    "1 Premium Choco to any Collectible Axie": (
        "app_axie_feed_premium_collectible"
    ),

    # --------------------------------------------------------
    # Historical gameplay tasks not represented by the
    # current V0.9 optimizer catalog.
    # --------------------------------------------------------
    "Craft 4 Ronin items": (
        "historical_craft_4_ronin_items"
    ),

    "Win 1 Curse Coliseum match": (
        "historical_win_1_curse_coliseum_match"
    ),

    "Win 1 Challenge in Dojo": (
        "historical_win_1_challenge_in_dojo"
    ),
    "1 Challenge in Dojo": (
        "historical_win_1_challenge_in_dojo"
    ),

    "Win 4 Ranked Battles": (
        "historical_origins_win_4_ranked_battles"
    ),
    "4 Ranked Battles": (
        "historical_origins_win_4_ranked_battles"
    ),
}


NORMALIZED_HISTORICAL_BOUNTY_TASK_ALIASES = {
    normalize_bounty_task_name(
        task_name
    ): task_id
    for task_name, task_id
    in HISTORICAL_BOUNTY_TASK_ALIASES.items()
}


def resolve_historical_bounty_task_id(
    action,
    requirement,
):
    """
    Resolve one historical DB Bounty row to a stable task ID.

    Resolution order:

    1. Existing V0.9 daily-board resolver.
    2. Historical compatibility aliases.

    Historical-only IDs are intentionally kept separate
    from BOUNTY_TASK_CATALOG so old data does not silently
    alter current optimizer behavior.
    """

    candidates = []

    if (
        isinstance(
            requirement,
            str,
        )
        and requirement.strip()
    ):
        candidates.append(
            requirement.strip()
        )

    if (
        isinstance(
            action,
            str,
        )
        and action.strip()
        and isinstance(
            requirement,
            str,
        )
        and requirement.strip()
    ):
        action_text = action.strip()
        requirement_text = (
            requirement.strip()
        )

        if not (
            requirement_text
            .casefold()
            .startswith(
                action_text.casefold()
            )
        ):
            candidates.append(
                f"{action_text} {requirement_text}"
            )

    # --------------------------------------------------------
    # First use the production V0.9 resolver.
    # --------------------------------------------------------

    for candidate in candidates:
        try:
            board = build_daily_board(
                [
                    candidate,
                ]
            )

        except Exception:
            continue

        if len(board) == 1:
            return {
                "task_id": next(
                    iter(board)
                ),
                "resolution_source": (
                    "V0.9_RESOLVER"
                ),
                "matched_text": candidate,
            }

    # --------------------------------------------------------
    # Historical compatibility fallback.
    # --------------------------------------------------------

    for candidate in candidates:
        normalized = (
            normalize_bounty_task_name(
                candidate
            )
        )

        task_id = (
            NORMALIZED_HISTORICAL_BOUNTY_TASK_ALIASES.get(
                normalized
            )
        )

        if task_id is not None:
            return {
                "task_id": task_id,
                "resolution_source": (
                    "HISTORICAL_COMPATIBILITY"
                ),
                "matched_text": candidate,
            }

    return {
        "task_id": None,
        "resolution_source": (
            "UNRESOLVED"
        ),
        "matched_text": None,
    }

TASK_NAME_ALIASES = {
    # --------------------------------------------------------
    # Buy Axie
    # --------------------------------------------------------
    "Buy any Axie": (
        "app_axie_buy_any_axie"
    ),
    "Buy an Axie": (
        "app_axie_buy_any_axie"
    ),
    "Any Axie": (
        "app_axie_buy_any_axie"
    ),

    # --------------------------------------------------------
    # Pouches
    # --------------------------------------------------------
    "Open 1 Premium Pouch": (
        "app_axie_open_1_premium_pouch"
    ),
    "Open a Premium Pouch": (
        "app_axie_open_1_premium_pouch"
    ),
    "1 Premium Pouch": (
        "app_axie_open_1_premium_pouch"
    ),

    "Open 3 Regular Pouches": (
        "app_axie_open_3_regular_pouches"
    ),
    "Open 3 Regular Lucky Pouches": (
        "app_axie_open_3_regular_pouches"
    ),
    "3 Regular Lucky Pouches": (
        "app_axie_open_3_regular_pouches"
    ),

    # --------------------------------------------------------
    # Regular CocoChoco feed
    # --------------------------------------------------------
    "Feed 1 Regular Choco": (
        "app_axie_feed_1_regular_choco"
    ),
    "Feed 1 Choco": (
        "app_axie_feed_1_regular_choco"
    ),
    "Feed 1 Choco to any Axie": (
        "app_axie_feed_1_regular_choco"
    ),
    "1 Regular Choco to any Axie": (
        "app_axie_feed_1_regular_choco"
    ),

    "Feed 10 Regular Choco to any Axie": (
        "app_axie_feed_10_choco_any_axie"
    ),
    "10 Regular Choco to any Axie": (
        "app_axie_feed_10_choco_any_axie"
    ),

    # --------------------------------------------------------
    # Evolved Axie feed
    # --------------------------------------------------------
    "Feed 5 Regular Choco to evolved Axie": (
        "app_axie_feed_5_regular_choco_evolved"
    ),
    "Feed 5 Choco to any Evolved Axie": (
        "app_axie_feed_5_regular_choco_evolved"
    ),
    "Feed 5 Choco to any Evolved Axie you own": (
        "app_axie_feed_5_regular_choco_evolved"
    ),
    "Feed 5 Regular Choco to any Evolved Axie": (
        "app_axie_feed_5_regular_choco_evolved"
    ),
    "Feed 5 Regular Choco to any Evolved Axie you own": (
        "app_axie_feed_5_regular_choco_evolved"
    ),
    "5 Regular Choco to any Evolved Axie": (
        "app_axie_feed_5_regular_choco_evolved"
    ),

    # --------------------------------------------------------
    # Beast release
    # --------------------------------------------------------
    "Release any Beast Axie": (
        "app_axie_release_beast_axie"
    ),

    # --------------------------------------------------------
    # Buy Regular CocoChoco
    # --------------------------------------------------------
    "Buy 3 Regular Choco": (
        "app_axie_buy_3_regular_choco"
    ),
    "Buy 3 Choco": (
        "app_axie_buy_3_regular_choco"
    ),
    "3 Regular Choco": (
        "app_axie_buy_3_regular_choco"
    ),
    "3 Choco": (
        "app_axie_buy_3_regular_choco"
    ),

    # --------------------------------------------------------
    # Origins
    # --------------------------------------------------------
    "Craft any Rune": (
        "origins_craft_any_rune"
    ),
}


def build_normalized_task_name_aliases():
    normalized_aliases = {}

    for (
        task_name,
        catalog_id,
    ) in TASK_NAME_ALIASES.items():
        normalized_name = (
            normalize_bounty_task_name(
                task_name
            )
        )

        existing_catalog_id = (
            normalized_aliases.get(
                normalized_name
            )
        )

        if (
            existing_catalog_id is not None
            and existing_catalog_id
            != catalog_id
        ):
            raise ValueError(
                "Conflicting normalized Bounty "
                "task alias: "
                f"{task_name!r}"
            )

        normalized_aliases[
            normalized_name
        ] = catalog_id

    return normalized_aliases


NORMALIZED_TASK_NAME_ALIASES = (
    build_normalized_task_name_aliases()
)



RESOURCE_NAME_ALIASES = {
    "Regular Choco": "regular_choco",
    "Premium Choco": "premium_choco",
}










def can_task_cover_task(candidate_task, other_task):
    if candidate_task["action"] != other_task["action"]:
        return False

    if candidate_task["target"] != other_task["target"]:
        return False

    if candidate_task["quantity"] < other_task["quantity"]:
        return False

    candidate_filters = candidate_task.get(
        "target_filters",
        {},
    )
    other_filters = other_task.get(
        "target_filters",
        {},
    )

    for key, value in other_filters.items():
        if candidate_filters.get(key) != value:
            return False

    return True


def asset_satisfies_task(asset_attributes, task):
    required_filters = task.get(
        "target_filters",
        {},
    )

    for key, required_value in required_filters.items():
        if asset_attributes.get(key) != required_value:
            return False

    return True


def can_share_same_action(
    task_a,
    task_b,
    asset_attributes,
):
    if task_a["action"] != task_b["action"]:
        return False

    if task_a["target"] != task_b["target"]:
        return False

    if task_a.get("resource") != task_b.get("resource"):
        return False

    if task_a["quantity"] != task_b["quantity"]:
        return False

    if not asset_satisfies_task(
        asset_attributes,
        task_a,
    ):
        return False

    if not asset_satisfies_task(
        asset_attributes,
        task_b,
    ):
        return False

    return True


def score_shared_action(
    task_a,
    task_b,
    asset_attributes,
):
    if not can_share_same_action(
        task_a,
        task_b,
        asset_attributes,
    ):
        return None

    return {
        "combined_bp": (
            task_a["reward_bp"]
            + task_b["reward_bp"]
        ),
        "resource": task_a.get("resource"),
        "quantity": task_a["quantity"],
    }


def instantiate_task(task, **parameters):
    task_instance = {
        **task,
        "target_filters": dict(
            task.get("target_filters", {})
        ),
    }

    for key, value in task_instance[
        "target_filters"
    ].items():
        if (
            isinstance(value, str)
            and value.startswith("$")
        ):
            parameter_name = value[1:]

            if parameter_name in parameters:
                task_instance[
                    "target_filters"
                ][key] = parameters[
                    parameter_name
                ]

    return task_instance



# ============================================================
# V0.9 — Bounty Task Requirement Model
# ============================================================

BOUNTY_REQUIREMENT_MODEL_VERSION = "0.9"


AXIE_BOUNTY_FILTER_TO_QUALIFICATION_KEY = {
    # Existing Bounty optimizer filter names
    "class": "axie_class",
    "collectible": "is_collectible",
    "evolved": "is_evolved",

    # V0.8 qualification criteria that may be used directly
    "axie_class": "axie_class",
    "min_level": "min_level",
    "max_level": "max_level",
    "min_breed_count": "min_breed_count",
    "max_breed_count": "max_breed_count",
    "is_collectible": "is_collectible",
    "is_evolved": "is_evolved",
    "required_collections": "required_collections",
    "any_collections": "any_collections",
    "required_part_names": "required_part_names",
    "any_part_names": "any_part_names",
    "min_ownership_days": "min_ownership_days",
}


AXIE_BOUNTY_BOOLEAN_FILTERS = {
    "collectible",
    "evolved",
    "is_collectible",
    "is_evolved",
}


AXIE_BOUNTY_LIST_FILTERS = {
    "required_collections",
    "any_collections",
    "required_part_names",
    "any_part_names",
}


def normalize_bounty_axie_class(value):
    if value is None:
        return None

    normalized = str(value).strip()

    if not normalized:
        raise ValueError(
            "Axie class requirement cannot be empty."
        )

    return normalized.title()


def normalize_bounty_requirement_list(
    filter_name,
    value,
):
    if isinstance(value, str):
        value = [value]

    if not isinstance(
        value,
        (list, tuple, set),
    ):
        raise ValueError(
            f"{filter_name} must be a string "
            "or collection of strings."
        )

    normalized = []

    for item in value:
        item_text = str(item).strip()

        if not item_text:
            raise ValueError(
                f"{filter_name} contains an empty value."
            )

        normalized.append(item_text)

    return normalized


def build_axie_qualification_criteria_from_task(
    task,
):
    """
    Translate an instantiated Axie-target Bounty task into
    the criteria vocabulary used by the V0.8 gameplay
    qualification engine.

    Returns:
        dict:
            Qualification criteria for Axie targets.

        None:
            The task does not target an Axie.
    """

    if task.get("target") != "axie":
        return None

    target_filters = task.get(
        "target_filters",
        {},
    )

    if target_filters is None:
        target_filters = {}

    if not isinstance(target_filters, dict):
        raise ValueError(
            "Axie task target_filters must be a dictionary."
        )

    criteria = {}

    for filter_name, value in target_filters.items():
        if (
            isinstance(value, str)
            and value.startswith("$")
        ):
            raise ValueError(
                "Unresolved Bounty task parameter "
                f"{value!r} in filter "
                f"{filter_name!r}. "
                "Instantiate the task before translating it."
            )

        qualification_key = (
            AXIE_BOUNTY_FILTER_TO_QUALIFICATION_KEY.get(
                filter_name
            )
        )

        if qualification_key is None:
            raise ValueError(
                "Unsupported Axie Bounty target filter: "
                f"{filter_name!r}"
            )

        if filter_name in AXIE_BOUNTY_BOOLEAN_FILTERS:
            if not isinstance(value, bool):
                raise ValueError(
                    f"{filter_name} must be True or False."
                )

        if filter_name in AXIE_BOUNTY_LIST_FILTERS:
            value = normalize_bounty_requirement_list(
                filter_name,
                value,
            )

        if qualification_key == "axie_class":
            value = normalize_bounty_axie_class(
                value
            )

        criteria[qualification_key] = value

    return criteria


def run_v09_bounty_requirement_model_test():
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 BOUNTY REQUIREMENT MODEL TEST"
    )
    print(
        "============================================================"
    )

    test_cases = []

    any_axie = instantiate_task(
        BOUNTY_TASK_CATALOG[
            "app_axie_buy_any_axie"
        ]
    )

    test_cases.append(
        (
            "Any Axie",
            build_axie_qualification_criteria_from_task(
                any_axie
            ),
            {},
        )
    )

    collectible = instantiate_task(
        BOUNTY_TASK_CATALOG[
            "app_axie_feed_premium_collectible"
        ]
    )

    test_cases.append(
        (
            "Collectible Axie",
            build_axie_qualification_criteria_from_task(
                collectible
            ),
            {
                "is_collectible": True,
            },
        )
    )

    evolved = instantiate_task(
        BOUNTY_TASK_CATALOG[
            "app_axie_feed_premium_evolved"
        ]
    )

    test_cases.append(
        (
            "Evolved Axie",
            build_axie_qualification_criteria_from_task(
                evolved
            ),
            {
                "is_evolved": True,
            },
        )
    )

    beast_release = instantiate_task(
        BOUNTY_TASK_CATALOG[
            "app_axie_release_beast_axie"
        ]
    )

    test_cases.append(
        (
            "Beast Axie",
            build_axie_qualification_criteria_from_task(
                beast_release
            ),
            {
                "axie_class": "Beast",
            },
        )
    )

    random_class = instantiate_task(
        BOUNTY_TASK_CATALOG[
            "app_axie_buy_random_class_axie"
        ],
        random_class="aquatic",
    )

    test_cases.append(
        (
            "Dynamic Random Class",
            build_axie_qualification_criteria_from_task(
                random_class
            ),
            {
                "axie_class": "Aquatic",
            },
        )
    )

    non_axie_task = instantiate_task(
        BOUNTY_TASK_CATALOG[
            "origins_win_vs_3_beast_bird_mech"
        ]
    )

    test_cases.append(
        (
            "Non-Axie Target",
            build_axie_qualification_criteria_from_task(
                non_axie_task
            ),
            None,
        )
    )

    all_passed = True

    for (
        label,
        actual,
        expected,
    ) in test_cases:
        passed = actual == expected

        print(
            f"{label}: "
            f"{'PASS' if passed else 'FAIL'}"
        )
        print(
            "  Actual:",
            actual,
        )
        print(
            "  Expected:",
            expected,
        )

        if not passed:
            all_passed = False

    unresolved_parameter_passed = False

    try:
        unresolved_task = instantiate_task(
            BOUNTY_TASK_CATALOG[
                "app_axie_buy_random_class_axie"
            ]
        )

        build_axie_qualification_criteria_from_task(
            unresolved_task
        )

    except ValueError as exc:
        unresolved_parameter_passed = True

        print(
            "Unresolved parameter guardrail: PASS"
        )
        print(
            "  Message:",
            str(exc),
        )

    else:
        print(
            "Unresolved parameter guardrail: FAIL"
        )
        all_passed = False

    if not unresolved_parameter_passed:
        all_passed = False

    print(
        "\nRequirement model version:",
        BOUNTY_REQUIREMENT_MODEL_VERSION,
    )

    print(
        "V0.9 Bounty Requirement Model:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed




# ============================================================
# V0.9 — Live Owned-Axie Candidate Resolution
# ============================================================

AXIE_OWNED_CANDIDATE_ACTIONS = {
    "feed",
    "release",
    "use",
    "evolve",
    "ascend",
}



def find_owned_axie_candidates_for_bounty_task(
    db_path,
    task,
    as_of_datetime=None,
):
    """
    Resolve exact currently owned Axies that can satisfy
    an instantiated Bounty task.

    Only actions that operate on an already-owned Axie
    are eligible for owned-roster matching.

    Buy tasks may still contain Axie qualification criteria,
    but those criteria describe the asset to acquire and
    must not be matched against the current owned roster.
    """

    criteria = (
        build_axie_qualification_criteria_from_task(
            task
        )
    )

    action = str(
        task.get("action") or ""
    ).strip().lower()

    if criteria is None:
        return {
            "applicable": False,
            "reason": "NON_AXIE_TARGET",
            "action": action,
            "criteria": None,
            "total_owned": None,
            "qualified_axie_ids": [],
            "disqualified_axie_ids": [],
            "unknown_axie_ids": [],
        }

    if action not in AXIE_OWNED_CANDIDATE_ACTIONS:
        return {
            "applicable": False,
            "reason": (
                "ACTION_DOES_NOT_USE_CURRENT_OWNED_AXIE"
            ),
            "action": action,
            "criteria": criteria,
            "total_owned": None,
            "qualified_axie_ids": [],
            "disqualified_axie_ids": [],
            "unknown_axie_ids": [],
        }

    # Local import keeps the existing optimizer startup
    # independent from the larger gameplay-data module
    # until live Axie qualification is actually requested.
    from gameplay_data import qualify_owned_axies

    qualification = qualify_owned_axies(
        db_path=db_path,
        criteria=criteria,
        as_of_datetime=as_of_datetime,
    )

    qualified_axie_ids = [
        str(profile["axie_id"])
        for profile
        in qualification["qualified"]
    ]

    disqualified_axie_ids = [
        str(profile["axie_id"])
        for profile
        in qualification["disqualified"]
    ]

    unknown_axie_ids = [
        str(profile["axie_id"])
        for profile
        in qualification["unknown"]
    ]

    return {
        "applicable": True,
        "reason": None,
        "action": action,
        "criteria": criteria,
        "total_owned": qualification[
            "total_owned"
        ],
        "qualified_axie_ids": (
            qualified_axie_ids
        ),
        "disqualified_axie_ids": (
            disqualified_axie_ids
        ),
        "unknown_axie_ids": (
            unknown_axie_ids
        ),
    }



def enrich_board_with_owned_axie_candidates(
    db_path,
    task_map,
    as_of_datetime=None,
):
    """
    Return a copy of the Bounty task map enriched with
    current owned-Axie qualification results.

    Existing task definitions are preserved.

    Axie-target actions that operate on an already-owned
    Axie receive exact eligible Axie IDs.

    Buy tasks and non-Axie targets remain explicitly
    non-applicable to owned-roster matching.
    """

    enriched_board = {}

    for task_id, task in task_map.items():
        enriched_task = {
            **task,
            "target_filters": dict(
                task.get(
                    "target_filters",
                    {},
                )
            ),
        }

        candidate_result = (
            find_owned_axie_candidates_for_bounty_task(
                db_path=db_path,
                task=enriched_task,
                as_of_datetime=as_of_datetime,
            )
        )

        enriched_task[
            "owned_axie_candidate_applicable"
        ] = candidate_result[
            "applicable"
        ]

        enriched_task[
            "owned_axie_candidate_reason"
        ] = candidate_result[
            "reason"
        ]

        enriched_task[
            "eligible_owned_axie_ids"
        ] = list(
            candidate_result[
                "qualified_axie_ids"
            ]
        )

        enriched_task[
            "unknown_owned_axie_ids"
        ] = list(
            candidate_result[
                "unknown_axie_ids"
            ]
        )

        enriched_task[
            "eligible_owned_axie_count"
        ] = len(
            candidate_result[
                "qualified_axie_ids"
            ]
        )

        enriched_task[
            "unknown_owned_axie_count"
        ] = len(
            candidate_result[
                "unknown_axie_ids"
            ]
        )

        enriched_task[
            "axie_qualification_criteria"
        ] = candidate_result[
            "criteria"
        ]

        enriched_board[
            task_id
        ] = enriched_task

    return enriched_board


def run_v09_board_axie_enrichment_test(
    db_path,
):
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 BOARD AXIE ENRICHMENT TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    board_entries = [
        "Feed 10 Regular Choco to any Axie",
        (
            "Feed 1 Premium Choco to any "
            "Shiny Axie you own"
        ),
        (
            "Feed 5 Regular Choco to any "
            "Level 20 or higher Axie you own"
        ),
        "Release any Dawn Axie",
        "Buy any Bug Axie",
        "Open 1 Premium Pouch",
    ]

    board = build_daily_board(
        board_entries
    )

    enriched = (
        enrich_board_with_owned_axie_candidates(
            db_path=db_path,
            task_map=board,
        )
    )

    # --------------------------------------------------------
    # Test 1 — unrestricted owned-Axie feed
    # --------------------------------------------------------

    any_feed = enriched[
        "feed_10_choco_any_axie"
    ]

    any_feed_passed = (
        any_feed[
            "owned_axie_candidate_applicable"
        ]
        and any_feed[
            "eligible_owned_axie_count"
        ] > 0
        and not any_feed[
            "unknown_owned_axie_ids"
        ]
    )

    print(
        "Any owned-Axie feed:",
        "PASS" if any_feed_passed else "FAIL",
    )
    print(
        "  Eligible:",
        any_feed[
            "eligible_owned_axie_count"
        ],
    )

    if not any_feed_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 2 — Shiny collection
    # --------------------------------------------------------

    shiny = enriched[
        "feed_premium_collection"
    ]

    shiny_passed = (
        shiny[
            "owned_axie_candidate_applicable"
        ]
        and shiny[
            "axie_qualification_criteria"
        ] == {
            "required_collections": [
                "SHINY",
            ],
        }
        and shiny[
            "eligible_owned_axie_count"
        ] > 0
    )

    print(
        "Shiny owned-Axie feed:",
        "PASS" if shiny_passed else "FAIL",
    )
    print(
        "  Eligible IDs:",
        shiny[
            "eligible_owned_axie_ids"
        ],
    )

    if not shiny_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 3 — Level 20+
    # --------------------------------------------------------

    level_task = enriched[
        "feed_5_regular_choco_min_level"
    ]

    level_passed = (
        level_task[
            "owned_axie_candidate_applicable"
        ]
        and level_task[
            "axie_qualification_criteria"
        ] == {
            "min_level": 20,
        }
        and level_task[
            "eligible_owned_axie_count"
        ] > 0
    )

    print(
        "Level 20+ owned-Axie feed:",
        "PASS" if level_passed else "FAIL",
    )
    print(
        "  Eligible:",
        level_task[
            "eligible_owned_axie_count"
        ],
    )
    print(
        "  Unknown:",
        level_task[
            "unknown_owned_axie_count"
        ],
    )

    if not level_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 4 — Dawn release
    # --------------------------------------------------------

    dawn = enriched[
        "release_random_class_axie"
    ]

    dawn_passed = (
        dawn[
            "owned_axie_candidate_applicable"
        ]
        and dawn[
            "axie_qualification_criteria"
        ] == {
            "axie_class": "Dawn",
        }
    )

    print(
        "Dawn release candidates:",
        "PASS" if dawn_passed else "FAIL",
    )
    print(
        "  Eligible IDs:",
        dawn[
            "eligible_owned_axie_ids"
        ],
    )

    if not dawn_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 5 — Buy task must not use owned roster
    # --------------------------------------------------------

    buy_bug = enriched[
        "buy_random_class_axie"
    ]

    buy_passed = (
        not buy_bug[
            "owned_axie_candidate_applicable"
        ]
        and buy_bug[
            "owned_axie_candidate_reason"
        ] == (
            "ACTION_DOES_NOT_USE_CURRENT_OWNED_AXIE"
        )
        and not buy_bug[
            "eligible_owned_axie_ids"
        ]
    )

    print(
        "Buy-task owned-roster guardrail:",
        "PASS" if buy_passed else "FAIL",
    )

    if not buy_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 6 — Non-Axie task
    # --------------------------------------------------------

    pouch = enriched[
        "open_1_premium_pouch"
    ]

    pouch_passed = (
        not pouch[
            "owned_axie_candidate_applicable"
        ]
        and pouch[
            "owned_axie_candidate_reason"
        ] == "NON_AXIE_TARGET"
    )

    print(
        "Non-Axie task:",
        "PASS" if pouch_passed else "FAIL",
    )

    if not pouch_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 7 — Original task structure remains intact
    # --------------------------------------------------------

    preservation_passed = all(
        (
            task_id in enriched
            and enriched[
                task_id
            ]["action"]
            == board[
                task_id
            ]["action"]
            and enriched[
                task_id
            ]["reward_bp"]
            == board[
                task_id
            ]["reward_bp"]
        )
        for task_id in board
    )

    print(
        "Existing task data preserved:",
        (
            "PASS"
            if preservation_passed
            else "FAIL"
        ),
    )

    if not preservation_passed:
        all_passed = False

    print(
        "\nV0.9 Board Axie Enrichment:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



def run_v09_owned_axie_candidate_test(
    db_path,
):
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 OWNED-AXIE CANDIDATE TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    # --------------------------------------------------------
    # Test 1 — Feed any owned Axie
    # --------------------------------------------------------

    any_owned_axie_task = instantiate_task(
        BOUNTY_TASK_CATALOG[
            "app_axie_feed_10_choco_any_axie"
        ]
    )

    any_owned_result = (
        find_owned_axie_candidates_for_bounty_task(
            db_path,
            any_owned_axie_task,
        )
    )

    any_owned_passed = (
        any_owned_result["applicable"]
        and (
            len(
                any_owned_result[
                    "qualified_axie_ids"
                ]
            )
            == any_owned_result[
                "total_owned"
            ]
        )
        and not any_owned_result[
            "disqualified_axie_ids"
        ]
        and not any_owned_result[
            "unknown_axie_ids"
        ]
    )

    print(
        "Feed any owned Axie:",
        "PASS" if any_owned_passed else "FAIL",
    )
    print(
        "  Total owned:",
        any_owned_result["total_owned"],
    )
    print(
        "  Qualified:",
        len(
            any_owned_result[
                "qualified_axie_ids"
            ]
        ),
    )

    if not any_owned_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 2 — Collectible Axie
    # --------------------------------------------------------

    collectible_task = instantiate_task(
        BOUNTY_TASK_CATALOG[
            "app_axie_feed_premium_collectible"
        ]
    )

    collectible_result = (
        find_owned_axie_candidates_for_bounty_task(
            db_path,
            collectible_task,
        )
    )

    collectible_partition = (
        len(
            collectible_result[
                "qualified_axie_ids"
            ]
        )
        + len(
            collectible_result[
                "disqualified_axie_ids"
            ]
        )
        + len(
            collectible_result[
                "unknown_axie_ids"
            ]
        )
    )

    collectible_passed = (
        collectible_result["applicable"]
        and collectible_result[
            "criteria"
        ] == {
            "is_collectible": True,
        }
        and collectible_partition
        == collectible_result[
            "total_owned"
        ]
        and len(
            collectible_result[
                "qualified_axie_ids"
            ]
        ) > 0
    )

    print(
        "Collectible owned Axies:",
        (
            "PASS"
            if collectible_passed
            else "FAIL"
        ),
    )
    print(
        "  Qualified IDs:",
        collectible_result[
            "qualified_axie_ids"
        ],
    )
    print(
        "  Unknown:",
        len(
            collectible_result[
                "unknown_axie_ids"
            ]
        ),
    )

    if not collectible_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 3 — Evolved Axie
    # --------------------------------------------------------

    evolved_task = instantiate_task(
        BOUNTY_TASK_CATALOG[
            "app_axie_feed_premium_evolved"
        ]
    )

    evolved_result = (
        find_owned_axie_candidates_for_bounty_task(
            db_path,
            evolved_task,
        )
    )

    evolved_partition = (
        len(
            evolved_result[
                "qualified_axie_ids"
            ]
        )
        + len(
            evolved_result[
                "disqualified_axie_ids"
            ]
        )
        + len(
            evolved_result[
                "unknown_axie_ids"
            ]
        )
    )

    evolved_passed = (
        evolved_result["applicable"]
        and evolved_result[
            "criteria"
        ] == {
            "is_evolved": True,
        }
        and evolved_partition
        == evolved_result[
            "total_owned"
        ]
        and len(
            evolved_result[
                "qualified_axie_ids"
            ]
        ) > 0
    )

    print(
        "Evolved owned Axies:",
        "PASS" if evolved_passed else "FAIL",
    )
    print(
        "  Qualified:",
        len(
            evolved_result[
                "qualified_axie_ids"
            ]
        ),
    )
    print(
        "  Unknown:",
        len(
            evolved_result[
                "unknown_axie_ids"
            ]
        ),
    )

    if not evolved_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 4 — Buy task must NOT use owned roster
    # --------------------------------------------------------

    buy_task = instantiate_task(
        BOUNTY_TASK_CATALOG[
            "app_axie_buy_any_axie"
        ]
    )

    buy_result = (
        find_owned_axie_candidates_for_bounty_task(
            db_path,
            buy_task,
        )
    )

    buy_guardrail_passed = (
        not buy_result["applicable"]
        and buy_result["reason"]
        == (
            "ACTION_DOES_NOT_USE_CURRENT_OWNED_AXIE"
        )
        and not buy_result[
            "qualified_axie_ids"
        ]
    )

    print(
        "Buy-task owned-roster guardrail:",
        (
            "PASS"
            if buy_guardrail_passed
            else "FAIL"
        ),
    )

    if not buy_guardrail_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 5 — Non-Axie target
    # --------------------------------------------------------

    non_axie_task = instantiate_task(
        BOUNTY_TASK_CATALOG[
            "origins_win_vs_3_beast_bird_mech"
        ]
    )

    non_axie_result = (
        find_owned_axie_candidates_for_bounty_task(
            db_path,
            non_axie_task,
        )
    )

    non_axie_passed = (
        not non_axie_result["applicable"]
        and non_axie_result["reason"]
        == "NON_AXIE_TARGET"
    )

    print(
        "Non-Axie target guardrail:",
        "PASS" if non_axie_passed else "FAIL",
    )

    if not non_axie_passed:
        all_passed = False

    print(
        "\nV0.9 Owned-Axie Candidate Resolution:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



def run_v09_advanced_requirement_model_test(
    db_path,
):
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 ADVANCED REQUIREMENT MODEL TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    test_cases = [
        {
            "label": "Japanese collectible",
            "task": {
                "action": "feed",
                "target": "axie",
                "quantity": 1,
                "resource": "premium_choco",
                "target_filters": {
                    "required_collections": [
                        "JAPANESE",
                    ],
                },
            },
            "expected_criteria": {
                "required_collections": [
                    "JAPANESE",
                ],
            },
        },
        {
            "label": "Pincer body part",
            "task": {
                "action": "feed",
                "target": "axie",
                "quantity": 1,
                "resource": "premium_choco",
                "target_filters": {
                    "required_part_names": [
                        "Pincer",
                    ],
                },
            },
            "expected_criteria": {
                "required_part_names": [
                    "Pincer",
                ],
            },
        },
        {
            "label": "Level 20+",
            "task": {
                "action": "feed",
                "target": "axie",
                "quantity": 1,
                "resource": "regular_choco",
                "target_filters": {
                    "min_level": 20,
                },
            },
            "expected_criteria": {
                "min_level": 20,
            },
        },
        {
            "label": "Owned 1+ day",
            "task": {
                "action": "feed",
                "target": "axie",
                "quantity": 1,
                "resource": "regular_choco",
                "target_filters": {
                    "min_ownership_days": 1,
                },
            },
            "expected_criteria": {
                "min_ownership_days": 1,
            },
        },
        {
            "label": "Evolved + Pincer",
            "task": {
                "action": "feed",
                "target": "axie",
                "quantity": 1,
                "resource": "premium_choco",
                "target_filters": {
                    "evolved": True,
                    "required_part_names": [
                        "Pincer",
                    ],
                },
            },
            "expected_criteria": {
                "is_evolved": True,
                "required_part_names": [
                    "Pincer",
                ],
            },
        },
    ]

    for test_case in test_cases:
        result = (
            find_owned_axie_candidates_for_bounty_task(
                db_path=db_path,
                task=test_case["task"],
            )
        )

        partition_count = (
            len(
                result[
                    "qualified_axie_ids"
                ]
            )
            + len(
                result[
                    "disqualified_axie_ids"
                ]
            )
            + len(
                result[
                    "unknown_axie_ids"
                ]
            )
        )

        passed = (
            result["applicable"]
            and result["criteria"]
            == test_case[
                "expected_criteria"
            ]
            and partition_count
            == result["total_owned"]
        )

        print(
            f"{test_case['label']}:",
            "PASS" if passed else "FAIL",
        )

        print(
            "  Criteria:",
            result["criteria"],
        )

        print(
            "  Qualified:",
            len(
                result[
                    "qualified_axie_ids"
                ]
            ),
        )

        print(
            "  Qualified IDs:",
            result[
                "qualified_axie_ids"
            ],
        )

        print(
            "  Disqualified:",
            len(
                result[
                    "disqualified_axie_ids"
                ]
            ),
        )

        print(
            "  Unknown:",
            len(
                result[
                    "unknown_axie_ids"
                ]
            ),
        )

        if not passed:
            all_passed = False

    print(
        "\nV0.9 Advanced Requirement Model:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



def run_v09_parameterized_axie_catalog_test():
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 PARAMETERIZED AXIE CATALOG TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    test_cases = [
        {
            "label": "Bird + Scaly Spear purchase",
            "catalog_id": (
                "app_axie_buy_class_with_part"
            ),
            "parameters": {
                "random_class": "bird",
                "required_part_name": (
                    "Scaly Spear"
                ),
            },
            "expected": {
                "axie_class": "Bird",
                "required_part_names": [
                    "Scaly Spear",
                ],
            },
        },
        {
            "label": "Plant + Cuckoo purchase",
            "catalog_id": (
                "app_axie_buy_class_with_part"
            ),
            "parameters": {
                "random_class": "plant",
                "required_part_name": "Cuckoo",
            },
            "expected": {
                "axie_class": "Plant",
                "required_part_names": [
                    "Cuckoo",
                ],
            },
        },
        {
            "label": "Evolved Axie purchase",
            "catalog_id": (
                "app_axie_buy_evolved_axie"
            ),
            "parameters": {},
            "expected": {
                "is_evolved": True,
            },
        },
        {
            "label": "Japanese collectible feed",
            "catalog_id": (
                "app_axie_feed_premium_collection"
            ),
            "parameters": {
                "collection": "JAPANESE",
            },
            "expected": {
                "required_collections": [
                    "JAPANESE",
                ],
            },
        },
        {
            "label": "Shiny collectible feed",
            "catalog_id": (
                "app_axie_feed_premium_collection"
            ),
            "parameters": {
                "collection": "SHINY",
            },
            "expected": {
                "required_collections": [
                    "SHINY",
                ],
            },
        },
        {
            "label": "Level 20+ feed",
            "catalog_id": (
                "app_axie_"
                "feed_5_regular_choco_min_level"
            ),
            "parameters": {
                "min_level": 20,
            },
            "expected": {
                "min_level": 20,
            },
        },
        {
            "label": "Any Axie release",
            "catalog_id": (
                "app_axie_release_any_axie"
            ),
            "parameters": {},
            "expected": {},
        },
        {
            "label": "Dawn Axie release",
            "catalog_id": (
                "app_axie_"
                "release_random_class_axie"
            ),
            "parameters": {
                "random_class": "dawn",
            },
            "expected": {
                "axie_class": "Dawn",
            },
        },
        {
            "label": "Any Axie evolution",
            "catalog_id": (
                "app_axie_evolve_any_axie"
            ),
            "parameters": {},
            "expected": {},
        },
        {
            "label": "Level 19+ ascension",
            "catalog_id": (
                "app_axie_ascend_min_level_axie"
            ),
            "parameters": {
                "min_level": 19,
            },
            "expected": {
                "min_level": 19,
            },
        },
    ]

    for test_case in test_cases:
        catalog_task = (
            BOUNTY_TASK_CATALOG[
                test_case["catalog_id"]
            ]
        )

        task = instantiate_task(
            catalog_task,
            **test_case["parameters"],
        )

        actual = (
            build_axie_qualification_criteria_from_task(
                task
            )
        )

        passed = (
            actual
            == test_case["expected"]
        )

        print(
            f"{test_case['label']}:",
            "PASS" if passed else "FAIL",
        )

        print(
            "  Actual:",
            actual,
        )

        print(
            "  Expected:",
            test_case["expected"],
        )

        if not passed:
            all_passed = False

    # --------------------------------------------------------
    # Missing-parameter guardrail
    # --------------------------------------------------------

    missing_parameter_passed = False

    try:
        incomplete_task = instantiate_task(
            BOUNTY_TASK_CATALOG[
                "app_axie_buy_class_with_part"
            ],
            random_class="bird",
        )

        build_axie_qualification_criteria_from_task(
            incomplete_task
        )

    except ValueError as exc:
        missing_parameter_passed = True

        print(
            "Missing parameter guardrail: PASS"
        )
        print(
            "  Message:",
            str(exc),
        )

    else:
        print(
            "Missing parameter guardrail: FAIL"
        )
        all_passed = False

    if not missing_parameter_passed:
        all_passed = False

    print(
        "\nV0.9 Parameterized Axie Catalog:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



def is_avoided_game(game_name):
    if not game_name:
        return False

    return game_name.strip().lower() in AVOIDED_GAMES






def get_reroll_tier(reroll_number):
    return REROLL_TIERS.get(reroll_number)





def get_next_reroll_info(rerolls_used):
    next_reroll_number = rerolls_used + 1

    if next_reroll_number > 10:
        return None

    tier = get_reroll_tier(next_reroll_number)

    return {
        "reroll_number": next_reroll_number,
        "cost": tier["cost"],
        "basic": tier["basic"],
        "intermediate": tier["intermediate"],
        "advanced": tier["advanced"],
        "master": tier["master"],
    }


def format_reroll_distribution(reroll_info):
    if reroll_info is None:
        return "No rerolls remaining"

    high_value_chance = (
        reroll_info["advanced"]
        + reroll_info["master"]
    )

    return (
        f"Basic {reroll_info['basic']:.0%} | "
        f"Intermediate {reroll_info['intermediate']:.0%} | "
        f"Advanced {reroll_info['advanced']:.0%} | "
        f"Master {reroll_info['master']:.0%} | "
        f"Advanced+ {high_value_chance:.0%}"
    )


def get_reroll_cost_level(cost):
    if cost <= 10:
        return "LOW"

    if cost <= 20:
        return "MODERATE"

    if cost <= 30:
        return "HIGH"

    return "VERY HIGH"


def get_empirical_bp_by_difficulty(conn):
    rows = conn.execute(
        """
        SELECT
            LOWER(TRIM(difficulty)) AS difficulty,
            COUNT(*) AS observations,
            AVG(reward_bp) AS avg_bp,
            MIN(reward_bp) AS min_bp,
            MAX(reward_bp) AS max_bp
        FROM bounty_board_tasks
        WHERE difficulty IS NOT NULL
          AND reward_bp IS NOT NULL
          AND reward_bp > 0
        GROUP BY LOWER(TRIM(difficulty))
        """
    ).fetchall()

    return {
        difficulty: {
            "observations": observations,
            "avg_bp": avg_bp,
            "min_bp": min_bp,
            "max_bp": max_bp,
        }
        for (
            difficulty,
            observations,
            avg_bp,
            min_bp,
            max_bp,
        ) in rows
    }


def estimate_expected_bp(reroll_info, difficulty_stats):
    expected_bp = 0.0
    covered_probability = 0.0
    missing_difficulties = []

    for difficulty in [
        "basic",
        "intermediate",
        "advanced",
        "master",
    ]:
        probability = reroll_info[difficulty]

        if probability == 0:
            continue

        stats = difficulty_stats.get(difficulty)

        if stats is None:
            missing_difficulties.append(difficulty)
            continue

        expected_bp += (
            probability
            * stats["avg_bp"]
        )

        covered_probability += probability

        if covered_probability > 0:
            provisional_expected_bp = (
                expected_bp / covered_probability
            )
        else:
            provisional_expected_bp = 0.0

    return {
        "known_expected_bp": expected_bp,
        "provisional_expected_bp": provisional_expected_bp,
        "covered_probability": covered_probability,
        "missing_difficulties": missing_difficulties,
    }


def estimate_reroll_value(
    current_bp,
    rerolls_used,
    difficulty_stats,
):
    reroll_info = get_next_reroll_info(rerolls_used)

    if reroll_info is None:
        return None

    estimate = estimate_expected_bp(
        reroll_info,
        difficulty_stats,
    )

    expected_gain = (
    estimate["provisional_expected_bp"]
    - current_bp
    )

    gain_per_slip = (
        expected_gain / reroll_info["cost"]
    )

    return {
        "reroll_info": reroll_info,
        "known_expected_bp": estimate["known_expected_bp"],
        "provisional_expected_bp": estimate["provisional_expected_bp"],
        "expected_gain": expected_gain,
        "gain_per_slip": gain_per_slip,
        "covered_probability": estimate["covered_probability"],
        "missing_difficulties": estimate["missing_difficulties"],
    }


def get_empirical_bp_by_action(conn):
    rows = conn.execute(
        """
        SELECT
            LOWER(TRIM(action)) AS action,
            COUNT(*) AS observations,
            AVG(reward_bp) AS avg_bp,
            MIN(reward_bp) AS min_bp,
            MAX(reward_bp) AS max_bp
        FROM bounty_board_tasks
        WHERE action IS NOT NULL
          AND reward_bp IS NOT NULL
          AND reward_bp > 0
        GROUP BY LOWER(TRIM(action))
        ORDER BY observations DESC
        """
    ).fetchall()

    return {
        action: {
            "observations": observations,
            "avg_bp": avg_bp,
            "min_bp": min_bp,
            "max_bp": max_bp,
        }
        for (
            action,
            observations,
            avg_bp,
            min_bp,
            max_bp,
        ) in rows
    }


def get_empirical_bp_by_difficulty_action(conn):
    rows = conn.execute(
        """
        SELECT
            LOWER(TRIM(difficulty)) AS difficulty,
            LOWER(TRIM(action)) AS action,
            COUNT(*) AS observations,
            AVG(reward_bp) AS avg_bp,
            MIN(reward_bp) AS min_bp,
            MAX(reward_bp) AS max_bp
        FROM bounty_board_tasks
        WHERE difficulty IS NOT NULL
            AND TRIM(difficulty) <> ''
            AND action IS NOT NULL
            AND TRIM(action) <> ''
            AND reward_bp IS NOT NULL
            AND reward_bp > 0
        GROUP BY
            LOWER(TRIM(difficulty)),
            LOWER(TRIM(action))
        ORDER BY
            difficulty,
            observations DESC
        """
    ).fetchall()

    return rows


def get_difficulty_action_profile(
    difficulty_action_stats,
    difficulty,
    action,
):
    difficulty = difficulty.strip().lower()
    action = action.strip().lower()

    for (
        row_difficulty,
        row_action,
        observations,
        avg_bp,
        min_bp,
        max_bp,
    ) in difficulty_action_stats:
        if (
            row_difficulty == difficulty
            and row_action == action
        ):
            return {
                "observations": observations,
                "avg_bp": avg_bp,
                "min_bp": min_bp,
                "max_bp": max_bp,
            }

    return None


def get_action_cost_class(action):
    if not action:
        return "unknown"

    return ACTION_COST_CLASSES.get(
        action.strip().lower(),
        "unknown",
    )



# ============================================================
# V0.9 — Bounty Economics Model
# ============================================================

BOUNTY_ECONOMICS_MODEL_VERSION = "0.9"


def parse_nonnegative_economic_decimal(
    value,
    field_name,
):
    from decimal import Decimal, InvalidOperation

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be a non-negative number."
        )

    if value is None:
        raise ValueError(
            f"{field_name} is required."
        )

    try:
        result = Decimal(
            str(value)
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ) as exc:
        raise ValueError(
            f"{field_name} must be a non-negative number."
        ) from exc

    if (
        not result.is_finite()
        or result < 0
    ):
        raise ValueError(
            f"{field_name} must be a non-negative number."
        )

    return result


def format_economic_decimal(
    value,
):
    text = format(
        value,
        "f",
    )

    if "." in text:
        text = text.rstrip(
            "0"
        ).rstrip(
            "."
        )

    if text in {
        "",
        "-0",
    }:
        return "0"

    return text


def normalize_non_weth_costs(
    non_weth_costs,
):
    if non_weth_costs is None:
        return {}

    if not isinstance(
        non_weth_costs,
        dict,
    ):
        raise ValueError(
            "non_weth_costs must be a dictionary."
        )

    normalized = {}

    for currency, amount in (
        non_weth_costs.items()
    ):
        if not isinstance(
            currency,
            str,
        ):
            raise ValueError(
                "Non-WETH cost currency names "
                "must be strings."
            )

        normalized_currency = (
            currency.strip().upper()
        )

        if not normalized_currency:
            raise ValueError(
                "Non-WETH cost currency names "
                "cannot be empty."
            )

        normalized_amount = (
            parse_nonnegative_economic_decimal(
                amount,
                (
                    "non_weth_costs"
                    f"[{currency!r}]"
                ),
            )
        )

        normalized[
            normalized_currency
        ] = format_economic_decimal(
            normalized_amount
        )

    return normalized


def build_empty_bounty_economic_state(
    task_id,
    task,
    status,
    reason,
):
    action = task.get(
        "action"
    )

    return {
        "economic_model_version": (
            BOUNTY_ECONOMICS_MODEL_VERSION
        ),
        "economic_applicable": (
            get_action_cost_class(
                action
            )
            != "gameplay_time"
        ),
        "economic_status": status,
        "economic_reason": reason,
        "task": task_id,
        "action": action,
        "action_cost_class": (
            get_action_cost_class(
                action
            )
        ),
        "estimated_gross_cost_weth": None,
        "estimated_recovery_weth": None,
        "estimated_net_cost_weth": None,
        "bp_per_0_001_weth": None,
        "economic_efficiency_status": None,
        "non_weth_costs": {},
        "economic_basis": None,
        "economic_confidence": None,
        "economic_notes": None,
        "missing_fields": [],
    }


def evaluate_bounty_task_economics(
    task_id,
    task,
    economics_inputs=None,
):
    """
    Evaluate forward-looking economics for one Bounty task.

    Required profile fields:

        gross_cost_weth
        expected_recovery_weth
        basis
        confidence

    Missing values never default to zero.

    Optional non-WETH costs remain in their original
    currencies and are not converted into WETH.
    """

    action = task.get(
        "action"
    )

    action_cost_class = (
        get_action_cost_class(
            action
        )
    )

    # --------------------------------------------------------
    # Gameplay-only tasks do not require WETH economics.
    # --------------------------------------------------------

    if action_cost_class == "gameplay_time":
        state = (
            build_empty_bounty_economic_state(
                task_id=task_id,
                task=task,
                status="NOT_APPLICABLE",
                reason=(
                    "Task is classified as gameplay time "
                    "rather than a direct economic spend."
                ),
            )
        )

        state[
            "economic_applicable"
        ] = False

        return state

    # --------------------------------------------------------
    # No economics input supplied.
    # --------------------------------------------------------

    if economics_inputs is None:
        return build_empty_bounty_economic_state(
            task_id=task_id,
            task=task,
            status="INPUT_REQUIRED",
            reason=(
                "No economics input was supplied "
                "for this task."
            ),
        )

    if not isinstance(
        economics_inputs,
        dict,
    ):
        raise ValueError(
            "economics_inputs must be a dictionary."
        )

    task_profiles = economics_inputs.get(
        "task_profiles",
        {},
    )

    if not isinstance(
        task_profiles,
        dict,
    ):
        raise ValueError(
            "economics_inputs['task_profiles'] "
            "must be a dictionary."
        )

    profile = task_profiles.get(
        task_id
    )

    if profile is None:
        return build_empty_bounty_economic_state(
            task_id=task_id,
            task=task,
            status="INPUT_REQUIRED",
            reason=(
                "No economics profile exists "
                f"for task {task_id}."
            ),
        )

    if not isinstance(
        profile,
        dict,
    ):
        raise ValueError(
            "Task economics profile must "
            "be a dictionary."
        )

    # --------------------------------------------------------
    # Require explicit economics values.
    # --------------------------------------------------------

    required_fields = (
        "gross_cost_weth",
        "expected_recovery_weth",
        "basis",
        "confidence",
    )

    missing_fields = [
        field_name
        for field_name
        in required_fields
        if (
            field_name not in profile
            or profile[
                field_name
            ] is None
            or (
                isinstance(
                    profile[
                        field_name
                    ],
                    str,
                )
                and not profile[
                    field_name
                ].strip()
            )
        )
    ]

    if missing_fields:
        state = (
            build_empty_bounty_economic_state(
                task_id=task_id,
                task=task,
                status="INPUT_REQUIRED",
                reason=(
                    "Economics profile is incomplete."
                ),
            )
        )

        state[
            "missing_fields"
        ] = missing_fields

        return state

    gross_cost = (
        parse_nonnegative_economic_decimal(
            profile[
                "gross_cost_weth"
            ],
            "gross_cost_weth",
        )
    )

    expected_recovery = (
        parse_nonnegative_economic_decimal(
            profile[
                "expected_recovery_weth"
            ],
            "expected_recovery_weth",
        )
    )

    basis = str(
        profile[
            "basis"
        ]
    ).strip()

    confidence = str(
        profile[
            "confidence"
        ]
    ).strip()

    non_weth_costs = (
        normalize_non_weth_costs(
            profile.get(
                "non_weth_costs"
            )
        )
    )

    net_cost = (
        gross_cost
        - expected_recovery
    )

    reward_bp = task.get(
        "reward_bp"
    )

    if (
        isinstance(
            reward_bp,
            bool,
        )
        or not isinstance(
            reward_bp,
            (int, float),
        )
        or reward_bp < 0
    ):
        raise ValueError(
            f"Invalid reward_bp for task {task_id}."
        )

    bp_per_0_001_weth = None

    if net_cost > 0:
        from decimal import Decimal

        bp_per_0_001_weth = float(
            (
                Decimal(
                    str(reward_bp)
                )
                * Decimal(
                    "0.001"
                )
            )
            / net_cost
        )

        if non_weth_costs:
            efficiency_status = (
                "WETH_PARTIAL_ONLY"
            )

        else:
            efficiency_status = (
                "CALCULATED"
            )

    elif net_cost == 0:
        if non_weth_costs:
            efficiency_status = (
                "NON_WETH_COSTS_PRESENT"
            )

        else:
            efficiency_status = (
                "ZERO_NET_WETH_COST"
            )

    else:
        efficiency_status = (
            "RECOVERY_EXCEEDS_GROSS_COST"
        )

    return {
        "economic_model_version": (
            BOUNTY_ECONOMICS_MODEL_VERSION
        ),
        "economic_applicable": True,
        "economic_status": "READY",
        "economic_reason": None,
        "task": task_id,
        "action": action,
        "action_cost_class": (
            action_cost_class
        ),
        "estimated_gross_cost_weth": (
            format_economic_decimal(
                gross_cost
            )
        ),
        "estimated_recovery_weth": (
            format_economic_decimal(
                expected_recovery
            )
        ),
        "estimated_net_cost_weth": (
            format_economic_decimal(
                net_cost
            )
        ),
        "bp_per_0_001_weth": (
            bp_per_0_001_weth
        ),
        "economic_efficiency_status": (
            efficiency_status
        ),
        "non_weth_costs": (
            non_weth_costs
        ),
        "economic_basis": basis,
        "economic_confidence": (
            confidence
        ),
        "economic_notes": profile.get(
            "notes"
        ),
        "missing_fields": [],
    }



def build_combo_economics_key(
    task_ids,
):
    """
    Build a stable identifier for a shared-action COMBO.

    Sorting makes the same pair resolve to the same key
    regardless of recommendation ordering.
    """

    if not isinstance(
        task_ids,
        (list, tuple),
    ):
        raise ValueError(
            "COMBO task_ids must be a list or tuple."
        )

    if len(task_ids) < 2:
        raise ValueError(
            "COMBO economics requires at least two tasks."
        )

    normalized = []

    for task_id in task_ids:
        if not isinstance(
            task_id,
            str,
        ):
            raise ValueError(
                "COMBO task IDs must be strings."
            )

        task_id = task_id.strip()

        if not task_id:
            raise ValueError(
                "COMBO task IDs cannot be empty."
            )

        normalized.append(
            task_id
        )

    return "||".join(
        sorted(
            normalized
        )
    )


def evaluate_bounty_combo_economics(
    recommendation,
    economics_inputs=None,
):
    """
    Evaluate economics for one shared-action COMBO.

    COMBO economics must use an explicit combo profile.

    Individual task profiles are intentionally NOT summed,
    because doing so could double-count one shared action.
    """

    tasks = recommendation.get(
        "tasks"
    )

    combo_key = build_combo_economics_key(
        tasks
    )

    base_state = {
        "economic_model_version": (
            BOUNTY_ECONOMICS_MODEL_VERSION
        ),
        "economic_applicable": True,
        "economic_status": None,
        "economic_reason": None,
        "task": None,
        "combo_key": combo_key,
        "combo_tasks": list(
            tasks
        ),
        "action": "shared_action",
        "action_cost_class": (
            "shared_action"
        ),
        "estimated_gross_cost_weth": None,
        "estimated_recovery_weth": None,
        "estimated_net_cost_weth": None,
        "bp_per_0_001_weth": None,
        "economic_efficiency_status": None,
        "non_weth_costs": {},
        "economic_basis": None,
        "economic_confidence": None,
        "economic_notes": None,
        "missing_fields": [],
    }

    if economics_inputs is None:
        base_state[
            "economic_status"
        ] = "INPUT_REQUIRED"

        base_state[
            "economic_reason"
        ] = (
            "No economics input was supplied "
            "for this COMBO."
        )

        return base_state

    if not isinstance(
        economics_inputs,
        dict,
    ):
        raise ValueError(
            "economics_inputs must be a dictionary."
        )

    combo_profiles = economics_inputs.get(
        "combo_profiles",
        {},
    )

    if not isinstance(
        combo_profiles,
        dict,
    ):
        raise ValueError(
            "economics_inputs['combo_profiles'] "
            "must be a dictionary."
        )

    profile = combo_profiles.get(
        combo_key
    )

    if profile is None:
        base_state[
            "economic_status"
        ] = "INPUT_REQUIRED"

        base_state[
            "economic_reason"
        ] = (
            "No explicit shared-action economics "
            f"profile exists for COMBO {combo_key}."
        )

        return base_state

    if not isinstance(
        profile,
        dict,
    ):
        raise ValueError(
            "COMBO economics profile must "
            "be a dictionary."
        )

    required_fields = (
        "gross_cost_weth",
        "expected_recovery_weth",
        "basis",
        "confidence",
    )

    missing_fields = [
        field_name
        for field_name
        in required_fields
        if (
            field_name not in profile
            or profile[
                field_name
            ] is None
            or (
                isinstance(
                    profile[
                        field_name
                    ],
                    str,
                )
                and not profile[
                    field_name
                ].strip()
            )
        )
    ]

    if missing_fields:
        base_state[
            "economic_status"
        ] = "INPUT_REQUIRED"

        base_state[
            "economic_reason"
        ] = (
            "COMBO economics profile is incomplete."
        )

        base_state[
            "missing_fields"
        ] = missing_fields

        return base_state

    gross_cost = (
        parse_nonnegative_economic_decimal(
            profile[
                "gross_cost_weth"
            ],
            "gross_cost_weth",
        )
    )

    expected_recovery = (
        parse_nonnegative_economic_decimal(
            profile[
                "expected_recovery_weth"
            ],
            "expected_recovery_weth",
        )
    )

    non_weth_costs = (
        normalize_non_weth_costs(
            profile.get(
                "non_weth_costs"
            )
        )
    )

    net_cost = (
        gross_cost
        - expected_recovery
    )

    combined_bp = recommendation.get(
        "combined_bp"
    )

    if (
        isinstance(
            combined_bp,
            bool,
        )
        or not isinstance(
            combined_bp,
            (int, float),
        )
        or combined_bp < 0
    ):
        raise ValueError(
            "Invalid combined_bp "
            f"for COMBO {combo_key}."
        )

    bp_per_0_001_weth = None

    if net_cost > 0:
        from decimal import Decimal

        bp_per_0_001_weth = float(
            (
                Decimal(
                    str(combined_bp)
                )
                * Decimal(
                    "0.001"
                )
            )
            / net_cost
        )

        if non_weth_costs:
            efficiency_status = (
                "WETH_PARTIAL_ONLY"
            )
        else:
            efficiency_status = (
                "CALCULATED"
            )

    elif net_cost == 0:
        if non_weth_costs:
            efficiency_status = (
                "NON_WETH_COSTS_PRESENT"
            )
        else:
            efficiency_status = (
                "ZERO_NET_WETH_COST"
            )

    else:
        efficiency_status = (
            "RECOVERY_EXCEEDS_GROSS_COST"
        )

    base_state.update(
        {
            "economic_status": "READY",
            "economic_reason": None,
            "estimated_gross_cost_weth": (
                format_economic_decimal(
                    gross_cost
                )
            ),
            "estimated_recovery_weth": (
                format_economic_decimal(
                    expected_recovery
                )
            ),
            "estimated_net_cost_weth": (
                format_economic_decimal(
                    net_cost
                )
            ),
            "bp_per_0_001_weth": (
                bp_per_0_001_weth
            ),
            "economic_efficiency_status": (
                efficiency_status
            ),
            "non_weth_costs": (
                non_weth_costs
            ),
            "economic_basis": str(
                profile["basis"]
            ).strip(),
            "economic_confidence": str(
                profile["confidence"]
            ).strip(),
            "economic_notes": profile.get(
                "notes"
            ),
            "missing_fields": [],
        }
    )

    return base_state



def add_bounty_economics_to_recommendations(
    recommendations,
    task_map,
    economics_inputs=None,
):
    """
    Attach forward-looking economics to executable
    recommendations.

    KEEP:
        Uses the explicit individual task profile.

    COMBO:
        Uses an explicit shared-action combo profile.
        Individual task profiles are never summed.

    Economics remains opt-in.
    """

    enriched = []

    for recommendation in recommendations:
        result = dict(
            recommendation
        )

        if economics_inputs is None:
            enriched.append(
                result
            )
            continue

        decision = result.get(
            "decision"
        )

        if decision == "KEEP":
            task_id = result.get(
                "task"
            )

            task = task_map.get(
                task_id
            )

            if task is None:
                raise ValueError(
                    "Cannot evaluate Bounty economics: "
                    f"task {task_id!r} was not found."
                )

            result[
                "economics"
            ] = evaluate_bounty_task_economics(
                task_id=task_id,
                task=task,
                economics_inputs=(
                    economics_inputs
                ),
            )

        elif decision == "COMBO":
            result[
                "economics"
            ] = evaluate_bounty_combo_economics(
                recommendation=result,
                economics_inputs=(
                    economics_inputs
                ),
            )

        enriched.append(
            result
        )

    return enriched



def format_bounty_economics(
    recommendation,
):
    economics = recommendation.get(
        "economics"
    )

    if economics is None:
        return ""

    status = economics.get(
        "economic_status"
    )

    if status == "NOT_APPLICABLE":
        return ""

    if status == "INPUT_REQUIRED":
        return (
            " | Economics: INPUT REQUIRED"
        )

    if status != "READY":
        return (
            f" | Economics: {status}"
        )

    line = (
        " | Economics: net "
        f"{economics['estimated_net_cost_weth']} WETH"
    )

    bp_efficiency = economics.get(
        "bp_per_0_001_weth"
    )

    if bp_efficiency is not None:
        line += (
            " | "
            f"{bp_efficiency:,.2f} "
            "BP/0.001 WETH"
        )

    non_weth_costs = economics.get(
        "non_weth_costs",
        {},
    )

    if non_weth_costs:
        other_costs = ", ".join(
            (
                f"{currency} {amount}"
            )
            for currency, amount
            in non_weth_costs.items()
        )

        line += (
            f" | Other costs: {other_costs}"
        )

    return line



def run_v09_bounty_economics_model_test():
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 BOUNTY ECONOMICS MODEL TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    # --------------------------------------------------------
    # Test 1 — Buy task with explicit economics
    # --------------------------------------------------------

    buy_task = {
        "action": "buy",
        "reward_bp": 670,
        "target": "axie",
        "quantity": 1,
    }

    economics_inputs = {
        "task_profiles": {
            "test_buy_axie": {
                "gross_cost_weth": (
                    "0.00083"
                ),
                "expected_recovery_weth": (
                    "0.00078"
                ),
                "basis": (
                    "Test marketplace estimate"
                ),
                "confidence": (
                    "estimated"
                ),
            },
        },
    }

    buy_state = (
        evaluate_bounty_task_economics(
            task_id="test_buy_axie",
            task=buy_task,
            economics_inputs=(
                economics_inputs
            ),
        )
    )

    buy_passed = (
        buy_state[
            "economic_status"
        ] == "READY"
        and buy_state[
            "estimated_gross_cost_weth"
        ] == "0.00083"
        and buy_state[
            "estimated_recovery_weth"
        ] == "0.00078"
        and buy_state[
            "estimated_net_cost_weth"
        ] == "0.00005"
        and buy_state[
            "bp_per_0_001_weth"
        ] == 13400.0
        and buy_state[
            "economic_efficiency_status"
        ] == "CALCULATED"
    )

    print(
        "Buy-task economics:",
        "PASS" if buy_passed else "FAIL",
    )
    print(
        "  State:",
        buy_state,
    )

    if not buy_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 2 — Missing task profile
    # --------------------------------------------------------

    release_task = {
        "action": "release",
        "reward_bp": 650,
        "target": "axie",
        "quantity": 1,
    }

    release_state = (
        evaluate_bounty_task_economics(
            task_id="test_release_axie",
            task=release_task,
            economics_inputs=(
                economics_inputs
            ),
        )
    )

    release_passed = (
        release_state[
            "economic_status"
        ] == "INPUT_REQUIRED"
        and release_state[
            "estimated_net_cost_weth"
        ] is None
    )

    print(
        "Missing-profile guardrail:",
        (
            "PASS"
            if release_passed
            else "FAIL"
        ),
    )

    if not release_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 3 — Incomplete profile
    # --------------------------------------------------------

    incomplete_inputs = {
        "task_profiles": {
            "test_release_axie": {
                "gross_cost_weth": (
                    "0.0005"
                ),
            },
        },
    }

    incomplete_state = (
        evaluate_bounty_task_economics(
            task_id="test_release_axie",
            task=release_task,
            economics_inputs=(
                incomplete_inputs
            ),
        )
    )

    incomplete_passed = (
        incomplete_state[
            "economic_status"
        ] == "INPUT_REQUIRED"
        and set(
            incomplete_state[
                "missing_fields"
            ]
        ) == {
            "expected_recovery_weth",
            "basis",
            "confidence",
        }
    )

    print(
        "Incomplete-profile guardrail:",
        (
            "PASS"
            if incomplete_passed
            else "FAIL"
        ),
    )

    if not incomplete_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 4 — Gameplay-time task
    # --------------------------------------------------------

    gameplay_task = {
        "action": "win",
        "reward_bp": 400,
        "target": "battle",
        "quantity": 1,
    }

    gameplay_state = (
        evaluate_bounty_task_economics(
            task_id="test_gameplay",
            task=gameplay_task,
            economics_inputs=None,
        )
    )

    gameplay_passed = (
        gameplay_state[
            "economic_status"
        ] == "NOT_APPLICABLE"
        and gameplay_state[
            "economic_applicable"
        ] is False
    )

    print(
        "Gameplay-time classification:",
        (
            "PASS"
            if gameplay_passed
            else "FAIL"
        ),
    )

    if not gameplay_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 5 — Non-WETH costs stay separate
    # --------------------------------------------------------

    open_task = {
        "action": "open",
        "reward_bp": 150,
        "target": "premium_pouch",
        "quantity": 1,
    }

    open_inputs = {
        "task_profiles": {
            "test_open_pouch": {
                "gross_cost_weth": "0",
                "expected_recovery_weth": (
                    "0"
                ),
                "basis": (
                    "Test pouch economics"
                ),
                "confidence": (
                    "exact"
                ),
                "non_weth_costs": {
                    "RON": "0.25",
                    "SLIPS": "50",
                },
            },
        },
    }

    open_state = (
        evaluate_bounty_task_economics(
            task_id="test_open_pouch",
            task=open_task,
            economics_inputs=(
                open_inputs
            ),
        )
    )

    open_passed = (
        open_state[
            "economic_status"
        ] == "READY"
        and open_state[
            "estimated_net_cost_weth"
        ] == "0"
        and open_state[
            "bp_per_0_001_weth"
        ] is None
        and open_state[
            "economic_efficiency_status"
        ] == "NON_WETH_COSTS_PRESENT"
        and open_state[
            "non_weth_costs"
        ] == {
            "RON": "0.25",
            "SLIPS": "50",
        }
    )

    print(
        "Non-WETH separation:",
        "PASS" if open_passed else "FAIL",
    )
    print(
        "  State:",
        open_state,
    )

    if not open_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 6 — Recovery may exceed gross cost
    # --------------------------------------------------------

    recovery_inputs = {
        "task_profiles": {
            "test_release_profit": {
                "gross_cost_weth": (
                    "0.0004"
                ),
                "expected_recovery_weth": (
                    "0.00045"
                ),
                "basis": (
                    "Test material recovery"
                ),
                "confidence": (
                    "estimated"
                ),
            },
        },
    }

    recovery_state = (
        evaluate_bounty_task_economics(
            task_id="test_release_profit",
            task=release_task,
            economics_inputs=(
                recovery_inputs
            ),
        )
    )

    recovery_passed = (
        recovery_state[
            "estimated_net_cost_weth"
        ] == "-0.00005"
        and recovery_state[
            "economic_efficiency_status"
        ] == (
            "RECOVERY_EXCEEDS_GROSS_COST"
        )
    )

    print(
        "Positive-recovery economics:",
        (
            "PASS"
            if recovery_passed
            else "FAIL"
        ),
    )

    if not recovery_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 7 — Negative input is rejected
    # --------------------------------------------------------

    invalid_passed = False

    invalid_inputs = {
        "task_profiles": {
            "test_invalid": {
                "gross_cost_weth": "-1",
                "expected_recovery_weth": "0",
                "basis": "test",
                "confidence": "test",
            },
        },
    }

    try:
        evaluate_bounty_task_economics(
            task_id="test_invalid",
            task=buy_task,
            economics_inputs=(
                invalid_inputs
            ),
        )

    except ValueError as exc:
        invalid_passed = True

        print(
            "Negative-value guardrail: PASS"
        )
        print(
            "  Message:",
            str(exc),
        )

    else:
        print(
            "Negative-value guardrail: FAIL"
        )

    if not invalid_passed:
        all_passed = False

    print(
        "\nV0.9 Bounty Economics Model:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed




def run_v09_keep_economics_integration_test():
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 KEEP ECONOMICS INTEGRATION TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    daily_input = build_daily_input(
        board_entries=[
            "Feed 1 Regular Choco",
        ],
        inventory={
            "Regular Choco": {
                "on_hand": 5,
                "reserved": 1,
            },
            "Premium Choco": 0,
        },
        slip_balance=100,
        reroll_numbers={},
        strategy_mode="Conserve",
        minimum_reserve=20,
    )

    # Resolve the real daily-board task ID rather than
    # assuming it matches the catalog ID.
    test_board = build_daily_board(
        daily_input[
            "board_entries"
        ]
    )

    task_id = next(
        iter(
            test_board
        )
    )

    print(
        "Resolved task ID:",
        task_id,
    )

    # --------------------------------------------------------
    # Test 1 — Existing behavior without economics
    # --------------------------------------------------------

    legacy_plan = optimize_daily_input(
        daily_input=daily_input,
        asset=None,
    )

    legacy_rec = next(
        recommendation
        for recommendation
        in legacy_plan[
            "recommendations"
        ]
        if recommendation.get(
            "task"
        ) == task_id
    )

    legacy_passed = (
        "economics"
        not in legacy_rec
    )

    print(
        "Economics opt-in behavior:",
        "PASS" if legacy_passed else "FAIL",
    )

    if not legacy_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 2 — Explicit economics profile
    # --------------------------------------------------------

    economics_inputs = {
        "task_profiles": {
            task_id: {
                "gross_cost_weth": (
                    "0.000006"
                ),
                "expected_recovery_weth": (
                    "0"
                ),
                "basis": (
                    "Test Regular Choco unit value"
                ),
                "confidence": (
                    "estimated"
                ),
            },
        },
    }

    economics_plan = optimize_daily_input(
        daily_input=daily_input,
        asset=None,
        economics_inputs=(
            economics_inputs
        ),
    )

    economics_rec = next(
        recommendation
        for recommendation
        in economics_plan[
            "recommendations"
        ]
        if recommendation.get(
            "task"
        ) == task_id
    )

    state = economics_rec[
        "economics"
    ]

    ready_passed = (
        state[
            "economic_status"
        ] == "READY"
        and state[
            "estimated_net_cost_weth"
        ] == "0.000006"
        and state[
            "bp_per_0_001_weth"
        ] is not None
    )

    print(
        "KEEP economics enrichment:",
        "PASS" if ready_passed else "FAIL",
    )
    print(
        "  State:",
        state,
    )

    if not ready_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 3 — Formatter displays economics
    # --------------------------------------------------------

    formatted_lines = (
        format_execution_plan(
            economics_plan
        )
    )

    formatted_text = "\n".join(
        formatted_lines
    )

    formatter_passed = (
        "Economics: net 0.000006 WETH"
        in formatted_text
        and "BP/0.001 WETH"
        in formatted_text
    )

    print(
        "KEEP economics formatting:",
        (
            "PASS"
            if formatter_passed
            else "FAIL"
        ),
    )

    print(
        "  Output:",
        formatted_text,
    )

    if not formatter_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 4 — Supplied economics set but missing profile
    # --------------------------------------------------------

    missing_plan = optimize_daily_input(
        daily_input=daily_input,
        asset=None,
        economics_inputs={
            "task_profiles": {},
        },
    )

    missing_rec = next(
        recommendation
        for recommendation
        in missing_plan[
            "recommendations"
        ]
        if recommendation.get(
            "task"
        ) == task_id
    )

    missing_formatted = "\n".join(
        format_execution_plan(
            missing_plan
        )
    )

    missing_passed = (
        missing_rec[
            "economics"
        ][
            "economic_status"
        ] == "INPUT_REQUIRED"
        and (
            "Economics: INPUT REQUIRED"
            in missing_formatted
        )
    )

    print(
        "Missing-profile integration:",
        (
            "PASS"
            if missing_passed
            else "FAIL"
        ),
    )

    if not missing_passed:
        all_passed = False

    print(
        "\nV0.9 KEEP Economics Integration:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



def run_v09_combo_economics_integration_test():
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 COMBO ECONOMICS INTEGRATION TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    combo_rec = {
        "decision": "COMBO",
        "tasks": [
            "feed_10_choco_any_axie",
            "feed_10_choco_beast",
        ],
        "combined_bp": 310,
        "resource": "regular_choco",
        "quantity_needed": 10,
        "quantity_saved": 10,
        "inventory_status": "READY",
        "shortfall": 0,
        "quantity_on_hand": 20,
        "quantity_reserved": 5,
        "quantity_available": 15,
    }

    combo_key = build_combo_economics_key(
        combo_rec[
            "tasks"
        ]
    )

    print(
        "Resolved COMBO key:",
        combo_key,
    )

    # --------------------------------------------------------
    # Test 1 — Explicit COMBO economics
    # --------------------------------------------------------

    economics_inputs = {
        "combo_profiles": {
            combo_key: {
                "gross_cost_weth": (
                    "0.00006"
                ),
                "expected_recovery_weth": (
                    "0"
                ),
                "basis": (
                    "Test shared Regular Choco action"
                ),
                "confidence": (
                    "estimated"
                ),
            },
        },
    }

    enriched = (
        add_bounty_economics_to_recommendations(
            recommendations=[
                combo_rec,
            ],
            task_map={},
            economics_inputs=(
                economics_inputs
            ),
        )
    )

    state = enriched[0][
        "economics"
    ]

    ready_passed = (
        state[
            "economic_status"
        ] == "READY"
        and state[
            "estimated_net_cost_weth"
        ] == "0.00006"
        and state[
            "bp_per_0_001_weth"
        ] is not None
    )

    print(
        "Explicit COMBO economics:",
        "PASS" if ready_passed else "FAIL",
    )
    print(
        "  State:",
        state,
    )

    if not ready_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 2 — Formatter
    # --------------------------------------------------------

    formatted = "\n".join(
        format_execution_plan(
            {
                "recommendations": enriched,
                "reroll_results": [],
            }
        )
    )

    formatter_passed = (
        "COMBO:"
        in formatted
        and (
            "Economics: net 0.00006 WETH"
            in formatted
        )
        and (
            "BP/0.001 WETH"
            in formatted
        )
    )

    print(
        "COMBO economics formatting:",
        (
            "PASS"
            if formatter_passed
            else "FAIL"
        ),
    )
    print(
        "  Output:",
        formatted,
    )

    if not formatter_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 3 — Individual task profiles MUST NOT be summed
    # --------------------------------------------------------

    individual_only_inputs = {
        "task_profiles": {
            "feed_10_choco_any_axie": {
                "gross_cost_weth": (
                    "0.00006"
                ),
                "expected_recovery_weth": "0",
                "basis": "Individual test",
                "confidence": "estimated",
            },
            "feed_10_choco_beast": {
                "gross_cost_weth": (
                    "0.00006"
                ),
                "expected_recovery_weth": "0",
                "basis": "Individual test",
                "confidence": "estimated",
            },
        },
    }

    individual_only = (
        add_bounty_economics_to_recommendations(
            recommendations=[
                combo_rec,
            ],
            task_map={},
            economics_inputs=(
                individual_only_inputs
            ),
        )
    )

    anti_double_count_passed = (
        individual_only[0][
            "economics"
        ][
            "economic_status"
        ] == "INPUT_REQUIRED"
        and individual_only[0][
            "economics"
        ][
            "estimated_net_cost_weth"
        ] is None
    )

    print(
        "Anti-double-count guardrail:",
        (
            "PASS"
            if anti_double_count_passed
            else "FAIL"
        ),
    )

    if not anti_double_count_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 4 — Stable COMBO key
    # --------------------------------------------------------

    reverse_key = build_combo_economics_key(
        list(
            reversed(
                combo_rec[
                    "tasks"
                ]
            )
        )
    )

    stable_key_passed = (
        reverse_key
        == combo_key
    )

    print(
        "Stable COMBO key:",
        (
            "PASS"
            if stable_key_passed
            else "FAIL"
        ),
    )

    if not stable_key_passed:
        all_passed = False

    print(
        "\nV0.9 COMBO Economics Integration:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed








def recommend_task_action(
    reward_bp,
    rerolls_used,
    game_name=None,
    feasible=True,
    avoided=False,
    minimum_bp=100,
):
    
    next_reroll = get_next_reroll_info(rerolls_used)

    if is_avoided_game(game_name):
        avoided = True



    if next_reroll is None:
        return {
            "decision": "KEEP",
            "reason": "No rerolls remaining",
            "next_reroll": None,
        }

    if avoided:
        return {
            "decision": "REROLL",
            "reason": "Task is intentionally avoided",
            "next_reroll": next_reroll,
        }

    if not feasible:
        return {
            "decision": "REROLL",
            "reason": "Task cannot currently be completed",
            "next_reroll": next_reroll,
        }

    if (
        reward_bp < minimum_bp
        and next_reroll["cost"] >= 100
        and feasible
        and not avoided
    ):
        return {
            "decision": "REVIEW",
            "reason": (
                f"Next reroll costs "
                f"{next_reroll['cost']} slips; "
                "expected-value analysis required"
            ),
            "next_reroll": next_reroll,
        }


    if reward_bp < minimum_bp:
        return {
            "decision": "REROLL",
            "reason": (
                f"{reward_bp} BP is below "
                f"{minimum_bp} BP threshold"
            ),
            "next_reroll": next_reroll,
        }

    return {
        "decision": "KEEP",
        "reason": (
            f"{reward_bp} BP meets "
            f"{minimum_bp} BP threshold"
        ),
        "next_reroll": next_reroll,
    }


def find_shared_action_pairs(task_map, asset):
    overlaps = []

    task_items = list(task_map.items())

    for i in range(len(task_items)):
        task_id_a, task_a = task_items[i]

        for j in range(i + 1, len(task_items)):
            task_id_b, task_b = task_items[j]

            shared_score = score_shared_action(
                task_a,
                task_b,
                asset,
            )

            if shared_score is not None:
                overlaps.append(
                    {
                        "task_a": task_id_a,
                        "task_b": task_id_b,
                        **shared_score,
                    }
                )

    return overlaps



def summarize_task_board(task_map):
    total_bp = 0

    for task in task_map.values():
        total_bp += task["reward_bp"]

    return {
        "task_count": len(task_map),
        "total_bp": total_bp,
    }


def calculate_overlap_savings(
    task_map,
    overlap,
):
    task_a = task_map[overlap["task_a"]]
    task_b = task_map[overlap["task_b"]]

    separate_quantity = (
        task_a["quantity"]
        + task_b["quantity"]
    )

    shared_quantity = overlap["quantity"]

    return {
        "separate_quantity": separate_quantity,
        "shared_quantity": shared_quantity,
        "quantity_saved": (
            separate_quantity - shared_quantity
        ),
    }


def calculate_overlap_efficiency(
    overlap,
    savings,
):
    combined_bp = overlap["combined_bp"]

    separate_efficiency = (
        combined_bp
        / savings["separate_quantity"]
    )

    shared_efficiency = (
        combined_bp
        / savings["shared_quantity"]
    )

    return {
        "separate_bp_per_unit": separate_efficiency,
        "shared_bp_per_unit": shared_efficiency,
    }


def analyze_task_board(
    task_map,
    asset,
):
    summary = summarize_task_board(task_map)

    overlaps = find_shared_action_pairs(
        task_map,
        asset,
    )

    overlap_details = []

    for overlap in overlaps:
        savings = calculate_overlap_savings(
            task_map,
            overlap,
        )

        efficiency = calculate_overlap_efficiency(
            overlap,
            savings,
        )

        overlap_details.append(
            {
                **overlap,
                **savings,
                **efficiency,
            }
        )

    recommendations = []
    covered_tasks = set()

    for overlap in overlap_details:
        recommendations.append(
            build_overlap_recommendation(overlap)
        )

        covered_tasks.add(overlap["task_a"])
        covered_tasks.add(overlap["task_b"])

    for task_id, task in task_map.items():
        if task_id not in covered_tasks:
            should_reroll, reason = should_reroll_task(
                task
            )

            if should_reroll:
                recommendations.append(
                    build_reroll_recommendation(
                        task_id,
                        task,
                        reason,
                    )
                )
            else:
                recommendations.append(
                    build_keep_recommendation(
                        task_id,
                        task,
                    )
                )

    return {
        "task_count": summary["task_count"],
        "total_bp": summary["total_bp"],
        "overlap_count": len(overlaps),
        "overlaps": overlap_details,
        "recommendations": recommendations,
    }


def build_overlap_recommendation(
    overlap,
):
    return {
        "decision": "COMBO",
        "tasks": [
            overlap["task_a"],
            overlap["task_b"],
        ],
        "combined_bp": overlap["combined_bp"],
        "resource": overlap["resource"],
        "quantity_needed": overlap["shared_quantity"],
        "quantity_saved": overlap["quantity_saved"],
    }


def build_keep_recommendation(
    task_id,
    task,
):
    return {
        "decision": "KEEP",
        "task": task_id,
        "reward_bp": task["reward_bp"],
    }


def summarize_execution_plan(
    analysis,
):
    recommendation_count = len(
        analysis["recommendations"]
    )

    task_count = analysis["task_count"]

    return {
        "task_count": task_count,
        "action_count": recommendation_count,
        "actions_saved": (
            task_count - recommendation_count
        ),
    }


def build_reroll_recommendation(
    task_id,
    task,
    reason,
):
    return {
        "decision": "REROLL",
        "task": task_id,
        "reward_bp": task["reward_bp"],
        "reason": reason,
    }


def should_reroll_task(task):
    if task.get("keep_override", False):
        return False, None
    
    if task["game"] in AVOIDED_GAMES:
        return True, "game is on avoid list"

    if task["reward_bp"] < 100:
        return True, "reward below 100 BP"

    return False, None


def summarize_decisions(analysis):
    counts = {
        "COMBO": 0,
        "KEEP": 0,
        "REROLL": 0,
    }

    for recommendation in analysis["recommendations"]:
        decision = recommendation["decision"]

        if decision in counts:
            counts[decision] += 1

    return counts


def summarize_task_coverage(analysis):
    counts = {
        "COMBO": 0,
        "KEEP": 0,
        "REROLL": 0,
    }

    for recommendation in analysis["recommendations"]:
        decision = recommendation["decision"]

        if decision == "COMBO":
            counts["COMBO"] += len(
                recommendation["tasks"]
            )

        elif decision in {"KEEP", "REROLL"}:
            counts[decision] += 1

    return counts


def summarize_bp_by_decision(analysis):
    bp = {
        "COMBO": 0,
        "KEEP": 0,
        "REROLL": 0,
    }

    for recommendation in analysis["recommendations"]:
        decision = recommendation["decision"]

        if decision == "COMBO":
            bp["COMBO"] += recommendation["combined_bp"]

        elif decision in {"KEEP", "REROLL"}:
            bp[decision] += recommendation["reward_bp"]

    return bp


def get_reroll_info(reroll_number):
    if reroll_number not in REROLL_TIERS:
        return None

    tier = REROLL_TIERS[reroll_number]

    return {
        "reroll_number": reroll_number,
        "slip_cost": tier["cost"],
        "master_chance": tier["master"],
    }


def calculate_reroll_path(
    max_reroll,
):
    total_slip_cost = 0
    no_master_probability = 1.0

    for reroll_number in range(
        1,
        max_reroll + 1,
    ):
        tier = REROLL_TIERS[
            reroll_number
        ]

        total_slip_cost += tier["cost"]

        no_master_probability *= (
            1 - tier["master"]
        )

    cumulative_master_chance = (
        1 - no_master_probability
    )

    return {
        "max_reroll": max_reroll,
        "total_slip_cost": total_slip_cost,
        "cumulative_master_chance": (
            cumulative_master_chance
        ),
    }


def evaluate_reroll_affordability(
    reroll_number,
    slip_balance,
):
    reroll_info = get_reroll_info(
        reroll_number
    )

    if reroll_info is None:
        return None

    slip_cost = reroll_info["slip_cost"]

    return {
        "reroll_number": reroll_number,
        "slip_balance": slip_balance,
        "slip_cost": slip_cost,
        "can_afford": (
            slip_balance >= slip_cost
        ),
        "remaining_slips": (
            slip_balance - slip_cost
            if slip_balance >= slip_cost
            else slip_balance
        ),
    }


def evaluate_reroll_path_affordability(
    max_reroll,
    slip_balance,
):
    path = calculate_reroll_path(
        max_reroll
    )

    total_cost = path[
        "total_slip_cost"
    ]

    return {
        "max_reroll": max_reroll,
        "slip_balance": slip_balance,
        "total_slip_cost": total_cost,
        "can_afford_path": (
            slip_balance >= total_cost
        ),
        "remaining_slips": (
            slip_balance - total_cost
            if slip_balance >= total_cost
            else slip_balance
        ),
    }


def get_max_affordable_reroll(
    slip_balance,
):
    total_cost = 0
    max_affordable = 0

    for reroll_number in range(1, 11):
        next_cost = REROLL_TIERS[
            reroll_number
        ]["cost"]

        if total_cost + next_cost > slip_balance:
            break

        total_cost += next_cost
        max_affordable = reroll_number

    return {
        "slip_balance": slip_balance,
        "max_affordable_reroll": max_affordable,
        "slips_spent": total_cost,
        "remaining_slips": (
            slip_balance - total_cost
        ),
    }


def evaluate_reroll_capacity(
    slip_balance,
):
    affordability = get_max_affordable_reroll(
        slip_balance
    )

    max_reroll = affordability[
        "max_affordable_reroll"
    ]

    path = calculate_reroll_path(
        max_reroll
    )

    return {
        **affordability,
        "cumulative_master_chance": (
            path["cumulative_master_chance"]
        ),
    }


def get_max_reroll_with_reserve(
    slip_balance,
    minimum_reserve,
):
    spendable_slips = max(
        0,
        slip_balance - minimum_reserve,
    )

    affordability = get_max_affordable_reroll(
        spendable_slips
    )

    return {
        "slip_balance": slip_balance,
        "minimum_reserve": minimum_reserve,
        "spendable_slips": spendable_slips,
        "max_affordable_reroll": affordability[
            "max_affordable_reroll"
        ],
        "slips_spent": affordability[
            "slips_spent"
        ],
        "remaining_slips": (
            slip_balance
            - affordability["slips_spent"]
        ),
    }


def evaluate_reroll_capacity_with_reserve(
    slip_balance,
    minimum_reserve,
):
    reserve_plan = get_max_reroll_with_reserve(
        slip_balance,
        minimum_reserve,
    )

    max_reroll = reserve_plan[
        "max_affordable_reroll"
    ]

    if max_reroll == 0:
        master_chance = 0.0
    else:
        path = calculate_reroll_path(
            max_reroll
        )

        master_chance = path[
            "cumulative_master_chance"
        ]

    return {
        **reserve_plan,
        "cumulative_master_chance": master_chance,
    }


def evaluate_next_reroll(
    reroll_number,
    slip_balance,
    minimum_reserve,
):
    reroll_info = get_reroll_info(
        reroll_number
    )

    if reroll_info is None:
        return None

    slip_cost = reroll_info["slip_cost"]

    projected_remaining = (
        slip_balance - slip_cost
    )

    can_afford = (
        slip_balance >= slip_cost
    )

    reserve_protected = (
        projected_remaining
        >= minimum_reserve
    )

    can_reroll = (
        can_afford
        and reserve_protected
    )

    actual_remaining = (
        projected_remaining
        if can_reroll
        else slip_balance
    )

    return {
        "reroll_number": reroll_number,
        "slip_balance": slip_balance,
        "slip_cost": slip_cost,
        "master_chance": reroll_info[
            "master_chance"
        ],
        "minimum_reserve": minimum_reserve,
        "projected_remaining": (
            projected_remaining
        ),
        "remaining_after_reroll": (
            actual_remaining
        ),
        "reserve_protected": reserve_protected,
        "can_reroll": can_reroll,
    }


def check_next_reroll_guardrail(
    reroll_number,
    slip_balance,
    minimum_reserve,
):
    evaluation = evaluate_next_reroll(
        reroll_number,
        slip_balance,
        minimum_reserve,
    )

    if evaluation is None:
        return None

    if evaluation["can_reroll"]:
        status = "ALLOWED"
        reason = (
            "reroll is affordable and "
            "slip reserve is protected"
        )
    else:
        status = "BLOCKED"
        reason = (
            "reroll would violate "
            "slip reserve"
        )

    return {
        **evaluation,
        "status": status,
        "reason": reason,
    }


def evaluate_task_reroll(
    task_id,
    task,
    reroll_number,
    slip_balance,
    minimum_reserve,
):
    should_reroll, task_reason = should_reroll_task(
        task
    )

    if not should_reroll:
        return {
            "task": task_id,
            "task_decision": "KEEP",
            "reroll_status": "NOT_NEEDED",
            "reason": "task does not meet reroll rules",
        }

    guardrail = check_next_reroll_guardrail(
        reroll_number,
        slip_balance,
        minimum_reserve,
    )

    return {
        "task": task_id,
        "task_decision": "REROLL",
        "task_reason": task_reason,
        "reroll_number": reroll_number,
        "slip_cost": guardrail["slip_cost"],
        "master_chance": guardrail[
            "master_chance"
        ],
        "reroll_status": guardrail["status"],
        "remaining_after_reroll": guardrail[
            "remaining_after_reroll"
        ],
    }


def evaluate_board_rerolls(
    analysis,
    task_map,
    reroll_number,
    slip_balance,
    minimum_reserve,
):
    results = []

    for recommendation in analysis[
        "recommendations"
    ]:
        if recommendation["decision"] != "REROLL":
            continue

        task_id = recommendation["task"]

        result = evaluate_task_reroll(
            task_id=task_id,
            task=task_map[task_id],
            reroll_number=reroll_number,
            slip_balance=slip_balance,
            minimum_reserve=minimum_reserve,
        )

        results.append(result)

    return results


def evaluate_board_rerolls_sequentially(
    analysis,
    task_map,
    reroll_number,
    slip_balance,
    minimum_reserve,
):
    results = []
    current_balance = slip_balance

    for recommendation in analysis[
        "recommendations"
    ]:
        if recommendation["decision"] != "REROLL":
            continue

        task_id = recommendation["task"]

        result = evaluate_task_reroll(
            task_id=task_id,
            task=task_map[task_id],
            reroll_number=reroll_number,
            slip_balance=current_balance,
            minimum_reserve=minimum_reserve,
        )

        results.append(result)

        if result["reroll_status"] == "ALLOWED":
            current_balance = result[
                "remaining_after_reroll"
            ]

    return {
        "starting_slips": slip_balance,
        "ending_slips": current_balance,
        "reroll_results": results,
    }


def evaluate_board_rerolls_by_task(
    analysis,
    task_map,
    reroll_numbers,
    slip_balance,
    minimum_reserve,
):
    results = []
    current_balance = slip_balance

    for recommendation in analysis[
        "recommendations"
    ]:
        if recommendation["decision"] != "REROLL":
            continue

        task_id = recommendation["task"]

        reroll_number = reroll_numbers[
            task_id
        ]

        result = evaluate_task_reroll(
            task_id=task_id,
            task=task_map[task_id],
            reroll_number=reroll_number,
            slip_balance=current_balance,
            minimum_reserve=minimum_reserve,
        )

        results.append(result)

        if result["reroll_status"] == "ALLOWED":
            current_balance = result[
                "remaining_after_reroll"
            ]

    return {
        "starting_slips": slip_balance,
        "ending_slips": current_balance,
        "reroll_results": results,
    }


def summarize_board_rerolls(
    reroll_evaluation,
):
    results = reroll_evaluation[
        "reroll_results"
    ]

    allowed = 0
    blocked = 0
    slips_spent = 0

    allowed_tasks = []
    blocked_tasks = []

    for result in results:
        if result["reroll_status"] == "ALLOWED":
            allowed += 1
            slips_spent += result["slip_cost"]

            allowed_tasks.append(
                result["task"]
            )

        elif result["reroll_status"] == "BLOCKED":
            blocked += 1

            blocked_tasks.append(
                result["task"]
            )

    return {
        "rerolls_considered": len(results),
        "rerolls_allowed": allowed,
        "rerolls_blocked": blocked,
        "slips_spent": slips_spent,
        "starting_slips": reroll_evaluation[
            "starting_slips"
        ],
        "ending_slips": reroll_evaluation[
            "ending_slips"
        ],
        "allowed_tasks": allowed_tasks,
        "blocked_tasks": blocked_tasks,
    }


def validate_strategy_mode(
    strategy_mode,
):
    if strategy_mode not in STRATEGY_MODES:
        raise ValueError(
            f"Unknown strategy mode: {strategy_mode}"
        )

    return strategy_mode


def normalize_strategy_mode(
    strategy_mode,
):
    return STRATEGY_MODE_ALIASES.get(
        strategy_mode,
        strategy_mode,
    )





def build_strategy_context(
    strategy_mode,
    minimum_reserve,
    current_rank=None,
    current_weekly_bp=None,
    days_remaining=None,
):
    strategy_mode = normalize_strategy_mode(
        strategy_mode
    )

    strategy_mode = validate_strategy_mode(
        strategy_mode
    )

    if minimum_reserve < 0:
        raise ValueError(
            "minimum_reserve cannot be negative"
        )

    if strategy_mode == "rank_push":
        if current_rank is None:
            raise ValueError(
                "rank_push requires current_rank"
            )

        if current_weekly_bp is None:
            raise ValueError(
                "rank_push requires current_weekly_bp"
            )

        if days_remaining is None:
            raise ValueError(
                "rank_push requires days_remaining"
            )

    context = {
        "strategy_mode": strategy_mode,
        "minimum_reserve": minimum_reserve,
        "current_rank": current_rank,
        "current_weekly_bp": current_weekly_bp,
        "days_remaining": days_remaining,
    }

    if current_rank is not None:
        context["rank_bonus_target"] = (
            get_next_rank_bonus_target(
                current_rank
            )
        )
    else:
        context["rank_bonus_target"] = None

    return context


def get_strategy_minimum_reserve(
    strategy_context,
):
    minimum_reserve = strategy_context[
        "minimum_reserve"
    ]

    strategy_mode = strategy_context[
        "strategy_mode"
    ]

    rank_bonus_target = strategy_context.get(
        "rank_bonus_target"
    )

    if (
        strategy_mode == "rank_push"
        and rank_bonus_target is not None
        and rank_bonus_target[
            "target_rank"
        ] is not None
        and rank_bonus_target[
            "bonus_increase_baxs"
        ] > 0
    ):
        return int(
            minimum_reserve
            * RANK_PUSH_RESERVE_FACTOR
        )

    return minimum_reserve









def evaluate_task_reroll_with_strategy(
    task_id,
    task,
    reroll_number,
    slip_balance,
    strategy_context,
):
    minimum_reserve = (
        get_strategy_minimum_reserve(
            strategy_context
        )
    )

    result = evaluate_task_reroll(
        task_id=task_id,
        task=task,
        reroll_number=reroll_number,
        slip_balance=slip_balance,
        minimum_reserve=minimum_reserve,
    )

    strategy_mode = strategy_context[
    "strategy_mode"
    ]

    normal_reserve = strategy_context[
        "minimum_reserve"
    ]

    rank_bonus_target = strategy_context.get(
        "rank_bonus_target"
    )

    strategy_reason = (
        "standard reserve policy"
    )

    if (
        strategy_mode == "rank_push"
        and minimum_reserve < normal_reserve
        and rank_bonus_target is not None
    ):
        strategy_reason = (
            f"rank push toward rank "
            f"{rank_bonus_target['target_rank']} "
            f"for +"
            f"{rank_bonus_target['bonus_increase_baxs']} "
            f"bAXS"
        )

    return {
        **result,
        "strategy_mode": strategy_mode,
        "effective_minimum_reserve": (
            minimum_reserve
        ),
        "strategy_reason": strategy_reason,
    }


def get_rank_bonus(
    rank,
):
    for min_rank, max_rank, bonus_baxs in (
        RANK_BONUS_TIERS
    ):
        if min_rank <= rank <= max_rank:
            return bonus_baxs

    return 0


def get_next_rank_bonus_target(
    rank,
):
    if rank < 1:
        return None

    for index, tier in enumerate(
        RANK_BONUS_TIERS
    ):
        min_rank, max_rank, bonus_baxs = tier

        if min_rank <= rank <= max_rank:
            if index == 0:
                return {
                    "current_rank": rank,
                    "current_bonus_baxs": bonus_baxs,
                    "target_rank": None,
                    "next_bonus_baxs": None,
                    "bonus_increase_baxs": 0,
                }

            next_better_tier = RANK_BONUS_TIERS[
                index - 1
            ]

            target_rank = next_better_tier[1]
            next_bonus = next_better_tier[2]

            return {
                "current_rank": rank,
                "current_bonus_baxs": bonus_baxs,
                "target_rank": target_rank,
                "next_bonus_baxs": next_bonus,
                "bonus_increase_baxs": (
                    next_bonus - bonus_baxs
                ),
            }

    return {
        "current_rank": rank,
        "current_bonus_baxs": 0,
        "target_rank": 3000,
        "next_bonus_baxs": 3,
        "bonus_increase_baxs": 3,
    }


def evaluate_board_rerolls_with_strategy(
    analysis,
    task_map,
    reroll_numbers,
    slip_balance,
    strategy_context,
):
    results = []
    current_balance = slip_balance

    for recommendation in analysis[
        "recommendations"
    ]:
        if recommendation["decision"] != "REROLL":
            continue

        task_id = recommendation["task"]

        reroll_number = reroll_numbers.get(
            task_id
        )

        if reroll_number is None:
            results.append(
                {
                    "task": task_id,
                    "task_decision": "REROLL",
                    "task_reason": recommendation[
                        "reason"
                    ],
                    "reroll_number": None,
                    "slip_cost": None,
                    "master_chance": None,
                    "reroll_status": "INPUT_REQUIRED",
                    "remaining_after_reroll": (
                        current_balance
                    ),
                    "strategy_mode": strategy_context[
                        "strategy_mode"
                    ],
                }
            )

            continue

        result = evaluate_task_reroll_with_strategy(
            task_id=task_id,
            task=task_map[task_id],
            reroll_number=reroll_number,
            slip_balance=current_balance,
            strategy_context=strategy_context,
        )

        results.append(result)

        if result["reroll_status"] == "ALLOWED":
            current_balance = result[
                "remaining_after_reroll"
            ]

    return {
        "strategy_mode": strategy_context[
            "strategy_mode"
        ],
        "starting_slips": slip_balance,
        "ending_slips": current_balance,
        "reroll_results": results,
    }



# ============================================================
# V0.9 — Structured Resource Inventory
# ============================================================

def get_inventory_resource_state(
    inventory,
    resource,
):
    """
    Return a normalized inventory state for one resource.

    Supports both legacy numeric inventory:

        {"regular_choco": 10}

    and V0.9 structured inventory:

        {
            "regular_choco": {
                "on_hand": 10,
                "reserved": 5,
                "available": 5,
            }
        }
    """

    value = inventory.get(
        resource,
        0,
    )

    # --------------------------------------------------------
    # Legacy numeric inventory
    # --------------------------------------------------------

    if isinstance(
        value,
        (int, float),
    ) and not isinstance(
        value,
        bool,
    ):
        return {
            "on_hand": value,
            "reserved": 0,
            "available": value,
        }

    # --------------------------------------------------------
    # Structured V0.9 inventory
    # --------------------------------------------------------

    if isinstance(
        value,
        dict,
    ):
        on_hand = value.get(
            "on_hand",
            0,
        )

        reserved = value.get(
            "reserved",
            0,
        )

        return {
            "on_hand": on_hand,
            "reserved": reserved,
            "available": (
                on_hand - reserved
            ),
        }

    raise ValueError(
        "Unsupported inventory value for "
        f"{resource}: {value!r}"
    )


def check_resource_availability(
    resource,
    quantity_needed,
    inventory,
):
    state = get_inventory_resource_state(
        inventory,
        resource,
    )

    on_hand = state[
        "on_hand"
    ]

    reserved = state[
        "reserved"
    ]

    available = state[
        "available"
    ]

    can_execute = (
        available >= quantity_needed
    )

    shortfall = max(
        0,
        quantity_needed - available,
    )

    reserve_constrained = (
        not can_execute
        and on_hand >= quantity_needed
    )

    return {
        "resource": resource,
        "quantity_needed": quantity_needed,
        "quantity_on_hand": on_hand,
        "quantity_reserved": reserved,
        "quantity_available": available,
        "can_execute": can_execute,
        "shortfall": shortfall,
        "reserve_constrained": (
            reserve_constrained
        ),
    }




def check_combo_resource_availability(
    recommendation,
    inventory,
):
    if recommendation["decision"] != "COMBO":
        return None

    return check_resource_availability(
        resource=recommendation[
            "resource"
        ],
        quantity_needed=recommendation[
            "quantity_needed"
        ],
        inventory=inventory,
    )


def evaluate_combo_inventory(
    analysis,
    inventory,
):
    results = []

    for recommendation in analysis[
        "recommendations"
    ]:
        if recommendation["decision"] != "COMBO":
            continue

        availability = (
            check_combo_resource_availability(
                recommendation,
                inventory,
            )
        )

        results.append(
            {
                "tasks": recommendation["tasks"],
                **availability,
            }
        )

    return results


def summarize_combo_inventory(
    combo_inventory_results,
):
    executable = 0
    blocked = 0
    resource_shortfalls = {}

    for result in combo_inventory_results:
        if result["can_execute"]:
            executable += 1
        else:
            blocked += 1

            resource = result["resource"]

            resource_shortfalls[resource] = (
                resource_shortfalls.get(
                    resource,
                    0,
                )
                + result["shortfall"]
            )

    return {
        "combos_considered": len(
            combo_inventory_results
        ),
        "combos_executable": executable,
        "combos_blocked": blocked,
        "resource_shortfalls": (
            resource_shortfalls
        ),
    }


def add_inventory_to_recommendations(
    analysis,
    inventory,
):
    updated_recommendations = []

    for recommendation in analysis[
        "recommendations"
    ]:
        updated = dict(recommendation)

        if recommendation["decision"] == "COMBO":
            availability = (
                check_combo_resource_availability(
                    recommendation,
                    inventory,
                )
            )

            updated["inventory_status"] = (
                "READY"
                if availability["can_execute"]
                else "SHORTFALL"
            )

            updated["quantity_on_hand"] = (
                availability[
                    "quantity_on_hand"
                ]
            )

            updated["quantity_reserved"] = (
                availability[
                    "quantity_reserved"
                ]
            )

            updated["quantity_available"] = (
                availability[
                    "quantity_available"
                ]
            )

            updated["shortfall"] = availability[
                "shortfall"
            ]

            updated["reserve_constrained"] = (
                availability[
                    "reserve_constrained"
                ]
            )

        updated_recommendations.append(
            updated
        )

    return updated_recommendations


def add_keep_inventory_status(
    recommendations,
    task_map,
    inventory,
):
    updated_recommendations = []

    for recommendation in recommendations:
        updated = dict(
            recommendation
        )

        if recommendation["decision"] == "KEEP":
            task_id = recommendation[
                "task"
            ]

            task = task_map[
                task_id
            ]

            resource = task.get(
                "resource"
            )

            if (
                resource is not None
                and resource in inventory
            ):
                quantity_needed = task[
                    "quantity"
                ]

                availability = (
                    check_resource_availability(
                        resource=resource,
                        quantity_needed=(
                            quantity_needed
                        ),
                        inventory=inventory,
                    )
                )

                updated[
                    "resource"
                ] = resource

                updated[
                    "quantity_needed"
                ] = quantity_needed

                updated[
                    "quantity_on_hand"
                ] = availability[
                    "quantity_on_hand"
                ]

                updated[
                    "quantity_reserved"
                ] = availability[
                    "quantity_reserved"
                ]

                updated[
                    "quantity_available"
                ] = availability[
                    "quantity_available"
                ]

                updated[
                    "inventory_status"
                ] = (
                    "READY"
                    if availability[
                        "can_execute"
                    ]
                    else "SHORTFALL"
                )

                updated[
                    "shortfall"
                ] = availability[
                    "shortfall"
                ]

                updated[
                    "reserve_constrained"
                ] = availability[
                    "reserve_constrained"
                ]

        updated_recommendations.append(
            updated
        )

    return updated_recommendations


# ============================================================
# V0.9 — Recommendation Owned-Axie Candidates
# ============================================================

def sort_axie_ids(
    axie_ids,
):
    def sort_key(axie_id):
        axie_text = str(axie_id)

        if axie_text.isdigit():
            return (
                0,
                int(axie_text),
            )

        return (
            1,
            axie_text,
        )

    return sorted(
        {
            str(axie_id)
            for axie_id in axie_ids
        },
        key=sort_key,
    )


def copy_owned_axie_candidate_fields(
    recommendation,
    task,
):
    updated = dict(
        recommendation
    )

    if (
        "owned_axie_candidate_applicable"
        not in task
    ):
        return updated

    updated[
        "owned_axie_candidate_applicable"
    ] = task[
        "owned_axie_candidate_applicable"
    ]

    updated[
        "owned_axie_candidate_reason"
    ] = task.get(
        "owned_axie_candidate_reason"
    )

    updated[
        "eligible_owned_axie_ids"
    ] = list(
        task.get(
            "eligible_owned_axie_ids",
            [],
        )
    )

    updated[
        "eligible_owned_axie_count"
    ] = len(
        updated[
            "eligible_owned_axie_ids"
        ]
    )

    updated[
        "unknown_owned_axie_ids"
    ] = list(
        task.get(
            "unknown_owned_axie_ids",
            [],
        )
    )

    updated[
        "unknown_owned_axie_count"
    ] = len(
        updated[
            "unknown_owned_axie_ids"
        ]
    )

    updated[
        "axie_qualification_criteria"
    ] = task.get(
        "axie_qualification_criteria"
    )

    return updated


def add_owned_axie_candidates_to_recommendations(
    recommendations,
    task_map,
):
    """
    Copy live owned-Axie qualification results from the
    enriched task map into optimizer recommendations.

    KEEP / REROLL:
        Copy the candidate state for that task.

    COMBO:
        Use the intersection of eligible Axies from both
        tasks. An Axie must satisfy both requirements to
        execute the shared action safely.

    Legacy optimizer mode:
        If task enrichment is absent, recommendations are
        returned unchanged.
    """

    updated_recommendations = []

    for recommendation in recommendations:
        decision = recommendation[
            "decision"
        ]

        # ----------------------------------------------------
        # KEEP / REROLL
        # ----------------------------------------------------

        if decision in {
            "KEEP",
            "REROLL",
        }:
            task_id = recommendation[
                "task"
            ]

            task = task_map[
                task_id
            ]

            updated = (
                copy_owned_axie_candidate_fields(
                    recommendation,
                    task,
                )
            )

            updated_recommendations.append(
                updated
            )

            continue

        # ----------------------------------------------------
        # COMBO
        # ----------------------------------------------------

        if decision == "COMBO":
            updated = dict(
                recommendation
            )

            task_ids = list(
                recommendation[
                    "tasks"
                ]
            )

            tasks = [
                task_map[
                    task_id
                ]
                for task_id in task_ids
            ]

            enrichment_present = all(
                (
                    "owned_axie_candidate_applicable"
                    in task
                )
                for task in tasks
            )

            if not enrichment_present:
                updated_recommendations.append(
                    updated
                )
                continue

            applicable_flags = [
                bool(
                    task[
                        "owned_axie_candidate_applicable"
                    ]
                )
                for task in tasks
            ]

            if all(
                applicable_flags
            ):
                candidate_sets = [
                    set(
                        str(axie_id)
                        for axie_id
                        in task.get(
                            "eligible_owned_axie_ids",
                            [],
                        )
                    )
                    for task in tasks
                ]

                shared_candidates = (
                    set.intersection(
                        *candidate_sets
                    )
                    if candidate_sets
                    else set()
                )

                shared_candidates = sort_axie_ids(
                    shared_candidates
                )

                updated[
                    "owned_axie_candidate_applicable"
                ] = True

                updated[
                    "owned_axie_candidate_reason"
                ] = None

                updated[
                    "eligible_owned_axie_ids"
                ] = shared_candidates

                updated[
                    "eligible_owned_axie_count"
                ] = len(
                    shared_candidates
                )

                updated[
                    "axie_qualification_criteria_by_task"
                ] = {
                    task_id: task_map[
                        task_id
                    ].get(
                        "axie_qualification_criteria"
                    )
                    for task_id in task_ids
                }

            elif not any(
                applicable_flags
            ):
                updated[
                    "owned_axie_candidate_applicable"
                ] = False

                updated[
                    "owned_axie_candidate_reason"
                ] = (
                    "COMBO_DOES_NOT_USE_CURRENT_OWNED_AXIE"
                )

                updated[
                    "eligible_owned_axie_ids"
                ] = []

                updated[
                    "eligible_owned_axie_count"
                ] = 0

            else:
                updated[
                    "owned_axie_candidate_applicable"
                ] = False

                updated[
                    "owned_axie_candidate_reason"
                ] = (
                    "MIXED_OWNED_AXIE_APPLICABILITY"
                )

                updated[
                    "eligible_owned_axie_ids"
                ] = []

                updated[
                    "eligible_owned_axie_count"
                ] = 0

            updated_recommendations.append(
                updated
            )

            continue

        updated_recommendations.append(
            dict(
                recommendation
            )
        )

    return updated_recommendations



def build_execution_plan(
    analysis,
    task_map,
    inventory,
    reroll_numbers,
    slip_balance,
    strategy_context,
    slip_state=None,
    economics_inputs=None,
):

    recommendations = (
        add_inventory_to_recommendations(
            analysis,
            inventory,
        )
    )

    recommendations = add_keep_inventory_status(
        recommendations,
        task_map,
        inventory,
    )

    recommendations = (
        add_owned_axie_candidates_to_recommendations(
            recommendations,
            task_map,
        )
    )

    recommendations = (
        add_bounty_economics_to_recommendations(
            recommendations=(
                recommendations
            ),
            task_map=task_map,
            economics_inputs=(
                economics_inputs
            ),
        )
    )

    reroll_plan = (
        evaluate_board_rerolls_with_strategy(
            analysis=analysis,
            task_map=task_map,
            reroll_numbers=reroll_numbers,
            slip_balance=slip_balance,
            strategy_context=strategy_context,
        )
    )

    if slip_state is None:
        slip_state = normalize_slip_state(
            slip_balance=slip_balance,
            minimum_reserve=strategy_context[
                "minimum_reserve"
            ],
        )

    projected_slip_state = (
        build_projected_slip_state(
            slip_state=slip_state,
            reroll_plan=reroll_plan,
        )
    )


    execution_summary = summarize_execution_plan(
    analysis
    )

    return {
        "strategy_mode": strategy_context[
            "strategy_mode"
        ],
        "task_count": analysis["task_count"],
        "total_bp": analysis["total_bp"],
        "action_count": execution_summary[
            "action_count"
        ],
        "actions_saved": execution_summary[
            "actions_saved"
        ],
        "recommendations": recommendations,
            "starting_slips": reroll_plan[
            "starting_slips"
        ],
        "ending_slips": reroll_plan[
            "ending_slips"
        ],

        # V0.9 structured Fortune Slip state.
        "slip_state": projected_slip_state,

        "reroll_results": reroll_plan[
            "reroll_results"
        ],
    }



def run_v09_recommendation_axie_candidate_test(
    db_path,
):
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 RECOMMENDATION AXIE CANDIDATE TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    daily_input = build_daily_input(
        board_entries=[
            (
                "Feed 1 Premium Choco to any "
                "Shiny Axie you own"
            ),
            (
                "Feed 5 Regular Choco to any "
                "Level 20 or higher Axie you own"
            ),
            "Buy any Bug Axie",
        ],
        inventory={
            "Regular Choco": 10,
            "Premium Choco": 2,
        },
        slip_balance=1000,
        reroll_numbers={},
        strategy_mode="Conserve",
        minimum_reserve=20,
    )

    execution_plan = optimize_daily_input(
        daily_input=daily_input,
        asset=None,
        db_path=db_path,
    )

    recommendations = (
        execution_plan[
            "recommendations"
        ]
    )

    recommendation_by_task = {
        recommendation.get(
            "task"
        ): recommendation
        for recommendation
        in recommendations
        if recommendation.get(
            "task"
        )
    }

    # --------------------------------------------------------
    # Shiny task
    # --------------------------------------------------------

    shiny = recommendation_by_task[
        "feed_premium_collection"
    ]

    shiny_passed = (
        shiny[
            "owned_axie_candidate_applicable"
        ]
        and shiny[
            "eligible_owned_axie_count"
        ] == 1
        and shiny[
            "eligible_owned_axie_ids"
        ] == [
            "11451464",
        ]
    )

    print(
        "Shiny recommendation candidates:",
        "PASS" if shiny_passed else "FAIL",
    )
    print(
        "  Eligible IDs:",
        shiny[
            "eligible_owned_axie_ids"
        ],
    )

    if not shiny_passed:
        all_passed = False

    # --------------------------------------------------------
    # Level 20+ task
    # --------------------------------------------------------

    level_task = recommendation_by_task[
        "feed_5_regular_choco_min_level"
    ]

    level_passed = (
        level_task[
            "owned_axie_candidate_applicable"
        ]
        and level_task[
            "eligible_owned_axie_count"
        ] > 0
        and len(
            level_task[
                "eligible_owned_axie_ids"
            ]
        )
        == level_task[
            "eligible_owned_axie_count"
        ]
    )

    print(
        "Level 20+ recommendation candidates:",
        "PASS" if level_passed else "FAIL",
    )
    print(
        "  Eligible:",
        level_task[
            "eligible_owned_axie_count"
        ],
    )

    if not level_passed:
        all_passed = False

    # --------------------------------------------------------
    # Buy-task guardrail
    # --------------------------------------------------------

    buy_task = recommendation_by_task[
        "buy_random_class_axie"
    ]

    buy_passed = (
        not buy_task[
            "owned_axie_candidate_applicable"
        ]
        and buy_task[
            "eligible_owned_axie_count"
        ] == 0
    )

    print(
        "Buy-task recommendation guardrail:",
        "PASS" if buy_passed else "FAIL",
    )

    if not buy_passed:
        all_passed = False

    # --------------------------------------------------------
    # Formatter
    # --------------------------------------------------------

    formatted_lines = (
        format_execution_plan(
            execution_plan
        )
    )

    candidate_output_present = any(
        "Eligible Axie"
        in line
        for line in formatted_lines
    )

    print(
        "Candidate IDs visible in output:",
        (
            "PASS"
            if candidate_output_present
            else "FAIL"
        ),
    )

    print(
        "\nFormatted actions:"
    )

    for line in formatted_lines:
        print(
            " ",
            line,
        )

    if not candidate_output_present:
        all_passed = False

    print(
        "\nV0.9 Recommendation Axie Candidates:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



def format_owned_axie_candidates(
    recommendation,
    sample_limit=5,
):
    """
    Format owned-Axie candidate information compactly.

    The execution-plan data structure keeps the full ID list.
    Console output shows all IDs only for small candidate sets.
    """

    if (
        "owned_axie_candidate_applicable"
        not in recommendation
    ):
        return ""

    if not recommendation[
        "owned_axie_candidate_applicable"
    ]:
        return ""

    axie_ids = recommendation.get(
        "eligible_owned_axie_ids",
        [],
    )

    count = len(
        axie_ids
    )

    if count == 0:
        return " | Eligible Axies: NONE"

    if count == 1:
        return (
            " | Eligible Axie: "
            f"#{axie_ids[0]}"
        )

    if count <= sample_limit:
        formatted_ids = ", ".join(
            f"#{axie_id}"
            for axie_id in axie_ids
        )

        return (
            " | Eligible Axies: "
            f"{formatted_ids}"
        )

    sample = ", ".join(
        f"#{axie_id}"
        for axie_id
        in axie_ids[
            :sample_limit
        ]
    )

    return (
        f" | Eligible Axies: {count} "
        f"(first {sample_limit}: {sample})"
    )



def format_inventory_reserve_state(
    recommendation,
):
    """
    Add reserve information when structured inventory
    is present in a recommendation.
    """

    if "quantity_on_hand" not in recommendation:
        return ""

    on_hand = recommendation.get(
        "quantity_on_hand",
        0,
    )

    reserved = recommendation.get(
        "quantity_reserved",
        0,
    )

    available = recommendation.get(
        "quantity_available",
        0,
    )

    if reserved <= 0:
        return ""

    if recommendation.get(
        "reserve_constrained",
        False,
    ):
        return (
            f" | On hand: {on_hand}"
            f" | Reserved: {reserved}"
            f" | Spendable: {available}"
            f" | RESERVE PROTECTED"
        )

    return (
        f" | On hand: {on_hand}"
        f" | Reserved: {reserved}"
        f" | Spendable: {available}"
    )



def format_execution_plan(
    execution_plan,
):
    lines = []

    reroll_results_by_task = {
        result["task"]: result
        for result in execution_plan[
            "reroll_results"
        ]
    }

    for recommendation in execution_plan[
        "recommendations"
    ]:
        decision = recommendation["decision"]

        # ====================================================
        # COMBO
        # ====================================================

        if decision == "COMBO":
            tasks = " + ".join(
                recommendation["tasks"]
            )

            status = recommendation.get(
                "inventory_status",
                "UNKNOWN",
            )

            line = (
                f"COMBO: {tasks} -> "
                f"{recommendation['combined_bp']} BP | "
                f"{recommendation['quantity_needed']} "
                f"{recommendation['resource']} | "
                f"{status}"
            )

            if recommendation.get(
                "shortfall",
                0,
            ) > 0:
                line += (
                    f" | shortfall "
                    f"{recommendation['shortfall']}"
                )

            line += (
                format_inventory_reserve_state(
                    recommendation
                )
            )

            line += (
                format_owned_axie_candidates(
                    recommendation
                )
            )

            line += (
                format_bounty_economics(
                    recommendation
                )
            )

            lines.append(line)

        # ====================================================
        # KEEP
        # ====================================================

        elif decision == "KEEP":
            line = (
                f"KEEP: {recommendation['task']} -> "
                f"{recommendation['reward_bp']} BP"
            )

            if "inventory_status" in recommendation:
                line += (
                    f" | {recommendation['quantity_needed']} "
                    f"{recommendation['resource']} | "
                    f"{recommendation['inventory_status']}"
                )

                if recommendation.get(
                    "shortfall",
                    0,
                ) > 0:
                    line += (
                        f" | shortfall "
                        f"{recommendation['shortfall']}"
                    )

            line += (
                format_inventory_reserve_state(
                    recommendation
                )
            )

            line += (
                format_owned_axie_candidates(
                    recommendation
                )
            )

            line += (
                format_bounty_economics(
                    recommendation
                )
            )

            lines.append(line)

        # ====================================================
        # REROLL
        # ====================================================

        elif decision == "REROLL":
            task_id = recommendation["task"]

            reroll_result = (
                reroll_results_by_task.get(
                    task_id
                )
            )

            if reroll_result is None:
                lines.append(
                    f"REROLL: {task_id}"
                )

            elif (
                reroll_result["reroll_status"]
                == "INPUT_REQUIRED"
            ):
                lines.append(
                    f"REROLL: {task_id} -> "
                    f"INPUT REQUIRED | "
                    f"{reroll_result['task_reason']}"
                )

            else:
                lines.append(
                    f"REROLL: {task_id} -> "
                    f"reroll "
                    f"{reroll_result['reroll_number']} | "
                    f"{reroll_result['slip_cost']} slips | "
                    f"Master "
                    f"{reroll_result['master_chance'] * 100:.0f}% | "
                    f"{reroll_result['reroll_status']} | "
                    f"{reroll_result['task_reason']}"
                )

    return lines

def format_execution_summary(
    execution_plan,
):
    return [
        (
            f"Strategy: "
            f"{execution_plan['strategy_mode']}"
        ),
        (
            f"Bounty tasks: "
            f"{execution_plan['task_count']}"
        ),
        (
            f"Total BP: "
            f"{execution_plan['total_bp']}"
        ),
        (
            f"Execution actions: "
            f"{execution_plan['action_count']}"
        ),
        (
            f"Actions saved: "
            f"{execution_plan['actions_saved']}"
        ),
        (
            f"Pending-plan slips: "
            f"{execution_plan['starting_slips']} "
            f"-> "
            f"{execution_plan['ending_slips']}"
        ),
    ]


def validate_execution_plan(
    execution_plan,
):
    accounted_tasks = []

    for recommendation in execution_plan[
        "recommendations"
    ]:
        decision = recommendation["decision"]

        if decision == "COMBO":
            accounted_tasks.extend(
                recommendation["tasks"]
            )

        elif decision in {"KEEP", "REROLL"}:
            accounted_tasks.append(
                recommendation["task"]
            )

    unique_tasks = set(accounted_tasks)

    return {
        "expected_task_count": execution_plan[
            "task_count"
        ],
        "accounted_task_count": len(
            accounted_tasks
        ),
        "unique_task_count": len(
            unique_tasks
        ),
        "all_tasks_accounted_for": (
            len(accounted_tasks)
            == execution_plan["task_count"]
        ),
        "no_duplicate_tasks": (
            len(accounted_tasks)
            == len(unique_tasks)
        ),
    }


def evaluate_v1_readiness(
    execution_plan,
):
    validation = validate_execution_plan(
        execution_plan
    )

    input_required = any(
        result["reroll_status"] == "INPUT_REQUIRED"
        for result in execution_plan[
            "reroll_results"
        ]
    )

    structurally_ready = (
        validation["all_tasks_accounted_for"]
        and validation["no_duplicate_tasks"]
    )

    if not structurally_ready:
        status = "NOT_READY"

    elif input_required:
        status = "INPUT_REQUIRED"

    else:
        status = "READY"

    return {
        **validation,
        "input_required": input_required,
        "v1_status": status,
    }


def resolve_catalog_id(
    entry,
):
    if isinstance(entry, str):
        task_name = entry

    else:
        if "catalog_id" in entry:
            return entry["catalog_id"]

        task_name = entry.get(
            "task_name"
        )

    if task_name in TASK_NAME_ALIASES:
        return TASK_NAME_ALIASES[
            task_name
        ]

    normalized_name = (
        normalize_bounty_task_name(
            task_name
        )
    )

    catalog_id = (
        NORMALIZED_TASK_NAME_ALIASES.get(
            normalized_name
        )
    )

    if catalog_id is not None:
        return catalog_id

    raise ValueError(
        f"Unknown task_name: {task_name}"
    )



def run_v09_task_name_resolution_test():
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 TASK NAME RESOLUTION TEST"
    )
    print(
        "============================================================"
    )

    test_cases = [
        (
            "Buy any Axie",
            "app_axie_buy_any_axie",
        ),
        (
            "Buy an Axie",
            "app_axie_buy_any_axie",
        ),
        (
            "Any Axie",
            "app_axie_buy_any_axie",
        ),
        (
            "  BUY ANY AXIE  ",
            "app_axie_buy_any_axie",
        ),
        (
            "Open a Premium Pouch",
            "app_axie_open_1_premium_pouch",
        ),
        (
            "1 Premium Pouch",
            "app_axie_open_1_premium_pouch",
        ),
        (
            "Feed 1 Choco to any Axie",
            "app_axie_feed_1_regular_choco",
        ),
        (
            "Feed 10 Regular Choco to any Axie",
            "app_axie_feed_10_choco_any_axie",
        ),
        (
            (
                "Feed 5 Regular Choco to any "
                "Evolved Axie you own"
            ),
            (
                "app_axie_"
                "feed_5_regular_choco_evolved"
            ),
        ),
        (
            "Open 3 Regular Lucky Pouches",
            (
                "app_axie_"
                "open_3_regular_pouches"
            ),
        ),
        (
            "Release any Beast Axie",
            "app_axie_release_beast_axie",
        ),
        (
            "3 Regular Choco",
            "app_axie_buy_3_regular_choco",
        ),
        (
            "Craft any Rune",
            "origins_craft_any_rune",
        ),
    ]

    all_passed = True

    for (
        task_name,
        expected_catalog_id,
    ) in test_cases:
        actual_catalog_id = (
            resolve_catalog_id(
                task_name
            )
        )

        passed = (
            actual_catalog_id
            == expected_catalog_id
        )

        print(
            f"{task_name!r}:",
            "PASS" if passed else "FAIL",
        )

        print(
            "  Actual:",
            actual_catalog_id,
        )

        print(
            "  Expected:",
            expected_catalog_id,
        )

        if not passed:
            all_passed = False

    unknown_guardrail_passed = False

    try:
        resolve_catalog_id(
            "Completely Unknown Bounty"
        )

    except ValueError as exc:
        unknown_guardrail_passed = True

        print(
            "Unknown-task guardrail: PASS"
        )
        print(
            "  Message:",
            str(exc),
        )

    else:
        print(
            "Unknown-task guardrail: FAIL"
        )
        all_passed = False

    if not unknown_guardrail_passed:
        all_passed = False

    print(
        "\nV0.9 Task Name Resolution:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



# ============================================================
# V0.9 — Parameterized Bounty Task Resolution
# ============================================================

AXIE_CLASS_NAME_MAP = {
    "aqua": "Aquatic",
    "aquatic": "Aquatic",
    "beast": "Beast",
    "bird": "Bird",
    "bug": "Bug",
    "dawn": "Dawn",
    "dusk": "Dusk",
    "mech": "Mech",
    "plant": "Plant",
    "reptile": "Reptile",
}


COLLECTION_NAME_MAP = {
    "jap": "JAPANESE",
    "japanese": "JAPANESE",
    "shiny": "SHINY",
    "mystic": "MYSTIC",
    "summer": "SUMMER",
    "nightmare": "NIGHTMARE",
    "xmas": "XMAS",
    "origin": "ORIGIN",
    "meo corp i": "MEO_CORP_I",
    "meo corp ii": "MEO_CORP_II",
}


def normalize_axie_class_phrase(
    class_name,
):
    normalized = (
        str(class_name)
        .strip()
        .casefold()
    )

    resolved = AXIE_CLASS_NAME_MAP.get(
        normalized
    )

    if resolved is None:
        raise ValueError(
            "Unsupported Axie class phrase: "
            f"{class_name!r}"
        )

    return resolved


def normalize_collection_phrase(
    collection_name,
):
    normalized = (
        str(collection_name)
        .strip()
        .casefold()
    )

    resolved = COLLECTION_NAME_MAP.get(
        normalized
    )

    if resolved is None:
        raise ValueError(
            "Unsupported collection phrase: "
            f"{collection_name!r}"
        )

    return resolved



def normalize_body_part_requirement_phrase(
    part_phrase,
):
    """
    Convert human Bounty wording such as:

        Catfish mouth
        Cuckoo horn
        Horn Antenna

    into the canonical Origins body-part name used by
    the V0.8 qualification layer:

        Catfish
        Cuckoo
        Antenna
    """

    normalized = " ".join(
        str(part_phrase).strip().split()
    )

    if not normalized:
        raise ValueError(
            "Body-part requirement cannot be empty."
        )

    part_slots = {
        "eyes",
        "ears",
        "back",
        "mouth",
        "horn",
        "tail",
    }

    words = normalized.split()

    if (
        len(words) > 1
        and words[0].casefold()
        in part_slots
    ):
        words = words[1:]

    if (
        len(words) > 1
        and words[-1].casefold()
        in part_slots
    ):
        words = words[:-1]

    normalized_name = " ".join(
        words
    ).strip()

    if not normalized_name:
        raise ValueError(
            "Body-part requirement has no "
            "canonical part name."
        )

    return normalized_name.title()



def resolve_parameterized_bounty_task_name(
    task_name,
):
    """
    Resolve known parameterized App.Axie Bounty wording.

    Returns:
        dict:
            {
                "catalog_id": ...,
                "parameters": {...},
            }

        None:
            No parameterized pattern matched.
    """

    normalized = (
        normalize_bounty_task_name(
            task_name
        )
    )

    # --------------------------------------------------------
    # Buy any <class> Axie
    # --------------------------------------------------------

    match = re.fullmatch(
        (
            r"(?:buy\s+)?any\s+"
            r"(aqua|aquatic|beast|bird|bug|"
            r"dawn|dusk|mech|plant|reptile)"
            r"\s+axie"
        ),
        normalized,
    )

    if match:
        return {
            "catalog_id": (
                "app_axie_buy_random_class_axie"
            ),
            "parameters": {
                "random_class": (
                    normalize_axie_class_phrase(
                        match.group(1)
                    )
                ),
            },
        }

        # --------------------------------------------------------
    # Buy / Any <class> Axie with <body part>
    # --------------------------------------------------------

    match = re.fullmatch(
        (
            r"(?:buy\s+)?(?:any\s+)?"
            r"(aqua|aquatic|beast|bird|bug|"
            r"dawn|dusk|mech|plant|reptile)"
            r"\s+axie\s+with\s+(.+)"
        ),
        normalized,
    )

    if match:
        return {
            "catalog_id": (
                "app_axie_buy_class_with_part"
            ),
            "parameters": {
                "random_class": (
                    normalize_axie_class_phrase(
                        match.group(1)
                    )
                ),
                "required_part_name": (
                    normalize_body_part_requirement_phrase(
                        match.group(2)
                    )
                ),
            },
        }
    
    # --------------------------------------------------------
    # Feed 10 Choco to any <class> Axie
    # --------------------------------------------------------

    match = re.fullmatch(
        (
            r"(?:feed\s+)?10\s+"
            r"(?:regular\s+)?choco\s+to\s+any\s+"
            r"(aqua|aquatic|beast|bird|bug|"
            r"dawn|dusk|mech|plant|reptile)"
            r"(?:\s+axie)?"
        ),
        normalized,
    )

    if match:
        return {
            "catalog_id": (
                "app_axie_"
                "feed_10_choco_random_class"
            ),
            "parameters": {
                "random_class": (
                    normalize_axie_class_phrase(
                        match.group(1)
                    )
                ),
            },
        }

    # --------------------------------------------------------
    # Premium Choco to a named collectible collection
    # --------------------------------------------------------

    match = re.fullmatch(
        (
            r"(?:feed\s+)?1\s+premium\s+choco\s+"
            r"to\s+any\s+"
            r"(jap|japanese|shiny|mystic|summer|"
            r"nightmare|xmas|origin|"
            r"meo\s+corp\s+i|meo\s+corp\s+ii)"
            r"\s+axie"
            r"(?:\s+you\s+own)?"
        ),
        normalized,
    )

    if match:
        return {
            "catalog_id": (
                "app_axie_feed_premium_collection"
            ),
            "parameters": {
                "collection": (
                    normalize_collection_phrase(
                        match.group(1)
                    )
                ),
            },
        }

    # --------------------------------------------------------
    # Feed 5 Regular Choco to Level N+ Axie
    # --------------------------------------------------------

    match = re.fullmatch(
        (
            r"feed\s+5\s+(?:regular\s+)?choco\s+"
            r"to\s+any\s+level\s+"
            r"(\d+)\s+or\s+higher\s+axie"
            r"(?:\s+you\s+own)?"
        ),
        normalized,
    )

    if match:
        return {
            "catalog_id": (
                "app_axie_"
                "feed_5_regular_choco_min_level"
            ),
            "parameters": {
                "min_level": int(
                    match.group(1)
                ),
            },
        }

    # --------------------------------------------------------
    # Release any <class> Axie
    # --------------------------------------------------------

    match = re.fullmatch(
        (
            r"release\s+any\s+"
            r"(aqua|aquatic|beast|bird|bug|"
            r"dawn|dusk|mech|plant|reptile)"
            r"\s+axie"
        ),
        normalized,
    )

    if match:
        return {
            "catalog_id": (
                "app_axie_"
                "release_random_class_axie"
            ),
            "parameters": {
                "random_class": (
                    normalize_axie_class_phrase(
                        match.group(1)
                    )
                ),
            },
        }

    # --------------------------------------------------------
    # Generic release
    # --------------------------------------------------------

    if normalized == "release any axie":
        return {
            "catalog_id": (
                "app_axie_release_any_axie"
            ),
            "parameters": {},
        }

    # --------------------------------------------------------
    # Buy any Evolved Axie
    # --------------------------------------------------------

    if normalized == "buy any evolved axie":
        return {
            "catalog_id": (
                "app_axie_buy_evolved_axie"
            ),
            "parameters": {},
        }

    # --------------------------------------------------------
    # Evolve an Axie
    # --------------------------------------------------------

    if normalized in {
        "evolve an axie",
        "evolve any axie",
    }:
        return {
            "catalog_id": (
                "app_axie_evolve_any_axie"
            ),
            "parameters": {},
        }

    # --------------------------------------------------------
    # Ascend Level N or higher Axie
    # --------------------------------------------------------

    match = re.fullmatch(
        (
            r"(?:ascend\s+)?"
            r"level\s+(\d+)\s+or\s+higher\s+axie"
        ),
        normalized,
    )

    if match:
        return {
            "catalog_id": (
                "app_axie_ascend_min_level_axie"
            ),
            "parameters": {
                "min_level": int(
                    match.group(1)
                ),
            },
        }

    return None


def resolve_bounty_task_definition(
    entry,
):
    """
    Resolve a human-readable or structured Bounty entry into
    a canonical catalog ID plus instantiation parameters.
    """

    if isinstance(entry, dict):
        if "catalog_id" in entry:
            parameters = dict(
                entry.get(
                    "parameters",
                    {}
                )
            )

            for parameter_name in (
                "random_class",
                "required_part_name",
                "collection",
                "min_level",
            ):
                if parameter_name in entry:
                    parameters[
                        parameter_name
                    ] = entry[
                        parameter_name
                    ]

            return {
                "catalog_id": entry[
                    "catalog_id"
                ],
                "parameters": parameters,
            }

        task_name = entry.get(
            "task_name"
        )

    else:
        task_name = entry

    # First preserve all exact / normalized legacy aliases.
    try:
        catalog_id = resolve_catalog_id(
            task_name
        )

    except ValueError:
        catalog_id = None

    if catalog_id is not None:
        parameters = {}

        if isinstance(entry, dict):
            for parameter_name in (
                "random_class",
                "required_part_name",
                "collection",
                "min_level",
            ):
                if parameter_name in entry:
                    parameters[
                        parameter_name
                    ] = entry[
                        parameter_name
                    ]

        return {
            "catalog_id": catalog_id,
            "parameters": parameters,
        }

    parameterized = (
        resolve_parameterized_bounty_task_name(
            task_name
        )
    )

    if parameterized is not None:
        return parameterized

    raise ValueError(
        f"Unknown task_name: {task_name}"
    )


def run_v09_parameterized_task_resolution_test():
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 PARAMETERIZED TASK RESOLUTION TEST"
    )
    print(
        "============================================================"
    )

    test_cases = [
        {
            "task_name": "Buy any Bug Axie",
            "catalog_id": (
                "app_axie_buy_random_class_axie"
            ),
            "parameters": {
                "random_class": "Bug",
            },
        },
        {
            "task_name": "Any Beast Axie",
            "catalog_id": (
                "app_axie_buy_random_class_axie"
            ),
            "parameters": {
                "random_class": "Beast",
            },
        },
        {
            "task_name": (
                "Buy any Bird Axie with Scaly Spear"
            ),
            "catalog_id": (
                "app_axie_buy_class_with_part"
            ),
            "parameters": {
                "random_class": "Bird",
                "required_part_name": (
                    "Scaly Spear"
                ),
            },
        },
        {
            "task_name": (
                "Any Beast Axie with Catfish mouth"
            ),
            "catalog_id": (
                "app_axie_buy_class_with_part"
            ),
            "parameters": {
                "random_class": "Beast",
                "required_part_name": "Catfish",
            },
        },
        {
            "task_name": (
                "Any Plant Axie with Cuckoo horn"
            ),
            "catalog_id": (
                "app_axie_buy_class_with_part"
            ),
            "parameters": {
                "random_class": "Plant",
                "required_part_name": "Cuckoo",
            },
        },
        {
            "task_name": (
                "Buy any Aqua Axie with Horn Antenna"
            ),
            "catalog_id": (
                "app_axie_buy_class_with_part"
            ),
            "parameters": {
                "random_class": "Aquatic",
                "required_part_name": "Antenna",
            },
        },
        {
            "task_name": (
                "Feed 10 Choco to any Aqua Axie"
            ),
            "catalog_id": (
                "app_axie_"
                "feed_10_choco_random_class"
            ),
            "parameters": {
                "random_class": "Aquatic",
            },
        },
        {
            "task_name": (
                "10 Regular Choco to any Bird"
            ),
            "catalog_id": (
                "app_axie_"
                "feed_10_choco_random_class"
            ),
            "parameters": {
                "random_class": "Bird",
            },
        },
        {
            "task_name": (
                "Feed 1 Premium Choco to any Jap Axie"
            ),
            "catalog_id": (
                "app_axie_feed_premium_collection"
            ),
            "parameters": {
                "collection": "JAPANESE",
            },
        },
        {
            "task_name": (
                "Feed 1 Premium Choco to any Shiny "
                "Axie you own"
            ),
            "catalog_id": (
                "app_axie_feed_premium_collection"
            ),
            "parameters": {
                "collection": "SHINY",
            },
        },
        {
            "task_name": (
                "Feed 5 Regular Choco to any "
                "Level 20 or higher Axie you own"
            ),
            "catalog_id": (
                "app_axie_"
                "feed_5_regular_choco_min_level"
            ),
            "parameters": {
                "min_level": 20,
            },
        },
        {
            "task_name": "Release any Dawn Axie",
            "catalog_id": (
                "app_axie_"
                "release_random_class_axie"
            ),
            "parameters": {
                "random_class": "Dawn",
            },
        },
        {
            "task_name": "Release any Axie",
            "catalog_id": (
                "app_axie_release_any_axie"
            ),
            "parameters": {},
        },
        {
            "task_name": "Buy any Evolved Axie",
            "catalog_id": (
                "app_axie_buy_evolved_axie"
            ),
            "parameters": {},
        },
        {
            "task_name": "Evolve an Axie",
            "catalog_id": (
                "app_axie_evolve_any_axie"
            ),
            "parameters": {},
        },
        {
            "task_name": "Level 19 or higher Axie",
            "catalog_id": (
                "app_axie_ascend_min_level_axie"
            ),
            "parameters": {
                "min_level": 19,
            },
        },
    ]

    all_passed = True

    for test_case in test_cases:
        actual = (
            resolve_bounty_task_definition(
                test_case["task_name"]
            )
        )

        expected = {
            "catalog_id": (
                test_case["catalog_id"]
            ),
            "parameters": (
                test_case["parameters"]
            ),
        }

        passed = actual == expected

        print(
            f"{test_case['task_name']!r}:",
            "PASS" if passed else "FAIL",
        )

        print(
            "  Actual:",
            actual,
        )

        print(
            "  Expected:",
            expected,
        )

        if not passed:
            all_passed = False

    print(
        "\nV0.9 Parameterized Task Resolution:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



def build_task_id(
    catalog_id,
):
    prefixes = (
        "app_axie_",
        "origins_",
        "axie_quest_",
    )

    for prefix in prefixes:
        if catalog_id.startswith(prefix):
            return catalog_id[
                len(prefix):
            ]

    return catalog_id


def resolve_task_id(
    entry,
    catalog_id,
):
    if isinstance(entry, dict):
        if "task_id" in entry:
            return entry["task_id"]

    return build_task_id(
        catalog_id
    )





def build_daily_board(
    board_entries,
):
    board = {}

    for entry in board_entries:
        resolution = (
            resolve_bounty_task_definition(
                entry
            )
        )

        catalog_id = resolution[
            "catalog_id"
        ]

        parameters = dict(
            resolution.get(
                "parameters",
                {},
            )
        )

        if catalog_id not in BOUNTY_TASK_CATALOG:
            raise ValueError(
                "Resolved Bounty catalog ID "
                "does not exist: "
                f"{catalog_id}"
            )

        task_id = resolve_task_id(
            entry,
            catalog_id,
        )

        catalog_task = (
            BOUNTY_TASK_CATALOG[
                catalog_id
            ]
        )

        task = instantiate_task(
            catalog_task,
            **parameters,
        )

        board[task_id] = task

    return board



def run_v09_daily_board_resolution_test():
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 DAILY BOARD RESOLUTION TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    # --------------------------------------------------------
    # Test 1 — Existing daily input remains compatible
    # --------------------------------------------------------

    legacy_board = build_daily_board(
        DAILY_BOARD_ENTRIES
    )

    legacy_passed = (
        len(legacy_board)
        == len(DAILY_BOARD_ENTRIES)
    )

    print(
        "Existing DAILY_BOARD_ENTRIES:",
        "PASS" if legacy_passed else "FAIL",
    )

    print(
        "  Input entries:",
        len(DAILY_BOARD_ENTRIES),
    )

    print(
        "  Built tasks:",
        len(legacy_board),
    )

    if not legacy_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 2 — Class + body-part purchase
    # --------------------------------------------------------

    bird_board = build_daily_board(
        [
            (
                "Buy any Bird Axie "
                "with Scaly Spear"
            ),
        ]
    )

    bird_task = bird_board[
        "buy_class_with_part"
    ]

    bird_passed = (
        bird_task[
            "target_filters"
        ] == {
            "class": "Bird",
            "required_part_names": (
                "Scaly Spear"
            ),
        }
    )

    print(
        "Bird + Scaly Spear:",
        "PASS" if bird_passed else "FAIL",
    )

    print(
        "  Filters:",
        bird_task[
            "target_filters"
        ],
    )

    if not bird_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 3 — Collection feed
    # --------------------------------------------------------

    shiny_board = build_daily_board(
        [
            (
                "Feed 1 Premium Choco to any "
                "Shiny Axie you own"
            ),
        ]
    )

    shiny_task = shiny_board[
        "feed_premium_collection"
    ]

    shiny_passed = (
        shiny_task[
            "target_filters"
        ] == {
            "required_collections": "SHINY",
        }
    )

    print(
        "Shiny collectible feed:",
        "PASS" if shiny_passed else "FAIL",
    )

    print(
        "  Filters:",
        shiny_task[
            "target_filters"
        ],
    )

    if not shiny_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 4 — Minimum gameplay level
    # --------------------------------------------------------

    level_board = build_daily_board(
        [
            (
                "Feed 5 Regular Choco to any "
                "Level 20 or higher Axie you own"
            ),
        ]
    )

    level_task = level_board[
        "feed_5_regular_choco_min_level"
    ]

    level_passed = (
        level_task[
            "target_filters"
        ] == {
            "min_level": 20,
        }
    )

    print(
        "Level 20+ feed:",
        "PASS" if level_passed else "FAIL",
    )

    print(
        "  Filters:",
        level_task[
            "target_filters"
        ],
    )

    if not level_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 5 — Class release
    # --------------------------------------------------------

    dawn_board = build_daily_board(
        [
            "Release any Dawn Axie",
        ]
    )

    dawn_task = dawn_board[
        "release_random_class_axie"
    ]

    dawn_passed = (
        dawn_task[
            "target_filters"
        ] == {
            "class": "Dawn",
        }
    )

    print(
        "Dawn release:",
        "PASS" if dawn_passed else "FAIL",
    )

    print(
        "  Filters:",
        dawn_task[
            "target_filters"
        ],
    )

    if not dawn_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 6 — Explicit structured entry
    # --------------------------------------------------------

    structured_board = build_daily_board(
        [
            {
                "catalog_id": (
                    "app_axie_"
                    "feed_premium_collection"
                ),
                "task_id": "test_japanese_feed",
                "collection": "JAPANESE",
            },
        ]
    )

    structured_task = (
        structured_board[
            "test_japanese_feed"
        ]
    )

    structured_passed = (
        structured_task[
            "target_filters"
        ] == {
            "required_collections": (
                "JAPANESE"
            ),
        }
    )

    print(
        "Structured parameterized entry:",
        (
            "PASS"
            if structured_passed
            else "FAIL"
        ),
    )

    print(
        "  Filters:",
        structured_task[
            "target_filters"
        ],
    )

    if not structured_passed:
        all_passed = False

    print(
        "\nV0.9 Daily Board Resolution:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed




def normalize_inventory(
    inventory,
):
    normalized = {}

    for resource_name, value in inventory.items():
        resource = RESOURCE_NAME_ALIASES.get(
            resource_name,
            resource_name,
        )

        # ----------------------------------------------------
        # Legacy numeric form
        # ----------------------------------------------------

        if isinstance(
            value,
            (int, float),
        ) and not isinstance(
            value,
            bool,
        ):
            on_hand = value
            reserved = 0

        # ----------------------------------------------------
        # V0.9 structured form
        # ----------------------------------------------------

        elif isinstance(
            value,
            dict,
        ):
            if "on_hand" not in value:
                raise ValueError(
                    "Structured inventory requires "
                    f"'on_hand': {resource_name}"
                )

            on_hand = value[
                "on_hand"
            ]

            reserved = value.get(
                "reserved",
                0,
            )

        else:
            raise ValueError(
                "Inventory quantity must be numeric "
                "or a structured inventory record: "
                f"{resource_name}"
            )

        for field_name, field_value in (
            (
                "on_hand",
                on_hand,
            ),
            (
                "reserved",
                reserved,
            ),
        ):
            if (
                not isinstance(
                    field_value,
                    (int, float),
                )
                or isinstance(
                    field_value,
                    bool,
                )
            ):
                raise ValueError(
                    "Inventory field must be numeric: "
                    f"{resource_name}.{field_name}"
                )

            if field_value < 0:
                raise ValueError(
                    "Inventory cannot be negative: "
                    f"{resource_name}.{field_name}"
                )

        if reserved > on_hand:
            raise ValueError(
                "Inventory reserved quantity cannot "
                "exceed on-hand quantity: "
                f"{resource_name}"
            )

        normalized[
            resource
        ] = {
            "on_hand": on_hand,
            "reserved": reserved,
            "available": (
                on_hand - reserved
            ),
        }

    return normalized




def derive_gameplay_inventory_from_ledger(
    conn,
    player_id="primary",
    item_names=None,
):
    """
    Derive current gameplay inventory from:

        latest verified snapshot
        + inventory_events strictly after that snapshot

    Snapshot rows are authoritative anchors.

    Events occurring at exactly the snapshot timestamp are
    intentionally excluded to prevent double-counting.
    """

    if item_names is None:
        item_names = (
            "Regular Choco",
            "Premium Choco",
        )

    derived_inventory = {}

    for item_name in item_names:
        snapshot = conn.execute(
            """
            SELECT
                id,
                snapshot_datetime,
                quantity_on_hand,
                source
            FROM gameplay_inventory_snapshots
            WHERE player_id = ?
              AND lower(item_type) = 'consumable'
              AND item_name = ?
            ORDER BY
                snapshot_datetime DESC,
                id DESC
            LIMIT 1
            """,
            (
                player_id,
                item_name,
            ),
        ).fetchone()

        if snapshot is None:
            derived_inventory[
                item_name
            ] = {
                "status": "NO_VERIFIED_SNAPSHOT",
                "snapshot_id": None,
                "snapshot_datetime": None,
                "snapshot_quantity": None,
                "event_delta": None,
                "on_hand": None,
            }

            continue

        snapshot_id = snapshot[0]
        snapshot_datetime = snapshot[1]
        snapshot_quantity = snapshot[2]
        snapshot_source = snapshot[3]

        event_row = conn.execute(
            """
            SELECT
                COALESCE(
                    SUM(quantity_change),
                    0
                ),
                COUNT(*)
            FROM inventory_events
            WHERE lower(item_type) = 'consumable'
              AND item_name = ?
              AND event_datetime > ?
            """,
            (
                item_name,
                snapshot_datetime,
            ),
        ).fetchone()

        event_delta = event_row[0]
        event_count = event_row[1]

        current_quantity = (
            snapshot_quantity
            + event_delta
        )

        status = "READY"

        if current_quantity < 0:
            status = "NEGATIVE_DERIVED_BALANCE"

        derived_inventory[
            item_name
        ] = {
            "status": status,
            "snapshot_id": snapshot_id,
            "snapshot_datetime": (
                snapshot_datetime
            ),
            "snapshot_quantity": (
                snapshot_quantity
            ),
            "snapshot_source": (
                snapshot_source
            ),
            "event_delta": event_delta,
            "event_count": event_count,
            "on_hand": current_quantity,
        }

    return derived_inventory


def build_optimizer_inventory_from_gameplay_ledger(
    conn,
    player_id="primary",
    reserves=None,
):
    """
    Convert the verified gameplay inventory ledger into
    the V0.9 structured optimizer inventory format.
    """

    if reserves is None:
        reserves = {}

    derived = (
        derive_gameplay_inventory_from_ledger(
            conn=conn,
            player_id=player_id,
        )
    )

    optimizer_inventory = {}

    for item_name, state in derived.items():
        if state["status"] != "READY":
            raise ValueError(
                "Gameplay inventory is not ready for "
                f"{item_name}: {state['status']}"
            )

        reserved = reserves.get(
            item_name,
            0,
        )

        optimizer_inventory[
            item_name
        ] = {
            "on_hand": state[
                "on_hand"
            ],
            "reserved": reserved,
        }

    return normalize_inventory(
        optimizer_inventory
    )



# ============================================================
# V0.9 — Optimizer Inventory Source Resolution
# ============================================================

INVENTORY_SOURCE_MANUAL = "manual"
INVENTORY_SOURCE_GAMEPLAY_DB = "gameplay_db"


def normalize_optimizer_inventory_source(
    inventory_source,
):
    if not isinstance(
        inventory_source,
        str,
    ):
        raise ValueError(
            "inventory_source must be a string."
        )

    normalized = (
        inventory_source
        .strip()
        .casefold()
    )

    aliases = {
        "manual": (
            INVENTORY_SOURCE_MANUAL
        ),
        "daily_input": (
            INVENTORY_SOURCE_MANUAL
        ),
        "gameplay_db": (
            INVENTORY_SOURCE_GAMEPLAY_DB
        ),
        "database": (
            INVENTORY_SOURCE_GAMEPLAY_DB
        ),
        "db": (
            INVENTORY_SOURCE_GAMEPLAY_DB
        ),
    }

    resolved = aliases.get(
        normalized
    )

    if resolved is None:
        raise ValueError(
            "Unsupported optimizer inventory source: "
            f"{inventory_source!r}"
        )

    return resolved


def resolve_daily_inventory_for_optimization(
    daily_input,
    inventory_source="manual",
    inventory_db_path=None,
    inventory_reserves=None,
    player_id="primary",
):
    """
    Resolve the inventory state used by the optimizer.

    MANUAL:
        Use the already-normalized inventory stored in
        daily_input.

    GAMEPLAY_DB:
        Derive on-hand inventory from the latest verified
        gameplay inventory snapshot plus later inventory
        events, then apply optimizer reserve policy.

    Database inventory is explicitly opt-in.
    """

    source = normalize_optimizer_inventory_source(
        inventory_source
    )

    # --------------------------------------------------------
    # Existing manual mode
    # --------------------------------------------------------

    if source == INVENTORY_SOURCE_MANUAL:
        return {
            "source": source,
            "inventory": daily_input[
                "inventory"
            ],
            "ledger_state": None,
        }

    # --------------------------------------------------------
    # Gameplay database mode
    # --------------------------------------------------------

    if inventory_db_path is None:
        raise ValueError(
            "inventory_db_path is required when "
            "inventory_source='gameplay_db'."
        )

    import sqlite3

    conn = sqlite3.connect(
        inventory_db_path
    )

    try:
        ledger_state = (
            derive_gameplay_inventory_from_ledger(
                conn=conn,
                player_id=player_id,
            )
        )

        not_ready = {
            item_name: state["status"]
            for item_name, state
            in ledger_state.items()
            if state["status"] != "READY"
        }

        if not_ready:
            details = ", ".join(
                (
                    f"{item_name}="
                    f"{status}"
                )
                for item_name, status
                in not_ready.items()
            )

            raise ValueError(
                "Gameplay inventory cannot be used "
                "by the optimizer until verified "
                "snapshots exist: "
                f"{details}"
            )

        optimizer_inventory = (
            build_optimizer_inventory_from_gameplay_ledger(
                conn=conn,
                player_id=player_id,
                reserves=inventory_reserves,
            )
        )

    finally:
        conn.close()

    return {
        "source": source,
        "inventory": optimizer_inventory,
        "ledger_state": ledger_state,
    }



def run_v09_gameplay_inventory_ledger_test():
    import sqlite3

    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 GAMEPLAY INVENTORY LEDGER TEST"
    )
    print(
        "============================================================"
    )

    conn = sqlite3.connect(
        ":memory:"
    )

    conn.execute(
        """
        CREATE TABLE gameplay_inventory_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT NOT NULL DEFAULT 'primary',
            snapshot_datetime TEXT NOT NULL,
            item_type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity_on_hand INTEGER NOT NULL,
            source TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE inventory_events (
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
            created_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    all_passed = True

    # --------------------------------------------------------
    # Verified snapshots
    # --------------------------------------------------------

    conn.execute(
        """
        INSERT INTO gameplay_inventory_snapshots (
            player_id,
            snapshot_datetime,
            item_type,
            item_name,
            quantity_on_hand,
            source
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "primary",
            "2026-08-25 12:00:00",
            "Consumable",
            "Regular Choco",
            20,
            "TEST_VERIFIED",
        ),
    )

    conn.execute(
        """
        INSERT INTO gameplay_inventory_snapshots (
            player_id,
            snapshot_datetime,
            item_type,
            item_name,
            quantity_on_hand,
            source
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "primary",
            "2026-08-25 12:00:00",
            "Consumable",
            "Premium Choco",
            5,
            "TEST_VERIFIED",
        ),
    )

    # --------------------------------------------------------
    # Same-timestamp event must NOT be counted
    # --------------------------------------------------------

    conn.execute(
        """
        INSERT INTO inventory_events (
            event_datetime,
            item_type,
            item_name,
            event_type,
            quantity_change
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "2026-08-25 12:00:00",
            "Consumable",
            "Regular Choco",
            "feed",
            -5,
        ),
    )

    # --------------------------------------------------------
    # Later events ARE counted
    # --------------------------------------------------------

    conn.execute(
        """
        INSERT INTO inventory_events (
            event_datetime,
            item_type,
            item_name,
            event_type,
            quantity_change
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "2026-08-25 12:05:00",
            "Consumable",
            "Regular Choco",
            "feed",
            -10,
        ),
    )

    conn.execute(
        """
        INSERT INTO inventory_events (
            event_datetime,
            item_type,
            item_name,
            event_type,
            quantity_change
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "2026-08-25 12:10:00",
            "Consumable",
            "Regular Choco",
            "pouch_reward",
            3,
        ),
    )

    conn.execute(
        """
        INSERT INTO inventory_events (
            event_datetime,
            item_type,
            item_name,
            event_type,
            quantity_change
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            "2026-08-25 12:15:00",
            "Consumable",
            "Premium Choco",
            "feed",
            -1,
        ),
    )

    derived = (
        derive_gameplay_inventory_from_ledger(
            conn
        )
    )

    # Regular:
    # 20 snapshot - 10 feed + 3 pouch = 13.
    regular_passed = (
        derived[
            "Regular Choco"
        ][
            "on_hand"
        ] == 13
        and derived[
            "Regular Choco"
        ][
            "event_delta"
        ] == -7
        and derived[
            "Regular Choco"
        ][
            "event_count"
        ] == 2
    )

    print(
        "Regular snapshot + delta:",
        "PASS" if regular_passed else "FAIL",
    )
    print(
        "  State:",
        derived[
            "Regular Choco"
        ],
    )

    if not regular_passed:
        all_passed = False

    premium_passed = (
        derived[
            "Premium Choco"
        ][
            "on_hand"
        ] == 4
        and derived[
            "Premium Choco"
        ][
            "event_delta"
        ] == -1
    )

    print(
        "Premium snapshot + delta:",
        "PASS" if premium_passed else "FAIL",
    )
    print(
        "  State:",
        derived[
            "Premium Choco"
        ],
    )

    if not premium_passed:
        all_passed = False

    # --------------------------------------------------------
    # Convert to optimizer structured inventory
    # --------------------------------------------------------

    optimizer_inventory = (
        build_optimizer_inventory_from_gameplay_ledger(
            conn=conn,
            reserves={
                "Regular Choco": 5,
                "Premium Choco": 1,
            },
        )
    )

    optimizer_passed = (
        optimizer_inventory[
            "regular_choco"
        ] == {
            "on_hand": 13,
            "reserved": 5,
            "available": 8,
        }
        and optimizer_inventory[
            "premium_choco"
        ] == {
            "on_hand": 4,
            "reserved": 1,
            "available": 3,
        }
    )

    print(
        "Optimizer inventory conversion:",
        "PASS" if optimizer_passed else "FAIL",
    )
    print(
        "  Inventory:",
        optimizer_inventory,
    )

    if not optimizer_passed:
        all_passed = False

    # --------------------------------------------------------
    # Missing snapshot must remain blocked
    # --------------------------------------------------------

    missing = (
        derive_gameplay_inventory_from_ledger(
            conn=conn,
            item_names=(
                "Unknown Choco",
            ),
        )
    )

    missing_passed = (
        missing[
            "Unknown Choco"
        ][
            "status"
        ] == "NO_VERIFIED_SNAPSHOT"
    )

    print(
        "Missing-snapshot guardrail:",
        "PASS" if missing_passed else "FAIL",
    )

    if not missing_passed:
        all_passed = False

    conn.close()

    print(
        "\nV0.9 Gameplay Inventory Ledger:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



def run_v09_optimizer_inventory_source_test():
    import os
    import sqlite3
    import tempfile

    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 OPTIMIZER INVENTORY SOURCE TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    # --------------------------------------------------------
    # Test 1 — Manual inventory remains the default
    # --------------------------------------------------------

    manual_input = build_daily_input(
        board_entries=[
            "Feed 1 Regular Choco",
        ],
        inventory={
            "Regular Choco": {
                "on_hand": 7,
                "reserved": 2,
            },
            "Premium Choco": 1,
        },
        slip_balance=100,
        reroll_numbers={},
        strategy_mode="Conserve",
        minimum_reserve=20,
    )

    manual_plan = optimize_daily_input(
        daily_input=manual_input,
        asset=None,
    )

    manual_recommendation = next(
        recommendation
        for recommendation
        in manual_plan["recommendations"]
        if recommendation.get("task")
        == "feed_1_regular_choco"
    )

    manual_passed = (
        manual_plan[
            "inventory_source"
        ] == "manual"
        and manual_plan[
            "inventory_ledger_state"
        ] is None
        and manual_recommendation[
            "quantity_on_hand"
        ] == 7
        and manual_recommendation[
            "quantity_reserved"
        ] == 2
        and manual_recommendation[
            "quantity_available"
        ] == 5
    )

    print(
        "Manual inventory default:",
        "PASS" if manual_passed else "FAIL",
    )
    print(
        "  Source:",
        manual_plan[
            "inventory_source"
        ],
    )
    print(
        "  On hand:",
        manual_recommendation[
            "quantity_on_hand"
        ],
    )
    print(
        "  Reserved:",
        manual_recommendation[
            "quantity_reserved"
        ],
    )
    print(
        "  Available:",
        manual_recommendation[
            "quantity_available"
        ],
    )

    if not manual_passed:
        all_passed = False

    # --------------------------------------------------------
    # Build isolated gameplay inventory database
    # --------------------------------------------------------

    temp_file = tempfile.NamedTemporaryFile(
        suffix=".db",
        delete=False,
    )

    temp_path = temp_file.name
    temp_file.close()

    conn = sqlite3.connect(
        temp_path
    )

    try:
        conn.execute(
            """
            CREATE TABLE gameplay_inventory_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL DEFAULT 'primary',
                snapshot_datetime TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_name TEXT NOT NULL,
                quantity_on_hand INTEGER NOT NULL,
                source TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE inventory_events (
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
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            INSERT INTO gameplay_inventory_snapshots (
                player_id,
                snapshot_datetime,
                item_type,
                item_name,
                quantity_on_hand,
                source
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "primary",
                "2026-08-25 12:00:00",
                "Consumable",
                "Regular Choco",
                20,
                "TEST_VERIFIED",
            ),
        )

        conn.execute(
            """
            INSERT INTO gameplay_inventory_snapshots (
                player_id,
                snapshot_datetime,
                item_type,
                item_name,
                quantity_on_hand,
                source
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "primary",
                "2026-08-25 12:00:00",
                "Consumable",
                "Premium Choco",
                5,
                "TEST_VERIFIED",
            ),
        )

        conn.execute(
            """
            INSERT INTO inventory_events (
                event_datetime,
                item_type,
                item_name,
                event_type,
                quantity_change
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "2026-08-25 12:10:00",
                "Consumable",
                "Regular Choco",
                "feed",
                -3,
            ),
        )

        conn.execute(
            """
            INSERT INTO inventory_events (
                event_datetime,
                item_type,
                item_name,
                event_type,
                quantity_change
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "2026-08-25 12:15:00",
                "Consumable",
                "Premium Choco",
                "pouch_reward",
                1,
            ),
        )

        conn.commit()

    finally:
        conn.close()

    # --------------------------------------------------------
    # Test 2 — Gameplay DB overrides manual inventory
    # --------------------------------------------------------

    try:
        db_plan = optimize_daily_input(
            daily_input=manual_input,
            asset=None,

            # Do not pass db_path here.
            # That would enable owned-Axie DB enrichment.
            inventory_source="gameplay_db",
            inventory_db_path=temp_path,
            inventory_reserves={
                "Regular Choco": 5,
                "Premium Choco": 1,
            },
        )

        db_recommendation = next(
            recommendation
            for recommendation
            in db_plan["recommendations"]
            if recommendation.get("task")
            == "feed_1_regular_choco"
        )

        db_passed = (
            db_plan[
                "inventory_source"
            ] == "gameplay_db"
            and db_recommendation[
                "quantity_on_hand"
            ] == 17
            and db_recommendation[
                "quantity_reserved"
            ] == 5
            and db_recommendation[
                "quantity_available"
            ] == 12
            and db_plan[
                "inventory_ledger_state"
            ][
                "Regular Choco"
            ][
                "event_delta"
            ] == -3
        )

        print(
            "Gameplay DB inventory:",
            "PASS" if db_passed else "FAIL",
        )
        print(
            "  Source:",
            db_plan[
                "inventory_source"
            ],
        )
        print(
            "  On hand:",
            db_recommendation[
                "quantity_on_hand"
            ],
        )
        print(
            "  Reserved:",
            db_recommendation[
                "quantity_reserved"
            ],
        )
        print(
            "  Available:",
            db_recommendation[
                "quantity_available"
            ],
        )

        if not db_passed:
            all_passed = False

        # ----------------------------------------------------
        # Test 3 — Missing verified snapshot remains blocked
        # ----------------------------------------------------

        conn = sqlite3.connect(
            temp_path
        )

        try:
            conn.execute(
                """
                DELETE FROM gameplay_inventory_snapshots
                WHERE item_name = 'Premium Choco'
                """
            )

            conn.commit()

        finally:
            conn.close()

        missing_snapshot_passed = False

        try:
            optimize_daily_input(
                daily_input=manual_input,
                asset=None,
                inventory_source="gameplay_db",
                inventory_db_path=temp_path,
            )

        except ValueError as exc:
            missing_snapshot_passed = (
                "NO_VERIFIED_SNAPSHOT"
                in str(exc)
            )

            print(
                "Missing snapshot guardrail:",
                (
                    "PASS"
                    if missing_snapshot_passed
                    else "FAIL"
                ),
            )
            print(
                "  Message:",
                str(exc),
            )

        else:
            print(
                "Missing snapshot guardrail: FAIL"
            )

        if not missing_snapshot_passed:
            all_passed = False

        # ----------------------------------------------------
        # Test 4 — Unknown inventory source
        # ----------------------------------------------------

        unknown_source_passed = False

        try:
            resolve_daily_inventory_for_optimization(
                daily_input=manual_input,
                inventory_source=(
                    "completely_unknown_source"
                ),
            )

        except ValueError as exc:
            unknown_source_passed = True

            print(
                "Unknown-source guardrail: PASS"
            )
            print(
                "  Message:",
                str(exc),
            )

        else:
            print(
                "Unknown-source guardrail: FAIL"
            )

        if not unknown_source_passed:
            all_passed = False

    finally:
        if os.path.exists(
            temp_path
        ):
            os.remove(
                temp_path
            )

    print(
        "\nV0.9 Optimizer Inventory Source:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



# ============================================================
# V0.9 — Structured Fortune Slip State
# ============================================================

def normalize_slip_state(
    slip_balance,
    minimum_reserve,
):
    """
    Normalize Fortune Slip state while preserving the
    existing numeric reroll engine.

    Legacy:
        slip_balance=1712
        minimum_reserve=20

    Structured:
        slip_balance={
            "on_hand": 1712,
            "reserved": 20,
        }

    Both produce:
        {
            "on_hand": 1712,
            "reserved": 20,
            "available": 1692,
        }

    'available' is informational here. The reroll engine
    must continue receiving on_hand + minimum_reserve
    separately so the reserve is not counted twice.
    """

    if (
        not isinstance(
            minimum_reserve,
            (int, float),
        )
        or isinstance(
            minimum_reserve,
            bool,
        )
    ):
        raise ValueError(
            "minimum_reserve must be numeric"
        )

    if minimum_reserve < 0:
        raise ValueError(
            "minimum_reserve cannot be negative"
        )

    # --------------------------------------------------------
    # Legacy numeric form
    # --------------------------------------------------------

    if (
        isinstance(
            slip_balance,
            (int, float),
        )
        and not isinstance(
            slip_balance,
            bool,
        )
    ):
        on_hand = slip_balance
        reserved = minimum_reserve

    # --------------------------------------------------------
    # V0.9 structured form
    # --------------------------------------------------------

    elif isinstance(
        slip_balance,
        dict,
    ):
        if "on_hand" not in slip_balance:
            raise ValueError(
                "Structured Fortune Slip state "
                "requires 'on_hand'."
            )

        on_hand = slip_balance[
            "on_hand"
        ]

        reserved = slip_balance.get(
            "reserved",
            minimum_reserve,
        )

        if reserved != minimum_reserve:
            raise ValueError(
                "Structured Fortune Slip reserve must "
                "match minimum_reserve. "
                f"reserved={reserved}, "
                f"minimum_reserve={minimum_reserve}"
            )

    else:
        raise ValueError(
            "slip_balance must be numeric or a "
            "structured Fortune Slip state."
        )

    for field_name, field_value in (
        (
            "on_hand",
            on_hand,
        ),
        (
            "reserved",
            reserved,
        ),
    ):
        if (
            not isinstance(
                field_value,
                (int, float),
            )
            or isinstance(
                field_value,
                bool,
            )
        ):
            raise ValueError(
                "Fortune Slip field must be numeric: "
                f"{field_name}"
            )

        if field_value < 0:
            raise ValueError(
                "Fortune Slip field cannot be negative: "
                f"{field_name}"
            )

    return {
        "on_hand": on_hand,
        "reserved": reserved,
        "available": max(
            0,
            on_hand - reserved,
        ),
    }




def build_projected_slip_state(
    slip_state,
    reroll_plan,
):
    """
    Combine the starting Fortune Slip state with the actual
    reroll plan produced by the existing reroll engine.
    """

    on_hand = slip_state[
        "on_hand"
    ]

    reserved = slip_state[
        "reserved"
    ]

    available = slip_state[
        "available"
    ]

    starting_slips = reroll_plan[
        "starting_slips"
    ]

    ending_slips = reroll_plan[
        "ending_slips"
    ]

    if starting_slips != on_hand:
        raise ValueError(
            "Reroll-plan starting balance does not match "
            "Fortune Slip on_hand state."
        )

    if ending_slips > starting_slips:
        raise ValueError(
            "Reroll-plan ending balance cannot exceed "
            "starting balance."
        )

    planned_spend = (
        starting_slips - ending_slips
    )

    projected_available = max(
        0,
        ending_slips - reserved,
    )

    return {
        "on_hand": on_hand,
        "reserved": reserved,
        "available": available,
        "planned_spend": planned_spend,
        "projected_ending": ending_slips,
        "projected_available": (
            projected_available
        ),
    }


def build_daily_input(
    board_entries,
    inventory,
    slip_balance,
    reroll_numbers,
    strategy_mode,
    minimum_reserve,
    current_rank=None,
    current_weekly_bp=None,
    days_remaining=None,
):
    strategy_context = build_strategy_context(
        strategy_mode=strategy_mode,
        minimum_reserve=minimum_reserve,
        current_rank=current_rank,
        current_weekly_bp=current_weekly_bp,
        days_remaining=days_remaining,
    )

    slip_state = normalize_slip_state(
        slip_balance=slip_balance,
        minimum_reserve=minimum_reserve,
    )

    return {
        "board_entries": board_entries,
        "inventory": normalize_inventory(
            inventory
        ),

        # Keep numeric balance for the existing reroll engine.
        "slip_balance": slip_state[
            "on_hand"
        ],

        # V0.9 structured state for reporting/accounting.
        "slip_state": slip_state,

        "reroll_numbers": reroll_numbers,
        "strategy_context": strategy_context,
    }



def run_v09_structured_slip_state_test():
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 STRUCTURED FORTUNE SLIP STATE TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    # --------------------------------------------------------
    # Test 1 — Legacy numeric input
    # --------------------------------------------------------

    legacy_input = build_daily_input(
        board_entries=[],
        inventory={},
        slip_balance=1712,
        reroll_numbers={},
        strategy_mode="Conserve",
        minimum_reserve=20,
    )

    legacy_expected = {
        "on_hand": 1712,
        "reserved": 20,
        "available": 1692,
    }

    legacy_passed = (
        legacy_input[
            "slip_state"
        ] == legacy_expected
        and legacy_input[
            "slip_balance"
        ] == 1712
    )

    print(
        "Legacy numeric Slip input:",
        "PASS" if legacy_passed else "FAIL",
    )
    print(
        "  State:",
        legacy_input[
            "slip_state"
        ],
    )
    print(
        "  Engine balance:",
        legacy_input[
            "slip_balance"
        ],
    )

    if not legacy_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 2 — Structured input
    # --------------------------------------------------------

    structured_input = build_daily_input(
        board_entries=[],
        inventory={},
        slip_balance={
            "on_hand": 1712,
            "reserved": 20,
        },
        reroll_numbers={},
        strategy_mode="Conserve",
        minimum_reserve=20,
    )

    structured_passed = (
        structured_input[
            "slip_state"
        ] == legacy_expected
        and structured_input[
            "slip_balance"
        ] == 1712
    )

    print(
        "Structured Slip input:",
        (
            "PASS"
            if structured_passed
            else "FAIL"
        ),
    )
    print(
        "  State:",
        structured_input[
            "slip_state"
        ],
    )
    print(
        "  Engine balance:",
        structured_input[
            "slip_balance"
        ],
    )

    if not structured_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 3 — Balance below reserve
    # --------------------------------------------------------

    below_reserve = normalize_slip_state(
        slip_balance={
            "on_hand": 15,
            "reserved": 20,
        },
        minimum_reserve=20,
    )

    below_reserve_passed = (
        below_reserve == {
            "on_hand": 15,
            "reserved": 20,
            "available": 0,
        }
    )

    print(
        "Below-reserve state:",
        (
            "PASS"
            if below_reserve_passed
            else "FAIL"
        ),
    )
    print(
        "  State:",
        below_reserve,
    )

    if not below_reserve_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 4 — Conflicting reserve guardrail
    # --------------------------------------------------------

    conflict_passed = False

    try:
        normalize_slip_state(
            slip_balance={
                "on_hand": 1712,
                "reserved": 25,
            },
            minimum_reserve=20,
        )

    except ValueError as exc:
        conflict_passed = True

        print(
            "Conflicting reserve guardrail: PASS"
        )
        print(
            "  Message:",
            str(exc),
        )

    else:
        print(
            "Conflicting reserve guardrail: FAIL"
        )

    if not conflict_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 5 — Existing validation remains compatible
    # --------------------------------------------------------

    try:
        validate_daily_input(
            legacy_input
        )

        validate_daily_input(
            structured_input
        )

    except Exception as exc:
        validation_passed = False

        print(
            "Daily-input validation: FAIL"
        )
        print(
            "  Error:",
            str(exc),
        )

    else:
        validation_passed = True

        print(
            "Daily-input validation: PASS"
        )

    if not validation_passed:
        all_passed = False

    print(
        "\nV0.9 Structured Fortune Slip State:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



def run_v09_projected_slip_state_test():
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 PROJECTED FORTUNE SLIP STATE TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    # --------------------------------------------------------
    # One guaranteed reroll:
    # Craft any Rune is below the 100 BP KEEP threshold.
    # Reroll #1 costs 10 slips.
    # --------------------------------------------------------

    daily_input = build_daily_input(
        board_entries=[
            "Craft any Rune",
        ],
        inventory={},
        slip_balance={
            "on_hand": 100,
            "reserved": 20,
        },
        reroll_numbers={
            "craft_any_rune": 1,
        },
        strategy_mode="Conserve",
        minimum_reserve=20,
    )

    execution_plan = optimize_daily_input(
        daily_input=daily_input,
        asset=None,
    )

    slip_state = execution_plan[
        "slip_state"
    ]

    reroll_results = execution_plan[
        "reroll_results"
    ]

    # --------------------------------------------------------
    # Test 1 — Starting state
    # --------------------------------------------------------

    starting_passed = (
        slip_state[
            "on_hand"
        ] == 100
        and slip_state[
            "reserved"
        ] == 20
        and slip_state[
            "available"
        ] == 80
    )

    print(
        "Starting Slip state:",
        "PASS" if starting_passed else "FAIL",
    )
    print(
        "  On hand:",
        slip_state[
            "on_hand"
        ],
    )
    print(
        "  Reserved:",
        slip_state[
            "reserved"
        ],
    )
    print(
        "  Available:",
        slip_state[
            "available"
        ],
    )

    if not starting_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 2 — Real reroll happened
    # --------------------------------------------------------

    reroll_passed = (
        len(reroll_results) == 1
        and reroll_results[0][
            "reroll_status"
        ] == "ALLOWED"
        and reroll_results[0][
            "slip_cost"
        ] == 10
    )

    print(
        "Real reroll plan:",
        "PASS" if reroll_passed else "FAIL",
    )

    if reroll_results:
        print(
            "  Status:",
            reroll_results[0][
                "reroll_status"
            ],
        )
        print(
            "  Slip cost:",
            reroll_results[0][
                "slip_cost"
            ],
        )

    if not reroll_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 3 — Planned spend derived from reroll plan
    # --------------------------------------------------------

    spend_passed = (
        slip_state[
            "planned_spend"
        ] == 10
    )

    print(
        "Planned Slip spend:",
        "PASS" if spend_passed else "FAIL",
    )
    print(
        "  Planned spend:",
        slip_state[
            "planned_spend"
        ],
    )

    if not spend_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 4 — Projected ending
    # --------------------------------------------------------

    ending_passed = (
        slip_state[
            "projected_ending"
        ] == 90
        and slip_state[
            "projected_available"
        ] == 70
    )

    print(
        "Projected Slip state:",
        "PASS" if ending_passed else "FAIL",
    )
    print(
        "  Projected ending:",
        slip_state[
            "projected_ending"
        ],
    )
    print(
        "  Projected available:",
        slip_state[
            "projected_available"
        ],
    )

    if not ending_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 5 — Legacy fields remain intact
    # --------------------------------------------------------

    compatibility_passed = (
        execution_plan[
            "starting_slips"
        ] == 100
        and execution_plan[
            "ending_slips"
        ] == 90
    )

    print(
        "Legacy Slip fields preserved:",
        (
            "PASS"
            if compatibility_passed
            else "FAIL"
        ),
    )
    print(
        "  starting_slips:",
        execution_plan[
            "starting_slips"
        ],
    )
    print(
        "  ending_slips:",
        execution_plan[
            "ending_slips"
        ],
    )

    if not compatibility_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 6 — No-reroll plan spends zero
    # --------------------------------------------------------

    no_reroll_input = build_daily_input(
        board_entries=[
            "Buy any Axie",
        ],
        inventory={},
        slip_balance={
            "on_hand": 100,
            "reserved": 20,
        },
        reroll_numbers={},
        strategy_mode="Conserve",
        minimum_reserve=20,
    )

    no_reroll_plan = optimize_daily_input(
        daily_input=no_reroll_input,
        asset=None,
    )

    no_reroll_state = no_reroll_plan[
        "slip_state"
    ]

    no_reroll_passed = (
        no_reroll_state[
            "planned_spend"
        ] == 0
        and no_reroll_state[
            "projected_ending"
        ] == 100
        and no_reroll_state[
            "projected_available"
        ] == 80
    )

    print(
        "No-reroll Slip state:",
        (
            "PASS"
            if no_reroll_passed
            else "FAIL"
        ),
    )

    if not no_reroll_passed:
        all_passed = False

    print(
        "\nV0.9 Projected Fortune Slip State:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed




def validate_daily_input(
    daily_input,
):
    board_entries = daily_input[
        "board_entries"
    ]

    task_ids = set()

    for entry in board_entries:
        resolution = (
            resolve_bounty_task_definition(
                entry
            )
        )

        catalog_id = resolution[
            "catalog_id"
        ]

        parameters = dict(
            resolution.get(
                "parameters",
                {},
            )
        )

        if catalog_id not in BOUNTY_TASK_CATALOG:
            raise ValueError(
                f"Unknown catalog_id: {catalog_id}"
            )

        task_id = resolve_task_id(
            entry,
            catalog_id,
        )

        if task_id in task_ids:
            raise ValueError(
                f"Duplicate task_id: {task_id}"
            )

        task_ids.add(
            task_id
        )

        # Instantiate here so validation sees the same
        # canonical task state that build_daily_board()
        # will later use.
        task = instantiate_task(
            BOUNTY_TASK_CATALOG[
                catalog_id
            ],
            **parameters,
        )

        # Axie-target tasks must not reach production
        # with unresolved parameter placeholders.
        if task.get("target") == "axie":
            build_axie_qualification_criteria_from_task(
                task
            )

    minimum_reserve = daily_input[
        "strategy_context"
    ][
        "minimum_reserve"
    ]

    slip_state = normalize_slip_state(
        slip_balance=daily_input.get(
            "slip_state",
            daily_input["slip_balance"],
        ),
        minimum_reserve=minimum_reserve,
    )

    if (
        daily_input["slip_balance"]
        != slip_state["on_hand"]
    ):
        raise ValueError(
            "slip_balance does not match "
            "Fortune Slip on_hand state."
        )
    inventory = daily_input[
        "inventory"
    ]

    # normalize_inventory() is intentionally called again
    # here so validation also works when validate_daily_input()
    # receives a manually constructed daily_input.
    normalize_inventory(
        inventory
    )

    reroll_numbers = daily_input[
        "reroll_numbers"
    ]

    for task_id, reroll_number in (
        reroll_numbers.items()
    ):
        if task_id not in task_ids:
            raise ValueError(
                "Unknown reroll task_id: "
                f"{task_id}"
            )

        if reroll_number not in REROLL_TIERS:
            raise ValueError(
                "Invalid reroll number: "
                f"{reroll_number}"
            )

    return True



def run_v09_structured_inventory_test():
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 STRUCTURED INVENTORY TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    # --------------------------------------------------------
    # Test 1 — Legacy flat inventory remains supported
    # --------------------------------------------------------

    legacy = normalize_inventory(
        {
            "Regular Choco": 10,
            "Premium Choco": 1,
        }
    )

    legacy_expected = {
        "regular_choco": {
            "on_hand": 10,
            "reserved": 0,
            "available": 10,
        },
        "premium_choco": {
            "on_hand": 1,
            "reserved": 0,
            "available": 1,
        },
    }

    legacy_passed = (
        legacy == legacy_expected
    )

    print(
        "Legacy flat inventory:",
        "PASS" if legacy_passed else "FAIL",
    )
    print(
        "  Actual:",
        legacy,
    )

    if not legacy_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 2 — Structured inventory
    # --------------------------------------------------------

    structured = normalize_inventory(
        {
            "Regular Choco": {
                "on_hand": 10,
                "reserved": 5,
            },
            "Premium Choco": {
                "on_hand": 2,
                "reserved": 1,
            },
        }
    )

    structured_passed = (
        structured[
            "regular_choco"
        ] == {
            "on_hand": 10,
            "reserved": 5,
            "available": 5,
        }
        and structured[
            "premium_choco"
        ] == {
            "on_hand": 2,
            "reserved": 1,
            "available": 1,
        }
    )

    print(
        "Structured inventory:",
        (
            "PASS"
            if structured_passed
            else "FAIL"
        ),
    )
    print(
        "  Regular:",
        structured[
            "regular_choco"
        ],
    )
    print(
        "  Premium:",
        structured[
            "premium_choco"
        ],
    )

    if not structured_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 3 — Reserve-constrained availability
    # --------------------------------------------------------

    availability = (
        check_resource_availability(
            resource="regular_choco",
            quantity_needed=6,
            inventory=structured,
        )
    )

    reserve_passed = (
        availability[
            "quantity_on_hand"
        ] == 10
        and availability[
            "quantity_reserved"
        ] == 5
        and availability[
            "quantity_available"
        ] == 5
        and not availability[
            "can_execute"
        ]
        and availability[
            "shortfall"
        ] == 1
        and availability[
            "reserve_constrained"
        ]
    )

    print(
        "Reserve constraint:",
        "PASS" if reserve_passed else "FAIL",
    )
    print(
        "  Availability:",
        availability,
    )

    if not reserve_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 4 — Physically insufficient inventory
    # --------------------------------------------------------

    physical_shortage = (
        check_resource_availability(
            resource="premium_choco",
            quantity_needed=3,
            inventory=structured,
        )
    )

    physical_passed = (
        physical_shortage[
            "quantity_on_hand"
        ] == 2
        and physical_shortage[
            "quantity_available"
        ] == 1
        and not physical_shortage[
            "can_execute"
        ]
        and not physical_shortage[
            "reserve_constrained"
        ]
    )

    print(
        "Physical shortage:",
        (
            "PASS"
            if physical_passed
            else "FAIL"
        ),
    )

    if not physical_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 5 — Reserved cannot exceed on-hand
    # --------------------------------------------------------

    reserve_guardrail_passed = False

    try:
        normalize_inventory(
            {
                "Regular Choco": {
                    "on_hand": 5,
                    "reserved": 6,
                },
            }
        )

    except ValueError as exc:
        reserve_guardrail_passed = True

        print(
            "Reserve > on-hand guardrail: PASS"
        )
        print(
            "  Message:",
            str(exc),
        )

    else:
        print(
            "Reserve > on-hand guardrail: FAIL"
        )

    if not reserve_guardrail_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 6 — Old production input still builds
    # --------------------------------------------------------

    legacy_daily_input = build_daily_input(
        board_entries=DAILY_BOARD_ENTRIES,
        inventory=DAILY_INVENTORY,
        slip_balance=DAILY_SLIP_BALANCE,
        reroll_numbers=DAILY_REROLL_NUMBERS,
        strategy_mode=DAILY_STRATEGY_MODE,
        minimum_reserve=(
            DAILY_MINIMUM_RESERVE
        ),
    )

    try:
        validate_daily_input(
            legacy_daily_input
        )

    except Exception as exc:
        production_passed = False

        print(
            "Legacy production input: FAIL"
        )
        print(
            "  Error:",
            str(exc),
        )

    else:
        production_passed = True

        print(
            "Legacy production input: PASS"
        )

    if not production_passed:
        all_passed = False

    print(
        "\nV0.9 Structured Inventory:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



def run_v09_daily_input_validation_test():
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 DAILY INPUT VALIDATION TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    # --------------------------------------------------------
    # Test 1 — Existing production-style daily input
    # --------------------------------------------------------

    legacy_input = build_daily_input(
        board_entries=DAILY_BOARD_ENTRIES,
        inventory=DAILY_INVENTORY,
        slip_balance=DAILY_SLIP_BALANCE,
        reroll_numbers=DAILY_REROLL_NUMBERS,
        strategy_mode=DAILY_STRATEGY_MODE,
        minimum_reserve=(
            DAILY_MINIMUM_RESERVE
        ),
    )

    try:
        validate_daily_input(
            legacy_input
        )

    except Exception as exc:
        legacy_passed = False

        print(
            "Existing daily input: FAIL"
        )
        print(
            "  Error:",
            str(exc),
        )

    else:
        legacy_passed = True

        print(
            "Existing daily input: PASS"
        )

    if not legacy_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 2 — Parameterized human-readable tasks
    # --------------------------------------------------------

    parameterized_input = build_daily_input(
        board_entries=[
            (
                "Buy any Bird Axie "
                "with Scaly Spear"
            ),
            (
                "Feed 1 Premium Choco to any "
                "Shiny Axie you own"
            ),
            (
                "Feed 5 Regular Choco to any "
                "Level 20 or higher Axie you own"
            ),
            "Release any Dawn Axie",
        ],
        inventory={
            "Regular Choco": 10,
            "Premium Choco": 2,
        },
        slip_balance=1000,
        reroll_numbers={},
        strategy_mode="Conserve",
        minimum_reserve=20,
    )

    try:
        validate_daily_input(
            parameterized_input
        )

    except Exception as exc:
        parameterized_passed = False

        print(
            "Parameterized daily input: FAIL"
        )
        print(
            "  Error:",
            str(exc),
        )

    else:
        parameterized_passed = True

        print(
            "Parameterized daily input: PASS"
        )

    if not parameterized_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 3 — Unknown task must remain blocked
    # --------------------------------------------------------

    unknown_input = build_daily_input(
        board_entries=[
            "Completely Unknown Bounty",
        ],
        inventory={},
        slip_balance=1000,
        reroll_numbers={},
        strategy_mode="Conserve",
        minimum_reserve=20,
    )

    unknown_guardrail_passed = False

    try:
        validate_daily_input(
            unknown_input
        )

    except ValueError as exc:
        unknown_guardrail_passed = True

        print(
            "Unknown-task guardrail: PASS"
        )
        print(
            "  Message:",
            str(exc),
        )

    else:
        print(
            "Unknown-task guardrail: FAIL"
        )

    if not unknown_guardrail_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 4 — Missing parameter must remain blocked
    # --------------------------------------------------------

    incomplete_input = build_daily_input(
        board_entries=[
            {
                "catalog_id": (
                    "app_axie_buy_class_with_part"
                ),
                "task_id": (
                    "incomplete_class_part"
                ),
                "random_class": "Bird",
            },
        ],
        inventory={},
        slip_balance=1000,
        reroll_numbers={},
        strategy_mode="Conserve",
        minimum_reserve=20,
    )

    missing_parameter_passed = False

    try:
        validate_daily_input(
            incomplete_input
        )

    except ValueError as exc:
        missing_parameter_passed = True

        print(
            "Missing-parameter guardrail: PASS"
        )
        print(
            "  Message:",
            str(exc),
        )

    else:
        print(
            "Missing-parameter guardrail: FAIL"
        )

    if not missing_parameter_passed:
        all_passed = False

    print(
        "\nV0.9 Daily Input Validation:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



def run_v09_reserve_aware_optimizer_test():
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 RESERVE-AWARE OPTIMIZER TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    daily_input = build_daily_input(
        board_entries=[
            (
                "Feed 10 Regular Choco "
                "to any Axie"
            ),
        ],
        inventory={
            "Regular Choco": {
                "on_hand": 15,
                "reserved": 10,
            },
        },
        slip_balance=1000,
        reroll_numbers={},
        strategy_mode="Conserve",
        minimum_reserve=20,
    )

    execution_plan = optimize_daily_input(
        daily_input=daily_input,
        asset=None,
    )

    recommendations = execution_plan[
        "recommendations"
    ]

    recommendation = next(
        item
        for item in recommendations
        if item.get("task")
        == "feed_10_choco_any_axie"
    )

    # --------------------------------------------------------
    # Test 1 — Physical inventory is preserved
    # --------------------------------------------------------

    on_hand_passed = (
        recommendation[
            "quantity_on_hand"
        ] == 15
    )

    print(
        "On-hand inventory:",
        "PASS" if on_hand_passed else "FAIL",
    )
    print(
        "  On hand:",
        recommendation[
            "quantity_on_hand"
        ],
    )

    if not on_hand_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 2 — Reserve is preserved
    # --------------------------------------------------------

    reserve_passed = (
        recommendation[
            "quantity_reserved"
        ] == 10
    )

    print(
        "Protected reserve:",
        "PASS" if reserve_passed else "FAIL",
    )
    print(
        "  Reserved:",
        recommendation[
            "quantity_reserved"
        ],
    )

    if not reserve_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 3 — Only spendable inventory is considered
    # --------------------------------------------------------

    spendable_passed = (
        recommendation[
            "quantity_available"
        ] == 5
    )

    print(
        "Spendable inventory:",
        (
            "PASS"
            if spendable_passed
            else "FAIL"
        ),
    )
    print(
        "  Spendable:",
        recommendation[
            "quantity_available"
        ],
    )

    if not spendable_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 4 — Task is blocked by reserve, not ownership
    # --------------------------------------------------------

    constraint_passed = (
        recommendation[
            "inventory_status"
        ] == "SHORTFALL"
        and recommendation[
            "shortfall"
        ] == 5
        and recommendation[
            "reserve_constrained"
        ]
    )

    print(
        "Reserve-constrained execution:",
        (
            "PASS"
            if constraint_passed
            else "FAIL"
        ),
    )
    print(
        "  Inventory status:",
        recommendation[
            "inventory_status"
        ],
    )
    print(
        "  Spendable shortfall:",
        recommendation[
            "shortfall"
        ],
    )
    print(
        "  Reserve constrained:",
        recommendation[
            "reserve_constrained"
        ],
    )

    if not constraint_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 5 — Formatter explains the reserve
    # --------------------------------------------------------

    formatted_lines = (
        format_execution_plan(
            execution_plan
        )
    )

    reserve_output_passed = any(
        (
            "On hand: 15" in line
            and "Reserved: 10" in line
            and "Spendable: 5" in line
            and "RESERVE PROTECTED" in line
        )
        for line in formatted_lines
    )

    print(
        "Reserve visible in output:",
        (
            "PASS"
            if reserve_output_passed
            else "FAIL"
        ),
    )

    print(
        "\nFormatted actions:"
    )

    for line in formatted_lines:
        print(
            " ",
            line,
        )

    if not reserve_output_passed:
        all_passed = False

    print(
        "\nV0.9 Reserve-Aware Optimizer:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



def prepare_daily_board_for_optimization(
    daily_input,
    db_path=None,
    as_of_datetime=None,
):
    """
    Validate and build the canonical daily Bounty board.

    When db_path is supplied, enrich applicable Axie-target
    tasks with exact live owned-Axie qualification results.

    Existing V1 optimizer behavior remains available when
    db_path is None.
    """

    validate_daily_input(
        daily_input
    )

    board = build_daily_board(
        daily_input["board_entries"]
    )

    if db_path is not None:
        board = (
            enrich_board_with_owned_axie_candidates(
                db_path=db_path,
                task_map=board,
                as_of_datetime=as_of_datetime,
            )
        )

    return board



def optimize_daily_input(
    daily_input,
    asset,
    db_path=None,
    as_of_datetime=None,
    inventory_source="manual",
    inventory_db_path=None,
    inventory_reserves=None,
    player_id="primary",
    economics_inputs=None,
):
    board = (
        prepare_daily_board_for_optimization(
            daily_input=daily_input,
            db_path=db_path,
            as_of_datetime=as_of_datetime,
        )
    )

    inventory_resolution = (
        resolve_daily_inventory_for_optimization(
            daily_input=daily_input,
            inventory_source=inventory_source,
            inventory_db_path=(
                inventory_db_path
            ),
            inventory_reserves=(
                inventory_reserves
            ),
            player_id=player_id,
        )
    )

    analysis = analyze_task_board(
        board,
        asset,
    )

    execution_plan = build_execution_plan(
        analysis=analysis,
        task_map=board,
        inventory=inventory_resolution[
            "inventory"
        ],
        reroll_numbers=daily_input[
            "reroll_numbers"
        ],
        slip_balance=daily_input[
            "slip_balance"
        ],
        strategy_context=daily_input[
            "strategy_context"
        ],
        slip_state=daily_input.get(
            "slip_state"
        ),
        economics_inputs=(
            economics_inputs
        ),
    )

    # V0.9 inventory provenance.
    execution_plan[
        "inventory_source"
    ] = inventory_resolution[
        "source"
    ]

    execution_plan[
        "inventory_ledger_state"
    ] = inventory_resolution[
        "ledger_state"
    ]

    return execution_plan



def run_v09_optimizer_axie_integration_test(
    db_path,
):
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 OPTIMIZER AXIE INTEGRATION TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    daily_input = build_daily_input(
        board_entries=[
            "Feed 10 Regular Choco to any Axie",
            (
                "Feed 1 Premium Choco to any "
                "Shiny Axie you own"
            ),
            (
                "Feed 5 Regular Choco to any "
                "Level 20 or higher Axie you own"
            ),
            "Release any Dawn Axie",
            "Buy any Bug Axie",
            "Open 1 Premium Pouch",
        ],
        inventory={
            "Regular Choco": 20,
            "Premium Choco": 2,
        },
        slip_balance=1000,
        reroll_numbers={},
        strategy_mode="Conserve",
        minimum_reserve=20,
    )

    # --------------------------------------------------------
    # Test 1 — Prepare the board through the same function
    # now used by optimize_daily_input()
    # --------------------------------------------------------

    board = (
        prepare_daily_board_for_optimization(
            daily_input=daily_input,
            db_path=db_path,
        )
    )

    board_passed = (
        len(board) == 6
    )

    print(
        "Prepared daily board:",
        "PASS" if board_passed else "FAIL",
    )
    print(
        "  Tasks:",
        len(board),
    )

    if not board_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 2 — unrestricted feed is enriched
    # --------------------------------------------------------

    any_feed = board[
        "feed_10_choco_any_axie"
    ]

    any_feed_passed = (
        any_feed[
            "owned_axie_candidate_applicable"
        ]
        and any_feed[
            "eligible_owned_axie_count"
        ] == any_feed[
            "eligible_owned_axie_count"
        ]
        and any_feed[
            "eligible_owned_axie_count"
        ] > 0
    )

    print(
        "Owned-Axie enrichment active:",
        (
            "PASS"
            if any_feed_passed
            else "FAIL"
        ),
    )
    print(
        "  Eligible:",
        any_feed[
            "eligible_owned_axie_count"
        ],
    )

    if not any_feed_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 3 — Shiny requirement reaches live DB
    # --------------------------------------------------------

    shiny = board[
        "feed_premium_collection"
    ]

    shiny_passed = (
        shiny[
            "owned_axie_candidate_applicable"
        ]
        and shiny[
            "axie_qualification_criteria"
        ] == {
            "required_collections": [
                "SHINY",
            ],
        }
        and shiny[
            "eligible_owned_axie_count"
        ] > 0
    )

    print(
        "Shiny live qualification:",
        "PASS" if shiny_passed else "FAIL",
    )
    print(
        "  Eligible IDs:",
        shiny[
            "eligible_owned_axie_ids"
        ],
    )

    if not shiny_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 4 — buy guardrail survives optimizer preparation
    # --------------------------------------------------------

    buy_bug = board[
        "buy_random_class_axie"
    ]

    buy_passed = (
        not buy_bug[
            "owned_axie_candidate_applicable"
        ]
        and buy_bug[
            "owned_axie_candidate_reason"
        ] == (
            "ACTION_DOES_NOT_USE_CURRENT_OWNED_AXIE"
        )
    )

    print(
        "Buy-task guardrail preserved:",
        "PASS" if buy_passed else "FAIL",
    )

    if not buy_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 5 — Actual optimizer can execute enriched board
    # --------------------------------------------------------

    try:
        execution_plan = optimize_daily_input(
            daily_input=daily_input,
            asset=None,
            db_path=db_path,
        )

    except Exception as exc:
        optimizer_passed = False

        print(
            "Optimizer with live Axie data: FAIL"
        )
        print(
            "  Error:",
            str(exc),
        )

    else:
        optimizer_passed = (
            execution_plan is not None
        )

        print(
            "Optimizer with live Axie data:",
            (
                "PASS"
                if optimizer_passed
                else "FAIL"
            ),
        )

    if not optimizer_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 6 — Legacy optimizer mode still works
    # --------------------------------------------------------

    try:
        legacy_plan = optimize_daily_input(
            daily_input=daily_input,
            asset=None,
        )

    except Exception as exc:
        legacy_passed = False

        print(
            "Legacy no-DB optimizer mode: FAIL"
        )
        print(
            "  Error:",
            str(exc),
        )

    else:
        legacy_passed = (
            legacy_plan is not None
        )

        print(
            "Legacy no-DB optimizer mode:",
            "PASS" if legacy_passed else "FAIL",
        )

    if not legacy_passed:
        all_passed = False

    print(
        "\nV0.9 Optimizer Axie Integration:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



def build_v1_demo_plan():
    
    demo_asset = {
        "class": "mech",
        "collectible": True,
        "evolved": True,
    }

    demo_board_entries = [
        {
            "task_id": "feed_10_choco_mech",
            "catalog_id": (
                "app_axie_feed_10_choco_random_class"
            ),
            "random_class": "mech",
        },
        {
            "task_id": "buy_mech_axie",
            "catalog_id": (
                "app_axie_buy_random_class_axie"
            ),
            "random_class": "mech",
        },
        {
            "task_id": "feed_10_choco_any",
            "catalog_id": (
                "app_axie_feed_10_choco_any_axie"
            ),
        },
        {
            "task_id": "feed_premium_collectible",
            "catalog_id": (
                "app_axie_feed_premium_collectible"
            ),
        },
        {
            "task_id": "feed_premium_evolved",
            "catalog_id": (
                "app_axie_feed_premium_evolved"
            ),
        },
        {
            "task_id": "origins_battle",
            "catalog_id": (
                "origins_win_vs_3_beast_bird_mech"
            ),
        },
    ]


    demo_input = build_daily_input(
        board_entries=demo_board_entries,
        inventory={
            "regular_choco": 10,
            "premium_choco": 1,
        },
        slip_balance=100,
        reroll_numbers={},
        strategy_mode="conserve",
        minimum_reserve=20,
    )

    
    return optimize_daily_input(
        daily_input=demo_input,
        asset=demo_asset,
    )


def run_daily_optimizer(
    daily_input,
    asset,
    title="AXIEOS DAILY BOUNTY PLAN",
    db_path=None,
    as_of_datetime=None,
    inventory_source="manual",
    inventory_db_path=None,
    inventory_reserves=None,
    player_id="primary",
    economics_inputs=None,
):
    execution_plan = optimize_daily_input(
        daily_input=daily_input,
        asset=asset,
        db_path=db_path,
        as_of_datetime=as_of_datetime,
        inventory_source=inventory_source,
        inventory_db_path=inventory_db_path,
        inventory_reserves=inventory_reserves,
        player_id=player_id,
        economics_inputs=(
            economics_inputs
        ),
    )

    print(f"\n{title}")

    for line in format_execution_summary(
        execution_plan
    ):
        print(line)

    print("\nActions:")

    for line in format_execution_plan(
        execution_plan
    ):
        print(line)

    readiness = evaluate_v1_readiness(
        execution_plan
    )

    print(
        "\nPlan Status:",
        readiness["v1_status"],
    )

    return execution_plan


def run_v1_demo():
    execution_plan = build_v1_demo_plan()

    print("\nAXIEOS BOUNTY OPTIMIZER V1")

    for line in format_execution_summary(
        execution_plan
    ):
        print(line)

    print("\nActions:")

    for line in format_execution_plan(
        execution_plan
    ):
        print(line)

    readiness = evaluate_v1_readiness(
        execution_plan
    )

    print(
        "\nV1 Status:",
        readiness["v1_status"],
    )

def run_daily_input_validation_test():
    bad_input = build_daily_input(
        board_entries=[
            {
                "task_id": "duplicate_task",
                "catalog_id": "app_axie_buy_any_axie",
            },
            {
                "task_id": "duplicate_task",
                "catalog_id": "app_axie_feed_10_choco_any_axie",
            },
        ],
        inventory={},
        slip_balance=100,
        reroll_numbers={},
        strategy_mode="conserve",
        minimum_reserve=20,
    )

    print("\nDAILY INPUT VALIDATION TEST")

    try:
        validate_daily_input(
            bad_input
        )
    except ValueError as error:
        print(error)

    unknown_catalog_input = build_daily_input(
        board_entries=[
            {
                "task_id": "unknown_task",
                "catalog_id": "not_a_real_catalog_id",
            },
        ],
        inventory={},
        slip_balance=100,
        reroll_numbers={},
        strategy_mode="conserve",
        minimum_reserve=20,
    )

    print("\nUNKNOWN CATALOG VALIDATION TEST")

    try:
        validate_daily_input(
            unknown_catalog_input
        )
    except ValueError as error:
        print(error)


    negative_slip_input = build_daily_input(
        board_entries=[
            {
                "task_id": "buy_any_axie",
                "catalog_id": "app_axie_buy_any_axie",
            },
        ],
        inventory={},
        slip_balance=-10,
        reroll_numbers={},
        strategy_mode="conserve",
        minimum_reserve=20,
    )

    print("\nNEGATIVE SLIP VALIDATION TEST")

    try:
        validate_daily_input(
            negative_slip_input
        )
    except ValueError as error:
        print(error)


    bad_reroll_input = build_daily_input(
        board_entries=[
            {
                "task_id": "buy_any_axie",
                "catalog_id": "app_axie_buy_any_axie",
            },
        ],
        inventory={},
        slip_balance=100,
        reroll_numbers={
            "buy_any_axie": 11,
        },
        strategy_mode="conserve",
        minimum_reserve=20,
    )

    print("\nREROLL NUMBER VALIDATION TEST")

    try:
        validate_daily_input(
            bad_reroll_input
        )
    except ValueError as error:
        print(error)


    negative_inventory_input = build_daily_input(
        board_entries=[
            {
                "task_id": "buy_any_axie",
                "catalog_id": "app_axie_buy_any_axie",
            },
        ],
        inventory={
            "regular_choco": -1,
        },
        slip_balance=100,
        reroll_numbers={},
        strategy_mode="conserve",
        minimum_reserve=20,
    )

    print("\nNEGATIVE INVENTORY VALIDATION TEST")

    try:
        validate_daily_input(
            negative_inventory_input
        )
    except ValueError as error:
        print(error)


    print("\nNEGATIVE RESERVE VALIDATION TEST")

    try:
        build_daily_input(
            board_entries=[
                {
                    "task_id": "buy_any_axie",
                    "catalog_id": "app_axie_buy_any_axie",
                },
            ],
            inventory={},
            slip_balance=100,
            reroll_numbers={},
            strategy_mode="conserve",
            minimum_reserve=-10,
        )
    except ValueError as error:
        print(error)


def run_live_runner_test():
    live_board_entries = [
        {
            "task_id": "feed_10_choco_mech",
            "catalog_id": (
                "app_axie_feed_10_choco_random_class"
            ),
            "random_class": "mech",
        },
        {
            "task_id": "buy_mech_axie",
            "catalog_id": (
                "app_axie_buy_random_class_axie"
            ),
            "random_class": "mech",
        },
        {
            "task_id": "feed_10_choco_any",
            "catalog_id": (
                "app_axie_feed_10_choco_any_axie"
            ),
        },
        {
            "task_id": "feed_premium_collectible",
            "catalog_id": (
                "app_axie_feed_premium_collectible"
            ),
        },
        {
            "task_id": "feed_premium_evolved",
            "catalog_id": (
                "app_axie_feed_premium_evolved"
            ),
        },
        {
            "task_id": "origins_battle",
            "catalog_id": (
                "origins_win_vs_3_beast_bird_mech"
            ),
        },
    ]

    live_input = build_daily_input(
        board_entries=live_board_entries,
        inventory={
            "regular_choco": 10,
            "premium_choco": 1,
        },
        slip_balance=100,
        reroll_numbers={},
        strategy_mode="conserve",
        minimum_reserve=20,
    )

    live_asset = {
        "class": "mech",
        "collectible": True,
        "evolved": True,
    }

    run_daily_optimizer(
        daily_input=live_input,
        asset=live_asset,
        title="LIVE RUNNER TEST",
    )


def reconcile_daily_bp(
    execution_plan,
    observed_total_bp,
):
    task_bp = execution_plan[
        "total_bp"
    ]

    additional_bp = (
        observed_total_bp - task_bp
    )

    return {
        "task_bp": task_bp,
        "observed_total_bp": observed_total_bp,
        "additional_bp": additional_bp,
        "matches_task_bp_only": (
            task_bp == observed_total_bp
        ),
    }


def summarize_reroll_history(
    reroll_history,
):
    total_slips_spent = 0
    slot_results = {}

    for slot_id, history in reroll_history.items():
        slot_slips = 0

        for reroll_number in history[
            "rerolls_used"
        ]:
            slot_slips += REROLL_TIERS[
                reroll_number
            ]["cost"]

        total_slips_spent += slot_slips

        slot_results[slot_id] = {
            "rerolls_used": history[
                "rerolls_used"
            ],
            "slips_spent": slot_slips,
            "starting_task": history[
                "starting_task"
            ],
            "final_task": history[
                "final_task"
            ],
        }

    return {
        "slots": slot_results,
        "total_slips_spent": total_slips_spent,
    }


def summarize_other_slip_spend(
    slip_spend,
):
    total_slips_spent = 0

    for item in slip_spend.values():
        total_slips_spent += item[
            "slips_spent"
        ]

    return {
        "items": slip_spend,
        "total_slips_spent": total_slips_spent,
    }


def build_daily_data_quality_summary(
    bp_reconciliation,
    slip_matches,
):
    issues = []

    if not bp_reconciliation[
        "matches_task_bp_only"
    ]:
        issues.append(
            "BP includes additional or unattributed BP"
        )

    if not slip_matches:
        issues.append(
            "Fortune Slip accounting does not reconcile"
        )

    return {
        "issue_count": len(issues),
        "issues": issues,
        "status": (
            "CLEAN"
            if not issues
            else "REVIEW"
        ),
    }



def format_daily_operational_summary(
    execution_plan,
    bp_reconciliation,
    reroll_history_summary,
    other_slip_summary,
    starting_slips,
    ending_slips,
    data_quality,
):
    total_reroll_slips = reroll_history_summary[
        "total_slips_spent"
    ]

    total_other_slips = other_slip_summary[
        "total_slips_spent"
    ]

    total_slip_spend = (
        total_reroll_slips
        + total_other_slips
    )

    return [
        f"Task BP: {bp_reconciliation['task_bp']}",
        (
            f"Observed total BP: "
            f"{bp_reconciliation['observed_total_bp']}"
        ),
        (
            f"Additional BP: "
            f"{bp_reconciliation['additional_bp']}"
        ),
        f"Reroll slips: {total_reroll_slips}",
        f"Other slip spend: {total_other_slips}",
        f"Total slip spend: {total_slip_spend}",
        f"Slips: {starting_slips} -> {ending_slips}",
        (
            f"Data quality: "
            f"{data_quality['status']}"
        ),
    ]

# ============================================================
# V0.9 — Recommendation vs Actual Tracking
# ============================================================

RECOMMENDATION_ACTUAL_MODEL_VERSION = "0.9"

VALID_ACTUAL_OUTCOME_STATUSES = {
    "COMPLETED",
    "REROLLED",
    "SKIPPED",
    "PARTIAL",
}


def build_recommendation_tracking_key(
    recommendation,
):
    """
    Build a stable key for one optimizer recommendation.

    KEEP:
        KEEP::task_id

    REROLL:
        REROLL::task_id

    COMBO:
        COMBO::task_a||task_b

    COMBO task IDs are sorted so the key remains stable
    regardless of task ordering.
    """

    if not isinstance(
        recommendation,
        dict,
    ):
        raise ValueError(
            "recommendation must be a dictionary."
        )

    decision = recommendation.get(
        "decision"
    )

    if decision in {
        "KEEP",
        "REROLL",
    }:
        task_id = recommendation.get(
            "task"
        )

        if not isinstance(
            task_id,
            str,
        ) or not task_id.strip():
            raise ValueError(
                f"{decision} recommendation "
                "requires a task ID."
            )

        return (
            f"{decision}::{task_id.strip()}"
        )

    if decision == "COMBO":
        tasks = recommendation.get(
            "tasks"
        )

        if not isinstance(
            tasks,
            (list, tuple),
        ) or len(tasks) < 2:
            raise ValueError(
                "COMBO recommendation requires "
                "at least two task IDs."
            )

        normalized_tasks = []

        for task_id in tasks:
            if not isinstance(
                task_id,
                str,
            ) or not task_id.strip():
                raise ValueError(
                    "COMBO task IDs must be "
                    "non-empty strings."
                )

            normalized_tasks.append(
                task_id.strip()
            )

        return (
            "COMBO::"
            + "||".join(
                sorted(
                    normalized_tasks
                )
            )
        )

    raise ValueError(
        "Unsupported recommendation decision: "
        f"{decision!r}"
    )


def parse_optional_actual_decimal(
    value,
    field_name,
):
    """
    Parse an optional signed Decimal value.

    Actual net economic cost may legitimately be negative
    when recovery exceeds cost.
    """

    from decimal import Decimal, InvalidOperation

    if value is None:
        return None

    if isinstance(
        value,
        bool,
    ):
        raise ValueError(
            f"{field_name} must be numeric."
        )

    try:
        result = Decimal(
            str(value)
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ) as exc:
        raise ValueError(
            f"{field_name} must be numeric."
        ) from exc

    if not result.is_finite():
        raise ValueError(
            f"{field_name} must be finite."
        )

    return result


def normalize_actual_recommendation_outcome(
    actual_outcome,
):
    if not isinstance(
        actual_outcome,
        dict,
    ):
        raise ValueError(
            "Actual recommendation outcome "
            "must be a dictionary."
        )

    status = actual_outcome.get(
        "status"
    )

    if not isinstance(
        status,
        str,
    ):
        raise ValueError(
            "Actual outcome status "
            "must be a string."
        )

    status = (
        status
        .strip()
        .upper()
    )

    if status not in (
        VALID_ACTUAL_OUTCOME_STATUSES
    ):
        raise ValueError(
            "Unsupported actual outcome status: "
            f"{status!r}"
        )

    actual_bp = actual_outcome.get(
        "actual_bp"
    )

    if actual_bp is not None:
        if (
            isinstance(
                actual_bp,
                bool,
            )
            or not isinstance(
                actual_bp,
                (int, float),
            )
            or actual_bp < 0
        ):
            raise ValueError(
                "actual_bp must be a "
                "non-negative number."
            )

    actual_slips_spent = (
        actual_outcome.get(
            "actual_slips_spent"
        )
    )

    if actual_slips_spent is not None:
        if (
            isinstance(
                actual_slips_spent,
                bool,
            )
            or not isinstance(
                actual_slips_spent,
                int,
            )
            or actual_slips_spent < 0
        ):
            raise ValueError(
                "actual_slips_spent must be a "
                "non-negative integer."
            )

    actual_net_cost = (
        parse_optional_actual_decimal(
            actual_outcome.get(
                "actual_net_cost_weth"
            ),
            "actual_net_cost_weth",
        )
    )

    return {
        "status": status,
        "actual_bp": actual_bp,
        "actual_slips_spent": (
            actual_slips_spent
        ),
        "actual_net_cost_weth": (
            format_economic_decimal(
                actual_net_cost
            )
            if actual_net_cost
            is not None
            else None
        ),
        "notes": actual_outcome.get(
            "notes"
        ),
    }


def get_recommendation_planned_bp(
    recommendation,
):
    decision = recommendation.get(
        "decision"
    )

    if decision == "KEEP":
        return recommendation.get(
            "reward_bp"
        )

    if decision == "COMBO":
        return recommendation.get(
            "combined_bp"
        )

    # A REROLL recommendation does not plan to earn the
    # current task's BP.
    if decision == "REROLL":
        return None

    return None


def get_recommendation_expected_net_cost_weth(
    recommendation,
):
    economics = recommendation.get(
        "economics"
    )

    if not isinstance(
        economics,
        dict,
    ):
        return None

    if economics.get(
        "economic_status"
    ) != "READY":
        return None

    return economics.get(
        "estimated_net_cost_weth"
    )



def build_recommendation_actual_tracking(
    execution_plan,
    actual_outcomes=None,
):
    """
    Compare optimizer recommendations with recorded outcomes.

    Missing actual evidence remains PENDING rather than being
    treated as zero or as a failed recommendation.
    """

    from decimal import Decimal, InvalidOperation

    if not isinstance(
        execution_plan,
        dict,
    ):
        raise ValueError(
            "execution_plan must be a dictionary."
        )

    if actual_outcomes is None:
        actual_outcomes = {}

    if not isinstance(
        actual_outcomes,
        dict,
    ):
        raise ValueError(
            "actual_outcomes must be a dictionary."
        )

    recommendations = execution_plan.get(
        "recommendations",
        [],
    )

    reroll_results = execution_plan.get(
        "reroll_results",
        [],
    )

    tracking_rows = []

    for recommendation in recommendations:
        decision = recommendation.get(
            "decision"
        )

        tracking_key = (
            build_recommendation_tracking_key(
                recommendation
            )
        )

        if decision == "COMBO":
            task_ids = list(
                recommendation.get(
                    "tasks",
                    [],
                )
            )

        else:
            task_id = recommendation.get(
                "task"
            )

            task_ids = (
                []
                if task_id is None
                else [
                    task_id,
                ]
            )

        planned_bp = (
            get_recommendation_planned_bp(
                recommendation
            )
        )

        planned_reroll_slips = None

        if decision == "REROLL":
            task_id = recommendation.get(
                "task"
            )

            for reroll_result in reroll_results:
                if (
                    reroll_result.get(
                        "task"
                    )
                    != task_id
                ):
                    continue

                planned_reroll_slips = (
                    reroll_result.get(
                        "slip_cost"
                    )
                )

                break

        expected_net_cost = (
            get_recommendation_expected_net_cost_weth(
                recommendation
            )
        )

        if expected_net_cost is None:
            expected_net_cost_text = None
        else:
            expected_net_cost_text = str(
                expected_net_cost
            )

        raw_actual_outcome = (
            actual_outcomes.get(
                tracking_key
            )
        )

        if raw_actual_outcome is None:
            actual_status = "PENDING"
            actual_bp = None
            actual_slips_spent = None
            actual_net_cost_text = None

            bp_variance = None
            slip_variance = None
            net_cost_variance_text = None

            recommendation_followed = None
            notes = None

        else:
            normalized_outcome = (
                normalize_actual_recommendation_outcome(
                    raw_actual_outcome
                )
            )

            actual_status = (
                normalized_outcome[
                    "status"
                ]
            )

            actual_bp = (
                normalized_outcome.get(
                    "actual_bp"
                )
            )

            actual_slips_spent = (
                normalized_outcome.get(
                    "actual_slips_spent"
                )
            )

            actual_net_cost = (
                normalized_outcome.get(
                    "actual_net_cost_weth"
                )
            )

            notes = (
                normalized_outcome.get(
                    "notes"
                )
            )

            if actual_net_cost is None:
                actual_net_cost_text = None
            else:
                actual_net_cost_text = str(
                    actual_net_cost
                )

            # ------------------------------------------------
            # Recommendation-followed status
            # ------------------------------------------------

            if decision == "KEEP":
                recommendation_followed = (
                    actual_status == "COMPLETED"
                )

            elif decision == "COMBO":
                recommendation_followed = (
                    actual_status == "COMPLETED"
                )

            elif decision == "REROLL":
                recommendation_followed = (
                    actual_status == "REROLLED"
                )

            else:
                recommendation_followed = None

            # ------------------------------------------------
            # BP variance
            # ------------------------------------------------

            if (
                planned_bp is not None
                and actual_bp is not None
            ):
                bp_variance = (
                    actual_bp
                    - planned_bp
                )

            else:
                bp_variance = None

            # ------------------------------------------------
            # Fortune Slip variance
            # ------------------------------------------------

            if (
                planned_reroll_slips is not None
                and actual_slips_spent is not None
            ):
                slip_variance = (
                    actual_slips_spent
                    - planned_reroll_slips
                )

            else:
                slip_variance = None

            # ------------------------------------------------
            # WETH cost variance
            # ------------------------------------------------

            if (
                expected_net_cost is not None
                and actual_net_cost is not None
            ):
                try:
                    expected_decimal = Decimal(
                        str(
                            expected_net_cost
                        )
                    )

                    actual_decimal = Decimal(
                        str(
                            actual_net_cost
                        )
                    )

                except (
                    InvalidOperation,
                    ValueError,
                    TypeError,
                ) as exc:
                    raise ValueError(
                        "Invalid WETH value while "
                        "calculating recommendation "
                        "cost variance."
                    ) from exc

                net_cost_variance_text = str(
                    actual_decimal
                    - expected_decimal
                )

            else:
                net_cost_variance_text = None

        tracking_rows.append(
            {
                "model_version": (
                    RECOMMENDATION_ACTUAL_MODEL_VERSION
                ),
                "tracking_key": tracking_key,
                "recommended_decision": decision,
                "task_ids": task_ids,
                "planned_bp": planned_bp,
                "planned_reroll_slips": (
                    planned_reroll_slips
                ),
                "expected_net_cost_weth": (
                    expected_net_cost_text
                ),
                "actual_status": actual_status,
                "actual_bp": actual_bp,
                "actual_slips_spent": (
                    actual_slips_spent
                ),
                "actual_net_cost_weth": (
                    actual_net_cost_text
                ),
                "bp_variance": bp_variance,
                "slip_variance": slip_variance,
                "net_cost_variance_weth": (
                    net_cost_variance_text
                ),
                "recommendation_followed": (
                    recommendation_followed
                ),
                "notes": notes,
            }
        )

    return tracking_rows



# ============================================================
# V0.9 — Bounty Optimizer Decision Persistence
# ============================================================

BOUNTY_OPTIMIZER_PERSISTENCE_VERSION = "0.9"


def serialize_optimizer_json(
    value,
):
    """
    Serialize optimizer evidence deterministically.

    Decimal and other non-standard scalar values are retained
    as strings rather than being discarded.
    """

    if value is None:
        return None

    return json.dumps(
        value,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        default=str,
    )


def get_recommendation_economics_status(
    recommendation,
):
    """
    Read an economics status when one is available.

    The complete recommendation is also persisted as JSON, so
    absence of this convenience column never destroys detail.
    """

    direct_status = recommendation.get(
        "economics_status"
    )

    if direct_status is not None:
        return str(
            direct_status
        )

    for container_name in (
        "economics",
        "bounty_economics",
    ):
        economics = recommendation.get(
            container_name
        )

        if not isinstance(
            economics,
            dict,
        ):
            continue

        for status_name in (
            "status",
            "economic_status",
            "efficiency_status",
        ):
            status = economics.get(
                status_name
            )

            if status is not None:
                return str(
                    status
                )

    return None


def persist_bounty_optimizer_run(
    conn,
    daily_session_id,
    run_datetime,
    strategy_mode,
    execution_plan,
    tracking_rows,
    actual_outcomes=None,
    optimizer_model_version=(
        BOUNTY_OPTIMIZER_PERSISTENCE_VERSION
    ),
    run_source="LIVE_OPTIMIZER",
    plan_status=None,
    inventory_source=None,
    notes=None,
):
    """
    Persist one optimizer invocation and all of its decisions.

    The operation is atomic. If any decision fails to save,
    the optimizer-run record and all decisions from that run
    are rolled back together.

    This function does not create gameplay sessions and does
    not modify bounty_board_tasks.
    """

    if not isinstance(
        execution_plan,
        dict,
    ):
        raise ValueError(
            "execution_plan must be a dictionary."
        )

    if not isinstance(
        tracking_rows,
        list,
    ):
        raise ValueError(
            "tracking_rows must be a list."
        )

    if actual_outcomes is None:
        actual_outcomes = {}

    if not isinstance(
        actual_outcomes,
        dict,
    ):
        raise ValueError(
            "actual_outcomes must be a dictionary."
        )

    if not isinstance(
        run_datetime,
        str,
    ) or not run_datetime.strip():
        raise ValueError(
            "run_datetime must be a non-empty string."
        )

    if not isinstance(
        strategy_mode,
        str,
    ) or not strategy_mode.strip():
        raise ValueError(
            "strategy_mode must be a non-empty string."
        )

    recommendations = list(
        execution_plan.get(
            "recommendations",
            [],
        )
    )

    if len(
        recommendations
    ) != len(
        tracking_rows
    ):
        raise ValueError(
            "Recommendation count does not match "
            "tracking-row count."
        )

    # --------------------------------------------------------
    # Validate recommendation/tracking alignment before any
    # database write occurs.
    # --------------------------------------------------------

    for decision_index, (
        recommendation,
        tracking_row,
    ) in enumerate(
        zip(
            recommendations,
            tracking_rows,
        )
    ):
        expected_key = (
            build_recommendation_tracking_key(
                recommendation
            )
        )

        actual_key = tracking_row.get(
            "tracking_key"
        )

        if expected_key != actual_key:
            raise ValueError(
                "Recommendation/tracking mismatch at "
                f"decision index {decision_index}: "
                f"{expected_key!r} != {actual_key!r}"
            )

    session_exists = conn.execute(
        """
        SELECT 1
        FROM gameplay_daily_sessions
        WHERE id = ?
        """,
        (
            daily_session_id,
        ),
    ).fetchone()

    if session_exists is None:
        raise ValueError(
            "Unknown gameplay daily session ID: "
            f"{daily_session_id!r}"
        )

    if plan_status is None:
        plan_status = execution_plan.get(
            "plan_status"
        )

        if plan_status is None:
            plan_status = execution_plan.get(
                "status"
            )

    if inventory_source is None:
        inventory_source = execution_plan.get(
            "inventory_source"
        )

    savepoint_name = (
        "bounty_optimizer_run_persistence"
    )

    conn.execute(
        f"SAVEPOINT {savepoint_name}"
    )

    try:
        cursor = conn.execute(
            """
            INSERT INTO bounty_optimizer_runs (
                daily_session_id,
                run_datetime,
                strategy_mode,
                optimizer_model_version,
                run_source,
                plan_status,
                inventory_source,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                daily_session_id,
                run_datetime.strip(),
                strategy_mode.strip(),
                str(
                    optimizer_model_version
                ),
                str(
                    run_source
                ),
                (
                    None
                    if plan_status is None
                    else str(
                        plan_status
                    )
                ),
                (
                    None
                    if inventory_source is None
                    else str(
                        inventory_source
                    )
                ),
                notes,
            ),
        )

        optimizer_run_id = (
            cursor.lastrowid
        )

        for decision_index, (
            recommendation,
            tracking_row,
        ) in enumerate(
            zip(
                recommendations,
                tracking_rows,
            )
        ):
            tracking_key = tracking_row[
                "tracking_key"
            ]

            raw_actual_outcome = (
                actual_outcomes.get(
                    tracking_key
                )
            )

            followed = tracking_row.get(
                "recommendation_followed"
            )

            if followed is None:
                followed_db = None
            else:
                followed_db = int(
                    bool(
                        followed
                    )
                )

            expected_net_cost = (
                tracking_row.get(
                    "expected_net_cost_weth"
                )
            )

            actual_net_cost = (
                tracking_row.get(
                    "actual_net_cost_weth"
                )
            )

            net_cost_variance = (
                tracking_row.get(
                    "net_cost_variance_weth"
                )
            )

            conn.execute(
                """
                INSERT INTO bounty_optimizer_decisions (
                    optimizer_run_id,
                    decision_index,
                    tracking_key,
                    tracking_model_version,
                    decision,
                    task_ids_json,
                    planned_bp,
                    planned_reroll_slips,
                    economics_status,
                    expected_net_cost_weth,
                    actual_status,
                    actual_bp,
                    actual_slips_spent,
                    actual_net_cost_weth,
                    bp_variance,
                    slip_variance,
                    net_cost_variance_weth,
                    recommendation_followed,
                    recommendation_json,
                    actual_outcome_json,
                    notes
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    optimizer_run_id,
                    decision_index,
                    tracking_key,
                    str(
                        tracking_row.get(
                            "model_version",
                            RECOMMENDATION_ACTUAL_MODEL_VERSION,
                        )
                    ),
                    tracking_row[
                        "recommended_decision"
                    ],
                    serialize_optimizer_json(
                        tracking_row.get(
                            "task_ids",
                            [],
                        )
                    ),
                    tracking_row.get(
                        "planned_bp"
                    ),
                    tracking_row.get(
                        "planned_reroll_slips"
                    ),
                    get_recommendation_economics_status(
                        recommendation
                    ),
                    (
                        None
                        if expected_net_cost is None
                        else str(
                            expected_net_cost
                        )
                    ),
                    tracking_row.get(
                        "actual_status",
                        "PENDING",
                    ),
                    tracking_row.get(
                        "actual_bp"
                    ),
                    tracking_row.get(
                        "actual_slips_spent"
                    ),
                    (
                        None
                        if actual_net_cost is None
                        else str(
                            actual_net_cost
                        )
                    ),
                    tracking_row.get(
                        "bp_variance"
                    ),
                    tracking_row.get(
                        "slip_variance"
                    ),
                    (
                        None
                        if net_cost_variance is None
                        else str(
                            net_cost_variance
                        )
                    ),
                    followed_db,
                    serialize_optimizer_json(
                        recommendation
                    ),
                    serialize_optimizer_json(
                        raw_actual_outcome
                    ),
                    tracking_row.get(
                        "notes"
                    ),
                ),
            )

        conn.execute(
            f"RELEASE SAVEPOINT {savepoint_name}"
        )

    except Exception:
        conn.execute(
            f"ROLLBACK TO SAVEPOINT {savepoint_name}"
        )

        conn.execute(
            f"RELEASE SAVEPOINT {savepoint_name}"
        )

        raise

    return optimizer_run_id



def reconcile_persisted_bounty_optimizer_run(
    conn,
    optimizer_run_id,
    tracking_rows,
    actual_outcomes=None,
):
    """
    Update the actual-result side of one previously persisted
    optimizer run.

    Planned recommendation fields remain immutable.

    The update is atomic: either all decision outcomes are
    reconciled successfully or none are changed.
    """

    if not isinstance(
        tracking_rows,
        list,
    ):
        raise ValueError(
            "tracking_rows must be a list."
        )

    if actual_outcomes is None:
        actual_outcomes = {}

    if not isinstance(
        actual_outcomes,
        dict,
    ):
        raise ValueError(
            "actual_outcomes must be a dictionary."
        )

    run_exists = conn.execute(
        """
        SELECT 1
        FROM bounty_optimizer_runs
        WHERE id = ?
        """,
        (
            optimizer_run_id,
        ),
    ).fetchone()

    if run_exists is None:
        raise ValueError(
            "Unknown optimizer run ID: "
            f"{optimizer_run_id!r}"
        )

    persisted_rows = conn.execute(
        """
        SELECT
            decision_index,
            tracking_key,
            decision
        FROM bounty_optimizer_decisions
        WHERE optimizer_run_id = ?
        ORDER BY decision_index
        """,
        (
            optimizer_run_id,
        ),
    ).fetchall()

    if len(
        persisted_rows
    ) != len(
        tracking_rows
    ):
        raise ValueError(
            "Persisted decision count does not match "
            "tracking-row count."
        )

    # --------------------------------------------------------
    # Validate all rows before any write occurs.
    # --------------------------------------------------------

    for decision_index, (
        persisted,
        tracking_row,
    ) in enumerate(
        zip(
            persisted_rows,
            tracking_rows,
        )
    ):
        (
            persisted_index,
            persisted_key,
            persisted_decision,
        ) = persisted

        if persisted_index != decision_index:
            raise ValueError(
                "Unexpected persisted decision index: "
                f"{persisted_index!r}"
            )

        tracking_key = tracking_row.get(
            "tracking_key"
        )

        if tracking_key != persisted_key:
            raise ValueError(
                "Tracking-key mismatch at decision "
                f"index {decision_index}: "
                f"{persisted_key!r} != "
                f"{tracking_key!r}"
            )

        tracking_decision = tracking_row.get(
            "recommended_decision"
        )

        if tracking_decision != persisted_decision:
            raise ValueError(
                "Decision mismatch at decision "
                f"index {decision_index}: "
                f"{persisted_decision!r} != "
                f"{tracking_decision!r}"
            )

    savepoint_name = (
        "bounty_optimizer_reconciliation"
    )

    conn.execute(
        f"SAVEPOINT {savepoint_name}"
    )

    try:
        for decision_index, tracking_row in enumerate(
            tracking_rows
        ):
            tracking_key = tracking_row[
                "tracking_key"
            ]

            raw_actual_outcome = (
                actual_outcomes.get(
                    tracking_key
                )
            )

            followed = tracking_row.get(
                "recommendation_followed"
            )

            if followed is None:
                followed_db = None
            else:
                followed_db = int(
                    bool(
                        followed
                    )
                )

            actual_net_cost = (
                tracking_row.get(
                    "actual_net_cost_weth"
                )
            )

            net_cost_variance = (
                tracking_row.get(
                    "net_cost_variance_weth"
                )
            )

            conn.execute(
                """
                UPDATE bounty_optimizer_decisions
                SET
                    actual_status = ?,
                    actual_bp = ?,
                    actual_slips_spent = ?,
                    actual_net_cost_weth = ?,
                    bp_variance = ?,
                    slip_variance = ?,
                    net_cost_variance_weth = ?,
                    recommendation_followed = ?,
                    actual_outcome_json = ?,
                    notes = COALESCE(?, notes),
                    updated_at = CURRENT_TIMESTAMP
                WHERE optimizer_run_id = ?
                  AND decision_index = ?
                """,
                (
                    tracking_row.get(
                        "actual_status",
                        "PENDING",
                    ),
                    tracking_row.get(
                        "actual_bp"
                    ),
                    tracking_row.get(
                        "actual_slips_spent"
                    ),
                    (
                        None
                        if actual_net_cost is None
                        else str(
                            actual_net_cost
                        )
                    ),
                    tracking_row.get(
                        "bp_variance"
                    ),
                    tracking_row.get(
                        "slip_variance"
                    ),
                    (
                        None
                        if net_cost_variance is None
                        else str(
                            net_cost_variance
                        )
                    ),
                    followed_db,
                    serialize_optimizer_json(
                        raw_actual_outcome
                    ),
                    tracking_row.get(
                        "notes"
                    ),
                    optimizer_run_id,
                    decision_index,
                ),
            )

        conn.execute(
            f"RELEASE SAVEPOINT {savepoint_name}"
        )

    except Exception:
        conn.execute(
            f"ROLLBACK TO SAVEPOINT {savepoint_name}"
        )

        conn.execute(
            f"RELEASE SAVEPOINT {savepoint_name}"
        )

        raise

    return len(
        tracking_rows
    )



def run_v09_optimizer_persistence_test():
    import sqlite3

    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 OPTIMIZER PERSISTENCE TEST"
    )
    print(
        "============================================================"
    )

    conn = sqlite3.connect(
        ":memory:"
    )

    conn.execute(
        """
        CREATE TABLE gameplay_daily_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date TEXT NOT NULL,
            player_id TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE bounty_optimizer_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            daily_session_id INTEGER NOT NULL,

            run_datetime TEXT NOT NULL,
            strategy_mode TEXT NOT NULL,
            optimizer_model_version TEXT NOT NULL,

            run_source TEXT NOT NULL
                DEFAULT 'LIVE_OPTIMIZER',

            plan_status TEXT,
            inventory_source TEXT,
            notes TEXT,

            created_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (daily_session_id)
                REFERENCES gameplay_daily_sessions(id)
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE bounty_optimizer_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            optimizer_run_id INTEGER NOT NULL,
            decision_index INTEGER NOT NULL,

            tracking_key TEXT NOT NULL,
            tracking_model_version TEXT NOT NULL,

            decision TEXT NOT NULL,
            task_ids_json TEXT NOT NULL,

            planned_bp INTEGER,
            planned_reroll_slips INTEGER,

            economics_status TEXT,
            expected_net_cost_weth TEXT,

            actual_status TEXT NOT NULL
                DEFAULT 'PENDING',

            actual_bp INTEGER,
            actual_slips_spent INTEGER,
            actual_net_cost_weth TEXT,

            bp_variance INTEGER,
            slip_variance INTEGER,
            net_cost_variance_weth TEXT,

            recommendation_followed INTEGER,

            recommendation_json TEXT,
            actual_outcome_json TEXT,

            notes TEXT,

            created_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (optimizer_run_id)
                REFERENCES bounty_optimizer_runs(id),

            UNIQUE(
                optimizer_run_id,
                decision_index
            )
        )
        """
    )

    cursor = conn.execute(
        """
        INSERT INTO gameplay_daily_sessions (
            session_date,
            player_id
        )
        VALUES (?, ?)
        """,
        (
            "2026-08-30",
            "primary",
        ),
    )

    daily_session_id = (
        cursor.lastrowid
    )

    execution_plan = {
        "recommendations": [
            {
                "decision": "KEEP",
                "task": "test_keep",
                "reward_bp": 100,
                "economics_status": "READY",
            },
            {
                "decision": "COMBO",
                "tasks": [
                    "test_combo_a",
                    "test_combo_b",
                ],
                "combined_bp": 300,
            },
            {
                "decision": "REROLL",
                "task": "test_reroll",
                "reward_bp": 20,
            },
        ],
        "reroll_results": [
            {
                "task": "test_reroll",
                "slip_cost": 20,
            },
        ],
        "plan_status": "READY",
        "inventory_source": "manual",
    }

    actual_outcomes = {
        "KEEP::test_keep": {
            "status": "COMPLETED",
            "actual_bp": 100,
            "actual_slips_spent": 0,
            "actual_net_cost_weth": (
                "0.00009"
            ),
        },
        (
            "COMBO::test_combo_a"
            "||test_combo_b"
        ): {
            "status": "COMPLETED",
            "actual_bp": 300,
            "actual_slips_spent": 0,
            "actual_net_cost_weth": (
                "0.00022"
            ),
        },
        "REROLL::test_reroll": {
            "status": "REROLLED",
            "actual_bp": 0,
            "actual_slips_spent": 20,
            "actual_net_cost_weth": None,
        },
    }

    execution_plan[
        "recommendations"
    ][0][
        "economics"
    ] = {
        "status": "READY",
        "estimated_net_cost_weth": (
            "0.00010"
        ),
    }

    execution_plan[
        "recommendations"
    ][1][
        "economics"
    ] = {
        "status": "READY",
        "estimated_net_cost_weth": (
            "0.00020"
        ),
    }

    tracking_rows = (
        build_recommendation_actual_tracking(
            execution_plan=(
                execution_plan
            ),
            actual_outcomes=(
                actual_outcomes
            ),
        )
    )

    optimizer_run_id = (
        persist_bounty_optimizer_run(
            conn=conn,
            daily_session_id=(
                daily_session_id
            ),
            run_datetime=(
                "2026-08-30T21:30:00+08:00"
            ),
            strategy_mode="conserve",
            execution_plan=(
                execution_plan
            ),
            tracking_rows=(
                tracking_rows
            ),
            actual_outcomes=(
                actual_outcomes
            ),
            run_source="TEST",
            notes=(
                "V0.9 in-memory persistence test"
            ),
        )
    )

    run_row = conn.execute(
        """
        SELECT
            daily_session_id,
            strategy_mode,
            optimizer_model_version,
            run_source,
            plan_status,
            inventory_source
        FROM bounty_optimizer_runs
        WHERE id = ?
        """,
        (
            optimizer_run_id,
        ),
    ).fetchone()

    decision_rows = conn.execute(
        """
        SELECT
            decision_index,
            tracking_key,
            decision,
            actual_status,
            recommendation_followed,
            recommendation_json,
            actual_outcome_json
        FROM bounty_optimizer_decisions
        WHERE optimizer_run_id = ?
        ORDER BY decision_index
        """,
        (
            optimizer_run_id,
        ),
    ).fetchall()

    run_passed = (
        run_row
        == (
            daily_session_id,
            "conserve",
            "0.9",
            "TEST",
            "READY",
            "manual",
        )
    )

    print(
        "Optimizer run row:",
        "PASS" if run_passed else "FAIL",
    )
    print(
        "  Row:",
        run_row,
    )

    decisions_passed = (
        len(
            decision_rows
        ) == 3
        and decision_rows[
            0
        ][1] == "KEEP::test_keep"
        and decision_rows[
            0
        ][3] == "COMPLETED"
        and decision_rows[
            0
        ][4] == 1
        and decision_rows[
            1
        ][1] == (
            "COMBO::test_combo_a"
            "||test_combo_b"
        )
        and decision_rows[
            2
        ][1] == "REROLL::test_reroll"
        and decision_rows[
            2
        ][3] == "REROLLED"
        and decision_rows[
            2
        ][4] == 1
    )

    print(
        "Decision rows:",
        (
            "PASS"
            if decisions_passed
            else "FAIL"
        ),
    )

    for row in decision_rows:
        print(
            " ",
            row[:5],
        )

    json_passed = True

    for row in decision_rows:
        try:
            recommendation_payload = (
                json.loads(
                    row[5]
                )
            )

            actual_payload = (
                json.loads(
                    row[6]
                )
            )

        except Exception:
            json_passed = False
            break

        if not isinstance(
            recommendation_payload,
            dict,
        ):
            json_passed = False

        if not isinstance(
            actual_payload,
            dict,
        ):
            json_passed = False

    print(
        "JSON round-trip:",
        (
            "PASS"
            if json_passed
            else "FAIL"
        ),
    )

    # --------------------------------------------------------
    # Atomic rollback test
    # --------------------------------------------------------

    before_runs = conn.execute(
        """
        SELECT COUNT(*)
        FROM bounty_optimizer_runs
        """
    ).fetchone()[0]

    before_decisions = conn.execute(
        """
        SELECT COUNT(*)
        FROM bounty_optimizer_decisions
        """
    ).fetchone()[0]

    conn.execute(
        """
        CREATE TRIGGER
            force_optimizer_decision_failure
        BEFORE INSERT
        ON bounty_optimizer_decisions
        WHEN NEW.decision_index = 1
        BEGIN
            SELECT RAISE(
                ABORT,
                'forced optimizer decision failure'
            );
        END
        """
    )

    rollback_raised = False

    try:
        persist_bounty_optimizer_run(
            conn=conn,
            daily_session_id=(
                daily_session_id
            ),
            run_datetime=(
                "2026-08-30T21:31:00+08:00"
            ),
            strategy_mode="conserve",
            execution_plan=(
                execution_plan
            ),
            tracking_rows=(
                tracking_rows
            ),
            actual_outcomes=(
                actual_outcomes
            ),
            run_source="ROLLBACK_TEST",
        )

    except sqlite3.DatabaseError as exc:
        rollback_raised = True

        print(
            "Forced failure raised: PASS"
        )
        print(
            "  Message:",
            str(exc),
        )

    else:
        print(
            "Forced failure raised: FAIL"
        )

    after_runs = conn.execute(
        """
        SELECT COUNT(*)
        FROM bounty_optimizer_runs
        """
    ).fetchone()[0]

    after_decisions = conn.execute(
        """
        SELECT COUNT(*)
        FROM bounty_optimizer_decisions
        """
    ).fetchone()[0]

    rollback_passed = (
        rollback_raised
        and before_runs == after_runs
        and before_decisions == (
            after_decisions
        )
    )

    print(
        "Atomic rollback:",
        (
            "PASS"
            if rollback_passed
            else "FAIL"
        ),
    )

    conn.close()

    all_passed = (
        run_passed
        and decisions_passed
        and json_passed
        and rollback_passed
    )

    print(
        "\nV0.9 Optimizer Persistence:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



# ============================================================
# V0.9 — Explicit Optimizer Run Save Integration
# ============================================================


def normalize_persisted_strategy_mode(
    strategy_mode,
):
    """
    Normalize a strategy label for persistence without
    changing optimizer strategy behavior.
    """

    if not isinstance(
        strategy_mode,
        str,
    ):
        raise ValueError(
            "strategy_mode must be a string."
        )

    stripped = strategy_mode.strip()

    if not stripped:
        raise ValueError(
            "strategy_mode cannot be empty."
        )

    alias_match = (
        STRATEGY_MODE_ALIASES.get(
            stripped
        )
    )

    if alias_match is not None:
        return alias_match

    return (
        stripped
        .casefold()
        .replace(
            " ",
            "_",
        )
    )


def build_optimizer_plan_persistence_signature(
    execution_plan,
):
    """
    Build a deterministic representation of the decisions
    contained in one optimizer plan.

    Used only for duplicate detection.
    """

    if not isinstance(
        execution_plan,
        dict,
    ):
        raise ValueError(
            "execution_plan must be a dictionary."
        )

    signature = []

    for decision_index, recommendation in enumerate(
        execution_plan.get(
            "recommendations",
            [],
        )
    ):
        signature.append(
            (
                decision_index,
                build_recommendation_tracking_key(
                    recommendation
                ),
                serialize_optimizer_json(
                    recommendation
                ),
            )
        )

    return signature


def find_duplicate_bounty_optimizer_run(
    conn,
    daily_session_id,
    strategy_mode,
    execution_plan,
    run_source="LIVE_OPTIMIZER",
):
    """
    Return an existing run ID if the same exact optimizer
    recommendation plan has already been persisted.
    """

    normalized_strategy = (
        normalize_persisted_strategy_mode(
            strategy_mode
        )
    )

    inventory_source = (
        execution_plan.get(
            "inventory_source"
        )
    )

    current_signature = (
        build_optimizer_plan_persistence_signature(
            execution_plan
        )
    )

    candidate_rows = conn.execute(
        """
        SELECT
            id,
            inventory_source
        FROM bounty_optimizer_runs
        WHERE daily_session_id = ?
          AND strategy_mode = ?
          AND run_source = ?
        ORDER BY id DESC
        """,
        (
            daily_session_id,
            normalized_strategy,
            str(
                run_source
            ),
        ),
    ).fetchall()

    for (
        optimizer_run_id,
        stored_inventory_source,
    ) in candidate_rows:

        if (
            stored_inventory_source
            != inventory_source
        ):
            continue

        stored_signature = conn.execute(
            """
            SELECT
                decision_index,
                tracking_key,
                recommendation_json
            FROM bounty_optimizer_decisions
            WHERE optimizer_run_id = ?
            ORDER BY decision_index
            """,
            (
                optimizer_run_id,
            ),
        ).fetchall()

        if stored_signature == current_signature:
            return optimizer_run_id

    return None


def save_optimizer_execution_plan_for_session(
    conn,
    session_date,
    strategy_mode,
    execution_plan,
    player_id="primary",
    run_datetime=None,
    run_source="LIVE_OPTIMIZER",
    notes=None,
    allow_historical=False,
    current_date=None,
):
    """
    Explicitly persist one completed optimizer plan.

    LIVE_OPTIMIZER saves protect against accidental
    historical attribution and exact duplicate saves.

    Recommendations are initially stored as PENDING.
    """

    if not isinstance(
        session_date,
        str,
    ) or not session_date.strip():
        raise ValueError(
            "session_date must be a non-empty string."
        )

    session_date = (
        session_date.strip()
    )

    normalized_strategy = (
        normalize_persisted_strategy_mode(
            strategy_mode
        )
    )

    if current_date is None:
        current_date = (
            datetime.now()
            .astimezone()
            .date()
            .isoformat()
        )

    if (
        str(
            run_source
        )
        == "LIVE_OPTIMIZER"
        and session_date
        != current_date
        and not allow_historical
    ):
        raise ValueError(
            "Historical LIVE_OPTIMIZER save blocked: "
            f"session date {session_date!r} does not "
            f"match current date {current_date!r}. "
            "This prevents retroactively manufacturing "
            "optimizer recommendation history."
        )

    session_row = conn.execute(
        """
        SELECT id
        FROM gameplay_daily_sessions
        WHERE session_date = ?
          AND player_id = ?
        """,
        (
            session_date,
            player_id,
        ),
    ).fetchone()

    if session_row is None:
        raise ValueError(
            "No gameplay daily session found for "
            f"{session_date!r}, "
            f"player {player_id!r}."
        )

    daily_session_id = (
        session_row[0]
    )

    duplicate_run_id = (
        find_duplicate_bounty_optimizer_run(
            conn=conn,
            daily_session_id=(
                daily_session_id
            ),
            strategy_mode=(
                normalized_strategy
            ),
            execution_plan=(
                execution_plan
            ),
            run_source=run_source,
        )
    )

    if duplicate_run_id is not None:
        raise ValueError(
            "Exact optimizer plan already persisted "
            f"as run #{duplicate_run_id}."
        )

    if run_datetime is None:
        run_datetime = (
            datetime.now()
            .astimezone()
            .isoformat(
                timespec="seconds"
            )
        )

    pending_tracking = (
        build_recommendation_actual_tracking(
            execution_plan=(
                execution_plan
            ),
            actual_outcomes=None,
        )
    )

    plan_status = (
        execution_plan.get(
            "plan_status"
        )
    )

    if plan_status is None:
        plan_status = (
            execution_plan.get(
                "status"
            )
        )

    if plan_status is None:
        readiness = (
            evaluate_v1_readiness(
                execution_plan
            )
        )

        plan_status = readiness.get(
            "v1_status"
        )

    try:
        optimizer_run_id = (
            persist_bounty_optimizer_run(
                conn=conn,
                daily_session_id=(
                    daily_session_id
                ),
                run_datetime=(
                    run_datetime
                ),
                strategy_mode=(
                    normalized_strategy
                ),
                execution_plan=(
                    execution_plan
                ),
                tracking_rows=(
                    pending_tracking
                ),
                actual_outcomes=None,
                run_source=(
                    run_source
                ),
                plan_status=(
                    plan_status
                ),
                inventory_source=(
                    execution_plan.get(
                        "inventory_source"
                    )
                ),
                notes=notes,
            )
        )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    return {
        "optimizer_run_id": (
            optimizer_run_id
        ),
        "daily_session_id": (
            daily_session_id
        ),
        "session_date": (
            session_date
        ),
        "strategy_mode": (
            normalized_strategy
        ),
        "run_datetime": (
            run_datetime
        ),
        "run_source": (
            run_source
        ),
        "decision_count": len(
            pending_tracking
        ),
        "actual_status": (
            "PENDING"
        ),
    }


def save_current_daily_optimizer_run(
    notes=None,
):
    """
    Explicit production command for saving the current
    bounty_daily_input.py optimizer recommendation.

    This function is intentionally NOT called by __main__.
    """

    today = (
        datetime.now()
        .astimezone()
        .date()
        .isoformat()
    )

    if DAILY_DATE != today:
        raise ValueError(
            "Current daily input is historical. "
            f"DAILY_DATE={DAILY_DATE!r}, "
            f"today={today!r}. "
            "Update bounty_daily_input.py to the genuine "
            "current Bounty session before saving a live "
            "optimizer recommendation."
        )

    execution_plan = (
        run_current_daily_plan()
    )

    conn = connect_database()

    try:
        result = (
            save_optimizer_execution_plan_for_session(
                conn=conn,
                session_date=(
                    DAILY_DATE
                ),
                strategy_mode=(
                    DAILY_STRATEGY_MODE
                ),
                execution_plan=(
                    execution_plan
                ),
                player_id="primary",
                run_source=(
                    "LIVE_OPTIMIZER"
                ),
                notes=notes,
            )
        )

    finally:
        conn.close()

    print()
    print(
        "Optimizer run saved:",
        result[
            "optimizer_run_id"
        ],
    )
    print(
        "Session date:",
        result[
            "session_date"
        ],
    )
    print(
        "Decisions saved:",
        result[
            "decision_count"
        ],
    )
    print(
        "Actual status:",
        result[
            "actual_status"
        ],
    )

    return result



def run_v09_explicit_optimizer_save_test():
    import sqlite3

    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 EXPLICIT OPTIMIZER SAVE TEST"
    )
    print(
        "============================================================"
    )

    conn = sqlite3.connect(
        ":memory:"
    )

    conn.execute(
        """
        CREATE TABLE gameplay_daily_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date TEXT NOT NULL,
            player_id TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE bounty_optimizer_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            daily_session_id INTEGER NOT NULL,
            run_datetime TEXT NOT NULL,
            strategy_mode TEXT NOT NULL,
            optimizer_model_version TEXT NOT NULL,
            run_source TEXT NOT NULL,
            plan_status TEXT,
            inventory_source TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE bounty_optimizer_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            optimizer_run_id INTEGER NOT NULL,
            decision_index INTEGER NOT NULL,
            tracking_key TEXT NOT NULL,
            tracking_model_version TEXT NOT NULL,
            decision TEXT NOT NULL,
            task_ids_json TEXT NOT NULL,
            planned_bp INTEGER,
            planned_reroll_slips INTEGER,
            economics_status TEXT,
            expected_net_cost_weth TEXT,
            actual_status TEXT NOT NULL
                DEFAULT 'PENDING',
            actual_bp INTEGER,
            actual_slips_spent INTEGER,
            actual_net_cost_weth TEXT,
            bp_variance INTEGER,
            slip_variance INTEGER,
            net_cost_variance_weth TEXT,
            recommendation_followed INTEGER,
            recommendation_json TEXT,
            actual_outcome_json TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(
                optimizer_run_id,
                decision_index
            )
        )
        """
    )

    conn.execute(
        """
        INSERT INTO gameplay_daily_sessions (
            session_date,
            player_id
        )
        VALUES (?, ?)
        """,
        (
            "2026-08-30",
            "primary",
        ),
    )

    conn.execute(
        """
        INSERT INTO gameplay_daily_sessions (
            session_date,
            player_id
        )
        VALUES (?, ?)
        """,
        (
            "2026-08-18",
            "primary",
        ),
    )

    execution_plan = {
        "recommendations": [
            {
                "decision": "KEEP",
                "task": "test_keep",
                "reward_bp": 100,
            },
            {
                "decision": "REROLL",
                "task": "test_reroll",
                "reward_bp": 20,
            },
        ],
        "reroll_results": [
            {
                "task": "test_reroll",
                "slip_cost": 20,
            },
        ],
        "plan_status": "READY",
        "inventory_source": "manual",
    }

    # --------------------------------------------------------
    # Test 1 — genuine current-date save
    # --------------------------------------------------------

    result = (
        save_optimizer_execution_plan_for_session(
            conn=conn,
            session_date="2026-08-30",
            strategy_mode="Conserve",
            execution_plan=execution_plan,
            run_datetime=(
                "2026-08-30T22:00:00+08:00"
            ),
            run_source="LIVE_OPTIMIZER",
            current_date="2026-08-30",
        )
    )

    run_row = conn.execute(
        """
        SELECT
            strategy_mode,
            run_source,
            plan_status,
            inventory_source
        FROM bounty_optimizer_runs
        WHERE id = ?
        """,
        (
            result[
                "optimizer_run_id"
            ],
        ),
    ).fetchone()

    decision_rows = conn.execute(
        """
        SELECT
            tracking_key,
            actual_status
        FROM bounty_optimizer_decisions
        WHERE optimizer_run_id = ?
        ORDER BY decision_index
        """,
        (
            result[
                "optimizer_run_id"
            ],
        ),
    ).fetchall()

    save_passed = (
        run_row
        == (
            "conserve",
            "LIVE_OPTIMIZER",
            "READY",
            "manual",
        )
        and decision_rows
        == [
            (
                "KEEP::test_keep",
                "PENDING",
            ),
            (
                "REROLL::test_reroll",
                "PENDING",
            ),
        ]
    )

    print(
        "Explicit current-date save:",
        "PASS" if save_passed else "FAIL",
    )

    # --------------------------------------------------------
    # Test 2 — exact duplicate must be blocked
    # --------------------------------------------------------

    duplicate_passed = False

    try:
        save_optimizer_execution_plan_for_session(
            conn=conn,
            session_date="2026-08-30",
            strategy_mode="Conserve",
            execution_plan=execution_plan,
            run_datetime=(
                "2026-08-30T22:01:00+08:00"
            ),
            run_source="LIVE_OPTIMIZER",
            current_date="2026-08-30",
        )

    except ValueError as exc:
        duplicate_passed = (
            "already persisted"
            in str(
                exc
            )
        )

        print(
            "Duplicate guardrail:",
            (
                "PASS"
                if duplicate_passed
                else "FAIL"
            ),
        )
        print(
            "  Message:",
            str(
                exc
            ),
        )

    else:
        print(
            "Duplicate guardrail: FAIL"
        )

    # --------------------------------------------------------
    # Test 3 — historical live attribution must be blocked
    # --------------------------------------------------------

    historical_passed = False

    try:
        save_optimizer_execution_plan_for_session(
            conn=conn,
            session_date="2026-08-18",
            strategy_mode="Conserve",
            execution_plan=execution_plan,
            run_datetime=(
                "2026-08-30T22:02:00+08:00"
            ),
            run_source="LIVE_OPTIMIZER",
            current_date="2026-08-30",
        )

    except ValueError as exc:
        historical_passed = (
            "Historical LIVE_OPTIMIZER save blocked"
            in str(
                exc
            )
        )

        print(
            "Historical-attribution guardrail:",
            (
                "PASS"
                if historical_passed
                else "FAIL"
            ),
        )
        print(
            "  Message:",
            str(
                exc
            ),
        )

    else:
        print(
            "Historical-attribution guardrail: FAIL"
        )

    # --------------------------------------------------------
    # Test 4 — failed guardrails added nothing
    # --------------------------------------------------------

    run_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM bounty_optimizer_runs
        """
    ).fetchone()[0]

    decision_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM bounty_optimizer_decisions
        """
    ).fetchone()[0]

    count_passed = (
        run_count == 1
        and decision_count == 2
    )

    print(
        "Guardrails leave DB unchanged:",
        "PASS" if count_passed else "FAIL",
    )
    print(
        "  Runs:",
        run_count,
    )
    print(
        "  Decisions:",
        decision_count,
    )

    conn.close()

    all_passed = (
        save_passed
        and duplicate_passed
        and historical_passed
        and count_passed
    )

    print(
        "\nV0.9 Explicit Optimizer Save:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed




def run_v09_optimizer_reconciliation_test():
    import sqlite3

    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 OPTIMIZER RECONCILIATION TEST"
    )
    print(
        "============================================================"
    )

    conn = sqlite3.connect(
        ":memory:"
    )

    conn.execute(
        """
        CREATE TABLE gameplay_daily_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date TEXT NOT NULL,
            player_id TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE bounty_optimizer_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            daily_session_id INTEGER NOT NULL,
            run_datetime TEXT NOT NULL,
            strategy_mode TEXT NOT NULL,
            optimizer_model_version TEXT NOT NULL,
            run_source TEXT NOT NULL
                DEFAULT 'LIVE_OPTIMIZER',
            plan_status TEXT,
            inventory_source TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE bounty_optimizer_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            optimizer_run_id INTEGER NOT NULL,
            decision_index INTEGER NOT NULL,
            tracking_key TEXT NOT NULL,
            tracking_model_version TEXT NOT NULL,
            decision TEXT NOT NULL,
            task_ids_json TEXT NOT NULL,
            planned_bp INTEGER,
            planned_reroll_slips INTEGER,
            economics_status TEXT,
            expected_net_cost_weth TEXT,
            actual_status TEXT NOT NULL
                DEFAULT 'PENDING',
            actual_bp INTEGER,
            actual_slips_spent INTEGER,
            actual_net_cost_weth TEXT,
            bp_variance INTEGER,
            slip_variance INTEGER,
            net_cost_variance_weth TEXT,
            recommendation_followed INTEGER,
            recommendation_json TEXT,
            actual_outcome_json TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL
                DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(
                optimizer_run_id,
                decision_index
            )
        )
        """
    )

    cursor = conn.execute(
        """
        INSERT INTO gameplay_daily_sessions (
            session_date,
            player_id
        )
        VALUES (?, ?)
        """,
        (
            "2026-08-30",
            "primary",
        ),
    )

    daily_session_id = (
        cursor.lastrowid
    )

    execution_plan = {
        "recommendations": [
            {
                "decision": "KEEP",
                "task": "test_keep",
                "reward_bp": 100,
            },
            {
                "decision": "REROLL",
                "task": "test_reroll",
                "reward_bp": 20,
            },
        ],
        "reroll_results": [
            {
                "task": "test_reroll",
                "slip_cost": 20,
            },
        ],
        "plan_status": "READY",
        "inventory_source": "manual",
    }

    # --------------------------------------------------------
    # Initial recommendation save — no actual evidence yet.
    # --------------------------------------------------------

    pending_tracking = (
        build_recommendation_actual_tracking(
            execution_plan=execution_plan,
            actual_outcomes=None,
        )
    )

    optimizer_run_id = (
        persist_bounty_optimizer_run(
            conn=conn,
            daily_session_id=(
                daily_session_id
            ),
            run_datetime=(
                "2026-08-30T21:45:00+08:00"
            ),
            strategy_mode="conserve",
            execution_plan=(
                execution_plan
            ),
            tracking_rows=(
                pending_tracking
            ),
            actual_outcomes=None,
            run_source="TEST",
        )
    )

    pending_rows = conn.execute(
        """
        SELECT
            decision_index,
            actual_status,
            recommendation_followed
        FROM bounty_optimizer_decisions
        WHERE optimizer_run_id = ?
        ORDER BY decision_index
        """,
        (
            optimizer_run_id,
        ),
    ).fetchall()

    pending_passed = (
        pending_rows
        == [
            (
                0,
                "PENDING",
                None,
            ),
            (
                1,
                "PENDING",
                None,
            ),
        ]
    )

    print(
        "Initial PENDING save:",
        (
            "PASS"
            if pending_passed
            else "FAIL"
        ),
    )
    print(
        "  Rows:",
        pending_rows,
    )

    # --------------------------------------------------------
    # Later actual evidence becomes available.
    # --------------------------------------------------------

    actual_outcomes = {
        "KEEP::test_keep": {
            "status": "COMPLETED",
            "actual_bp": 100,
            "actual_slips_spent": 0,
            "actual_net_cost_weth": None,
        },
        "REROLL::test_reroll": {
            "status": "REROLLED",
            "actual_bp": 0,
            "actual_slips_spent": 30,
            "actual_net_cost_weth": None,
        },
    }

    completed_tracking = (
        build_recommendation_actual_tracking(
            execution_plan=execution_plan,
            actual_outcomes=actual_outcomes,
        )
    )

    updated_count = (
        reconcile_persisted_bounty_optimizer_run(
            conn=conn,
            optimizer_run_id=(
                optimizer_run_id
            ),
            tracking_rows=(
                completed_tracking
            ),
            actual_outcomes=(
                actual_outcomes
            ),
        )
    )

    updated_rows = conn.execute(
        """
        SELECT
            decision_index,
            actual_status,
            actual_bp,
            actual_slips_spent,
            bp_variance,
            slip_variance,
            recommendation_followed,
            actual_outcome_json
        FROM bounty_optimizer_decisions
        WHERE optimizer_run_id = ?
        ORDER BY decision_index
        """,
        (
            optimizer_run_id,
        ),
    ).fetchall()

    keep_row = updated_rows[0]
    reroll_row = updated_rows[1]

    update_passed = (
        updated_count == 2
        and keep_row[1] == "COMPLETED"
        and keep_row[2] == 100
        and keep_row[4] == 0
        and keep_row[6] == 1
        and reroll_row[1] == "REROLLED"
        and reroll_row[3] == 30
        and reroll_row[5] == 10
        and reroll_row[6] == 1
    )

    print(
        "Outcome reconciliation:",
        (
            "PASS"
            if update_passed
            else "FAIL"
        ),
    )

    print(
        "  KEEP:",
        keep_row[:7],
    )

    print(
        "  REROLL:",
        reroll_row[:7],
    )

    json_passed = all(
        isinstance(
            json.loads(
                row[7]
            ),
            dict,
        )
        for row in updated_rows
    )

    print(
        "Actual JSON round-trip:",
        (
            "PASS"
            if json_passed
            else "FAIL"
        ),
    )

    # --------------------------------------------------------
    # Guardrail — mismatched tracking data must not update.
    # --------------------------------------------------------

    bad_tracking = [
        dict(
            row
        )
        for row in completed_tracking
    ]

    bad_tracking[0][
        "tracking_key"
    ] = "KEEP::wrong_task"

    mismatch_passed = False

    before_statuses = conn.execute(
        """
        SELECT
            actual_status,
            actual_slips_spent
        FROM bounty_optimizer_decisions
        WHERE optimizer_run_id = ?
        ORDER BY decision_index
        """,
        (
            optimizer_run_id,
        ),
    ).fetchall()

    try:
        reconcile_persisted_bounty_optimizer_run(
            conn=conn,
            optimizer_run_id=(
                optimizer_run_id
            ),
            tracking_rows=(
                bad_tracking
            ),
            actual_outcomes=(
                actual_outcomes
            ),
        )

    except ValueError as exc:
        mismatch_passed = True

        print(
            "Mismatch guardrail: PASS"
        )
        print(
            "  Message:",
            str(exc),
        )

    else:
        print(
            "Mismatch guardrail: FAIL"
        )

    after_statuses = conn.execute(
        """
        SELECT
            actual_status,
            actual_slips_spent
        FROM bounty_optimizer_decisions
        WHERE optimizer_run_id = ?
        ORDER BY decision_index
        """,
        (
            optimizer_run_id,
        ),
    ).fetchall()

    unchanged_passed = (
        before_statuses
        == after_statuses
    )

    print(
        "Mismatch leaves rows unchanged:",
        (
            "PASS"
            if unchanged_passed
            else "FAIL"
        ),
    )

    conn.close()

    all_passed = (
        pending_passed
        and update_passed
        and json_passed
        and mismatch_passed
        and unchanged_passed
    )

    print(
        "\nV0.9 Optimizer Reconciliation:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed




def load_gameplay_bounty_session_rows(
    conn,
    session_date,
    player_id="primary",
):
    """
    Load and resolve all recorded Bounty task rolls for
    one gameplay daily session.

    This is read-only.

    Each DB row receives a stable V0.9/historical task ID
    through resolve_historical_bounty_task_id().
    """

    session = conn.execute(
        """
        SELECT
            id,
            session_date,
            player_id
        FROM gameplay_daily_sessions
        WHERE session_date = ?
          AND player_id = ?
        """,
        (
            session_date,
            player_id,
        ),
    ).fetchone()

    if session is None:
        raise ValueError(
            "No gameplay daily session found for "
            f"{session_date!r}, player {player_id!r}."
        )

    daily_session_id = session[0]

    rows = conn.execute(
        """
        SELECT
            id,
            task_slot,
            roll_number,
            game,
            difficulty,
            action,
            requirement,
            reward_bp,
            reroll_cost_slips,
            completed,
            selected_final
        FROM bounty_board_tasks
        WHERE daily_session_id = ?
        ORDER BY
            task_slot,
            roll_number,
            id
        """,
        (
            daily_session_id,
        ),
    ).fetchall()

    resolved_rows = []

    for row in rows:
        (
            row_id,
            task_slot,
            roll_number,
            game,
            difficulty,
            action,
            requirement,
            reward_bp,
            reroll_cost_slips,
            completed,
            selected_final,
        ) = row

        resolution = (
            resolve_historical_bounty_task_id(
                action=action,
                requirement=requirement,
            )
        )

        resolved_rows.append(
            {
                "db_id": row_id,
                "daily_session_id": (
                    daily_session_id
                ),
                "session_date": session_date,
                "player_id": player_id,
                "task_slot": task_slot,
                "roll_number": roll_number,
                "game": game,
                "difficulty": difficulty,
                "action": action,
                "requirement": requirement,
                "reward_bp": reward_bp,
                "reroll_cost_slips": (
                    reroll_cost_slips
                ),
                "completed": bool(
                    completed
                ),
                "selected_final": bool(
                    selected_final
                ),
                "task_id": resolution[
                    "task_id"
                ],
                "resolution_source": resolution[
                    "resolution_source"
                ],
            }
        )

    return resolved_rows


def find_unique_recorded_task_match(
    session_rows,
    task_id,
):
    """
    Match one optimizer task ID to its recorded DB roll.

    Multiple occurrences in different task slots are treated
    as ambiguous rather than silently choosing the wrong one.
    """

    matches = [
        row
        for row in session_rows
        if row[
            "task_id"
        ] == task_id
    ]

    if not matches:
        return None

    slots = {
        row[
            "task_slot"
        ]
        for row in matches
    }

    if len(slots) > 1:
        raise ValueError(
            "Recorded task match is ambiguous across "
            f"multiple slots for {task_id!r}: "
            f"{sorted(slots)}"
        )

    # If the same semantic task appeared more than once
    # inside the same reroll chain, use the earliest matching
    # occurrence as the recommendation reference point.
    return sorted(
        matches,
        key=lambda row: (
            row[
                "roll_number"
            ],
            row[
                "db_id"
            ],
        ),
    )[0]


def get_recorded_slot_rows(
    session_rows,
    task_slot,
):
    return sorted(
        [
            row
            for row in session_rows
            if row[
                "task_slot"
            ] == task_slot
        ],
        key=lambda row: (
            row[
                "roll_number"
            ],
            row[
                "db_id"
            ],
        ),
    )


def calculate_recorded_reroll_spend_after_row(
    session_rows,
    reference_row,
):
    """
    Sum all recorded reroll costs after one task roll.

    This intentionally captures additional rerolls made after
    the recommendation point. Comparing this with the planned
    reroll cost exposes overspend/underspend as slip variance.
    """

    slot_rows = get_recorded_slot_rows(
        session_rows=session_rows,
        task_slot=reference_row[
            "task_slot"
        ],
    )

    return sum(
        (
            row.get(
                "reroll_cost_slips"
            )
            or 0
        )
        for row in slot_rows
        if row[
            "roll_number"
        ] > reference_row[
            "roll_number"
        ]
    )


def build_actual_outcomes_from_gameplay_session(
    conn,
    execution_plan,
    session_date,
    player_id="primary",
):
    """
    Convert recorded gameplay DB evidence into the
    actual_outcomes dictionary consumed by
    build_recommendation_actual_tracking().

    No economic cost is invented here. bounty_board_tasks
    contains completion/BP/reroll evidence, but not a reliable
    task-level actual WETH cost.
    """

    session_rows = (
        load_gameplay_bounty_session_rows(
            conn=conn,
            session_date=session_date,
            player_id=player_id,
        )
    )

    actual_outcomes = {}

    for recommendation in execution_plan.get(
        "recommendations",
        [],
    ):
        decision = recommendation[
            "decision"
        ]

        tracking_key = (
            build_recommendation_tracking_key(
                recommendation
            )
        )

        # ====================================================
        # KEEP
        # ====================================================

        if decision == "KEEP":
            task_id = recommendation[
                "task"
            ]

            matched = (
                find_unique_recorded_task_match(
                    session_rows=session_rows,
                    task_id=task_id,
                )
            )

            if matched is None:
                # Missing evidence remains PENDING when the
                # tracking model consumes actual_outcomes.
                continue

            slot_rows = (
                get_recorded_slot_rows(
                    session_rows=session_rows,
                    task_slot=matched[
                        "task_slot"
                    ],
                )
            )

            later_rows = [
                row
                for row in slot_rows
                if row[
                    "roll_number"
                ] > matched[
                    "roll_number"
                ]
            ]

            if matched[
                "selected_final"
            ]:
                if matched[
                    "completed"
                ]:
                    status = "COMPLETED"
                    actual_bp = matched[
                        "reward_bp"
                    ]
                else:
                    status = "SKIPPED"
                    actual_bp = 0

                actual_slips = 0

            elif later_rows:
                status = "REROLLED"
                actual_bp = 0

                actual_slips = (
                    calculate_recorded_reroll_spend_after_row(
                        session_rows=(
                            session_rows
                        ),
                        reference_row=matched,
                    )
                )

            else:
                status = "SKIPPED"
                actual_bp = 0
                actual_slips = 0

            actual_outcomes[
                tracking_key
            ] = {
                "status": status,
                "actual_bp": actual_bp,
                "actual_slips_spent": (
                    actual_slips
                ),
                "actual_net_cost_weth": None,
                "notes": (
                    "Derived from gameplay "
                    f"session {session_date}; "
                    f"DB task row #{matched['db_id']}."
                ),
            }

        # ====================================================
        # REROLL
        # ====================================================

        elif decision == "REROLL":
            task_id = recommendation[
                "task"
            ]

            matched = (
                find_unique_recorded_task_match(
                    session_rows=session_rows,
                    task_id=task_id,
                )
            )

            if matched is None:
                continue

            slot_rows = (
                get_recorded_slot_rows(
                    session_rows=session_rows,
                    task_slot=matched[
                        "task_slot"
                    ],
                )
            )

            later_rows = [
                row
                for row in slot_rows
                if row[
                    "roll_number"
                ] > matched[
                    "roll_number"
                ]
            ]

            if later_rows:
                status = "REROLLED"
                actual_bp = 0

                actual_slips = (
                    calculate_recorded_reroll_spend_after_row(
                        session_rows=(
                            session_rows
                        ),
                        reference_row=matched,
                    )
                )

            elif (
                matched[
                    "selected_final"
                ]
                and matched[
                    "completed"
                ]
            ):
                status = "COMPLETED"
                actual_bp = matched[
                    "reward_bp"
                ]
                actual_slips = 0

            else:
                status = "SKIPPED"
                actual_bp = 0
                actual_slips = 0

            actual_outcomes[
                tracking_key
            ] = {
                "status": status,
                "actual_bp": actual_bp,
                "actual_slips_spent": (
                    actual_slips
                ),
                "actual_net_cost_weth": None,
                "notes": (
                    "Derived from gameplay "
                    f"session {session_date}; "
                    f"DB task row #{matched['db_id']}."
                ),
            }

        # ====================================================
        # COMBO
        # ====================================================

        elif decision == "COMBO":
            task_ids = recommendation[
                "tasks"
            ]

            completed_rows = []
            matched_count = 0

            for task_id in task_ids:
                matched = (
                    find_unique_recorded_task_match(
                        session_rows=session_rows,
                        task_id=task_id,
                    )
                )

                if matched is None:
                    continue

                matched_count += 1

                if (
                    matched[
                        "selected_final"
                    ]
                    and matched[
                        "completed"
                    ]
                ):
                    completed_rows.append(
                        matched
                    )

            if matched_count == 0:
                continue

            if len(
                completed_rows
            ) == len(
                task_ids
            ):
                status = "COMPLETED"

            elif completed_rows:
                status = "PARTIAL"

            else:
                status = "SKIPPED"

            actual_bp = sum(
                (
                    row[
                        "reward_bp"
                    ]
                    or 0
                )
                for row in completed_rows
            )

            actual_outcomes[
                tracking_key
            ] = {
                "status": status,
                "actual_bp": actual_bp,
                "actual_slips_spent": None,
                "actual_net_cost_weth": None,
                "notes": (
                    "Derived from gameplay "
                    f"session {session_date}; "
                    "COMBO task completion evidence."
                ),
            }

    return actual_outcomes



def run_v09_gameplay_actual_outcome_adapter_test():
    import sqlite3

    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 GAMEPLAY ACTUAL OUTCOME ADAPTER TEST"
    )
    print(
        "============================================================"
    )

    conn = sqlite3.connect(
        ":memory:"
    )

    conn.execute(
        """
        CREATE TABLE gameplay_daily_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date TEXT NOT NULL,
            player_id TEXT NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE bounty_board_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            daily_session_id INTEGER NOT NULL,
            task_slot INTEGER NOT NULL,
            roll_number INTEGER NOT NULL,
            game TEXT,
            difficulty TEXT,
            action TEXT,
            requirement TEXT,
            reward_bp INTEGER DEFAULT 0,
            reroll_cost_slips INTEGER DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            selected_final INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    cursor = conn.execute(
        """
        INSERT INTO gameplay_daily_sessions (
            session_date,
            player_id
        )
        VALUES (?, ?)
        """,
        (
            "2026-08-27",
            "primary",
        ),
    )

    session_id = cursor.lastrowid

    # --------------------------------------------------------
    # Resolve test task IDs through the real V0.9 resolver.
    # --------------------------------------------------------

    keep_task_id = next(
        iter(
            build_daily_board(
                [
                    "Feed 1 Regular Choco",
                ]
            )
        )
    )

    reroll_task_id = next(
        iter(
            build_daily_board(
                [
                    "Craft any Rune",
                ]
            )
        )
    )

    combo_a_id = next(
        iter(
            build_daily_board(
                [
                    "Feed 10 Regular Choco to any Axie",
                ]
            )
        )
    )

    combo_b_id = next(
        iter(
            build_daily_board(
                [
                    "Feed 10 Regular Choco to any Beast Axie",
                ]
            )
        )
    )

    # --------------------------------------------------------
    # Slot 1 — KEEP completed
    # --------------------------------------------------------

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
            reroll_cost_slips,
            completed,
            selected_final
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            1,
            0,
            "App.Axie",
            "basic",
            "feed",
            "Feed 1 Regular Choco",
            25,
            0,
            1,
            1,
        ),
    )

    # --------------------------------------------------------
    # Slot 2 — REROLL followed by Buy any Axie
    # --------------------------------------------------------

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
            reroll_cost_slips,
            completed,
            selected_final
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            2,
            0,
            "Axie Origins",
            "basic",
            "craft",
            "Craft any Rune",
            12,
            0,
            0,
            0,
        ),
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
            reroll_cost_slips,
            completed,
            selected_final
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            2,
            1,
            "App.Axie",
            "intermediate",
            "buy",
            "Buy any Axie",
            200,
            10,
            1,
            1,
        ),
    )

    # --------------------------------------------------------
    # Slots 3 + 4 — COMBO tasks completed
    # --------------------------------------------------------

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
            reroll_cost_slips,
            completed,
            selected_final
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            3,
            0,
            "App.Axie",
            "intermediate",
            "feed",
            "Feed 10 Regular Choco to any Axie",
            150,
            0,
            1,
            1,
        ),
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
            reroll_cost_slips,
            completed,
            selected_final
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            4,
            0,
            "App.Axie",
            "intermediate",
            "feed",
            "Feed 10 Regular Choco to any Beast Axie",
            160,
            0,
            1,
            1,
        ),
    )

    conn.commit()

    execution_plan = {
        "recommendations": [
            {
                "decision": "KEEP",
                "task": keep_task_id,
                "reward_bp": 25,
            },
            {
                "decision": "REROLL",
                "task": reroll_task_id,
                "reward_bp": 12,
            },
            {
                "decision": "COMBO",
                "tasks": [
                    combo_a_id,
                    combo_b_id,
                ],
                "combined_bp": 310,
            },
        ],
        "reroll_results": [
            {
                "task": reroll_task_id,
                "slip_cost": 10,
            },
        ],
    }

    actual_outcomes = (
        build_actual_outcomes_from_gameplay_session(
            conn=conn,
            execution_plan=execution_plan,
            session_date="2026-08-27",
            player_id="primary",
        )
    )

    tracking = (
        build_recommendation_actual_tracking(
            execution_plan=execution_plan,
            actual_outcomes=(
                actual_outcomes
            ),
        )
    )

    by_key = {
        row[
            "tracking_key"
        ]: row
        for row in tracking
    }

    all_passed = True

    # --------------------------------------------------------
    # KEEP
    # --------------------------------------------------------

    keep_key = (
        build_recommendation_tracking_key(
            execution_plan[
                "recommendations"
            ][0]
        )
    )

    keep = by_key[
        keep_key
    ]

    keep_passed = (
        keep[
            "actual_status"
        ] == "COMPLETED"
        and keep[
            "actual_bp"
        ] == 25
        and keep[
            "recommendation_followed"
        ] is True
        and keep[
            "bp_variance"
        ] == 0
    )

    print(
        "KEEP DB adapter:",
        "PASS" if keep_passed else "FAIL",
    )
    print(
        "  Row:",
        keep,
    )

    if not keep_passed:
        all_passed = False

    # --------------------------------------------------------
    # REROLL
    # --------------------------------------------------------

    reroll_key = (
        build_recommendation_tracking_key(
            execution_plan[
                "recommendations"
            ][1]
        )
    )

    reroll = by_key[
        reroll_key
    ]

    reroll_passed = (
        reroll[
            "actual_status"
        ] == "REROLLED"
        and reroll[
            "actual_slips_spent"
        ] == 10
        and reroll[
            "slip_variance"
        ] == 0
        and reroll[
            "recommendation_followed"
        ] is True
    )

    print(
        "REROLL DB adapter:",
        (
            "PASS"
            if reroll_passed
            else "FAIL"
        ),
    )
    print(
        "  Row:",
        reroll,
    )

    if not reroll_passed:
        all_passed = False

    # --------------------------------------------------------
    # COMBO
    # --------------------------------------------------------

    combo_key = (
        build_recommendation_tracking_key(
            execution_plan[
                "recommendations"
            ][2]
        )
    )

    combo = by_key[
        combo_key
    ]

    combo_passed = (
        combo[
            "actual_status"
        ] == "COMPLETED"
        and combo[
            "actual_bp"
        ] == 310
        and combo[
            "bp_variance"
        ] == 0
        and combo[
            "recommendation_followed"
        ] is True
    )

    print(
        "COMBO DB adapter:",
        (
            "PASS"
            if combo_passed
            else "FAIL"
        ),
    )
    print(
        "  Row:",
        combo,
    )

    if not combo_passed:
        all_passed = False

    # --------------------------------------------------------
    # Missing session guardrail
    # --------------------------------------------------------

    missing_passed = False

    try:
        build_actual_outcomes_from_gameplay_session(
            conn=conn,
            execution_plan=execution_plan,
            session_date="2099-01-01",
        )

    except ValueError as exc:
        missing_passed = True

        print(
            "Missing-session guardrail: PASS"
        )
        print(
            "  Message:",
            str(exc),
        )

    else:
        print(
            "Missing-session guardrail: FAIL"
        )

    if not missing_passed:
        all_passed = False

    conn.close()

    print(
        "\nV0.9 Gameplay Actual Outcome Adapter:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed



def run_v09_recommendation_actual_tracking_test():
    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 RECOMMENDATION VS ACTUAL TEST"
    )
    print(
        "============================================================"
    )

    all_passed = True

    execution_plan = {
        "recommendations": [
            {
                "decision": "KEEP",
                "task": "test_keep",
                "reward_bp": 100,
                "economics": {
                    "economic_status": "READY",
                    "estimated_net_cost_weth": (
                        "0.00010"
                    ),
                },
            },
            {
                "decision": "COMBO",
                "tasks": [
                    "test_combo_b",
                    "test_combo_a",
                ],
                "combined_bp": 300,
                "economics": {
                    "economic_status": "READY",
                    "estimated_net_cost_weth": (
                        "0.00020"
                    ),
                },
            },
            {
                "decision": "REROLL",
                "task": "test_reroll",
                "reward_bp": 50,
            },
        ],
        "reroll_results": [
            {
                "task": "test_reroll",
                "slip_cost": 20,
            },
        ],
    }

    keep_key = (
        "KEEP::test_keep"
    )

    combo_key = (
        "COMBO::test_combo_a||test_combo_b"
    )

    reroll_key = (
        "REROLL::test_reroll"
    )

    actual_outcomes = {
        keep_key: {
            "status": "COMPLETED",
            "actual_bp": 100,
            "actual_slips_spent": 0,
            "actual_net_cost_weth": (
                "0.00009"
            ),
        },
        combo_key: {
            "status": "COMPLETED",
            "actual_bp": 300,
            "actual_slips_spent": 0,
            "actual_net_cost_weth": (
                "0.00022"
            ),
        },
        reroll_key: {
            "status": "REROLLED",
            "actual_bp": 0,
            "actual_slips_spent": 20,
        },
    }

    tracking = (
        build_recommendation_actual_tracking(
            execution_plan=execution_plan,
            actual_outcomes=(
                actual_outcomes
            ),
        )
    )

    by_key = {
        row["tracking_key"]: row
        for row in tracking
    }

    # --------------------------------------------------------
    # Test 1 — KEEP
    # --------------------------------------------------------

    keep = by_key[
        keep_key
    ]

    keep_passed = (
        keep[
            "recommendation_followed"
        ] is True
        and keep[
            "bp_variance"
        ] == 0
        and keep[
            "net_cost_variance_weth"
        ] == "-0.00001"
    )

    print(
        "KEEP actual tracking:",
        "PASS" if keep_passed else "FAIL",
    )
    print(
        "  Row:",
        keep,
    )

    if not keep_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 2 — COMBO stable identity + economics
    # --------------------------------------------------------

    combo = by_key[
        combo_key
    ]

    combo_passed = (
        combo[
            "recommendation_followed"
        ] is True
        and combo[
            "planned_bp"
        ] == 300
        and combo[
            "bp_variance"
        ] == 0
        and combo[
            "net_cost_variance_weth"
        ] == "0.00002"
    )

    print(
        "COMBO actual tracking:",
        (
            "PASS"
            if combo_passed
            else "FAIL"
        ),
    )
    print(
        "  Row:",
        combo,
    )

    if not combo_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 3 — REROLL slips
    # --------------------------------------------------------

    reroll = by_key[
        reroll_key
    ]

    reroll_passed = (
        reroll[
            "recommendation_followed"
        ] is True
        and reroll[
            "planned_bp"
        ] is None
        and reroll[
            "planned_reroll_slips"
        ] == 20
        and reroll[
            "slip_variance"
        ] == 0
    )

    print(
        "REROLL actual tracking:",
        (
            "PASS"
            if reroll_passed
            else "FAIL"
        ),
    )
    print(
        "  Row:",
        reroll,
    )

    if not reroll_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 4 — Missing actual stays PENDING
    # --------------------------------------------------------

    pending = (
        build_recommendation_actual_tracking(
            execution_plan=execution_plan,
            actual_outcomes={},
        )
    )

    pending_passed = all(
        row[
            "actual_status"
        ] == "PENDING"
        and row[
            "recommendation_followed"
        ] is None
        for row in pending
    )

    print(
        "Pending-outcome behavior:",
        (
            "PASS"
            if pending_passed
            else "FAIL"
        ),
    )

    if not pending_passed:
        all_passed = False

    # --------------------------------------------------------
    # Test 5 — Invalid status guardrail
    # --------------------------------------------------------

    invalid_passed = False

    try:
        build_recommendation_actual_tracking(
            execution_plan=execution_plan,
            actual_outcomes={
                keep_key: {
                    "status": (
                        "MADE_UP_STATUS"
                    ),
                },
            },
        )

    except ValueError as exc:
        invalid_passed = True

        print(
            "Invalid-status guardrail: PASS"
        )
        print(
            "  Message:",
            str(exc),
        )

    else:
        print(
            "Invalid-status guardrail: FAIL"
        )

    if not invalid_passed:
        all_passed = False

    print(
        "\nV0.9 Recommendation vs Actual:",
        "PASS" if all_passed else "FAIL",
    )

    return all_passed




def run_rank_push_strategy_test():
    task_id = "harvest_5"

    task = BOUNTY_TASK_CATALOG[
        "axie_quest_harvest_5"
    ]

    conserve_context = build_strategy_context(
        strategy_mode="Conserve",
        minimum_reserve=20,
    )

    rank_push_context = build_strategy_context(
        strategy_mode="Rank Push",
        minimum_reserve=20,
        current_rank=412,
        current_weekly_bp=1000,
        days_remaining=3,
    )

    rank_one_context = build_strategy_context(
        strategy_mode="Rank Push",
        minimum_reserve=20,
        current_rank=1,
        current_weekly_bp=1000,
        days_remaining=3,
    )

    conserve_result = (
        evaluate_task_reroll_with_strategy(
            task_id=task_id,
            task=task,
            reroll_number=1,
            slip_balance=25,
            strategy_context=conserve_context,
        )
    )

    rank_push_result = (
        evaluate_task_reroll_with_strategy(
            task_id=task_id,
            task=task,
            reroll_number=1,
            slip_balance=25,
            strategy_context=rank_push_context,
        )
    )

    rank_one_result = (
        evaluate_task_reroll_with_strategy(
            task_id=task_id,
            task=task,
            reroll_number=1,
            slip_balance=25,
            strategy_context=rank_one_context,
        )
    )

    print("\nSTRATEGY TEST")

    print(
        "Rank 1 target:",
        rank_one_context["rank_bonus_target"],
    )

    print(
        "Conserve:",
        conserve_result["reroll_status"],
        "| reserve:",
        conserve_result[
            "effective_minimum_reserve"
        ],
    )

    print(
        "Rank Push — Rank 412:",
        rank_push_result["reroll_status"],
        "| reserve:",
        rank_push_result[
            "effective_minimum_reserve"
        ],
    )

    print(
        "Rank Push reason:",
        rank_push_result[
            "strategy_reason"
        ],
    )


    print(
        "Rank Push — Rank 1:",
        rank_one_result["reroll_status"],
        "| reserve:",
        rank_one_result[
            "effective_minimum_reserve"
        ],
    )




def run_v09_integration_validation(
    db_path,
):
    """
    Run the complete V0.9 Bounty Optimizer validation suite.

    Includes:
    - all V0.9 unit/integration tests;
    - production-backed Axie qualification tests;
    - production historical task-resolution coverage;
    - current daily-plan regression;
    - production optimizer-history mutation guardrail.

    Synthetic persistence tests use in-memory databases.
    Genuine production optimizer-history row counts must be
    unchanged before and after this validation.
    """

    import contextlib
    import io
    import sqlite3

    print(
        "\n"
        "============================================================"
    )
    print(
        "AXIEOS V0.9 FINAL INTEGRATION VALIDATION"
    )
    print(
        "============================================================"
    )

    # ========================================================
    # Validation catalog
    # ========================================================

    test_groups = [
        (
            "REQUIREMENTS & AXIE QUALIFICATION",
            [
                (
                    "Bounty requirement model",
                    run_v09_bounty_requirement_model_test,
                    False,
                ),
                (
                    "Board Axie enrichment",
                    run_v09_board_axie_enrichment_test,
                    True,
                ),
                (
                    "Owned Axie candidates",
                    run_v09_owned_axie_candidate_test,
                    True,
                ),
                (
                    "Advanced requirements",
                    run_v09_advanced_requirement_model_test,
                    True,
                ),
                (
                    "Parameterized Axie catalog",
                    run_v09_parameterized_axie_catalog_test,
                    False,
                ),
                (
                    "Recommendation Axie candidates",
                    run_v09_recommendation_axie_candidate_test,
                    True,
                ),
                (
                    "Task-name resolution",
                    run_v09_task_name_resolution_test,
                    False,
                ),
                (
                    "Parameterized task resolution",
                    run_v09_parameterized_task_resolution_test,
                    False,
                ),
                (
                    "Daily-board resolution",
                    run_v09_daily_board_resolution_test,
                    False,
                ),
                (
                    "Optimizer Axie integration",
                    run_v09_optimizer_axie_integration_test,
                    True,
                ),
            ],
        ),
        (
            "INVENTORY, SLIPS & INPUT",
            [
                (
                    "Gameplay inventory ledger",
                    run_v09_gameplay_inventory_ledger_test,
                    False,
                ),
                (
                    "Optimizer inventory source",
                    run_v09_optimizer_inventory_source_test,
                    False,
                ),
                (
                    "Structured slip state",
                    run_v09_structured_slip_state_test,
                    False,
                ),
                (
                    "Projected slip state",
                    run_v09_projected_slip_state_test,
                    False,
                ),
                (
                    "Structured inventory",
                    run_v09_structured_inventory_test,
                    False,
                ),
                (
                    "Daily-input validation",
                    run_v09_daily_input_validation_test,
                    False,
                ),
                (
                    "Reserve-aware optimizer",
                    run_v09_reserve_aware_optimizer_test,
                    False,
                ),
            ],
        ),
        (
            "BOUNTY ECONOMICS",
            [
                (
                    "Economics model",
                    run_v09_bounty_economics_model_test,
                    False,
                ),
                (
                    "KEEP economics integration",
                    run_v09_keep_economics_integration_test,
                    False,
                ),
                (
                    "COMBO economics integration",
                    run_v09_combo_economics_integration_test,
                    False,
                ),
            ],
        ),
        (
            "TRACKING & PERSISTENCE",
            [
                (
                    "Recommendation vs actual",
                    run_v09_recommendation_actual_tracking_test,
                    False,
                ),
                (
                    "Gameplay actual-outcome adapter",
                    run_v09_gameplay_actual_outcome_adapter_test,
                    False,
                ),
                (
                    "Optimizer persistence",
                    run_v09_optimizer_persistence_test,
                    False,
                ),
                (
                    "Optimizer reconciliation",
                    run_v09_optimizer_reconciliation_test,
                    False,
                ),
                (
                    "Explicit optimizer save",
                    run_v09_explicit_optimizer_save_test,
                    False,
                ),
            ],
        ),
    ]

    # ========================================================
    # Production optimizer-history baseline
    # ========================================================

    production_conn = sqlite3.connect(
        db_path
    )

    try:
        before_runs = production_conn.execute(
            """
            SELECT COUNT(*)
            FROM bounty_optimizer_runs
            """
        ).fetchone()[0]

        before_decisions = production_conn.execute(
            """
            SELECT COUNT(*)
            FROM bounty_optimizer_decisions
            """
        ).fetchone()[0]

    finally:
        production_conn.close()

    print()
    print(
        "Production optimizer-history baseline:"
    )
    print(
        "  Runs:",
        before_runs,
    )
    print(
        "  Decisions:",
        before_decisions,
    )

    # ========================================================
    # Run all 25 V0.9 tests
    # ========================================================

    test_results = []
    failure_details = []

    for (
        group_name,
        tests,
    ) in test_groups:

        print()
        print(
            group_name
        )
        print(
            "-" * len(
                group_name
            )
        )

        for (
            test_name,
            test_function,
            needs_db_path,
        ) in tests:

            captured_output = io.StringIO()

            try:
                with contextlib.redirect_stdout(
                    captured_output
                ):
                    if needs_db_path:
                        result = test_function(
                            db_path
                        )
                    else:
                        result = (
                            test_function()
                        )

                passed = (
                    result is True
                )

                error_text = None

            except Exception as exc:
                passed = False

                error_text = (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

            test_results.append(
                {
                    "group": group_name,
                    "name": test_name,
                    "passed": passed,
                }
            )

            print(
                " ",
                test_name + ":",
                (
                    "PASS"
                    if passed
                    else "FAIL"
                ),
            )

            if not passed:
                captured_lines = [
                    line
                    for line
                    in captured_output
                    .getvalue()
                    .splitlines()
                    if line.strip()
                ]

                failure_details.append(
                    {
                        "group": group_name,
                        "name": test_name,
                        "error": error_text,
                        "output_tail": (
                            captured_lines[
                                -12:
                            ]
                        ),
                    }
                )

    # ========================================================
    # Production historical task-resolution validation
    # ========================================================

    production_conn = sqlite3.connect(
        db_path
    )

    try:
        historical_rows = (
            production_conn.execute(
                """
                SELECT
                    s.session_date,
                    t.id,
                    t.action,
                    t.requirement
                FROM bounty_board_tasks AS t
                JOIN gameplay_daily_sessions AS s
                  ON s.id = t.daily_session_id
                WHERE t.selected_final = 1
                ORDER BY
                    s.session_date,
                    t.task_slot
                """
            ).fetchall()
        )

    finally:
        production_conn.close()

    unresolved_historical = []

    for (
        session_date,
        row_id,
        action,
        requirement,
    ) in historical_rows:

        resolution = (
            resolve_historical_bounty_task_id(
                action=action,
                requirement=requirement,
            )
        )

        if (
            resolution.get(
                "task_id"
            )
            is None
        ):
            unresolved_historical.append(
                {
                    "session_date": (
                        session_date
                    ),
                    "db_id": row_id,
                    "action": action,
                    "requirement": requirement,
                }
            )

    historical_resolution_passed = (
        len(
            historical_rows
        ) > 0
        and not unresolved_historical
    )

    print()
    print(
        "PRODUCTION HISTORICAL RESOLUTION"
    )
    print(
        "-------------------------------"
    )
    print(
        "  Final selected tasks:",
        len(
            historical_rows
        ),
    )
    print(
        "  Unresolved:",
        len(
            unresolved_historical
        ),
    )
    print(
        "  Status:",
        (
            "PASS"
            if historical_resolution_passed
            else "FAIL"
        ),
    )

    # ========================================================
    # Normal current-plan regression
    # ========================================================

    daily_plan_output = io.StringIO()

    try:
        with contextlib.redirect_stdout(
            daily_plan_output
        ):
            current_plan = (
                run_current_daily_plan()
            )

        readiness = (
            evaluate_v1_readiness(
                current_plan
            )
        )

        daily_plan_status = (
            readiness.get(
                "v1_status"
            )
        )

        daily_plan_passed = (
            daily_plan_status
            == "READY"
        )

        daily_plan_error = None

    except Exception as exc:
        daily_plan_passed = False
        daily_plan_status = None

        daily_plan_error = (
            f"{type(exc).__name__}: "
            f"{exc}"
        )

    print()
    print(
        "CURRENT DAILY PLAN REGRESSION"
    )
    print(
        "-----------------------------"
    )
    print(
        "  Plan status:",
        daily_plan_status,
    )
    print(
        "  Status:",
        (
            "PASS"
            if daily_plan_passed
            else "FAIL"
        ),
    )

    # ========================================================
    # Verify production optimizer history was not mutated
    # ========================================================

    production_conn = sqlite3.connect(
        db_path
    )

    try:
        after_runs = production_conn.execute(
            """
            SELECT COUNT(*)
            FROM bounty_optimizer_runs
            """
        ).fetchone()[0]

        after_decisions = production_conn.execute(
            """
            SELECT COUNT(*)
            FROM bounty_optimizer_decisions
            """
        ).fetchone()[0]

    finally:
        production_conn.close()

    production_untouched = (
        before_runs == after_runs
        and before_decisions
        == after_decisions
    )

    print()
    print(
        "PRODUCTION HISTORY SAFETY"
    )
    print(
        "-------------------------"
    )
    print(
        "  Runs:",
        f"{before_runs} -> {after_runs}",
    )
    print(
        "  Decisions:",
        (
            f"{before_decisions} "
            f"-> {after_decisions}"
        ),
    )
    print(
        "  Status:",
        (
            "PASS"
            if production_untouched
            else "FAIL"
        ),
    )

    # ========================================================
    # Final summary
    # ========================================================

    passed_tests = sum(
        1
        for result in test_results
        if result[
            "passed"
        ]
    )

    total_tests = len(
        test_results
    )

    all_tests_passed = (
        passed_tests
        == total_tests
    )

    all_passed = (
        all_tests_passed
        and historical_resolution_passed
        and daily_plan_passed
        and production_untouched
    )

    print()
    print(
        "=" * 60
    )
    print(
        "V0.9 FINAL VALIDATION SUMMARY"
    )
    print(
        "=" * 60
    )

    print(
        "V0.9 tests:",
        f"{passed_tests}/{total_tests}",
        (
            "PASS"
            if all_tests_passed
            else "FAIL"
        ),
    )

    print(
        "Historical task resolution:",
        (
            "PASS"
            if historical_resolution_passed
            else "FAIL"
        ),
    )

    print(
        "Current daily plan:",
        (
            "PASS"
            if daily_plan_passed
            else "FAIL"
        ),
    )

    print(
        "Production history safety:",
        (
            "PASS"
            if production_untouched
            else "FAIL"
        ),
    )

    if failure_details:
        print()
        print(
            "FAILURE DETAILS"
        )
        print(
            "---------------"
        )

        for failure in failure_details:
            print()
            print(
                failure[
                    "group"
                ],
                "/",
                failure[
                    "name"
                ],
            )

            if (
                failure[
                    "error"
                ]
                is not None
            ):
                print(
                    "  Error:",
                    failure[
                        "error"
                    ],
                )

            if failure[
                "output_tail"
            ]:
                print(
                    "  Output tail:"
                )

                for line in failure[
                    "output_tail"
                ]:
                    print(
                        "   ",
                        line,
                    )

    if not historical_resolution_passed:
        print()
        print(
            "UNRESOLVED PRODUCTION TASKS"
        )

        for row in (
            unresolved_historical
        ):
            print(
                " ",
                row,
            )

    if (
        not daily_plan_passed
        and daily_plan_error
        is not None
    ):
        print()
        print(
            "Daily-plan error:",
            daily_plan_error,
        )

    print()
    print(
        "V0.9 Integration Validation:",
        (
            "PASS"
            if all_passed
            else "FAIL"
        ),
    )

    return all_passed






def run_current_daily_plan():
    daily_input = build_daily_input(
        board_entries=DAILY_BOARD_ENTRIES,
        inventory=DAILY_INVENTORY,
        slip_balance=DAILY_SLIP_BALANCE,
        reroll_numbers=DAILY_REROLL_NUMBERS,
       strategy_mode=DAILY_STRATEGY_MODE,
        minimum_reserve=DAILY_MINIMUM_RESERVE,
    )

    execution_plan = run_daily_optimizer(
        daily_input=daily_input,
        asset=None,
        title=f"AXIEOS DAILY BOUNTY PLAN — {DAILY_DATE}",
    )


    reconciliation = reconcile_daily_bp(
        execution_plan,
        DAILY_OBSERVED_TOTAL_BP,
    )

    print("\nBP RECONCILIATION")

    print(
        "Task BP:",
        reconciliation["task_bp"],
    )

    print(
        "Observed total BP:",
        reconciliation[
            "observed_total_bp"
        ],
    )

    print(
        "Additional BP:",
        reconciliation[
            "additional_bp"
        ],
    )

    print(
        "Task BP alone matches:",
        reconciliation[
            "matches_task_bp_only"
        ],
    )


    reroll_history_summary = (
        summarize_reroll_history(
            DAILY_REROLL_HISTORY
        )
    )

    print("\nREROLL HISTORY")

    for slot_id, result in (
        reroll_history_summary["slots"].items()
    ):
        print(
            f"{slot_id}: "
            f"{result['rerolls_used']} | "
            f"{result['slips_spent']} slips"
        )

    print(
        "Total reroll slips spent:",
        reroll_history_summary[
            "total_slips_spent"
        ],
    )


    other_slip_summary = (
        summarize_other_slip_spend(
            DAILY_OTHER_SLIP_SPEND
        )
    )


    total_recorded_slip_spend = (
        reroll_history_summary[
            "total_slips_spent"
        ]
        + other_slip_summary[
            "total_slips_spent"
        ]
    )

    calculated_ending_slips = (
        DAILY_SLIP_BALANCE
        - total_recorded_slip_spend
    )

    print("\nSLIP ACCOUNTING")

    print(
        "Starting slips:",
        DAILY_SLIP_BALANCE,
    )

    print(
        "Recorded spend:",
        total_recorded_slip_spend,
    )

    print(
        "Calculated ending slips:",
        calculated_ending_slips,
    )


    slip_difference = (
        DAILY_OBSERVED_ENDING_SLIPS
        - calculated_ending_slips
    )

    print("\nSLIP RECONCILIATION")

    print(
        "Calculated ending slips:",
        calculated_ending_slips,
    )

    print(
        "Observed ending slips:",
        DAILY_OBSERVED_ENDING_SLIPS,
    )

    print(
        "Difference:",
        slip_difference,
    )

    print(
        "Matches:",
        calculated_ending_slips
        == DAILY_OBSERVED_ENDING_SLIPS,
    )


    data_quality = build_daily_data_quality_summary(
        bp_reconciliation=reconciliation,
        slip_matches=(
            calculated_ending_slips
            == DAILY_OBSERVED_ENDING_SLIPS
        ),
    )

    print("\nDATA QUALITY")

    print(
        "Status:",
        data_quality["status"],
    )

    print(
        "Issues:",
        data_quality["issue_count"],
    )

    for issue in data_quality["issues"]:
        print(
            "-",
            issue,
        )



    print("\nOTHER SLIP SPEND")

    for item_id, result in (
        other_slip_summary["items"].items()
    ):
        print(
            f"{item_id}: "
            f"{result['quantity']} | "
            f"{result['slips_spent']} slips"
        )

    print(
        "Total other slips spent:",
        other_slip_summary[
            "total_slips_spent"
        ],
    )

    print(
        "Total recorded slips spent:",
        reroll_history_summary[
            "total_slips_spent"
        ]
        + other_slip_summary[
            "total_slips_spent"
        ],
    )


    print("\nAUG 18 OPERATIONAL SUMMARY")

    operational_summary = (
        format_daily_operational_summary(
            execution_plan=execution_plan,
            bp_reconciliation=reconciliation,
            reroll_history_summary=(
                reroll_history_summary
            ),
            other_slip_summary=(
                other_slip_summary
            ),
            starting_slips=DAILY_SLIP_BALANCE,
            ending_slips=calculated_ending_slips,
            data_quality=data_quality,
        )
    )

    for line in operational_summary:
        print(line)


    return execution_plan




if __name__ == "__main__":
    run_current_daily_plan()