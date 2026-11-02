# Proposal: agents-mirror-sync

Issue: #696 — sync the stale `agents/` SOUL + skill copies from current host profiles
(docs-only), extend to all lanes under the #703 standing-rules uplift, and add the
newly-provisioned lanes.

## Why

`agents/` is the in-tree copy of the host Hermes fleet's profiles. The committed copies
on master were stale (pre-#690 worktree/OpenSpec/testing conventions, and pre-#703
standing rules): several lanes' `SOUL.md` + `SKILL.md` did not match what the host
profiles carry today, and two lanes were missing entirely — `tll-tester` (adopted #703
host uplift this cycle) and `tll-pr-rebase` (newly provisioned on the host, profile live
on the gateway). The planner routed the mirror refresh as a tree-write to the
implementer (#696/#703): re-sync all six lanes' in-tree copies from the updated host
profiles and add the two missing lane rows.

## What Changes

- `agents/README.md` — add the `tll-tester` and `tll-pr-rebase` rows to the fleet table.
- `agents/tll-tester/{SOUL.md,skills/tll-tester/SKILL.md}` — NEW, byte-copied from the
  host `tll-tester` profile.
- `agents/tll-pr-rebase/{SOUL.md,skills/tll-pr-rebase/SKILL.md}` — NEW, byte-copied from
  the host `tll-pr-rebase` profile.
- `agents/tll-{planner,architect,security,reviewer,implementer}/` (`SOUL.md` +
  `skills/<lane>/SKILL.md`) — re-synced byte-for-byte from the current host profiles
  (each now carries the #703 standing rules / the lane's current SOUL), replacing the
  stale pre-#690 copies.

## Impact

Docs-only, additive, non-breaking. No code, no schema, no data, no workflow, no README
regeneration. Every copied file byte-matches its host profile (verified with `cmp`), per
the owner mandate that the host profile and the in-tree mirror must match. Green under
`make openspec-check`, `make lint` and the test suite.

## References

Closes #696. Reflects #703 (the #703 standing-rule lift is what the six updated host
SOULs/skills carry) and #704 (the newly provisioned tll-pr-rebase lane).
