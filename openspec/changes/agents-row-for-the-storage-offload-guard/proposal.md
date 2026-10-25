# The §8 guard row `storage_offload` was closed with, written at last

Issue: #369
Capability: `agents-guard-registry`

## Why

Rule 6c requires a change's guard row in the `AGENTS.md` §8 table **in the same change**. The
change that closed the ranked `storage_offload` gap (#364, PR #366 — this tree's
`openspec/changes/data-gap-storage-offload`) could not write its row: in that headless bot run an
`AGENTS.md` write was gated behind an approval prompt that never returned, so it filed #369 instead
of working around the guard. The guard shipped registered in `make test` and **undiscoverable from
the rulebook**.

#369 then sat through two changes that landed the neighbouring owed rows:
`openspec/changes/the-owed-section-8-rows/proposal.md` and
`openspec/changes/land-the-owed-rulebook-rows/proposal.md` both list it under **"Not covered"**,
because *"its own body does not name the test it belongs beside, so the row cannot be written
without re-deriving which guard it means — left open deliberately rather than guessed at"*. Its
body is also truncated mid-clause (`issue.md` lines 5-7 end on `—`, `the`, `(`), so the guard is
not literally named anywhere in it.

It is derivable from the tree, and this change derives it rather than guessing:

- `openspec/changes/data-gap-storage-offload/proposal.md:3` — that change **is** #364.
- `openspec/changes/data-gap-storage-offload/tasks.md` items 4 and 5 name its guards:
  `tests/test_data_gap_analysis.py::test_storage_offload_backfill_traces_to_the_captured_source_text`
  and `::test_storage_offload_coverage_can_never_shrink` — both present today
  (`tests/test_data_gap_analysis.py:1270`, `:1308`).
- `grep -n storage_offload AGENTS.md` returns **only** §4 (lines 649-650): the store may hold the
  key, and **no §8 row names either guard**. The row is genuinely owed.
- *"next to the existing"* (the truncated `Done when:` clause) resolves to the existing
  `tests/test_data_gap_analysis.py` rows in §8 — the #163 `engine_min_version` row is the direct
  precedent (a ranked dimension closed by evidence, same file, same shape).

## What Changes

- **`AGENTS.md` §8 gains ONE row** for the two `storage_offload` guards, placed beside the #163
  `engine_min_version` row: it names both guards and what they catch — a `storage_offload` value
  whose storage medium / size tokens are not in the model's own captured `data/raw/*.json` text (an
  invented value accepted), a `storage_offload` on a model with no real `…/status/<id>` post behind
  it, and the closed dimension silently reopening (a floor of 9 models, and no more models missing
  it than the filed 41/49 plus models added since).
- **`tests/test_agents_rows.py`** pins it, the mechanism that change established
  (`the-owed-section-8-rows`): the row is present, it names both guards, those guards really live
  in the module the row names, and §8 still parses as a table. Proved RED against the pre-change
  `AGENTS.md` and GREEN after.

Additive only, and documentation only: no data, code, target, stage, job, image or README change, so
`ARCHITECTURE.md` is unchanged (rule 6h).

## Impact

`AGENTS.md` (§8 table), `tests/test_agents_rows.py` (one new test block + three checks in the
existing ones), this change and the regenerated `OPENSPEC.md`. `make validate`,
`make validate-mapped`, `make test`, `make architecture-check` are unaffected except that the new
row text must parse as a table row.

Rule 3c: this issue changes **`AGENTS.md` §8** (a guard registry row, not a rule). That part is
review-required — a reviewer signs off on the §8 diff before it merges.

## Not covered (out of scope)

- **The other §8/§4/§6j rows owed by other issues** (#212, #314, #322, #375, #380, #385, #405, and
  the measurement-dimension guards noticed while deriving this one — see `findings.md`). Each keeps
  its own issue and its own wording; a row is never smuggled in under another issue's name.
- **Re-deriving or rewriting #369's body.** The body stays as filed; this change records the
  derivation in the proposal instead of editing the specification it was given.
- **Any change to the guards themselves.** The two tests are unchanged — this writes the row that
  describes them.
