# Tasks

- [x] Record `API_SHAPES` (7 endpoint families, 14 read paths) in `scripts/gh_json_fields.py`, transcribed from live `gh api` reads on 2026-11-24
- [x] Extend `check_argv()` and `scan_scripts()` to read `gh api <path> --jq/-q <expr>` through the AST, resolving f-string endpoints and module/local string bindings
- [x] Refuse an unrecorded path, an unrecorded family, an unreadable endpoint and an unreadable expression; keep the `--json`-projection and fieldless-`gh api` exemptions
- [x] Add the RED-first guards in `tests/test_gh_json_fields.py` (planted `.actor.loginr` goes red; base revision = 7 failed, no traceback) and pin every recorded family
- [x] Update `ARCHITECTURE.md` §3/§6 rows and the Makefile target comment; keep every existing recorded `--json` set pinned
- [~] Extend the `AGENTS.md` §8 row for `tests/test_gh_json_fields.py` so it names the `gh api … --jq` surface too — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Run the focused module (80 passed, 0 failed), `make lint`, `make architecture-check`, `make openspec-check` and regenerate `OPENSPEC.md`
- [x] Write `findings/1668.md` (including the owed-row declaration) and open the PR ready for review
