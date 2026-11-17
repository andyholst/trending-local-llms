# Tasks: multiarch-base-test-image-publishers (issue #958)

- [x] Shared manifest verdict `scripts/image_manifest_check.py` (the ONE implementation; `--tag`/`--label`/`--require`) — verified: 31 green checks in `python3 tests/test_image_manifest_check.py`, and `scripts/openspec_manifest_check.py` delegates to it with its 19 existing checks still green (`python3 tests/test_openspec_manifest_check.py`)
- [x] `make image-manifest-check TAG=<tag> LABEL=<name>` target (Makefile-only reach, .PHONY) — verified: pinned by `test_the_target_is_makefile_only_and_wired`
- [x] `build` and `test-image` jobs publish `platforms: linux/amd64,linux/arm64` with 45-minute headroom — verified: pinned by `test_both_publishers_declare_both_platforms`
- [x] UNGATED `make image-manifest-check` after BOTH the publish and skip-rebuild branches in each job (the #919 both-paths pattern) — verified: pinned by `test_both_paths_verify_base_and_test_manifests`
- [x] arm64 run-proof smoke after the manifest check in each job (`hermes --version` for the base, test-layer imports for the test image) — verified: pinned by `test_the_arm64_run_proof_steps_exist`
- [x] OpenSpec change (proposal + spec scenarios with Test: lines + this tasks file) and `make openspec-check` green — verified: `make openspec-check` green in this branch
- [x] `ARCHITECTURE.md` §4 job rows + §6 script row updated and `make architecture-refresh` regenerated, `make architecture-check` green — verified: gate green in this branch
- [x] `findings.md` written and `make findings-check` green — verified in this branch
