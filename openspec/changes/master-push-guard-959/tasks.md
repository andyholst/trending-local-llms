# Tasks: master-push-guard-959

- [x] OpenSpec change created (proposal, `specs/master-push-guard/spec.md` with per-scenario `- **Test:**` lines, tasks) — verified: `openspec-check` scenario-test resolution green
- [x] `make check-branch-protection` public target (host-side like the other alarms) + the `queued-alarm.yml` step running it with the owner PAT — verified: wiring tests + `make lint` (workflow-guard scan) green
- [x] `scripts/check_branch_protection.py` — the DECISION: strict required contexts naming `validate` + `live-smoke` (bare or `workflow / job`), `enforce_admins` true; exit 1 names every gap, exit 2 for an unreadable read, never a silent clean — verified by the suite and by the live run against the repo (it reports the real 404 today)
- [x] `tests/test_branch_protection.py` green on the new code (23 checks: pass/refuse/404/malformed/wiring)
- [x] `ARCHITECTURE.md` §3/§4/§6 rows + inventory block regenerated (`make architecture-refresh`), `OPENSPEC.md` index regenerated; `AGENTS.md` Rule 1 guard sentence, §6 `queued-alarm.yml` bullet, §8 guard row (rule 3c disclosure posted on issue #959)
- [~] Owner applies the branch protection to `master` (FULL-OBJECT PUT: `required_status_checks {strict: true, contexts: ["qa-validate / validate", "qa-validate / live-smoke"]}`, `enforce_admins: true`, `required_pull_request_reviews: null`, `restrictions: null`) — blocked: repository settings are an owner-approved act (issue #959); the recorded shape lives in `openspec/changes/master-push-guard-959/proposal.md`
- [x] Guard PR opened with the five-section body + `closes #959`, never draft; `openspec-record-pr` archives this change at the merge head; `make openspec-archive-check` green
- [~] Post-application proof: a direct push to `master` is REFUSED, a green PR still auto-merges, and the next weekly `queued-alarm` sweep runs `make check-branch-protection` green — blocked: can only run after the owner applies the setting
- [~] Next weekly `queued-alarm` run green with the new step — blocked: waits for the Wednesday delivery after the setting lands
