# Tasks

- [x] 1. Write the proposal + capability spec for the issue (`hf-link-verification`: the search leg looks the id up, a definitive dead id is refused before the snapshot lands, an indeterminate answer is kept, the check is opt-in for callers and on for the CLI, a full link is reduced to its id).
- [x] 2. `scripts/update_trending.py` — `write_raw_snapshot(..., verify_hf=False)`: check every model `hf` and `formats[].hf` with `hf_repo_resolves`; a definitive 401/404 drops the model (or the bad format entry) with one loud `[write-raw] WARN:` naming the backend, model and id; an indeterminate answer keeps the value.
- [x] 3. `scripts/update_trending.py` — `normalize_hf_ref` reduces a full link through `hf_id.normalise` after collapsing the `https://huggingface.co/` prefix (one HF-id definition, rule 6d).
- [x] 4. `scripts/update_trending.py` — `main()` passes `verify_hf=True` to the `--write-raw` call; the default stays `False` for direct callers.
- [x] 5. `.hermes/skills/data-search/SKILL.md` — the rule that the `hf` id is looked up with the authenticated HF API before it is written, and an unverified id is left out.
- [x] 6. `tests/test_ingest_hf_verify.py` — write-raw tests: a 404 model dropped with a named warning, a 429 kept, a bad format dropped only, the default makes no request, the CLI turns it on, a full `hf.co` link reduced, and the skill states the lookup.
- [x] 7. `AGENTS.md` §8 row for the guard, and the `scripts/update_trending.py` row in `ARCHITECTURE.md` names the write-time check (rule 6h).
- [x] 8. Verified: `make lint`, `make _validate`, `make _test`, the host-side OpenSpec checks, and `make architecture-check` (the Docker-wrapper gates are recorded if the environment has no Docker). — done locally: `make lint`, `make validate` (`QA PASSED`, exit 0), `make architecture-check`, `make findings-check`, `make test` and `python3 tests/test_ingest_hf_verify.py` (30/30); the module fails on the pre-change base with `TypeError: write_raw_snapshot() got an unexpected keyword argument 'verify_hf'`, so the pin is real.
- [x] 9. `OPENSPEC.md` regenerated with `make openspec-index`.
- [x] 10. `findings.md` written for what this change found and will not fix here (rule 6g).
