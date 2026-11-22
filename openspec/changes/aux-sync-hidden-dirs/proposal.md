# Proposal: aux-sync-hidden-dirs

Issue: #1217
PR: (pending)

## Why

`make agent-aux-local-sync ALL_PROFILES=1` refused with
`[aux-local-sync] REFUSED: not a profile name: '.deleted'` (exit 2) on a host
that keeps retired profiles in `~/.hermes/profiles/.deleted/`. The all-profiles
enumerator took EVERY child directory of the profiles home and fed the name
through the live-profile name check, so an archive directory made the whole
command unusable; only an explicit `PROFILE=<list>` worked.

## What Changes

- `collect_targets()` skips dot-directories when enumerating `--all-profiles`;
  retired archives are untouched and no longer block the live homes.
- An explicit `--profile .deleted` is STILL refused — skipping hidden names in
  the sweep does not silently accept one when the operator names it.
- A guard in `tests/test_agent_aux_local_sync.py` runs the real seam against a
  scratch home with a hidden archive: green on the new code (47/0), RED on
  `origin/master` with three failures naming the old refusal.
- An AGENTS.md §8 row records the guard.

## Impact

- Only the all-profiles enumeration changes; explicit targeting, backups, the
  auxiliary-block merge and every refusal contract are untouched.
- The guard lives in an already-wired module, so both PR and master-push CI run
  it with no new target or script (rules 6d/6m).

## Not Covered

- Deleting or relocating any retired profile directory (rule 3b: nothing is
  removed by automation; `.deleted/` stays byte-for-byte).
- Changing the profile-name regex or accepting hidden names explicitly.
