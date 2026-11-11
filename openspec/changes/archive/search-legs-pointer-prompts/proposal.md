# A leg's contract is the skill it preloads — the search prompts stop carrying a rulebook

**Issue:** [#638](https://github.com/andyholst/trending-local-llms/issues/638)
**Capability:** `agent-leg-skills` (the seam #549 opened; this closes it for the search legs)

## Why

#549 moved every agent leg's contract into `.hermes/skills/<name>/SKILL.md` and gave each leg a
pointer plus parameters. The seam landed — the skills exist, `_setup` registers the directory, and
`make check-agent-skills` enforces it — but the SEARCH legs never moved. Measured on `master` with
`make agent-skills-report`:

```
_search-amd              prompt= 2338 skills=data-search,bot-unattended
_search-nvidia           prompt= 1906 skills=data-search,bot-unattended
_search-cpu              prompt= 1713 skills=data-search,bot-unattended
_search-metal            prompt= 1709 skills=data-search,bot-unattended
```

Those four prompts restated what the `data-search` skill already said, and the rules themselves lived
in three `Makefile` variables — `DIM_ASK` (≈1.7 KB), `ENGINE_ASK` (≈2.3 KB) and `SCRAPE_ASK` (≈0.7 KB)
— expanded into every leg. One rule therefore had two homes (a `Makefile` line and a skill paragraph)
and nothing proved they agreed. The gate could not see the duplication either: `PROMPT_BUDGET` was
3200 characters, so a 2.3 KB rulebook passed as "a pointer".

The cost is the failure mode #549 exists for. A leg's behaviour is corrected by editing prose that no
gate compares; a leg that kept an old sentence is invisible because the only check is length; and the
`Makefile` — which owns shell, stages and targets (rule 6m) — became the home of the longest prose in
the repository.

## What Changes

- **`.hermes/skills/data-search/SKILL.md`** — becomes the ONE home of the search contract. It absorbs
  the three retired variables' text verbatim in substance: the scrape request and the key read BY
  NAME, the terminal-tool pin (`execute_code` sends an empty Bearer → `HTTP 401`), the engine rule
  (never an engine invented from a model name or a quant; harnesses are not engines; `engine_repo`
  and its one verified lookup), the five measurement dimensions (on the model AND on the measurement),
  the `source_post` + engagement-counter rule, the clean-`tps` rule, the per-query `--write-raw`
  write, and the AMD leg's ROCm rules (classified by hardware, API in `quant`, decode t/s only, skip
  datacenter Instinct). It also documents each backend's parameters.
- **`Makefile`** — `DIM_ASK`, `ENGINE_ASK` and `SCRAPE_ASK` are deleted, and each of the four
  `_search-*` recipes is a pointer plus that run's parameters (`backend`, its keyword list,
  `$(MODEL_QUERIES)`, the `--write-raw` command). `_fix`, `_implement-issue`, `_review-issue` and
  `_review-issue-window` lose the rule text they still restated and keep their parameters.
- **`scripts/check_agent_skills.py`** — `PROMPT_BUDGET` 3200 → 900, and a new finding for
  `RETIRED_RULES`: each retired rule MUST be stated in the skill it moved to and MUST NOT appear in
  any recipe.
- **Tests (rule 6b, same change)** — the assertions that pinned those rules in the `Makefile` move to
  the skill, at the same strength: `tests/test_hermes_prompts.py` (engine rule, five dimensions),
  `tests/test_search_key.py` (the key's name, the tool pin), `tests/test_post_signal.py`,
  `tests/test_amd_backend.py`, `tests/test_engine_registry.py`, `tests/test_engine_aliases.py`,
  `tests/test_search_budget.py`, and `tests/test_agent_skills.py` (the gate's own new findings, proved
  on a copy of the tree).
- **`AGENTS.md`** — the owed §2 rule **6p** (a leg's contract is its project skill, preloaded with
  `-s`; `PROMPT_BUDGET` 900) and its §8 row, plus the three §8 rows that still described the retired
  variables. **This part is review-required (rule 3c)** and is called out in the PR body.
- **`ARCHITECTURE.md`** — the seam section and the `check-agent-skills` rows describe the tightened
  budget, the retired rules and the parameters a recipe now carries.

## Impact

The `Makefile` loses ~9 KB of prose that is not shell; a bot's rules are edited in ONE reviewed file
per leg; and the gate's budget is small enough to fail when a rule creeps back in. A search leg still
searches exactly what it searched before — the keyword lists and `$(MODEL_QUERIES)` remain parameters
of the recipe, and `scripts/smoke_search.py` / `scripts/query_coverage.py` read the same strings.

No data, contract, README, workflow, image or new-target change: `check-agent-skills`,
`agent-skills-report` and `hermes-skills-register` already exist and are already wired to `make lint`
and `qa-validate`.

## Not covered

- **A behavioural proof inside `make test` that Hermes really loads `-s data-search`.** The unit suite
  has no Hermes install; the registration is proved by `tests/test_agent_skills.py` against
  `scripts/hermes_skills_register.py`'s real config write, and the live half stays
  `make agent-shell-keys-check` / `make hermes-smoke` in `live-smoke`.
- **Moving the keyword lists into the skill.** They are parameters, and three guards read them from
  the recipes: `tests/test_card_fit.py` (the low-end card queries), `tests/test_amd_backend.py` (the
  AMD keyword set) and `scripts/smoke_search.py` (its `BACKEND_KEYWORDS` must equal the Makefile's
  lists). Moving them would move the drift, not remove it.
- **The `skills/gather-data.md` guide.** It is the human/agent technique reference; the contract a leg
  is bound by is the project skill, and rewriting the guide in this change would fork the prose again.
