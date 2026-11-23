## ADDED Requirements

### Requirement: A divergent text mirror is classified by direction

The seam SHALL classify a byte-divergent lane mirror as `FORWARD` (every base line still
appears in the host, in order — the host deleted nothing), `STALE` (every host line appears
in the base, in order — the host is behind master) or `MIXED`, and SHALL print the verdict
with the `+/-` line delta. Equal bytes are not divergent and are skipped.

#### Scenario: A forward host that added a note

- **Given** a base `SOUL.md` of `alpha,beta` and a host copy of `alpha,NOTE forward,beta`
- **When** the seam runs report-only
- **Then** it prints `CLASSIFY tll-tester/SOUL.md FORWARD +1/-0` and exits 1
- **Test:** tests/test_fleet_host_reconcile.py::test_forward_host_classifies_and_write_keeps_a_backup

#### Scenario: A stale host missing a master line

- **Given** a base of `alpha,beta,gamma` and a host copy of `alpha,beta`
- **When** the seam runs with `--write`
- **Then** it prints `CLASSIFY tll-tester/SOUL.md STALE +0/-1`, writes the union and exits 0
- **Test:** tests/test_fleet_host_reconcile.py::test_stale_host_restores_master_bytes

#### Scenario: Both sides changed

- **Given** a base of `alpha,beta,gamma` and a host copy of `alpha,NEW,gamma,EXTRA`
- **When** the seam computes the union
- **Then** it prints `MIXED +2/-1`
- **Test:** tests/test_fleet_host_reconcile.py::test_mixed_host_union_is_a_lossless_superset

### Requirement: The union is lossless and drops only an exact duplicate run

The union SHALL be an ordered superset of BOTH inputs — a `replace` opcode keeps the base
chunk AND the host chunk — so master's pinned needles are restored while forward notes
survive. An exact duplicate contiguous run of two or more lines SHALL be dropped, first
occurrence winning, with a loud `[union] dropped a duplicate block (N lines)` report. A
violated invariant SHALL exit 2 writing nothing.

#### Scenario: A mixed mirror keeps every line once, order-preserving

- **Given** a base of `alpha,beta,gamma` and a host copy of `alpha,NEW,gamma,EXTRA`
- **When** `--write` lands the union
- **Then** each of `alpha,beta,gamma,NEW,EXTRA` appears exactly once, master's `alpha,beta,gamma`
  order survives and the host's `NEW` keeps its place
- **Test:** tests/test_fleet_host_reconcile.py::test_mixed_host_union_is_a_lossless_superset

#### Scenario: A bullet block copied twice

- **Given** a host `SOUL.md` carrying `a1,a2,b1` followed by `a1,a2` again
- **When** `--write` lands the union
- **Then** the duplicate run is reported and the result is `a1,a2,b1`
- **Test:** tests/test_fleet_host_reconcile.py::test_duplicate_block_is_dropped_and_reported

### Requirement: Writing is opt-in and backs up first

The default invocation SHALL write nothing; `--write` SHALL write the COMPUTED UNION, never
the host bytes verbatim, and SHALL keep the pre-existing file as `<name>.bak-<UTC>` (never
clobbering an existing backup, rule 3b spirit), printing every backup path.

#### Scenario: Report-only changes neither bytes nor mtime

- **Given** a divergent host file
- **When** the seam runs without `--write`
- **Then** the bytes and mtime are unchanged and no `.bak-*` file appears
- **Test:** tests/test_fleet_host_reconcile.py::test_report_only_leaves_bytes_and_mtime_untouched

#### Scenario: A forward write keeps the old bytes as a backup

- **Given** a forward-divergent host file
- **When** `--write` lands the union
- **Then** exactly one `.bak-<UTC>` exists, its bytes equal the pre-write bytes and its path
  is printed
- **Test:** tests/test_fleet_host_reconcile.py::test_forward_host_classifies_and_write_keeps_a_backup

### Requirement: One destination mechanism serves the host refresh and the reviewed delivery

Without `--dest` the destination SHALL be the host profile home (`<home>/<lane>/<rel>`); with
`DEST=<worktree>` it SHALL be `<dest>/agents/<lane>/<rel>`. In both cases the bytes written
are the computed union, so a raw host copy never enters the tree.

#### Scenario: The repo tree receives the union for review

- **Given** a worktree checked out at the base and a divergent scratch home
- **When** `make fleet-host-reconcile BASE=HEAD DEST=<worktree> WRITE=1` runs
- **Then** `<worktree>/agents/<lane>/<rel>` carries the union and no host byte is copied
- **Test:** tests/test_fleet_host_reconcile.py::test_forward_host_classifies_and_write_keeps_a_backup

### Requirement: Undecidable input is a loud exit 2 writing nothing

A base that is not a commit, a missing profile home or an unreadable base blob SHALL exit 2,
print a `REFUSED` line and leave every file untouched.

#### Scenario: An unresolvable base

- **Given** `--base no-such-ref` and a divergent host file
- **When** the seam runs with `--write`
- **Then** it exits 2, prints `REFUSED` and the file is byte-identical
- **Test:** tests/test_fleet_host_reconcile.py::test_unresolvable_base_exits_two_writing_nothing

### Requirement: The seam is wired to the Makefile, CI and the description

`make fleet-host-reconcile` SHALL exist, `qa-validate`'s `validate` job SHALL call the
read-only half (`BASE=HEAD PROFILES_HOME=agents`), `ARCHITECTURE.md` SHALL document both the
target and `scripts/fleet_host_reconcile.py`, and the suite SHALL be discovered by `make test`.

#### Scenario: Wiring guard

- **Given** a tree where any of the four wiring facts is absent
- **When** the guard runs
- **Then** it fails loudly naming the missing fact
- **Test:** tests/test_fleet_host_reconcile.py::test_the_target_is_wired_to_make_ci_and_the_description
