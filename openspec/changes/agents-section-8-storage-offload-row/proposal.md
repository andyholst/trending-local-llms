# Proposal: agents-section-8-storage-offload-row

Issue: the `tech-debt` issue filed from #364 / PR #366 —
`<!-- tech-debt-signature: agents-section-8-row-owed-for-storage-offload-guard -->`.

## Why

Issue #364 closed the top-ranked `data-gap` dimension (`storage_offload`) and shipped
two guards with it in `tests/test_data_gap_analysis.py`:

    $ grep -n "def test_storage_offload" tests/test_data_gap_analysis.py
    1270:def test_storage_offload_backfill_traces_to_the_captured_source_text():
    1308:def test_storage_offload_coverage_can_never_shrink():

Both are wired into that module's `main()` (lines 1534–1535), so `make test` runs
them. Its rule row, however, was never written: AGENTS.md writes were refused
inside the implementing run (a headless bot run has no approval prompt to answer
— "Silence is not consent", #310), so rule 6c's "the guard's row scrolls with the
guard" was left owed. Measured on the fetched tip, `e793221`:

    $ python3 - <<'EOF'
    ... sec = AGENTS.md[## 8. Regression guards:]
    ... 'storage_offload' in sec
    EOF
    storage_offload in §8: False
    test_storage_offload in §8: False

§8 documents the #163 sibling (`engine_min_version`) and the analysis itself
(#115), but nothing names the #364 guards: a reader of the rulebook cannot find
them, and nothing fails when they are deleted. `tests/test_agents_rows.py` already
pins exactly this class of owed row (#310/#391/#400), so the fix has a home and a
guard.

## What Changes

- **`AGENTS.md` §8 gains one row**, immediately after the
  `tests/test_data_gap_analysis.py — test_engine_min_version_*` (#163) row it
  mirrors, naming both #364 guards and what they catch: a structured
  `storage_offload` whose storage medium / size tokens are absent from the model's
  own captured `data/raw/*.json` text or that traces to no real `…/status/<id>`
  post, a model whose post states no offload being filled anyway, and the closed
  gap silently reopening (coverage floor, the 41/49 the filed issue recorded).
- **`tests/test_agents_rows.py` pins it**, so the row cannot vanish again: the
  §8 table MUST name
  `test_storage_offload_backfill_traces_to_the_captured_source_text`, the
  dimension and the measured 41/49, and the module the row names MUST define both
  guards AND call them from its `main()` (a guard reachable by no target is a
  defect, rule 6d). It FAILS on the pre-change `AGENTS.md`
  (`git show origin/master:AGENTS.md` → 0 hits for `test_storage_offload`).

Documentation only: no data, contract, validator, Makefile target, workflow job,
image or script changes, so `data/models.json`, `README.md` (not rendered from
§8), `ARCHITECTURE.md` (rule 6h: its §10 block derives targets/jobs/scripts, none
of which move) and the validator stages are untouched. AGENTS.md's *behaviour* is
unchanged — the row documents an existing guard, it does not add a rule — so rule
3c's behaviour-change comment does not apply.

## Impact

`AGENTS.md` (one §8 row), `tests/test_agents_rows.py` (the #364 pin + its
docstring), this OpenSpec change and the regenerated `OPENSPEC.md` index.

## Not covered

- **The `storage_offload` values themselves.** #364 backfilled them; this change
  only documents their guard.
- **The other owed §8 rows.** `scripts/check_agent_skills.py --report` still
  prints `AGENTS.md rule (issue #549): OWED (AGENTS.md is write-protected)` — a
  separate rule, its own work item.
- **A general "every `check_*`/`test_*` has a §8 row" gate.** A whole-tree
  completeness rule is a different judgement (which modules need a row, which are
  fixtures) and belongs in its own reviewed change; this change pins the one row
  that was owed.
