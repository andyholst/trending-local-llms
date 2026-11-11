# agent-image-publish

## ADDED Requirements

### Requirement: The publish probe receives the credential it reads

`scripts/ensure_image.py push_check()` reads the GHCR credential from the
environment (`GITHUB_TOKEN` or `GH_TOKEN`). The `publish-agent-image` workflow's
`Prove this credential can push` step MUST therefore export `GITHUB_TOKEN:
${{ github.token }}` — the default token, never a `secrets.*` reference — so the
probe finds the credential instead of failing `no credential in the environment`.

WHEN the `publish-agent-image` workflow is dispatched,
THEN the probe step exports the same default token the login step uses, and the
probe reaches the registry instead of reporting a missing credential.

#### Scenario: the probe step hands over the token the script reads

- **Given** the workflow's probe step and the script that runs in it
- **When** the step's `env` is compared with the variable `ensure_image.py` reads
- **Then** the step exports `GITHUB_TOKEN: ${{ github.token }}` and references no `secrets.*`
- **Test:** `tests/test_publish_agent_image.py::test_the_probe_step_hands_over_the_token_the_script_reads`
