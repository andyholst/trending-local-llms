# Tasks

- [x] 1. `openspec/{config.yaml,Dockerfile,specs/}` exist and the CLI runs only in that image
- [x] 2. `scripts/ensure_image.py` publishes/consumes an `openspec` image tag (one code path, no host npm)
- [x] 3. Makefile: `openspec-image|new|validate|status|archive|shell|tasks-check|index|index-check|check` are wired
- [x] 4. `scripts/check_openspec_tasks.py` fails an ACTIVE change with an unticked `- [ ]` task
- [x] 5. `scripts/openspec_index.py` renders `OPENSPEC.md` and `--check` fails on a stale/missing row
- [x] 6. `scripts/file_findings.py` files one issue per finding, deduped, and fails loudly when the analysis is missing
- [x] 7. The implementer prompt requires the OpenSpec change, the index refresh and `findings.md`
- [x] 8. `qa-validate` runs `make openspec-check`; `refresh-bot` publishes the openspec image; `issue-bot` files the findings only after the loop is green
- [x] 9. Guards exist and are wired into `make test`: `tests/test_check_openspec_tasks.py`, `tests/test_openspec_index.py`, `tests/test_file_findings.py`, plus the workflow/prompt assertions in `tests/test_workflows.py` — each fails on the pre-change code
- [x] 10. `AGENTS.md` states the three rules and lists the new guards in §8; `README.md` documents the targets and the index
- [x] 11. `make test`, `make validate`, `make validate-mapped`, `make openspec-check` and `make secret-scan` are green
