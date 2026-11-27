# Proposal: findings-prepush-guard-1804

Issue: #1804

## Why

A host-pushed implementation PR reaches CI without its `findings/<issue>.md` and only
discovers the omission at `make findings-check-for-pr` after a full push and run — measured
on PR #1803 (`fix/ghost-run-head-visibility-1797`), qa-validate run 45992168460, first error
`[findings] FAIL .../findings/1797.md is missing … (Makefile:569)`. The remedy lives only in
a skill pitfall, so each new lane repeats the miss. Rule 6g makes the analysis mandatory; the
failure just arrives too late and costs a diagnosis on two threads plus a repair round.

## What Changes

- `scripts/file_findings.py` gains a `--prepush` mode that reuses the ONE resolution seam the
  CI gate already uses (`analysis_path` → `slice_analysis_path` → `parse`): per-issue file,
  ONE sibling slice when the canonical file is absent, `- none` accepted, malformed or
  ambiguous loudly refused, no issue named is undecidable (exit 2). No shape exemption —
  the lane calls it on its own implementation branch.
- The existing CI-wired `findings-check-for-pr` make target accepts `PREPUSH=1 ISSUE=<n>` so
  the guard is a fast, offline, host-side check with no new target, gate or registry entry.
  The plain invocation stays byte-identical.
- `agents/skills/issue-implement/SKILL.md` tells host lanes to run the guard before any push.
- `tests/test_file_findings.py` is extended with the missing / none / slice / ambiguity /
  wiring guards, RED-proved on the pre-change seam.

## Impact

- CI's shape-aware gate, the plain `findings-check`, and `file-findings` are unchanged.
- No network, no container, no new make target, no workflow edit, no credential.
- The analysis file remains per issue (`findings/<issue>.md`, rule 6g / #1493).

## Not covered

- No `AGENTS.md` edit is made by this headless lane. The owed §8 guard-row extension naming
  `tests/test_file_findings.py`'s new guards is declared blocked (rule 3c human sign-off) in
  `tasks.md` and left to an attended reviewer.
- No change to the shape exemptions, the filing flow, or the gate's CI wiring.
