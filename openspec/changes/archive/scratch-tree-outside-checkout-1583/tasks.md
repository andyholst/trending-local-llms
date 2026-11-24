# Tasks: scratch-tree-outside-checkout-1583

- [x] Add the `_scratch(prefix)` / `_remove(path)` seams to `tests/test_cross_model_attribution.py` and point its E2E replay site at them
- [x] Replace both `shutil_rmtree(tmp, ignore_errors=True)` calls in that module with the loud `_remove`
- [x] Add the same `_scratch(prefix)` / `_remove(path)` seams to `tests/test_weight_gb_contradiction.py` and point its E2E replay site at them
- [x] Replace both `shutil.rmtree(tmp, ignore_errors=True)` calls in that module with the loud `_remove`
- [x] Add the outside-the-checkout + residue guard and the loud-removal guard to EACH module, registered in its `main()`
- [x] Prove all four guards RED against the pre-change behaviour (in-checkout path / `ignore_errors`) — `FAIL the scratch tree is built outside the checkout` and `FAIL a failing removal raises loudly` in each module
- [x] Regenerate `OPENSPEC.md` and run the fast offline gates (`make lint`, the two focused modules)
- [x] Commit on `ci/tech-debt-scratch-tree-1583` and open the PR READY (`Closes #1583` in title AND body)
