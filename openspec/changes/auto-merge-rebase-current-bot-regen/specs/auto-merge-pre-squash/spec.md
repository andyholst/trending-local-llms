## ADDED Requirements

### Requirement: The pre-squash gate regenerates a current bot head's stale generated pair

For an open, non-draft, bot-owned PR whose head already carries `origin/master`,
`make auto-merge-rebase` SHALL run the tree's OWN generators on that tree and SHALL
lease-push a regeneration commit when — and only when — the committed
`OPENSPEC.md` or `ARCHITECTURE.md` differs byte-for-byte from what those generators
render. The decision SHALL NOT use `MAX_OPENSPEC_INDEX_DRIFT` or `openspec_index.py
--drift`; those are deliberate gate slack (#1415), not a measure of correctness. A
landed regeneration SHALL print `verdict=regenerated` and the SAME `rebased=true`
squash-skip key (with the #1616 CI proof), and the new head SHALL pass
`openspec-index-check` and `architecture_bot.py --check`. An already-current pair
SHALL push nothing and keep `verdict=current`, `rebased=false`.

#### Scenario: A current bot head with a stale index is regenerated before the squash

- **Given** an open non-draft bot-owned PR whose head carries `origin/master` (so
  `branch_behind` answers False) but whose committed `OPENSPEC.md` does not list an
  archive its own tree carries, as proved by that tree's own generator
- **When** `make auto-merge-rebase PR=<n>` runs
- **Then** the seam regenerates through the tree's own `--write` generator, commits
  as the agent, lease-pushes to the PR's own head, prints `verdict=regenerated` +
  `rebased=true` and says this run will not merge, and the new head's
  `openspec-index-check` is green while the PR's own commit survives unchanged
- **Test:** tests/test_auto_merge_rebase.py::test_a_current_bot_head_with_a_stale_index_is_regenerated_before_the_squash

#### Scenario: A current bot head whose index is already current pushes nothing

- **Given** the same shape but the committed `OPENSPEC.md` is identical to the tree's
  own `--write` render
- **When** the seam runs
- **Then** nothing is committed or pushed, the branch oid is byte-identical, and the
  output stays `verdict=current`, `rebased=false`
- **Test:** tests/test_auto_merge_rebase.py::test_current_head_reports_current_and_pushes_nothing

#### Scenario: A current bot head stale in both generated files refreshes both

- **Given** a current bot head whose `OPENSPEC.md` and `ARCHITECTURE.md` §10 block are
  both stale against that tree's own generators
- **When** the seam runs
- **Then** the ONE no-rebase sync core calls both `regenerate_index` and
  `regenerate_architecture`, the new head's index and architecture checks are both
  green, and the report names both regenerations (`#1601` pair)
- **Test:** tests/test_auto_merge_rebase.py::test_a_current_bot_head_regenerates_the_architecture_block_too

#### Scenario: A human-owned stale head is reported and untouched

- **Given** a human-authored head whose index is stale and whose generated pair
  differs from its tree
- **When** the seam runs
- **Then** the branch is byte-identical, the output is `verdict=human-owned`,
  `rebased=false`, and no regeneration write occurs — the §6s/#1089 refusal stays
  absolute; narrowing it is an owner ruling (Option B)
- **Test:** tests/test_auto_merge_rebase.py::test_a_human_owned_stale_index_head_is_reported_and_untouched

### Requirement: One shared sync core, with the rebaser unchanged for the sweep

`scripts/pr_health.py` SHALL expose ONE core `sync_branch(cwd, head, *, rebase)` that
creates a detached worktree at the fetched branch tip, optionally rebases onto the
fetched master, runs both regenerators, and lease-pushes with `_git`'s identity
injection and the owner-PAT seam only when a regeneration changed a file.
`rebase_and_push` SHALL remain the `rebase=True` wrapper the §6s sweep uses, with
its `(pushed, ci_verified, message)` contract and #1616 CI proof unchanged;
`regenerate_current` SHALL be the thin `rebase=False` entry point.

#### Scenario: The sweep's rebaser still works through the shared core

- **Given** a behind-and-clean bot branch that the §6s sweep decides to repair
- **When** `rebase_and_push` is called
- **Then** it delegates to `sync_branch(..., rebase=True)`, rebases, regenerates both
  artifacts, lease-pushes with the #1616 CI proof, and keeps its 3-tuple return shape
- **Test:** tests/test_pr_health.py::test_the_rebaser_regenerates_the_index_on_the_rebased_tree
