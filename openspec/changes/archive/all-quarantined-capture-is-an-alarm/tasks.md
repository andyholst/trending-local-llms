# Tasks

- [x] 1. The tracked change exists (this directory) before any code edit
- [x] 2. `scripts/self_correct_raw.py::main()` counts the surviving model rows per readable
      snapshot (read back from the corrected file) and sums them across the capture
- [x] 3. When the capture read ≥1 snapshot but 0 rows survive, it prints a distinct
      `CAPTURE UNUSABLE:` line and returns 1; a capture that kept ≥1 row keeps its existing
      code path and exit code
- [x] 4. The module docstring's exit-code contract names the third non-zero state
- [x] 5. `tests/test_raw_quarantine.py` gains a real-command test over an all-bad snapshot:
      non-zero exit, the `CAPTURE UNUSABLE` line, every `QUARANTINED:` row reported, no model
      left; the existing partial-quarantine tests still assert exit 0
- [x] 6. `OPENSPEC.md` regenerated (`scripts/openspec_index.py --write` run directly in this
      docker-less agent container, the same python-equivalent seam the prior change used) and
      `scripts/openspec_index.py --check` green
- [x] 7. `tests/test_raw_quarantine.py` (61 checks, 0 failed) and `scripts/self_correct_raw.py`
      verified against the real command in a temp `TRENDING_DATA_DIR`; the full
      `make test` / `make validate` surface needs the docker/test image (absent here) — the
      change touches no target, stage, workflow or image, so `ARCHITECTURE.md` is unchanged
      (rule 6h)
