# The real `make issue-pick` prints exactly one line

**Issue:** [#578](https://github.com/andyholst/trending-local-llms/issues/578)
**Capability:** `issue-queue`

## Why

`make` echoes each recipe line. `#562` replaced the sweep's `sed` of the queue row with a
**capture** — `OUT=$(make issue-pick)` — so the recipe's own echo became the FIRST line of the
value, `PICK="${OUT#issue=}"` held a command plus the value, and the step refused its own queue.

Measured in production on runs **40190558547** (11:50Z) and **40194644167** (12:46Z): `implement`
was skipped in both, so the hourly queue implemented nothing for two hours, and `sweep-alarm`
reported OK because the run existed and was fresh (#498).

`#577` silenced the five affected recipes and added `test_a_captured_recipe_is_silent`, which
reads the workflows and the Makefile. That guard is a **text** check. The step test that would
have caught the original defect stubbed `make` with a script that printed the value alone —
removing exactly the line the real recipe contributes.

## What Changes

- **`tests/test_issue_review.py`** — `test_the_real_issue_pick_prints_exactly_one_line` runs the
  **REAL** `make issue-pick` with the `gh` stub on `PATH` (the replaced EXTERNAL system, as the
  rest of that module already does) and asserts:
  - stdout is exactly **one** non-empty line,
  - that line is `issue=<number>` and nothing else,
  - no line is the recipe's own echo (`python3 …`, `make …`, `sed …`),
  - the reasoning arrives on **stderr**, never in the value's stream.

## Impact

The capture path is now proved end to end: the recipe, `scripts/issue_queue.py` and the reading
contract the workflow depends on. A future edit that un-silences the recipe fails here with the
echoed line in the failure detail.

## Not covered (out of scope)

- The alarm half of #578 — a fresh run that delivered nothing is still invisible to `sweep-alarm`
  (issue #498, separate change).
- Only `issue-pick` is proved end to end; the other four captured recipes are covered by the text
  guard alone (filed as a finding).
