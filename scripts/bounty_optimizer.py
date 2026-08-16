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