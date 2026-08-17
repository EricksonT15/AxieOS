from database import connect_database



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


def build_strategy_context(
    strategy_mode,
    minimum_reserve,
    current_rank=None,
    current_weekly_bp=None,
    days_remaining=None,
):
    strategy_mode = validate_strategy_mode(
        strategy_mode
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


def evaluate_task_reroll_with_strategy(
    task_id,
    task,
    reroll_number,
    slip_balance,
    strategy_context,
):
    minimum_reserve = strategy_context[
        "minimum_reserve"
    ]

    result = evaluate_task_reroll(
        task_id=task_id,
        task=task,
        reroll_number=reroll_number,
        slip_balance=slip_balance,
        minimum_reserve=minimum_reserve,
    )

    return {
        **result,
        "strategy_mode": strategy_context[
            "strategy_mode"
        ],
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

    minimum_reserve = strategy_context[
        "minimum_reserve"
    ]

    for recommendation in analysis[
        "recommendations"
    ]:
        if recommendation["decision"] != "REROLL":
            continue

        task_id = recommendation["task"]

        reroll_number = reroll_numbers[
            task_id
        ]

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
            lines.append(
                f"KEEP: {recommendation['task']} -> "
                f"{recommendation['reward_bp']} BP"
            )

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
            else:
                lines.append(
                    f"REROLL: {task_id} -> "
                    f"reroll {reroll_result['reroll_number']} | "
                    f"{reroll_result['slip_cost']} slips | "
                    f"Master {reroll_result['master_chance'] * 100:.0f}% | "
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
            f"Slips: "
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

    ready = (
        validation["all_tasks_accounted_for"]
        and validation["no_duplicate_tasks"]
    )

    return {
        **validation,
        "v1_status": (
            "READY"
            if ready
            else "NOT_READY"
        ),
    }


def run_v1_demo():
    print("\nAXIEOS BOUNTY OPTIMIZER V1")

    for line in format_execution_summary(
        aug15_execution_plan_test
    ):
        print(line)

    print("\nActions:")

    for line in format_execution_plan(
        aug15_execution_plan_test
    ):
        print(line)

    readiness = evaluate_v1_readiness(
        aug15_execution_plan_test
    )

    print(
        "\nV1 Status:",
        readiness["v1_status"],
    )





if __name__ == "__main__":
    print("REROLL TIERS")

    for reroll_number in range(1, 11):
        tier = get_reroll_tier(reroll_number)

        print(
            f"Reroll {reroll_number}: "
            f"{tier['cost']} slips | "
            f"Basic {tier['basic']:.0%} | "
            f"Intermediate {tier['intermediate']:.0%} | "
            f"Advanced {tier['advanced']:.0%} | "
            f"Master {tier['master']:.0%}"
        )

    print()
    print("NEXT REROLL TEST")

    for rerolls_used in [0, 3, 6, 8, 10]:
        info = get_next_reroll_info(rerolls_used)

        if info is None:
            print(
                f"{rerolls_used} rerolls used: "
                "No rerolls remaining"
            )
        else:
            print(
                f"{rerolls_used} rerolls used -> "
                f"Reroll {info['reroll_number']} "
                f"costs {info['cost']} slips"
            )


    print()
    print("EMPIRICAL BP BY DIFFICULTY")

    conn = connect_database()
    difficulty_stats = get_empirical_bp_by_difficulty(conn)
    conn.close()

    for difficulty in [
        "basic",
        "intermediate",
        "advanced",
        "master",
    ]:
        stats = difficulty_stats.get(difficulty)

        if stats is None:
            print(
                f"{difficulty.title()}: "
                "No observations yet"
            )
            continue

        print(
            f"{difficulty.title()}: "
            f"n={stats['observations']} | "
            f"avg={stats['avg_bp']:.2f} BP | "
            f"min={stats['min_bp']} | "
            f"max={stats['max_bp']}"
        )


    print()
    print("EMPIRICAL BP BY ACTION")

    conn = connect_database()
    action_stats = get_empirical_bp_by_action(conn)
    conn.close()

    for action, stats in action_stats.items():
        print(
            f"{action}: "
            f"n={stats['observations']} | "
            f"avg={stats['avg_bp']:.2f} BP | "
            f"min={stats['min_bp']} | "
            f"max={stats['max_bp']}"
        )


    print()
    print("EMPIRICAL BP BY DIFFICULTY + ACTION")

    conn = connect_database()
    difficulty_action_stats = (
        get_empirical_bp_by_difficulty_action(conn)
    )
    conn.close()

    for (
        difficulty,
        action,
        observations,
        avg_bp,
        min_bp,
        max_bp,
    ) in difficulty_action_stats:
        print(
            f"{difficulty} / {action}: "
            f"n={observations} | "
            f"avg={avg_bp:.2f} BP | "
            f"min={min_bp} | "
            f"max={max_bp}"
        )


    print()
    print("TASK PROFILE TEST")

    test_profiles = [
        ("basic", "buy"),
        ("intermediate", "buy"),
        ("intermediate", "craft"),
        ("advanced", "feed"),
        ("master", "buy"),
    ]

    for difficulty, action in test_profiles:
        profile = get_difficulty_action_profile(
            difficulty_action_stats,
            difficulty,
            action,
        )

        if profile is None:
            print(
                f"{difficulty} / {action}: "
                "No observations yet"
            )
            continue

        print(
            f"{difficulty} / {action}: "
            f"n={profile['observations']} | "
            f"avg={profile['avg_bp']:.2f} BP | "
            f"range={profile['min_bp']}"
            f"-{profile['max_bp']}"
        )




    print()
    print("EXPECTED BP TEST")

    conn = connect_database()
    difficulty_stats = get_empirical_bp_by_difficulty(conn)
    conn.close()

    for rerolls_used in [0, 3, 6, 8]:
        reroll_info = get_next_reroll_info(rerolls_used)

        estimate = estimate_expected_bp(
            reroll_info,
            difficulty_stats,
        )

        print(
            f"Next reroll #{reroll_info['reroll_number']} "
            f"({reroll_info['cost']} slips)"
        )

        print(
            f"  Known expected BP: "
            f"{estimate['known_expected_bp']:.2f}"
        )

        print(
            f"  Probability covered: "
            f"{estimate['covered_probability']:.0%}"
        )

        if estimate["missing_difficulties"]:
            print(
                "  Missing data: "
                + ", ".join(
                    estimate["missing_difficulties"]
                )
            )


    print()
    print("REROLL VALUE TEST")

    test_cases = [
        (30, 0),
        (70, 6),
        (70, 8),
        (200, 0),
    ]

    for current_bp, rerolls_used in test_cases:
        value = estimate_reroll_value(
            current_bp,
            rerolls_used,
            difficulty_stats,
        )

        print(
            f"{current_bp} BP after "
            f"{rerolls_used} rerolls:"
        )

        print(
            f"  Provisional expected BP: "
            f"{value['provisional_expected_bp']:.2f}"
        )

        print(
            f"  Probability coverage: "
            f"{value['covered_probability']:.0%}"
        )

        if value["missing_difficulties"]:
            print(
                "  Missing data: "
                + ", ".join(value["missing_difficulties"])
            )

        print(
            f"  Expected gain: "
            f"{value['expected_gain']:+.2f} BP"
        )

        print(
            f"  Expected gain/slip: "
            f"{value['gain_per_slip']:+.2f}"
        )





    print()
    print("DECISION TEST")

    test_tasks = [
        {
            "name": "Buy 1 Consumable",
            "game": "App.Axie",
            "bp": 30,
            "rerolls": 0,
            "feasible": True,
            "avoided": False,
        },
        {
            "name": "Den of Mysteries Floor 3",
            "game": "Axie Den of Mysteries",
            "bp": 100,
            "rerolls": 0,
            "feasible": True,
            "avoided": False,
        },
        {
            "name": "Spend 1000 Classic Gold",
            "game": "Axie Classic",
            "bp": 100,
            "rerolls": 0,
            "feasible": False,
            "avoided": False,
        },
        {
            "name": "70 BP after 6 rerolls",
            "game": "Axie Origins",
            "bp": 70,
            "rerolls": 6,
            "feasible": True,
            "avoided": False,
        },
        {
            "name": "70 BP after 8 rerolls",
            "game": "Axie Origins",
            "bp": 70,
            "rerolls": 8,
            "feasible": True,
            "avoided": False,
        },
        {
            "name": "Buy any Axie",
            "game": "App.Axie",
            "bp": 200,
            "rerolls": 0,
            "feasible": True,
            "avoided": False,
        },
    ]
    

    for task in test_tasks:
        result = recommend_task_action(
            reward_bp=task["bp"],
            rerolls_used=task["rerolls"],
            game_name=task["game"],
            feasible=task["feasible"],
            avoided=task["avoided"],
)

        print(
            f"{task['name']}: "
            f"{result['decision']} — "
            f"{result['reason']}"
        )

        if result["decision"] in {"REROLL", "REVIEW"}:
            next_reroll = result["next_reroll"]

            print(
                f"  Next reroll: "
                f"{next_reroll['reroll_number']} "
                f"({next_reroll['cost']} slips)"
            )

            print(
                f"  Cost level: "
                f"{get_reroll_cost_level(next_reroll['cost'])}"
            )

            print(
                f"  Distribution: "
                f"{format_reroll_distribution(next_reroll)}"
            )


    print()
    print("ACTION COST CLASS TEST")

    for action in [
        "buy",
        "feed",
        "open",
        "release",
        "craft",
        "play",
        "defeat",
    ]:
        print(
            f"{action}: "
            f"{get_action_cost_class(action)}"
        )    




    print("\nBOUNTY CATALOG TEST")

    for key, task in BOUNTY_TASK_CATALOG.items():
        print(
            key,
            "->",
            task["action"],
            task["target"],
            task["reward_bp"],
            task["target_filters"],
        )
    print("\nTASK OVERLAP TEST")

    generic_buy = BOUNTY_TASK_CATALOG[
        "app_axie_buy_any_axie"
    ]

    specific_buy = BOUNTY_TASK_CATALOG[
        "app_axie_buy_random_class_axie"
    ]

    print(
        "Specific covers generic:",
        can_task_cover_task(
            specific_buy,
            generic_buy,
        ),
    )

    print(
        "Generic covers specific:",
        can_task_cover_task(
            generic_buy,
            specific_buy,
        ),
    )


    print("\nCHOCO OVERLAP TEST")

    generic_feed = BOUNTY_TASK_CATALOG[
        "app_axie_feed_10_choco_any_axie"
    ]

    specific_feed = BOUNTY_TASK_CATALOG[
        "app_axie_feed_10_choco_random_class"
    ]

    print(
        "Specific feed covers generic:",
        can_task_cover_task(
            specific_feed,
            generic_feed,
        ),
    )

    print(
        "Generic feed covers specific:",
        can_task_cover_task(
            generic_feed,
            specific_feed,
        ),
    )


    print("\nPREMIUM CHOCO CATALOG TEST")

    for key in [
        "app_axie_feed_premium_collectible",
        "app_axie_feed_premium_evolved",
    ]:
        task = BOUNTY_TASK_CATALOG[key]

        print(
            key,
            "->",
            task["resource"],
            task["quantity"],
            task["target_filters"],
        )

    print("\nASSET REQUIREMENT TEST")

    test_axie = {
        "collectible": True,
        "evolved": True,
    }

    collectible_task = BOUNTY_TASK_CATALOG[
        "app_axie_feed_premium_collectible"
    ]

    evolved_task = BOUNTY_TASK_CATALOG[
        "app_axie_feed_premium_evolved"
    ]

    print(
        "Qualifies for collectible task:",
        asset_satisfies_task(
            test_axie,
            collectible_task,
        ),
    )

    print(
        "Qualifies for evolved task:",
        asset_satisfies_task(
            test_axie,
            evolved_task,
        ),
    )


    print("\nSAME ACTION OVERLAP TEST")

    test_axie = {
        "collectible": True,
        "evolved": True,
    }

    collectible_task = BOUNTY_TASK_CATALOG[
        "app_axie_feed_premium_collectible"
    ]

    evolved_task = BOUNTY_TASK_CATALOG[
        "app_axie_feed_premium_evolved"
    ]

    print(
        "Can share one Premium Choco feed:",
        can_share_same_action(
            collectible_task,
            evolved_task,
            test_axie,
        ),
    )


    print("\nSHARED ACTION VALUE TEST")

    shared_value = score_shared_action(
        collectible_task,
        evolved_task,
        test_axie,
    )

    print(
        "Combined BP:",
        shared_value["combined_bp"],
    )

    print(
        "Resource:",
        shared_value["resource"],
    )

    print(
        "Quantity consumed:",
        shared_value["quantity"],
    )


    print("\nTASK INSTANTIATION TEST")

    mech_feed = instantiate_task(
        BOUNTY_TASK_CATALOG[
            "app_axie_feed_10_choco_random_class"
        ],
        random_class="mech",
    )

    print(
        "Resolved filters:",
        mech_feed["target_filters"],
    )

    generic_feed = BOUNTY_TASK_CATALOG[
        "app_axie_feed_10_choco_any_axie"
    ]

    mech_axie = {
        "class": "mech",
    }

    mech_overlap = score_shared_action(
        generic_feed,
        mech_feed,
        mech_axie,
    )

    print(
        "Can share one 10-Choco feed:",
        mech_overlap is not None,
    )

    if mech_overlap is not None:
        print(
            "Combined BP:",
            mech_overlap["combined_bp"],
        )

    print(
        "Resource:",
        mech_overlap["resource"],
    )

    print(
        "Quantity consumed:",
        mech_overlap["quantity"],
    )        

    plant_axie = {
        "class": "plant",
    }

    false_overlap = score_shared_action(
        generic_feed,
        mech_feed,
        plant_axie,
    )

    print(
        "Plant can falsely satisfy Mech task:",
        false_overlap is not None,
    )

    aug15_feed_tasks = {
    "generic_feed": generic_feed,
    "mech_feed": mech_feed,
}

    aug15_overlaps = find_shared_action_pairs(
        aug15_feed_tasks,
        mech_axie,
    )

    print(
        "Detected Aug 15 overlaps:",
        len(aug15_overlaps),
    )

    for overlap in aug15_overlaps:
        print(overlap)

    aug15_board_summary = summarize_task_board(
        aug15_feed_tasks
    )

    print(
        "Aug 15 test board task count:",
        aug15_board_summary["task_count"],
    )

    print(
        "Aug 15 test board total BP:",
        aug15_board_summary["total_bp"],
    )   

    if aug15_overlaps:
        savings = calculate_overlap_savings(
            aug15_feed_tasks,
            aug15_overlaps[0],
        )

        print(
            "Choco needed separately:",
            savings["separate_quantity"],
        )

        print(
            "Choco needed with overlap:",
            savings["shared_quantity"],
        )

        print(
            "Choco saved:",
            savings["quantity_saved"],
        )

        efficiency = calculate_overlap_efficiency(
            aug15_overlaps[0],
            savings,
        )

        print(
            "BP per Choco without overlap:",
            efficiency["separate_bp_per_unit"],
        )

        print(
            "BP per Choco with overlap:",
            efficiency["shared_bp_per_unit"],
        )

    aug15_analysis = analyze_task_board(
        aug15_feed_tasks,
        mech_axie,
    )

    print("\nAUG 15 BOARD ANALYSIS")

    print(
        "Task count:",
        aug15_analysis["task_count"],
    )

    print(
        "Total BP:",
        aug15_analysis["total_bp"],
    )

    print(
        "Overlap count:",
        aug15_analysis["overlap_count"],
    )

    print(
        "Overlap details:",
        aug15_analysis["overlaps"],
    )

    print(
        "Recommendations:",
        aug15_analysis["recommendations"],
    )

    keep_test_tasks = {
        "buy_any_axie": BOUNTY_TASK_CATALOG[
            "app_axie_buy_any_axie"
        ],
    }

    keep_test_analysis = analyze_task_board(
        keep_test_tasks,
        {},
    )

    print("\nKEEP TEST")

    print(
        "Recommendations:",
        keep_test_analysis["recommendations"],
    )


    mixed_test_tasks = {
    "generic_feed": generic_feed,
    "mech_feed": mech_feed,
    "buy_any_axie": BOUNTY_TASK_CATALOG[
        "app_axie_buy_any_axie"
    ],
}

mixed_test_analysis = analyze_task_board(
    mixed_test_tasks,
    mech_axie,
)

print("\nMIXED BOARD TEST")

print(
    "Task count:",
    mixed_test_analysis["task_count"],
)

print(
    "Total BP:",
    mixed_test_analysis["total_bp"],
)

print(
    "Recommendations:",
    mixed_test_analysis["recommendations"],
)

aug15_buy_mech = instantiate_task(
    BOUNTY_TASK_CATALOG[
        "app_axie_buy_random_class_axie"
    ],
    random_class="mech",
)

aug15_combo_axie = {
    "class": "mech",
    "collectible": True,
    "evolved": True,
}

aug15_full_board = {
    "feed_10_choco_mech": mech_feed,
    "buy_mech_axie": aug15_buy_mech,
    "feed_10_choco_any": generic_feed,
    "feed_premium_collectible": BOUNTY_TASK_CATALOG[
        "app_axie_feed_premium_collectible"
    ],
    "feed_premium_evolved": BOUNTY_TASK_CATALOG[
        "app_axie_feed_premium_evolved"
    ],
    "origins_battle": BOUNTY_TASK_CATALOG[
        "origins_win_vs_3_beast_bird_mech"
    ],
}

aug15_full_analysis = analyze_task_board(
    aug15_full_board,
    aug15_combo_axie,
)

print("\nAUG 15 FULL 6-TASK BOARD")

print(
    "Task count:",
    aug15_full_analysis["task_count"],
)

print(
    "Total BP:",
    aug15_full_analysis["total_bp"],
)

print(
    "Overlap count:",
    aug15_full_analysis["overlap_count"],
)

print(
    "Recommendations:",
    aug15_full_analysis["recommendations"],
)

aug15_execution_plan = summarize_execution_plan(
    aug15_full_analysis
)

print("\nAUG 15 EXECUTION PLAN")

print(
    "Bounty tasks:",
    aug15_execution_plan["task_count"],
)

print(
    "Execution actions:",
    aug15_execution_plan["action_count"],
)

print(
    "Actions saved by combos:",
    aug15_execution_plan["actions_saved"],
)


reroll_test_tasks = {
    "harvest_5": BOUNTY_TASK_CATALOG[
        "axie_quest_harvest_5"
    ],
}

reroll_test_analysis = analyze_task_board(
    reroll_test_tasks,
    {},
)


den_test_tasks = {
    "den_defeat_20_enemies": BOUNTY_TASK_CATALOG[
        "den_defeat_20_enemies"
    ],
}

den_test_analysis = analyze_task_board(
    den_test_tasks,
    {},
)


print("\nDEN AVOID TEST")

print(
    "Recommendations:",
    den_test_analysis["recommendations"],
)


decision_test_board = {
    "generic_feed": generic_feed,
    "mech_feed": mech_feed,
    "buy_any_axie": BOUNTY_TASK_CATALOG[
        "app_axie_buy_any_axie"
    ],
    "harvest_5": BOUNTY_TASK_CATALOG[
        "axie_quest_harvest_5"
    ],
    "den_defeat_20_enemies": BOUNTY_TASK_CATALOG[
        "den_defeat_20_enemies"
    ],
}

decision_test_analysis = analyze_task_board(
    decision_test_board,
    mech_axie,
)

print("\nFULL DECISION TEST")

print(
    "Task count:",
    decision_test_analysis["task_count"],
)

print(
    "Recommendations:",
    decision_test_analysis["recommendations"],
)


decision_summary = summarize_decisions(
    decision_test_analysis
)

print("\nDECISION SUMMARY")

print(
    "COMBO:",
    decision_summary["COMBO"],
)

print(
    "KEEP:",
    decision_summary["KEEP"],
)

print(
    "REROLL:",
    decision_summary["REROLL"],
)


task_coverage = summarize_task_coverage(
    decision_test_analysis
)

print("\nTASK COVERAGE SUMMARY")

print(
    "Tasks in COMBO:",
    task_coverage["COMBO"],
)

print(
    "Tasks to KEEP:",
    task_coverage["KEEP"],
)

print(
    "Tasks to REROLL:",
    task_coverage["REROLL"],
)

print(
    "Total tasks accounted for:",
    sum(task_coverage.values()),
)


bp_summary = summarize_bp_by_decision(
    decision_test_analysis
)

print("\nBP DECISION SUMMARY")

print(
    "BP in COMBO:",
    bp_summary["COMBO"],
)

print(
    "BP to KEEP:",
    bp_summary["KEEP"],
)

print(
    "BP marked for REROLL:",
    bp_summary["REROLL"],
)

print(
    "Total board BP:",
    sum(bp_summary.values()),
)


print("\nREROLL TIER TEST")

print(
    "Reroll 1:",
    REROLL_TIERS[1],
)

print(
    "Reroll 7:",
    REROLL_TIERS[7],
)

print(
    "Reroll 10:",
    REROLL_TIERS[10],
)


reroll_info_test = get_reroll_info(7)

print("\nREROLL INFO TEST")
print(reroll_info_test)


reroll_path_test = calculate_reroll_path(
    10
)

print("\nREROLL PATH TEST")

print(
    "Total slip cost:",
    reroll_path_test[
        "total_slip_cost"
    ],
)

print(
    "Cumulative Master chance:",
    round(
        reroll_path_test[
            "cumulative_master_chance"
        ] * 100,
        2,
    ),
    "%",
)


affordability_test = (
    evaluate_reroll_affordability(
        reroll_number=7,
        slip_balance=100,
    )
)

print("\nREROLL AFFORDABILITY TEST")
print(affordability_test)


path_affordability_test = (
    evaluate_reroll_path_affordability(
        max_reroll=7,
        slip_balance=100,
    )
)

print("\nREROLL PATH AFFORDABILITY TEST")
print(path_affordability_test)


max_reroll_test = get_max_affordable_reroll(
    slip_balance=100
)

print("\nMAX AFFORDABLE REROLL TEST")
print(max_reroll_test)


reroll_capacity_test = evaluate_reroll_capacity(
    slip_balance=100
)

print("\nREROLL CAPACITY TEST")

print(
    "Max affordable reroll:",
    reroll_capacity_test[
        "max_affordable_reroll"
    ],
)

print(
    "Slips spent:",
    reroll_capacity_test[
        "slips_spent"
    ],
)

print(
    "Remaining slips:",
    reroll_capacity_test[
        "remaining_slips"
    ],
)

print(
    "Cumulative Master chance:",
    round(
        reroll_capacity_test[
            "cumulative_master_chance"
        ] * 100,
        2,
    ),
    "%",
)


reserve_test = get_max_reroll_with_reserve(
    slip_balance=100,
    minimum_reserve=20,
)

print("\nREROLL RESERVE TEST")
print(reserve_test)


reserve_capacity_test = (
    evaluate_reroll_capacity_with_reserve(
        slip_balance=100,
        minimum_reserve=20,
    )
)

print("\nRESERVE CAPACITY TEST")

print(
    "Max reroll:",
    reserve_capacity_test[
        "max_affordable_reroll"
    ],
)

print(
    "Slips spent:",
    reserve_capacity_test[
        "slips_spent"
    ],
)

print(
    "Remaining slips:",
    reserve_capacity_test[
        "remaining_slips"
    ],
)

print(
    "Cumulative Master chance:",
    round(
        reserve_capacity_test[
            "cumulative_master_chance"
        ] * 100,
        2,
    ),
    "%",
)


next_reroll_test = evaluate_next_reroll(
    reroll_number=7,
    slip_balance=100,
    minimum_reserve=20,
)

print("\nNEXT REROLL TEST")
print(next_reroll_test)


blocked_reroll_test = evaluate_next_reroll(
    reroll_number=9,
    slip_balance=100,
    minimum_reserve=20,
)

print("\nBLOCKED REROLL TEST")
print(blocked_reroll_test)


reroll_action_test = check_next_reroll_guardrail(
    reroll_number=7,
    slip_balance=100,
    minimum_reserve=20,
)

blocked_action_test = check_next_reroll_guardrail(
    reroll_number=9,
    slip_balance=100,
    minimum_reserve=20,
)

print("\nREROLL GUARDRAIL TEST")
print(reroll_action_test)

print("\nBLOCKED GUARDRAIL TEST")
print(blocked_action_test)


task_reroll_allowed_test = evaluate_task_reroll(
    task_id="harvest_5",
    task=BOUNTY_TASK_CATALOG[
        "axie_quest_harvest_5"
    ],
    reroll_number=7,
    slip_balance=100,
    minimum_reserve=20,
)

task_reroll_blocked_test = evaluate_task_reroll(
    task_id="harvest_5",
    task=BOUNTY_TASK_CATALOG[
        "axie_quest_harvest_5"
    ],
    reroll_number=9,
    slip_balance=100,
    minimum_reserve=20,
)

print("\nTASK REROLL ALLOWED TEST")
print(task_reroll_allowed_test)

print("\nTASK REROLL BLOCKED TEST")
print(task_reroll_blocked_test)


task_keep_test = evaluate_task_reroll(
    task_id="buy_any_axie",
    task=BOUNTY_TASK_CATALOG[
        "app_axie_buy_any_axie"
    ],
    reroll_number=7,
    slip_balance=100,
    minimum_reserve=20,
)

print("\nTASK KEEP TEST")
print(task_keep_test)


board_reroll_test = evaluate_board_rerolls(
    analysis=decision_test_analysis,
    task_map=decision_test_board,
    reroll_number=7,
    slip_balance=100,
    minimum_reserve=20,
)

print("\nBOARD REROLL TEST")

for result in board_reroll_test:
    print(result)


sequential_reroll_test = (
    evaluate_board_rerolls_sequentially(
        analysis=decision_test_analysis,
        task_map=decision_test_board,
        reroll_number=7,
        slip_balance=100,
        minimum_reserve=20,
    )
)

print("\nSEQUENTIAL BOARD REROLL TEST")

print(
    "Starting slips:",
    sequential_reroll_test["starting_slips"],
)

for result in sequential_reroll_test[
    "reroll_results"
]:
    print(result)

print(
    "Ending slips:",
    sequential_reroll_test["ending_slips"],
)


reroll_numbers_test = {
    "harvest_5": 4,
    "den_defeat_20_enemies": 7,
}

per_task_reroll_test = (
    evaluate_board_rerolls_by_task(
        analysis=decision_test_analysis,
        task_map=decision_test_board,
        reroll_numbers=reroll_numbers_test,
        slip_balance=100,
        minimum_reserve=20,
    )
)

print("\nPER-TASK REROLL TEST")

print(
    "Starting slips:",
    per_task_reroll_test["starting_slips"],
)

for result in per_task_reroll_test[
    "reroll_results"
]:
    print(result)

print(
    "Ending slips:",
    per_task_reroll_test["ending_slips"],
)


mixed_guardrail_numbers = {
    "harvest_5": 4,
    "den_defeat_20_enemies": 9,
}

mixed_guardrail_test = (
    evaluate_board_rerolls_by_task(
        analysis=decision_test_analysis,
        task_map=decision_test_board,
        reroll_numbers=mixed_guardrail_numbers,
        slip_balance=100,
        minimum_reserve=20,
    )
)

print("\nMIXED GUARDRAIL TEST")

print(
    "Starting slips:",
    mixed_guardrail_test["starting_slips"],
)

for result in mixed_guardrail_test[
    "reroll_results"
]:
    print(result)

print(
    "Ending slips:",
    mixed_guardrail_test["ending_slips"],
)


mixed_reroll_summary = summarize_board_rerolls(
    mixed_guardrail_test
)

print("\nBOARD REROLL SUMMARY")

print(
    "Rerolls considered:",
    mixed_reroll_summary[
        "rerolls_considered"
    ],
)

print(
    "Rerolls allowed:",
    mixed_reroll_summary[
        "rerolls_allowed"
    ],
)

print(
    "Rerolls blocked:",
    mixed_reroll_summary[
        "rerolls_blocked"
    ],
)

print(
    "Slips spent:",
    mixed_reroll_summary[
        "slips_spent"
    ],
)

print(
    "Starting slips:",
    mixed_reroll_summary[
        "starting_slips"
    ],
)

print(
    "Ending slips:",
    mixed_reroll_summary[
        "ending_slips"
    ],
)


print(
    "Allowed tasks:",
    mixed_reroll_summary[
        "allowed_tasks"
    ],
)

print(
    "Blocked tasks:",
    mixed_reroll_summary[
        "blocked_tasks"
    ],
)


strategy_mode_test = validate_strategy_mode(
    "conserve"
)

print("\nSTRATEGY MODE TEST")
print(strategy_mode_test)


strategy_context_test = build_strategy_context(
    strategy_mode="conserve",
    minimum_reserve=20,
)

print("\nSTRATEGY CONTEXT TEST")
print(strategy_context_test)


strategy_reroll_test = (
    evaluate_task_reroll_with_strategy(
        task_id="harvest_5",
        task=BOUNTY_TASK_CATALOG[
            "axie_quest_harvest_5"
        ],
        reroll_number=7,
        slip_balance=100,
        strategy_context=strategy_context_test,
    )
)

print("\nSTRATEGY REROLL TEST")
print(strategy_reroll_test)


print("\nRANK BONUS TEST")

print(
    "Rank 412:",
    get_rank_bonus(412),
)

print(
    "Rank 218:",
    get_rank_bonus(218),
)

print(
    "Rank 1200:",
    get_rank_bonus(1200),
)

print(
    "Rank 4000:",
    get_rank_bonus(4000),
)


print("\nNEXT RANK BONUS TARGET TEST")

print(
    "Rank 412:",
    get_next_rank_bonus_target(412),
)

print(
    "Rank 1200:",
    get_next_rank_bonus_target(1200),
)

print(
    "Rank 1:",
    get_next_rank_bonus_target(1),
)


rank_push_context_test = build_strategy_context(
    strategy_mode="rank_push",
    minimum_reserve=20,
    current_rank=412,
    current_weekly_bp=16189,
    days_remaining=2,
)

print("\nRANK PUSH CONTEXT TEST")
print(rank_push_context_test)


print("\nRANK PUSH VALIDATION TEST")

try:
    build_strategy_context(
        strategy_mode="rank_push",
        minimum_reserve=20,
    )
except ValueError as error:
    print(error)


weekly_context_test = build_strategy_context(
    strategy_mode="rank_push",
    minimum_reserve=20,
    current_rank=412,
    current_weekly_bp=16189,
    days_remaining=2,
)

print("\nWEEKLY STRATEGY CONTEXT TEST")
print(weekly_context_test)


print("\nRANK PUSH COMPLETE VALIDATION TEST")

try:
    build_strategy_context(
        strategy_mode="rank_push",
        minimum_reserve=20,
        current_rank=412,
        current_weekly_bp=16189,
    )
except ValueError as error:
    print(error)


strategy_board_test = (
    evaluate_board_rerolls_with_strategy(
        analysis=decision_test_analysis,
        task_map=decision_test_board,
        reroll_numbers={
            "harvest_5": 4,
            "den_defeat_20_enemies": 7,
        },
        slip_balance=100,
        strategy_context=strategy_context_test,
    )
)

print("\nSTRATEGY BOARD REROLL TEST")

print(
    "Strategy:",
    strategy_board_test["strategy_mode"],
)

print(
    "Starting slips:",
    strategy_board_test["starting_slips"],
)

for result in strategy_board_test[
    "reroll_results"
]:
    print(result)

print(
    "Ending slips:",
    strategy_board_test["ending_slips"],
)


rank_push_board_test = (
    evaluate_board_rerolls_with_strategy(
        analysis=decision_test_analysis,
        task_map=decision_test_board,
        reroll_numbers={
            "harvest_5": 4,
            "den_defeat_20_enemies": 7,
        },
        slip_balance=100,
        strategy_context=rank_push_context_test,
    )
)

print("\nRANK PUSH BOARD TEST")

print(
    "Strategy:",
    rank_push_board_test["strategy_mode"],
)

print(
    "Current rank:",
    rank_push_context_test["current_rank"],
)

print(
    "Target rank:",
    rank_push_context_test[
        "rank_bonus_target"
    ]["target_rank"],
)

print(
    "Potential bonus increase:",
    rank_push_context_test[
        "rank_bonus_target"
    ]["bonus_increase_baxs"],
    "bAXS",
)

print(
    "Ending slips:",
    rank_push_board_test["ending_slips"],
)


inventory_test = {
    "regular_choco": 6,
    "premium_choco": 1,
}

regular_combo = (
    aug15_full_analysis["recommendations"][0]
)

regular_inventory_test = (
    check_combo_resource_availability(
        regular_combo,
        inventory_test,
    )
)

print("\nCOMBO INVENTORY TEST")
print(regular_inventory_test)


all_combo_inventory_test = (
    evaluate_combo_inventory(
        analysis=aug15_full_analysis,
        inventory=inventory_test,
    )
)

print("\nALL COMBO INVENTORY TEST")

for result in all_combo_inventory_test:
    print(result)


combo_inventory_summary = (
    summarize_combo_inventory(
        all_combo_inventory_test
    )
)

print("\nCOMBO INVENTORY SUMMARY")

print(
    "Combos considered:",
    combo_inventory_summary[
        "combos_considered"
    ],
)

print(
    "Combos executable:",
    combo_inventory_summary[
        "combos_executable"
    ],
)

print(
    "Combos blocked:",
    combo_inventory_summary[
        "combos_blocked"
    ],
)

print(
    "Resource shortfalls:",
    combo_inventory_summary[
        "resource_shortfalls"
    ],
)


inventory_recommendation_test = (
    add_inventory_to_recommendations(
        analysis=aug15_full_analysis,
        inventory=inventory_test,
    )
)

print("\nINVENTORY-AWARE RECOMMENDATIONS")

for recommendation in (
    inventory_recommendation_test
):
    print(recommendation)



execution_plan_test = build_execution_plan(
    analysis=decision_test_analysis,
    task_map=decision_test_board,
    inventory=inventory_test,
    reroll_numbers={
        "harvest_5": 4,
        "den_defeat_20_enemies": 7,
    },
    slip_balance=100,
    strategy_context=strategy_context_test,
)

print("\nINTEGRATED EXECUTION PLAN")

print(
    "Strategy:",
    execution_plan_test["strategy_mode"],
)

print(
    "Starting slips:",
    execution_plan_test["starting_slips"],
)

print("\nRecommendations:")

for recommendation in execution_plan_test[
    "recommendations"
]:
    print(recommendation)

print("\nReroll results:")

for result in execution_plan_test[
    "reroll_results"
]:
    print(result)

print(
    "\nEnding slips:",
    execution_plan_test["ending_slips"],
)


aug15_execution_plan_test = build_execution_plan(
    analysis=aug15_full_analysis,
    task_map=aug15_full_board,
    inventory={
        "regular_choco": 10,
        "premium_choco": 1,
    },
    reroll_numbers={},
    slip_balance=100,
    strategy_context=strategy_context_test,
)

print("\nAUG 15 END-TO-END PLAN")

print(
    "Strategy:",
    aug15_execution_plan_test["strategy_mode"],
)

print(
    "Starting slips:",
    aug15_execution_plan_test["starting_slips"],
)

print("\nRecommendations:")

for recommendation in aug15_execution_plan_test[
    "recommendations"
]:
    print(recommendation)

print(
    "\nEnding slips:",
    aug15_execution_plan_test["ending_slips"],
)


print("\nAUG 15 PLAN SUMMARY")

print(
    "Bounty tasks:",
    aug15_execution_plan_test[
        "task_count"
    ],
)

print(
    "Total BP:",
    aug15_execution_plan_test[
        "total_bp"
    ],
)

print(
    "Execution actions:",
    aug15_execution_plan_test[
        "action_count"
    ],
)

print(
    "Actions saved:",
    aug15_execution_plan_test[
        "actions_saved"
    ],
)


readable_plan_test = format_execution_plan(
    execution_plan_test
)

print("\nHUMAN-READABLE EXECUTION PLAN")

for line in readable_plan_test:
    print(line)


readable_summary_test = format_execution_summary(
    execution_plan_test
)

print("\nDAILY BOUNTY PLAN")

for line in readable_summary_test:
    print(line)

print("\nActions:")

for line in format_execution_plan(
    execution_plan_test
):
    print(line)


print("\nAUG 15 DAILY BOUNTY PLAN")

for line in format_execution_summary(
    aug15_execution_plan_test
):
    print(line)

print("\nActions:")

for line in format_execution_plan(
    aug15_execution_plan_test
):
    print(line)


plan_validation_test = validate_execution_plan(
    aug15_execution_plan_test
)

print("\nEXECUTION PLAN VALIDATION TEST")
print(plan_validation_test)


v1_readiness_test = evaluate_v1_readiness(
    aug15_execution_plan_test
)

print("\nBOUNTY OPTIMIZER V1 READINESS TEST")
print(v1_readiness_test)

run_v1_demo()