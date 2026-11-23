"""Lock the planner skill's store-shape description to the real store (fleet sync, 2026-11-23).

The #689 split moved per-(model, engine, source_post) measurement rows out of a
model-level `engines[]` array into `engagement.seen_posts[]`. A skill that still
teaches `engines[]` makes the planner count the wrong rows and report a false
store loss. Both assertions read the REAL files — no stand-ins (rule 6m).
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data" / "models.json"
SKILL = ROOT / "agents" / "tll-planner" / "skills" / "tll-planner" / "SKILL.md"


_passed = 0
_failed = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"  ok   {label}")
    else:
        _failed += 1
        print(f"  FAIL {label}" + (f"\n       {detail}" if detail else ""))


def test_store_measurement_rows_live_in_seen_posts_not_engines_array() -> None:
    print("\nStore shape: measurement rows live in engagement.seen_posts[]")
    store = json.loads(STORE.read_text(encoding="utf-8"))
    check("engines and models keys exist", {"engines", "models"} <= set(store))
    check("engines is a dict", isinstance(store["engines"], dict))
    models = store["models"]
    check("models is a non-empty list", isinstance(models, list) and bool(models))
    model = models[0]
    check("no per-model engines[] array (#689 split)", "engines" not in model,
          "the #689 split removed the per-model engines[] array")
    engagement = model["engagement"]
    check("engagement is a dict", isinstance(engagement, dict))
    posts = engagement["seen_posts"]
    check("seen_posts is a non-empty list", isinstance(posts, list) and bool(posts))
    check("seen_posts rows carry the measurement shape", {
        "url", "date", "engine", "tps", "hardware", "quant",
        "likes", "comments", "reshares", "views",
    } <= set(posts[0]), str(sorted(posts[0])))


def test_planner_skill_describes_the_real_store_shape() -> None:
    print("\nPlanner skill: documents the real store shape")
    text = SKILL.read_text(encoding="utf-8")
    check("skill names engagement.seen_posts[]", "engagement.seen_posts[]" in text)
    check("skill names models as a list",
          "models` is a LIST" in text or "models` (a list)" in text)
    for stale in (
        "each model carries an `engines[]` array",
        "each model has an `engines[]` array",
        "per-model `engines[]` rows",
    ):
        check(f"stale store shape absent: {stale}", stale not in text)


def main() -> int:
    test_store_measurement_rows_live_in_seen_posts_not_engines_array()
    test_planner_skill_describes_the_real_store_shape()
    print(f"\nPASSED {_passed} | FAILED {_failed}")
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
