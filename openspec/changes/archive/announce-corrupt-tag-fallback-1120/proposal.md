# Proposal: announce-corrupt-tag-fallback-1120

**Issue:** [#1120](https://github.com/andyholst/trending-local-llms/issues/1120)
PR: #1134
**Capability:** `image-fallback-announcement`

## Why

The corrupt-tag fallback (issue #1118: a published hash tag whose manifest
answers but whose blobs ghcr has GC'd — `ensure_base` / `ensure_test` /
`ensure_openspec` then build the image locally) is invisible on the PR that
needed it. The verdict lives only in a log line of one job; a reviewer of a
green PR cannot tell whether CI pulled the published, content-hashed artifact
or silently rebuilt it from the branch's own Dockerfile. After #1118 both
states print green — the supply-chain distinction needs a machine-readable
report and a PR announcement (#1120).

## What Changes

- `scripts/ensure_image.py` gains a machine-readable report line
  `corrupt-tag-fallback=<image>=<tag>` printed by each corrupt-tag fallback path
  (base / test / openspec) alongside the existing prose verdict; the normal
  pull, not-published and local-reuse paths print no such line.
- `scripts/bot_markers.py` registers the marker `corrupt-tag-fallback`
  (REGISTRY + WRITTEN + ARTIFACTS, kind `image_fallback` under `qa-validate`);
  AGENTS.md §6j names it in the same change (rule 6j).
- New `scripts/announce_image_fallback.py` + `make announce-image-fallback`:
  composes ONE comment naming which images were built without a pull (tag,
  reason, run URL) carrying the registered marker stamped `run=<run-id>`,
  reads the PR's comments with `--paginate` and skips when that run already
  announced (dedup), posts via `gh issue comment` with the default
  `github.token` (the owner PAT cannot comment, rule 6e).
- `qa-validate.yml` `validate` job: the `image-ensure` step captures the seam's
  output and writes only the allowlisted key `corrupt_fallback` into
  `GITHUB_OUTPUT` (rule 3f); the `openspec-check` step does the same; a new
  `pull_request`-only step calls `make announce-image-fallback` when either
  captured a fallback. The `validate` job's `issues: read` becomes
  `issues: write` for that one comment.

## Impact

- `scripts/ensure_image.py` — three fallback branches print the machine line.
- `scripts/bot_markers.py` — one new registered marker; AGENTS.md §6j row.
- `scripts/announce_image_fallback.py` (new), `make announce-image-fallback`
  (new target), `qa-validate.yml` (capture steps + a `collect-fallback` job
  output + the new `announce-fallback` job that owns `issues: write`).
- `tests/test_ensure_image.py` extended; `tests/test_image_fallback_announce.py`
  new (PATH-stubbed `gh`, rule 6m); `tests/test_workflows.py` qa-validate pins
  updated; AGENTS.md §8 guard row.

## Not covered

- Announcing on non-qa-validate pipelines (issue-bot/refresh-bot legs keep the
  log-line state unchanged; only the PR-consuming pipeline announces). The
  `live-smoke` job's own `image-ensure` is not announced either: `validate` is
  the job whose images the merge gate depends on, and its announcement names
  the revision the PR was tested against.
- Auto-merge behaviour: an announced fallback does not hold the merge — #1118
  made the fallback a deliberate green path; this change only makes it visible.
