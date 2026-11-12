# Proposal: log-tail-honored

Issue: #630
PR: #845 (measured: `Makefile:174` declared `HERMES_LOG_TAIL ?= 60` while the scrub seam
`--stream` printed every line; `grep -rn HERMES_LOG_TAIL` found only the definition, two test
fixtures with their own copy, and archived openspec prose)

## Why

A `?=` knob is the shape an operator sets — `HERMES_LOG_TAIL=200 make fix` — and when nothing
reads it the act changes nothing and says nothing. The scrub seam went LIVE (`--stream`,
issue #591) and stopped passing `--tail`, but the knob stayed declared: every round since has
been "bounded" only in appearance, and the only tests mentioning the variable defined their own
copy inside a fixture tree, which proves nothing about the real Makefile. Rule 6d forbids dead
code on the scripts side; the Makefile's knobs were the unguarded mirror of the same defect —
worse, because a knob reads like documentation of a bound that no longer exists.

## What Changes

- **`scripts/check_makefile_knobs.py`** — the guard: every top-level `NAME ?=` knob in the
  Makefile must appear in a USE shape somewhere in the runner's tree (`$(NAME)` / `${NAME}` /
  `$NAME`, a real `os.environ`/`getenv` read in `scripts/`, a YAML `NAME:` env key in
  `.github/workflows/`, a Dockerfile `ARG NAME`). Comments, docstrings, `tests/**` fixtures and
  `openspec/**` prose are NOT readers — that is exactly the false cover the dead knob had.
  Exit 0 clean, 1 naming `Makefile:line` per dead knob, 2 when the Makefile is unreadable.
- **`make check-makefile-knobs`** — the new public target (`_check-makefile-knobs` host recipe),
  bundled into the `lint` recipe (rule 6d), so `qa-validate`'s `validate` job and the fix loop
  run it where the knob lives.
- **`HERMES_LOG_TAIL` removed from the `Makefile`** — the knob is gone; the seam comment states
  that the only bound is `scripts/scrub_log.py`'s `--tail` default in `--in` (post-mortem) mode,
  and that `--stream` prints every redacted line live.
- **`tests/test_makefile_knobs.py`** — runs the REAL guard against planted fixture trees: a dead
  knob goes RED naming file:line; prose-only mentions (comment, docstring, fixture, archive) go
  RED; the five use shapes go green; a missing Makefile exits 2; the REAL Makefile passes its own
  guard and no longer declares the dead knob; the lint wiring is asserted.
- **`tests/test_scrub_log.py`** — the two fixture Makefiles drop their stale
  `HERMES_LOG_TAIL ?= 60` copy (they never referenced it).
- **Documentation rows**: `ARCHITECTURE.md` lint-target table + §6 scripts table + generated
  §10 via `make architecture-refresh`, and an `AGENTS.md` §8 guard row.

## Impact

- Affected specs: `makefile-knobs` (new capability)
- Affected code: `Makefile` (knob removal, two new targets, one lint line), `scripts/`, `tests/`
- No data, contract, or pipeline-contract change; nothing existing is removed except the dead
  knob itself, which had no reader.

## Not covered

- `:=` internal variables (not operator-settable; a dead internal is caught by rule 6d's
  script wiring test, not by this guard).
- Knobs consumed through dynamic indirection (a name built at runtime) — no static lint can see
  those; the refusal is of the provable shapes only.
