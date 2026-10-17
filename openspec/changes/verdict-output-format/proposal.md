# A step's output file holds `key=value`, never a command's whole stream

**Issue:** [#346](https://github.com/andyholst/trending-local-llms/issues/346)
**Capability:** `ci-output-safety`

## Why

Every implementer run that actually implemented an issue died on its verdict step, after the model work was done:

```
implement  14:44:38.98  make issue-verdict | tee /dev/stderr >> "$GITHUB_OUTPUT"
implement  14:44:38.99  python3 scripts/issue_verdict.py --issue 329     <- make echoing its recipe
implement  14:44:39.03  ##[error]Invalid format 'python3 scripts/issue_verdict.py --issue 329 '
```

`make` is not silenced for that recipe, so its first stdout line is the echoed command — which is not `key=value`, and Actions refuses the whole step. Everything after it was **skipped**: `Commit + push the branch`, `Open the PR`, `Fix loop`, `Report the outcome`, and even `Fail loudly when the implementation did not happen`. Measured twice, on the same issue (#329): runs [39026771566](https://github.com/andyholst/trending-local-llms/actions/runs/39026771566) (17 min of Hermes work) and [39040036748](https://github.com/andyholst/trending-local-llms/actions/runs/39040036748) (24 min). #329 carries two `issue-bot-start` markers, no outcome comment, and a branch that was announced but never pushed.

The same shape sits on two `refresh-bot` steps (`make rebuild-decision | tee /dev/stderr >> "$GITHUB_OUTPUT"`); they only work because that recipe happens to be `@`-silenced, so one Makefile edit away from the same failure.

And the shape is a **leak surface**, not only a format bug: `tee /dev/stderr` copies the command's whole stdout into a public job log, and `>>` copies it into the run's output file. GitHub masks the values it registers, so a transformed one (base64, a URL, a slice) sails past — rule 3d's whole point. Nothing in the repo guarded that shape: `check-secret-output` names `secrets-in-run-block`, `prints-secret-value`, `xtrace-with-secrets`, `value-in-argv`, `env-dump`, `key-shaped-literal` — a wholesale copy of a stream is none of them.

## What Changes

- **`.github/workflows/issue-bot.yml`** — the verdict step captures the output and writes ONLY the parsed key (an allowlist), printing at most the parsed verdict. No `tee`, no wholesale redirect. The refusal guarantee is preserved and made explicit: `bash -e` (the runner's default) plus a **bare** assignment means `make` exiting 2 aborts the step.
- **`.github/workflows/refresh-bot.yml`** — both `rebuild-decision` steps take the same shape: capture, parse the decision's six keys, print only the `(note)` reasons. This is the class, not the instance (the two steps are currently safe only by accident).
- **`Makefile`** — `issue-verdict` is `@`-silenced, so no consumer can inherit the echoed recipe line.
- **`scripts/check_secret_output.py`** — two new rules, both over any tracked script or workflow:
  - `whole-stdout-into-output-file`: a pipeline or `$(…)` whose output is redirected into `$GITHUB_OUTPUT`. A pipe INSIDE a quoted argument (`echo "k=$(cmd | sed …)" >> file`) is the safe shape and is not flagged.
  - `whole-stdout-into-log`: `… | tee /dev/stderr` (or `/dev/stdout`).
- **`tests/test_secret_output.py`** — the two rules falsified on the measured line, the fixed shape proven clean, and the **shipped verdict step executed** against a stub `make` whose output carries the recipe echo, a diagnostic and a secret-shaped value: only `verdict=` may reach `$GITHUB_OUTPUT`, and the value must reach neither the file nor the log. A second test drives `make` exiting 2 and requires a non-zero step.
- **`tests/test_issue_triage.py`** — the assertion that locked the old piped shape (`make issue-verdict | tee /dev/stderr >> "$GITHUB_OUTPUT"`) now locks the new one; it was the test that kept the bug in place.
- **`AGENTS.md`** (§3d bullet, §8 row) and `OPENSPEC.md`.

## Impact

The implementer's pipeline reaches `Commit + push` → `Open the PR` → outcome comment instead of dying at the verdict; both `refresh-bot` decisions keep their outputs with the same values and no whole-stream copy. The guard is a new **exit condition** on `make check-secret-output` (already the first steps of qa-validate's `validate` job), and it is verified to go red on the pre-change tree (6 violations: the 3 measured lines × 2 rules). No data, no README, no schema.

## Not covered

- **#344** (the reviewer's pick parsing) and **#345** (a hand-filed `tech-debt` issue gets a green no-op) — the other two bot defects, their own changes.
- The reviewer's `review-issue-mark` step keeps its `echo "$OUT"` diagnostic line: it writes one computed literal to the output file and prints diagnostics deliberately. Making ALL diagnostics allowlisted everywhere is a wider change; this one removes the wholesale copies that exist.
- No behaviour change to what a verdict MEANS (`implement`/`refine`/`close`) — only how its result reaches the step's outputs.
