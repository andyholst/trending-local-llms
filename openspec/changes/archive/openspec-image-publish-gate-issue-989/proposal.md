# Proposal: openspec-image-publish-gate-issue-989

**Issue:** #989
PR: #990

## Why

`make rebuild-decision` prints `publish_openspec=yes` when the OpenSpec CLI image's own content-hash tag is MISSING (a publish is needed) — the same polarity as the base image's `built=yes`. `refresh-bot.yml` wired the `openspec-image` job backwards: it built + pushed when `publish_openspec == 'no'` (tag already current) and skipped the build when `'yes'` (tag missing). The first run after a merged `openspec/Dockerfile` change therefore published nothing and died at `make openspec-manifest-check` with `REFUSED (undecidable): docker manifest inspect exited 1: manifest unknown` (exit 2). Measured on runs 43658287668 and 43676720912 (2026-11-15) for tag `openspec-322b2b9f240c`, first needed after merge `aec1410` (#919). The old test pins locked the inversion in place, so the suite stayed green while every refresh went red.

## What Changes

- `refresh-bot.yml`: the `Build + push the OpenSpec image` step gates on `publish_openspec == 'yes'`; the `already current — skip rebuild` step gates on `== 'no'` — the exact mirror of the base image's `built == 'yes'` gating.
- `tests/test_workflows.py`: both pins become step-name-keyed assertions on the actual `if:` of each step (red on the inverted wiring, proven by running them against `origin/master`'s workflow).

## Impact

- Affected specs: `ci-pipelines`
- Affected code: `.github/workflows/refresh-bot.yml`, `tests/test_workflows.py`
- No script or Makefile change: the decision's polarity was already correct and already tested (`tests/test_ensure_image.py`); only the workflow wiring was wrong.

## Not covered

- Re-diagnosis of the two ledger rows for the failed runs (the filer's own re-diagnosis seam — issue #969 — raises them once the fix lands).
- Publishing a tag by hand; the fix makes the weekly refresh do it automatically.
