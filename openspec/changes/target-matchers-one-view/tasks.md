# Tasks — target-matchers-one-view (#752)

- [x] New guard `tests/test_target_matchers_one_view.py` goes RED on the old tree: a target-line matcher literal outside `architecture_bot.py` is refused (measured: 5 FAILs on the base commit, three copies named)
- [x] `architecture_bot.target_at_line()` becomes the shared line-level view
- [x] `architecture_check.stage_lists()` uses it; `_ANY_TARGET` deleted
- [x] `tests/test_architecture_bot.py::_makefile_targets()` delegates to the bot's `make_targets()` (suite green: 79/79)
- [x] `tests/test_workflows.py::_makefile_commands()` uses the bot's `target_at_line()`
- [x] AGENTS.md §8 guard row added
- [ ] full `make test` + `make lint` + `make openspec-check` green on the branch
