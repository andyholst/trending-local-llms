# Tasks: fix-openspec-archive-newline-1782

- [x] Add `scripts/openspec_archive_newline.py` (host-side, stdlib only; appends a final newline to archived text files lacking one, leaves binary/empty/already-correct files untouched, idempotent, refuses a missing archive dir).
- [x] Wire the seam into the `openspec-archive` Makefile recipe immediately after the CLI archive call.
- [x] Add `tests/test_openspec_archive_newline.py` driving the real seam against a planted archive dir and pinning the recipe wiring; prove the wiring assertion is RED on the pre-change Makefile.
- [x] Describe the new script/target in `ARCHITECTURE.md` and regenerate the derived §10 inventory block.
- [x] Run the fast offline gates (targeted test module, `make lint`, OpenSpec index + binding + spec-test checks), tick these boxes, regenerate `OPENSPEC.md`, and push for CI verification.
