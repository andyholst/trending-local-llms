# Proposal: architect-wiki-role

Issue: #1773 (tll-architect wiki freshness; the daily CI job, weekly cron and rulebook rows are sibling slices of the same issue)
PR: pending

## Why

The owner directed on 2026-11-26 that `tll-architect` OWNS wiki/documentation freshness: a false doc claim must be UPDATED against the fetched tree, an obsolete page must be ARCHIVED into `docs/archive/` with a dated marker and a pointer, and one `enhancement` issue must be filed per change with measured evidence and the sha. At the freshly fetched base sha `37c6d88150fdb73fd0583a59099aee0b418d7927` none of that behaviour appears in the architect's two in-tree role mirrors or two host profile copies. A duty left in chat is invisible to the next session, so docs can keep contradicting the tree with no accountable lane.

## What Changes

- Add one `## Wiki / documentation freshness (issue #1773)` clause to each of the four role texts: `agents/tll-architect/SOUL.md`, `agents/tll-architect/skills/tll-architect/SKILL.md`, and the two host copies under `~/.hermes/profiles/tll-architect/`. Each clause pins: measure against the fetched tree; UPDATE a false claim; ARCHIVE an obsolete doc with a dated marker and pointer; one `enhancement` issue per change with evidence and sha; never invent a value; never hand-edit a generated artifact; amend the prior 'no cron / no workflow' prohibitions ONLY for this duty; the weekly cron reviews the daily CI findings.
- Add `tests/test_architect_wiki_role.py`, a source-level RED-first guard wired into `main()`: it fails on the pinned base role text (all nine needles absent, measured exit 1) and passes on this head (exit 0). It checks both tree mirrors and, when a host home is mounted, both host copies.
- Add `findings/1773-architect-role.md` with Evidence / Why / Done when and a declared §8 Owed-row for the rulebook lane (rule 3c). Regenerate `OPENSPEC.md` through `scripts/openspec_index.py --write`; never hand-edit it.

## Impact

- Capability: `architect-wiki-role` — the architect lane's written duty to keep wiki/doc claims true against the fetched tree, scoped to role text plus a guard test.
- Scope: one issue, one small non-breaking documentation change; no data, schema, README, Makefile, workflow or `AGENTS.md` byte is touched by this slice. The daily `wiki-maintenance` CI job and the weekly host cron are owned by sibling lanes on #1773 and are referenced, not implemented here.
- Rule 6t is preserved: the daily check rides the ONE existing `refresh-bot.yml` schedule; no second GitHub Actions schedule is introduced by this amendment.
