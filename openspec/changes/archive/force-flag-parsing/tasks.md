# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `scripts/ensure_image.py` has ONE `force_flag(argv)` parser, used by both `publish` and `decide`
- [x] 3. `--force=<bool>`, `--force <bool>` and a bare `--force` are all read; off values are off; a bare flag never raises IndexError
- [x] 4. `Makefile`'s `publish-agent-image` forwards the value (`--force=$(FORCE)`)
- [x] 5. `tests/test_ensure_image.py::test_force_reaches_the_script_as_a_value_not_a_bare_flag` drives the real entry points and asserts the Makefile wiring
- [x] 6. The guard verified RED against the pre-change `Makefile` + `scripts/ensure_image.py` (4 failures) and GREEN after
- [x] 7. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 8. `make lint`, `make test`, `make validate-mapped`, `make architecture-check` and `make openspec-check` green
