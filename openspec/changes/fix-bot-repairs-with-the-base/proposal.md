# Proposal: fix-bot-repairs-with-the-base

Issue: #383

## Why

fix-bot repairs a red PR **in isolation**: it re-reads the branch, spends LLM rounds
on it, never bounds a round, and never looks at whether the **base** already carries
the fix. Both failures measured today are that shape:

- **No per-round bound.** Run 39124432576 spent **1 h 58 m inside round 1 of 3** and
  was killed by the job's `timeout-minutes: 120` (`The operation was canceled`) — the
  loop's own failure path (report, PR comment, window close) never ran and the PR got
  nothing. Issue #372.
- **It repairs against a stale base.** Run 39183131652 (PR #377) spent over an hour
  on a failure the base had ALREADY fixed — the `NVIDIA FP4-Local` engine is a
  prompt-level defect fixed by #379, and the earlier `engine_min_version` failure was
  fixed by #374. Neither fix exists in the branch's own tree, which is all fix-bot
  ever reads. AGENTS.md says "Fix the class, not the PR", yet the bot re-derives the
  class fix by hand in every stale PR.
- **Silence looks like progress.** The container's stdout is block-buffered through
  `docker run` with no TTY, so an hour of repair prints nothing at all.

## What Changes

- **Every Hermes round is bounded.** `scripts/fix_loop.sh` runs `make fix` under
  `timeout "$HERMES_FIX_TIMEOUT"` (default **1800 s**, next to
  `HERMES_FIX_REASONING` in the `Makefile`), so `FIX_ROUNDS` rounds plus their checks
  fit inside a 2 h job. A timed-out round is **reported** — in the loop's log and in
  `qa-report.txt`, which is what the PR comment shows — instead of being killed by the
  job limit after the budget is gone.
- **The Makefile bounds the Hermes call itself.** `_fix` runs
  `timeout $(HERMES_FIX_TIMEOUT) hermes …` and `fix` forwards the same variable into
  the container, so the container is reaped cleanly with the round instead of being
  orphaned; the loop's host-level `timeout` is the backstop. ONE number, both sides.
- **The base is merged BEFORE any LLM round.** `merge_base()` fetches
  `origin/$FIX_BASE` (unshallowing first, because `actions/checkout` clones shallow),
  and merges it when the branch is behind — the same "bring a behind branch up to date
  before you push" AGENTS.md §6n already requires of a human. A failure the base
  already fixed then costs **zero LLM rounds**. It is never fatal: no checkout, no
  fetch, or a conflicting merge leaves the branch exactly as it was, loudly.
- **A round that changes nothing stops the loop.** The failure's byte-identical
  signature plus an untouched working tree means a fix that did not stick, so the loop
  reports it and exits instead of spending the remaining rounds on the same failure.
  The check is asked ONLY inside a git checkout, so a control-flow fixture can never
  trip it.
- **Notes survive the report truncation.** `run_checks` truncates the report at the
  start of every round, so loop-written notes (a timed-out round, a no-progress round)
  accumulate in `$QA_REPORT.notes` and are folded in by the next `run_checks`.

## Impact

`scripts/fix_loop.sh`, `Makefile` (`HERMES_FIX_TIMEOUT`, the `fix` wrapper, `_fix`),
`tests/test_fix_loop.py` (three new guards plus a hermetic `cwd` — the suite used to
run the loop inside this very checkout, which a base merge must never touch),
`tests/test_hermes_prompts.py` (its dry-run guard now accepts a bounded `hermes` call
and requires `_fix` to be bounded), the OpenSpec change and the regenerated
`OPENSPEC.md` index.

No make target, stage, pipeline job or image is added or renamed, so `ARCHITECTURE.md`
is unchanged (rule 6h) — verified by `make architecture-check`.

## Not covered

- **Issue #372** is the bound alone; this change supersedes it (the same rule, in
  `scripts/fix_loop.sh`) and the PR body closes #383, not #372 — a reviewer should
  close #372 as covered when this lands.
- **Streaming the container's output.** The round is now bounded and its timeout is
  reported, which is the actionable half; making `docker run` line-buffered is its own
  change.
- **Retrying the whole PR after the base merge reveals a NEW failure** introduced by
  the base. The loop already re-checks after the merge and repairs what it finds; a
  base that breaks a branch is a different finding with its own evidence.
- **The `AGENTS.md` §8 row** for the new guards: `AGENTS.md` is a protected
  agent-instruction file and this run has no approver (rule 3c). The exact row is in
  `findings.md`.
