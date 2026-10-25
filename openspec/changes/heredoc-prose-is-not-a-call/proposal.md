# The architecture inventory reads only what a `run:` block executes

**Issue:** [#544](https://github.com/andyholst/trending-local-llms/issues/544)
**Capability:** `architecture-description`

## Why

`scripts/architecture_bot.py::workflow_targets` reports every `make <target>` it finds in
a workflow's `run:` bodies. A `run:` body is not only commands, though: it also holds
HERE-DOCUMENT CONTENT and QUOTED STRINGS, and both were being read as calls.

Measured on `origin/master`: a block that writes the sentence "this PR passes `make
openspec-check`" into `pr-body.md` and then really runs `make validate` was reported as
calling BOTH, so §10 of `ARCHITECTURE.md` claimed a target the pipeline never runs. The
phantom disappeared only because #287 moved that heredoc into `make pr-body` — the scanner
was never fixed, so the next heredoc with a `make` in it re-creates the same wrong line.

## What Changes

- **`scripts/architecture_bot.py`** — `command_text()` strips what a shell would NOT
  execute before the `make` sweep:
  - a heredoc body (`<<'WORD'` … `WORD`), which is file content;
  - single- and double-quoted strings, which the shell never splits into a command.
  Shell COMMENTS are deliberately left alone: a `make` a reader can see in a step is still
  reported.
- **`tests/test_architecture_bot.py`** — a case that drives the real `workflow_targets`
  with a workflow holding both shapes plus two real calls, asserts the prose is gone and
  the real calls (including one whose argument is quoted) survive, and asserts the
  qa-validate workflow's real targets still come through (the filter is not vacuous).
- **`AGENTS.md`** §8 — the guard row (review-required, rule 3c).

## Impact

The generated §10 block only. On the current tree the block is unchanged (the phantom had
already been removed by #287), so this is a guard against the class recurring, not a
description change. No target, job or data change.

## Not covered (out of scope)

- A `make` inside a shell COMMENT is still reported. It is visible to a reader, but it is
  not a call either; narrowing that changes the docstring's stated intent, so it is filed
  as a finding rather than folded in here.
- A heredoc whose delimiter is quoted AND expanded (`<<-"EOF"`) is handled by the same
  rule; a delimiter built from a variable is not, and no workflow here does that.
