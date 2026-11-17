# Proposal: closing-pr-requires-bounded-openspec-change (Issue: #1109)

Issue: #1109
PR: #1111

## Why

Rule 6f is mandatory — "Work MUST start by creating the change (`make openspec-new`) — before any code" — but every OpenSpec gate is one-directional. `openspec-archive-check --pr` (#779/#866) refuses an ACTIVE change left unarchived by the closing PR; `openspec-binding-check` (#952) refuses an ACTIVE change with no `Issue:` binding. Nothing asks the mirror question: **does a PR that closes an issue carry a change at all?** The gap is the absence of the check itself — no gate reads the PR's closes (measured by reading every openspec gate in `scripts/`). Re-measured 2026-11-17, correcting this issue's original evidence (Issue #1109 comment): the named sweep deliveries #1095/#934/#935 were NOT escapes — each PR head (#1100/#1104/#1105) carries an archived change naming its issue (the original grep used the wrong spelling `Issue: #N` vs `**Issue:** [#N]` and read `master` instead of the PR heads), and every closing commit in the last 60 of `master` is likewise tracked. The prong is therefore PREVENTIVE: it fires red on an unbound close (test-locked: `CLOSE of #5001 — NO OpenSpec change names Issue: …` with the `make openspec-new` remedy) and passes every tracked close in history.

## What Changes

- `scripts/openspec_archive_check.py` gains a **fourth prong** in `--pr` mode: every issue the PR closes (already computed by `closing_pr_issues()` through `scripts/pr_closure.py`'s closing-keyword parser) must be named by the `Issue:` line of at least one change — ACTIVE or ARCHIVED — in the PR head's tree, parsed with `openspec_index._refs` (the ONE parser, rule 6d). `closing − referenced` refuses (exit 1) naming each orphaned issue and the remedy: `make openspec-new NAME=…` before implementing (binding `Issue: #<n>`), or `make openspec-record-pr` when a change exists but lost its binding.
- The prong **exempts non-implementing branch shapes** — `pr_closure.KEEPER_BRANCH` (`ci/keeper-*`, #872) and `pr_closure.REFRESH_BRANCH` (`ci/trending-refresh-*`) read from the PR's `headRefName` — the same discrimination `make pr-closure` applies (rule 6e). A keeper/refresh PR closes nothing it implements, so it owes no change.
- `tests/test_openspec_archive_check.py`: the PATH stub `gh` answers `.headRefName` from `FAKE_HEAD_<n>`; new pins prove the refusal shape (closing PR, no change → exit 1 naming issue + remedy), the green shapes (archived change naming the closed issue; active-only mismatch still owned by the #866 prong), and the exemption shapes (keeper/refresh branches).

## Impact

- qa-validate's existing `openspec-archive-check PR=<n>` gate (already run on every PR) now refuses untracked implementations before the squash — no new target, job or pipeline (rules 6d/6m: bundled into the gate the pipeline already runs).
- AGENTS.md §6f gains one sentence naming the enforcement; §8's archive-check row is extended.
- Measured instances #1100/#1104/#1105 are already in flight when this lands; they are named in issue #1109 rather than back-papered (a post-hoc proposal would be paperwork theater).

## Not covered

- No leg creates the change automatically when an implementer skips `make openspec-new` — the gate refuses, the author creates. (Automating creation is a different change.)
- Issues closed by manual human PRs with genuinely no procedural content (pure data appends) still owe a change; §6f says so today. If the owner wants a data-only exemption, that is a separate rule change, not this gate's call.
