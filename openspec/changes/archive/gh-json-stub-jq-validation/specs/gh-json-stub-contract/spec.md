# gh-json-stub-contract

## ADDED Requirements

### Requirement: the ghost-alarm stub validates every request family the contract records

The stub `gh` in `tests/test_auto_merge_rebase.py` MUST send EVERY request through the ONE
field contract (`scripts/gh_json_fields.py --check-argv`) when that contract has an opinion
about it — a `--json <fields>` list (issue #1158), a `--jq`/`-q` projection (issues
#1668/#1676), or a `gh api <path> --jq <expr>` call. A request the real `gh` would refuse
MUST make the stub exit non-zero, so a test can never prove a property of a request the
production CLI rejects. The stub MUST also be able to answer an `api` request from a
planted payload, so the contract verdict and the recorded answer are both observable.

WHEN the stub is invoked with an argv the contract refuses,
THEN it exits non-zero and names the refusal instead of answering from its own dispatch.

#### Scenario: an unknown `--jq` path is refused, not answered

- **Given** the stub `gh` and a planted `api` payload carrying `title`
- **When** it is invoked as `gh api repos/o/r/pulls/1 --jq .mergedAtX`
- **Then** it exits non-zero naming `.mergedAtX` (the real seam refuses the path), never reaching its own `unexpected gh` branch
- **Test:** `tests/test_auto_merge_rebase.py::test_the_ghost_gh_stub_refuses_a_jq_path_the_contract_refuses`

#### Scenario: a recorded `--jq` path answers from the planted payload

- **Given** the stub `gh` and a planted `api` payload `{"title": "hello"}`
- **When** it is invoked as `gh api repos/o/r/pulls/1 --jq .title`
- **Then** the contract accepts the path and the stub prints `hello`
- **Test:** `tests/test_auto_merge_rebase.py::test_the_ghost_gh_stub_answers_a_recorded_jq_path`

#### Scenario: a `-q` projection outside its own `--json` list is refused

- **Given** the stub `gh`
- **When** it is invoked as `gh pr list --json number -q .title`
- **Then** it exits non-zero naming `.title`, because the same argv's `--json` list does not carry it
- **Test:** `tests/test_auto_merge_rebase.py::test_the_ghost_gh_stub_refuses_a_q_projection_outside_its_json_list`

#### Scenario: the existing `--json` validation half is unchanged

- **Given** the ghost alarm's own reads (`run list`, `run view --json jobs`)
- **When** they are built by the real seam
- **Then** every request still passes the contract, and the ghost pins in this module stay green
- **Test:** `tests/test_auto_merge_rebase.py::test_the_ghost_alarm_refuses_a_gh_answer_of_the_wrong_shape`
