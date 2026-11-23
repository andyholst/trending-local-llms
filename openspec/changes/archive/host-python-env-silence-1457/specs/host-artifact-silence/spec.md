## ADDED Requirements

### Requirement: A redirected target's host prerequisite writes nothing to fd 1

The `python-env-image` prerequisite SHALL be silent when the host branch runs: its
recipe line SHALL be `@`-prefixed so make does not echo it, and the ensure script's
stdout SHALL be redirected off fd 1. The in-container `@:` escape SHALL stay silent and
unchanged.

#### Scenario: The host expansion is silent

- **Given** `make -n pr-body ISSUE=<n>` expanded with `IN_CONTAINER=` empty
- **When** the expansion is read
- **Then** the prerequisite's ensure command is present and carries a stdout redirection off fd 1
- **Test:** tests/test_python_env_in_container.py::test_the_host_ensure_recipe_is_silent

### Requirement: The forced host branch's artifacts are byte-pure

Given the host branch forced (`IN_CONTAINER=` empty), `make pr-title` and `make pr-body`
SHALL print exactly the composer's output and nothing else, so a redirected artifact
holds no ensure line.

#### Scenario: The PR title

- **Given** the host branch forced and a stub `docker` standing in for the container runtime
- **When** `make pr-title ISSUE=<n> KIND=<k>` runs
- **Then** its stdout is byte-equal to `pr_body.title(<n>, <k>) + "\n"`
- **Test:** tests/test_pr_body.py::test_the_forced_host_branch_stdout_is_byte_pure

#### Scenario: The PR body

- **Given** the host branch forced and a stub `docker` standing in for the container runtime
- **When** `make pr-body ISSUE=<n> BRANCH=<b>` runs
- **Then** its stdout is byte-equal to `pr_body.render(<n>, <b>)`
- **Test:** tests/test_pr_body.py::test_the_forced_host_branch_stdout_is_byte_pure

### Requirement: The redirect guard covers a redirected target's prerequisites

The workflow redirect guard SHALL resolve a redirected target's PREREQUISITE recipes,
including recipe lines inside conditional branches, and refuse a prerequisite recipe
that is not silent.

#### Scenario: A noisy prerequisite

- **Given** a workflow line `make <target> … > <file>`
- **When** the redirect guard scans
- **Then** it also refuses a non-silent recipe on any prerequisite of `<target>`
- **Test:** tests/test_workflows.py::test_a_recipe_redirected_into_a_file_never_echoes_its_own_command

### Requirement: The keeper body carries no ensure line

The real `make keeper-pr` sequence with `BODY_TARGET=architecture-pr-body` SHALL capture
a body with no `ensure_image.py` line when the host branch is forced.

#### Scenario: The captured keeper body

- **Given** the shipped publish step run against the real keeper seam with the host branch forced
- **When** the body is captured
- **Then** it contains no `ensure_image.py` line
- **Test:** tests/test_architecture_bot.py::test_the_shipped_steps_actually_commit_push_and_open_a_pr
