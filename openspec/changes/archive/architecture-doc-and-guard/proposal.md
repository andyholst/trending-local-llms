# Proposal: architecture-doc-and-guard

Issue: #178
PR: #180

## Why

This repository has a rulebook (`AGENTS.md`) and 55 `make` targets, four
pipelines, three runner images and 19 scripts — but **no description of the
system**. A reader (or an agent starting work) has to reconstruct the data flow,
what each target runs, which image each job pulls and what each pipeline may do
from four workflow files and a hand-commented Makefile.

That gap is already visible: `AGENTS.md` § "Makefile targets" describes
`make lint`, `make lint-fix`, `make chained`, `make loop` and `make test-install`
— none of which exist in this repo's Makefile. And the bots change the pipeline
unattended: an implementation that adds a target or a job leaves no durable
explanation a human can read (the PR body disappears with the branch).

## What Changes

- **`ARCHITECTURE.md`** at the repo root, describing: the data flow and
  contracts (`data/raw/*` → `make merge` → `data/models.json` → `README.md` +
  `data/snapshots/*`), **every public make target** grouped with the image it runs
  in, **every job** of `refresh-bot.yml` / `qa-validate.yml` / `fix-bot.yml` /
  `issue-bot.yml` with its triggers, `needs`, gates and tokens, the three images
  and how each content-hash tag is decided, every script in `scripts/`, the guard
  map (pointing at AGENTS.md §8), and the life of a change.
- **`make architecture-check`** (`scripts/architecture_check.py`) — the guard that
  makes the description part of the change: it fails when a public target, a
  workflow or a script is missing from the description, when the description's §3
  target tables name something the Makefile no longer has, or when it references a
  workflow/script that does not exist.
- **Wired where it bites**: `qa-validate`'s `validate` job, the fix loop (before
  the network-bound `validate`, so a stale description is repaired by the same
  loop) and `make test` (through `tests/test_architecture.py`).
- **AGENTS.md rule 6h**: any change that adds, renames or removes a make target, a
  stage, a pipeline job or an image MUST update `ARCHITECTURE.md` in the same
  change; the implementer prompt requires it, so the bot maintains the file.
- **`README.md`** (through its template in `scripts/update_trending.py`) points at
  the file.

## Impact

`ARCHITECTURE.md` (new), `scripts/architecture_check.py` (new),
`tests/test_architecture.py` (new), `Makefile` (target, `_test`, the implementer
prompt), `scripts/fix_loop.sh` (the check list), `scripts/update_trending.py`
(README template), `.github/workflows/qa-validate.yml` (the step), `AGENTS.md`
(rule 6h + §8 row), `README.md` (regenerated), plus the OpenSpec change and
`OPENSPEC.md`.

Data is untouched: no change to `data/**`, no contract change, no search change.

## Not covered

- Replacing `AGENTS.md`: the rulebook stays the rulebook (what MUST happen), the
  new file only describes (how it works).
- Generating the description from the Makefile/workflows: the *guard* is
  automatic, the prose is written — a generated file could not explain *why*.
- Splitting the description per subsystem (search leg, ingest, validator): one
  file first.
- Fixing the drift in `AGENTS.md` § "Makefile targets" (targets named there that
  do not exist) — its own finding.
