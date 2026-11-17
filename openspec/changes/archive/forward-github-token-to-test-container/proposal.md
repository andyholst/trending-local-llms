# Forward the job GitHub token, BY NAME, to the container test suite (Issue: #1095)

Issue: #1095
PR: #1100

## Why

`make test`'s container probes `api.github.com` for engine-registry repo metadata (rule: every engine must point at a real repo). `scripts/engine_registry.py::fetch_repo_meta` reads `GH_TOKEN`/`GITHUB_TOKEN` and sends `Authorization: Bearer …` — but nothing forwards a token into the test container: `TEST_RUN` (Makefile) forwards only NOUS/FIRECRAWL/HF/TYPESAFE, and qa-validate's `Run unit tests (in container)` step carries no env. GitHub's unauthenticated limit is 60 req/h per shared NAT'd runner IP: measured run 43896135854 (PR #1092, head b9b64d8) red the merge gate on one aged registry WARN (`'StairCut': unreachable … 24d old: REPEAT past one refresh`) while the same head passed locally 129/129 and via curl — the merge gate is nondeterministic, decided by one probe's rate-limit luck.

## What Changes

- `Makefile` `TEST_RUN`: forward `-e GH_TOKEN` by NAME (rule 3e — never a value on a line; unset on a host stays unset in the container, which is today's behavior).
- `.github/workflows/qa-validate.yml` `Run unit tests (in container)` step: `env: GH_TOKEN: ${{ github.token }}` — the job's own default token (contents:read; authenticated public GETs lift the 60/h NAT ceiling), still only through `make test` (rule 6m).
- `tests/test_engine_registry.py`: new test `test_the_test_container_gets_the_github_token_by_name` — asserts the `TEST_RUN` recipe line carries `-e GH_TOKEN` (read from the Makefile), asserts the qa-validate test step's `env:` maps `GH_TOKEN` to `${{ github.token }}`, and drives `scripts/docker_test_run.sh` with a PATH-stubbed `docker` (external system stand-in, rule 6m) to prove the forwarded flag reaches the real container argv.

## Impact

- `validate`/`live-smoke` stop flaking on registry probes under GitHub rate limits; a green local `make test` predicts a green PR again.
- No new secrets: `github.token` is the job's default identity, forwarded by name only.

## Not covered

- A recorded-fixture fallback for `fetch_repo_meta` (the Done-when's alternative shape) — the token-forwarding half is the fix; the offline cache stays available via `ENGINE_REGISTRY_META_FILE`.
- `make live`/`live-smoke`'s other stages that probe GitHub (they share `TEST_RUN`/`DOCKER_RUN` only where already wired).
