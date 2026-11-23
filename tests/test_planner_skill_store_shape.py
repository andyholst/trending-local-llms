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


def test_store_measurement_rows_live_in_seen_posts_not_engines_array() -> None:
    store = json.loads(STORE.read_text(encoding="utf-8"))
    assert {"engines", "models"} <= set(store)
    assert isinstance(store["engines"], dict)
    models = store["models"]
    assert isinstance(models, list) and models
    model = models[0]
    assert "engines" not in model, "the #689 split removed the per-model engines[] array"
    engagement = model["engagement"]
    assert isinstance(engagement, dict)
    posts = engagement["seen_posts"]
    assert isinstance(posts, list) and posts
    assert {
        "url", "date", "engine", "tps", "hardware", "quant",
        "likes", "comments", "reshares", "views",
    } <= set(posts[0])


def test_planner_skill_describes_the_real_store_shape() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert "engagement.seen_posts[]" in text
    assert "models` is a LIST" in text or "models` (a list)" in text
    for stale in (
        "each model carries an `engines[]` array",
        "each model has an `engines[]` array",
        "per-model `engines[]` rows",
    ):
        assert stale not in text, f"stale store shape still documented: {stale}"
