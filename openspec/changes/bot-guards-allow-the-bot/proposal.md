# Every bot guard admits the bot itself, and the scheduled path is uniform

**Issue:** [#238](https://github.com/andyholst/trending-local-llms/issues/238)
**Capability:** `bot-guards` (the owner/collaborator trigger guard every bot pipeline carries)

## Why

Every bot pipeline gates its first job behind a "Owner / collaborator trigger guard"
that must pass before any secret is read. The guard's contract (AGENTS.md rule 6j) is
"the owner, or a collaborator with write/maintain/admin, for BOTH `github.actor` and
`github.triggering_actor`". Measured against current `master` (I extracted each
workflow's real guard script and ran it for every caller class with a stub `gh`):

| caller | refresh-bot | fix-bot | issue-bot | issue-review-bot | publish-agent-image |
|---|---|---|---|---|---|
| owner dispatch | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| write collaborator | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| read/triage collaborator | REFUSE | REFUSE | REFUSE | REFUSE | REFUSE |
| non-collaborator | REFUSE | REFUSE | REFUSE | REFUSE | REFUSE |
| `github-actions[bot]` (the bot itself) | REFUSE | REFUSE | REFUSE | REFUSE | REFUSE |
| `schedule` event | ALLOW | ALLOW | REFUSE | REFUSE | n/a (no cron) |

Two defects:

1. **The bot itself is refused everywhere.** When one workflow dispatches another with
   the default `GITHUB_TOKEN`, `github.actor`/`github.triggering_actor` is
   `github-actions[bot]`. `qa-validate`'s `dispatch-fixbot` happens to use the owner PAT
   today, so it slips through as the owner — but nothing in the guard permits the bot, so
   a bot-to-bot dispatch is one token choice away from being permanently refused
   (measured: `github-actions[bot]` -> `Refused: ... is not the owner or a collaborator`).
   `llgenie`'s guard allows `github-actions[bot]` explicitly; this repo's does not.
2. **The scheduled path is inconsistent.** `refresh-bot` and `fix-bot` carry an explicit
   `if [ "$EVENT" = "schedule" ]` bypass; `issue-bot` and `issue-review-bot` — both hourly
   crons — do not. Their scheduled runs pass only because `github.actor` today resolves to
   the owner (`andyholst`); a cron attributed to `github-actions[bot]` is refused and the
   bot silently stops.

## What Changes

- Every bot guard (`refresh-bot`, `fix-bot`, `issue-bot`, `issue-review-bot`,
  `publish-agent-image`) admits the same identities: the owner, a `write|maintain|admin`
  collaborator, and `github-actions[bot]`.
- Every bot guard that has a cron carries the `schedule` bypass, uniformly.
- `tests/test_workflows.py` locks it: `github-actions[bot]` is ALLOWED by every bot guard
  on a manual dispatch; read/triage collaborators and non-collaborators stay REFUSED;
  every bot guard with a cron carries the schedule bypass.
- `AGENTS.md` rule 6j adds "or `github-actions[bot]` (the bot itself)" — a protected-file
  edit, flagged as review-required (rule 3c).

## Not covered

- A run-failure reactor / `queued-alarm` for this repo — filed as its own issue if wanted.
- Consolidating the per-workflow guard step into one shared job — the per-workflow `guard`
  job is the current shape and is kept.
