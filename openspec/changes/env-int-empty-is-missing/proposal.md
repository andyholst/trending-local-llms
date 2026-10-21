# Proposal: env-int-empty-is-missing

Issue: #487 — pr-health: the sweep is red on every run

## Why

Measured on run [39530945300](https://github.com/andyholst/trending-local-llms/actions/runs/39530945300/job/118996453651):
`guard: success · sweep: failure`, failing at the step that REPORTS silent PRs,
before it read a single PR:

```
python3 scripts/pr_health.py --repo "…" --comment
  default=int(os.environ.get("MAX_FIXBOT_COMMITS", "2")),
ValueError: invalid literal for int() with base 10: ''
```

Two layers each assumed the other does not exist:

1. the public `pr-health` target ALWAYS forwards
   `MAX_FIXBOT_COMMITS="$(MAX_FIXBOT_COMMITS)"`, so the `COMMENT=1` call exports it
   **empty** (set, zero-length);
2. `scripts/pr_health.py` defaults with `int(os.environ.get(name, "2"))`, which
   treats *unset* as the default but *empty* as a value — and `int("")` raises.

So the alarm whose whole purpose is "a silent PR must be loud" was itself silently
refused on every scheduled sweep since the repair half landed (#475/#478). AGENTS.md
§2.3d already states the rule for credentials ("an empty value counts as missing: that
is the shape a missing GitHub secret takes at run time"), but it was never applied to
SETTINGS.

## What Changes

- **New `scripts/env_int.py`** — ONE implementation of "read a number from the
  environment": unset **or** blank (`""`, `"   "`) yields the default; a non-numeric
  value raises `EnvSettingError` naming the variable and what it held (a typo must
  never be silently read as the default). Exposes `env_int` and `env_float`.
- **Every `int(os.environ…)` / `float(os.environ…)` in `scripts/` now uses it** —
  `pr_health`, `issue_queue` (3 sites), `issue_review`, `ensure_image` (2), `validate`
  (2), `verify_closure` (2). Only `pr-health` forwards an empty value today, but the
  class is the same everywhere.
- **`Makefile`**: the public `pr-health` target forwards `MAX_FIXBOT_COMMITS` only
  when it is SET (`$(if …)`) — the wrapper stops manufacturing an empty value.
- **`tests/test_pr_health.py`** gains: the `env_int`/`env_float` truth table
  (unset / empty / whitespace / value / padded / garbage), the REAL
  `make pr-health REPO=… COMMENT=1` call with a stub `gh` (the network boundary) and
  no `MAX_FIXBOT_COMMITS` — the exact production shape — plus a repo-wide guard that
  fails on a new bare `int(os.environ…)`, and a Makefile assertion that the empty
  value is never forwarded.

## Impact

- The sweep runs again: `make pr-health COMMENT=1` reports and comments on silent PRs
  instead of dying on its own configuration.
- No behaviour change where a value IS set; `MAX_FIXBOT_COMMITS=abc` is still loud,
  now naming the variable.
- Proven both ways: 6 of the new checks FAIL against the pre-change sources (measured),
  all 45 pass after.

## Not covered

- The GitHub-side reason a PR is silent (a conflict, a missing run) — unchanged; this
  fix is only that the alarm can run at all.
- `float(os.environ…)` sites outside `scripts/` (none exist in the tree).
- The other pipelines' settings (`REVIEW_GAP_HOURS`, `VERDICT_TTL_HOURS`, …) are passed
  as make arguments today; they now read through `env_int` for the day a wrapper
  forwards one empty.
