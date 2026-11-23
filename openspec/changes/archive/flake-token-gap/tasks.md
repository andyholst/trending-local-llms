# Tasks: flake-token-gap

- [x] Make the token-presence half a declared coverage gap instead of an assertion
- [x] Make the siblings' pass/fail half conditional on a resolved token, tree-clean half hard
- [x] Add the RED-first guards proving the old assertion reddened without a token
- [x] Prove the guards RED against the base revision of the module
- [x] Run `make lint`, the module, and `make test`
- [x] Write `findings.md`, regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Compose the PR body, open the PR, record and archive the change, push and monitor the checks

Evidence:

- **The real failing check, from the runner's own FAIL block** on four branches today
  (`197d190`, `ff0f178`, `cddc532`, `c9291da`): `FAIL #1177: the env contains a token name,
  never a literal in the tree` — not the sibling half #1177's body describes.
- **RED, reproduced on the base module in a token-free identity** (`GH_TOKEN`/`GITHUB_TOKEN`
  unset, `gh` off `PATH`): that exact FAIL line. The same run shows the siblings really do
  exit 1 there (`test_engine_registry.py exit 1`, `test_measurement_attribution.py exit 1`),
  which is the environmental red the old code reported as its own.
- **GREEN, same token-free identity, new code**: `47 passed, 0 failed`, with BOTH halves
  announced through the seam —
  `[coverage-gap] test_the_scratch_subprocesses_inherit_authentication: no GH_TOKEN/…` and
  `[coverage-gap] test_the_measured_suite_modules_leave_the_tree_clean: …`, and the tree-clean
  half still asserted.
- **GREEN with a token**: `51 passed, 0 failed` — the by-name inheritance half is a hard check
  again, so a real regression in it is still red.
- The builders (`_credential_gap`, `_sibling_gap`) BUILD and RETURN; only the caller announces
  (issue #1173), and `make lint` / `make architecture-check` / `tests/test_agents_rows.py`
  (`PASSED 124 | FAILED 0`) are green.
