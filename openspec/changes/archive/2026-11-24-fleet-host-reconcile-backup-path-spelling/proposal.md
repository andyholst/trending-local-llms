# Proposal: fleet-host-reconcile backup-path spelling

Issue: #1552
PR: #1588

## Why

`scripts/fleet_host_reconcile.py` builds its profile home with
`Path(args.profiles_home).expanduser().resolve()`, so every path it prints is CANONICAL. On
macOS `/var` is a symlink to `/private/var`, so a `--profiles-home` under `/var/folders/...`
prints as `/private/var/folders/...`, while `tests/test_fleet_host_reconcile.py` builds its
expected needle from the UNRESOLVED temp path. The substring assertion therefore compares
`/var/folders/...` with `/private/var/folders/...` and reds on a healthy mac (measured
`33 ok, 1 FAIL` at `5042cbeb`; reproduced here at base `663c8d9b`). Linux runners have no
symlinked `/var`, so CI is blind to it and the guard's purpose — proving a lossless write — is
defeated on the host that needs it.

## What Changes

- `scripts/fleet_host_reconcile.py`: keep the caller's SPELLING for the profile home —
  absolute (`expanduser().absolute()`) but never symlink-resolved — so the seam's printed
  `BACKUP`/`UNION` paths name the tree the operator pointed at. Reads and writes follow
  symlinks transparently, so classification, union and bytes are unchanged.
- `tests/test_fleet_host_reconcile.py`: pin the agreement with ONE fixture per OS shape —
  a macOS-shaped home reached through a symlinked ancestor (RED against the pre-fix seam on
  any host, because the symlink reproduces `/var` -> `/private/var`), and a Linux-shaped plain
  tree where handed and resolved spellings coincide. Each asserts the backup exists, holds
  the pre-write bytes, is printed in the handed spelling, and resolves to the real file.

## Impact

Non-breaking and additive-test-only in behaviour terms: exit codes, classify verdicts, the
union and the written bytes are untouched; only the printed path spelling changes (from a
canonical rewrite to the caller's own). No new stage, make target, workflow trigger or
rulebook row.

## Not covered

- No change to `make fleet-host-reconcile`'s contract, its Makefile wiring or ARCHITECTURE.md
  rows (the target and script descriptions stay accurate).
- No `AGENTS.md` edit and no `agents/*/SOUL.md` mirror edit.
- No new cron, no CI dispatch, no merge, no master push.
