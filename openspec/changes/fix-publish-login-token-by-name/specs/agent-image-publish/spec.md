# agent-image-publish

## ADDED Requirements

### Requirement: The GHCR login passes the credential by NAME only

`publish-agent-image`'s GHCR login step MUST pass the default token to the shell
through `env:` (`GHCR_TOKEN`), so the `run:` line expands it at run time and never
interpolates `${{ github.token }}` as script text. GitHub's own token is a
credential too; interpolated into `run:`, it sits in the script GitHub writes and
in any `ps`/`--debug` output (AGENTS.md rule 3e).

WHEN the login step runs,
THEN the token reaches the shell by NAME (`echo "$GHCR_TOKEN" | docker login …`)
and the `run:` line carries no `${{ }}` expression.

#### Scenario: the login run text interpolates no credential

- **Given** the `publish-agent-image` workflow's login step
- **When** its `run:` line is read
- **Then** it expands `$GHCR_TOKEN` and contains no `${{ }}`, and `GHCR_TOKEN: ${{ github.token }}` is set in the step's `env:`
- **Test:** `tests/test_publish_agent_image.py::test_publishing_uses_the_default_token_not_a_pat`
