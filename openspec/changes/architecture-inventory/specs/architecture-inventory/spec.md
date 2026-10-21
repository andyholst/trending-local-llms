# architecture-inventory

## ADDED Requirements

### Requirement: The inventory is derived from the tree, never authored

`ARCHITECTURE.md`'s §10 block MUST be produced from the repository itself — the
workflows, the Makefile, the scripts and `README.md` — so that no line of it can
be a claim nobody can check. It MUST list every pipeline with its triggers (cron
slots included), its jobs in file order with their `needs`, and the `make`
targets each job actually calls, carrying the Makefile's own `##` description of
each target. A `make` that appears only in a workflow comment, or that names no
make target, MUST NOT be reported as a call. A matrix call MUST render as the
static prefix plus `*` (`search-*`), never as a target name that does not exist.

#### Scenario: every pipeline, trigger, job and target is reported

- **Given** a workflow `ci.yml` with `name: fixture-bot`, a cron `13 5 * * *`, `workflow_dispatch`, a `guard` job and a `work` job that `needs: guard` and runs `make merge`
- **When** the inventory is generated for that tree
- **Then** the block names `.github/workflows/ci.yml`, `fixture-bot`, the cron slot `13 5 * * *`, the job chain `guard` then `work` (needs `guard`), and `make merge` with the Makefile's description
- **Test:** `tests/test_architecture_bot.py::test_block_is_derived_from_the_tree`

#### Scenario: prose is not behaviour

- **Given** a workflow whose top-level comment says ``make nonsense`` and whose step body runs ``make not-a-target``
- **When** the inventory is generated
- **Then** neither token appears in the block
- **Test:** `tests/test_architecture_bot.py::test_block_is_derived_from_the_tree`

### Requirement: The product's flow is named and verified

The block MUST show the product end to end — search → raw snapshots → ingest →
trend fields → render → `README.md` → snapshot — with the real targets and
artifacts, and MUST list one line per script taken from that script's own
docstring, plus the `README.md` sections a refresh rewrites. Every target, script
and artifact a flow step names MUST be verified: a step the tree no longer backs
is a LOUD failure, and the generator MUST NOT write a block that describes it.

#### Scenario: a flow step whose target is gone is refused

- **Given** a tree whose Makefile no longer defines `merge`
- **When** `--check` or `--write` runs
- **Then** both exit non-zero, name `make merge`, and `--write` leaves the document untouched
- **Test:** `tests/test_architecture_bot.py::test_a_flow_the_tree_does_not_back_is_refused`

#### Scenario: scripts and README sections are part of the inventory

- **Given** a tree with `scripts/update_trending.py` whose docstring reads "Fold raw snapshots into the store." and a README with `## ❤️ Most loved`
- **When** the inventory is generated
- **Then** the block carries `` `scripts/update_trending.py` — Fold raw snapshots into the store. `` and lists the README section
- **Test:** `tests/test_architecture_bot.py::test_block_is_derived_from_the_tree`

### Requirement: A stale inventory turns the guard red, and the markers are mandatory

`make architecture-check` MUST fail when the block on disk differs from the block
the tree generates, naming the difference and the command that repairs it
(`make architecture-refresh`), and MUST pass once the block has been regenerated.
A document without the two markers MUST be a loud failure in BOTH modes — never a
silent no-op, and never a rewrite that guesses where the block belongs.

#### Scenario: the tree moves and the description does not

- **Given** a document whose block was generated, and a tree that then gains a workflow
- **When** `--check` runs
- **Then** it exits 1, says the block is STALE, and names `make architecture-refresh`; after `--write` it exits 0 and the new workflow is described
- **Test:** `tests/test_architecture_bot.py::test_check_is_red_on_a_stale_block_and_green_after_write`

#### Scenario: no markers is a loud failure

- **Given** an `ARCHITECTURE.md` with no `<!-- architecture-bot:begin -->` / `<!-- architecture-bot:end -->` pair
- **When** `--write` (or `--check`) runs
- **Then** it exits 1, names the missing marker, and the file is unchanged
- **Test:** `tests/test_architecture_bot.py::test_missing_markers_are_loud_and_write_nothing`

### Requirement: A daily, model-free pipeline keeps it current

`architecture-bot.yml` MUST run on a daily off-the-hour cron plus owner dispatch,
carry the owner/collaborator/bot guard as its FIRST job (rule 6j, schedule
bypass), assert its base (rule 6n), regenerate and then prove the WHOLE document
through `make`, and open a PR with the regenerated block ONLY when that block
changed. It MUST NOT merge, MUST NOT push `master`, and its PR body MUST carry no
closing keyword (it implements no issue, and `pr_closure` refuses a claim over an
issue it does not implement).

#### Scenario: a daily run that changes nothing opens nothing

- **Given** a tree whose block already matches
- **When** the pipeline runs
- **Then** it is green with no branch, no commit and no PR
- **Test:** `tests/test_architecture_bot.py::test_wired_into_the_makefile_the_guard_and_the_pipeline`

#### Scenario: the pipeline's shape is asserted, not promised

- **Given** the shipped `architecture-bot.yml`
- **When** the wiring test reads it
- **Then** the guard is the first job, `make base-check`, `make architecture-refresh` and `make architecture-check` are called after a checkout, the PR is gated on `steps.drift.outputs.changed`, the branch stamp ends in `Z`, and no `Closes #` appears
- **Test:** `tests/test_architecture_bot.py::test_wired_into_the_makefile_the_guard_and_the_pipeline`

### Requirement: The real repository's description is current

The repository's own `ARCHITECTURE.md` MUST satisfy `--check` at every commit, and
its block MUST name every workflow and every script in the tree.

#### Scenario: the checked-in block matches the checked-in tree

- **Given** this repository
- **When** `scripts/architecture_bot.py --check` runs against the root
- **Then** it exits 0, and the block contains every `.github/workflows/*.yml` and every file in `scripts/`
- **Test:** `tests/test_architecture_bot.py::test_real_repository_inventory_is_current`
