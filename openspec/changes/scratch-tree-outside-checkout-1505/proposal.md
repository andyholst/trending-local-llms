# Proposal: scratch-tree-outside-checkout-1505

Issue: #1505

## Why

`tests/test_ingest_refusal_grouping.py` builds its three ingest-replay scratch trees at `ROOT / "tmp-882-*"` — INSIDE the checkout — and removes them with `shutil.rmtree(tmp, ignore_errors=True)`. Measured on this host during the #1494 work: one such directory survived a full `make test` (root-owned files left by the container identity), stayed untracked and NOT gitignored, and a later `git add -A` swept its files into a rebase index. `ignore_errors=True` is exactly the silent-laundering shape this repo's own guards refuse elsewhere, and a surviving scratch tree is one `git add -A` away from being committed by any lane while silently changing the tree a generated-artifact guard reads.

## What Changes

- Add two module seams in `tests/test_ingest_refusal_grouping.py`: `_scratch(prefix)` builds the replay tree under `tempfile.mkdtemp()` OUTSIDE the checkout (unique per run), and `_remove(path)` deletes it LOUDLY with a bare `shutil.rmtree` — no `ignore_errors`.
- Point all three replay sites (`tmp-882-group-e2e`, `tmp-882-distinct-e2e`, `tmp-882-replay-e2e`) at `_scratch(...)`, and replace every trailing `shutil.rmtree(tmp, ignore_errors=True)` with `_remove(tmp)`.
- `_run_ingest` stops deleting the tree it was handed; the caller owns creation and removal.
- Add two guards: one proves the scratch tree lives outside `ROOT` and leaves no `tmp-882-*` residue inside the checkout, one proves a failing removal raises instead of being swallowed.

## Impact

Test-only. No data format, contract, Makefile target, script, workflow, image or rulebook change; `make test` still reaches the real `ingest_raw_snapshots` through the same subprocess seam. A surviving scratch tree can no longer be staged by a lane's `git add -A`, and a removal that fails is loud.

## Not covered

- No change to the refusal grouping/dedup behaviour, the refusals ledger, or any other test module's scratch paths.
- No CI dispatch, no merge, no master push, no collaborator grant.
