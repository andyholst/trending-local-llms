# Record the human-owned index ruling (#1089)

**Issue:** [#1089](https://github.com/andyholst/trending-local-llms/issues/1089)
**Capability:** `auto-merge-index-partition`

## Why

`scripts/auto_merge_rebase.py::classify` returns `verdict=human-owned` for a behind
branch whose head branch is not a bot shape, and the gate leaves it byte-identical.
A human-owned branch cut before a merge wave is therefore still squashed as-is, with
the `OPENSPEC.md` regenerated at BRANCH-CUT time, so the squashed tree can carry an
index that no longer matches the tree it lands into. Issue #1049's Done-when named
the open question as "a human decision" — regen for human-owned branches too, or keep
rule 6s's report-only partition and rely on the keeper — and #1089 was filed because
no issue tracked the ruling. A ruling that lives only in a PR body is exactly the
"analysis ships issues, never code" defect rule 6g exists to prevent.

## What Changes

- **AGENTS.md §6s records the ruling, explicitly.** The report-only partition for a
  human-owned branch is a DECISION, not an accident: `auto-merge-rebase` keeps
  returning `human-owned` (reported, never rewritten), and the declared repair for the
  residual stale index is the event-driven index keeper of §6q — not a rebase of a
  branch only its author can resolve conflicts in.
- **`tests/test_agents_rows.py` locks the ruling** with a phrase assertion over
  `rule_section("6s")`, the same seam the neighbouring §6s rows use, so the rulebook
  cannot silently drop the decision again.

## Out of scope (this change)

- Any change to `scripts/auto_merge_rebase.py`'s verdicts — the behaviour is the
  ruling; only its RECORDING is missing.
- The alternative ruling (regenerate `OPENSPEC.md` for human-owned branches too,
  rewriting a human's branch). That is a different decision and would need its own
  issue + rule 3c sign-off.
- The keeper's implementation (§6q) — it already exists and is unchanged.
