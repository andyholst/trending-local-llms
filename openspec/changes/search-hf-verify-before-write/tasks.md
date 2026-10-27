# Tasks

- [ ] 1. Write the proposal + capability spec for the issue (`hf-link-verification`: the search leg looks the id up, a definitive dead id is refused before the snapshot lands, an indeterminate answer is kept, the check is opt-in for callers and on for the CLI, a full link is reduced to its id).
- [ ] 2. `scripts/update_trending.py` — `write_raw_snapshot(..., verify_hf=False)`: check every model `hf` and `formats[].hf` with `hf_repo_resolves`; a definitive 401/404 drops the model (or the bad format entry) with one loud `[write-raw] WARN:` naming the backend, model and id; an indeterminate answer keeps the value.
- [ ] 3. `scripts/update_trending.py` — `normalize_hf_ref` reduces a full link through `hf_id.normalise` after collapsing the `https://huggingface.co/` prefix (one HF-id definition, rule 6d).
- [ ] 4. `scripts/update_trending.py` — `main()` passes `verify_hf=True` to the `--write-raw` call; the default stays `False` for direct callers.
- [ ] 5. `.hermes/skills/data-search/SKILL.md` — the rule that the `hf` id is looked up with the authenticated HF API before it is written, and an unverified id is left out.
- [ ] 6. `tests/test_ingest_hf_verify.py` — write-raw tests: a 404 model dropped with a named warning, a 429 kept, a bad format dropped only, the default makes no request, the CLI turns it on, a full `hf.co` link reduced, and the skill states the lookup.
- [ ] 7. `AGENTS.md` §8 row for the guard, and the `scripts/update_trending.py` row in `ARCHITECTURE.md` names the write-time check (rule 6h).
- [ ] 8. Verified: `make lint`, `make _validate`, `make _test`, the host-side OpenSpec checks, and `make architecture-check` (the Docker-wrapper gates are recorded if the environment has no Docker).
- [ ] 9. `OPENSPEC.md` regenerated with `make openspec-index`.
- [ ] 10. `findings.md` written for what this change found and will not fix here (rule 6g).
