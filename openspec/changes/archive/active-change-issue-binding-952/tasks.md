# Tasks: active-change-issue-binding-952

- [x] 1. `scripts/openspec_binding_check.py` — the ONE verdict (active scan via the
      shared `openspec_index._refs` parser, `Binding-exempt:` declaration, exit 1/0/2,
      `--changes-dir` fixture seam)
- [x] 2. `Makefile`: `.PHONY` entry, the `openspec-binding-check` target
      (`$(PYTHON_RUN) python3 scripts/openspec_binding_check.py`), and it added as a
      prerequisite of `make openspec-check`
- [x] 3. `tests/test_openspec_binding.py` — planted shapes (unbound red; both Issue
      spellings green; Issue line without `#<n>` red; declared exemption green AND
      reported; prose-not-exemption red; archive out of scope; missing proposal red;
      unreadable tree exit 2), the REAL tree green, and the REAL Makefile/qa-validate
      wiring — 25/25 green
- [x] 4. `AGENTS.md` §6f sentence + §8 guard row (rule-3c diff declared on issue #952)
- [x] 5. `ARCHITECTURE.md` §6 target/script rows + `make architecture-refresh`
      regenerated inventory block; `make lint` green
- [x] 6. `.hermes/skills/issue-implement`: the change's `Issue:` binding is written at
      creation so the record step can never refuse for its absence
- [x] 7. Full local gates: `make openspec-check`, `make lint`, `make secret-scan`,
      `make openspec-index`
