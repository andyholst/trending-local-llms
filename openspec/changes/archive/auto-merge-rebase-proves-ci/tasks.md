# Tasks: auto-merge-rebase-proves-ci

- [x] Add `github_repo_slug` and prove the rebased head's OWN run through `verify_rebased_ci` in `scripts/pr_health.py` (bounded poll, exact-sha match, ONE gh field contract)
- [x] Return `(pushed, ci_verified, message)` from `rebase_and_push`; report an unverified push as UNVERIFIED in `run_rebaser`
- [x] Make `scripts/auto_merge_rebase.py` report `verdict=rebased`/`rebased=true` only on that proof; a zero-jobs head is `ci-unverified`, exit 1
- [x] Add RED-first guards in `tests/test_auto_merge_rebase.py`: the real seam against a stub remote + planted run list FAILS on a zero-jobs rebased head, proves the healthy direction, and proves a wrong-shaped gh answer is UNPROVEN
- [x] Add the `pr-health REBASE=1` sweep-path guard in `tests/test_pr_health.py`
- [x] Regenerate `OPENSPEC.md` and run the targeted modules plus `make lint`
- [x] Write `findings/1616.md`, update the `ARCHITECTURE.md` rows and the `AGENTS.md` §8 row, push and confirm CI registers on the new head
