# Tasks

- [x] 1. Proposal + capability spec for `agent-leg-skills` (issue #194): the container has no `gh` (measured by `scripts/container_audit.py`), so a leg recipe or preloaded skill that instructs `gh <subcommand>` is unreachable code; the forbiddance wording stays legal.
- [x] 2. `scripts/check_agent_skills.py`: `GH_ABSENCE` / `GH_COMMAND` / `gh_findings()` — instruct-with-subcommand is a finding, absence/forbiddance wording is not; `check()` scans every leg recipe AND every `.hermes/skills/*/SKILL.md`.
- [x] 3. `tests/test_agent_skills.py`: two planted cases in the defect matrix (a recipe instructing `gh issue edit`, a skill instructing `gh pr comment`) — both turn the gate red.
- [x] 4. `tests/test_agent_skills.py::test_the_gh_guard_refuses_instructions_and_keeps_forbiddances`: planted instruction goes red, `bot-unattended` forbiddance wordings stay green, the real recipes+skills instruct no gh.
- [x] 5. `AGENTS.md` §6p gains the enforced sentence; §8's `tests/test_agent_skills.py` row gains the new defect (rule 3c review-required diff, announced on the issue).
- [x] 6. Local gates green: `make lint` (incl. `check-agent-skills`), `make architecture-check`, and the host-runnable test-module sweep is green — the container-only modules (`faketime`, the Hermes probe, PyYAML) execute in CI's test image, where `make test`, `make validate` and `make openspec-check` run.
- [x] 7. PR opened (not draft) via `make pr-body` with `closes #194`; the rule-3c comment naming the AGENTS.md §6p + §8 diff posted on the issue; `make openspec-record-pr ISSUE=194 PR=<n>` writes the `PR:` line and regenerates the index.
- [~] 8. PR merged green (qa-validate `auto-merge` once `validate` + `live-smoke` are green) and the change archived with `make openspec-archive` + `make openspec-index` in the keeper change that follows the merge — blocked: the merge is owned by qa-validate's auto-merge gate, not this branch.
