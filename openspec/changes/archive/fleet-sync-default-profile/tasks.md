# Tasks: fleet-sync-default-profile

- [x] Render the base chain and compare the default profile's owned blocks in `scripts/fleet_host_sync_check.py`
- [x] Add the RED-first guards in `tests/test_fleet_lifecycle.py` (synced green, drifted red, missing home named)
- [x] Prove the guard RED against the base revision of the seam
- [x] Run `make lint`, the module, and `make test`
- [x] Write `findings.md`, regenerate `OPENSPEC.md` and run `make openspec-check`
- [x] Compose the PR body, open the PR, record and archive the change, push and monitor the checks

Evidence:

- RED on the base revision of the seam (`git show origin/master:scripts/fleet_host_sync_check.py`):
  `FAIL 4` — the acceptance line, the drifted-default refusal, its named block and the
  named-absent check all fail; the old seam never looks at the default profile.
- GREEN on the new seam: `the default profile's owned blocks` named in the OK line; a
  planted `provider: custom` + `base_url` drift exits 1 naming `profile=default`;
  an absent `config.yaml` is named `SKIP`, never a silent pass.
- The chain is rendered from the BASE blobs (`agents/model_chain.json` + `Makefile`) in a
  scratch root, so local unmerged work cannot launder a stale host.
- `make fleet-host-sync-check BASE=origin/master` on this host: the default profile's owned
  blocks match the render (no drift line); the 8 reported divergences are the host's lane
  bytes against the moved master, a pre-existing host state.
