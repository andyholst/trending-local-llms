# Proposal: lint-trailing-newlines

Issue: #186

## Why

Every tracked text file in this repository should end with a newline, and
**nothing checks it**: there is no `make lint`, no `.editorconfig`, no CI step and
no rule in `AGENTS.md` (`grep -c lint AGENTS.md` → 0). Measured on `master` while
filing this: **5 of 448 tracked text files already end without one** —
`ARCHITECTURE.md`, `scripts/architecture_check.py`, `tests/test_architecture.py`
and two OpenSpec files, all added the same day — so the rule was being violated in
the very change that documented the repo.

A file without a final newline is not cosmetic: git prints `\ No newline at end of
file`, the next append shows a spurious last-line change (a reviewer reads a
one-line edit as two), and a line-oriented tool can drop that line. It is the one
formatting rule every file of every kind in this repo can be held to.

## What Changes

- **`scripts/lint_linefeeds.py`** — fail closed on every tracked text file
  (`git ls-files`) whose last byte is not `\n`; `--fix` appends exactly one newline
  to each and re-reports, so a second run is a no-op. A binary file (NUL byte in
  its first 8000) and an empty file are never findings; an untracked file can never
  fail it. Pure stdlib, so the host and the container give the same answer.
- **`make lint` / `make lint-fix`**, both named in `ARCHITECTURE.md` (rule 6h —
  the guard in #178 fails otherwise, which is the point).
- **Wired where it bites** (rule 6d): the FIRST step of `qa-validate`'s `validate`
  job, the FIRST check in `scripts/fix_loop.sh` (so a bot round repairs a missing
  newline like any other red check, before the slow checks), and
  `tests/test_lint_linefeeds.py` in `make test`.
- **`.editorconfig`** with `insert_final_newline = true` + LF, so the editor
  enforces what CI enforces.
- **The 5 offenders are repaired in the same change** — a lint that is red on
  `master` is a lint nobody can merge past — and `AGENTS.md` gains rule **6i** plus
  its §8 guard row; `README.md` mentions the gate through its template.

## Impact

`scripts/lint_linefeeds.py` and `tests/test_lint_linefeeds.py` (new),
`.editorconfig` (new), `Makefile` (two targets + the suite), `scripts/fix_loop.sh`
(check list), `.github/workflows/qa-validate.yml` (step), `AGENTS.md` (rule 6i +
§8 row), `ARCHITECTURE.md` (the targets + the script), `scripts/update_trending.py`
(README template), `README.md` (regenerated), the OpenSpec change + `OPENSPEC.md`,
and the five files that were missing their final newline.

Data is untouched: `data/**` (all 300+ snapshots and raw files) already ends with
a newline — measured.

## Not covered

- Formatting beyond the final newline (trailing whitespace, line length,
  indentation): this is the rule the repo actually needs today, and
  `.editorconfig` already states the indentation conventions for the editor.
- Ruff/black/flake8 for the Python: a separate decision about dependencies and
  about what the bots would have to fix.
- Normalising CRLF **inside** a file: the check is about the final newline; a
  CRLF-only ending is reported, a mixed file is its own finding.
