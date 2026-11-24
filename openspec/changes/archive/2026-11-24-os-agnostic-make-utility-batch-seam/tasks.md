# Tasks: os-agnostic-make-utility-batch-seam

- [x] Route the eight pure utility targets through `$(PYTHON_RUN)` with the `python-env-image` prerequisite
- [x] Extend the Slice 4 seeded set in `tests/test_workflows.py::test_python_env_seam_routes_migrated_recipes_through_the_container` and prove it RED on the pre-change Makefile
- [x] Update the `tests/test_agent_skills.py` pin for the migrated `check-agent-skills` recipe
- [x] Confirm `make -n` expands each migrated recipe to a pure container command and the two `self-archive-*` targets stay host-side
- [x] Run `make lint` and the full `make test` at the exact head
- [x] Regenerate `OPENSPEC.md` and pass `make openspec-check` with every box ticked
- [ ] Write `findings.md`, commit on `fix/os-agnostic-make-utility-batch-1494`, push and open the PR closing #1494
