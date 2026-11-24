# Proposal: scratch-tree-outside-checkout-1583

Issue: #1583
PR: #1590

## Why

The #1505 change (`scratch-tree-outside-checkout-1505`, PR #1574) fixed the exact
shape in `tests/test_ingest_refusal_grouping.py` — an ingest-replay scratch tree
built at `ROOT / "tmp-…"` INSIDE the checkout and removed with
`shutil.rmtree(tmp, ignore_errors=True)` — and deliberately left the two sibling
modules carrying the same shape for their own issue (rule 6g). This is that issue.
Measured on `origin/master` at `663c8d9b`:

- `tests/test_cross_model_attribution.py:493` sets
  `tmp = ROOT / "tmp-ig702-e2e"` and removes it at lines 495 and 511 with
  `shutil_rmtree(tmp, ignore_errors=True)`.
- `tests/test_weight_gb_contradiction.py:248` sets
  `tmp = ROOT / "tmp-ig615-e2e"` and removes it at lines 249 and 264 with
  `shutil.rmtree(tmp, ignore_errors=True)`.

Both are untracked, NOT gitignored scratch directories inside the repository
working tree, so a surviving one is one `git add -A` away from being committed by
any lane, and a failed cleanup is swallowed silently — the same silent-laundering
shape that let the #1494 sweep stage thousands of scratch files.

## What Changes

- Add the same two module seams to each of the two modules: `_scratch(prefix)`
  builds the replay tree under `tempfile.mkdtemp()` OUTSIDE the checkout (unique
  per run), and `_remove(path)` deletes it LOUDLY with a bare `shutil.rmtree` — no
  `ignore_errors`.
- Point each module's E2E replay site at `_scratch(...)` and replace both
  `shutil.rmtree(..., ignore_errors=True)` calls in each module with `_remove(...)`.
- Add one guard per module, registered in its `main()`: the scratch tree lives
  outside `ROOT` and leaves no `tmp-<module>-*` residue inside the checkout, and a
  failing removal raises instead of being swallowed.

## Impact

Test-only. No data format, contract, Makefile target, script, workflow, image or
rulebook change; each module still drives the real `ingest_raw_snapshots` through
the same subprocess seam with no mock. A surviving scratch tree can no longer be
staged by a lane's `git add -A`, and a removal that fails is loud.

## Not covered

- No change to `tests/test_ingest_refusal_grouping.py` (#1505 already landed there).
- No change to any refusal rule, the store, the ingest behaviour, or the two
  modules' own assertions about the pipeline.
- No CI dispatch, no merge, no master push, no collaborator grant.
