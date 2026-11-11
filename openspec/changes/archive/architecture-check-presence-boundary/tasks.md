# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `scripts/architecture_check.py`: `validate_stages()` reads the validator's stage map by AST; every `--only` stage names a registered stage and every stage is selected by one
- [x] 3. `scripts/architecture_check.py`: `described_jobs()` compares §4's job tables/bullets per workflow with `architecture_bot.workflow_jobs` — both directions, plus "no §4 section" as a failure
- [x] 4. `ARCHITECTURE.md`: the guard's boundary is documented and the stale `queued-alarm` `sweep` job row is corrected
- [x] 5. The rulebook half (`AGENTS.md` rule 6h + §8 row) is recorded in `findings.md` — `AGENTS.md` is a protected file this run cannot write, so it becomes its own tracked issue (rule 6g)
- [x] 6. `tests/test_architecture.py`: each new check is proved against a fixture that is wrong, and green against the same fixture fixed; both new checks report the same fixture GREEN under the pre-change guard
- [x] 7. `make architecture-check`, `make lint` and the whole unit suite green on the host (Docker is absent in this run, so the container targets `make test`/`make validate` ran as their bodies: `scripts/run_tests.sh` and `scripts/validate.py`), `validate-mapped` and the full `validate` (links included) green; the only red modules are environment-bound (`test_commit_authorship.py` needs real history, this clone is 1-commit shallow)
- [x] 8. `OPENSPEC.md` regenerated; `openspec-tasks-check` and `openspec-index-check` green. `openspec validate --changes` (the CLI in its image) cannot run here — no Docker/node in this environment — so the structure follows an existing change's shape exactly
