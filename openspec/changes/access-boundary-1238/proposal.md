# Proposal: access-boundary-1238

Issue: #1238 (owner directive 2026-11-22)

## Why

Agents in the fleet had no written rule forbidding collaborator / repository access grants. Rule 6u lists owner-only actions (publishing, merging, CI dispatch, rulings) but is silent on access, so a lane could treat an invite or permission change as an ordinary coordination step.

## What Changes

- AGENTS.md §2 gains rule 6v: collaborator / repository access is human-only; agents never grant, request on behalf of, or work around it; the need goes to the shared issue thread.
- `tests/test_access_boundary.py` reads the real rulebook, checks every clause and proves a planted omission is named.
- §8 regression row records the failure mode.

## Capabilities

### New Capabilities
- `agent-access-boundary`: the written, tested rule that only the human owner grants repository access.

### Modified Capabilities
- (none)

## Impact

Rulebook + one test file + one regression row. No data, workflow or credential changes.
