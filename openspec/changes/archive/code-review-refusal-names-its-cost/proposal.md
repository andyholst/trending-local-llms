# A refused `gh` read names the cost it actually had

**Issue:** [#278](https://github.com/andyholst/trending-local-llms/issues/278)'s follow-through (found by verifying the merged fix live)
**Capability:** `code-review-scan` (the bot's deterministic checks)

## Why

#278 moved the secrets check onto the repo's declared contract, so it runs even though the live
`gh secret list` read is refused. Verifying that fix **live** (run 38876843174) showed the log
now contradicts itself:

```
[code-review] WARNING: 'gh secret list …' was refused (1): ['… HTTP 403 …'] — that check is SKIPPED this run
[code-review] INFO: the live `gh secret list` read was unavailable …; the secrets check ran against
  the repo's declared contract instead, so it did not go unchecked.
```

`_gh_soft` appended **"— that check is SKIPPED this run"** unconditionally, whatever the refusal
cost. After #278 the secrets refusal costs **no** check, so the WARNING asserts a consequence it
did not have — one line above an INFO saying the opposite. That is the same defect class as the
red check that blamed the mirror (#292/#293) and #278 itself: a message that names the wrong
causal story, and a reader who acts on it looks in the wrong place.

The distinction is real for the sibling read too: a refused **run-count** read *does* skip
`check_workflow_never_ran` (#309), so that warning must keep saying so.

## What Changes

- **`scripts/code_review.py`** — `_gh_soft` takes `skips: str | None`. It names what the refusal
  costs: a real skipped check prints `… IS SKIPPED this run` (unchanged for the run-count read),
  and `skips=None` prints `— no check is skipped by this refusal`. `defined_secrets` passes
  `skips=None`, because its refusal now costs nothing.
- **`tests/test_code_review.py`** — two tests, in `main()`, driving the REAL functions against a
  `gh` that refuses like the default token does, and asserting **both** directions: a refused
  secrets read does not claim a skipped check and says it costs none; a refused run-count read
  still names the check it skips.

## Not covered

- **`check_workflow_never_ran` is still skipped** when the runs read is refused — #309 owns that;
  this change only makes the log say so truthfully.
- **The `AGENTS.md` §8 row** (rule 6c) remains owed for `tests/test_code_review.py` and is already
  tracked by #310 — `AGENTS.md` is a protected rule file whose write approval has not returned.
  This change adds no new row obligation beyond it.
