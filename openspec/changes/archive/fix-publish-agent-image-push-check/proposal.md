# Proposal: fix-publish-agent-image-push-check

Issue: #229

## Why

The `publish-agent-image` pipeline (added in #206, merged in #226) fails on every
real dispatch, before the build. The `publish` job's `Prove this credential can
push` step runs `make agent-image-push-check`, and
`scripts/ensure_image.py push_check()` reads the credential **from the
environment** (`os.environ.get("GITHUB_TOKEN")` / `GH_TOKEN`) — but the workflow's
probe step sets **no env**, relying on the earlier `docker login` step, which the
script does not read. Measured on runs
[38679326521](https://github.com/andyholst/trending-local-llms/actions/runs/38679326521)
and
[38679514541](https://github.com/andyholst/trending-local-llms/actions/runs/38679514541):

```
[push-check] FAIL: no credential in the environment (GITHUB_TOKEN or GH_TOKEN).
  The image build was NOT started.
```

The probe was right to fail (fast, naming the credential, saying the build was
not started); the workflow simply never handed it the token. The PR's CI was green
throughout, because a `workflow_dispatch`-only workflow is never executed by the
`pull_request` pipeline — its runtime is exercised only when dispatched.

## What Changes

- **`.github/workflows/publish-agent-image.yml`**: the probe step gains
  `env: GITHUB_TOKEN: ${{ github.token }}` — the same default token the login step
  uses, now handed to the probe by name.
- **`tests/test_publish_agent_image.py`**: a new test locks it — the probe step
  exports exactly the variable `ensure_image.py` reads, and it is the default
  token, not a `secrets.*` reference.
- A tracked OpenSpec change with the spec scenario.

## Impact

Additive: one `env:` on one step plus its regression test. The publish path is
unchanged; a dispatch now reaches the build.

## Not covered

- Rebuilding/re-publishing the image itself (that is what a dispatch does).
