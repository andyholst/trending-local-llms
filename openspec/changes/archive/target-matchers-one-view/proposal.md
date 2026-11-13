# Every target-line matcher is one view of the single Makefile parser

Issue: #752
PR: #913

## Why

Issue #512 unified the two *counting* parsers (126 vs 178) into
`architecture_bot`'s one scan, but #513's analysis left its own finding open:
two *line-level* target matchers stayed as private second copies, and this
session measured a **third** the finding never named:

- `scripts/architecture_check.py::_ANY_TARGET` (`^([A-Za-z_][A-Za-z0-9_-]*):(?!=)`)
  tracks "which target owns this `validate.py --only …` list" with a regex
  byte-identical to `architecture_bot._TARGET_LINE` — a copy that must be kept
  in sync by hand forever.
- `tests/test_architecture_bot.py::_makefile_targets()` re-parses the real
  Makefile with its own looser regex that counts `.PHONY` lines as targets —
  it already disagrees with the shared parser today (the real Makefile has 145
  `.PHONY` lines; the shared scan skips them, the copy does not).
- `tests/test_workflows.py::_makefile_commands()` (line ~2638) carries the same
  looser copy to attribute recipe commands to targets — the third view, never
  listed by the original finding.

Every one of these is a `name:(?!=)` matcher that can drift from the one scan
silently — exactly the class #512 removed for counts.

## What Changes

- `architecture_bot` gains `target_at_line(line)` — the line-level view of the
  one scan (skips `_TARGET_SKIP` prefixes, matches `_TARGET_LINE`).
- `architecture_check.stage_lists()` uses it; `_ANY_TARGET` is deleted.
- `tests/test_architecture_bot.py::_makefile_targets()` delegates to the bot
  module's `make_targets()`; its regex copy is deleted.
- `tests/test_workflows.py::_makefile_commands()` uses the bot module's
  `target_at_line()`; its regex copy is deleted.
- A new guard `tests/test_target_matchers_one_view.py` fails when a target-line
  matcher literal (`:(?!=`) exists outside `architecture_bot.py`, and pins the
  `stage_lists` attribution plus the helper-vs-shared equality against the
  real Makefile.

## Impact

- Capability: `architecture-description` (the generated inventory + its check).
- No behavior change for CI verdicts: the shared view attributes the same
  targets as `_ANY_TARGET` (identical regex) and the helpers' `.PHONY` entries
  were never asserted on.

## Not covered

- Recipe-line classification (tabs) — already the bot module's own logic.
- YAML `on:`-block scanning in `architecture_bot._on_block` — different shape,
  not a Makefile target matcher.

## PR

[will be recorded by `make openspec-record-pr` when the PR opens]
