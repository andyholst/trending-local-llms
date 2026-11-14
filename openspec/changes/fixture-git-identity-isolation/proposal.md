# Proposal: fixture-git-identity-isolation

Issue: #943 — "test_worktree_base.py's identity-fallback assertion reads the
host's global git config" (tech-debt, filed from the 2026-11-14 host-suite sweep).

## Why

`tests/test_worktree_base.py` commits only through `-c user.*` overrides, so its
fixture clones store NO identity — but `scripts/worktree_base.py::_identity_args`
asks `git config user.email`, which resolves **the machine running the suite's
global git config**. On any developer host that is non-empty, so the assertion
"it falls back to the repo's bot identity when the checkout has none" (the only
identity lock in the file) goes red locally (`PASSED 122 | FAILED 1`, measured
2026-11-14 on `origin/master`) while the container (no global config) stays
green. The behavior it claims to lock — the documented `identity=fallback`
committer for a bare checkout, and the never-override rule for a configured one
(`scripts/worktree_base.py:67-79`) — is therefore pinned on NEITHER machine:
on the host it fails for the wrong reason; in CI only half of it is tested.
`tests/test_commit_authorship.py:193-210` already establishes the isolation
pattern (`GIT_CONFIG_GLOBAL`).

## What Changes

- `tests/test_worktree_base.py::run_script` isolates git config for every
  scripted call by DEFAULT: `GIT_CONFIG_GLOBAL=/dev/null` +
  `GIT_CONFIG_SYSTEM=/dev/null` in the child env (a caller's explicit `env=`
  entry still overrides). The scripted git then sees ONLY the fixture's own
  repo config on every machine.
- `tests/test_worktree_base.py` gains `test_rebase_respects_a_configured_checkout_identity`:
  a fixture repo with its OWN `git config user.email` must NOT receive the
  fallback (`identity=fallback` absent, the rebased commit's committer is the
  repo's identity) — pinning `_identity_args`' never-override half locally too.

## Impact

- `tests/test_worktree_base.py` only. No product code, no Makefile, no workflow,
  no data (rule 6h/6m inventory unchanged).
- `make test` is host-independent for this file: green on a host WITH a global
  git identity and in the container, same 124 assertions.

## Not covered

- The script's identity semantics themselves (correct as documented; §3f wires
  `make git-identity` in workflows) — unchanged.
- Other suites' host-vs-container false reds (the known skip-list: `test_fix_loop`,
  `test_agent_shell_keys`, `test_openspec_archive_check`, `test_hermes_update_needed`)
  — out of scope; this change fixes only the git-config leak.
