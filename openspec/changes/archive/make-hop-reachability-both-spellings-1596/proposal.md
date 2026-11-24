# Proposal: make-hop-reachability-both-spellings-1596

Issue: #1596
PR: #1614

## Why

`scripts/check_no_bare_host_python.py` (PR #1566, issue #1496) promises to follow a public target one make hop into a private `_x` recipe. Its matcher was

    HOP_RE = re.compile(r"\$\(MAKE\)[^\n]*?\b(_[A-Za-z0-9_-]+)")

which recognises ONLY the recursive-`make` spelling. The Makefile's live `_refresh` recipe drives its whole private chain with the PLAIN spelling (`make _setup`, `make _search`, `make _merge`, …), and that plain form is the file's dominant idiom (the fan-out `@make -j4 _search-nvidia …`, `_setup`'s skills registers). So an entire class of call sites was never walked: a bare host `python3`/`pip`/`uv` planted in a private recipe reached through a PUBLIC target's plain `make _x` hop exited 0 INVISIBLE — measured by the reviewer on merged master `c7fa437e`. This is a REACHABILITY hole, distinct from #1593's TOKEN hole (already fixed): the token set was fine, the traversal was blind.

## What Changes

- Widen `HOP_RE` to match BOTH spellings — `$(MAKE) … _x` and the plain `make _x`, including an optional run of make flags (`--no-print-directory`, `-j4`) before the target.
- Strip the recipe-echo `@` prefix before matching, so the file's `@make … _x` fan-out idiom is followed like a bare `make`.
- Keep the suppression intact: a hop line carrying a container harness (`$(DOCKER_RUN)`, `$(TEST_RUN)`, …) stays clean for BOTH spellings, because that hop already runs inside the image.
- Lock both polarities in `tests/test_os_agnostic_make.py`: a planted bare interpreter behind a plain `make _setup` hop from a public target goes RED naming target + line, and the harnessed twins stay GREEN. Prove RED-first against the pre-change guard.
- Reconcile the guard docstring, the `check-no-bare-host-python` target description, the Makefile mirror prose, `ARCHITECTURE.md` and the OpenSpec index.

## Impact

One additive widening of a guard's reachability, inside a guard already green on the real tree. No new exception is granted, no existing detection is removed, and no schema, contract, API, table or data-shape changes. `make lint` / `make check-no-bare-host-python` stay green at the head.

## Not covered

- #1593's token hole (already landed). The bare `piptools` module spelling is not added. No new host-only exception.
