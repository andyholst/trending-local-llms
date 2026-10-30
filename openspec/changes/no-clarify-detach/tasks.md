# Tasks

- [x] 1. The tracked change exists (this directory) before any edit.
- [x] 2. Measured the defect on a real run: the `search (cpu)` leg detaches with `Input required; detached without cancelling` (run 40872677522), and the same shape hit the `amd` leg on 10-26 (run 40407812898).
- [x] 3. `Makefile` `_setup` executes `hermes tools disable clarify`, STRICTLY (an unsupported Hermes build fails the setup so a leg that can still ask cannot be provisioned).
- [x] 4. `tests/test_hermes_prompts.py::test_the_provisioning_seam_disables_clarify` pins the seam (disable present + strict), registered in `main()`.
- [x] 5. `AGENTS.md` §8 row names the guard and the measured failure.
- [x] 6. `make lint` green on the tree (incl. `check-agent-skills`, which treats `_setup` as a leg only when a recipe line mentions `hermes -z` — the added comment avoids that).
- [x] 7. `OPENSPEC.md` regenerated (`make openspec-index`); `make openspec-tasks-check`, `make openspec-index-check`, `make openspec-validate` green.
- [x] 8. `findings.md` written (`make findings-check`).
