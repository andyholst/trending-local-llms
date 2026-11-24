## ADDED Requirements

### Requirement: pip-tools console scripts are named before the shorter pip token

A guard SHALL recognise `pip-compile`, `pip-sync` and `pip-tools` as their OWN interpreter tokens in a PUBLIC make target's recipe, shell expression or reachable private hop, and SHALL order them before the bare `pip` alternative in the token match so a trailing `-` cannot launder the finding. The near-miss spellings `python3.12`, `my-python3` and `scripts/pip` SHALL remain non-matches.

#### Scenario: A planted pip-tools console script in a public target is named

- **Given** a Makefile whose NON-exception PUBLIC target `search-smoke` carries a bare `pip-compile --quiet …` and a bare `pip-tools --version`
- **When** the detector runs against that Makefile
- **Then** it exits non-zero and reports both findings naming `search-smoke` and their physical line numbers with tokens `pip-compile` and `pip-tools`
- **Test:** tests/test_os_agnostic_make.py::test_the_detector_sees_the_pip_tools_console_scripts_and_keeps_them_harnessed

#### Scenario: The real pip-tools recipes stay green because they are harnessed

- **Given** the real Makefile whose private `_requirements` / `_generate-requirements` recipes carry those commands and whose only public entries are `$(DOCKER_RUN) make _x` hops
- **When** the detector walks `requirements` and `generate-requirements`
- **Then** both walks are empty and the real tree exits 0 — clean for the right reason (containerised), not because the token set cannot see the commands
- **Test:** tests/test_os_agnostic_make.py::test_the_detector_sees_the_pip_tools_console_scripts_and_keeps_them_harnessed
