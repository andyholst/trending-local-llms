# Tasks: attribute-pipeline-failure-rows-with-proof

- [ ] `scripts/pipeline_failure_attribute.py` — the attribution seam: proof gates (merged PR through the real `gh` client, `guard_test_exists` from `scripts/pipeline_failure_guard_check.py`, `evidence_is_checkable` from `scripts/issue_verdict.py`, row must be diagnosed), additive stamp, report mode, refusals exit 2 and name the failed condition
- [ ] `Makefile` — `pipeline-failure-attribute` target (host pattern of `pipeline-failure-issue`, `RUN=`/`FIX_PR=`/`GUARD=`/`EVIDENCE=`/`REPORT=1`, `DRY=1` preview) + `.PHONY` entry
- [ ] `.github/workflows/queued-alarm.yml` — attribution step (report mode each sweep; stamp mode only when the owner's dispatch inputs name a run/PR/guard) placed BEFORE the ledger-PR landing step, using the existing ledger-landing mechanism so a stamped row rides the same reviewed PR
- [ ] `tests/test_pipeline_failure_attribute.py` — the six spec scenarios, driving the real script against recorded `gh` fixtures and planted ledgers (rule 6m: external system only, no `scripts/` rebinding)
- [ ] `tests/test_workflows.py` — `test_the_attribution_step_runs_before_the_ledger_landing_step` and `test_a_workflow_that_drops_the_attribution_step_is_red` (the second proved against `git show origin/master:.github/workflows/queued-alarm.yml`)
- [ ] `AGENTS.md` §6r: the attribution seam in the failure chain, and §8: the new guard row (reviewed on the PR — rule 3c)
- [ ] `make architecture-refresh` regenerates the inventory block and `make architecture-check` passes with the new target + script rows
- [ ] `make openspec-index` regenerated; `make openspec-check` green (proposal, spec with per-scenario tests, no unticked box)
- [ ] Local gates green in the container image: `make lint`, `make test`, `make secret-scan` + `make secret-scan-self-test`, `make pipeline-failure-guard-check`
- [ ] The attribution claims for the three open rows (`42976201014` / #826, `42977708147` / #827, `43047130543` / #828) are posted on their own issue threads with the evidence that survives the adversarial check — or #1053 records, with evidence, that a class has no landed guard-carrying fix and the row stays open (rule 2: never invent a `fix_pr`/`guard`)
- [ ] Findings recorded via `findings.md` + `make file-findings` for anything this change noticed but did not fix (rule 6g)
- [ ] PR opened (not draft) with the five-section body and `closes #1053`, then monitored until `validate` + `live-smoke` are green on the head commit
