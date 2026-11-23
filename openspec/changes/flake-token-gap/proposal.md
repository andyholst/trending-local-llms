# Proposal: flake-token-gap

Issue: #1371

## Why

`tests/test_refusals_land_declaration.py` is red on every `make test` this host and CI ran
today (`153`/`154`/`155`/`157` passed, 1 failed) while the branch's own diff touched nothing
near it. The runner's FAIL block names the check, and it is NOT the one issue #1177's body
describes:

```
FAIL #1177: the env contains a token name, never a literal in the tree
```

That check asserts `"GH_TOKEN" in env or "GITHUB_TOKEN" in env` where `env = _test_env()`, and
`_test_env()` resolves a token from the already-authenticated `gh` client at run time, falling
back to nothing. So the assertion is "this identity can produce a GitHub token" — an
environmental property, not a property of the tree. The module's actual contract (#1155: only
a declared landing writes `data/refusals.json`) is fully host-verifiable.

A red suite that no change caused trains every reader to ignore red, which is exactly the noise
rule 6c's host/container split and the `coverage_gap` seam exist to remove.

## What Changes

- The token-PRESENCE half stops being an assertion and becomes a **declared coverage gap**:
  `announce(declare_gap(...))` when no token resolves, green and named, with the reason.
- The tree-owned halves stay hard: the credential travels BY NAME (`env=_test_env()`, never
  printed, never written), and `#1155`'s landing rule is unchanged.
- `test_the_measured_suite_modules_leave_the_tree_clean`: the three siblings' pass/fail half is
  hard ONLY when the identity can authenticate their #972 GitHub probe; otherwise it is
  announced as a declared gap naming the sibling, and the tree-clean half stays hard (issue
  #1372, the same root in its second half).

## Impact

One test module. No product code, workflow, target, data or contract change. The suite stops
going red on an identity without a resolvable GitHub token, and a sibling's real regression is
still red whenever the probe can authenticate (CI).

## Not covered

- The #972 probe's own unauthenticated fallback (`scripts/engine_registry.py`) — a registered
  engine's repo being re-probed is the sibling's contract, recorded as #1372's second half.
