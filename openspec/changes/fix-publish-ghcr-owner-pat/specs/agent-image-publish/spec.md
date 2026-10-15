# agent-image-publish

## ADDED Requirements

### Requirement: The GHCR login uses the owner PAT, passed by NAME

`publish-agent-image`'s GHCR login step MUST use the owner PAT
`FIXBOT_DISPATCH_TOKEN` (the fleet's one long-lived credential) and pass it to the
shell through `env:` (`GHCR_TOKEN`), so the `run:` line expands it at run time and
never interpolates a credential expression as script text — where it would sit in
the script GitHub writes and in any `ps`/`--debug` output (AGENTS.md rule 3e). The
probe step's `GITHUB_TOKEN` MUST be the same PAT, and the `guard` job MUST keep the
default `github.token`, because it runs BEFORE any secret is read.

WHEN the login step runs,
THEN the token reaches the shell by NAME (`echo "$GHCR_TOKEN" | docker login …`)
and the `run:` line carries no `${{ }}` expression.

#### Scenario: the login and probe use the owner PAT

- **Given** the `publish-agent-image` workflow's login and probe steps
- **When** their `env:` and `run:` lines are read
- **Then** the login expands `$GHCR_TOKEN` and contains no `${{ }}`, and both `GHCR_TOKEN` and `GITHUB_TOKEN` are set from `secrets.FIXBOT_DISPATCH_TOKEN`
- **Test:** `tests/test_publish_agent_image.py::test_publishing_uses_the_owner_pat_for_ghcr`, `tests/test_publish_agent_image.py::test_the_probe_step_hands_over_the_token_the_script_reads`

#### Scenario: the guard keeps the default token

- **Given** the `publish-agent-image` workflow's `guard` job (which runs before any secret is read)
- **When** its token is read
- **Then** it is `github.token`, not a secret
- **Test:** `tests/test_publish_agent_image.py::test_the_guard_runs_first_and_before_any_secret`
