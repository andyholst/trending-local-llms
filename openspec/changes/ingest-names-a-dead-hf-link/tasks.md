# Tasks

- [x] 1. Write the proposal + capability spec for issue #333 (`hf-link-verification`: only a definitive answer is a finding, a merge names a NEW model's dead repo, the check is opt-in for callers and on for the CLI).
- [x] 2. `scripts/update_trending.py` — `hf_repo_resolves`: True / definitive False on 401+404 / None on transport error, 403, 429, 5xx, or a value that is not `owner/repo`; `HF_MODEL_API` is the endpoint seam.
- [x] 3. `scripts/update_trending.py` — `note_unresolved_hf`: one loud line per definitively dead `hf` / `format-hf`, naming the id and the model.
- [x] 4. `scripts/update_trending.py` — `ingest_raw_snapshots(..., verify_hf=False)` checks only models ADDED this merge; `main()` passes `verify_hf=True`.
- [x] 5. `tests/test_ingest_hf_verify.py` (new) — a real local HF stand-in for the 200/401/404/429/500 classification, the loud line and its silence, no request for an existing model, no request under the default, and the CLI wiring.
- [x] 6. `Makefile`: the new module added to the `_test` fallback chain, so the existing "every `tests/test_*.py` runs" guard stays green.
- [x] 7. `ARCHITECTURE.md` (rule 6h): the `scripts/update_trending.py` row describes the verification and its seam.
- [x] 8. Verified: `make test`, `make validate`, `make lint`, `make openspec-check`, `make architecture-check` green.
- [x] 9. `OPENSPEC.md` regenerated (`make openspec-index`).
- [x] 10. `findings.md` written for the §8 row this change owes and cannot write (protected file).
