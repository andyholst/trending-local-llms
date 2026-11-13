---
name: issue-implement
description: Use when an issue-bot run must triage ONE issue from issue.md against the fetched tree, then either implement exactly its acceptance criteria or write the verdict that retires it.
version: 1.0.0
author: Asimov Agent
license: CC-BY-4.0
metadata:
  hermes:
    tags: [trending-local-llms, bots, issue-bot, implementation]
---

# Issue implementation

The biggest leg: it turns one issue into a reviewable change. The job commits, rebases, opens the
PR and runs the fix loop from what you leave behind, so the tree and the working files are the
deliverable.

## Inputs

- **`issue.md`** at the repo root: the issue, its whole comment thread (author + timestamp) and a
  decision instruction. Its **acceptance criteria are the scope** — implement exactly those, no
  widening, and do not implement a different finding.
- **The tree itself**, which is the freshly fetched `origin/master` (`make base-check` proved it,
  AGENTS.md rule 6n). Every claim in the issue is judged against it, never against the issue's
  words.
- **`AGENTS.md`** — the authority. This skill never overrides it.

## Output

- **`triage.md` first, always**, in the shape the prompt names: `TRIAGE: implement`, or
  `TRIAGE: refine` + `REFINED:` (the restatement that WOULD be implementable, with acceptance
  criteria and the scope boundary), or `TRIAGE: close` + `EVIDENCE:` (a file:line, a command with
  its output, a measured behaviour) + `REASON:`. A close with no evidence block is refused.
- **Only on `TRIAGE: implement`:** the change itself, edited in place in the checkout, plus
  `findings.md` at the repo root.
- A refine or a close implements **nothing**: no code change, no branch, no PR — the workflow
  applies the verdict (one comment, a label, or a close).

## Rules

- **Decide before you edit.** Re-check the issue against the tree: grep the file it names, run the
  command it quotes, read the test it cites. Gone or already fixed → `close` with evidence. Stale
  or wrong text → `refine`. Otherwise → `implement`. A `tech-debt` issue is judged exactly like a
  `data-gap-analysis` one.
- **OpenSpec first, and it is the checklist of record.** Create the tracked change with
  `make openspec-new NAME=<kebab-slug>` before any code; then `proposal.md` (Why / What Changes /
  Not covered), `specs/<capability>/spec.md`
  (one Requirement per behaviour, each Scenario in Given/When/Then with a `- **Test:**` line
  naming the test that locks it) and a `tasks.md` checklist ticked as each step is verified.
  `make openspec-index` then `make openspec-check` before you finish.
- **Additive only** in `data/models.json`, `data/raw/*.json`, `data/snapshots/*.json` and the
  contracts: never remove or rename a key, never shrink a value, and a new key is optional and
  never `required` (AGENTS.md rules 3b/6b).
- **Never fabricate data.** Every value traces to a real X post or a verified upstream source, or
  is marked `(est)`.
- **Wire everything** (rule 6d): a new script, subcommand or validator check is reachable from a
  `make` target CI runs, and the stage's tests change in the same commit (rule 6b).
- **Regenerate what is generated:** `python3 scripts/update_trending.py` when data changed;
  `ARCHITECTURE.md` (rule 6h) and `AGENTS.md` §8 when a target, job, image, script or guard
  changed.
- **Owed rulebook rows never leave a bare `- [ ]` (issue #659).** `AGENTS.md` is a protected
  agent-instruction file: a headless leg has no approver, so its write is REFUSED — that refusal
  is rule 3c working (the sign-off is a human act), not an obstacle to route around. When your
  change owes `AGENTS.md` a row (§6b/§6e/§8 …): (1) the `tasks.md` box for that row is written AT
  CREATION as `- [~] <row> — blocked: rule 3c human sign-off (AGENTS.md protected in a headless
  leg)` — a blocked box is green-but-review-required, while a bare `- [ ]` fails the pre-PR
  `make tasks-check` gate and strands the change (measured: #654–657 died exactly that way);
  (2) record the FULL row text verbatim as a `findings.md` finding with an
  `- **Owed-row:** <!-- owed-row: section=<id> needle="<needle>" -->` line, so
  `make file-findings` files a ledger issue carrying the registered owed-row marker and
  `make owed-rows-check` reports the row LANDED once an attended run applies the diff.
- **Edit the files themselves.** No `*.patch`, `*.rej`, report dumps or backup copies — a change
  written into a patch file is not an implementation. `findings.md` is the ONE working file.
- **Analysis ships issues, never code:** one `## <title>` section per real gap you found, each with
  `**Evidence:**`, `**Why:**`, `**Done when:**`, or the single line `- none`. Never fix a finding
  here. `make findings-check` must pass.
- **Gates only on `TRIAGE: implement`:** `make validate`, `make validate-mapped`, `make test`,
  `make openspec-check`, `make architecture-check` — fix what they report, never weaken a test.
- **Branch naming states what the PR does.** An implementation branch binds its issue —
  `ci/<slug>-<issue>` or `ci/data-gap-<issue>-<slug>` — and the PR body carries ONE
  `Closes #<issue>` bound to it (rule 6e). A PR that only records or unblocks drift observed
  during a run (an archive move, an index or architecture regeneration, a ledger append) is a
  KEEPER: its branch takes the declared keeper shape `ci/keeper-<slug>` or
  `ci/keeper-<slug>-<issue>`, and its body carries `refs #N` and **no** closing keyword —
  `scripts/pr_closure.py` reads a keeper's trailing number as a reference and refuses a keeper
  that writes `Closes #N` as a false claim (issue #872, measured on PR #867).
- **Do not push, do not merge, do not touch `master`.** The job does that.
