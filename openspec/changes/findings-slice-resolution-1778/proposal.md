# Parallel lanes may satisfy the findings gate with one slice file

Issue: #1778

## Why

`make findings-check-for-pr` resolves only `findings/<issue>.md`. When several
lanes close one umbrella issue, each writes its own slice
(`findings/1767-planner.md`, `findings/1767-implementer.md`,
`findings/1773-architect-role.md`) to avoid the sibling conflict #1493 removed.
The gate then reds every correct slice delivery with
`[findings] FAIL findings/<issue>.md is missing`, even though analysis is present.
Measured on PRs #1769/#1770/#1776 (runs 45801501655, 45801511284, 45802490687).

## What Changes

- Add ONE explicit resolution rule in `scripts/file_findings.py`: when the
  canonical per-issue file is absent in the shape-aware check, exactly one
  `findings/<issue>-*.md` file stands in for it.
- The canonical file always wins; zero matches keep the existing loud failure;
  more than one is a loud ambiguity naming the candidates, never a guess.
- An explicit `--path` and the single-issue path stay byte-identical.

## Impact

Sibling lanes closing a shared issue can each carry their own analysis file and
pass `qa-validate/validate`. Filing (`--file`) is unchanged.

## Not covered

No rulebook wording is changed. A §8 row extension, if a reviewer deems one
owed, is filed as a separate rule-3c issue and declared as a blocked task here.
