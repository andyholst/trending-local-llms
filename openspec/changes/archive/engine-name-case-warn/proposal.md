# Proposal: engine-name-case-warn

Issue: #645
PR: #899

## Why

The engines-registry lookup matches names EXACTLY, so the fourth failure on
refresh PR #416 was `engine 'EXLlamaV3' has no repo url in engines registry`
while the registry carries `ExLlamaV3` — a case-only slip first seen as a red
PR hours later. `write_raw_snapshot` normalises `id` and `hf` and verifies the
link fields (#417, #644) but never looks at `engines[].engine`; this is the
same "written without a lookup" class on the engine side (issue #645).

## What Changes

- `write_raw_snapshot` gains a case-slip WARN: when a measurement's engine
  name is absent from the registry but a case-insensitive match exists, print
  one loud `[write-raw] WARN:` naming the backend, the model id, the written
  spelling and the registered spelling.
- The written name is NEVER renamed and the measurement is NEVER refused: a
  genuinely new engine stays unregistered and reds validation for a human
  (AGENTS.md rule 6), and only the search spelling is the thing to fix.
- The check is local (no network): it runs on every write regardless of
  `verify_hf`, and the store read is guarded so a store that cannot be read
  never crashes a search write.

## Impact

- `scripts/update_trending.py` — new `_engine_case_slips()` helper plus the
  WARN pass inside `write_raw_snapshot` (already wired: every `--write-raw`
  leg runs it; no new make target).
- `tests/test_ingest_hf_verify.py` — new
  `test_write_raw_warns_on_engine_name_case_slip` drives the real writer
  against the real registry (rule 6m: no stand-ins).
- `AGENTS.md` §8 gains the guard row.

## Not covered

- Renaming engine names in already-written raw snapshots or the store
  (rule 3b — additive only).
- Auto-registration of genuinely new engines (existing path:
  `scripts/engine_registry.py`, rule 6).
