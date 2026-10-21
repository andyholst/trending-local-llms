# Tasks

- [x] 1. Re-checked the issue against the fetched base: `refresh-bot` advanced its checkout at the START of `aggregate`, but nothing re-based the generated tree before the PR — the defect still holds (`refresh-bot.yml`, `Commit + open PR if changed`)
- [x] 2. The tracked change exists (this directory) before any code edit
- [x] 3. `scripts/refresh_base.py sync` — reset only the generated files onto the fetched tip, keep the raw snapshots + gap baseline, report `raw_floor`
- [x] 4. `sync` refuses a dirty path outside the generated set and a HEAD with commits of its own
- [x] 5. `scripts/refresh_base.py require-tip` — fetch and fail unless the fetched base is in `HEAD`
- [x] 6. `make refresh-sync` / `make refresh-require-tip` (host targets beside `base-*`)
- [x] 7. `make merge` / `_merge` forward `SINCE=` only when set, so the re-derivation re-ingests this run's raws
- [x] 8. `refresh-bot.yml`: sync + `merge SINCE=` before the branch cut, `require-tip` before the push and the PR, no-change opens no PR
- [x] 9. `tests/test_refresh_base.py` — real git repositories: move/keep, no-op, refusals, stale guard, lost fetch, wiring + order
- [x] 10. `ARCHITECTURE.md` target rows + the generated §10 inventory (`make architecture-refresh`), `make architecture-check` green
- [x] 11. `OPENSPEC.md` regenerated (`make openspec-index`) and the index check green
- [x] 12. `findings.md` written (AGENTS.md rows are protected: filed as their own finding)
