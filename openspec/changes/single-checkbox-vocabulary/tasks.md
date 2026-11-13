# Tasks — single-checkbox-vocabulary (issue #636)

- [x] Add `scripts/task_boxes.py`: `BOX_STATES`, `BOX_CORE`, `box_pattern()`, `BOX_RE`, `BOX_RE_MULTILINE`, `open_box()` / `checked()` / `blocked()` — verified: `python3 tests/test_task_boxes.py` green on the new module
- [x] `scripts/check_openspec_tasks.py` imports the shared pattern/helpers (no private `_CHECKBOX` regex, no private state comparisons) — verified: `python3 tests/test_check_openspec_tasks.py` green
- [x] `scripts/openspec_index.py` imports the shared pattern/helpers (no private `_TASK_BOX` regex, no private state comparisons) — verified: `python3 tests/test_openspec_index.py` green and `make openspec-index-check` green
- [x] `tests/test_task_boxes.py` locks the three spec scenarios (one home; composed pattern; same classification; add-a-state mutation seen by both copies) — verified: green in the suite
- [x] `ARCHITECTURE.md` §6 gains the `scripts/task_boxes.py` row; `make architecture-check` green
- [x] `make test`, `make lint`, `make openspec-check` green with the change active
