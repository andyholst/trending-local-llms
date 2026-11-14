# The OpenSpec CLI image seam reuses its exact tag when it is already here

**Issue:** #767
**Capability:** `openspec-image-seam` (the one entry point that prepares the OpenSpec CLI image every `make openspec-*` target runs in)
PR: #920

## Why

`scripts/ensure_image.py::ensure_openspec` consults the registry BEFORE looking at the machine:
`published(openspec_tag())` → `docker pull`. The published tag
`ghcr.io/andyholst/trending-local-llms-openspec:openspec-<sha12>` is built by
`refresh-bot.yml`'s `openspec-image` job on amd64 runners with no `platforms:` input, so it is an
**amd64-only** manifest list. On an arm64 host `docker pull` dies with
`no matching manifest for linux/arm64/v8`, and `_run(check=True)` turns it into a
`CalledProcessError` that fails every `make openspec-*` target.

Re-measured **2026-11-14 on the same arm64 host** the issue was filed from, with the current
`master` code and no environment override:

```
$ make openspec-image
  $ docker pull ghcr.io/andyholst/trending-local-llms-openspec:openspec-084926422515
subprocess.CalledProcessError: Command '['docker', 'pull', …]' returned non-zero exit status 1.
make: *** [openspec-image] Error 1
```

— while `docker image inspect` answers **the same exact tag locally** (an amd64 image pulled in the
platform-hack era, 299 MB). The seam re-pulls a tag it already has, and the pull cannot be
satisfied on this architecture. Today the only local workarounds are the `DOCKER_DEFAULT_PLATFORM=
linux/amd64` hack (qemu emulation) or the `IMAGE_REPO=<absent-repo>` override (forcing the
not-published → build branch) — and `tests/test_architecture.py` **forbids** those hacks on the CI
side, so the seam is green where it is never broken and broken where it is never checked.

`ensure_python` (added by #766) already proves the pattern this issue asks for: `python_env_ready()`
is a `docker image inspect` shortcut — present locally → reuse, no registry call at all.
`ensure_openspec` has no such check.

## What Changes

- `ensure_openspec` decides in this order:
  1. `openspec_ready()` — `docker image inspect <openspec_tag()>` succeeds → `docker tag` the exact
     tag onto `OPENSPEC_IMAGE`, **zero registry calls** (no pull, no manifest inspect). The tag
     name carries this revision's Dockerfile+`openspec/` hash, so a local copy of it matches the
     inputs byte-for-byte — the same reasoning `python_env_ready()` uses.
  2. not local → `published(openspec_tag())` → pull + tag, **byte-identical to today** (a fresh
     amd64 CI runner takes exactly this path; CI is unchanged).
  3. not published → build, now tagging **both** `OPENSPEC_IMAGE` and the exact hash tag —
     mirroring how `refresh-bot.yml`'s build-push-action tags both — so the *next* run on that host
     hits the local shortcut and never probes the registry.
- The module docstring states the reuse rule and keeps the #235 loud-registry rule intact: a
  genuine registry failure is still an error, never "absent".

## Impact

- `scripts/ensure_image.py`: `openspec_ready()` + `ensure_openspec` decision order + dual-tag build.
- `tests/test_ensure_image.py`: new guard `test_ensure_openspec_present_locally_is_reused_without_a_pull`
  (RED on the old code: the old seam probes the registry and pulls); the existing
  `test_openspec_image_is_hash_tagged_and_pulled_or_built` updated for the dual-tag build.
- `ARCHITECTURE.md` §6 row for `scripts/ensure_image.py`; `AGENTS.md` §8 guard row (rule 6c).
- No Makefile target, workflow job or CI behaviour changes: `ensure-openspec` is already wired
  (`openspec-image` ← `openspec-new`/`openspec-validate`/… ← qa-validate's `openspec-check`), so
  rule 6m is satisfied with no new target.

## Not covered

- Issue #767's option (1): publishing the tag multi-arch (`docker/build-push-action`
  `platforms: [linux/amd64, linux/arm64]` in `refresh-bot.yml`'s `openspec-image` job). A **fresh**
  arm64 host with no local copy still hits the amd64-only pull. Recorded as this change's finding
  and filed as its own `tech-debt` issue (rule 6g).
- The base/test images' pull-first rules — same class, separate issues.
