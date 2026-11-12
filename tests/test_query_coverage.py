#!/usr/bin/env python3
"""The searches must ask for the models we rank (issue #264).

The query set was a fixed keyword list that named no model: of 24 queries the ONE
model-specific one named `qwen3.8-27b`, and none named `Strata`, so every figure for
the model topping the trend list arrived incidentally. These lock the rule and its
wiring — over the REAL store and over stores built here, with the real code running:

  1. a trending model gets a query naming it, and the whole top N ends up covered;
  2. a trending model no query names makes the coverage run FAIL (exit 1), so the gap
     is loud and separable from "the query ran and found nothing";
  3. the hand-curated base is KEPT, never replaced by the derived queries;
  4. a query naming a SIBLING model does not cover (qwen3.8-27b never covers the 125B);
  5. the four search prompts and the guard are wired to the one implementation;
  6. the REAL store is covered, and the derived query is what the prompts send.

Run standalone: python3 tests/test_query_coverage.py   or   make test
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import update_trending as UT  # noqa: E402

SCRIPT = ROOT / "scripts" / "query_coverage.py"
# The FLATTENED store (inline engines[]), exactly what the CLI reads via
# `update_trending.load_store()` — the aged derivation keys on each model's
# measurement dates, which the bare catalog file does not carry.
REAL_STORE = UT.load_store()
_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name} {detail}")


def _store_with(ids: list[str]) -> dict:
    """A store whose trending band is exactly `ids` (a fresh last_seen = band 0)."""
    return {"models": [
        {"id": i, "name": i, "last_seen": "2999-01-01",
         "engagement": {"trend_score": 1.0, "posts_7d": 1},
         "engines": [{"engine": "llama.cpp", "tps": "10", "hardware": "CPU",
                      "date": "2026-01-01"}]}
        for i in ids]}


def _aged_store() -> dict:
    """A store with ONE trending model and ONE aged (non-trending, old last_seen)
    model whose only measurement is older still — the exact case rule 6o's
    top-N derivation left unqueried."""
    return {"models": [
        {"id": "new-model", "name": "new-model", "last_seen": "2999-01-01",
         "engagement": {"trend_score": 5.0, "posts_7d": 3},
         "engines": [{"engine": "llama.cpp", "tps": "10", "hardware": "CPU",
                      "date": "2999-01-01"}]},
        {"id": "old-model", "name": "old-model", "last_seen": "2020-01-01",
         "engagement": {"trend_score": 0.0, "posts_7d": 0},
         "engines": [{"engine": "llama.cpp", "tps": "9", "hardware": "CPU",
                      "date": "2020-06-01"}]},
    ]}


def _run_cli(store: dict, *args: str) -> subprocess.CompletedProcess:
    """Run the real CLI against `store` through its own env hook."""
    td = Path(tempfile.mkdtemp())
    (td / "models.json").write_text(json.dumps(store))
    env = dict(os.environ, TRENDING_DATA_DIR=str(td))
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=str(ROOT), env=env,
                          capture_output=True, text=True, timeout=60)


def test_a_trending_model_gets_a_query_naming_it():
    # Given a store whose trending models include the model that motivated the issue
    store = _store_with(["qwen3.8-27b", "qwen3.8-flash-next-125b"])

    # When  the derived query set is built
    derived = UT.derived_queries(store)

    # Then  a query names each of them by its own id, and nothing is uncovered
    check("derive: a query names the 125B",
          "qwen3.8-flash-next-125b tokens per second" in derived, derived)
    check("derive: a query names the 27B",
          "qwen3.8-27b tokens per second" in derived, derived)
    check("derive: every trending model is covered", UT.uncovered_models(store) == [],
          UT.uncovered_models(store))


def test_an_uncovered_trending_model_fails_the_run():
    # Given a trending model no query can name (no usable id)
    store = _store_with(["qwen3.8-flash-next-125b", ""])

    # When  the coverage run evaluates it
    r = _run_cli(store)

    # Then  it exits 1 and says which model no query reaches
    check("guard: a trending model no query names fails the run (exit 1)", r.returncode == 1,
          r.returncode)
    check("guard: the failure names the gap", "no query names" in r.stderr, r.stderr[-200:])
    check("guard: the model no query names is listed", "MISS" in r.stdout, r.stdout[-200:])


def test_the_empty_id_is_the_only_uncovered_shape():
    """A model with no usable id must never be 'covered' by an empty key matching
    everything — that would make the guard vacuous."""
    # Given the matching rule
    # When  an empty id is checked against a real query
    # Then  it matches nothing
    check("rule: an empty id is named by nothing",
          not UT.query_names_model("qwen3.8-27b tokens per second", {"id": ""}))
    check("rule: an empty id is not a substring match either",
          not UT.query_names_model("anything at all", {"id": ""}))


def test_an_aged_model_gets_a_query_naming_it():
    """The AGED half of the query set (this change): a model that left the
    trending window is named again, so its stale figure can be refreshed and its
    ranked-dimension gaps can close."""
    store = _aged_store()

    # When  the aged derivations are built
    aged = UT.aged_models(store)
    aged_throughput = UT.aged_derived_queries(store)
    aged_footprint = UT.aged_footprint_queries(store)

    # Then  the non-trending model is sampled, and gets throughput + footprint
    check("aged: the non-trending model is selected, the trending one is not",
          [m.get("id") for m in aged] == ["old-model"], [m.get("id") for m in aged])
    check("aged: a throughput query names it",
          UT.model_query(store["models"][1]) in aged_throughput, aged_throughput)
    check("aged: a footprint query names it and asks the ranked dimensions",
          UT.footprint_query(store["models"][1]) in aged_footprint, aged_footprint)
    foot = UT.footprint_query(store["models"][1])
    for term in ("vram", "ram", "context", "weights", "offload", "engine version"):
        check(f"aged footprint: it asks for {term}", term in foot, foot)

    # And  the pair reaches EVERY leg, never only one
    full = UT.all_search_queries(store)
    for leg in full:
        check(f"aged: the {leg} leg carries the aged throughput query",
              UT.model_query(store["models"][1]) in full[leg], sorted(full))
        check(f"aged: the {leg} leg carries the aged footprint query",
              UT.footprint_query(store["models"][1]) in full[leg], sorted(full))

    # And  the coverage guard is green over the pair (both derivations)
    check("aged: the derived set covers the aged model",
          UT.uncovered_models(store) == [], UT.uncovered_models(store))


def test_the_aged_sample_is_the_oldest_measurements():
    """The aged sample is BOUNDED and picks the models whose newest measurement
    is the OLDEST — the rows that most need a fresh search."""
    # Given three non-trending models aged differently (and one trending)
    store = {"models": [
        {"id": "mid", "name": "mid", "last_seen": "2021-01-01",
         "engagement": {"trend_score": 0.0, "posts_7d": 0},
         "engines": [{"engine": "llama.cpp", "tps": "1", "hardware": "CPU", "date": "2021-06-01"}]},
        {"id": "oldest", "name": "oldest", "last_seen": "2019-01-01",
         "engagement": {"trend_score": 0.0, "posts_7d": 0},
         "engines": [{"engine": "llama.cpp", "tps": "1", "hardware": "CPU", "date": "2019-06-01"}]},
        {"id": "newest-of-aged", "name": "newest-of-aged", "last_seen": "2023-01-01",
         "engagement": {"trend_score": 0.0, "posts_7d": 0},
         "engines": [{"engine": "llama.cpp", "tps": "1", "hardware": "CPU", "date": "2023-06-01"}]},
        {"id": "trending", "name": "trending", "last_seen": "2999-01-01",
         "engagement": {"trend_score": 5.0, "posts_7d": 1},
         "engines": [{"engine": "llama.cpp", "tps": "5", "hardware": "CPU", "date": "2999-01-01"}]},
    ]}

    # When  the aged sample is bounded to two
    aged = UT.aged_models(store, 2)

    # Then  it is the two OLDEST-newest-date models, oldest first, never the trending one
    check("aged: bounds the sample to N most-aged",
          [m.get("id") for m in aged] == ["oldest", "mid"], [m.get("id") for m in aged])

    # A model with NO measurement date at all outranks every dated row (most aged)
    bare = {"models": [dict(m) for m in store["models"]]
            + [{"id": "no-measurement", "name": "no-measurement", "last_seen": "2018-01-01",
                "engagement": {"trend_score": 0.0, "posts_7d": 0}, "engines": []}]}
    aged_bare = UT.aged_models(bare, 2)
    check("aged: a model with no measurement is the most aged (sorts first)",
          [m.get("id") for m in aged_bare] == ["no-measurement", "oldest"],
          [m.get("id") for m in aged_bare])


def test_an_unsearchable_aged_model_is_not_sampled():
    """An aged model with no usable id is not searchable — naming it would emit
    a query that matches nothing (the vacuous-match guard), so it is excluded
    from the sample exactly as an empty-id trending model is flagged."""
    store = dict(_aged_store())
    store["models"].append({"id": "", "name": "nameless", "last_seen": "2018-01-01",
                            "engagement": {"trend_score": 0.0, "posts_7d": 0},
                            "engines": []})
    aged = UT.aged_models(store)
    check("aged: a searchable model is sampled, the empty-id one is not",
          [m.get("id") for m in aged] == ["old-model"], [m.get("id") for m in aged])


def test_the_curated_queries_are_kept():
    # Given the hand-curated groups and a trending model set
    store = _store_with(["qwen3.8-flash-next-125b"])

    # When  the set the searches use is built
    full = UT.all_search_queries(store)

    # Then  every curated query is still there, with the derived ones appended
    missing = [(b, q) for b, qs in UT.SEARCH_GROUPS.items() for q in qs if q not in full[b]]
    check("curated: the base is kept, never replaced", not missing, missing)
    check("curated: the derived query is appended to every leg",
          all(UT.model_query(store["models"][0]) in full[b] for b in full), sorted(full))


def test_a_footprint_query_names_each_ranked_model():
    """A throughput answer can state no footprint (tech-debt `ranked-gaps-need-new-search-data`).

    The derived set asked each ranked model for `tokens per second` and nothing else, so the
    posts that answered it were free to state no VRAM, weights, context window or engine build
    — and the ranked dimension gaps are dominated by models whose captured posts state no such
    figure. Each ranked model therefore also gets a dedicated FOOTPRINT query, on every leg.
    """
    # Given a store whose trending band is two models
    store = _store_with(["qwen3.8-flash-next-125b", "bonsai-2-test"])

    # When  the footprint queries are derived
    foot = UT.footprint_queries(store)
    one = UT.footprint_query(store["models"][0])

    # Then  one per trending model, each naming it and asking for the footprint terms
    check("footprint: one query per trending model", len(foot) == 2, foot)
    check("footprint: the query names the ranked model",
          UT.query_names_model(one, store["models"][0]), one)
    for term in ("vram", "ram", "context", "weights", "offload", "engine version"):
        check(f"footprint: the query asks for {term}", term in one, one)
    check("footprint: it names only its own model, never a sibling",
          not UT.query_names_model(one, {"id": "qwen3.8-27b"}), one)

    # And  every leg carries BOTH halves — the throughput query is kept, never replaced
    full = UT.all_search_queries(store)
    incomplete = [(b, q) for b in full
                  for q in UT.derived_queries(store) + foot if q not in full[b]]
    check("footprint: every leg carries the throughput AND the footprint queries",
          not incomplete, incomplete)
    check("footprint: the throughput query is still there",
          UT.model_query(store["models"][0]) in full[sorted(full)[0]], sorted(full))

    # And  the coverage guard still passes on the pair
    check("footprint: the derived set still covers every trending model",
          UT.uncovered_models(store) == [], UT.uncovered_models(store))


def test_a_sibling_model_query_does_not_cover():
    # Given the query that names the 27B
    q = "qwen3.8-27b dflash speculative tokens"

    # When  it is checked against the 125B and against the 27B
    # Then  it names only the 27B
    check("rule: a sibling's query does not cover the 125B",
          not UT.query_names_model(q, {"id": "qwen3.8-flash-next-125b"}), q)
    check("rule: it does cover the 27B", UT.query_names_model(q, {"id": "qwen3.8-27b"}), q)
    check("rule: the curated set alone does NOT name the 125B (the issue's gap)",
          not any(UT.query_names_model(q2, {"id": "qwen3.8-flash-next-125b"})
                  for qs in UT.SEARCH_GROUPS.values() for q2 in qs))


def test_every_ranked_gap_dimension_is_asked():
    """A dimension the analysis RANKS but no query ASKS can never be closed by a
    search (issue #460: `storage_offload` was missing on 59 models and
    `engine_min_version` on 35 while every ranked model had a throughput query AND a
    footprint query — the suffix asked for four dimensions, the analysis ranked five).
    The suffix is pinned to the ONE dimension list, not to a hand-kept second list.
    """
    import data_gap_analysis as gaps

    # Given the ranked dimensions themselves
    dims = [str(d["key"]) for d in gaps.DIMENSIONS]
    check("dimensions: the analysis ranks five", len(dims) >= 5, dims)

    # When  the ONE implementation compares them against the footprint suffix
    not_asked = UT.dimensions_not_asked()

    # Then  no ranked dimension is unasked — and the ask is proven on a REAL query
    check("dimensions: no ranked dimension is asked by nothing", not_asked == [], not_asked)
    one = UT.footprint_query({"id": "qwen3.8-27b"})
    for key in dims:
        token = UT.DIMENSION_ASK_TOKENS.get(key, key)
        check(f"dimensions: {key} is asked by the word {token!r}", token in one, one)

    # And  the guard itself says so through the real CLI over the real store
    proc = subprocess.run([sys.executable, str(SCRIPT), "--top", str(UT.QUERY_TOP_N), "--json"],
                          capture_output=True, text=True, cwd=str(ROOT))
    payload = json.loads(proc.stdout)
    check("guard: the real coverage run reports zero unasked dimensions",
          proc.returncode == 0 and payload["dimensions_missing"] == [],
          payload.get("dimensions_missing"))


def test_the_prompts_and_the_guard_are_wired():
    # Given the Makefile that drives the searches
    mk = (ROOT / "Makefile").read_text()

    # Then  every search prompt asks for the derived model queries ...
    for backend in ("nvidia", "metal", "cpu", "amd"):
        block = mk.split(f".PHONY: _search-{backend}\n", 1)[1].split("\n\n", 1)[0]
        check(f"wiring: the {backend} prompt asks for $(MODEL_QUERIES)",
              "$(MODEL_QUERIES)" in block, block[:80])
    check("wiring: MODEL_QUERIES comes from the one implementation",
          "scripts/query_coverage.py --queries" in mk)

    # ... the guard runs in the search validation ...
    check("wiring: _validate-search runs the coverage guard",
          "python3 scripts/query_coverage.py" in
          mk.split("_validate-search:", 1)[1].split("self_correct_raw", 1)[0])

    # ... and the prompts really carry the ranked models once expanded
    out = subprocess.run(["make", "-n", "_search-amd"], cwd=str(ROOT), capture_output=True,
                         text=True, timeout=60).stdout
    check("wiring: the expanded prompt names the ranked models",
          "qwen3.8-flash-next-125b tokens per second" in out, out[:120])
    # ... including a FOOTPRINT query per ranked model (the dimension gaps), and a sentence
    # that tells the agent what they ask for — a bare list would read as more throughput
    # queries and the footprint figure would stay unrecorded.
    check("wiring: the expanded prompt carries a footprint query",
          "qwen3.8-flash-next-125b vram ram context weights offload engine version" in out,
          out[:200])
    # The wording that tells the agent what the footprint queries ASK for lives in the leg's
    # PRELOADED skill, not in the prompt (issue #638: a prompt is a pointer plus this run's
    # parameters, so a rule duplicated there would drift from the one reviewed file).
    check("wiring: the leg is pointed at its preloaded skill",
          "-s data-search" in out, out[:200])
    # ... and the expanded prompt ALSO carries an aged model's query — a row that left the
    # trending window must be re-queried on the same legs (this change).
    aged = UT.aged_derived_queries(REAL_STORE)
    if aged:
        check("wiring: the expanded prompt names at least one aged model",
              aged[0] in out, (aged[0], out[:200]))


def test_the_real_store_is_covered():
    # Given the repo's own store
    # When  the coverage is evaluated over it
    derived = UT.derived_queries(REAL_STORE)
    missing = UT.uncovered_models(REAL_STORE)
    aged = UT.aged_models(REAL_STORE)
    aged_derived = UT.aged_derived_queries(REAL_STORE)
    aged_foot = UT.aged_footprint_queries(REAL_STORE)
    r = _run_cli(REAL_STORE)

    # Then  every top-N trending model is named, and the CLI agrees (exit 0)
    check("real: the top-N trending models are all named", not missing,
          [m.get("id") for m in missing])
    check("real: the derived set is one throughput query per model",
          len(derived) == min(UT.QUERY_TOP_N, len(UT.trending_models(REAL_STORE))),
          f"{len(derived)} queries")
    footprint = UT.footprint_queries(REAL_STORE)
    check("real: the footprint set is one query per ranked model",
          len(footprint) == len(derived), f"{len(footprint)} queries")
    ranked_ids = [m.get("id") for m in UT.trending_models(REAL_STORE)[:len(footprint)]]
    check("real: every footprint query is built from a ranked model's own id",
          footprint == [f"{mid} {UT.MODEL_FOOTPRINT_SUFFIX}" for mid in ranked_ids], footprint)
    # The aged half: a bounded sample of the most-aged non-trending rows is ALSO named
    # (this change) — the trending top-N and the aged sample together must all be
    # covered, so the real coverage run is green AND `--queries` prints an aged query.
    check("real: the aged sample is a bounded, non-empty set of non-trending rows",
          0 < len(aged) <= UT.QUERY_AGED_N and
          not any(m.get("id") in {t.get("id") for t in UT.trending_models(REAL_STORE)}
                  for m in aged), [m.get("id") for m in aged])
    check("real: the aged sample holds the oldest newest-measurement rows",
          aged == sorted(aged, key=lambda m: UT.newest_measurement_date(m)),
          [UT.newest_measurement_date(m) for m in aged])
    check("real: aged_derived is one throughput query per aged model",
          len(aged_derived) == len(aged) == len(aged_foot), f"{len(aged_derived)}/{len(aged)}")
    ageds = ",".join(aged_derived + aged_foot)
    check("real: every aged model is named by the aged set",
          all(UT.query_names_model(ageds, m) for m in aged), ageds[:200])
    check("real: the coverage run exits 0",
          r.returncode == 0, r.stderr[-200:])
    check("real: --queries prints exactly what the prompts append (both halves, both sets)",
          _run_cli(REAL_STORE, "--queries").stdout.strip()
          == ",".join(derived + footprint + aged_derived + aged_foot),
          _run_cli(REAL_STORE, "--queries").stdout.strip()[:200])


def test_a_silenced_guard_is_refused():
    # Given the ability to narrow the guard to nothing
    # When  --top 0 is asked for
    r = _run_cli(_store_with(["qwen3.8-flash-next-125b"]), "--top", "0")

    # Then  it refuses rather than passing vacuously
    check("guard: --top 0 is refused (a guard that checks nothing is not a guard)",
          r.returncode == 2 and "must be >= 1" in r.stderr, r.returncode)


def test_the_rule_is_documented():
    # Given the docs a human and the next agent read
    agents = (ROOT / "AGENTS.md").read_text()
    readme = (ROOT / "README.md").read_text()
    skill = (ROOT / "skills" / "gather-data.md").read_text()

    # Then  the rule, its guard row and the navigation are all there
    # Renumbered 6m -> 6o by issue #270: 6m was already the "ONE path through the
    # Makefile" rule, and this assertion pinned the number as well as the text.
    check("docs: AGENTS.md carries rule 6o", "6o. **The searches must ask for the models we rank" in agents)
    check("docs: AGENTS.md names the make target the rule is driven by",
          "make query-coverage" in agents)
    check("docs: the section-8 row names this test",
          "tests/test_query_coverage.py" in agents)
    check("docs: the README explains the derived queries",
          "query-coverage" in readme and "QUERY_TOP_N" in readme)
    check("docs: the search skill documents the derived queries",
          "Trending-model queries (issue #264)" in skill)
    # The leg's preloaded skill is where a prompt's rule now lives (issue #638): it must say that
    # each ranked model gets TWO queries, so the footprint half is never read as more throughput.
    leg = (ROOT / ".hermes" / "skills" / "data-search" / "SKILL.md").read_text()
    check("docs: the leg's skill says each ranked model gets a footprint query",
          "**two** queries" in leg
          and "**footprint** (`<id> vram ram context weights offload engine version`)" in leg,
          leg[:400])


def main() -> int:
    test_a_trending_model_gets_a_query_naming_it()
    test_an_uncovered_trending_model_fails_the_run()
    test_the_empty_id_is_the_only_uncovered_shape()
    test_an_aged_model_gets_a_query_naming_it()
    test_the_aged_sample_is_the_oldest_measurements()
    test_an_unsearchable_aged_model_is_not_sampled()
    test_the_curated_queries_are_kept()
    test_a_sibling_model_query_does_not_cover()
    test_a_footprint_query_names_each_ranked_model()
    test_every_ranked_gap_dimension_is_asked()
    test_the_prompts_and_the_guard_are_wired()
    test_the_rule_is_documented()
    test_the_real_store_is_covered()
    test_a_silenced_guard_is_refused()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
