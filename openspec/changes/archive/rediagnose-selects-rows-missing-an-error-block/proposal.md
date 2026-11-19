# Proposal: rediagnose-selects-rows-missing-an-error-block

Issue: #1136
PR: #1149

## Why

Rule 6r says a ledger row must carry the failure's own error text. `make pipeline-failure-issue`
also has a repair pass — re-diagnosis — that re-reads the log of a row whose diagnosis never
landed. That pass selected its pending set by the presence of a KEY:

```python
pending = [e for e in ledger["failures"]
           if e.get("undiagnosed") and not e.get("rediagnosed_utc") and not e.get("log_expired")]
```

But the filer writes `"undiagnosed": log_error`, so a row whose log read SUCCEEDED stores
`undiagnosed: None`, and a row stamped by a ledger PR (issue #1099's stamp pass) never carries the
key at all. Measured 2026-11-19 against the committed `data/pipeline_failures.json` (20 rows): the
old filter selects **zero** rows, while FIVE rows sit in the ledger with no diagnosis at all —
runs `43147240875` (issue #1039, `fix_pr` 922, `guard` `tests/test_owed_rows.py`),
`43716345030`, `43716362366`, `43718826142`, `43725338063` (issues #1040–#1043, `fix_pr` 1082,
`guard` `tests/test_openspec_index_repair.py`) — each with `fix_pr` + `guard` + `stamp_utc` and NO
`error_excerpt`, NO `rediagnosed_excerpt`, NO `undiagnosed`, NO `log_expired`. They are invisible
to BOTH repair paths: the re-diagnosis filter never selects them, and `make pipeline-failure-attribute`
refuses them as undiagnosed. Meanwhile `make pipeline-failure-guard-check` answered
`17 diagnosed failure(s) closed with a landed fix PR + guard test`, counting them as resolved.
Five rows therefore claim a landed fix for a failure no reader — and no future sweep — can ever
name (the reproduction command issues #1040–#1043 promise was never read).

A second symptom of the same root: a freshly FILED row stores no diagnosis either, so the old
filter treated every successfully-read filing as pending, and the pass would re-fetch and
self-annotate the issue it had just diagnosed on the same sweep.

## What Changes

- **ONE diagnosis predicate** — `scripts/pipeline_failure_issue.py::row_is_diagnosed(entry)`: a row
  is diagnosed when it carries a stored `error_excerpt` (or the legacy `rediagnosed_excerpt`
  spelling). Every reader of the ledger asks this one question (rule 6d).
- **ONE pending seam** — `rediagnose_pending(ledger)`: pending = NOT diagnosed AND not
  `rediagnosed_utc` AND not the terminal `log_expired` drain. The re-diagnosis pass, the
  attribution report (`diagnosed_unattributed`) and its refusal all read through these seams.
- **Filing records its diagnosis in the row** (additive key, rule 3b): `error_excerpt`, SCRUBBED
  through the §3d redactor before the write — `data/pipeline_failures.json` is a tracked file, so
  an error block copied from a log must never carry a secret value. `None` when the log read
  failed, which is what keeps that row pending.
- **The guard names the two classes apart** (`scripts/pipeline_failure_guard_check.py`): a stamped
  row that carries NO error block is its own REPORTED line (`attributed … but carries NO error
  block`, naming the fix PR, the guard and the seam that recovers it), never the
  closed-without-guard refusal and never red; `summary()` reports `diagnosed_attributed` and
  `attributed_without_diagnosis` separately and names the run ids. The attribution REFUSAL on such
  a row stays in force (re-diagnosis owns it).
- Tests (`tests/test_pipeline_failure_issue.py`, `tests/test_pipeline_failure_guard.py`,
  `tests/test_pipeline_failure_attribution.py`) plant the stamped-and-errorless row and prove the
  sweep fetches it, prove an already-diagnosed row is byte-identical, prove a filing's own row is
  not re-fetched, and run the REAL gate over the committed ledger asserting the five measured run
  ids are named as their own class.
- Rulebook/description: `AGENTS.md` §6r (the selection rule) + two §8 rows; `ARCHITECTURE.md`'s
  `pipeline-failure-issue` target row, its `pipeline-failure-guard-check` target row and the two
  script rows.

## Impact

- Capability: `alarms` (the pipeline-failure filer/gate half of rule 6r).
- `make pipeline-failure-issue` (the `queued-alarm` sweep): the next dispatched run re-reads the
  logs of the five rows, raises their `error_excerpt` + `rediagnosed_utc` + grown `targets` +
  `failing_steps`/`error_region`, and posts ONE `pipeline-rediagnose` annotation on issues
  #1039–#1043. Nothing rewrites an existing stored value (rule 3b).
- `make pipeline-failure-guard-check` (qa-validate's `validate` job): stays green on the committed
  ledger (12 diagnosed+attributed, 5 attributed-without-a-diagnosis) instead of flattening both
  classes into one count.
- No contract, data-shape or README change; no Makefile target added or renamed.

## Not covered

- It does NOT diagnose the five rows itself: only the `queued-alarm` sweep reads live logs, and
  agents may not dispatch pipelines (owner directive 2026-11-15, rule 6t). This change makes the
  rows SELECTABLE; the next sweep lands their text.
- It does not make attributed-without-a-diagnosis RED. A red gate would block every merge in the
  repo until a sweep ran, and the repair path (re-diagnosis) is already owned by the sweep; the
  gate's red stays reserved for a closed failure with no guard test (issue #802's contract).
- It does not archive any change, and it changes no rule outside the selection sentence in §6r.
