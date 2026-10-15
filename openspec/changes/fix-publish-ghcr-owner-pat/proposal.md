# Proposal: fix-publish-ghcr-owner-pat

Issue: #248

## Why

`publish-agent-image` logs in to GHCR with the per-run default `github.token`.
The fleet's single long-lived credential is the owner fine-grained PAT
`FIXBOT_DISPATCH_TOKEN` (Actions, Contents, Pull requests, Packages, Workflows
R/W) — the token that pushes, dispatches, and (since #242's scope fix) merges a PR
that edits a workflow file. Using it for the GHCR login too leaves ONE credential
to reason about; the default token is a second, per-run, auto-scoped credential
that has to stay in sync with it.

The `guard` job MUST keep the default `github.token`: it runs BEFORE any secret is
read, so putting a secret there would defeat its own purpose.

## What Changes

- **`.github/workflows/publish-agent-image.yml`**: the login step sets
  `GHCR_TOKEN: ${{ secrets.FIXBOT_DISPATCH_TOKEN }}` and the probe step sets
  `GITHUB_TOKEN: ${{ secrets.FIXBOT_DISPATCH_TOKEN }}` — both passed by NAME (rule
  3e: never interpolated into the `run:` text). The `guard` job keeps
  `github.token`.
- **`tests/test_publish_agent_image.py`**: `test_publishing_uses_the_owner_pat_for_ghcr`
  and `test_the_probe_step_hands_over_the_token_the_script_reads` assert the PAT;
  the guard test asserts the guard's own token stays the default.
- **`ARCHITECTURE.md`**: the publish job row and the Tokens note (rule 6h).
- A tracked OpenSpec change.

## Impact

Behaviour is unchanged (the login still authenticates the triggering actor), and
there is one credential. A forced dispatch is monitored to prove the build + push
still work.

## Not covered

- The token-by-NAME interpolation fix — merged in #242 (#240).
- Every bot step using the PAT: the comment steps MUST keep `github.token` (the PAT
  cannot comment — AGENTS.md rule 6e).
