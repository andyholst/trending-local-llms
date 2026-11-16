# Tasks: keeper-pr-one-landing-sequence

- [x] `scripts/keeper_pr.py` implements the ONE landing sequence (nothing-to-land 0, refuse-extra 1, #960 mergeable-only dedupe, agent-identity one-commit branch, body via the keeper's own target, `gh pr create`, failure 2) — verified: `make test` (test_keeper_pr)
- [x] `Makefile` defines `_keeper-pr` + public `keeper-pr` reaching the script — verified: `make keeper-pr` dry-run inside the test scene + `make lint`
- [x] `qa-validate.yml` `index-repair` land step replaced by `make keeper-pr FILE=OPENSPEC.md … DEDUPE=1` — verified: `make test` (test_workflows keeper pins + test_keeper_pr scan)
- [x] `qa-validate.yml` `architecture-repair` land step replaced by `make keeper-pr FILE=ARCHITECTURE.md … DEDUPE=1` — verified: same
- [x] `queued-alarm.yml` ledger land step replaced by `make keeper-pr FILE=data/pipeline_failures.json …` (no DEDUPE, per #802 semantics) — verified: same
- [x] `tests/test_keeper_pr.py` drives the real script end-to-end (real git remote, `gh` PATH stub) and the Done-when scan refuses re-spelled landing shells — verified: `make test`
- [x] `tests/test_workflows.py` + `tests/test_pipeline_failure_issue.py` pins moved to the seam (rule 6c) — verified: `make test`
- [x] `ARCHITECTURE.md` §4 job rows, §6 target + script rows, generated block refreshed — verified: `make architecture-check`
- [x] `AGENTS.md` §8 guard row for `tests/test_keeper_pr.py` — verified: shipped in this change
