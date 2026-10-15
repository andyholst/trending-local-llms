# ONE path: business logic through the Makefile, every target wired to CI, no mocks in business logic (issue #262)

**Issue:** [#262](https://github.com/andyholst/trending-local-llms/issues/262)
**Capability:** `one-path`

## Why

Rules 6c/6d/6h say "wired to a target CI runs", and §8 lists the guards, but the three properties
below are stated in pieces and can be satisfied in letter while broken in spirit. Each has already
bitten this repo: the fix-loop loss on PR #80 (an ignored path in a pathspec), the inline
`${{ github.token }}` interpolation on #241, the guard that admitted no bot on #238. All three were
green in the places that were supposed to catch them.

- A **workflow** can reach into `scripts/*.py` or call `pytest` directly: CI then executes a
  command you cannot reproduce with `make`, bypassing the target that owns the repo's decisions.
- A **target** can be added, documented in `ARCHITECTURE.md`, and called by nothing — green
  forever because it never executes. Rule 6d checks the reverse direction only (a script must be
  reachable from a target CI runs), so the loop is open on this side.
- A **test** can monkeypatch the very function it claims to lock. It passes because the stand-in
  returned the wanted answer; the real function could be deleted and the suite would stay green.

## What Changes

- **`AGENTS.md` rule 6m** — the three properties as one numbered hard rule: through the Makefile
  always; every real target called by a workflow; no test replaces the system under test. It states
  the ONE permitted exception (an **external** system may stand in — a local git remote, a local
  HTTP server or a recorded fixture the real client reads, a stub CLI on `PATH` — and the
  production code that builds the request must still run).
- **`tests/test_makefile_only.py`** (into `make _test`, rule 6d) — the enforcement: a test that
  patches/rebinds/fakes a symbol defined under `scripts/`; a workflow `run:` that reaches the
  product without `make`; a `make <target>` a workflow calls that the Makefile does not define; a
  CI gate target (`test`, `validate`, `lint`, `openspec-check`, `architecture-check`) that no
  workflow calls.
- **`AGENTS.md` §8** — the guard row.

## Impact

No product behaviour changes: the tree already satisfies all three properties, and the guard passes
22/0 on it. What changes is that they are now checked rather than assumed. The one judgement call is
the mock rule's boundary — it targets replacing the **system under test**, not standing in for an
**external** system, so the existing suite (which patches the network in `tests/test_validate_links.py`
and reads fixture GitHub metadata in `tests/test_engine_registry.py`) stays valid.

## Not covered

- Wiring `make _test`'s per-file list itself into a single target is existing behaviour, untouched.
- Whether every *local-only* convenience target should also run in CI is a separate question (some
  are host-specific and CI has no such host); this rule covers targets that do verification,
  generation or publishing work.
