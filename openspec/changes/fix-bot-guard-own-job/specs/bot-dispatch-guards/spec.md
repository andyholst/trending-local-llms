# bot-dispatch-guards

## ADDED Requirements

### Requirement: a bot guard is its own job and declares no secret

Every bot pipeline SHALL carry its owner/collaborator guard as its own job — first, declaring no
`secrets.*` anywhere in it — and every other job of that pipeline SHALL run only after it. A
job-level `env:` holding `secrets.*` is materialised when the JOB starts, so a guard that is only
the first STEP of the secret-carrying job does not run "before any secret", however early that
step sits.

#### Scenario: the guard job holds no secret

- **GIVEN** a bot pipeline with a guard job
- **WHEN** that job's `env` and its steps are read
- **THEN** neither declares a `secrets.*` reference

- **Test:** `tests/test_workflows.py::test_guard_is_before_any_secret`

#### Scenario: every job runs only after the guard

- **GIVEN** a bot pipeline whose guard job is `guard`
- **WHEN** every other job's transitive `needs` are resolved
- **THEN** each one depends on `guard`, so a refused caller means no other job starts and no
  secret is materialised

- **Test:** `tests/test_workflows.py::test_guard_is_before_any_secret`

#### Scenario: the guard job itself needs nothing

- **GIVEN** a bot pipeline's guard job
- **WHEN** its dependencies are resolved
- **THEN** it has none: nothing runs before the guard

- **Test:** `tests/test_workflows.py::test_guard_is_before_any_secret`

### Requirement: fix-bot carries the guard before its secrets

`fix-bot.yml` SHALL carry the guard as its own FIRST job, holding no secret at all, with the work
in a separate `fix` job that declares the four secrets at job level and `needs` the guard.

#### Scenario: fix-bot's secrets live behind the guard

- **GIVEN** `fix-bot.yml`
- **WHEN** its jobs are read
- **THEN** the first job is `guard`, it declares no `secrets.*` and none of its steps touches one,
  and the `fix` job — which does declare the secrets at job level — `needs` it

- **Test:** `tests/test_workflows.py::test_owner_guards`

- **Test:** `tests/test_workflows.py::test_guard_is_before_any_secret`

### Requirement: the guarded-pipeline registry covers every guarded pipeline

`BOT_GUARDS` SHALL name every bot pipeline that carries a guard, and the job that guard is, so
each guard is EXECUTED for every caller class rather than merely described.

#### Scenario: fix-bot's guard is executed, not just asserted

- **GIVEN** `BOT_GUARDS`
- **WHEN** the guard behaviour suite runs
- **THEN** `fix-bot.yml`'s guard job is driven against the owner, a write collaborator, the bot
  itself, a read-only collaborator, a non-collaborator and a stranger re-running an owner run —
  and so are the two pipelines that were missing from the registry (`code-review-bot.yml`,
  `queued-alarm.yml`)

- **Test:** `tests/test_workflows.py::test_guard_behaviour`
