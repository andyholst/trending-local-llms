# Proposal: cua-driver-x11-runtime-libs

Issue: #1727
PR: #1729

## Why

The CI/local container bakes the Hermes CLI through the one `install_hermes_ci.sh` seam. The external installer stages the channel's default tool `cua-driver` and verifies it with a real `cua-driver --version` dynamic-load smoke test. On the current image that check fails (exit 127, `libX11.so.6` not found, with `libXi.so.6` and `libxkbcommon.so.0` also missing), so the image ships a default tool that cannot run. The failure on refresh run 45585404150 was a non-fatal warning — the fatal pin cause was already fixed in #1723 — but a staged binary that cannot execute is still a real defect. Declaring the three arch-neutral Debian packages in the image's single apt layer fixes the cause without weakening the check.

## What Changes

- Append exactly `libx11-6 libxi6 libxkbcommon0` to the existing system apt `RUN` in `Dockerfile:19-23`, before the seam RUN at `:55-56`. No new apt layer, no reorder, no upgrade.
- Add one additive Dockerfile-shape test in `tests/test_install_hermes_ci.py` that pins those three declarations before the seam and refuses any verification opt-out, and wire it into `main()`.
- Add this tracked change, `findings/1727.md` and a regenerated `OPENSPEC.md`.

## Impact

The image carries the runtime libraries the staged binary links, so the default tool's `--version` entry check runs as a real check on both amd64 and arm64: the RED probe (libs "not found", rc 127) becomes GREEN (`cua-driver 0.52.0`, rc 0). The seam, its pin contract, the tags, the data shape and every CI dispatch stay byte-identical. No consumer contract changes.

## Not covered

- No headless-tolerant verification, no skip, no `|| true`, no opt-out flag and no fork of the external Hermes installer.
- No change to `scripts/install_hermes_ci.sh`, the Makefile, any workflow, the image manifest, the publisher (#1724) or the pin (#1723).
- No data, README, schema, table, ranking, label, schedule or rulebook churn, and no merge or master push.
