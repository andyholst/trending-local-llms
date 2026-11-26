## ADDED Requirements

### Requirement: The planner may run up to three implementer lanes concurrently

The planner SHALL dispatch up to 3 `tll-implementer` lanes CONCURRENTLY against DISTINCT open
issues when their target files differ, and SHALL serialise only a genuine shared-file collision
through `make dispatch-check ISSUE=<n> MACHINE=<user@host> CLAIMS="p1 p2"`. The board is never
drained strictly one lane at a time while movable issues and PRs remain.

#### Scenario: Three distinct open issues with disjoint target files

- **Given** three open issues whose implementer target files do not overlap
- **When** the planner works the board
- **Then** it dispatches three lanes in the same cycle, one issue per lane, each against the freshly fetched `origin/master` sha
- **Test:** tests/test_parallel_planner_dispatch.py::test_the_guard_is_green_on_the_working_tree

#### Scenario: A clause is absent from the fetched base

- **Given** the fetched `origin/master` planner skill before this change
- **When** the source-level guard reads that base blob through `git show`
- **Then** all ten contract clauses are reported absent (RED), naming the base sha
- **Test:** tests/test_parallel_planner_dispatch.py::test_the_guard_is_red_on_the_fetched_base

### Requirement: Every concurrent lane is separately accountable

Each dispatched lane SHALL have its own query file, its own signed issue claim with the
twice-claim race guard, its own worktree off the fetched `origin/master`, its own lease-checked
branch ending in `-<issue>` pushed with `--force-with-lease` pinned to the freshly fetched remote
ref, and its own board-visible bookend pair on the issue thread (signed start `dispatch #<id>`
and signed finish `done #<id> · handover <...>`).

#### Scenario: A lane's branch ref moved before its push

- **Given** a per-lane branch whose remote ref advanced after the dispatch was written
- **When** the lane attempts its lease-checked push
- **Then** the push is refused and the lane STOPs rather than overwriting another writer, and the collision is ruled on the shared issue thread
- **Test:** tests/test_parallel_planner_dispatch.py::test_each_clause_is_named_in_the_dispatch_section

#### Scenario: A lane finishes without a thread bookend

- **Given** a pushed branch and an opened PR but no signed finish comment on the issue's OWN thread
- **When** the planner reads the board to delegate the next step
- **Then** the lane is not treated as done, because a chat message or a branch alone is not a bookend
- **Test:** tests/test_parallel_planner_dispatch.py::test_the_guard_is_green_on_the_working_tree

### Requirement: Protected work and merges stay behind a human gate

The planner SHALL NOT dispatch onto a tech-debt issue or a protected-rulebook issue (`AGENTS.md`
§7b/§8 or an `agents/*/SOUL.md` edit under rule 3c) without explicit owner sign-off on that issue
thread; a reviewer's process acceptance is not write approval. The planner SHALL NOT merge, open a
branch, or push to master — qa-validate merges green heads only. Rule-3c rows this head cannot
write are declared as owed rows in the findings file.

#### Scenario: A dispatch target is a protected-rulebook issue with no owner sign-off

- **Given** an open issue whose work requires an `AGENTS.md` §8 or `agents/*/SOUL.md` edit and whose thread carries no owner sign-off
- **When** the planner considers that issue for a lane
- **Then** it does not dispatch, and records the owed row in `findings/1767-planner.md` for an attended run
- **Test:** tests/test_parallel_planner_dispatch.py::test_the_contract_keeps_the_existing_guardrails

#### Scenario: The guard is silently dropped from the test runner

- **Given** the source guard module exists but no `main()` calls its `test_*` functions
- **When** the guard's wiring self-check runs
- **Then** it fails, because a test never called from `main()` never executes in `make test`
- **Test:** tests/test_parallel_planner_dispatch.py::test_the_guard_is_discovered_and_called
