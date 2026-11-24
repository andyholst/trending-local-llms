## ADDED Requirements

### Requirement: The printed backup path uses the caller's spelling

The seam SHALL print every destination and `.bak-<UTC>` path in the SPELLING THE CALLER HANDED
(absolute, tilde-expanded, never symlink-resolved), so its output names the tree the operator
pointed at. A home reached through a symlinked ancestor — macOS `/var` -> `/private/var` —
SHALL therefore print `/var/folders/...`, not `/private/var/folders/...`; on a plain tree the
handed and resolved spellings coincide. The printed token SHALL still resolve to the backup
file that exists.

#### Scenario: A macOS-shaped home under a symlinked ancestor

- **Given** a profile home reached through a symlink (the `/var` -> `/private/var` shape) with
  a forward-divergent `SOUL.md`
- **When** `--write` lands the union
- **Then** exactly one `.bak-<UTC>` exists holding the pre-write bytes, the `BACKUP` line
  prints the handed symlinked spelling, and that token resolves to the backup file
- **Test:** tests/test_fleet_host_reconcile.py::test_backup_path_keeps_the_handed_spelling_on_a_symlinked_macos_shaped_home

#### Scenario: A Linux-shaped plain home

- **Given** a profile home with no symlinked ancestor (handed and resolved spellings coincide)
  and a forward-divergent `SOUL.md`
- **When** `--write` lands the union
- **Then** the `BACKUP` line prints the handed path, which resolves to the one backup file
  holding the pre-write bytes
- **Test:** tests/test_fleet_host_reconcile.py::test_backup_path_keeps_the_handed_spelling_on_a_plain_linux_shaped_home
