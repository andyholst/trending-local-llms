# Proposal: openspec-index-drift-trigger

Issue: #1634
PR: #1640

## Why

The root `OPENSPEC.md` index silently rots after every merge that archives a change, and
nothing repairs it until the drift exceeds a tolerance. Measured on master `cb139e7c`
(2026-11-24):

```text
$ python3 scripts/openspec_index.py --check
[openspec-index] WARN OPENSPEC.md drifted by 1 of at most 25 changes — run `make openspec-index`
[openspec-index]   the count line says 'Active changes: **1** · archived: **520**', disk needs '...522**'
(rc 0)
```

Two independent gaps combine:

1. `openspec-index-check` exits 0 with a WARN while drift is within
   `MAX_OPENSPEC_INDEX_DRIFT` (25), so `qa-validate`'s `validate` job stays green on a
   stale index — yet rule 6f advertises "the index current" as a gate.
2. qa-validate's event-driven `index-repair` keeper is `if: failure() && push to master`,
   so it only runs when `validate` is already RED. A WARN never wakes it, and the drift
   compounds merge over merge (issue #1625's regeneration was superseded within an hour).

The design comment (`BOT tll-architect · design #1634`, issuecomment-7139758319) chose
repair **C**: keep the tolerance and the PR-head gate byte-identical, and wake the keeper
on a GREEN push whose `validate` reports drift. Merge-time regeneration (A) was refused by
§6s/#1089 and covers only ~36% of merges; a hard FAIL beyond a smaller tolerance (B) newly
reds every legitimately-open PR and needs a keeper anyway.

## What Changes

- `scripts/openspec_index.py` gains `--drift` beside `--check`, reusing the ONE measure
  `index_drift()`. It prints exactly `drift=<n>` on stdout and exits 0 for ANY drift on a
  readable tree; the reasons go to stderr so the stdout contract stays one line. A missing
  or unreadable index is stderr + exit 2, no stdout. `MAX_OPENSPEC_INDEX_DRIFT` and the
  `--check` WARN/FAIL branches are untouched.
- `Makefile` gains `openspec-index-drift` (beside `openspec-index-check`, same
  `python-env-image` wrapper, declared `.PHONY`). It is a REPORT target, not a gate.
- `.github/workflows/qa-validate.yml`: `validate` grows an allowlisted `index_drift` output
  key and a step that runs `make openspec-index-drift` and parses ONLY the `drift=` key
  into `$GITHUB_OUTPUT`; `index-repair`'s `if:` widens to
  `(failure() || needs.validate.outputs.index_drift != '0') && push to master`.
- `scripts/master_alarm.py::GATES` gains the additive entry
  `"openspec-index-drift": ("alarm", "master-alarm")` — required because
  `validate_gates_from_trees()` reads every `make X` the validate job runs.
- `ARCHITECTURE.md`: one new public-target row, the §4 `index-repair` job row corrected,
  and the generated inventory refreshed in the same change (rule 6h).
- `AGENTS.md`: §6q and the §6b `index-repair` row state the widened trigger; §8 gains one
  row for the new guard (rule 3c, review-required — the reviewer signs off the diff).

## Impact

Nothing newly reds. The tolerance, `--check`'s exit codes and the #1239 merge-tree step are
byte-identical; a push with drift still ends `validate` GREEN. The only new behaviour is a
possible extra generated-artifact keeper PR per merge-heavy push, deduped by the #960
mergeable-only rule and each also refreshing `ARCHITECTURE.md`.

No schema, data, contract, table or cron change; one additive registry key (rule 3b). The
`AGENTS.md` edit is review-required under rule 3c: the architect declared the sections on
this thread and `tll-reviewer` signs off the diff on #1634.

RED on the base: the new module against pristine `origin/master` answers
`PASSED 10 | FAILED 14` (exit 1) — `--drift` is an unknown argument (argparse exit 2) and
the workflow/Makefile/registry tokens are absent. GREEN on this head:
`PASSED 24 | FAILED 0`.

## Not covered

- Merge-time index regeneration (repair A) and a smaller-tolerance hard FAIL (repair B):
  both rejected in the design, the first by the §6s/#1089 ruling.
- Extending `auto-merge-rebase`'s pre-squash regeneration to a CURRENT bot head, and the
  ~64% human-owned merges: the design's named residual, a separate small change.
- Any change to `MAX_OPENSPEC_INDEX_DRIFT` or to `--check`'s verdicts.
