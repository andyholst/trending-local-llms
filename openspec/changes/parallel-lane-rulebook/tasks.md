# Tasks — parallel-lane-rulebook (issue #1767, rulebook §7b/§8 half)

- [x] Fresh worktree off the fetched `origin/master` (`37c6d88150fdb73fd0583a59099aee0b418d7927`), branch `fix/parallel-lane-rule-1767`; owner checkout untouched
- [x] `AGENTS.md` §7b: additive bullet allowing up to 3 concurrent `tll-implementer` lanes (distinct issues, own worktree/branch, signed claim, lease-checked push); Rule 3c note clause for #1767 appended
- [x] `AGENTS.md` §8: guard row naming `test_parallel_implementer_lanes`, `test_parallel_planner_dispatch`, `test_parallel_lane_rulebook`; existing rows unchanged
- [x] `tests/test_parallel_lane_rulebook.py::test_parallel_lane_rulebook` wired into `main()` — RED on base `AGENTS.md` (bullet + row absent), GREEN on this head
- [x] `findings/1767.md` with Evidence / Why / Done when for both findings
- [x] OpenSpec change with proposal, capability spec + Test lines, all tasks ticked; `OPENSPEC.md` regenerated
- [x] Fast offline checks green (pr-body five-section check, pr-closure, lint, authorship, architecture-check); containerised `make validate` / full `make test` are CI-only — blocked: qa-validate runs on the pushed head
