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



TASK_NAME_ALIASES = {
    "Buy any Axie": "app_axie_buy_any_axie",
    "Open 1 Premium Pouch": "app_axie_open_1_premium_pouch",
    "Feed 1 Regular Choco": "app_axie_feed_1_regular_choco",
    "Release any Beast Axie": "app_axie_release_beast_axie",
    "Buy 3 Regular Choco": "app_axie_buy_3_regular_choco",
    "Craft any Rune": "origins_craft_any_rune",
    "Feed 5 Regular Choco to evolved Axie": (
        "app_axie_feed_5_regular_choco_evolved"
    ),
    "Open 3 Regular Pouches": (
        "app_axie_open_3_regular_pouches"
    ),
}


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

def check_combo_resource_availability(
    recommendation,
    inventory,
):
    if recommendation["decision"] != "COMBO":
        return None

    resource = recommendation["resource"]
    quantity_needed = recommendation[
        "quantity_needed"
    ]

    quantity_available = inventory.get(
        resource,
        0,
    )

    return {
        "resource": resource,
        "quantity_needed": quantity_needed,
        "quantity_available": quantity_available,
        "can_execute": (
            quantity_available >= quantity_needed
        ),
        "shortfall": max(
            0,
            quantity_needed - quantity_available,
        ),
    }


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

            updated["quantity_available"] = (
                availability["quantity_available"]
            )

            updated["shortfall"] = availability[
                "shortfall"
            ]

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
        updated = dict(recommendation)

        if recommendation["decision"] == "KEEP":
            task_id = recommendation["task"]
            task = task_map[task_id]

            resource = task.get("resource")

            if (
                resource is not None
                and resource in inventory
            ):
                quantity_needed = task["quantity"]

                quantity_available = inventory.get(
                    resource,
                    0,
                )

                updated["resource"] = resource
                updated["quantity_needed"] = (
                    quantity_needed
                )
                updated["quantity_available"] = (
                    quantity_available
                )

                updated["inventory_status"] = (
                    "READY"
                    if quantity_available
                    >= quantity_needed
                    else "SHORTFALL"
                )

                updated["shortfall"] = max(
                    0,
                    quantity_needed
                    - quantity_available,
                )

        updated_recommendations.append(
            updated
        )

    return updated_recommendations


def build_execution_plan(
    analysis,
    task_map,
    inventory,
    reroll_numbers,
    slip_balance,
    strategy_context,
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

    reroll_plan = (
        evaluate_board_rerolls_with_strategy(
            analysis=analysis,
            task_map=task_map,
            reroll_numbers=reroll_numbers,
            slip_balance=slip_balance,
            strategy_context=strategy_context,
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
        "reroll_results": reroll_plan[
            "reroll_results"
        ],
    }


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

            lines.append(line)

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

            lines.append(line)

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

    raise ValueError(
        f"Unknown task_name: {task_name}"
    )


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
        catalog_id = resolve_catalog_id(
            entry
        )

        task_id = resolve_task_id(
            entry,
            catalog_id,
        )

        task = BOUNTY_TASK_CATALOG[
            catalog_id
        ]

        random_class = (
            entry.get("random_class")
            if isinstance(entry, dict)
            else None
        )

        if random_class is not None:
            task = instantiate_task(
                task,
                random_class=random_class,
            )

        board[task_id] = task

    return board


def normalize_inventory(
    inventory,
):
    normalized = {}

    for resource_name, quantity in inventory.items():
        resource = RESOURCE_NAME_ALIASES.get(
            resource_name,
            resource_name,
        )

        normalized[resource] = quantity

    return normalized



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
    return {
        "board_entries": board_entries,
        "inventory": normalize_inventory(
            inventory
        ),
        "slip_balance": slip_balance,
        "reroll_numbers": reroll_numbers,
        "strategy_context": build_strategy_context(
            strategy_mode=strategy_mode,
            minimum_reserve=minimum_reserve,
            current_rank=current_rank,
            current_weekly_bp=current_weekly_bp,
            days_remaining=days_remaining,
        ),
    }


def validate_daily_input(
    daily_input,
):
    board_entries = daily_input[
        "board_entries"
    ]

    task_ids = set()

    for entry in board_entries:
        catalog_id = resolve_catalog_id(
            entry
        )

        task_id = resolve_task_id(
            entry,
            catalog_id,
        )

        if task_id in task_ids:
            raise ValueError(
                f"Duplicate task_id: {task_id}"
            )

        task_ids.add(task_id)

        if catalog_id not in BOUNTY_TASK_CATALOG:
            raise ValueError(
                f"Unknown catalog_id: {catalog_id}"
            )

    if daily_input["slip_balance"] < 0:
        raise ValueError(
            "slip_balance cannot be negative"
        )


    inventory = daily_input[
        "inventory"
    ]

    for resource, quantity in inventory.items():
        if quantity < 0:
            raise ValueError(
                f"Inventory cannot be negative: {resource}"
            )

    reroll_numbers = daily_input[
        "reroll_numbers"
    ]

    for task_id, reroll_number in (
        reroll_numbers.items()
    ):
        if task_id not in task_ids:
            raise ValueError(
                f"Unknown reroll task_id: {task_id}"
            )

        if reroll_number not in REROLL_TIERS:
            raise ValueError(
                f"Invalid reroll number: {reroll_number}"
            )

    return True





def optimize_daily_input(
    daily_input,
    asset,
):
    
    validate_daily_input(
        daily_input
    )

    board = build_daily_board(
        daily_input["board_entries"]
    )

    analysis = analyze_task_board(
        board,
        asset,
    )

    return build_execution_plan(
        analysis=analysis,
        task_map=board,
        inventory=daily_input["inventory"],
        reroll_numbers=daily_input[
            "reroll_numbers"
        ],
        slip_balance=daily_input[
            "slip_balance"
        ],
        strategy_context=daily_input[
            "strategy_context"
        ],
    )




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
):
    execution_plan = optimize_daily_input(
        daily_input=daily_input,
        asset=asset,
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