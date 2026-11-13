# Proposal: owed-rules-blocked-box

Issue: #659

## Why

`AGENTS.md` is a protected agent-instruction file: a detached (headless)
implementation leg has no approver, so its write is REFUSED
(`consent-gated file write ... was denied by the user (non-interactive mode)` —
measured in #654, #655, #656, #657, four consecutive bot runs whose agent
reasoned correctly, applied nothing, and left a bare `- [ ]` in `tasks.md`).
With the pre-PR `make tasks-check` gate (issue #658) that bare box now refuses
the PR before it opens, so the change strands and the rulebook row is simply
never declared anywhere. Measured consequence: bot changes that owed
AGENTS.md §6j/§8 rows went red, and the rulebook still described the
pre-guard behaviour (rule 3c starvation, #345-class).

The refusal is not a bug to route around — the sign-off is a human act
(rule 3c). The defect is that the owed row is UNDECLARED: the headless leg has
no contract that says "when the write is refused, write the box blocked AT
CREATION and hand the FULL row text to the owed-row ledger."

## What Changes

- `scripts/file_findings.py` gains an optional `- **Owed-row:**` finding field.
  It must parse through the registered owed-row grammar
  (`scripts/bot_markers.parse_owed_rows` — ONE definition, rule 6j); a field
  that declares nothing valid fails `make findings-check` loudly, naming the
  finding and the grammar. When valid, the filed `tech-debt` issue body carries
  the owed-row declaration RE-RENDERED through `bot_markers.owed_row_marker`
  beside the dedup signature — the exact marker `make owed-rows-check` reads.
- The `issue-implement` skill (preloaded by every implement leg) gains the
  owed-rulebook contract: when a change owes `AGENTS.md` a row, the `tasks.md`
  box is written AT CREATION as
  `- [~] … — blocked: rule 3c human sign-off (AGENTS.md protected in a headless
  leg)` — green-but-review-required — and the FULL row text is recorded as an
  Owed-row finding so the ledger issue carries it. A bare `- [ ]` for an owed
  row is forbidden.
- `AGENTS.md` §6g states the contract and §8 gains the guard row (this diff is
  itself review-required under rule 3c; the PR review is the sign-off).

## Impact

- `scripts/file_findings.py` — optional field grammar, validation, marker
  rendering (already wired: `make findings-check` + `make file-findings` run in
  `issue-bot.yml` and `fix_loop.sh`; no new make target).
- `.hermes/skills/issue-implement/SKILL.md` — the headless-leg contract.
- `tests/test_file_findings.py` — owed-row filed-marker + loud-failure tests;
  `tests/test_workflows.py` — `test_the_implement_leg_never_leaves_an_owed_rulebook_row_bare`.
- `AGENTS.md` §6g + §8 (review-required diff, rule 3c).

## Not covered

- Changing Hermes's protected-file refusal itself (option (a) of #659 lives
  outside this repo; this change implements option (b), which the issue accepts
  on its own).
- Auto-landing a row from a ledger issue — landing an AGENTS.md diff remains a
  human/approved act (rule 3c); the ledger only makes it checkable.
- `make owed-rows-check` itself (unchanged; issue #523 already ships the reader).
