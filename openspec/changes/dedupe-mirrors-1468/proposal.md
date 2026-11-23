# Proposal: dedupe-mirrors-1468

Issue: #1468

## Why

PR #1463 landed a four-lane skill-mirror union by concatenation. Where a host note
overlapped a master rule, the merge emitted the shared prose twice and spliced one
bullet mid-sentence: five phrases in the planner mirror are 2× on master but 1× at
base `84cace0b` AND 1× in the host copy (`Dispatch a lane to run ONLY the fast
offline checks`, `Enforce BOTH halves mechanically BEFORE`, ``A head's local `make
validate` ``, `Dispatch the next lane only when`, `queue the rest`), the concurrency
bullet repeats its closing sentence, the `Lanes change locally and PUSH` bullet
carries two copies of the Owner-directive paragraph, line 229 is a dangling fragment,
and the implementer mirror ends `chasing it (#972).` with a dangling `chasing it.`
duplicate. The host-ahead pin was blind to all of it, so `qa-validate` went green.

## What Changes

- Remove only the repeated copies the union invented in
  `agents/tll-planner/skills/tll-planner/SKILL.md` and
  `agents/tll-implementer/skills/tll-implementer/SKILL.md`.
- Keep every genuine rule/note exactly once: base-only sentences (the measured
  7-lane concurrency numbers, the `make dispatch-check` guard text, the
  `#1423` Owner-directive wording) and host-only sentences (the CI-bound status
  note, `Unbounded lanes do not finish faster`) both survive.
- Drop three pre-existing duplicate bullets already present twice at base in the
  planner mirror (`Verify a landed change against origin/master`, `Cron fires run
  WITHOUT approval`, `Do NOT "sync" a host by wiping Hermes runtime stamps`) so no
  duplicated bullet remains in any of the four mirrors.

## Impact

Docs-only. No data, contract, workflow, target or test-logic change. The mirrors
converge toward the host copies, which carry each note exactly once.

## Not covered

- Strengthening the union pin itself (#1469, queued behind this change).
- Re-syncing the host mirrors from master (the reviewer's binding caution until
  this change lands).
