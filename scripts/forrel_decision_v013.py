import csv
import tempfile
from pathlib import Path
from decimal import Decimal
from collections import Counter

ROOT = Path(tempfile.gettempdir())

ROSTER = ROOT / "axieos_v013_protection_roster_v4.csv"
REGISTER = ROOT / "axieos_v013_checkpoint65_decision_register.csv"

OUTPUT = ROOT / "axieos_v013_task135f_portfolio_v1.csv"
QUEUE = ROOT / "axieos_v013_task135f_work_queue_v1.csv"

def read_csv(path):
    if not path.is_file():
        raise SystemExit(f"Missing input: {path}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def main():
    roster = read_csv(ROSTER)
    register = read_csv(REGISTER)

    owned = {r["axie_id"]: r for r in roster}
    reviews = {r["axie_id"]: r for r in register}

    if (
        len(roster) != 160 or len(owned) != 160
        or len(register) != 69 or len(reviews) != 69
    ):
        raise SystemExit("STOP: Inventory baseline mismatch.")

    assignments = {
        axie_id
        for axie_id, r in owned.items()
        if r["terrarium_plot"]
    }

    eggs = {
        axie_id
        for axie_id, r in owned.items()
        if r["protection_status"] == "EGG_PROTECTED"
    }

    if not (
        len(assignments) == 90
        and eggs == {"12266445"}
        and not (assignments & eggs)
        and set(reviews) == set(owned) - assignments - eggs
    ):
        raise SystemExit("STOP: Protection boundary mismatch.")

    rules = {
        "TERRARIUM_LOCK_EXCEPTION": (
            "REVIEW", 1, "LOCK_CONFLICT",
            "Reported Terrarium lock conflicts with assignment snapshot",
            "Reconcile live lock; do not change registration"
        ),
        "LISTED_ORIGINS_REVIEW": (
            "ORIGINS", 2, "GAMEPLAY_AND_LISTING_REVIEW",
            "Listed Axie has unresolved Origins value",
            "Assess active cards and listing before any action"
        ),
        "UNLISTED_ORIGINS_REVIEW": (
            "ORIGINS", 3, "GAMEPLAY_REVIEW",
            "Possible Origins team, synergy, or build value",
            "Confirm gameplay role and active cards"
        ),
        "UNLISTED_ECONOMICS_RESEARCH": (
            "FORREL", 4, "RESEARCH_ONLY",
            "Not assigned in captured plots; availability unverified",
            "Compare release preview with realistic resale value"
        ),
        "LISTED_ECONOMICS_RESEARCH": (
            "SELL", 5, "LISTING_EVALUATION",
            "Existing displayed asking price; sale not executed",
            "Assess listing price, net proceeds, and demand"
        ),
    }

    results = []
    counts = Counter()
    asking_total = Decimal("0")

    for axie_id, original in owned.items():
        status = original["protection_status"]
        review = reviews.get(axie_id)

        price = ""
        reference = ""

        if status == "COLLECTIBLE_PROTECTED":
            if axie_id not in assignments:
                raise SystemExit("Unassigned collectible conflict.")

            lane = "RETAIN"
            priority = 9
            decision_status = "PROTECTED"
            reason = "Collectible and active Terrarium assignment"
            next_step = "Maintain collectible and assignment protection"

        elif status == "TERRARIUM_ASSIGNED_PROTECTED":
            if axie_id not in assignments:
                raise SystemExit("Terrarium assignment conflict.")

            lane = "RETAIN"
            priority = 9
            decision_status = "PROTECTED"
            reason = "Current Terrarium assignment"
            next_step = "Preserve deployment and review productivity"

        elif status == "EGG_PROTECTED":
            if axie_id != "12266445":
                raise SystemExit("Unexpected egg.")

            lane = "RETAIN"
            priority = 9
            decision_status = "PROTECTED"
            reason = "Unhatched Axie; adult attributes unknown"
            next_step = "Refresh adult metadata after hatching"

        elif status == "ASSIGNMENT_REVIEW_REQUIRED":
            if not review:
                raise SystemExit(f"Missing review: #{axie_id}")

            category = review["operational_category"]

            if category not in rules:
                raise SystemExit(
                    f"Unexpected review category: {category}"
                )

            (
                lane, priority, decision_status,
                reason, next_step
            ) = rules[category]

            price = review["asking_price_weth"]
            reference = review["reference_mementos"]

            if category.startswith("LISTED_"):
                if not price or Decimal(price) <= 0:
                    raise SystemExit(
                        f"Missing listed price: #{axie_id}"
                    )
                asking_total += Decimal(price)
            elif price:
                raise SystemExit(
                    f"Unexpected asking price: #{axie_id}"
                )

            if review["final_decision"] != "HOLD":
                raise SystemExit(
                    f"Unexpected decision: #{axie_id}"
                )

        else:
            raise SystemExit(
                f"Unknown protection state: #{axie_id}"
            )

        counts[lane] += 1

        results.append({
            "axie_id": axie_id,
            "class": original["axie_class"],
            "level": original["level"],
            "breed_count": original["breed_count"],
            "collections": original["collections"],
            "terrarium_plot": original["terrarium_plot"],
            "origins_role": original["origins_team_role"],
            "analysis_lane": lane,
            "decision_status": decision_status,
            "priority": priority,
            "explanation": reason,
            "next_action": next_step,
            "asking_price_weth": price,
            "reference_mementos": reference,
            "market_net_proceeds_verified": "NO",
            "release_net_proceeds_verified": "NO",
            "release_approved": "NO",
            "sell_approved": "NO",
            "automatic_execution": "DISABLED",
        })

    expected = {
        "RETAIN": 91,
        "ORIGINS": 23,
        "FORREL": 30,
        "SELL": 15,
        "REVIEW": 1,
    }

    if (
        dict(counts) != expected
        or asking_total != Decimal("0.01249")
        or len(results) != 160
        or not all(
            r["release_approved"] == "NO"
            and r["sell_approved"] == "NO"
            for r in results
        )
    ):
        raise SystemExit("STOP: Optimizer safety validation failed.")

    results.sort(
        key=lambda r: (
            r["priority"],
            int(r["axie_id"])
        )
    )

    queue = [
        r for r in results
        if r["analysis_lane"] != "RETAIN"
    ]

    for path, dataset in (
        (OUTPUT, results),
        (QUEUE, queue),
    ):
        with path.open(
            "w", encoding="utf-8-sig", newline=""
        ) as f:
            writer = csv.DictWriter(
                f, fieldnames=list(dataset[0])
            )
            writer.writeheader()
            writer.writerows(dataset)

    print("AXIEOS V0.13 - TASK 135F")
    print("CHECKPOINT 66: EXPLAINABLE OPTIMIZER V1")

    print("\nPORTFOLIO LANES")
    for lane, expected_count in expected.items():
        print(f"{lane}: {counts[lane]}")

    print("\nGROSS DISPLAYED ASKING VALUE")
    print(format(asking_total, "f"), "WETH")

    print("\nFIRST 10 REVIEW PRIORITIES")
    for r in queue[:10]:
        print(
            f"#{r['axie_id']} | "
            f"{r['analysis_lane']} | "
            f"{r['decision_status']} | "
            f"{r['next_action']}"
        )

    print("\nSAFETY")
    print("Release approvals: 0")
    print("Sell approvals: 0")
    print("Automatic execution: DISABLED")
    print("Production database writes: 0")

    print("\nPortfolio matrix:", OUTPUT)
    print("Action research queue:", QUEUE)
    print("VALIDATION: PASS")

if __name__ == "__main__":
    main()
