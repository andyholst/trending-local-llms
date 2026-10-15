# The live pre-flight checks fail loudly instead of skipping

**Issue:** [#209](https://github.com/andyholst/trending-local-llms/issues/209)
**Capability:** `live-checks`

## Why

Two scripts prove the live path before a 20-minute search leg, and both could
report success having checked nothing:

- `scripts/hermes_smoke.sh` — `[hermes-smoke] SKIP: NOUS_API_KEY not set` +
  `exit 0`;
- `scripts/model_caps_check.py` — `[model-caps] SKIP: NOUS_API_KEY not set` +
  `return 0`.

`make hermes-smoke` runs in five workflows (`issue-bot`, `issue-review-bot`,
`fix-bot`, `qa-validate`, `refresh-bot`); `make model-caps` runs in
`qa-validate`'s `live-smoke` job and in every search leg's pre-flight. On a run
where the key is missing or misnamed — the exact defect class #124 was
(`HF_TOKEN` auto-routed instead of the alias) — both printed success and the run
continued, so the failure surfaced later as a provider error inside the model
call, or as a plausible-looking answer produced by a different provider that
happened to have a key in the environment.

`AGENTS.md` states the rule these two broke: *"A skipped test is a loud FAILURE,
never a silent skip … a broken/absent prerequisite can never silently pass CI while
the real behavior is unverified."* A scheduled bot run with no key cannot do the
work it was scheduled for; the honest outcome is a loud failure naming the missing
secret. Both tests that pinned the old behaviour
(`tests/test_hermes_smoke.py`: *"NOUS_API_KEY unset → SKIP, exit 0"* and
`tests/test_search_budget.py`: *"no key, no catalog → SKIP exit 0"*) changed with
it — a test that locks a silent skip is part of the defect.

## What Changes

- Both checks **FAIL** when `NOUS_API_KEY` is unset: non-zero exit, a message that
  names the variable, what could not be proven (the `nous-deepseek` alias and its
  routing; the endpoint's model id, real `max_completion_tokens` and `reasoning`
  support) and the consequence of a green result here.
- One explicit, non-default opt-out for a caller that knowingly runs without a key
  (an offline developer reproducing the data path):
  `LIVE_CHECK_ALLOW_UNCONFIGURED=1` → `NOT CONFIGURED` + exit 0, on both scripts.
  **No workflow sets it**, and `tests/test_hermes_smoke.py` reads every
  `.github/workflows/*.yml` and fails if one does.
- The two tests that pinned the skip now pin the failure and the opt-out path
  (`tests/test_hermes_smoke.py`, `tests/test_search_budget.py`).
- `ARCHITECTURE.md` says it for `hermes-smoke`, `model-caps` and `pipeline-smoke`;
  the README bullet on key handling gains the same sentence (through its template
  in `scripts/update_trending.py`); `AGENTS.md` gains the section 8 row.

## Not covered

- `make search-smoke` (Firecrawl reachability) already fails loudly — verified in
  `scripts/smoke_search.py`: with no `FIRECRAWL_API_KEY` it prints
  `[error] FIRECRAWL_API_KEY not set` and returns 1, and its `--url-only` mode
  returns 0 without touching the network. It is therefore not part of this defect
  and does not get the opt-out flag; the flag exists only for the two checks that
  gate the *model* call.
- Publishing the agent image, its rebuild decision and the implementer's thread
  read: [#206](https://github.com/andyholst/trending-local-llms/issues/206),
  [#208](https://github.com/andyholst/trending-local-llms/issues/208),
  [#210](https://github.com/andyholst/trending-local-llms/issues/210).
