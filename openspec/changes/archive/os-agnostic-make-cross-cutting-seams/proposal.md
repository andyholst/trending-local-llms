# Proposal: os-agnostic-make-cross-cutting-seams

Issue: #1496
PR: #1566

## Why

`#712` (OS-agnostic make) had two cross-cutting seams a target-by-target scan cannot see, both still running the HOST interpreter (architect's design comment on #712, 2026-11-23T12:04:48Z):

1. the `scrubbed_run` macro (`Makefile:213`) — every agent leg pipes its stream through host `bash -o pipefail` + host `python3 scripts/scrub_log.py`, reached by nine public targets (`search-nvidia/metal/cpu/amd`, `search`, `fix`, `implement-issue`, `review-issue`, `review-issue-window`);
2. the parse-time `$(shell python3 …)` execs (`query_coverage.py --queries`, `query_vocab.py --print {nvidia,metal,cpu,amd}`), which run at Makefile PARSE time on the host before any container starts.

Neither is a single target that could be routed; both are reached from many. A host with Docker but not the pinned Python/deps therefore still leaks the OS/toolchain into the pipeline, and nothing mechanical stopped a NEW bare host invocation from being added.

## What Changes

- Route the redaction filter through the ONE `$(PYTHON_RUN)` python-env seam: `scrubbed_run` becomes `cmd | $(PYTHON_RUN) python3 scripts/scrub_log.py …`. The harness is injected at the REDACTOR end of the pipeline, never around the command being scrubbed — those agent legs are already `$(DOCKER_RUN)`/`$(TEST_RUN)` containers, so wrapping them again would be docker-in-docker. The capture contract is unchanged (raw + redacted files, `--append` per round, streamed masked lines, the command's own status under `pipefail`).
- Route the five parse-time query execs through the same seam (`$(shell $(PYTHON_RUN) python3 …)`); they stay recursive (`=`), so the seam still starts only when a leg prompt actually reads the list.
- Route `_search-preflight`'s credential check (`require_env.py`) through the seam too, with `PYTHON_RUN` forwarding the one name it proves (`FIRECRAWL_API_KEY`), so `make search-*` starts no host interpreter before the agent container.
- Add `scripts/check_no_bare_host_python.py` (+ `tests/test_os_agnostic_make.py`): reads the REAL Makefile and fails when a PUBLIC target outside the documented host-only exceptions reaches a bare host `python3`/`pip`/`uv` through a recipe line, a `$(call …)` macro body, a `$(shell …)` exec, or one bare `$(MAKE) _x` hop. Proven RED against the pre-change tree (the two seams above).
- Make the host-only exception list MECHANICAL: the ONE list is `EXCEPTIONS` in the scanner (image build/selection, gh/GitHub-state bound, host git identity/worktree, the cheapest pre-image-ensure guards, host orchestration/local probes), mirrored between the Makefile's `HOST-EXCEPTIONS-BEGIN/END` markers, with the test proving the two agree. Reconcile the host-seam docs in `ARCHITECTURE.md` and `README.md`.
- Wire the guard into `make lint` behind a new `check-no-bare-host-python` target; regenerate `ARCHITECTURE.md`'s §10 inventory.

## Impact

Non-breaking: no schema, contract, API, table or data-shape change, and no behaviour change for any other `$(PYTHON_RUN)` caller. The redaction contract, log paths and exit-status propagation are byte-for-byte the same; the parse-time lists derive from the same scripts. A Docker-only runner now runs the redactor, the query derivation and the search credential pre-flight inside the python-env image. The exception list documents the ~100 targets that deliberately stay host-side (they need `gh`/host git/host docker/local network), and the guard makes that list enforceable instead of prose.

## Not covered

- Migrating any of the ~100 documented host-only exception targets (each needs `gh`, the host `.git`, the host docker CLI or localhost access) — they stay host-side and are now mechanically pinned as such.
- The 17 image build/selection targets, the ~31 gh-bound targets, the 9 host-git targets and the 7 cheap pre-image guards beyond documenting them.
- Publishing the python-env image to a registry (Slice 1's local-build contract is unchanged).
