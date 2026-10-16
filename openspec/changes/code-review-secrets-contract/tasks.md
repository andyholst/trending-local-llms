# Tasks

- [x] 1. Reproduce #278 on `master`: run 38868116656 — green, with `gh secret list` refused `HTTP 403` and the secrets check reporting `SKIPPED`.
- [x] 2. `scripts/code_review.py`: `DECLARED_SECRETS` — the repo's own secret contract — and `check_secrets_not_defined` driven by it.
- [x] 3. `findings()` runs the secrets check UNCONDITIONALLY (a live read may only union in names); `main()`'s misleading NOTE becomes an INFO.
- [x] 4. `referenced_secrets()` / `_without_comments()` — one implementation, comments excluded (measured: `qa-validate.yml:144` documents the guard with a literal `${{ secrets.X }}`).
- [x] 5. Four tests in `tests/test_code_review.py`, registered in `main()`: reported with no API read; declared + `GITHUB_TOKEN` not reported; the contract equals the workflows' references in BOTH directions; a commented reference is prose.
- [x] 6. Verified RED on `origin/master`'s `scripts/code_review.py` (2 named failures) and green with the fix (28 checks, 0 failures).
- [x] 7. `findings.md` records the sibling credential-gated check AND the owed `AGENTS.md` §8 row (rule 6g) — neither is fixed here.
- [x] 8. `make openspec-check`, `make lint`, `make architecture-check` green.
- [x] 9. Commit, push, open the PR (ready for review, never a draft).

> The `AGENTS.md` §8 row rule 6c asks for is **not a task of this change**: `AGENTS.md` is a
> protected rule file and its write approval did not return, so the row cannot be authored here.
> It is recorded in `findings.md` and filed as its own issue (#212's situation) rather than
> ticked off untruthfully or worked around.
