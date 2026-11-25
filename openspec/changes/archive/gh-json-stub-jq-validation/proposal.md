# The ghost-alarm gh stub must refuse what the real gh refuses, for `--jq` too

**Issue:** #1672
PR: #1702
**Capability:** `gh-json-stub-contract`

## Why

`tests/test_auto_merge_rebase.py::STUB_GH_RUNS` is the stub `gh` that drives the
ghost-run alarm (issue #1115). Since #1158 it validates each request through the ONE
field contract (`scripts/gh_json_fields.py --check-argv`), so a stub can no longer answer
a query the real CLI would refuse. But the validation only fires from
`case "$prev" in --json)`, and issue #1668/#1676 extended that SAME contract to
`gh api <path> --jq '<expr>'` projections. Measured on `origin/master` `0c7de7a6`:

```
sh <stub> api repos/o/r/pulls/1 --jq .mergedAtX
  -> exit 3, "unexpected gh: api repos/o/r/pulls/1 --jq .mergedAtX"
python3 scripts/gh_json_fields.py --check-argv gh api repos/o/r/pulls/1 --jq .mergedAtX
  -> asks for .mergedAtX, which the recorded answer shape of that endpoint does not carry
```

So the stub answers (with `unexpected gh`, not a contract refusal) a request the real gh
refuses at RUN time, and a future test that drives a `--jq` call through this stub would
prove nothing about the path it names — rule 6m's exact hole, reopened for the second
recorded family.

## What Changes

- **`tests/test_auto_merge_rebase.py::STUB_GH_RUNS`** — the validation loop fires on
  `--json`, `--jq` and `-q` (once per argv), not only after `--json`, so EVERY request the
  contract has an opinion about is validated by the stub. The stub also gains an `api`
  dispatch answering `$FAKE_API`, so a `--jq` request can be driven end to end (contract
  verdict, then recorded answer) instead of dying at the `*)` branch.
- **`tests/test_auto_merge_rebase.py`** — three pins driving the REAL stub as an external
  stand-in (rule 6m): an unknown `--jq` path is refused, a recorded path answers, and a
  `-q` projection outside its own `--json` list is refused. All three are RED against the
  base revision (the old stub answers none of them).

## Impact

Test-only. No production script, workflow or data changes; the real seam
(`scripts/gh_json_fields.py`) is untouched. The stub becomes contract-complete for both
recorded families (`--json` fields and `gh api … --jq` paths).

## Not covered (out of scope — separate issues)

- The §8 rulebook row that names this guard: `AGENTS.md` is a protected agent-instruction
  file, so a headless leg records it as an owed row (findings + the registered
  `owed-row` marker) rather than editing the rulebook. Declared review-required.
- Any other stub `gh` in the tree; this change covers the ghost-alarm stub named in #1672.
