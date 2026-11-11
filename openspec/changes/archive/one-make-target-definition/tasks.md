# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `architecture_bot.py` owns the single scan; `make_targets` (full) and `public_targets` (projection) both derive from it
- [x] 3. `architecture_check.py` imports `public_targets` and drops its own `_TARGET_LINE`/`_SKIP_PREFIX`/local function
- [x] 4. `test_public_targets_are_a_projection_of_the_full_set` asserts public ⊆ full, the exact projection, and no second parser in the check
- [x] 5. Verified RED against the pre-change tree (the check carried its own parser) and GREEN after
- [x] 6. `python3 scripts/openspec_index.py --write` regenerated `OPENSPEC.md`; index + tasks + spec checks green
- [x] 7. `make architecture-check` (the generated §10 block is byte-stable) passes
- [x] 8. `make test` passes (this change adds/updates tests in the same commit, rule 6b)
