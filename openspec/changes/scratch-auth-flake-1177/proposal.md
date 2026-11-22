# Proposal: scratch-auth-flake-1177

Issue: #1177

## Why

`tests/test_refusals_land_declaration.py` runs three real suite modules in a scratch checkout.
Those subprocesses inherited a host env without GH_TOKEN/GITHUB_TOKEN, so the #972 engine
reachability probe used anonymous api.github.com; once the 60/hr quota is spent the same tree
is red on one run and green on the next.

## What Changes

- Resolve the caller's GitHub credential from the already-authenticated `gh` client at run
  time and pass it via env to both scratch subprocess helpers. Never store a value (rule 3e).
- Add a guard that both helpers use the resolved env and that no credential literal or print
  appears in the tree.

## Capabilities

### New Capabilities
- `authenticated-scratch-subprocess`: deterministic scratch-suite execution with caller auth.

### Modified Capabilities
- (none)

## Impact

Test harness only; no product data, store write, CI dispatch or access change.
