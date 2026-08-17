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


def build_v1_demo_plan():
    demo_mech_feed = instantiate_task(
        BOUNTY_TASK_CATALOG[
            "app_axie_feed_10_choco_random_class"
        ],
        random_class="mech",
    )

    demo_buy_mech = instantiate_task(
        BOUNTY_TASK_CATALOG[
            "app_axie_buy_random_class_axie"
        ],
        random_class="mech",
    )

    demo_asset = {
        "class": "mech",
        "collectible": True,
        "evolved": True,
    }

    demo_board = {
        "feed_10_choco_mech": demo_mech_feed,
        "buy_mech_axie": demo_buy_mech,
        "feed_10_choco_any": BOUNTY_TASK_CATALOG[
            "app_axie_feed_10_choco_any_axie"
        ],
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

    analysis = analyze_task_board(
        demo_board,
        demo_asset,
    )

    strategy_context = build_strategy_context(
        strategy_mode="conserve",
        minimum_reserve=20,
    )

    return build_execution_plan(
        analysis=analysis,
        task_map=demo_board,
        inventory={
            "regular_choco": 10,
            "premium_choco": 1,
        },
        reroll_numbers={},
        slip_balance=100,
        strategy_context=strategy_context,
    )



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





if __name__ == "__main__":
    run_v1_demo()

