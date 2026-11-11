# Proposal: fix-publish-login-token-by-name

Issue: #240

## Why

The `publish-agent-image` GHCR login step interpolated the credential into the
`run:` text:

```yaml
- name: Log in to GHCR with the default token
  run: echo "${{ github.token }}" | docker login ghcr.io -u "${{ github.actor }}" --password-stdin
```

`${{ github.token }}` becomes part of the script GitHub writes and runs, so the
token sits in the script file and in any `ps`/`--debug` output — the same
"a value on a command line / in the script is public to the machine" rule that
`AGENTS.md` rule 3e and llgenie's `secrets-in-run-block` guard state. GitHub's
own token is a credential too, even though it is not under `secrets.`.

This repo's own `scripts/check_secret_output.py` does not flag it (it matches
`${{ secrets.X }}`, not `${{ github.token }}`) — filed as a separate finding.

## What Changes

- **`.github/workflows/publish-agent-image.yml`**: the login step passes the token
  and the actor through `env:` (`GHCR_TOKEN`, `GHCR_USER`); the `run:` line expands
  `$GHCR_TOKEN` at run time and interpolates no `${{ }}`.
- **`tests/test_publish_agent_image.py`**: `test_publishing_uses_the_default_token_not_a_pat`
  now asserts the token is passed by NAME and that the login `run:` line carries
  no `${{ }}` expression.
- A tracked OpenSpec change.

## Impact

Behaviour is unchanged (the login still uses the default token as the actor); the
credential is no longer written into the script text.

## Not covered

- Extending `scripts/check_secret_output.py` to also flag `${{ github.token }}` in
  a `run:` block — filed as its own issue.
