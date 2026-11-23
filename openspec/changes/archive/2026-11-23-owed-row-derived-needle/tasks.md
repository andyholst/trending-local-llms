# Tasks: owed-row-derived-needle

- [x] Refuse a DERIVED needle already present in the declared section
- [x] Guard it RED on #1357's shape (planted fixture + the real `AGENTS.md`) with a positive control
- [x] RED-prove the guard against the base revision of `scripts/owed_row_derive.py`
- [x] Regenerate `ARCHITECTURE.md` after the script docstring edit
- [x] Run the module, `make lint`, `make test`, `make architecture-check`, `make openspec-check`, `make findings-check`
- [~] Extend `AGENTS.md` §8's row for `tests/test_filer_owed_rows.py` to name the already-present-needle refusal — blocked: rule 3c human sign-off (AGENTS.md protected in a headless leg)
- [x] Archive the change by name (`make openspec-archive NAME=owed-row-derived-needle`), regenerate `OPENSPEC.md` and push
