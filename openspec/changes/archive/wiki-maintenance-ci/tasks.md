# Tasks: wiki-maintenance-ci

- [x] Add `scripts/wiki_maintenance.py` with offline `--check` deriving truth from data/models.json, the README render and the ARCHITECTURE.md inventory — false claims (file+needle, UPDATE) and obsolete docs (evidence, ARCHIVE), loud exit 2 on an unreadable source
- [x] Add the optional `--apply` that prints a keeper PR body with no closing keyword and never mutates a doc
- [x] Add `_wiki-maintenance` / `wiki-maintenance` and `_wiki-maintenance-check` / `wiki-maintenance-check` Makefile targets (internal recipe + public wrapper, single python-env seam, no bare host python)
- [x] Add ONE guarded `wiki-maintenance` job to refresh-bot.yml's existing schedule — no new `on.schedule`, no second workflow
- [x] Add RED-first `tests/test_wiki_maintenance.py` (current green, planted stale/obsolete RED, keeper body, unreadable tree, wiring) and wire it into `make test`
- [x] Write `findings/1773-ci.md` with Evidence/Why/Done-when and the §8 Owed-row
- [x] Regenerate `OPENSPEC.md` and run `make lint`, the focused test, `make pr-closure`, `make check-commit-authorship` and the five-section `pr-message-check`
