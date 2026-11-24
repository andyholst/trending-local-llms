# Tasks: make-hop-reachability-both-spellings-1596

- [x] Prove the reachability hole against the real detector: a planted bare host python reached through a plain `make _setup` hop from a public target exits 0 invisible on the pre-change scanner
- [x] Widen `HOP_RE` to follow BOTH `$(MAKE) … _x` and plain `make _x` (with optional make flags, `@`-echo stripped) while keeping the container-harness suppression for both spellings
- [x] Add the two-polarity property test to `tests/test_os_agnostic_make.py` (planted RED naming target + line; harnessed twins GREEN; real-tree plain hops walked)
- [x] Reconcile the guard docstring, the `check-no-bare-host-python` target description, the Makefile mirror prose and `ARCHITECTURE.md`
- [x] Prove RED-first against the pre-change guard (9 checks fail there, rc=1) and GREEN at the head (61/0 in the module)
- [x] Bind this change to `Issue: #1596` and regenerate `OPENSPEC.md`
