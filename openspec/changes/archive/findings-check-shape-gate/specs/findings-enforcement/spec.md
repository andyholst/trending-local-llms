## ADDED Requirements

### Requirement: The analysis gate is shape-aware

`make findings-check-for-pr` SHALL fail when an implementation-shaped PR head
has no well-formed `findings.md`, and SHALL stay green for a PR that is not an
implementation. "Implementation-shaped" SHALL be decided by
`scripts/pr_closure.implementation_shaped`, built only from that module's
existing derivations (`implemented_issue`, a closing binding, or an
`implement #<n>` claim), with the declared `NON_IMPLEMENTATION_BRANCHES` prefixes
winning over any claim.

#### Scenario: An implementation-shaped head with no findings.md

- **Given** a head branch `ci/data-gap-12-x` and no `findings.md`
- **When** `scripts/file_findings.py --check --branch ci/data-gap-12-x` runs
- **Then** it exits non-zero and names `findings.md`
- **Test:** tests/test_file_findings.py::test_an_implementation_shaped_head_without_findings_goes_red

#### Scenario: A run that found nothing is still green

- **Given** an implementation-shaped head carrying `findings.md` = `- none`
- **When** the check runs
- **Then** it exits 0 and reports `0 finding(s)`
- **Test:** tests/test_file_findings.py::test_none_is_a_valid_empty_analysis

#### Scenario: Every exempt shape is skipped

- **Given** each of `ci/trending-refresh-<UTC>`, `ci/keeper-<slug>`,
  `ci/openspec-index-repair-<UTC>`, `ci/architecture-block-repair-<UTC>`,
  `ci/openspec-invalid-change-repair-<UTC>`, `ci/pipeline-failure-ledger-<UTC>`,
  `docs/<slug>-1394` and `rule/<slug>-1432`, with no `findings.md`
- **When** the check runs with that branch
- **Then** it exits 0 and the SKIP line names the exempt prefix
- **Test:** tests/test_file_findings.py::test_exempt_shapes_are_skipped

#### Scenario: A push or dispatch event is a green no-op

- **Given** `--event` naming a payload with no `pull_request`
- **When** the check runs
- **Then** it exits 0 and reports nothing to require
- **Test:** tests/test_file_findings.py::test_a_push_event_is_a_green_noop

#### Scenario: A closing claim alone makes a shapeless branch implementation

- **Given** `--branch shapeless-branch --body-file` whose body says `Closes #12`
- **When** the check runs
- **Then** it exits non-zero because the claim makes it implementation-shaped
- **Test:** tests/test_file_findings.py::test_a_closing_claim_alone_makes_it_implementation

#### Scenario: A quoted claim is not a claim

- **Given** a shapeless branch whose body quotes `` `Closes #12` `` in backticks
- **When** the check runs
- **Then** it exits 0 — `visible_text` strips code, the same view GitHub binds
- **Test:** tests/test_file_findings.py::test_a_quoted_claim_is_not_a_claim

### Requirement: The gate is wired where CI decides

The shape-aware check SHALL be reachable from `make` and SHALL be executed by
`qa-validate`'s `validate` job and by `scripts/fix_loop.sh`, so a direct
worktree PR cannot be green without its analysis.

#### Scenario: Wiring is read from the tree

- **Given** the Makefile, `qa-validate.yml`, `scripts/fix_loop.sh` and
  `ARCHITECTURE.md`
- **When** the wiring assertions run
- **Then** the target exists, the workflow calls it, the loop lists it, and the
  description documents it
- **Test:** tests/test_file_findings.py::test_the_shape_gate_is_wired_to_ci_and_the_fix_loop
