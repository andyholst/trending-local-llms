## ADDED Requirements

### Requirement: The test container receives the GitHub token by name

The container test suite must run its GitHub-bound probes authenticated: the `TEST_RUN` macro forwards `GH_TOKEN` by NAME (never a value), and qa-validate's `Run unit tests (in container)` step provides the value through the job's own default token (`GH_TOKEN: ${{ github.token }}`), so `scripts/engine_registry.py::fetch_repo_meta` sends its `Authorization: Bearer` header in CI and an aged-registry WARN can no longer red every PR through the unauthenticated 60 req/h NAT limit.

#### Scenario: The Makefile forwards GH_TOKEN by name into the test container

Given the `TEST_RUN` recipe in the Makefile
When it is read and the container run is executed through `scripts/docker_test_run.sh` with a PATH-stubbed docker recording its argv
Then the recorded argv contains `-e GH_TOKEN` and no token VALUE anywhere in the command

- **Test:** tests/test_engine_registry.py::test_the_test_container_gets_the_github_token_by_name

#### Scenario: qa-validate's test step provides the job token as the value

Given the `Run unit tests (in container)` step of qa-validate.yml
When its wiring is read
Then the step maps `GH_TOKEN` in its `env:` to `${{ github.token }}` and still runs only `make test` (no target bypassed, rule 6m)

- **Test:** tests/test_engine_registry.py::test_the_test_container_gets_the_github_token_by_name

#### Scenario: A token in the environment makes the product's request authenticated

Given `GH_TOKEN` set in the environment and no `ENGINE_REGISTRY_META_FILE`
When `fetch_repo_meta` builds its request to the GitHub repos API
Then the request carries `Authorization: Bearer <token>` (and no token in the environment means no Authorization header at all)

- **Test:** tests/test_engine_registry.py::test_fetch_repo_meta_network_paths
