# agent-image-publish

## ADDED Requirements

### Requirement: The agent image is published deliberately, behind a guard

Publishing the image every bot job runs in MUST be a deliberate act with its own
pipeline: dispatch-only, the owner/collaborator guard first and before any secret,
and the default `GITHUB_TOKEN` as the credential. No data refresh and no pull
request may publish it.

WHEN the publish pipeline is triggered, THEN its first job verifies that both
`github.actor` and `github.triggering_actor` are the owner or a collaborator with
`admin`, `maintain` or `write` — before any secret is read — and it can be
triggered in no other way than `workflow_dispatch`.

#### Scenario: only a manual dispatch can publish

- **Given** the workflow file
- **When** its triggers are read
- **Then** it declares `workflow_dispatch` and none of `schedule`, `pull_request`, `push`, `workflow_run`
- **Test:** `tests/test_publish_agent_image.py::test_the_pipeline_is_dispatch_only`

#### Scenario: the guard runs first and reads both actors

- **Given** the workflow file
- **When** its jobs are read in order
- **Then** `guard` is the first job, `publish` needs it, and the guard checks `github.actor` and `github.triggering_actor`, allowing only `admin|maintain|write` and refusing everyone else
- **Test:** `tests/test_publish_agent_image.py::test_the_guard_runs_first_and_before_any_secret`

#### Scenario: publishing uses the default token

- **Given** the workflow file
- **When** its credential use is read
- **Then** the GHCR login is the default `github.token` as the triggering actor, it asks for `packages: write` and `contents: read`, and no `secrets.` reference appears
- **Test:** `tests/test_publish_agent_image.py::test_publishing_uses_the_default_token_not_a_pat`

#### Scenario: the pipeline never lands a change

- **Given** the workflow file
- **When** it is read for git writes
- **Then** it contains no `gh pr merge`, no `git push` and no PR-head checkout
- **Test:** `tests/test_publish_agent_image.py::test_the_pipeline_never_merges_and_never_pushes_a_branch`

### Requirement: The credential is proven before the build

A publish run MUST fail in seconds when the credential cannot write the package,
instead of after the multi-minute build that re-downloads Hermes.

WHEN the publish job runs, THEN it executes `make agent-image-push-check` — one
empty blob-upload POST — before `make publish-agent-image`, and repeats the
registry's own refusal when that POST is refused.

#### Scenario: the probe runs before the build

- **Given** the workflow's publish job
- **When** its steps are read in order
- **Then** `make agent-image-push-check` appears before `make publish-agent-image`
- **Test:** `tests/test_publish_agent_image.py::test_the_push_check_runs_before_the_build`

#### Scenario: a refused credential reports the registry's words

- **Given** a registry that refuses the upload session with `permission_denied: create_package`
- **When** `make agent-image-push-check` runs against it
- **Then** it exits non-zero, repeats that message verbatim, and says the image build was NOT started
- **Test:** `tests/test_publish_agent_image.py::test_push_check_proves_the_credential_before_the_build`

#### Scenario: no credential is a loud failure

- **Given** no `GITHUB_TOKEN` and no `GH_TOKEN`
- **When** `make agent-image-push-check` runs
- **Then** it exits non-zero, names the credential it needs and says the build was NOT started
- **Test:** `tests/test_publish_agent_image.py::test_push_check_proves_the_credential_before_the_build`

### Requirement: A publish is a no-op when this revision is already published

The hash tag names the image's inputs, so re-publishing unchanged inputs MUST cost
seconds — and a forced rebuild MUST be possible when it is genuinely needed.

WHEN the hash tag is already on the registry, THEN `make publish-agent-image`
builds nothing and pushes nothing unless `--force`/`FORCE=1` was given; otherwise
it builds once and pushes BOTH the hash tag and the consumer `:latest` ref.

#### Scenario: an already-published revision costs nothing

- **Given** the registry serves this revision's `dockerfile-<sha12>` tag
- **When** `make publish-agent-image` runs
- **Then** it exits 0 saying the tag is already published, and no `docker build` and no `docker push` is executed
- **Test:** `tests/test_publish_agent_image.py::test_publish_is_a_noop_when_this_revision_is_already_published`

#### Scenario: an absent tag is built once and published under both refs

- **Given** the tag is not on the registry
- **When** `make publish-agent-image` runs
- **Then** it builds once with the hash tag and pushes both that tag and `:latest`
- **Test:** `tests/test_publish_agent_image.py::test_publish_builds_and_pushes_both_refs_when_absent`

#### Scenario: force rebuilds the same inputs on demand

- **Given** the tag is already published
- **When** `make publish-agent-image FORCE=1` runs
- **Then** it builds and pushes anyway
- **Test:** `tests/test_publish_agent_image.py::test_force_rebuilds_the_same_inputs_on_demand`

#### Scenario: the refs come from the one script that owns the tags

- **Given** `make agent-image-ref` and `make image-tags`
- **When** both are run
- **Then** the hash tag they print is the same value, and `ref` also prints the consumer `:latest` ref
- **Test:** `tests/test_publish_agent_image.py::test_ref_prints_the_hash_tag_and_the_consumer_tag`
