# Proposal: test-suite-identity-and-coverage-gaps

Issue: #1147 — "The test container runs as the image's default uid while the
suite assumes the invoking uid: assert the uid and REPORT the bypass"
PR: (recorded by `make openspec-record-pr` when the PR opens)

## Why

Two measured states, one root cause — the suite cannot say what it did not run.

1. `make test` answered "136 modules green" and never said WHOSE uid measured
   them. `TEST_RUN` (Makefile) starts every test container through
   `scripts/docker_test_run.sh` and passes no `--user`, so the container runs as
   the image's default user — verified live on this host: `docker exec
   tll-test-3965-16821 id -u` → `0` — while the host half of the suite
   (`scripts/run_tests.sh`, `tests/hermes_home.py`, every permission plant)
   assumes the invoking uid. The mismatch is invisible in the verdict.

2. `tests/test_agent_skills.py`'s permission half printed `SKIP teardown: …
   permission plant bypassed (uid 0 — DAC_OVERRIDE …)` and returned, so its
   module exited 0 — measured in CI: qa-validate run 44551541279, 135 modules
   green, where the planted mode-0o000 tree was removed cleanly by uid 0 and the
   guard then died on its own cleanup `chmod`. A green run carried a half-covered
   guard and the verdict said nothing about it, because a passing module's output
   was `mktemp`'d and deleted unread (the issue #911 shape #911 fixed only for
   the suite-level capture).

The fix is not "make the plant work under uid 0" (that is a different change):
it is that the suite REPORTS the identity it measured and the coverage it did
not get, loudly, through one seam.

## What Changes

- **`scripts/coverage_gap.py` (new, stdlib-only)** — the ONE definition (rule 6d)
  of `IDENTITY_PREFIX`/`identity_line()`, `GAP_PREFIX`/`declare_gap`/
  `declare_bypass_gap`, `BYPASS_PHRASE` and `scan_module_output`, plus the CLI
  `--gap-prefix | --phrase | --identity-line` the bash runner reads. A shell
  guard and a Python guard can now share the strings without either re-spelling
  them; a renamed marker used to raise nothing and simply read as "no gap was
  declared".
- **`scripts/run_tests.sh`** — reads all three strings from the seam (a seam it
  cannot read exits 2, never a vacuous clean); prints the suite identity line
  before any verdict (`container uid… invoking uid… run-as=…`); and scans EVERY
  module's output — including a passing one, whose output used to be deleted
  unread — so a declared gap is named in the verdict (`[harness] coverage-gap N
  declared …`) and a bypass phrase that never travelled inside the declared
  `[coverage-gap]` seam turns the run red naming the module, the issue and the fix.
- **`scripts/docker_test_run.sh`** — prints the invoking `uid:gid` and forwards it
  into the container as `TLL_INVOKING_UID` (a variable NAME, never a value, rule 3e)
  so the identity line inside the container can state whether the container ran as
  the invoker or as the image's default user. It still passes no `--user`.
- **`Makefile` `test:` recipe** — the capture it tees must contain the identity line
  (`[harness] suite identity:`) or the gate refuses, alongside the issue #911
  empty-capture guard; it also counts the declared coverage-gap reports it captured.
- **`tests/test_agent_skills.py`** — the permission half declares its gap through
  the seam instead of printing a bare `SKIP`; the always-checked half
  (stuck-ness no privilege can override) still locks the teardown contract.
- **`tests/test_test_container_identity.py` (new module)** — runs the REAL runner
  over planted fixture dirs, the REAL wrapper against a stub `docker` on PATH, and
  the REAL `make test` recipe (rule 6m; only external stand-ins).
- **Docs**: `ARCHITECTURE.md` §6 rows (new `scripts/coverage_gap.py` row, extended
  `run_tests.sh` / `docker_test_run.sh` rows) + `make architecture-refresh` for the
  generated inventory; `AGENTS.md` changes ONLY in §8 (a new regression-guard row
  plus the updated clause on the issue #1145 row) — no §1–§7 rule text changes, so
  no rule-3c behaviour change is required (rule 6c: guard row + test together).

## Impact

- Capabilities: `test-runner` (identity line, declared gaps, undeclared-bypass
  refusal, one seam for the strings) and `test-container` (the wrapper names and
  forwards the invoking identity).
- Spec deltas: `specs/test-runner/spec.md`, `specs/test-container/spec.md`.
- Tests: `tests/test_test_container_identity.py` (new, auto-discovered),
  `tests/test_test_capture_guard.py` (extended), `tests/test_agent_skills.py`
  (the bypass half now reports through the seam).
- Data (`data/models.json`, `data/raw/*`, contracts): none. Pipeline/data
  contracts: none. No workflow changed.

## Not covered

- Running the test container under the invoker's identity (`--user=$(id -u):$(id -g)`
  in `TEST_RUN`) so the permission plants are honoured IN CI as well as on the
  host. That is the acquisition half of this gap and is filed as its own
  `tech-debt` finding (`findings.md`), never fixed inside the change that found it
  (rule 6g).
- Any other guard that silently skips: this change gives the suite the mechanism
  and the refusal; converting each existing silent skip is per-guard follow-up work.
- Fixing `DAC_OVERRIDE` behaviour in the image: uid 0 legitimately bypasses a
  mode-0o000 directory, so the honest state is a DECLARED gap, not a fake failure.
