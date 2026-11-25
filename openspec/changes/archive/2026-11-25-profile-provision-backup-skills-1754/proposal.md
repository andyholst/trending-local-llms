# Proposal: profile-provision-backup-skills-1754

Issue: #1754
PR: #1755

## Why

`agent-profile-provision` copies a lane's rendered `config.yaml` into the Hermes profile home and
backs the prior config up as `config.yaml.bak-<UTC>` (rule 3b). It also copies the lane's `SOUL.md`
and `skills/` tree over the host home (issue #1214), but copies those WITHOUT a backup. On every
master merge an M-wake must re-provision the fleet (rule 6w), so a legitimate re-sync silently
destroyed host-ahead forward work in `tll-planner/skills/tll-planner/SKILL.md` — measured
2026-11-25 22:38Z, the 60094-byte file carrying the four clauses tracked by #1745 was replaced by
the 58294-byte base copy with no `SKILL.md.bak-…`. `make fleet-host-sync-check` then went GREEN:
the gate read the loss as parity. The forward bytes survived only because an older backup existed.

## What Changes

- `scripts/agent_profile_provision.py` writes a timestamped `*.bak-<UTC>` beside EVERY lane-home
  file it is about to overwrite — `SOUL.md` and every file under `skills/**` — before the copy,
  and prints each backup path in the seam's own output. A collision within the same second gets
  `-2`, `-3`, … so a first backup holding forward work is never overwritten by a later re-run.
- The existing `config.yaml.bak-<UTC>` behaviour and the summary line are unchanged; the new
  per-file lines are additive and carry no credential value (rule 3e).
- `tests/test_agent_profile_provision.py` gains guards that drive the REAL seam over a scratch
  tree with planted host-ahead skill/SOUL bytes, assert the forward bytes survive in a timestamped
  backup, assert the output names it, and prove the guards RED on the pre-change seam.

## Impact

- `scripts/agent_profile_provision.py` — one additive `_backup_file` helper plus the two copy
  sites in `provision_one`; no CLI, target, docstring or contract change.
- `tests/test_agent_profile_provision.py` — three new guards wired into `main()`.
- Host re-provision is now loss-free: the rule-3b guarantee ("no existing value is ever shrunk or
  destroyed") covers host prompt files, not just the tracked data store.

## Not covered

- Deciding whether a host-ahead skill clause is forward work or staleness (#1464/#1745) stays a
  human/reviewer decision; this change only preserves the bytes until that decision lands.
- Landing the four `tll-planner/SKILL.md` forward clauses into the rulebook is #1745, not here.
- No `AGENTS.md` edit, no new `make` target, no workflow/data change: no rule-3c row is owed.
