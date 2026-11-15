# Keeper: raise the pipeline-failure ledger row for run 43110467252 (Issue: #833)

Issue: #833
PR: #1067
Binding-exempt: keeper — a data raise observed by the master-alarm red run 43761917321; this change implements no open issue and closes none.

## Why

`make pipeline-failure-guard-check` is RED on the newest push to `master` (run 43761917321, head `6c6b42fb`):

```
pipeline-failure-guard-check: run 43110467252 issue 833: issue CLOSED without a fix PR or a guard test — a closed pipeline failure must carry the change and the test that keep it fixed
```

The fix for #833 DID land: PR #1057 (`fix(tech-debt): implement #833 …`, merged 2026-11-15, `Closes #833`) delivered the guard `tests/test_implement_stream.py`. But its merge never raised the ledger row in `data/pipeline_failures.json` — the row carried `fix_pr: null` beside a CLOSED issue, so the gate refuses and auto-merge is blocked repo-wide (rule 6q: a red push gate has no repairer until a keeper lands).

## What Changes

- `data/pipeline_failures.json`: the entry for `run_id 43110467252` (issue #833) gains its `fix_pr: 1057` (the guard was already raised by the #969 re-diagnosis pass) — filling the null field, additive only (rule 3b: no key removed, no value shrunk; every other row byte-identical).
- `updated_utc` moves to the raise time (a growing counter, rule 3b).
- `tests/test_pipeline_failure_guard.py::test_run_43110467252_is_raised_onto_the_landed_implement_guard` pins the raised row against the committed ledger, the same shape as the #820–#829 row pins.

## Impact

- Unblocks `qa-validate`'s `pipeline-failure-guard-check` gate, hence auto-merge, for every open PR.
- No contract, script, Makefile or gate change. The ledger shape is unchanged — the raise fills a field the filer already declares (`fix_pr`), matching the raised rows #800/#820–#829/#825.

## Not covered

- The pipeline gap that let a merged fix leave its ledger row unraised (no leg stamps `fix_pr` when a pipeline-failure issue closes — the re-diagnosis pass stamps the guard, nothing stamps the fix PR). That is analysis work: filed as a finding by this run's findings.md, never fixed inside this keeper (rule 6g).
