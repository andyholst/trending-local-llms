## ADDED Requirements

### Requirement: The `R:` marker resolves a PR run first seen after its merge

`watch_monitor` SHALL resolve a `pull_request` run whose live `pull_requests` is empty from the
merge-surviving `head_branch` source before the diff runs, so the emitted marker still carries
its trailing `:<pr>` on the run's FIRST sight. GitHub clears a run's `pull_requests` once its
PR merges and the branch is deleted, and the caller-owned `run_prs` map can only record a run
seen while the association was live; a red run whose first sight is post-merge would otherwise
lose the thread a woken lane must read. The marker's SHAPE SHALL NOT change: a push-triggered
run and an unresolvable PR run keep the shorter form.

#### Scenario: A first-sight post-merge run names its PR

- **Given** a run row `{"id": 45116060775, "status": "completed", "conclusion": "failure", "name": "qa-validate", "event": "pull_request", "head_branch": "ci/tech-debt-pr-rebase-soul-1361", "pull_requests": []}` and a resolved branch map `{"ci/tech-debt-pr-rebase-soul-1361": 1362}`
- **When** `inject_run_prs` enriches the row and `marker_state` diffs it into an empty state
- **Then** the emitted marker is `R:45116060775:completed:failure:qa-validate:1362` and the next state's `run_prs` maps `"45116060775"` to `"1362"`
- **Test:** tests/test_watch_monitor.py::test_r_marker_resolves_a_pr_first_seen_after_the_merge

#### Scenario: A push run and an unresolved branch are never given a PR

- **Given** a `push` run with `head_branch: "master"` and a `pull_request` run whose `head_branch` is absent from the resolved map
- **When** `inject_run_prs` runs over both
- **Then** both rows keep `pull_requests: []`, so the push marker keeps its shorter shape and no PR number is invented
- **Test:** tests/test_watch_monitor.py::test_r_marker_resolves_a_pr_first_seen_after_the_merge

#### Scenario: A live association is not overwritten

- **Given** a `pull_request` run already carrying `pull_requests: [{"number": 5}]` and a resolved map naming a different number for its branch
- **When** `inject_run_prs` runs
- **Then** the row keeps `[{"number": 5}]`
- **Test:** tests/test_watch_monitor.py::test_r_marker_resolves_a_pr_first_seen_after_the_merge

### Requirement: The branch resolution is capped and never guesses

`watch_monitor.resolve_branch_prs` SHALL resolve a branch with `gh pr list --state all --head
<branch>` and accept the answer only when it is exactly one PR, so an ambiguous, empty or
unreadable branch contributes nothing. It SHALL resolve at most `PR_RESOLVE_MAX` branches per
call, so a tick following a burst of merges cannot become a request storm.

#### Scenario: Only a unique PR resolves

- **Given** a stub `gh` on PATH answering one branch with two PRs, one with an empty list, one with a non-zero exit and one with a single PR
- **When** `resolve_branch_prs` runs over the four branches
- **Then** only the single-PR branch is in the returned map
- **Test:** tests/test_watch_monitor.py::test_branch_resolution_is_capped_and_never_guesses

#### Scenario: The per-tick budget bounds the request count

- **Given** more branches than `PR_RESOLVE_MAX`
- **When** `resolve_branch_prs` runs
- **Then** exactly `PR_RESOLVE_MAX` `gh` invocations are made
- **Test:** tests/test_watch_monitor.py::test_branch_resolution_is_capped_and_never_guesses

### Requirement: The guard fails on the pre-change seam

The new scenarios SHALL be RED against the base revision's `scripts/watch_monitor.py`, because
the base seam has no `inject_run_prs`/`resolve_branch_prs` and therefore cannot name a PR on a
first-sight post-merge run. A guard that passes on both revisions locks nothing.

#### Scenario: The base seam cannot resolve a first-sight post-merge run

- **Given** `git show origin/master:scripts/watch_monitor.py` swapped into the tree
- **When** `tests/test_watch_monitor.py` runs
- **Then** the module fails (`inject_run_prs` does not exist), and it passes again once the change is restored
- **Test:** tests/test_watch_monitor.py::test_r_marker_resolves_a_pr_first_seen_after_the_merge
