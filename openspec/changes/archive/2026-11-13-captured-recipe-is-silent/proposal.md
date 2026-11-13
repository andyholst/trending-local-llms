# A captured recipe is silent, so the value is the first line

**Issues:** [#547](https://github.com/andyholst/trending-local-llms/issues/547), [#548](https://github.com/andyholst/trending-local-llms/issues/548), [#539](https://github.com/andyholst/trending-local-llms/issues/539) (the same class)
**Capability:** `issue-bot-artifacts`

## Why

`make` echoes each recipe line to stdout. `#562` replaced the sweep's `sed` of the queue
row with `OUT=$(make issue-pick)` — a CAPTURE — and the recipe was not silenced, so `OUT`
held two lines:

```
python3 scripts/issue_queue.py --pick --gap-hours 3
issue=362
```

`PICK="${OUT#issue=}"` therefore became that command plus the value, the step refused it as
"not a number", and the `pick` job failed. Measured in production, twice: runs **40190558547**
and **40194644167**, where `implement` was skipped and the sweep implemented nothing for two
hours.

`#539` guarded the REDIRECT case (`make x > file`) only. A command substitution is the same
defect with the same cost, and four more recipes had it: `review-issue-pick`,
`review-issue-mark`, `review-issue-body-hash` (the reviewer's window proof) and
`refresh-sync` (whose `mode=`/`behind_base=` the refresh reads).

## What Changes

- **`Makefile`** — `issue-pick`, `review-issue-pick`, `review-issue-mark`,
  `review-issue-body-hash` and `refresh-sync` start with `@`, so a captured stdout is the
  product's own lines and nothing else.
- **`tests/test_workflows.py`** — a guard for the CAPTURE shape: every `$(make <target>)` a
  workflow performs must resolve to a fully silenced recipe. It is non-vacuous and pins
  `issue-pick`, the measured case.
- **`AGENTS.md`** §8 — the row is owed where the protected-file gate refuses the write; the
  exact text is recorded in `findings.md`.

## Impact

Five recipes gain `@`. Every consumer that parses a key (`^issue=`, `^body_sha=`,
`^mode=`) sees the same lines minus make's echo. No data, README or ranking change.

## Not covered (out of scope)

- `issue-queue` and other human-facing targets still echo their command: their output is
  read by a person, not captured into a value, and silencing them would hide which
  parameters produced the queue.
