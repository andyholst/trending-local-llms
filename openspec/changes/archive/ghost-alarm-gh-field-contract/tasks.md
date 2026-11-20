# Tasks: ghost-alarm-gh-field-contract

Issue: #1158

- [x] `scripts/gh_json_fields.py` exists: `RUN_LIST_FIELDS` recorded from gh's own
      `Available fields` output, `request()` refusing an unknown field at build time,
      `check_argv()` validating a whole argv, `scan_scripts()` reading every
      `gh run list` call in `scripts/` through the AST, exit codes 0/1/2 decided loudly.
- [x] `make _check-gh-json-fields` + `make check-gh-json-fields` exist and `make lint`
      bundles the scan; `make lint` runs green with it.
- [x] `tests/test_gh_json_fields.py` locks: the recorded field set equals the real CLI
      answer set; the seam refuses `htmlUrl` and admits `url`; the ghost alarm builds
      `RUNS_JSON` through the seam with no unknown field; the tree scan is green here and
      red on the pre-change shape (`file:line` + `htmlUrl`); an unreadable `--json`
      expression is a finding; a missing `scripts/` tree exits 2; the `--check-argv` mode
      refuses; the wiring (lint bundles it, qa-validate runs lint, no direct workflow call).
- [x] `scripts/ghost_run_alarm.py` asks for `url` (never `htmlUrl`), validates each gh argv
      through `check_argv` before calling, checks the answer shape (array vs `{"jobs": […]}`),
      maps a missing `gh` to the same loud `READ FAILED` exit 2, and prints the URL gh answered.
      Measured live against this repository: the pre-change read printed **50 false ghosts**,
      the fixed read prints **3 real ones** (`44633794376`, `44613011844`, `44037397846`).
- [x] The ghost half of `tests/test_auto_merge_rebase.py`: the stub `gh` refuses a request the
      real CLI refuses and answers the fixed one; the jobs payloads are gh's real shapes; a
      wrong-shaped answer is exit 2 and NOT a ghost verdict; a real `{"jobs": []}` answer is
      still a ghost; a missing `gh` is exit 2 with no traceback.
- [x] `AGENTS.md` §8 carries the guard row for the new scan (attended run, rule 3c sign-off:
      no rulebook rule changed, this §8 row only).
- [x] `ARCHITECTURE.md`: the `lint` group's `check-gh-json-fields` row, the `lint` target row
      updated, the §6 script row for `scripts/gh_json_fields.py`, and the generated inventory
      block regenerated — `make architecture-check` green (166 targets, block matches the tree).
- [x] `findings.md` records what this run found: the answer-shape half (fixed here, annotated
      on #1158) and the filing-worthy finding that the contract covers only `run list` while 52
      `gh … --json` sites exist (`make findings-check` green).

## Gates on the branch head

- [x] `tests/test_gh_json_fields.py` (33 checks) and `tests/test_auto_merge_rebase.py`
      (89 checks) green on this branch.
- [x] `make lint`, `make findings-check`, `make architecture-check`, `make openspec-index`
      green on this branch head.
- [x] Full suite (`scripts/run_tests.sh`, every `tests/test_*.py`) green on this branch head.
- [x] `make openspec-check` green (change validates, spec `Test:` lines resolve, backlog under
      the cap, index current, no unticked box).
