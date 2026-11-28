Issue: #1860
PR: #1863

# Proposal: host-self-correction-1860

Closes #1860.

## Why

The owner directed that CI sync the divergence between host Hermes profile SOUL files and `AGENTS.md` so tll machines self-correct. The read-only gate (`fleet_host_sync_check.py`) refuses divergence, and `qa-validate.yml` runs the reconcile seam report-only, but the reconcile comparison set covered only `SOUL.md` and `skills/<lane>/SKILL.md` — the host `AGENTS.md` was never compared, so a machine could hold a stale rulebook while every check stayed green. There was also no repo-authoritative apply path: the classify/union/backup logic existed but no attended, protected-write-safe way to converge a host.

## What Changes

- Define the comparison set in ONE place (`scripts/fleet_host_sync_check.py`): `MIRROR_RELS` plus the single host `RULEBOOK_REL = "AGENTS.md"` and `PROTECTED_RELS`. `fleet_host_reconcile.py` imports those names (rule 6d); `config.yaml` stays with `agent-profile-provision` (#1401).
- Reconcile the host rulebook against the repo-root `AGENTS.md` with the SAME classify / lossless-union / backup-first path as the lane mirrors. A repo-tree `--rulebook` override keeps the CI proof report-only against a repo tree.
- Add an apply path: `make fleet-host-reconcile BASE=origin/master WRITE=1 PROFILES_HOME=<host> ATTESTED=1`. `ATTESTED=1` (`--attended-signoff`) is REQUIRED when the pending set contains a protected instruction file; without it the run refuses before any backup or write (fail closed, rule 3c). Report-only stays the default.
- Wire CI: `qa-validate.yml` runs the read-only rulebook comparison plus `tests/test_fleet_host_reconcile.py`; no CI step passes `WRITE=1`, so no live host is written from a workflow. No cron and no new Actions schedule.
- Add five guards to `tests/test_fleet_host_reconcile.py` proving STALE converges, FORWARD is preserved, a protected write fails closed, `config.yaml` is untouched, and the Makefile/CI wiring stays in place.

## Impact

Additive seam only. No change to the lane byte contract, no `config.yaml` change, no rulebook or host file edited by this PR, no runtime stamp touched, no data/schema/API change, no cron and no Actions `schedule:`. `report-only` remains the default; the write path can only be used by an attended operator on a host.

## Not covered

- Writing any live host profile home (the owner runs `make fleet-host-reconcile ... WRITE=1 ATTESTED=1` on that machine).
- Rewriting the root `AGENTS.md` rulebook from CI or from a bot lane (rule 3c).
- Host-side cleanup of accumulated duplicate clauses — separate known issues.
