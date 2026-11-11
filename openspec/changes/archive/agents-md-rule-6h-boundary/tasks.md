# Tasks

- [x] 1. The tracked change exists (this directory) before the rulebook edit, with its `agents-rulebook` capability spec and this checklist
- [x] 2. `AGENTS.md` rule 6h — the boundary is stated after the presence-failure list: the guard proves PRESENCE and two STRUCTURAL claims (the `--only` stage lists of Makefile targets match `scripts/validate.py`'s stage map; §4's job tables/bullets match the workflows' real `jobs:` keys), and it cannot read prose — a wrong sentence about a real target passes (the write is the review-required diff of rule 3c; the exact text is the one issue #512 spelled out)
- [x] 3. `AGENTS.md` §8 — the `tests/test_architecture.py` row names the two structural checks and the three tests that lock them (`test_validate_only_stage_lists_match_the_validator`, `test_pipeline_job_names_match_the_workflow_job_keys`, `test_doc_states_what_the_guard_does_not_prove`), and the boundary
- [x] 4. The three named tests already exist on master and `make architecture-check` is green — the rulebook change describes enforced behaviour, not a new promise (verified before the edit, not added here)
- [x] 5. `OPENSPEC.md` regenerated (`python3 scripts/openspec_index.py --write`); `make openspec-index-check` and the tasks gate green
- [x] 6. `make lint` green and `make test` green; no code, make target, stage, pipeline job, image, script, contract or data changed (nothing else owes a description — `ARCHITECTURE.md` unchanged, rule 6h)
- [x] 7. `findings.md` records what this run noticed and did not fix (rule 6g)
