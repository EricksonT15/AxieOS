import csv
import tempfile
from pathlib import Path
from decimal import Decimal as D
from collections import Counter, defaultdict

ROOT = Path(tempfile.gettempdir())

REGISTER = ROOT / "axieos_v013_checkpoint65_decision_register.csv"
SALES = ROOT / "axieos_v013_checkpoint67_listing_scenarios.csv"
PREVIEWS = ROOT / "axieos_v013_release_preview_observations_v1.csv"

OUTPUT = ROOT / "axieos_v013_checkpoint68_comparison_v1.csv"

def load(path):
    if not path.is_file():
        raise SystemExit(f"STOP: Missing {path}")

    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def main():
    register = load(REGISTER)
    sales = load(SALES)
    previews = load(PREVIEWS)

    if len(register) != 69 or len({
        r["axie_id"] for r in register
    }) != 69:
        raise SystemExit("STOP: Decision register mismatch.")

    scenarios = (
        "ASKING_100_PERCENT",
        "ASKING_90_PERCENT",
        "ASKING_80_PERCENT",
    )

    sale_map = {}

    for row in sales:
        key = (row["axie_id"], row["scenario"])

        if key in sale_map:
            raise SystemExit("STOP: Duplicate sale scenario.")

        if (
            row["scenario"] not in scenarios
            or row["release_approved"] != "NO"
            or row["sell_approved"] != "NO"
            or row["current_fee_verified"] != "NO"
        ):
            raise SystemExit("STOP: Unsafe sale evidence.")

        sale_map[key] = D(row["estimated_sale_net_weth"])

    if len(sale_map) != 72:
        raise SystemExit("STOP: Expected 72 sale scenarios.")

    preview_map = {r["axie_id"]: r for r in previews}
    if len(preview_map) != 3:
        raise SystemExit("STOP: Preview baseline mismatch.")

    results = []
    counts = Counter()
    net_totals = defaultdict(lambda: D("0"))

    categories = {
        "UNLISTED_ECONOMICS_RESEARCH": "FORREL_RESEARCH",
        "LISTED_ECONOMICS_RESEARCH": "SALE_RESEARCH",
        "LISTED_ORIGINS_REVIEW": "ORIGINS_PROTECTION_FIRST",
        "UNLISTED_ORIGINS_REVIEW": "ORIGINS_PROTECTION_FIRST",
        "TERRARIUM_LOCK_EXCEPTION": "LOCK_CONFLICT",
    }

    for row in register:
        axie_id = row["axie_id"]
        category = row["operational_category"]

        if category not in categories:
            raise SystemExit(
                f"STOP: Unknown category for #{axie_id}"
            )

        if (
            row["release_approved"] != "NO"
            or row["sell_approved"] != "NO"
            or row["final_decision"] != "HOLD"
        ):
            raise SystemExit(
                f"STOP: Approval conflict for #{axie_id}"
            )

        is_listed = category.startswith("LISTED_")
        sale_values = {}

        for scenario in scenarios:
            value = sale_map.get((axie_id, scenario))

            if is_listed and value is None:
                raise SystemExit(
                    f"STOP: Missing sale scenario #{axie_id}"
                )

            if not is_listed and value is not None:
                raise SystemExit(
                    f"STOP: Unexpected sale scenario #{axie_id}"
                )

            sale_values[scenario] = value

            if value is not None:
                net_totals[(category, scenario)] += value

        preview = preview_map.get(axie_id, {})
        live_status = preview.get("live_status", "")

        has_preview = live_status == "RELEASE_PREVIEW_AVAILABLE"

        if category == "TERRARIUM_LOCK_EXCEPTION":
            action = "RESOLVE_TERRARIUM_LOCK"

        elif category in (
            "LISTED_ORIGINS_REVIEW",
            "UNLISTED_ORIGINS_REVIEW",
        ):
            action = "VERIFY_ORIGINS_VALUE_FIRST"

        elif is_listed:
            action = "EVALUATE_EXISTING_MARKETPLACE_LISTING"

        else:
            action = "VERIFY_AVAILABILITY_AND_ECONOMICS"

        counts[category] += 1

        results.append({
            "axie_id": axie_id,
            "operational_category": category,
            "analysis_focus": categories[category],
            "next_action": action,
            "asking_price_weth": row["asking_price_weth"],
            "net_sale_at_100_weth": (
                str(sale_values[scenarios[0]])
                if is_listed else ""
            ),
            "net_sale_at_90_weth": (
                str(sale_values[scenarios[1]])
                if is_listed else ""
            ),
            "net_sale_at_80_weth": (
                str(sale_values[scenarios[2]])
                if is_listed else ""
            ),
            "release_break_even_net_at_90_weth": (
                str(sale_values[scenarios[1]])
                if is_listed else ""
            ),
            "live_release_preview": (
                "YES" if has_preview else "NO"
            ),
            "preview_total_min": (
                preview.get("potential_total_min", "")
                if has_preview else ""
            ),
            "preview_total_max": (
                preview.get("potential_total_max", "")
                if has_preview else ""
            ),
            "preview_fee_ron": (
                preview.get("estimated_fee_ron", "")
                if has_preview else ""
            ),
            "release_net_value_verified": "NO",
            "sale_net_value_verified": "NO",
            "economic_comparison_complete": "NO",
            "release_approved": "NO",
            "sell_approved": "NO",
            "final_decision": "HOLD",
        })

    expected = {
        "UNLISTED_ECONOMICS_RESEARCH": 30,
        "LISTED_ECONOMICS_RESEARCH": 15,
        "LISTED_ORIGINS_REVIEW": 9,
        "UNLISTED_ORIGINS_REVIEW": 14,
        "TERRARIUM_LOCK_EXCEPTION": 1,
    }

    if dict(counts) != expected:
        raise SystemExit("STOP: Category count mismatch.")

    sell_100 = net_totals[
        ("LISTED_ECONOMICS_RESEARCH", scenarios[0])
    ]
    sell_90 = net_totals[
        ("LISTED_ECONOMICS_RESEARCH", scenarios[1])
    ]

    if (
        sell_100 != D("0.008033425")
        or sell_90 != D("0.0072300825")
        or sum(r["live_release_preview"] == "YES"
               for r in results) != 1
    ):
        raise SystemExit("STOP: Financial baseline mismatch.")

    with OUTPUT.open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=list(results[0])
        )
        writer.writeheader()
        writer.writerows(results)

    print("AXIEOS V0.13 - TASK 135F")
    print("CHECKPOINT 68: SALE VS RELEASE ENGINE")

    print("\nCOVERAGE")
    print("Adults compared:", len(results))
    print("Priced marketplace listings:", 24)
    print("Live release previews:", 1)
    print("Verified release net valuations:", 0)
    print("Completed sale-vs-release comparisons:", 0)

    print("\nSELL LANE BREAK-EVEN THRESHOLDS")
    print("At 100% asking:", sell_100, "WETH")
    print("At 90% asking:", sell_90, "WETH")

    ranked = sorted(
        [
            r for r in results
            if r["operational_category"]
            == "LISTED_ECONOMICS_RESEARCH"
        ],
        key=lambda r: (
            -D(r["net_sale_at_90_weth"]),
            int(r["axie_id"])
        ),
    )

    print("\nTOP 5 SELL-LANE LISTING VALUES")
    for r in ranked[:5]:
        print(
            f"#{r['axie_id']} | "
            f"Net at 90% asking: "
            f"{r['net_sale_at_90_weth']} WETH"
        )

    print("\nSAFETY")
    print("Origin protection preserved: YES")
    print("Release approvals: 0")
    print("Sale approvals: 0")
    print("Automatic execution: DISABLED")
    print("Production database writes: 0")

    print("\nComparison report:", OUTPUT)
    print("VALIDATION: PASS")

if __name__ == "__main__":
    main()
