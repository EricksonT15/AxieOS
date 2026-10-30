import csv
import json
from pathlib import Path
from datetime import date

base = Path.cwd() / "reports" / "axieos_v013"
out = base / "checkpoint95"
report = out / "dojo_weekly_register_5.csv"

if report.exists():
    raise SystemExit(
        "STOP: Register already exists. "
        "Preserving previous records."
    )

# October 27, 2026 user-provided Dojo screenshot.
# Assignment to a specific land plot is not yet verified.
roster = [
    ("12148372", "Jinx2", 18, 0,
     "GENERAL_TRAINING", 19, "REVIEW_SOON"),
    ("7140614", "", 17, 0,
     "GENERAL_TRAINING", 19, "CONTINUE"),
    ("12213537", "ForRel", 15, 1,
     "FORREL_PAUSED", 19, "CONTINUE_AXP"),
    ("12198498", "Beecher1", 14, 1,
     "ORIGINS_PROTECTED", 19, "PROTECT"),
    ("3212156", "ForRel Pilot", 5, 0,
     "FORREL_ACTIVE_PILOT", 9, "CONTINUE_PILOT"),
]

if len(roster) != 5 or len({r[0] for r in roster}) != 5:
    raise SystemExit("STOP: Dojo roster mismatch")

rows = []

for axie_id, name, level, evolved, role, milestone, action in roster:
    if not 1 <= level < milestone:
        raise SystemExit(f"STOP: Level validation #{axie_id}")

    rows.append({
        "axie_id": axie_id,
        "name": name,
        "last_observed_level": level,
        "evolved_parts": evolved,
        "observation_date": "2026-10-27",
        "training_status": "TRAINING",
        "specific_plot_verified": "NO",
        "role": role,
        "recommendation": action,
        "next_review_level": milestone,
        "levels_until_review": milestone - level,
        "current_level_verified_this_week": "YES",
        "ascension_approved": "NO",
        "release_approved": "NO",
        "reassignment_approved": "NO",
    })

out.mkdir(parents=True, exist_ok=True)

with report.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

guide = """# AxieOS Dojo Training Policy V1

Checkpoint 95 — 2026-10-27

## Weekly review

1. Review the five current Dojo trainees.
2. Update observed levels only when checked.
3. Review an Axie upon reaching its next milestone.
4. Preserve Origins-protected Axies.
5. Keep ForRel release decisions separate from AXP training.
6. Consider new trainees only after reviewing current slots.

## Safety

No automatic ascensions, releases, wallet actions,
or Terrarium reassignments.

This is an advisory register.
The specific plot assignment is not verified.
"""

(out / "dojo_policy_v1.md").write_text(
    guide, encoding="utf-8"
)

manifest = {
    "checkpoint": 95,
    "task": "135G",
    "roster_date": "2026-10-27",
    "trainees": 5,
    "active_forrel_pilots": 1,
    "paused_forrel_experiments_in_dojo": 1,
    "plot_assignments_verified": False,
    "ascensions_authorized": 0,
    "releases_authorized": 0,
    "reassignments_authorized": 0,
    "production_database_writes": 0,
}

(out / "manifest.json").write_text(
    json.dumps(manifest, indent=2),
    encoding="utf-8"
)

print("AXIEOS V0.13 - TASK 135G")
print("CHECKPOINT 95: DOJO TRAINING REGISTER")
print()
print("Current Dojo trainees:", len(rows))
print("Active ForRel pilots: 1")
print("Paused ForRel experiment still training: 1")
print("Protected Origins trainee: 1")
print()
print("NEXT LEVEL REVIEWS")
for r in sorted(rows, key=lambda x: x["levels_until_review"]):
    print(
        f"#{r['axie_id']} | "
        f"Lv{r['last_observed_level']} -> "
        f"Lv{r['next_review_level']} | "
        f"{r['recommendation']}"
    )

print()
print("Ascensions/releases/reassignments authorized: 0")
print("Production database writes: 0")
print("Bundle:", out)
print("VALIDATION: PASS")
