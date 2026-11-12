# Proposal: duplicate-change-for-one-edit

Issue: #622

## Why

Two changes once proposed the same `AGENTS.md` §4 sentence side by side:
`openspec/changes/agents-md-footprint-dimensions/` (issue #375) and
`openspec/changes/the-owed-section-4-sentence/` (issue #371, CLOSED) — two
proposals, two capability specs and one duplicated Requirement for the SAME
§4 footprint sentence, each naming a different test file (neither of which was
written). `make openspec-check` and `openspec-index-check` prove a change is
well formed and indexed; nothing notices that a second change proposes the same
edit, so a run can land one rule twice (or neither, since each change believed
the other's file carried the pin), and the index a reader must wade through is
inflated by a duplicate entry for one sentence.

## What Changes

- A NEW deterministic gate, `scripts/openspec_duplicate_check.py`
  (`make openspec-duplicate-check`), which runs on every active change and
  FAILS, exit 1, when two DIFFERENT active changes each declare a capability
  Requirement with the SAME heading under the SAME kind (`ADDED`∩`ADDED` or
  `MODIFIED`∩`MODIFIED`), naming both changes, the capability and the heading.
  ADDED∩MODIFIED of one heading is a legitimate refinement chain and is the one
  never flagged — that is exactly how `firecrawl-refusal-is-loud` (ADDED) and
  `outage-verdict-tolerates-a-failed-query` (MODIFIED) coexist today.
- **`make openspec-check`** gains `openspec-duplicate-check` in its dependency
  list and therefore in its `--only` gate (rule 6d: a check reachable only by
  accident is a defect).
- **`tests/test_openspec_duplicate_check.py`** drives the REAL script against
  fixture change trees: the two-header duplication pair (modeled on
  `agents-md-footprint-dimensions` + `the-owed-section-4-sentence`) FAILS
  naming both changes; an ADDED+MODIFIED same-heading pair PASSES (the
  firecrawl/outage shape); unrelated changes PASS; the real repo PASSES.
- **`ARCHITECTURE.md`** describes the script and the target (rule 6h) and its
  regenerated §10 inventory.

## Impact

One new script, one make target wired into the openspec gate, one test module,
this tracked change and the regenerated `OPENSPEC.md` index. No data
(`data/**`), no README, no workflow job, no image. The gate has no network or
`gh` dependency, so it runs in the agent container the way `openspec-tasks-check`
does.

## Not covered (out of scope)

- Comparing proposal **text** beyond requirement headings: a proposal names its
  files in prose that varies in wording, so matching parsed "removes the file
  row" strings would false-positive on clearly-distinct changes. The heading +
  kind pair is the stable, testable duplicate signal.
- Archived changes: a change under `openspec/changes/archive/` is a settled
  record and is never a duplicate candidate (rule 3b — nothing is removed, so
  an old duplicate entry stays visible in the index history).
