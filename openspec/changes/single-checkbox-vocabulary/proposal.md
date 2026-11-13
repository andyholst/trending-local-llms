# One checkbox vocabulary for both task readers

**Issue:** [#636](https://github.com/andyholst/trending-local-llms/issues/636)
**PR:** [#889](https://github.com/andyholst/trending-local-llms/pull/889)
**Capability:** `openspec-task-checkbox`

## Why

The two readers of an OpenSpec `tasks.md` spell the box vocabulary separately:
`scripts/check_openspec_tasks.py:56` (`_CHECKBOX`) and `scripts/openspec_index.py:53`
(`_TASK_BOX`) are two independent copies of the same regex — added, in the same
change, when `~` became the third state. Nothing makes them agree about what a
task box IS: a fourth state added to one reader is silently a non-task in the
other, which is exactly how `- [~]` read as "all tasks checked" before issue
#409. This is the class rule 6j names for bot markers — one vocabulary, one
implementation.

## What Changes

- **`scripts/task_boxes.py` (new)** — the ONE definition: `BOX_STATES` (the
  bracket characters), `BOX_CORE`/`box_pattern()` (the line shape, composed from
  `BOX_STATES` so a state added there propagates by construction), and the
  classification helpers `open_box()` / `checked()` / `blocked()`.
- **`scripts/check_openspec_tasks.py`** — imports the shared pattern and the
  helpers instead of keeping a private `_CHECKBOX` and its own state
  comparisons; its gate semantics (fence-skipping, the `blocked:` annotation
  rule) stay in the gate.
- **`scripts/openspec_index.py`** — imports the shared MULTILINE pattern and
  the helpers instead of a private `_TASK_BOX` and its own `lower()=="x"` /
  `"~"` comparisons.
- **`tests/test_task_boxes.py` (new)** — proves the vocabulary has one home,
  that both readers classify every state in the vocabulary the same way, and
  that adding a state in the ONE place (a copy of `BOX_STATES` fed to copies of
  both readers, run for real) is seen by both.

## Impact

- No public behaviour changes: same exit codes, same `OPENSPEC.md` rows, same
  failing states. This is pure de-duplication of a shared contract.
- No new `make` target: `task_boxes.py` is a library reached through the two
  targets that already import it (like `engine_registry.py` and
  `bot_markers.py`), with its §6 row in `ARCHITECTURE.md`.

## Not covered

- Fence-handling differences between the readers (the gate skips fenced
  boxes, the index counts them) — deliberate today, and its own question if
  it ever needs unifying.
- The `blocked:` annotation rule, which is gate semantics, not vocabulary.
