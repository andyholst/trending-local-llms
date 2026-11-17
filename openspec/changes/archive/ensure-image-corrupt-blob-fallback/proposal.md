# Proposal: ensure-image-corrupt-blob-fallback

Issue: #1118 — "ensure_image treats a published-but-undownloadable base tag as pullable"
PR: #1119
(filed by the findings chain from PR #1116's diagnosis, run 44020917206).

## Why

`scripts/ensure_image.py` knows two registry states: the tag is **served**
(`published()` answers True → `docker pull`) and the tag is **absent** (docker's own
absence wording → build locally; #235 keeps every other registry failure loud).
Measured on PR #1116's qa-validate run 44020917206, a THIRD state exists: the
registry serves the manifest but a layer blob is gone (ghcr GC / incomplete
publish):

```
docker pull ghcr.io/andyholst/trending-local-llms:dockerfile-5b44520adc6c
failed to copy: httpReadSeeker: failed open: could not fetch content descriptor
sha256:5da1ec36… (application/vnd.oci.image.layer.v1.tar+gzip) from remote: not found
```

`published()` answers True, the pull dies with `CalledProcessError`, `make
image-ensure` exits 1, and **every job behind it (`validate`, `live-smoke`) is red
with no fallback** — a PR head pinned to such a tag is unmergeable forever, and no
alarm names the cause. `ensure_base`, `ensure_test` and `ensure_openspec` all pull
through the same hole.

## What Changes

- `scripts/ensure_image.py`: pulls go through one `_pull_or_fail` seam that
  captures docker's output and tells the states apart — success, a **missing-blob
  failure** (`content descriptor` / `blob unknown` / `content blob` →
  `BlobsUnfetchable`, the caller builds THIS revision's Dockerfile — the very file
  the tag was hashed from), or any other pull failure (raised loudly, #235 rule
  unchanged: a hiccup never triggers a rebuild). `ensure_base`, `ensure_test` and
  `ensure_openspec` each gain the fallback; their verdict lines name the corrupt
  state truthfully.
- `tests/test_ensure_image.py`: the docker PATH-stub gains
  `FAKE_DOCKER_PULL_ERROR` (the external system fails the pull with real docker's
  wording) and a new test locks all three shapes for base and test images.

## Impact

- `make image-ensure` (and every CI job behind it) survives a corrupt published tag
  instead of hard-failing; the pull path for healthy tags is byte-identical.
- No Makefile target, workflow, contract or data change — the seam stays behind
  the existing `image-ensure` / `image-ensure-test` targets (rules 6d/6m).

## Not covered

- Re-publishing the broken tag (a registry-side act; issue #958's multi-arch
  publisher already republished the current revision).
- Any alarm that proactively detects blob-GC in ghcr — this change makes the
  failure survivable, not visible before it bites; a proactive check is a separate
  finding if one is ever needed.
