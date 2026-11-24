# Proposal: pr-ready-never-draft-1563

Issue: #1563 — "Fleet: never open a draft PR — every fleet PR is ready for review"

## Why

Owner directive 2026-11-24: every fleet PR goes up READY FOR REVIEW, never a draft. A draft is
invisible to reviewers and to `auto-merge` (`scripts/auto_merge_rebase.py` verdict `draft` →
"untouched"), so a finished change can sit green and unlandable, stalling the board and hiding
work that is actually done. Measured on this repo: `gh pr list` answers `isDraft` and
`closingIssuesReferences`, and `scripts/pr_health.py::findings` has always SKIPPED drafts
("a draft is allowed to be quiet") — so nothing named one. The rule was prose in the lane
skills only, with no mechanical signal.

## What Changes

- Extend (do NOT rewrite) `scripts/pr_health.py` with a pure `draft_findings` verdict: an open
  DRAFT that carries a bound issue (GitHub's `closingIssuesReferences`, else the issue its
  branch encodes through `pr_closure`'s ONE parser) is NAMED with that issue number and the one
  remedy. `findings`/`rebase_plan`/`auto_merge_rebase.classify` keep their draft semantics
  untouched. A genuinely unfinished draft binds no issue and is not named.
- Add `--draft-only`: exit 1 only on a bound draft, 0 otherwise — the CI-side assertion. The
  full sweep reports the draft verdict in both modes (additive stdout only).
- Wire `make pr-draft-check` (REPO=) through the Makefile and call it from the existing
  `pr-health.yml` `sweep` job before the full sweep. No `schedule:` added or edited.
- State "open every PR READY (never draft)" in both `agents/tll-planner/skills/tll-planner/SKILL.md`
  and `agents/tll-implementer/skills/tll-implementer/SKILL.md`.
- Describe the new target and workflow step in `ARCHITECTURE.md` and regenerate its inventory.

## Impact

- Additive only: no schema/contract/API/data-shape change, no `agents/*/SOUL.md`, no
  AGENTS.md §7b/§8 edit, no schedule. The silent-PR verdict and the rebaser are unchanged.
- `make pr-health` now prints one extra summary line and, when a bound draft exists, one DRAFT
  line; its exit code is unchanged. `make pr-draft-check` is a new read-only gate.

## Not covered

- Automatically converting a draft to ready (a human/author act; the sweep only names it).
- CI-side `github.event.pull_request.draft` assertion: `pr-health.yml` is dispatch-only with no
  `pull_request` trigger, and adding one would re-run the rebaser sweep on every PR update. The
  assertion is the `make pr-draft-check` seam the dispatch sweep runs; `qa-validate`'s existing
  `auto-merge` `draft == false` guard already refuses a draft at merge time.
