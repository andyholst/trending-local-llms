# Tasks: os-agnostic-make-cross-cutting-seams

- [x] Create the OpenSpec change (`openspec/changes/os-agnostic-make-cross-cutting-seams/`) before any code edit
- [x] Route the `scrubbed_run` redactor through the ONE `$(PYTHON_RUN)` seam at the redactor end of the pipeline, leaving the capture contract and the command's exit status unchanged
- [x] Route the five parse-time `$(shell python3 …)` query execs through `$(PYTHON_RUN)`, keeping them recursive so the seam still starts only when a leg prompt reads the list
- [x] Route `_search-preflight`'s `require_env.py` credential check through `$(PYTHON_RUN)` and forward the `FIRECRAWL_API_KEY` name through the seam, so `make search-*` starts no host interpreter before the agent container
- [x] Add `scripts/check_no_bare_host_python.py`: fail on a PUBLIC target outside the documented exceptions reaching a bare host `python3`/`pip`/`uv` via a recipe line, a `$(call …)` macro body, a `$(shell …)` exec, or one bare `$(MAKE) _x` hop
- [x] Name the pip-tools console scripts as their OWN tokens (#1593): `INTERP_RE` matches `pip-compile`, `pip-sync`, `pip-tools` before the shorter `pip`, so a planted bare `pip-compile`/`pip-tools` in a NON-exception public target is reported naming target + line while the private `_requirements`/`_generate-requirements` recipes stay green through their `$(DOCKER_RUN) make _x` hop
- [x] Prove the scanner RED against the pre-change tree (`git show origin/master:Makefile`): the 5 parse-time execs and all 9 `scrubbed_run` targets reported (exit 1), and GREEN at this head (exit 0)
- [x] Add `tests/test_os_agnostic_make.py` exercising the REAL detector on the REAL Makefile (29 checks): green tree + CLI, exception-list agreement, both seams containerised, and the RED-on-pre-change-shapes lock
- [x] Make the host-only exception list mechanical: `EXCEPTIONS` in the scanner mirrored between the Makefile's `HOST-EXCEPTIONS-BEGIN/END` markers, with a test proving the two agree and that every name is a real public target
- [x] Wire the guard into `make lint` behind the public `check-no-bare-host-python` target
- [x] Reconcile the host-seam docs: `ARCHITECTURE.md` target row + script row + regenerated §10 inventory; the `README.md` contribute bullet (template + generated file kept byte-equal)
- [x] Run the fast offline gates green at the exact head: `make lint`, `make architecture-check`, the targeted module `python3 tests/test_os_agnostic_make.py`
- [x] Regenerate `OPENSPEC.md` with the active change bound to #1496
