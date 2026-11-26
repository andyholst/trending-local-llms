# Proposal: wiki-rulebook

Issue: #1773

## Why

The owner directed (2026-11-26) that `tll-architect` owns wiki/documentation freshness, with a
DAILY CI check and a WEEKLY host cron. The duty, the cadence and the new guard were declared in
the issue and the role mirrors, but `AGENTS.md` §7b/§8 carried no `tll-architect` /
`wiki-maintenance` / `docs/archive/` row at base `37c6d881`: a reader of the rulebook could not
learn that false documentation claims must be UPDATED, obsolete pages ARCHIVED with a dated
marker, one evidence-backed issue filed per change, values never invented and generated
artifacts never hand-edited. Rule 3c requires the behaviour to live in the rulebook, not only in a
chat note.

## What Changes

- Add ONE bold-led bullet to `AGENTS.md` §7b naming the architect's wiki-maintenance duty: measure
  doc claims against the fetched tree, UPDATE false statements, ARCHIVE obsolete pages into
  `docs/archive/` with a dated marker, FILE one `enhancement` issue per change with the measured
  evidence, never invent a value, never hand-edit a generated artifact, and keep rule 6t's ONE
  scheduled pipeline with a DAILY CI check plus a WEEKLY host cron.
- Append ONE clause to the single `Rule 3c note:` line recording that this rule was added by issue
  #1773 and is review-required, appended at the END so a sibling landing is never overwritten.
- Add ONE row to `AGENTS.md` §8 naming `tests/test_wiki_rulebook.py` and its three guard functions
  (`test_architect_wiki_role`, `test_wiki_maintenance`, `test_wiki_rulebook`).
- Add `tests/test_wiki_rulebook.py` as a source-level RED-first guard: it fails on the pristine base
  `AGENTS.md` (3 failures), passes on the landed tree, and also refuses any dropped pre-existing
  §7b rule. Register all three functions in the module's `main()`; `scripts/run_tests.sh` discovers
  the module by its `test_*.py` glob.
- Regenerate the root `OPENSPEC.md` index from `openspec/changes/**`.

## Impact

Purely additive documentation plus a test pin: no schema, contract, API, data shape, workflow,
Makefile or script change, and no dead code. No existing rule is removed or narrowed. The only
protected instruction file touched is `AGENTS.md`, authorized by the owner directive on #1773
(the rule-3c sign-off for THIS change); delivery still lands by reviewed PR, never a direct master
push. Disjoint from the sibling #1773 work on the architect role/skill/CI/cron — this change does
not touch `agents/*`, `Makefile`, `scripts/`, `.github/` or host profiles.

## Not covered

- No new GitHub Actions schedule (the DAILY check rides the existing `refresh-bot.yml` cadence),
  no master push or merge, no host cron installation, and no data write.
