# Proposal: arm64-smoke-no-pytest-1807

Issue: #1807
PR: #1811

## Why

The arm64 run-proof in `make test-image-smoke` imports `pytest`, but the TEST image
deliberately ships NO pytest (issue #768: tests are scripts, not pytest modules) and
`requirements-test.txt` declares only markdown-it-py, mdurl, pyyaml and tabulate.
Issue #1747 added QEMU before the smoke, which exposed the missing dependency as
`ModuleNotFoundError: No module named 'pytest'` in refresh-bot run 46000947806, job
140514052616. The failing `test-image` job blocked `search`/`aggregate`, leaving the
store ~244 h stale. The gate that pinned the smoke's import line actually asserted
`"import pytest"` was present, so the defect was locked in by a test.

## What Changes

- The `test-image-smoke` recipe proves the arm64 test layer with the libraries the
  image really ships (`markdown_it`, `tabulate`) and no longer imports pytest. One
  mechanism, one arch selector (the existing `--platform linux/arm64`), no publisher
  or image-layer change.
- `tests/test_image_manifest_check.py` stops asserting that pytest is imported and
  gains a guard that the smoke imports the shipped libraries and never imports
  pytest, plus a check that `requirements-test.txt` has no pytest. Proven RED on the
  pristine base (35 passed, 2 failed) and GREEN on the head (37 passed, 0 failed).
- `findings/1807.md` declares the owed AGENTS.md §8 row for the new guard, blocked
  on rule 3c human sign-off — no headless edit of the protected rulebook.

## Impact

- `make test-image-smoke` still takes `TAG=<exact published tag>` and still runs one
  arm64 docker run after the manifest check; only its import probe changes.
- No workflow, new target, new label, schedule, image layer, data or README change.
- The anti-vacuous import proof is preserved: the python -c line still fails loudly
  when the test layer's libraries are missing.

## Not covered

- Installing pytest into the test image — it would reverse issue #768's design and
  make `check-pytest-imports` and the script-based suite inconsistent.
- The SIGPIPE search-leg failure (issue #1808) and the rule-3c §8 row (owed, blocked).
- The arm64 image build/publish itself: the smoke runs against an already published
  tag; this change only makes its proof runnable.
