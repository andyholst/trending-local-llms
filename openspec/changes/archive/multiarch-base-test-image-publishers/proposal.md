# Proposal: multiarch-base-test-image-publishers

Issue: #958 — "The base and test image publishers are still amd64-only"
PR: #1114

**Capability:** `agent-image-publish`

## Why

`refresh-bot.yml` publishes the Hermes base image (`ghcr.io/…:latest` +
`:<repo>:dockerfile-<sha12>`) and the test image (`…-test`) through
`docker/build-push-action` steps that carry **no `platforms:`** — only the
`openspec-image` job declares `linux/amd64,linux/arm64` (issue #919).
`scripts/ensure_image.py published()` answers "published" on ANY host, so an
arm64 checkout pulls the amd64-only manifest and dies with
`no matching manifest for linux/arm64/v8` — measured on the arm64 host of
record 2026-11-14, which needs `DOCKER_DEFAULT_PLATFORM=linux/amd64` in the
operator's shell for every `make refresh` / `make test`. #919 fixed exactly
this for the OpenSpec CLI image and called the amd64-only publishing of the
other two images systemic; the workaround has lived in one operator's shell
ever since, not in the pipeline.

## What Changes

- The `build` (base image) and `test-image` jobs of `refresh-bot.yml` declare
  `platforms: linux/amd64,linux/arm64` on their build-push steps. The base
  Dockerfile is arch-neutral: `python:3.12-slim` is multi-arch, apt deps are
  multi-arch, and the Hermes install seam installs managed Python
  (python-build-standalone provides aarch64 builds) — the multi-arch build ITSELF
  proves the Hermes base installs on arm64 (the RUN steps execute under QEMU on
  the amd64 runner), the same proven pattern the `openspec-image` job uses.
- The manifest verdict lives in ONE tested unit,
  `scripts/image_manifest_check.py` (issue 6d one-implementation rule);
  `scripts/openspec_manifest_check.py` delegates to it so the OpenSpec tag's
  behavior stays byte-identical.
- New Makefile target `make image-manifest-check TAG=<exact tag> LABEL=<name>`
  refuses (exit 1) a published base/test tag whose manifest answers fewer than
  `linux/amd64` AND `linux/arm64`; an unreadable manifest is exit 2 (never a
  silent clean). The `build` and `test-image` jobs run it UNGATED after both
  the publish and the "already current — skip rebuild" branches — the exact
  both-paths pattern `make openspec-manifest-check` uses (issue #919) — so a
  legacy amd64-only tag for a revision is refused, not reused forever.
- The jobs also PROVE the arm64 variant runs: after the manifest check passes,
  each runs the published tag under `--platform linux/arm64` (`hermes
  --version` for the base, `import pytest` for the test image) — Done-when's
  "proven to install and run under both".
- Build-job timeouts rise (20→45, 30→45) to cover QEMU-emulated arm64 layer
  builds on the amd64 runner.

## Impact

- **Affected specs:** `agent-image-publish` (ADDED requirement).
- **Affected code:** `.github/workflows/refresh-bot.yml` (build + test-image
  jobs), `scripts/image_manifest_check.py` (new), `scripts/openspec_manifest_check.py`
  (delegates), `Makefile` (new target), `tests/test_image_manifest_check.py` (new),
  `ARCHITECTURE.md` (§4 job rows, §6 script row, generated block).
- **Not covered:** publishing a `linux/arm64`-only variant, changing
  `rebuild-decision` cadence, and the local `docker-test-build` path (it builds
  for the host arch by design). Multi-arch builds of the BASE image remain
  weekly/Sunday cadence — the extra QEMU build time lands only on rebuild days.
