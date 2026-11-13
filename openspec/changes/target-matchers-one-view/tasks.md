# Tasks — target-matchers-one-view (#752)

- [ ] New guard `tests/test_target_matchers_one_view.py` goes RED on the old tree: a target-line matcher literal outside `architecture_bot.py` is refused
- [ ] `architecture_bot.target_at_line()` becomes the shared line-level view
- [ ] `architecture_check.stage_lists()` uses it; `_ANY_TARGET` deleted
- [ ] `tests/test_architecture_bot.py::_makefile_targets()` delegates to the bot's `make_targets()`
- [ ] `tests/test_workflows.py::_makefile_commands()` uses the bot's `target_at_line()`
- [ ] AGENTS.md §8 guard row added
- [ ] `make openspec-check`, `make architecture-check`, targeted tests green; full `make test` green
