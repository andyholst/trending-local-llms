# Proposal: syntaxwarning-escape

Issue: #190

## Why

`scripts/update_trending.py` carried a single unescaped backslash in its module
docstring — the text git prints for a file with no final newline:

```
SyntaxWarning: "\ " is an invalid escape sequence. Such sequences will not work
in the future. Did you mean "\\ "? A raw string is also an option.
```

Every import of the module raised it. It was invisible in practice: `make lint`
checked only the final newline, `make validate` never compiled a module, and the
suite imported the module after the warning had already scrolled past. A single
stray backslash in a docstring is easy to miss in review, and PEP 686's warning
path ends in an **error** in a future Python — so this is a latent break, not a
style nit. A real warning in the same stream would be missed for the same reason.

Measured on `origin/master` before this change: the warning fires on import; and
of 71 tracked `.py` modules, this one was the only offender — so the guard lands
green on the tree it ships.

## What Changes

- **`scripts/update_trending.py`** — the offending `\ ` in the module docstring is
  escaped, so the module imports without a `SyntaxWarning`.
- **`scripts/lint_syntax.py`** (new) — fail closed on every tracked `*.py` module
  whose source does not compile without a `SyntaxWarning` (or does not parse at
  all). The file set is what git tracks (`git ls-files '*.py'`), so an untracked
  or generated module can never fail the lint and a new module is covered the
  moment it is added. Each file is compiled **from source** with the warning
  promoted to an error, so no import side effect runs; pure stdlib, so host and
  container agree. The warning registry is cleared per file so a module that was
  already imported (this script itself) cannot hide its own warning.
- **`make lint`** runs it beside `lint_linefeeds.py` — the FIRST step of
  `qa-validate`'s `validate` job and the first check in `scripts/fix_loop.sh`, so a
  bot round repairs a `SyntaxWarning` like any other red check (rule 6d).
- **`tests/test_lint_syntax.py`** (new) — drives the real script against a real git
  fixture and against this repository, and asserts the wiring — the suite member
  for the guard.
- **`ARCHITECTURE.md`** — the `lint` target row and the scripts table name the new
  guard (rule 6h).
- **`AGENTS.md` §8** — a row for the guard, next to the trailing-newline row.

## Impact

`scripts/update_trending.py` (one line), `scripts/lint_syntax.py` (new),
`tests/test_lint_syntax.py` (new), `Makefile` (`lint` + the suite fallback chain),
`ARCHITECTURE.md`, `AGENTS.md` (§8 row), the OpenSpec change + `OPENSPEC.md`.

Data is untouched: no `data/**` file changes. `make lint`, `make test`,
`make architecture-check` and `make openspec-check` are the gates.

## Not covered

- Linting beyond a `SyntaxWarning`: unused imports, undefined names, style — a
  separate decision about dependencies and about what the bots would have to fix.
  This guard is exactly the class of defect the issue reported and nothing more.
