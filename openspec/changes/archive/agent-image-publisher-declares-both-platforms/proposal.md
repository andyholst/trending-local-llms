# Proposal: agent-image-publisher-declares-both-platforms

Issue: #1724 — the privileged publisher declares both platforms on the SAME hash tag (slice 1 of the arm64 image fix)
PR: #1726

**Capability:** `agent-image-publish`

## Why

`refresh-bot.yml` already publishes the base, test and OpenSpec images for
`linux/amd64,linux/arm64`, and `ensure_image.py decide` already treats a published
single-arch tag as a rebuild reason through the ONE manifest verdict
(`scripts/image_manifest_check.py`, issue #1143). The dispatch-only privileged
publisher is the remaining hole: `scripts/ensure_image.py::publish` still calls
plain `docker build` + two `docker push`, so it can overwrite a dual-arch hash tag
and `:latest` with an amd64-only manifest. The ungated `make image-manifest-check`
step then refuses that tag and the refresh delivers nothing — measured on refresh
run 44422028712, which REFUSED `…:dockerfile-5b44520adc6c` for missing
`linux/arm64`.

## What Changes

- `scripts/ensure_image.py::publish()` replaces the single-arch build and the two
  separate pushes with ONE `docker buildx build --platform <PLATFORMS> --push`
  declaring the same three refs (`IMAGE`, hash tag, `:latest`). `--push` is the
  only way Buildx publishes a multi-platform OCI index; a plain `docker push`
  cannot push an index built this way.
- `<PLATFORMS>` is derived at call time from
  `image_manifest_check.REQUIRED_PLATFORMS` (already imported at `ensure_image.py:73`
  and used by `decide`), so the publisher cannot spell a second, drifting platform
  list (rule 6d). No `platform.machine()` / `uname` selector is added.
- The tag recipe, the no-op/force guard and the `_serves()` registry verification
  in `publish()` are unchanged. An amd64 host still receives the `linux/amd64`
  child; only the manifest's platform SET grows from one to two.
- `tests/test_ensure_image.py`'s fake-docker stub learns the additive `buildx build`
  call shape (record its `-t` refs and make them readable because `--push`
  publishes them). Its existing `build` / `push` cases are untouched, so every
  other ensure-image test keeps the same behaviour.
- `tests/test_publish_agent_image.py` moves its call-shape assertions to the Buildx
  form and adds two guards: the publish call declares both platforms from the ONE
  contract, and the publisher carries no second platform list or host-arch selector.

## Impact

- `capability: agent-image-publish` — the publisher's contract now names the platform set it must write, sourced from the single existing verdict.
- Changed: `scripts/ensure_image.py`, `tests/test_ensure_image.py`, `tests/test_publish_agent_image.py`, this change, `findings/1724.md`.
- Unchanged: `.github/workflows/publish-agent-image.yml` (Buildx is already set up), `Makefile` (already calls `ensure_image.py publish`), `refresh-bot.yml`, `image_manifest_check.py`, `decide`/`arch_flag`, tags, `data/`, README and every contract.
- No schedule, no label, no merge, no host-side architecture selector.

## Not covered

- F1 (gate wiring on the privileged publisher), F2 (host-architecture selection at the image-choice seam) and F3 (docs-only §6 row) are separate follow-up issues; none is bundled here.
