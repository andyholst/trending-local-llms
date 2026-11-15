# agent-leg-runs-in-test-image

## ADDED Requirements

### Requirement: a self-verifying agent leg runs in the TEST image, never the base

The agent legs that must guard their own change against the repository's
canonical suite — `make implement-issue`, `make review-issue`, `make
review-issue-window`, and `make fix` — invoke their Hermes agent through
`$(TEST_RUN)` (the TEST image: the base image plus `requirements-test.txt`),
not `$(DOCKER_RUN)` (the base image). The TEST image carries the test-only
validators' dependencies (`markdown-it-py`, `pyyaml`, `tabulate`) that
`check_readme_tables_wellformed` and `tests/test_amd_backend.py` need, so the
leg's own `python3 scripts/run_tests.sh` — the self-verification it runs before
its change is judged — succeeds inside its environment, exactly as the `make
test` / `make validate` gates it must pass run in CI.

WHEN a leg that must self-verify (implement / review / fix) launches its agent
THEN the Makefile recipe drives it through `$(TEST_RUN …)` (the TEST image), not `$(DOCKER_RUN)` (the base image),
AND the canonical suite (`tests/test_amd_backend.py`) runs green inside that image,
AND the base image's python still lacks `markdown-it-py` (so the base is provably the wrong place for a self-verifying leg).

#### Scenario: the implementer leg runs the self-verification suite green in the TEST image

- **Given** the shipped `implement-issue` / `review-issue` / `review-issue-window` / `fix` Makefile recipes
- **When** the agent inside the leg runs its self-verification (`python3 scripts/run_tests.sh`, which drives `test_amd_backend.py` → `check_readme_tables_wellformed`)
- **Then** the leg's container is the TEST image — `$(TEST_RUN)` — which installs `markdown-it-py`, so the suite passes instead of redding on `readme-tables: 'markdown-it-py' is not installed`
- **Test:** `tests/test_implement_stream.py::test_agent_legs_run_in_the_test_image` — asserts the shipped recipes use `$(TEST_RUN … make _setup && make _<leg>)`, RED on the pre-#833 `$(DOCKER_RUN)` wiring and GREEN on it

#### Scenario: a non-verifying search leg stays in the cheaper base image

- **Given** the four search legs (`search-nvidia`, `search-metal`, `search-cpu`, `search-amd`)
- **When** they launch their scrape agents
- **Then** they keep `$(DOCKER_RUN)` (the base image) — they never run the canonical suite, so the test image buys them nothing
- **Test:** `tests/test_amd_backend.py::test_wiring_parity` — the search-leg wrappers stay on `$(DOCKER_RUN …)` (unchanged pin)

### Requirement: the test-only validator dependency is declared only where the TEST image installs it

`markdown-it-py` (the README-table validator and `test_amd_backend.py`
dependency) is declared in `requirements-test.in` and layered into the TEST
image only — it must NOT appear in the base `requirements.in` / base
`requirements.txt`. This is the precondition that makes running a
self-verifying leg in the base image a false-red (the defect issue #833's run
hit) and the TEST image the correct environment.

WHEN the dependency manifests are read
THEN `markdown-it-py` is declared in `requirements-test.in`
AND it is absent from the base `requirements.in`
AND every self-verifying agent leg runs where that test dep is installed.

#### Scenario: the base image lacks markdown-it-py, the test image provides it

- **Given** `requirements.in` (base) and `requirements-test.in` (test image)
- **When** the manifests and the characterisation (a python without `markdown_it` reds `test_amd_backend.py`) are checked
- **Then** `markdown-it-py` appears only in `requirements-test.in`, base `requirements.in` does not name it, and the guard passes
- **Test:** `tests/test_implement_stream.py::test_markdown_it_is_a_test_image_dependency` — RED if `markdown-it-py` ever leaks into `requirements.in` or into the base image layer
