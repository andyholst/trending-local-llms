## ADDED Requirements

### Requirement: A private hop is followed in both make spellings

A guard SHALL follow a recipe line's hop into a PRIVATE `_x` recipe whether the hop is spelled `$(MAKE) … _x` or the plain `make _x`, including an optional run of make flags and a leading recipe-echo `@`. A hop line carrying a container harness SHALL remain clean under both spellings.

#### Scenario: A bare host interpreter reached through a plain hop is detected

- **Given** a Makefile whose PUBLIC target `search-smoke` exposes the private `_setup` recipe through one plain `make _setup` hop, and `_setup` runs a bare `python3 scripts/query_vocab.py --print nvidia`
- **When** the detector runs against that Makefile
- **Then** it exits non-zero and reports a finding naming `search-smoke` and the private recipe's physical line number
- **Test:** tests/test_os_agnostic_make.py::test_the_guard_follows_both_hop_spellings_into_private_recipes

#### Scenario: The recursive spelling reaches the same private recipe

- **Given** the same Makefile with the hop written `$(MAKE) --no-print-directory _setup`
- **When** the detector walks `search-smoke`
- **Then** it reports the same finding — one behaviour across both spellings
- **Test:** tests/test_os_agnostic_make.py::test_the_guard_follows_both_hop_spellings_into_private_recipes

#### Scenario: A harnessed hop stays green under both spellings

- **Given** the same private recipe carrying a bare host interpreter, reached through `$(DOCKER_RUN) make _setup` or `$(DOCKER_RUN) sh -c "make _setup"`
- **When** the detector walks the public target
- **Then** the walk is empty — the hop already runs inside the container, which is the suppression the guard has always had
- **Test:** tests/test_os_agnostic_make.py::test_the_guard_follows_both_hop_spellings_into_private_recipes
