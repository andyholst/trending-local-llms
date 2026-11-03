# test-container

## ADDED Requirements

### Requirement: a killed test client removes its container

`TEST_RUN` SHALL start the test container through `scripts/docker_test_run.sh`. That wrapper SHALL name the container and SHALL remove that name when the wrapper process dies, including when the wrapper is killed.

#### Scenario: the client is killed

- **GIVEN** a `TEST_RUN` client that has started its container,
- **WHEN** that client is killed,
- **THEN** the container it named is removed.

- **Test:** `tests/test_docker_test_run.py`
