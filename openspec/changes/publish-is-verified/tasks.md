# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `publish()` re-probes BOTH refs after the pushes (`_serves`, bounded retries) and raises `PublishUnverified`
- [x] 3. The CLI exits 1 with `[publish] FAIL:` naming the refs the registry does not serve
- [x] 4. The docker stub serves what a push writes, and `FAKE_DOCKER_PUSH_INVISIBLE=1` models the invisible case
- [x] 5. The guard covers the happy path (VERIFIED, both refs asked) and the invisible path (exit 1, names them)
- [x] 6. Verified RED on the pre-change script (4 failures — it never asked the registry) and GREEN after (`PASSED 82 | FAILED 0`)
- [x] 7. `OPENSPEC.md` regenerated; `openspec-index-check` and `check_openspec_tasks` green
- [x] 8. `make lint`, `make test`, `make architecture-check` and `make openspec-check` green
