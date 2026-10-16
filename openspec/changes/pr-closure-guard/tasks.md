# Tasks

- [x] 1. Write the proposal + capability spec for issue #284 (`pr-lifecycle`: a merged PR closes the issue it implements).
- [x] 2. `AGENTS.md` rule 6e: one closing keyword bound to the issue the branch implements; a PR that implements no issue closes none (the refresh PR references its tracking issue). Disclosed on #284 per rule 3c, and its §8 guard row added.
- [x] 3. `scripts/pr_closure.py` — the ONE implementation: derives the branch's issue (its FIRST number, so the title slug cannot win; a refresh branch implements none), refuses a chained reference, a missing keyword for the branch issue, and a keyword on a PR that implements no issue; reads the webhook payload by path.
- [x] 4. `make pr-closure` (host-side, image-free) wired into `qa-validate`'s `validate` job; `.github/workflows/refresh-bot.yml`'s `Closes #1` → `Refs #1`.
- [x] 5. `tests/test_pr_closure.py` — the two measured bodies refused, the correct forms accepted, the branch-issue derivation pinned, every GitHub closing keyword recognised, the CLI driven over real event payload files, and the wiring asserted. In the `make _test` chain.
- [x] 6. `ARCHITECTURE.md` (rule 6h): the script row and the new `validate` step.
- [x] 7. Verified: the guard FAILS on the pre-change workflows (2 named checks red against `git show origin/master:…` for `qa-validate.yml` and `refresh-bot.yml`), and passes on this tree; `make lint`, `make openspec-check`, `make architecture-check`, `make test` green.
- [x] 8. Code is not a claim: a closing keyword inside a fenced block or an inline code span is ignored, because GitHub links nothing there — found while dogfooding (this change's own PR says `Closes #284` in backticks, and GitHub's `closingIssuesReferences` came back EMPTY while a naive parse read it as a binding). The report in `main()` uses the same stripped view.
- [x] 9. `findings.md` written (`make findings-check` green) and `OPENSPEC.md` regenerated (`make openspec-index`).
