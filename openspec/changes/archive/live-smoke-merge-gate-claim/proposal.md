# a §4 job row may not claim a model call the job never makes (live-smoke is fetch-only)

**Issue:** #1033
PR: #1135
**Capability:** `architecture-job-behaviour-claim` (the ARCHITECTURE.md §4 job-row
guard in `scripts/architecture_check.py`, and the two §4/§6b rows it corrects).

## Why

`qa-validate`'s `live-smoke` job is now pure fetch: issue #1029 (owner directive
2026-11-15, rule 6t) removed its `make hermes-smoke` step, so no model call gates a
merge any more. Both rulebooks kept the old wording — `ARCHITECTURE.md` §4's
`live-smoke` row listed `hermes-smoke`, and `AGENTS.md` §6b's bullet did the same —
so the description still told every reader that a real Hermes call sat behind the
required status check literally named `live-smoke` (rule 1 names that context in
branch protection). The tree says otherwise and nothing noticed: the §4 guard
compares **names** only (`tests/test_architecture.py::test_pipeline_job_names_match_the_workflow_job_keys`),
and the boundary paragraph even promises that "a sentence that is wrong about a real
target" passes. A description that claims a model call in the merge gate is the
documented shape rule 6t exists to prevent, so it must be a gate, not a typo.

## What Changes

- `scripts/architecture_check.py` gains `job_call_findings` (bundled into the existing
  `architecture` stage — no new target, rule 6d/6m): every §4 `| Job | Does |` row is
  read as a BEHAVIOUR claim, and a row that names a model/agent target the job's own
  `run:` steps never call is RED, naming the workflow, the job and the target.
- The model-call set is `check_secret_output.AGENT_TARGETS_TO_SCRUB` (the ONE list of
  "what runs the agent") plus `hermes-smoke` and `refresh` — no second copy (rule 6d).
- A DENIAL is not a claim: the same exemption the cadence guard got in issue #1032
  (`_CADENCE_RETIRED`) — `no`/`not`/`never`/`removed`/`dropped` beside the name — so the
  corrected row can say `hermes-smoke` was dropped from the job without red-ing itself.
- `scripts/architecture_bot.py` gains `job_slice` / `job_targets`: "what does ONE job
  call" is derived from the one workflow parser, never a second YAML reader.
- `ARCHITECTURE.md` §4 (`live-smoke` row) and `AGENTS.md` §6b (its `live-smoke` bullet)
  state the truth: fetch-only, no model or agent call gates a merge; the job's NAME
  survives because branch protection names the required context literally, so renaming
  it (issue #1033's other option) is an owner repository-settings act, never an agent edit.

## Impact

- `scripts/architecture_check.py` — one new check inside the existing stage; already
  wired through `make architecture-check` (qa-validate `validate`, the fix loop,
  `make test`), so rule 6m gains no unwired target.
- `scripts/architecture_bot.py` — two helper functions on the existing parser.
- `tests/test_architecture.py` — five new tests (red-on-the-old-row, green when the job
  really calls it, denial-is-not-a-claim, one-list-not-a-copy, shipped tree green).
- **AGENTS.md sections this change alters (rule 3c, review-required):** §6b's
  `qa-validate` `live-smoke` bullet (fetch-only; the rename is an owner act) and one new
  §8 guard row naming this suite. No other section moves, and no rule's behaviour
  changes — the rule (6t) already existed; the docs now match it and a gate enforces it.

## Not covered

- Renaming the job/context `live-smoke` itself: branch protection names that context and
  only the owner may rewrite it (rule 1). This change makes the name honest by
  describing it, and leaves the rename to the owner on the issue.
- Every other kind of prose claim (a wrong sentence about an image, a step's purpose) —
  the §4 guard still cannot read prose, and the boundary paragraph says which claims it
  does check.
