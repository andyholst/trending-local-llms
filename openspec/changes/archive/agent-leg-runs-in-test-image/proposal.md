# Agent legs that self-verify run in the TEST image, not the base (issue #833)

**Issue:** [#833](https://github.com/andyholst/trending-local-llms/issues/833)
PR: #1057
**Capability:** `agent-leg-runs-in-test-image`

## Why

A scheduled issue-bot sweep failed (run 43110467252) because the implementer
leg's OWN self-verification could not run the canonical suite: `make
implement-issue` (and the sibling `review-issue`, `review-issue-window` and
`fix` legs) runs the agent inside the **base** image (`$(DOCKER_RUN)`), whose
python lacks `markdown-it-py`. When the agent verifies its work by running
`python3 scripts/run_tests.sh` (or `test_amd_backend.py`) inside that
container, `check_readme_tables_wellformed` reports
`readme-tables: 'markdown-it-py' is not installed` and the module FAILS — even
though the deterministic gates that will judge the change (`make test`, `make
validate`) run inside the **TEST** image (`$(TEST_RUN)`), which lays
`requirements-test.txt` (`markdown-it-py`, `pyyaml`, `tabulate`) on top of the
base. The agent's own environment therefore disagrees with the gates it must
pass, producing a false red the workload has to dismiss and derailing the run.

`test_amd_backend.py` drives exactly that validator and FAILS (exit 1) on a
python without `markdown-it-py`, while passing under the TEST image — measured
on this repository both ways. The agent legs that must guard their own change
against the canonical suite must run in the image that can execute it.

## What Changes

- Makefile: the four agent legs that self-verify against the canonical suite —
  `implement-issue`, `review-issue`, `review-issue-window`, and `fix` — run via
  `$(TEST_RUN)` (the TEST image, `base + requirements-test.txt`) instead of
  `$(DOCKER_RUN)` (the base image). The TEST image is built `FROM` the base, so
  it still carries the Hermes CLI, the pinned nerve plugin and every base
  system/`requirements.txt` dependency — it is a strict superset that ADDS the
  readme-table validator's deps. A leg that must pass `make test`/`make
  validate` now runs in the same image CI uses for those gates.
- The non-verifying search legs (`search-nvidia/metal/cpu/amd`) stay on
  `$(DOCKER_RUN)`: they scrape and write raw snapshots and never run the
  canonical suite, so the cheaper base image remains correct for them.
- Guard tests: the shipped agent-leg wiring is pinned to the TEST image, so an
  implementer/reviewer/fixer can run `run_tests.sh` in its own environment; and
  the declaration that `markdown-it-py` (the test dep the validator needs)
  lives ONLY in `requirements-test.in`, never the base `requirements.in` — the
  precondition that makes the base image the wrong place for these legs.

## Out of scope

- No change to `make test`/`make validate` themselves — they already run in the
  TEST image; this change aligns the legs that invoke them in-container.
- No change to the search legs' image, the base image's dependency set, or the
  OpenSpec/architecture tool images.
- Not fixing the specific 2026-11-11 run's cascade downstream of the false red
  (a leftover file without a trailing newline, the fix loop's round-cap
  timeout, a missing `findings.md`) — those are consequence-of-the-run failures
  already guarded separately; this change removes the environment divergence
  that set the run up to derail.
