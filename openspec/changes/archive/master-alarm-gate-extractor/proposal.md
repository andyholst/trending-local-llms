# Proposal: master-alarm-gate-extractor

Issue: #1281
PR: #1285

## Why

`scripts/master_alarm.py::validate_gates_from_trees` extracts the `validate`
job's gates with `re.findall(r"make\s+([a-z0-9_-]+)(?=[\"'\s]|$)", wf_text, re.M)`
over the whole job text. The lookahead admits a quote, apostrophe, whitespace or
EOL after the target — and nothing else. So the echo literal
`Run 'make openspec-index' and rebase` in PR #1242's new merge-tree step yields a
PHANTOM gate `openspec-index`, while the REAL gate on the same step,
`if ! make openspec-index-check; then`, is NOT extracted (`;` fails the lookahead).
Measured on PR #1242's head workflow: extracted contains `openspec-index`=True,
`openspec-index-check`=False; `make test` reds with
`uncovered=['openspec-index']` (run `45007542439`). Rule 6q's promise — every
deterministic gate of the `validate` job sits on the keeper list or the alarm
list — is only as good as this extraction: a gate written `make X;` (the normal
shell shape) is invisible, so a NEW gate can ship unregistered with the guard
green, and a prose literal reds the guard on text that runs nothing.

## What Changes

- `validate_gates_from_trees` becomes line-oriented: a `#` comment line and a
  line whose command word is `echo`/`printf`/`say`/`warn`/`annotate` contribute
  nothing, and quoted spans are removed before matching, so a `make <target>`
  inside a quoted argument is prose, not a command.
- The target terminator set grows to `;`, `|`, `&`, `)`, a backtick, a quote,
  whitespace and EOL, so `make X;` / `make X && …` / `make X | …` / `make X)` /
  `` `make X` `` are all gates.
- `tests/test_master_alarm.py` locks both halves: a planted
  `run: make <newgate>;` is extracted (and so reds the registry test until
  `GATES` names it), and the PR #1242 echo literal extracts as no gate.

## Impact

- `scripts/master_alarm.py` — the extractor and its two module constants.
- `tests/test_master_alarm.py` — new locks in the existing registry test.
- No make target, workflow, contract or rulebook change.

## Not covered

- Gates invoked through a variable (`make "$TARGET"`) — the target is not a
  literal, so it was never visible to this extractor.
- The other direction (a gate the extractor sees that the job does not run) —
  the prose half of this change.
