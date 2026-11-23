# Proposal: python-env-seam-in-container

Issue: #1411
PR: #1451

## Why

#712 Slice 3 routes `pr-title`, `pr-body` and `architecture-pr-body` through the ONE
python-env seam, but the seam cannot be exercised from inside the test container: the
image carries no `docker`, so a `$(PYTHON_RUN)` recipe dies `FileNotFoundError: 'docker'`
when `make test` drives it. Measured: 22 red checks across `test_pr_body.py`,
`test_workflows.py` and `test_architecture_bot.py`, every one a missing `docker`.

## What Changes

- Give the ONE `PYTHON_RUN` assignment an `$(if $(IN_CONTAINER),…)` fork: on a host it is
  the pinned harness; inside a container it expands to EMPTY.
- Skip the `python-env-image` ensure step in-container (`ifeq ($(IN_CONTAINER),)`) with a
  SILENT `@:` escape, so a prerequisite can never reach a redirected PR body.
- Route `pr-title`, `pr-body`, `architecture-pr-body` through `python-env-image` +
  `$(PYTHON_RUN)`, each recipe staying a pure `python3 scripts/pr_body.py …` command.
- Extend the Slice-1/2 seam guard with the three targets, add
  `tests/test_python_env_in_container.py`, and force-execute the in-container branch in
  `tests/test_pr_body.py`.
- Restate the three stale `ARCHITECTURE.md` prose rows (rule 6h, review-required docs edit).

## Impact

No data, contract, README, workflow, target, stage, job or image change. Host runs keep
the pinned image; container-inner runs use the container's own interpreter, which is safe
because `requirements-test.in` is `-c requirements.txt` plus test libraries. One issue,
one small non-breaking PR.

## Not covered

- No second `PYTHON_RUN` assignment, and no definition literal in a comment (the Slice-1
  guard counts raw substrings).
- No routing of `refresh-pr-body` (host-only) or the gh-bound keeper-body targets.
