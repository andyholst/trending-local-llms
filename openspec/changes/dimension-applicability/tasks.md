# Tasks

- [x] 1. Write the proposal + `data-gap-analysis` capability spec for issue #469.
- [x] 2. `DIMENSIONS` entries may carry an `applies` predicate; `storage_offload` carries `_applies_storage_offload` (MoE, ≥ 30B, or a streaming engine).
- [x] 3. `analyse()` splits `missing` from `not_applicable`, skips non-applicable models in the free-text scan, and only signatures dimensions that have a real gap.
- [x] 4. `render()` names the non-applicable set ("cannot apply" section) with the model ids.
- [x] 5. Tests: dense 2B excluded, MoE/70B/Strata included, the dimension leaves the signature once applicable models state it, an empty list never signatures, detector fixtures made applicable.
- [x] 6. Verified RED on `origin/master`'s script (`KeyError: 'not_applicable'`, dense model counted missing) and GREEN after (181 passed).
- [x] 7. `make data-gaps` on the real store: 37 → 23 missing, 58 not applicable, signature unchanged (no re-filing).
- [x] 8. `findings.md` written; `make openspec-check`, `make architecture-check`, `make lint` green.
