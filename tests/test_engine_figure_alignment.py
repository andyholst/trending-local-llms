#!/usr/bin/env python3
"""Engine-figure alignment (issue #795): one spelling map, a recorded rule decision,
and a FAILING cross-row duplicate gate.

The repo's promise (AGENTS.md rules 5/5b/6) is that every figure is attributed to one
correctly-spelled, repo-linked engine. Three alignment gaps this suite locks shut:

  1. `mlx.fast` (49 raw search snapshots) vs the registry's 'MLX-fast (Bonsai 2)':
     `make engine-check` decided 'no-repo' on the spelling forever. ONE map —
     `engine_registry.ENGINE_NAME_ALIASES` (rule 6d) — re-homes captured spellings to
     their registered engine (the target must BE registered; an alias to a missing
     engine keeps the loud WARN).
  2. 'Bonsai Oryon' is PACKAGING (a .deb wrapping PrismML's llama.cpp fork + ggml),
     not an inference engine — the issue's stranded 34.8 t/s figure. The decision is
     recorded in the registry entry's note and in the spelling map; `apply_engine_aliases`
     re-homes it at ingest for EVERY model, and `fabricated_engine_reason` no longer
     refuses the declared spelling as a hardware token.
  3. A measurement (engine+tps+date+source_post) filed under two model ids — and a
     variant id (prefix-related) sharing engine+tps+date across two posts, the copy the
     hardware-keyed scan (#693, report-only) cannot see — now FAILS `make validate`
     through `check_no_duplicate_measurements` unless justified as data by
     `measurement_model_aliases` (#652 vehicle). No shipped row is removed (rule 3b).

Run:  python3 tests/test_engine_figure_alignment.py    or   make test
"""
from __future__ import annotations

import copy
import io
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import engine_registry as ER  # noqa: E402
import update_trending as UT  # noqa: E402
import validate as V  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f" FAIL {name}" + (f" :: {detail}" if detail else ""))


def shipped_engines() -> dict:
    return json.loads((ROOT / "data" / "models.json").read_text())["engines"]


# --- the spelling map ---------------------------------------------------------

def test_the_spelling_map_is_one_definition_with_registered_repo_linked_targets():
    engines = shipped_engines()
    aliases = ER.ENGINE_NAME_ALIASES
    check("map holds the two decided spellings",
          aliases == {"mlx.fast": "MLX-fast (Bonsai 2)",
                      "Bonsai Oryon": "llama.cpp (PrismML fork)"}, json.dumps(aliases))
    for raw, target in aliases.items():
        check(f"'{raw}' re-homes to the registered engine '{target}'", target in engines,
              f"{target} not in data/models.json engines")
        check(f"alias target '{target}' carries a repo url (rule 5b)",
              str(engines[target].get("url") or "").startswith("https://github.com/"),
              json.dumps(engines[target]))
        check(f"the alias key '{raw}' is itself not registered", raw not in engines)
    # canonical_engine_name resolves only against a registry holding the target —
    # the map may never hide a genuinely unknown engine.
    check("canonical resolves a registered target",
          ER.canonical_engine_name("mlx.fast", engines) == "MLX-fast (Bonsai 2)")
    check("canonical keeps the raw name when the target is NOT registered",
          ER.canonical_engine_name("Bonsai Oryon", {}) == "Bonsai Oryon")
    check("map has one home",
          sum(1 for p in (ROOT / "scripts").glob("*.py")
              if "ENGINE_NAME_ALIASES = {" in p.read_text()) == 1)


def test_planted_captured_spellings_re_home_at_ingest():
    engines = shipped_engines()
    m = {"id": "some-model-9b", "engine_aliases": {},
         "supported_engines": ["mlx.fast", "Bonsai Oryon"],
         "engines": [{"engine": "mlx.fast", "tps": 100.0, "date": "2026-11-01"},
                     {"engine": "Bonsai Oryon", "tps": 34.8, "date": "2026-10-16"}]}
    out = UT.apply_engine_aliases(copy.deepcopy(m))
    names = [e["engine"] for e in out]
    check("captured 'mlx.fast' re-homes at ingest",
          "MLX-fast (Bonsai 2)" in names and "mlx.fast" not in names, str(names))
    check("captured 'Bonsai Oryon' re-homes at ingest",
          "llama.cpp (PrismML fork)" in names and "Bonsai Oryon" not in names, str(names))
    again = UT.apply_engine_aliases(copy.deepcopy({"id": "some-model-9b", "engines": out}))
    check("the rename is idempotent", [e["engine"] for e in again] == names, str(again))
    own = copy.deepcopy(m)
    own["engine_aliases"] = {"mlx.fast": "Ollama"}
    names_own = [e["engine"] for e in UT.apply_engine_aliases(own)]
    check("the model's own engine_aliases still win over the registry map",
          "Ollama" in names_own and "MLX-fast (Bonsai 2)" not in names_own, str(names_own))
    check("the declared spelling is not 'fabricated' for a registered target",
          UT.fabricated_engine_reason("Bonsai Oryon", m, engines) is None)
    check("an unknown engine with the same hardware token is STILL refused",
          UT.fabricated_engine_reason("Oryon Serve", m, engines) is not None)


def test_the_engine_check_is_warn_free_on_the_shipped_raw_captures():
    os.environ["ENGINE_REGISTRY_META_FILE"] = str(ROOT / "tests" / "fixtures" / "github_meta.json")
    try:
        store = json.loads((ROOT / "data" / "models.json").read_text())
        decisions = ER.check_raw(ROOT / "data" / "raw", store)
    finally:
        os.environ.pop("ENGINE_REGISTRY_META_FILE", None)
    aliased = [d for d in decisions if d.get("engine") in ER.ENGINE_NAME_ALIASES]
    check("no decision is emitted for an aliased spelling", not aliased,
          json.dumps(aliased))
    check("every remaining decision is 'registered'",
          all(d.get("decision") == "registered" for d in decisions),
          json.dumps(decisions)[:400])


def test_the_bonsai_oryon_decision_is_recorded_in_the_registry():
    engines = shipped_engines()
    check("'Bonsai Oryon' is NOT registered as an engine", "Bonsai Oryon" not in engines)
    note = str(engines["llama.cpp (PrismML fork)"].get("note") or "")
    check("the registry note names Bonsai Oryon as packaging whose figures re-home here",
          "Bonsai Oryon" in note and "PACKAGING" in note, note[:200])
    check("the MLX-fast registry entry already names the mlx.fast spelling",
          "mlx.fast" in str(engines["MLX-fast (Bonsai 2)"].get("note") or ""))


# --- the cross-row duplicate gate ---------------------------------------------

def test_make_validate_fails_on_a_planted_cross_row_duplicate():
    post = "https://lightbrd.com/someuser/status/123"
    models = [
        {"id": "model-alpha-9b", "name": "Alpha", "engines":
            [{"engine": "llama.cpp", "tps": 42.0, "date": "2026-10-01",
              "hardware": "RTX 4090", "quant": "Q4", "source_post": post}]},
        {"id": "model-beta-8b", "name": "Beta", "engines":
            [{"engine": "llama.cpp", "tps": 42.0, "date": "2026-10-01",
              "hardware": "RTX 4090", "quant": "Q4", "source_post": post}]},
    ]
    found = V.cross_row_duplicate_measurements(models)
    check("the same post under two ids is found",
          any(r == "same post" and set(ids) == {"model-alpha-9b", "model-beta-8b"}
              for r, _k, ids in found), json.dumps(found))
    V.FAILURES.clear()
    try:
        V.check_no_duplicate_measurements({"models": models})
        fails = list(V.FAILURES)
    finally:
        V.FAILURES.clear()
    check("make validate FAILS on the planted duplicate", fails, "no failure recorded")
    check("the failure names both ids and the figure",
          fails and "model-alpha-9b" in fails[0] and "model-beta-8b" in fails[0]
          and "42.0 t/s" in fails[0], fails[0] if fails else "")


def test_a_planted_variant_pair_sharing_engine_tps_and_date_fails():
    models = [
        {"id": "qwen3.8-27b", "name": "Base", "engines":
            [{"engine": "TokenSpeed", "tps": 961.6, "date": "2026-10-21",
              "hardware": "RTX 4090", "quant": "Q4",
              "source_post": "https://lightbrd.com/u1/status/1"}]},
        {"id": "qwen3.8-27b-swift", "name": "Variant", "engines":
            [{"engine": "TokenSpeed", "tps": 961.6, "date": "2026-10-21",
              "hardware": "RTX 4090 GPU", "quant": "Q4_K",
              "source_post": "https://lightbrd.com/u2/status/2"}]},
        {"id": "unrelated-llm-9x", "name": "Unrelated", "engines":
            [{"engine": "TokenSpeed", "tps": 961.6, "date": "2026-10-21",
              "hardware": "A100", "quant": "FP8",
              "source_post": "https://lightbrd.com/u3/status/3"}]},
    ]
    found = V.cross_row_duplicate_measurements(models)
    pairs = {tuple(sorted(ids)) for _r, _k, ids in found}
    check("the variant pair (different post, renamed hardware) FAILS",
          ("qwen3.8-27b", "qwen3.8-27b-swift") in pairs, json.dumps(sorted(pairs)))
    check("two UNRELATED ids sharing engine+tps+date are NOT flagged",
          ("qwen3.8-27b", "unrelated-llm-9x") not in pairs
          and ("qwen3.8-27b-swift", "unrelated-llm-9x") not in pairs,
          json.dumps(sorted(pairs)))
    V.FAILURES.clear()
    try:
        V.check_no_duplicate_measurements({"models": models})
        fails = list(V.FAILURES)
    finally:
        V.FAILURES.clear()
    check("make validate FAILS on the variant pair", fails and "variant pair" in fails[0],
          fails[0] if fails else "")


def test_justified_variant_and_bakeoff_pairs_pass_the_gate():
    models = [
        {"id": "qwen3.8-27b", "name": "Base", "engines":
            [{"engine": "TokenSpeed", "tps": 961.6, "date": "2026-10-21",
              "hardware": "RTX 4090", "quant": "Q4",
              "source_post": "https://lightbrd.com/u1/status/1"}]},
        {"id": "qwen3.8-27b-swift", "name": "Variant",
         "measurement_model_aliases": ["qwen3.8-27b"], "engines":
            [{"engine": "TokenSpeed", "tps": 961.6, "date": "2026-10-21",
              "hardware": "RTX 4090 GPU", "quant": "Q4_K",
              "source_post": "https://lightbrd.com/u2/status/2"}]},
        {"id": "lfm2.5-24b-a2b", "name": "Bakeoff A",
         "measurement_model_aliases": ["qwen3.6-35b-a3b"], "engines":
            [{"engine": "vllm", "tps": 18.0, "date": "2026-09-09",
              "hardware": "RTX 5090", "quant": "FP8",
              "source_post": "https://lightbrd.com/guide/status/7"}]},
        {"id": "qwen3.6-35b-a3b", "name": "Bakeoff B",
         "measurement_model_aliases": ["lfm2.5-24b-a2b"], "engines":
            [{"engine": "vllm", "tps": 18.0, "date": "2026-09-09",
              "hardware": "RTX 5090", "quant": "FP8",
              "source_post": "https://lightbrd.com/guide/status/7"}]},
    ]
    check("justified pairs return nothing",
          V.cross_row_duplicate_measurements(models) == [],
          json.dumps(V.cross_row_duplicate_measurements(models)))
    V.FAILURES.clear()
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            V.check_no_duplicate_measurements({"models": models})
            V.check_measurement_alias_map({"models": models})
        fails = list(V.FAILURES)
    finally:
        V.FAILURES.clear()
    check("the gate AND the alias-map check stay green on justified pairs",
          not fails, fails[0] if fails else "")


def test_allow_list_exact_pairs_are_justified_without_an_alias():
    """#1213 F1: the validator honours the SAME CROSS_MODEL_ALLOW_LIST ingest reads.
    Migrating these two pairs to the allow-list and dropping their store aliases
    must NOT red `validate --only data` — the two justifications are ONE seam."""
    import update_trending as ut
    keys = [
        ("vLLM", "25.4", "2026-10-14",
         "https://lightbrd.com/GuideboardLabs/status/2110246672166699354"),
        ("llama.cpp (strix-llama.cpp fork)", "21", "2026-10-17",
         "https://lightbrd.com/laky_fx/status/2111512795803988237"),
    ]
    models = []
    for key in keys:
        allowed = sorted(ut.CROSS_MODEL_ALLOW_LIST[key])
        # The allow-list keys the exact str(tps) spelling the store carries:
        # "25.4" -> 25.4, "21" -> 21 (float() would render "21.0" and miss the key).
        tps = float(key[1]) if "." in key[1] else int(key[1])
        for mid in allowed:
            models.append({
                "id": mid, "name": mid,  # deliberately NO measurement_model_aliases
                "engines": [{"engine": key[0], "tps": tps,
                             "date": key[2], "hardware": "RTX 4090", "quant": "FP8",
                             "source_post": key[3]}],
            })
    found = V.cross_row_duplicate_measurements(models)
    check("allow-list-exact pairs with NO alias are not flagged",
          found == [], json.dumps(found))
    V.FAILURES.clear()
    try:
        V.check_no_duplicate_measurements({"models": models})
        fails = list(V.FAILURES)
    finally:
        V.FAILURES.clear()
    check("make validate --only data stays green on the migrated pairs",
          not fails, fails[0] if fails else "")


def test_the_shipped_store_has_no_undocumented_cross_row_duplicates():
    store = UT.load_store()
    found = V.cross_row_duplicate_measurements(store["models"])
    check("the shipped store flags nothing", found == [], json.dumps(found)[:400])
    V.FAILURES.clear()
    try:
        V.check_no_duplicate_measurements(store)
        fails = list(V.FAILURES)
    finally:
        V.FAILURES.clear()
    check("the gate is green on the shipped store", not fails, fails[0] if fails else "")
    planted = copy.deepcopy(store["models"][0])
    planted = copy.deepcopy(planted)
    planted["id"] = "zz-plant-gate-check"
    if planted.get("engines"):
        planted["engines"] = [dict(planted["engines"][0])]
        planted.pop("measurement_model_aliases", None)
        store2 = {"models": store["models"] + [planted]}
        found2 = V.cross_row_duplicate_measurements(store2["models"])
        check("the gate still bites on the shipped data if an undocumented copy reappears",
              any("zz-plant-gate-check" in ids for _r, _k, ids in found2),
              json.dumps(found2)[:300])


def main() -> int:
    print("engine-figure alignment: spellings, decisions, duplicate gate (issue #795)")
    test_the_spelling_map_is_one_definition_with_registered_repo_linked_targets()
    test_planted_captured_spellings_re_home_at_ingest()
    test_the_engine_check_is_warn_free_on_the_shipped_raw_captures()
    test_the_bonsai_oryon_decision_is_recorded_in_the_registry()
    test_make_validate_fails_on_a_planted_cross_row_duplicate()
    test_a_planted_variant_pair_sharing_engine_tps_and_date_fails()
    test_justified_variant_and_bakeoff_pairs_pass_the_gate()
    test_allow_list_exact_pairs_are_justified_without_an_alias()
    test_the_shipped_store_has_no_undocumented_cross_row_duplicates()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
