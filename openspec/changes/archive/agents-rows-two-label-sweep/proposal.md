# The §6j / §6e rows for the two-label sweep and the tree-evidence verdict, and the §6b / §8 rows #497 owes

**Issue:** [#494](https://github.com/andyholst/trending-local-llms/issues/494),
[#497](https://github.com/andyholst/trending-local-llms/issues/497) (owed by the change that
implements this issue)
**Capability:** `rulebook`

## Why

Two changes shipped their behaviour and their guards but could not write their `AGENTS.md`
rows: the file is protected and the approval prompt never returned in a headless bot run
(rule 3c, the same failure #310/#391/#400/#369 recorded). The code is in the tree and green,
so the rulebook is the only thing that still describes the OLD behaviour — which is worse than
an undocumented feature, because an agent reads the rulebook as authority:

- **§6j** still says the implementer's sweep reads `data-gap-analysis`, while
  `issue_queue.QUEUE_LABELS` reads both actionable labels as ONE oldest-first queue. 48
  `tech-debt` issues — everything the bots' own findings filed — had no reader at all before
  that list existed (#345), so a reader of §6j would re-introduce the starvation.
- **§6e** never mentions the implementer's `TRIAGE` verdict at all: `scripts/issue_verdict.py`
  refuses a `close` or `refine` whose `EVIDENCE:` names no `path:line`, checkable path or
  `make`/`python3`/`gh` command, and that refusal is the only thing standing between a lazy
  close and a buried live gap.
- **§6b** describes `issue-bot.yml`'s trigger surface as one cron slot (`19 * * * *`); the
  pipeline carries a second (`49 * * * *`) because GitHub delays and drops on-the-hour crons.
- **§8** has no row for `tests/test_sweep_alarm.py` (#497), so the delivery alarm that exists
  precisely because a DROPPED cron leaves no run for `queued-alarm` to see is invisible to a
  reader of the guard table.

## What Changes

- `AGENTS.md` **§6j**: the implementer's sweep reads EVERY actionable label
  (`data-gap-analysis`, `tech-debt`) as ONE oldest-first queue, one issue per run, competing on
  age; the reviewer keeps its own `data-gap-analysis` default so a `tech-debt` body is never
  silently refined.
- `AGENTS.md` **§6e**: before its verdict the implementer re-checks the issue against the base
  it fetched (`make base-check`), writes `triage.md` (`implement` / `refine` / `close`), and
  `make issue-verdict` applies it; an `EVIDENCE:` naming nothing in the tree is REFUSED — a
  stale issue is closed on proof, never on prose.
- `AGENTS.md` **§6b**: `issue-bot.yml`'s second schedule slot (`49 * * * *` beside
  `19 * * * *`), the same backup rule `refresh-bot` follows, serialised by
  `concurrency: issue-bot-<n>`, with an idle sweep a green no-op.
- `AGENTS.md` **§8**: rows for
  `tests/test_issue_triage.py::test_three_mock_issues_decide_implement_refine_or_close_against_the_tree`,
  `tests/test_issue_review.py::test_the_queue_reads_both_labels_as_one_oldest_first_list` and
  `tests/test_sweep_alarm.py` (+ `make sweep-alarm`).
- `tests/test_agents_rows.py`: a pin per row, so the ledger cannot rot back to prose — the rows
  are checked for presence, for the module they name, and for the measured failure they catch.

## Impact

Documentation of already-shipped behaviour plus one pinning test. No data, no contract, no
workflow, no `make` target and no script changes, so no value, no schema and no pipeline
behaviour moves; `ARCHITECTURE.md` is unaffected (rule 6h — no target, job, image or script is
added, renamed or removed).

## Not covered

- The behaviour itself: `QUEUE_LABELS`, `scripts/issue_verdict.py`'s evidence gate, the second
  cron slot and `scripts/sweep_alarm.py` already exist and are unchanged here.
- The reviewer's own label default: this change DESCRIBES it, it does not widen it to
  `tech-debt` (a reviewer whose verb is rewriting an issue body must not rewrite a bot's
  evidence-carrying finding).
- Nothing is fixed that a finding names: any gap noticed here is filed, not implemented
  (rule 6g).
