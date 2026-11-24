# Tasks: fleet-host-reconcile backup-path spelling

- [x] Change `scripts/fleet_host_reconcile.py` to keep the caller's profile-home spelling (`expanduser().absolute()`, never symlink-resolved) so printed `BACKUP`/`UNION` paths are not rewritten (issue #1552)
- [x] Add a macOS-shaped fixture test (home reached through a symlinked ancestor) that is RED against the pre-fix seam and asserts the handed spelling, the pre-write bytes and that the printed token resolves to the real backup
- [x] Add a Linux-shaped plain-tree fixture test pinning the same agreement where handed and resolved spellings coincide
- [x] Wire both fixtures into `main()` so `make test` / pytest execute them (rule 6d)
- [x] RED-verify: base `663c8d9b` + the new module = 40 ok / 2 FAIL; fixed head = 41 ok / 0 FAIL
- [x] Regenerate `OPENSPEC.md` and leave the OpenSpec task/index checks green
