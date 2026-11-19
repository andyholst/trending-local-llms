# test-container

## ADDED Requirements

### Requirement: The test container names the identity it was started under

`scripts/docker_test_run.sh` — the client every `TEST_RUN` target starts its container
through — MUST state the invoking `uid:gid` on its own output and forward it into the
container as `TLL_INVOKING_UID`, a variable NAME carrying the invoker's numeric identity
and never a secret value (rule 3e). It MUST NOT invent a `--user` flag: the container keeps
the image's default user, and the point of the forwarding is that the suite's identity line
(`scripts/coverage_gap.py::identity_line`, read by `scripts/run_tests.sh`) can then state
whether the process ran as the invoking uid or as that default user. Before this, the host
half of the suite assumed the invoking uid while `docker exec <test container> id -u`
answered `0`, and no verdict line could tell the two apart (issue #1147).

#### Scenario: the wrapper states and forwards the invoking identity, and passes no --user

- **Given** `scripts/docker_test_run.sh` run with a `docker` PATH stub that records its argv
- **When** the wrapper starts its container
- **Then** its own output carries `[harness] docker_test_run identity:` naming the invoking
  `uid:gid`, the recorded argv contains `-e` followed by
  `TLL_INVOKING_UID=<uid>:<gid>` and the caller's argv unchanged, and neither the recorded
  argv nor the wrapper's `docker run` line contains `--user`
- **Test:** tests/test_test_container_identity.py::test_the_container_wrapper_names_and_forwards_the_invoking_identity

#### Scenario: the forwarded identity makes a container uid visible in the suite's verdict

- **Given** the seam's `--identity-line` rendered with a forwarded invoking `uid:gid` that
  is not the process's own (the container state: image default user, invoker something else)
- **When** the suite prints its identity line
- **Then** the line names both halves and says `run-as=image default user, NOT the invoking
  uid`, so a privileged-container run is reported rather than mistaken for the invoker's
  identity — the state that let qa-validate run 44551541279 report 135 modules green over a
  permission plant uid 0 walked straight through
- **Test:** tests/test_test_container_identity.py::test_the_identity_line_distinguishes_a_container_uid_from_the_invoker
