# Proposal: openspec-image-multiarch-919

Issue: #919 — "Publishing the OpenSpec CLI image stays amd64-only, so a fresh arm64
PR: #957
host still cannot pull it"

**Capability:** `openspec-image-publishing`

## Why

`refresh-bot.yml`'s `openspec-image` job builds and pushes
`ghcr.io/…-openspec:openspec-<sha12>` with no `platforms:`, so the published
manifest is amd64-only. On an arm64 machine with no local copy of the tag,
`docker manifest inspect` answers "published" and `docker pull` then dies with
`no matching manifest for linux/arm64/v8` — issue #767's original failure, still
reachable (measured on this host 2026-11-14: every `make openspec-*` call needs
`DOCKER_DEFAULT_PLATFORM=linux/am64` as a workaround, and a fresh arm64 checkout
has no local image to reuse). The first thing an implementation run does here is
`make openspec-new`, so the image shape gates every local change (issue #919).

## What Changes

- The `openspec-image` job publishes a **multi-architecture manifest**:
  `platforms: [linux/amd64, linux/arm64]` on the build-push step
  (`openspec/Dockerfile` is arch-neutral: `node:22-alpine` is multi-arch and the
  npm-installed CLI is pure JS). The Dockerfile gains a comment recording the
  multi-arch contract — its content hash changes, so the next refresh publishes
  the multi-arch tag for the revision that carries it.
- New verification gate `make openspec-manifest-check` (`scripts/openspec_manifest_check.py`):
  reads the manifest of a published tag through `docker manifest inspect` and
  REFUSES (exit 1) when it lacks `linux/arm64` (or amd64); a manifest it cannot
  read is a loud exit 2. `refresh-bot.yml` runs it after publishing AND on the
  "already current — skip rebuild" branch, so a legacy amd64-only tag never
  passes as current again.
- `tests/test_openspec_manifest_check.py` (rule 6m: the registry is the only
  stand-in — a stubbed `docker` on PATH; the real script runs) proves every
  refusal shape and pins the workflow: the publisher's `platforms:` list and the
  verify steps must stay in step with each other.

## Impact

- `.github/workflows/refresh-bot.yml` (openspec-image job), `openspec/Dockerfile`
  (comment bump → new hash tag), `scripts/openspec_manifest_check.py` (new),
  `Makefile` (target + `.PHONY`), `tests/test_openspec_manifest_check.py` (new),
  `AGENTS.md` §6f sentence (rule-3c diff declared in a comment on issue #919),
  `ARCHITECTURE.md` rows + regenerated inventory.

## Not covered

- The base/test image publishers stay amd64-only — the issue body calls that
  systemic; multi-arch for the Hermes base is a heavier change recorded in
  `findings.md` as its own follow-up, never silently dropped.
