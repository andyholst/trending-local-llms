# Tasks: pr-rebase-soul-generated-artifacts

- [x] Add `OPENSPEC.md` + `ARCHITECTURE.md` §10 to the lane's habitual-conflict list with the regenerate rule
- [x] Add the guard pinning the list in `tests/test_fleet_handover_protocol.py`
- [x] Regenerate `OPENSPEC.md` and run the focused guard + `make lint` + `make architecture-check`
- [x] Run `make test` on the branch head
- [x] Write `findings.md`, commit and push the branch
