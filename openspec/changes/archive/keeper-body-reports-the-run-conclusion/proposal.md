# Proposal: keeper-body-reports-the-run-conclusion

Issue: #1651
PR: #1658

## Why

Issue #1634 widened qa-validate's `index-repair` trigger from `failure()` to
`(failure() || needs.validate.outputs.index_drift != '0')`, so the keeper now wakes on a
GREEN push whose `validate` only reported drift. The keeper's record did not follow:
`scripts/openspec_index_repair.py::compose_pr_body` hardcodes "went red at the OpenSpec
gate", and the job's checkout step is named "Checkout the exact master commit that went
red". Measured on the shipped tree (`origin/master` `a0f9adc5`): post-merge push run
`4546683307` concluded `completed/success`, yet keeper PR #1649's body told its reader
the run went red. A reader diagnosing the merge is sent after a red that never happened
(rules 2 and 6g). The repair itself works; only its record lies.

## What Changes

- `scripts/openspec_index_repair.py::compose_pr_body` gains additive keyword-only seams
  `run_green` and `index_drift`; a green-with-drift run prints "stayed GREEN … and only
  REPORTED index drift (`drift=<n>`)" and never the words "went red", while a red run
  keeps its original wording byte-for-byte. The CLI gains `--run-green` /
  `--index-drift`; the verdict is still never re-decided here (rule 6d).
- `.github/workflows/qa-validate.yml`: the `index-repair` checkout step name becomes
  "Checkout the exact master commit the run validated (red or drifted-green)"; the
  keeper's landing step forwards the run's real conclusion to its body seam through the
  `RUN_GREEN` / `INDEX_DRIFT` keys already published by `validate`. No `schedule:` key
  is added or edited; the `refresh-bot` cron stays byte-identical.
- `Makefile`: `openspec-index-repair-pr-body` forwards the two new knobs to the real
  composer, staying a pure `$(PYTHON_RUN) python3 scripts/…` recipe (rule 6m).
- `tests/test_openspec_index_repair.py` gains a RED-first fixture driving the REAL CLI
  with green-drift run `4546683307`, asserting no false "went red" claim and that the
  red path is unchanged; `tests/test_workflows.py` pins the conclusion wiring.
- `ARCHITECTURE.md`: the §3 target row and §6 script row are corrected. No `AGENTS.md`
  §7b/§8 or lane `SOUL.md` text is touched.

## Impact

Prose and additive optional arguments only. A caller that passes neither new knob gets
the exact body it got before; no gate, verdict, schema, data shape or trigger changes.
The two sibling keepers (architecture/invalid-change) still fire on `failure()` only and
their step names stay byte-identical.

## Technical Solution

One seam: `compose_pr_body` takes the run's conclusion as data from the same `validate`
output key the trigger reads, and both the body and the workflow step name word the
record from it. A fixture renders the body from the measured green run `4546683307` and
asserts the false red claim is gone.

## Not covered

- The sibling keepers' hardcoded sentences (`architecture_block_repair.py:132`,
  `openspec_invalid_change_repair.py:276`) — `failure()`-only triggers keep them true.
- The residual pre-squash regeneration gap (#1645).
- No schedule, no cron, no merge, no master push, no protected instruction-file edit.
