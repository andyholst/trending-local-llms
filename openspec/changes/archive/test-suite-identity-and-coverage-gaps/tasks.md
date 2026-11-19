# Tasks

- [x] 1. The tracked change exists (this directory, `make openspec-new`) before any code or test edit
- [x] 2. `scripts/coverage_gap.py` (new) defines ONCE: `IDENTITY_PREFIX`/`identity_line()`,
      `GAP_PREFIX`/`declare_gap`/`declare_bypass_gap`, `BYPASS_PHRASE`,
      `scan_module_output`, and the `--gap-prefix | --phrase | --identity-line` CLI the
      shell reads (rule 6d)
- [x] 3. `scripts/run_tests.sh` reads all three strings from the seam (unreadable seam →
      exit 2 naming it), prints the identity line before any verdict, and scans EVERY
      module's output — passing modules included — so declared gaps reach the verdict and
      an undeclared bypass phrase fails the run naming the module and the fix
- [x] 4. `scripts/docker_test_run.sh` prints the invoking `uid:gid` and forwards it as
      `TLL_INVOKING_UID` (NAME only, never a value — rule 3e) without inventing `--user`
- [x] 5. `Makefile`'s `test:` recipe refuses a capture with no `[harness] suite identity:`
      line (alongside the issue #911 empty-capture guard) and counts the declared
      coverage-gap reports it captured
- [x] 6. `tests/test_agent_skills.py`'s permission half declares its gap through the seam
      instead of printing a bare `SKIP`, and still states the always-checked half that
      keeps the teardown contract locked (issue #1145)
- [x] 7. `tests/test_test_container_identity.py` (new, auto-discovered) proves all of it by
      running the REAL runner, the REAL wrapper against a stub `docker` on PATH, and the
      REAL `test:` recipe through `make -f` — external stand-ins only (rule 6m) —
      including the pre-change reds: identity absent from a verdict-bearing capture → red;
      bare `SKIP` bypass → red; declared gap → green AND named
- [x] 8. `tests/test_test_capture_guard.py` extended: the `test:` recipe now carries the
      identity-line guard and the coverage-gap count
- [x] 9. Docs in the same change (rules 6h/6c): `ARCHITECTURE.md` §6 row for
      `scripts/coverage_gap.py` + extended `run_tests.sh`/`docker_test_run.sh` rows +
      `make architecture-refresh`; `AGENTS.md` §8 only (new guard row, updated #1145 row)
- [x] 10. Gates green on the exact head: `make lint`, the full `make test`,
      `make openspec-check`, `make openspec-index`
