# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. The `displayTitle` backstop (`in_flight`) is deleted, with `_runs()` and its call
- [x] 3. `reason=run-in-flight` and `started` follow the start comment / start activity only
- [x] 4. The module's docstring and the inline comment name the start comment as the one signal, with the measured reason
- [x] 5. `test_the_queue_attributes_a_run_by_its_start_comment_not_its_title` covers the title-only case, the no-`run list` call, and the fresh start comment
- [x] 6. Verified RED on the pre-change queue (3 failures: `started=1`, `reason=run-in-flight`, the `run list` call) and GREEN after (`PASSED 70 | FAILED 0`)
- [x] 7. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 8. `make lint`, `make test`, `make architecture-check` and `make openspec-check` green
