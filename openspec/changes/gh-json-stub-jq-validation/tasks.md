# Tasks

- [x] 1. Write the proposal + capability spec (issue #1672).
- [x] 2. `STUB_GH_RUNS`: validate on `--json`/`--jq`/`-q` and answer `api` from `$FAKE_API`.
- [x] 3. Pin the stub with three tests driving the REAL stub: unknown `--jq` path refused, recorded path answered, `-q` outside its `--json` list refused.
- [x] 4. RED-prove the new pins against `origin/master`'s `tests/test_auto_merge_rebase.py`; record the counts (`173 passed, 3 failed` on the base stub, `176 passed, 0 failed` with the fix).
- [x] 5. Record the owed §8 row as a finding carrying the registered `owed-row` marker (rule 3c: `AGENTS.md` is protected in a headless leg).
- [x] 6. Gates: `make lint`, the targeted module, `make architecture-check`, `make openspec-check`, `make findings-check`.
- [x] 7. Commit, push, open the PR (`Closes #1672`), then record/archive the change onto that branch with `make openspec-record-pr` and regenerate `OPENSPEC.md`.
