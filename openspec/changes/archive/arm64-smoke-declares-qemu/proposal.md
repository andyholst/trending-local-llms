# Proposal: arm64-smoke-declares-qemu

Issue: #1739
PR: #1742

## Why

The multi-arch publisher fix (#1724) made the base image answer both
`linux/amd64` and `linux/arm64`, and the designer scanned all 581 executable
AArch64 ELFs in the published arm64 layer — zero x86-64. The layer is sound.
The `build` job of `refresh-bot.yml` still fails its arm64 QEMU smoke with
`exec /root/.local/bin/hermes: exec format error` (exit 255) because the smoke
runs `docker run --platform linux/arm64` on an **amd64** runner with no
`docker/setup-qemu-action` anywhere in `.github/workflows/`: no binfmt_misc
handler is registered for the host-side run. The comment claiming the build
itself established QEMU is false. This change declares the missing runner
prerequisite.

## What Changes

- Add ONE `docker/setup-qemu-action` step to the `build` job of
  `.github/workflows/refresh-bot.yml`, immediately before the "Prove the arm64
  base runs, not just exists (QEMU smoke)" step.
- Pin that step to the immutable 40-hex commit
  `99012661954931238ded8c8b007157a8430204e1` (the repo action-pin rule).
- Give it exactly `platforms: linux/arm64` — emulation registration only. No
  second publish-platform list, no `uname`/`platform.machine()` selector, no
  publisher or installer change.
- Replace the misleading comment at the smoke with the true prerequisite.
- Add RED-first workflow-shape guards and this change's findings record.

## Impact

Additive and CI-harness only. The published image, its manifest, the publisher
(`scripts/ensure_image.py::publish`) and the installer
(`scripts/install_hermes_ci.sh`) are untouched. `image_manifest_check.REQUIRED_PLATFORMS`
remains the one platform set. No data, README, schema or table churn.

## Not covered

- No new GitHub Actions `schedule:`, no Hermes cron, no queue label, no merge
  and no push to `master`.
- No rebuild of the arm64 image — it is already correct.
