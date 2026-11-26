# Findings — issue #1767 (implementer-lane mirror)

## The tracked implementer mirrors still describe one serial lane

- **Signature:** implementer-parallel-lane-contract-absent
- **Evidence:** measured on `origin/master` = `37c6d88150fdb73fd0583a59099aee0b418d7927`: neither `agents/tll-implementer/SOUL.md` nor `agents/tll-implementer/skills/tll-implementer/SKILL.md` carries a `## Concurrent-lane contract (issue #1767)` section or any of the owner-mandated concurrent-lane obligations — one issue/worktree/branch per lane, signed claim before work, no shared branch or file edits, a max of 3 live lanes, a `--force-with-lease` push, no master push/merge, and reading the lane's own soul and skill. The new `tests/test_parallel_implementer_lanes.py` overlaid on that base exits 1 with all 15 obligation needles missing; on this head it exits 0.
- **Why:** without the contract in BOTH mirrors, an implementer started from the host profile (or from the repo copy) can start a second issue while another lane holds the branch or file, defeat the lease check or push `master`. A chat-only directive is not a durable rule the lane reloads.
- **Done when:** both mirrors carry the contract and the guard passes on this head and fails on the base text; this PR is READY with `Refs #1767` and does not close the umbrella issue.

## The `AGENTS.md` §8 guard row for the new test is owed (rule 3c)

- **Signature:** owed-row-1767-implementer-guard
- **Evidence:** the owner's 2026-11-26 instruction grants rule-3c sign-off for the #1767 rulebook change and assigns the `AGENTS.md` §7b/§8 edit to a separate subagent. A protected `AGENTS.md` write is outside this subagent's strict file scope, so the §8 row for `tests/test_parallel_implementer_lanes.py` is declared here rather than edited here (rule 3c; rule 6c requires the guard row in the same initiative).
- **Why:** a guard with no §8 row looks unlocked to a later reader, and a headless lane writing the protected rulebook without sign-off is the #1402 failure mode.
- **Done when:** the rulebook owner adds the §8 row naming `tests/test_parallel_implementer_lanes.py` and its RED-on-base guard in the companion PR; `make owed-rows-check` then reports the row LANDED.
- **Owed-row:** <!-- owed-row: section=8 needle=tests/test_parallel_implementer_lanes.py -->
