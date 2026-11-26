# Proposal: test-image-qemu-handler

Issue: #1747 (test-image root cause; the aggregate token and search-leg SIGPIPE are separate)
PR: pending

## Why

Run `45657191852` test-image job `139359390667` pulled the published arm64 test image and then died with `exec /usr/local/bin/python3: exec format error` (exit 255) at `make test-image-smoke`. #1739 registered a QEMU handler in the `build` job only; the `test-image` job's host-side `docker run --platform linux/arm64` has no binfmt_misc handler on its own runner. The buildkit `ingest ref is locked` lines in the same log were transient and non-fatal.

## What Changes

- Add the same pinned `docker/setup-qemu-action@99012661954931238ded8c8b007157a8430204e1` step with `platforms: linux/arm64` immediately before the test-image arm64 smoke in `refresh-bot.yml`.
- Add `tests/test_workflows.py::test_test_image_arm64_smoke_declares_qemu_handler` (wired into `main()`): RED on the old job shape (no handler before the smoke), GREEN on this head, with the pin and single platform asserted.
- Append the test-image finding to `findings/1747.md`, with the protected §8 row declared owed to the owner (rule 3c). OpenSpec change with capability spec and all tasks ticked.

## Impact

- Capability: `agent-image-publish` (the published arm64 test image is runnable in the test-image job, not just present in the manifest).
- Additive: one workflow step and one wiring test; no Makefile, script, data or rulebook byte changes.
- Scoped: the search-leg SIGPIPE classification and the aggregate GH_TOKEN are separate PRs; #1747 stays open until all shapes have landed and a fresh weekly run is green.
