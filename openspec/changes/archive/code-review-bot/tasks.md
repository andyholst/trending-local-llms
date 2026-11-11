# Tasks

- [x] 1. Write the proposal + spec for the code-review bot (issue #253, mirrors llgenie #269).
- [x] 2. `scripts/code_review.py`: the deterministic checks (inline scripts, undefined secrets, never-ran, reusable orphan, cron collisions) + the marker-deduped, capped filer; `scan` / `file`.
- [x] 3. `.github/workflows/code-review-bot.yml`: its own slot + `concurrency`, the owner/collaborator/bot guard FIRST with the `schedule` bypass, `make code-review-scan` / `make code-review-file`.
- [x] 4. `make code-review-scan` / `make code-review-file` targets + `.PHONY`.
- [x] 5. `tests/test_code_review.py` wired into `make _test` (the checks, the filer's dedup + cap, the narrowest promise, the wiring, self-consistency).
- [x] 6. README (the generator's template) + `ARCHITECTURE.md`; run `make lint`, `make test`, `make architecture-check`, `make openspec-check`.
- [x] 7. Commit, push, open the PR (closes #253).
