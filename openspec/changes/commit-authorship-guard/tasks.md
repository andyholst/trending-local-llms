# Tasks: commit-authorship-guard

- [x] Add `scripts/check_commit_authorship.py` — the identity rule AND the message-trailer rule, with a loud failure on an unreadable range
- [x] Add `tests/test_commit_authorship.py` — one test per rule against real throwaway git repos, plus the pass-on-this-repo self-test
- [x] Add `make check-commit-authorship` + `make commit-authorship-report`
- [x] Wire `tests/test_commit_authorship.py` into `make test`'s `_test` fallback chain
- [x] Add `make check-commit-authorship` to `qa-validate.yml`'s `validate` job and `fetch-depth: 0` to its checkout
- [x] AGENTS.md: the new hard rule + §8 row are **OWED, not written** — a protected rule file whose write approval did not return; recorded in `proposal.md`, in the PR body and filed as its own issue (the #212 / #312 situation). No `rule <id>` citation is left dangling, so `tests/test_rule_numbers.py` stays green (rule 6c)
- [x] Update ARCHITECTURE.md (script, targets, workflow step; rule 6h)
- [x] Regenerate the root `OPENSPEC.md` index (`make openspec-index`)
- [x] Gates green: `make lint`, `make openspec-check`, `make architecture-check`, `make test`
- [x] Commit (Conventional), push the branch, open the PR with `closes #317`; qa-validate green on the PR is the final verification
