# Tasks: attribute-pipeline-failure-rows-with-proof

- [x] `scripts/pipeline_failure_issue.py` — the attribution pass beside the filer, the re-diagnosis
      pass (#987) and the merged-PR stamp pass (#1099): proof gates (the fix PR MERGED through the
      real `gh` client with `mergedAt`, `guard_test_exists` from `scripts/pipeline_failure_guard_check.py`
      plus the named `::test`, the guard tied to the fix PR's own `tests/` diff, evidence through
      `scripts/issue_verdict.py`'s evidence rule naming a path the fix touched and never the ledger
      itself, row already diagnosed), additive raise, report mode, refusals exit 2 naming the failed
      condition with nothing written.
- [x] `scripts/bot_markers.py` — the `pipeline-attribution` marker registered (rule 6j) and round-tripped
      through its own parser; no second copy of the literal anywhere (rule 6d).
- [x] `Makefile` — `pipeline-failure-attribute` target (the `pipeline-failure-*` host pattern;
      `RUN=`/`FIX_PR=`/`GUARD=`/`EVIDENCE=`, report mode when none is supplied, `LIMIT=`) + `.PHONY` entry.
- [x] `.github/workflows/queued-alarm.yml` — attribution step (report mode each sweep; stamp mode only
      when the owner's dispatch inputs name a run/PR/guard/evidence, on the default `github.token`)
      placed AFTER the filer step and BEFORE the ledger-PR landing step, so a stamped row rides the
      same reviewed ledger PR.
- [x] `tests/test_pipeline_failure_attribution.py` — every scenario in the spec, driving the real
      script against the recorded `gh` fixture imported from `tests/test_pipeline_failure_issue.py`
      (one fixture, rule 6d) and planted ledgers (rule 6m: external system only, no `scripts/` rebinding).
- [x] `tests/test_workflows.py` — `test_the_attribution_step_runs_before_the_ledger_landing_step` and
      `test_a_workflow_that_drops_the_attribution_step_is_red` (proved against the current
      `queued-alarm.yml`: step removed, step moved after the landing, step bypassing the Makefile —
      each red, and the bypass names the rule 6m defect rather than only the missing target).
- [x] `AGENTS.md` §6r: the attribution seam in the failure chain, and §8: the new guard row (landed in
      this branch; the PR diff is the rule 3c review surface). The §6r/§8 wording was corrected against
      the live measurement after the first draft claimed the three measured rows were UNDIAGNOSED —
      they are DIAGNOSED (re-diagnosed 2026-11-15) and unattributed.
- [x] `ARCHITECTURE.md` — the target-table row for `pipeline-failure-attribute`, the `queued-alarm` job
      description, and `make architecture-refresh` regenerating the inventory block;
      `make architecture-check` green.
- [x] `make openspec-index` regenerated; `make openspec-check` green (proposal, spec whose every
      scenario names a test that exists, no unticked box).
- [x] Local gates green in this branch: `make lint`, `make secret-scan` + `make secret-scan-self-test`,
      `make check-secret-output`, `make openspec-check`, `make architecture-check`,
      `make pipeline-failure-guard-check`, and `make pipeline-failure-attribute` run live in report
      mode against the shipped ledger (read-only, writes nothing). `make test`: 131/134 modules green;
      `tests/test_agent_skills.py` is the only red module and it is RED ON `master` TOO — measured
      identically in the user's checkout at `5d8ad491` and in this worktree (`OSError [Errno 66]`
      cleanup race), filed as its own finding #1137 (rule 6g: fixed in its own change, not here).
      The suite that gates the merge is CI's `make test` on the head commit, monitored below.
- [x] The three rows #1053 measured (`42976201014` / #826, `42977708147` / #827, `43047130543` / #828)
      are handled HONESTLY: the live report names all three as DIAGNOSED-but-unattributed (each OPEN
      under an `agent:refined` verdict hold, `unattributed_diagnosed_rows=3`, ledger byte-identical),
      that output is recorded on #1053 as the evidence
      (`https://github.com/andyholst/trending-local-llms/issues/1053#issuecomment-7001230691`), and NO
      `fix_pr`/`guard` is invented for any of them (rule 2) — an attribution stays available only
      through an attested claim naming a MERGED, guard-carrying fix PR for that row's error class.
- [x] Findings recorded via `findings.md` + `make file-findings` for anything this change noticed but
      did not fix (rule 6g): (a) five ledger rows (#1039–#1043) carry `fix_pr` + `guard` with no error
      block and are selected by NEITHER the re-diagnosis pass (its filter needs an `undiagnosed` key
      they lack) NOR the attribution pass (no diagnosis) — filed as
      `https://github.com/andyholst/trending-local-llms/issues/1136`, with its rule 3c comment naming
      the §6r/§8 change that issue owes; (b) `tests/test_agent_skills.py` is red on the host for a
      reason unrelated to this change (the real `hermes` CLI keeps writing `installs/…` into the test's
      temp home, so `TemporaryDirectory` cleanup races it) — measured identically on `master`
      `5d8ad491` and filed as `https://github.com/andyholst/trending-local-llms/issues/1137`.
- [x] PR opened (not draft) with the five-section body and one closing keyword on #1053; `validate` +
      `live-smoke` on the head commit gate the squash merge (qa-validate's `auto-merge` job).
