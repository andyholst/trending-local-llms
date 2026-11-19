# Proposal: agent-image-decision-asks-architectures

Issue: #1143 — "refresh-bot's publisher reuses the legacy amd64-only agent image tag, so `image-manifest-check` reds the build job and the refresh delivers nothing"
PR: #1144

**Capability:** `agent-image-publish`

## Why

`scripts/ensure_image.py decide` decides whether the Hermes agent image is REBUILT
and re-published, and it asks exactly one registry question per tag: `published()` —
"does `docker manifest inspect` answer at all". It never asks **which architectures**
that manifest answers. `scripts/image_manifest_check.py` (the ONE manifest verdict,
issue #958) DOES ask — but only as a verify step that runs AFTER the decision.

The two questions disagree in production right now. The published base tag for this
revision, `dockerfile-5b44520adc6c`, and `:latest` answer `linux/amd64` + an
`unknown/unknown` attestation child only (measured 2026-11-19 against the registry:
no `linux/arm64` child; the published test tag is the same, while the OpenSpec image
is genuinely dual-arch). `decide` therefore reports `built=no reason=current`, the
build job prints "reusing it", and the UNGATED `make image-manifest-check` refuses the
tag: refresh-bot `build` failed on both 2026-11-18 deliveries (runs 44330910573,
44422028712), `test-image`, `search` and `aggregate` were skipped, and the trend
gather has delivered nothing since 2026-11-11. The tag predates the multi-arch
publisher (`99bd2286`) and `Dockerfile`/`Dockerfile.test` have not changed since
`ea4bcf51`, so the reuse path can never repair it — the pipeline is permanently red
until a human dispatches the privileged publisher.

## What Changes

- `scripts/ensure_image.py` gains a **reuse verdict that asks the architecture
  question**, through the ONE existing implementation: it imports
  `scripts/image_manifest_check.py` (`check`, `REQUIRED_PLATFORMS`) instead of
  spelling a second platform list (rule 6d).
- `decide(force, dow)` treats a tag that is published but answers fewer platforms than
  required as **not reusable**: new rebuild reasons `base-tag-single-arch`,
  `test-tag-single-arch`, `openspec-tag-single-arch`, plus data keys
  `base_arch` / `test_arch` / `openspec_arch` (`ok`, `single-arch`, or the missing
  platforms) so the decision stays readable as data.
- A manifest the verdict **cannot read** (exit 2: no document, registry failure) is a
  loud `RegistryUnknown` from `decide`, never a rebuild reason — the #235 rule ("a
  registry hiccup is not absence") stays intact for the architecture question too.
- No workflow, Makefile or publisher step changes shape: when `decide` says
  `built=yes`, refresh-bot's existing dual-arch `build-push` step publishes the SAME
  hash tag over the legacy single-arch one, and the existing manifest + arm64 run-proof
  steps go green. The repair therefore needs no privileged dispatch.

## Impact

- `capability: agent-image-publish` — the reuse decision now requires the platforms the
  publisher already promises.
- `scripts/ensure_image.py` (`decide`, the new reuse probe), `tests/test_ensure_image.py`
  (the docker stub now answers `manifest inspect` with a real manifest-list document;
  platforms per ref are seedable).
- `refresh-bot.yml` `build` / `test-image` jobs: behavior changes (they rebuild),
  content unchanged.
- Host effect: once the tags are dual-arch, this arm64 machine stops needing
  `DOCKER_DEFAULT_PLATFORM=linux/amd64` and stops running the toolchain under QEMU.

## Not covered

- The `make publish-agent-image` path (`ensure_image.publish()`) still builds and pushes
  a SINGLE-architecture image with plain `docker build`/`docker push`. Run by the
  dispatch-only `publish-agent-image.yml`, it can overwrite a dual-arch tag with a
  single-arch manifest. That is a separate change (filed as a finding by this one, rule 6g).
- The `ensure_*` pull paths (a host pulling a single-arch tag for its own architecture)
  are not re-plumbed here; they get their verdict from the same probe only after the
  publisher is fixed.
- No data, README, ranking or contract file is touched.
