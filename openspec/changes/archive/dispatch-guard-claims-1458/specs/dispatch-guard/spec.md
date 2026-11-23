# Spec delta: dispatch-guard (dispatch-guard-claims-1458)

## ADDED Requirements

### Requirement: Shared target paths are serialised across lanes

The guard SHALL accept one or more `--claim <repo-relative path>` arguments (or a
space-separated `CLAIMS=` environment value) naming the files a dispatch will touch. When
at least one claim is given, the guard SHALL read the caller-owned registry's per-lane rows
and SHALL refuse when a claim overlaps a path another lane whose state is `active` already
claims — the same path, or one containing the other at a path-segment boundary. The
refusal SHALL name the HOLDING lane and both paths. A lane whose state is anything else
(`finished`, …) SHALL NOT block: its claims are free. A claim that is not repo-relative
(absolute, `~`, or climbing with `..`) SHALL be refused. The count, stale-target, ceiling
and in-repo-registry refusals SHALL keep firing unchanged, and an invocation with NO claim
SHALL behave exactly as it did before this requirement — the registry's lane rows are not
consulted and a registry without them stays valid.

#### Scenario: No overlap with another lane is allowed

- **Given** a caller-owned registry whose active lane claims `agents/tll-planner/skills/tll-planner/SKILL.md`
- **When** `make dispatch-check ISSUE=<n> --claim scripts/dispatch_guard.py` (or `CLAIMS=`) runs
- **Then** it exits 0, prints `ALLOW`, and carries the claimed paths in the verdict
- **Test:** tests/test_dispatch_guard.py::test_claims_overlap_refuses_active_and_allows_finished

#### Scenario: Overlap with an ACTIVE lane is refused naming the holder

- **Given** a caller-owned registry whose ACTIVE lane `tll-planner` claims `agents/tll-planner/skills/tll-planner/SKILL.md`
- **When** the guard evaluates a dispatch claiming that same path, or its containing directory
- **Then** it refuses with a reason naming the path and the holding lane `tll-planner`
- **Test:** tests/test_dispatch_guard.py::test_claims_overlap_refuses_active_and_allows_finished

#### Scenario: Overlap with a FINISHED lane is allowed

- **Given** a caller-owned registry whose FINISHED lane claims `docs/README.md`
- **When** the guard evaluates a dispatch claiming `docs/README.md`
- **Then** it allows the dispatch, because a finished lane holds nothing
- **Test:** tests/test_dispatch_guard.py::test_claims_overlap_refuses_active_and_allows_finished

#### Scenario: An in-repo claim path is refused

- **Given** a `--claim` value that is absolute (points inside the checkout) or climbs out with `..`
- **When** the guard normalizes the claim
- **Then** it refuses with a reason stating the path must be repo-relative
- **Test:** tests/test_dispatch_guard.py::test_claim_paths_and_registry_rows_are_normalized

#### Scenario: The existing refusals and the no-claim behaviour are unchanged

- **Given** a CLOSED issue, a MERGED bound PR, an over-ceiling count, an in-repo registry, and an open dispatch with overlapping registry claims but NO `--claim`
- **When** the guard evaluates each
- **Then** the first four keep their own refusals, and the claim-free dispatch allows exactly as before
- **Test:** tests/test_dispatch_guard.py::test_cli_and_make_forward_claims_and_keep_existing_refusals
