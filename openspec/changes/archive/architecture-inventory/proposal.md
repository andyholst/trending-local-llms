# Proposal: architecture-inventory

Issue: #479 — architecture-bot: a daily, deterministic refresh of ARCHITECTURE.md's living inventory

## Why

`ARCHITECTURE.md` is the only artifact that answers *"which bot does what, and how
does a trending model reach `README.md`?"* — and rule 6h makes it part of every
change. Its prose is hand-maintained, and the half that describes the MACHINERY
rots silently between touches:

- The pipeline section counted **"Seven workflows"** over a directory of **ten**;
  nothing noticed, because `scripts/architecture_check.py` only asks whether a
  workflow or a script name appears *somewhere* in the text — never whether the
  description of a bot's triggers, jobs or `make` targets still matches the YAML.
- The same is true of the data flow and of `scripts/`: a script's one-line purpose
  lived only in prose a human had to remember to copy.

A description nobody regenerates is an assertion, and an assertion that cannot be
checked is the shape this repository's rules exist to prevent.

## What Changes

- **New script `scripts/architecture_bot.py`** — derives a block between
  `<!-- architecture-bot:begin -->` / `<!-- architecture-bot:end -->` from the
  tree itself:
  - every workflow in `.github/workflows/`: its `name:`, its triggers and cron
    slots, its jobs in file order with their `needs`, and the `make` targets each
    job actually calls (scanned in `run:` bodies only, so a `make` in a workflow
    COMMENT is not reported; only names the Makefile defines are reported; a
    matrix call renders as `search-*`), each with the Makefile's own `##`
    description;
  - the product end to end (`FLOW`): `make search` → `data/raw/*.json` →
    `make merge` (ingest) → the trend fields → `render_readme` → `README.md` →
    the snapshot, every target/script/artifact verified against the tree;
  - one line per script in `scripts/`, taken from that script's own docstring;
  - the `README.md` sections (title, `##` sections, `#` backend tables) a refresh
    rewrites.
- **`--write`** replaces the block (`make architecture-refresh`); **`--check`**
  fails when the block on disk is stale (`make architecture-check`, which
  `qa-validate`, the fix loop and `make test` already run) and when a FLOW
  reference is not backed by the tree. `--write` refuses to publish a flow it
  cannot back, so the generator never asserts something it did not verify.
- **New pipeline `.github/workflows/architecture-bot.yml`** — daily cron
  `13 5 * * *` + owner dispatch, guard as the FIRST job (rule 6j), `base-check`
  (rule 6n), `make architecture-refresh`, `make architecture-check`, then a
  commit + PR ONLY when the block changed. No model: nothing in the block can be
  invented.
- **`ARCHITECTURE.md` §10** holds the markers and the explanation; §3 gains the
  `architecture-refresh` row; §4 documents the new pipeline and states the real
  workflow count.
- **`AGENTS.md`**: rule 6h extended with the generated half and the daily bot, a
  §6b bullet for the pipeline, and a §8 row for the new guard.
- **Tests**: `tests/test_architecture_bot.py` (fixture trees + the real repo, no
  mocks) and the guard registration in `tests/test_workflows.py`.

## Impact

- No data, contract, README or store change: the product's behaviour is
  untouched. The change is a new generated documentation block, its generator, its
  daily pipeline and their guards.
- `make architecture-check` becomes STRICTER: a change that adds a workflow, a
  make target, a script or a README section without regenerating the block is
  now red. That is the point of the change (the description is part of it, rule
  6h) and it is repaired by one command (`make architecture-refresh`).
- The bot is a no-op on a tree that has not moved: no branch, no PR, no commit.

## Not covered

- The hand-written prose of `ARCHITECTURE.md` (§1–§9). The bot keeps the
  MECHANICAL half true; explaining *why* a pipeline exists stays a human/agent
  obligation under rule 6h, and a prose sentence that drifts inside §4 is not
  detected by this change.
- `AGENTS.md` prose beyond rule 6h, §6b and §8 (the rulebook stays hand-written).
- Refreshing the block on the caller's checkout: the bot runs in CI, and locally a
  human/agent runs `make architecture-refresh` in their own worktree (rule 6n).
