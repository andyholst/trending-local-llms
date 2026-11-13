# Proposal: the-owed-section-8-rows

Issues: #391 · #400 · #310 (three of the eleven "§8 row is owed" issues)

## Why

Rule 6c requires a change's guard row in `AGENTS.md` §8 **in the same change**. Three changes
could not write theirs: in a headless bot run, an `AGENTS.md` write is gated behind an approval
prompt that never returned — *"Silence is not consent"* (#310) — so their guards shipped
registered in `make test` and **undiscoverable from the rulebook**, which is the exact drift §8
exists to prevent. The issues each record precisely which row they owe:

- **#400** — a row for `tests/test_ci_wiring.py`: the dead `python3 -m pytest … 2>/dev/null ||`
  branch (pytest is absent from the test image and stderr was discarded, so the intended
  entrypoint never ran while the suite stayed green), a hand-maintained module chain a new test
  could be missed from, a runner that does not stop at the first red, and a suite that discovers
  nothing and reports success.
- **#310** — a row for `tests/test_code_review.py`: an undeclared secret reported with no API
  read; the declared contract not matching the workflows' references in either direction;
  `GITHUB_TOKEN` exempt; a commented reference not counted as a read.
- **#391** — the loop's `$REPORT.notes` scratch file: `: >"$NOTES"` created `qa-report.txt.notes`
  in the checkout root whatever happened, `.gitignore` ignored only the exact name, and a bot's
  `git add -A` committed a **0-byte** file into PR #387 — a non-empty one would publish a hung
  round's notes inside the repository. The rows for `test_scratch_notes_stay_out_of_the_tree`
  and `test_fix_bot_push_behaviour` now name it.

## What Changes

- **§8 gains two rows** (`tests/test_ci_wiring.py`, `tests/test_code_review.py`) and **two
  existing rows are extended** to name the scratch-notes failure.
- **`tests/test_agents_rows.py`** (12 checks) pins them: the rows are present, they name modules
  that exist, the guards they name really live in those modules, and §8 still parses as a table.
- Verified RED against the pre-change `AGENTS.md` (the rows are absent) and GREEN after.

## Impact

`AGENTS.md` (§8 table), `tests/test_agents_rows.py` (new), this OpenSpec change and the
regenerated `OPENSPEC.md`. No code, target, stage, job or image changes.

## Not covered

The other eight "§8/§4/§6j row is owed" issues (#212, #314, #322, #369, #375, #380, #385, #405)
— each names its own exact wording and follows in its own change, so a row is never smuggled in
under a different issue's name.
