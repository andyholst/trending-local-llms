# bot-verification-protocol

## ADDED Requirements

### Requirement: bots are exercised one at a time, and verified one at a time after merge

`AGENTS.md` SHALL state the bot verification protocol: every dispatcher is
exercised ONE bot per cycle, never several at once; a defect is fixed on a branch
whose PR carries the fix AND the regression guard for it, proved by the no-mocks
unit tests CI runs; the next bot's cycle starts only when the current PR's
`guard` and `validate` jobs are green; a PR lands only through qa-validate's
`auto-merge` job (never `--admin`, never a hand merge); and a PR is not
"verified" until it is MERGED, after which each merged bot is re-dispatched on
its own before the next one starts.

#### Scenario: the protocol is part of the rulebook

- **GIVEN** `AGENTS.md`,
- **WHEN** its §6b pipeline section is read,
- **THEN** it SHALL carry the one-bot-at-a-time protocol, the fix-PR-with-guard
  contract, the `auto-merge`-only merge rule, and the post-merge verification pass.

- **Test:** `tests/test_workflows.py::test_bot_verification_protocol_is_documented_and_guarded`

### Requirement: the guard the protocol mandates is the guard the tree proves

Each bot pipeline named by the protocol SHALL carry the owner / write+
collaborator / `github-actions[bot]` trigger guard as the FIRST step of the job
that carries it, deciding on BOTH `github.actor` and `github.triggering_actor`,
so every start — the audit dispatch, the re-run and the post-merge verification —
admits only those three identities (rules 6d/6j).

#### Scenario: every named pipeline's guard is its job's first step

- **GIVEN** every pipeline in `tests/test_workflows.py`'s `BOT_GUARDS`,
- **WHEN** the steps of the job that carries its guard are read,
- **THEN** the guard step SHALL be the first step of that job.

- **Test:** `tests/test_workflows.py::test_bot_verification_protocol_is_documented_and_guarded`

#### Scenario: the protocol leaves the document and the guard stays proven

- **GIVEN** the protocol text is removed from `AGENTS.md`, or a guard is moved
  off the first step of its job,
- **WHEN** the suite runs,
- **THEN** it SHALL fail (the protocol is a rule, not prose).

- **Test:** `tests/test_workflows.py::test_bot_verification_protocol_is_documented_and_guarded`
