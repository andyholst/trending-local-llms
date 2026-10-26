# pr-body

## ADDED Requirements

### Requirement: The refresh and architecture PR bodies are composed by targets

`make refresh-pr-body` MUST print the run's window block followed by the refresh contract, and MUST
refuse when it has no window. `make architecture-pr-body RUN_URL=…` MUST print a body that names the
run and carries NO closing keyword. Both workflows MUST redirect/pipe the target instead of
building the text inline.

#### Scenario: the refresh body

- **Given** a window block file
- **When** `make refresh-pr-body WINDOW_FILE=…` runs
- **Then** the block is first, the contract follows, and an unreadable window exits non-zero
- **Test:** tests/test_pr_body.py::test_the_other_two_pr_bodies_are_composed_too

#### Scenario: the architecture body

- **Given** a run URL
- **When** `make architecture-pr-body RUN_URL=…` runs
- **Then** the body names the run, references #479 without closing it, and `pr_closure` finds no
  closing claim
- **Test:** tests/test_pr_body.py::test_the_other_two_pr_bodies_are_composed_too

#### Scenario: the workflows hold no body text

- **Given** `refresh-bot.yml` and `architecture-bot.yml`
- **When** their PR steps are read
- **Then** each calls its target, and no inline contract sentence or `printf` body remains
- **Test:** tests/test_pr_body.py::test_the_other_two_pr_bodies_are_composed_too
