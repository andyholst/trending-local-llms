# Tasks: agent-image-decision-asks-architectures

- [x] `scripts/image_manifest_check.py::arch_verdict` — the data-shaped view of the ONE
      manifest reader (`ok` / `single-arch` + the missing platforms / `undecidable`),
      sharing `_read_manifest` and `_platforms` with `check` and reusing the published
      `REQUIRED_PLATFORMS`.
- [x] `scripts/ensure_image.py` reads that verdict and the shared `REQUIRED_PLATFORMS`
      (no second platform vocabulary) and raises `RegistryUnknown` when the manifest
      cannot be read — #235's rule applied to the architecture question too.
- [x] `decide()` gains the prong: a published ref answering fewer architectures than the
      publish gate demands is a rebuild reason (`latest-tag-single-arch`,
      `base-tag-single-arch`, `test-tag-single-arch`, `openspec-tag-single-arch`), reported
      as data (`latest_arch`, `base_arch`, `test_arch`, `openspec_arch`). Skipped when the
      rebuild is already owed (`--force true` / Sunday) — the question decides REUSE only.
- [x] `tests/test_ensure_image.py` seeds the architectures a published tag answers
      (`FAKE_DOCKER_ARCHES`; the stub prints a real manifest-list document, ghcr's
      `unknown/unknown` attestation child included) and pins all four scenarios:
      single-arch base rebuilt, multi-arch reused, single-arch openspec republished,
      one-reader seam. `PASSED 139 | FAILED 0`.
- [x] Rule 6c proof: the same test file run against `git show origin/master:scripts/ensure_image.py`
      is RED (`PASSED 131 | FAILED 8`), green against the new seam.
- [x] `make lint` green (linefeeds, workflow guards, agent-model chain).
- [x] `make test` green end to end in this branch's tree.
- [x] `make openspec-check` green (proposal + spec + tasks; the index rows this change).
- [x] `make secret-scan` + `make secret-scan-self-test` green.
- [x] PR opened with the five-section body and `closes #1143` (auto-merge then gates
      `validate` + `live-smoke` green on the head commit) — rule 6e monitors that pipeline
      from this run.
