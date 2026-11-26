# Tasks — test-image-qemu-handler (issue #1747, test-image shape only)

- [x] `refresh-bot.yml` test-image job: pinned `docker/setup-qemu-action` step with `platforms: linux/arm64` before `make test-image-smoke`
- [x] Guard wired into `tests/test_workflows.py::main()` — RED on the old job shape (no handler before smoke), GREEN on this head
- [x] Standalone probe on the two workflow texts: old FAIL, new PASS (qemu@2994 < smoke@3114)
- [x] OpenSpec change with proposal, capability spec + Test line, all tasks ticked; index regenerated
- [x] `findings/1747.md` carries this finding with the owed §8 row declared (rule 3c)
- [x] Fast offline checks green; containerised `make validate` / `live-smoke` are CI-only — blocked: qa-validate runs on the pushed head
