# Proposal: agents-md-footprint-dimensions

Issue: #375

## Why

`AGENTS.md` §4 describes the canonical store, and its `data/models.json` bullet
lists the optional per-measurement footprint dimensions as **four** keys —
`weight_gb`, `context_tokens`, `system_ram_min`, `storage_offload` — while the
contracts declare **five**: `engine_min_version` was added at measurement level
by #371 (one model-level and one measurement-level occurrence in each of
`data/model_contract.json` and `data/search_contract.json`), and the rulebook was
not brought along.

The rulebook is what every agent and every fix-bot round reads before touching
the store, so a dimension it does not name is a dimension nothing is told it may
carry: a figure whose engine build decides whether it reproduces at all reads as
"not part of the schema" and is dropped from the capture instead of stored. The
`data-gaps` analysis ranks `engine_min_version` as a real requirement dimension,
so the description and the contract disagreeing is the defect, not the gap.

The §4 sentence could not be written from the run that found it (#371's change,
PR #374): `AGENTS.md` is a protected agent-instruction file and rule 3c makes an
`AGENTS.md` change review-required, so that run filed this issue instead of
editing the file — the rulebook's own words for what it owed.

## What Changes

- **`AGENTS.md` §4** — the `data/models.json` bullet's footprint sentence names
  all five optional per-measurement dimensions and says why the fifth belongs on
  the measurement (a version is a property of the engine that produced the
  figure), citing #337 and #371. The sentence is applied verbatim from the
  issue body, which spelled out the exact replacement text.
- **`AGENTS.md` §8** — one guard row for the new pin (rule 6c: the row scrolls
  with the guard).
- **`tests/test_agents_rows.py`** —
  `test_the_footprint_sentence_names_every_dimension` derives the dimension keys
  from the CONTRACT rather than from a list in this file (an optional
  measurement key the model row also carries, i.e. the footprint family, never
  an engagement counter) and fails when §4's sentence does not name one of them.
  A future dimension added to both contracts therefore reds `make test` until
  the rulebook names it, which is the drift this issue exists for.

## Impact

One rulebook sentence, one guard row, one pin in an existing test module, this
tracked change and the regenerated `OPENSPEC.md` index.

Nothing about the data flow changes: the contracts already declare the key
OPTIONAL (rule 3b/6b — no contract edit, so no `*.vN.json`), ingest already
merges it, and `data/models.json` / `data/raw/**` / `data/snapshots/**` are
untouched — hence `README.md` is byte-identical and `check_no_value_loss` has
nothing to compare. No make target, stage, pipeline job, image or script is
added or renamed, so `ARCHITECTURE.md` is unchanged (rule 6h).

Rule 3c is satisfied by this change being reviewable: the issue named the exact
section and the exact sentence, and the diff a reviewer signs off is precisely
that sentence plus its pin.

## Not covered (out of scope)

- `data/MODEL_CONTRACT.md`, the prose companion to `model_contract.json`: it is
  a separate document with its own schema narrative; bringing it in line is a
  distinct judgement about every key it describes, not this one sentence.
- The other owed rulebook sentences filed from the same session's runs. Each is
  its own `tech-debt` issue with its own change (rule 6g — analysis ships
  issues, a fix is one issue).
- Any change to the `data-gaps` ranking, the search prompts, or a backfill of
  `engine_min_version` values — #371 already did the backfill and this change
  only makes the rulebook describe it.
