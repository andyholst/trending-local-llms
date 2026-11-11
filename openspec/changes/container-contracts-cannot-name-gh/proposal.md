# Proposal — container-contracts-cannot-name-gh

Issue: #194
PR: (opened by this change — set at PR open)

## Why

Issue #194 asked `skills/gather-data.md` to carry the `gh pr create --add-label` +
`--add-assignee @me` instructions so every future refresh PR gets the labels the triage pipeline
dispatches on. That instruction was applied to `AGENTS.md` and the legacy `skills/` folder — both
**read by a host-side agent** — while the pipelines that actually run the refresh today are the
`.hermes/skills` container legs (`data-search`, `bot-unattended`, `issue-implement`). Those legs
run in the base image, and `make container-audit` (`scripts/container_audit.py`, since 2026-10-06)
proves the pinned base images carry **no GitHub CLI at all**: `gh` is `MISSING` in
`trending-local-llms:latest`, `…-test:latest` and `…-openspec:latest`, with GitHub writes done
host-side by the workflow steps. So a container-bound contract that tells the agent to run
`gh <subcommand>` is a **lie the agent can only fail on or skip silently** — the exact hazard the
refresh agent itself wrote into `bot-unattended` ("You have no `gh` and no network write. Do not
comment, close, label, or edit anything"). #194's `--add-assignee @me` half is additionally a
no-op here (the owner is already the assignee of every issue in this repo).

What was missing was the **gate**: nothing compared the contracts the legs preload with the
container's real toolset, so the hazard exists in the rulebook text but is unenforced — a future
issue or a careless skill edit can write `gh …` into a leg recipe or a preloaded skill and no
check ever notices.

## What changes

1. `scripts/check_agent_skills.py` grows `GH_ABSENCE` / `GH_COMMAND` / `gh_findings()`: a line that
   INSTRUCTS `gh <subcommand>` (issue/pr/api/repo/label/search/workflow/release/actions) in any
   `hermes -z` leg recipe or any `.hermes/skills/*/SKILL.md` is a finding; a line that
   **forbids** gh or **states gh is absent** (the `bot-unattended` forbiddance — "You have no
   `gh`", "no `gh`", "Do not comment, close, label, or edit anything", "has no gh", "no
   GitHub CLI", "forbid … gh") is the contract itself and is never a finding. `check()` scans the
   recipes AND every preloaded skill, so the scan scope matches exactly what a leg can read.
2. `tests/test_agent_skills.py`: two planted-fixture cases in the defect matrix (a recipe
   instructing `gh issue edit`, a skill instructing `gh pr comment`) plus
   `test_the_gh_guard_refuses_instructions_and_keeps_forbiddances` — the planted fixtures MUST go
   red, the forbiddance wordings MUST stay legal, and the real tree (recipes + all five skills)
   MUST instruct no gh anywhere a leg can read it.
3. `AGENTS.md` §6p gains the sentence the gate enforces, and §8's `tests/test_agent_skills.py`
   row gains the new defect (rule 3c: this issue changes §6p and the §8 row, review-required).

## Impact

- `make check-agent-skills` (bundled into `make lint`, already the FIRST step of qa-validate's
  `validate` job and the fix loop — no new CI wiring needed, rule 6d satisfied).
- No workflow, Makefile recipe, or skill text changes: the gate documents the already-true
  invariant and refuses a future violation.

## Not covered

- Installing `gh` into the base image — deliberately NOT done: the container is token-free by
  design (rule 3e), and the host workflow is where GitHub writes belong.
- The unstructured `skills/gather-data.md` (read host-side, not preloaded by any leg): its
  #194 label guidance stays as written.
- `tests/test_workflows.py`'s gh-state test: already merged (`ci/sweep-comments-662`, commit
  19c70b3) and carried by this branch untouched.
