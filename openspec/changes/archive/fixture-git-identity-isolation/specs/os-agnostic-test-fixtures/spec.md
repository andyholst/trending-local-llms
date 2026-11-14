# os-agnostic-test-fixtures

## ADDED Requirements

### Requirement: A git fixture's identity is decided by the fixture, never by the machine running the suite

A test that drives a scripted git MUST isolate git configuration to the fixture:
the child environment carries `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` pointing
at empty files by default, so "the checkout has no identity" means the same thing
on a developer laptop with a global git identity and in the CI container. A
fixture repo that configures its OWN identity MUST keep it: the product's
never-override rule is exercised locally, not only asserted.

#### Scenario: the identity-fallback lock passes on a host that HAS a global git identity

- **Given** the `test_worktree_base.py` rebase fixture — commits made only through
  `-c user.*` overrides, so the clone stores no identity — run on a machine whose
  user HAS a global git identity
- **When** `run_script` executes the rebase mode with its default isolated child env
- **Then** the scripted `git config user.email` inside the script reads EMPTY, the
  script prints `identity=fallback`, and the assertion
  "it falls back to the repo's bot identity when the checkout has none" goes GREEN
- **Test:** tests/test_worktree_base.py::test_rebase_brings_the_commit_onto_the_fetched_tip

#### Scenario: a fixture repo with its own identity is never overridden

- **Given** a rebase fixture whose repo config carries its OWN `user.email`
- **When** the rebase mode runs through the isolated `run_script`
- **Then** `identity=fallback` is NOT printed and the rebased commit's committer
  is the fixture repo's identity
- **Test:** tests/test_worktree_base.py::test_rebase_respects_a_configured_checkout_identity
