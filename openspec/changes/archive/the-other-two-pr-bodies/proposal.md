# The refresh and architecture PR bodies are composed too

**Issue:** [#542](https://github.com/andyholst/trending-local-llms/issues/542)
**Capability:** `pr-body`

## Why

`refresh-bot.yml` built its PR body with a `{ … } > "$PR_BODY"` block and `architecture-bot.yml`
with four `printf` lines. Neither text could be rendered locally or run by a test — the defect #287
fixed for the implementer's body, still standing in the other two pipelines.

The refresh body embeds the run's **window block** (#199) and the contract a reviewer relies on, so
a wording or marker drift there is invisible to the suite. The architecture body deliberately
carries **no closing keyword** (`pr_closure` refuses a claim on a PR that implements no issue), so a
composer for it must also prove the absence.

## What Changes

- **`scripts/pr_body.py`** — `refresh_body(window)` and `architecture_body(run_url)`, reached by
  `--for refresh` / `--for architecture` (the implementation body keeps its `--issue`/`--branch`
  shape). An empty window is **REFUSED** (a body with a blank first section is the #199 defect), and
  `architecture_body` raises if `pr_closure` finds a closing claim in its own output.
- **`make refresh-pr-body [WINDOW_FILE=…]`** and **`make architecture-pr-body RUN_URL=…`**, both
  `@`-silenced so a redirect or a pipe holds the body alone.
- **Both workflows** redirect/pipe the target instead of building text inline.
- **`tests/test_pr_body.py`** — the window block comes first, the contract follows byte for byte, an
  unreadable window is refused, the architecture body names the run and carries no closing keyword,
  and neither workflow holds inline body text.

## Impact

Both bodies are renderable and testable locally, and the architecture body's rule-6e shape is proved
by the composer rather than trusted.

## Not covered (out of scope)

- The refresh PR's **title** is still inline (`chore: Hermes refresh of trending LLM data`); #541 did
  this for the implementer's title only. Filed as a finding.
