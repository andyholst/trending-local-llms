# Spec delta: image-fallback-announcement

## ADDED Requirements

### Requirement: The corrupt-tag fallback reports itself machine-readably

When `ensure_base`, `ensure_test` or `ensure_openspec` takes the published-
but-corrupt fallback (issue #1118: the registry serves the tag's manifest but
not its blobs) and builds the image locally, the seam SHALL print one line
`corrupt-tag-fallback=<image>=<tag>` (image ∈ {base, test, openspec}) alongside
the existing prose verdict. A normal pull, a not-published build or a local
reuse SHALL print no such line — the line means exactly "this image was built
without a pull" and nothing else.

#### Scenario: A corrupt tag fallback prints the report line

- **Given** a published base tag whose `docker pull` fails with the
  missing-blob wording (PATH-stubbed docker)
- **When** `ensure_image.py ensure-base` runs
- **Then** the verdict prose still names the corrupt tag, and the stdout
  carries a `corrupt-tag-fallback=base=<tag>` line
- **Test:** tests/test_ensure_image.py::test_the_corrupt_fallback_reports_its_image_machine_readably

#### Scenario: A healthy path prints no report line

- **Given** a published, pullable tag and a not-published tag (stubbed docker)
- **When** the corresponding ensure paths run
- **Then** no `corrupt-tag-fallback=` line appears on stdout
- **Test:** tests/test_ensure_image.py::test_a_healthy_path_prints_no_fallback_report

### Requirement: qa-validate announces a corrupt-tag fallback on the PR

`make announce-image-fallback` SHALL post exactly ONE comment on the PR naming
which images were built without a pull (image name and tag), carrying the
registered `corrupt-tag-fallback` marker stamped `run=<run-id>` (the
`bot_markers` registry is the only marker spelling, rule 6j), through
`gh issue comment` with the ambient default `github.token`. Before posting it
SHALL read the PR's comments with `--paginate` and skip when a comment already
carries this run's marker stamp; a stamp of a different run does NOT suppress
a new announcement. A missing PR number, repo or images list is a loud exit 2,
never a silent pass.

#### Scenario: The fallback is announced with the registered marker

- **Given** images `base` and `openspec` reported built-not-pulled and a PR
  with no such comment (PATH-stubbed gh recording its argv)
- **When** `scripts/announce_image_fallback.py --post` runs
- **Then** one `gh issue comment` was called, its body names both images and
  their tags, and `bot_markers.read_marker` reads the comment back as the
  `qa-validate`/`image_fallback` marker with this run's id
- **Test:** tests/test_image_fallback_announce.py::test_the_announcement_names_the_images_and_carries_the_registered_marker

#### Scenario: One announcement per run

- **Given** a PR whose comments already carry a marker stamped `run=<same-id>`
- **When** the announcer runs again for the same run
- **Then** no second comment is posted and the script exits 0 saying it deduped
- **Test:** tests/test_image_fallback_announce.py::test_the_announcement_is_deduplicated_by_the_run_id

#### Scenario: A newer run may announce again

- **Given** a PR whose only such marker is stamped with an OLDER run id
- **When** the announcer runs for a NEW run id
- **Then** the new announcement is posted (the marker's `run=` is the dedup key)
- **Test:** tests/test_image_fallback_announce.py::test_the_announcement_is_deduplicated_by_the_run_id

#### Scenario: The comment read is not first-page-only

- **Given** a PR comment thread (stubbed gh answering page by page)
- **When** the announcer checks for an existing announcement
- **Then** the recorded `gh issue comment list` call carries `--paginate` (the
  #662 class: a first-page read misses the newest comment and double-posts)
- **Test:** tests/test_image_fallback_announce.py::test_a_long_thread_is_read_whole_for_the_dedupe

#### Scenario: Missing inputs refuse loudly

- **Given** a call with no PR number (or no images, or no repo)
- **When** the announcer runs
- **Then** it exits 2 with a refusal naming the missing input and posts nothing
- **Test:** tests/test_image_fallback_announce.py::test_missing_inputs_fail_loudly

### Requirement: qa-validate wires the announcement through the Makefile

The `validate` job of `qa-validate.yml` SHALL capture `make image-ensure` and
`make openspec-check` output and write only the allowlisted key
`corrupt_fallback` into `GITHUB_OUTPUT` (rule 3f — never whole stdout), and a
`pull_request`-only step gated on a non-empty captured value SHALL call
`make announce-image-fallback` with the captured images. The announcement step
uses the default `github.token` (the owner PAT cannot comment).

#### Scenario: The workflow announces only what the seam reported

- **Given** the qa-validate workflow source
- **When** `tests/test_workflows.py` parses the `validate` job
- **Then** the `image-ensure` and `openspec-check` steps write only
  `corrupt_fallback=` into `$GITHUB_OUTPUT`, and a gated step runs exactly
  `make announce-image-fallback` (a target the Makefile defines) with the
  default token
- **Test:** tests/test_workflows.py::test_the_corrupt_tag_fallback_is_announced_on_the_pr
