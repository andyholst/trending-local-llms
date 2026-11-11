# agent-image-publish

## ADDED Requirements

### Requirement: The push probe exchanges the token for a push-scoped GHCR token

GHCR does not accept a raw token as a Bearer on the registry API. `push_check()`
MUST exchange the ambient credential for a push-scoped token at the registry's
token endpoint (`GET {scheme}://{host}/token?scope=repository:{path}:pull,push&service={host}`,
Basic auth, non-empty username), then start the empty blob upload with
`Authorization: Bearer <scoped>`. It MUST still report the registry's own refusal
verbatim, at the token endpoint or at the upload.

WHEN the `publish-agent-image` workflow is dispatched,
THEN the probe exchanges the credential for a push-scoped token and the upload is
accepted (HTTP 201/202), instead of failing `403 invalid token`.

#### Scenario: the probe starts a scoped upload session

- **Given** a local stand-in for the registry's token + upload endpoints
- **When** `push-check` runs against it with an ambient token
- **Then** it first GETs the token endpoint with Basic auth and then POSTs the blob-upload carrying the SCOPED token
- **Test:** `tests/test_publish_agent_image.py::test_push_check_proves_the_credential_before_the_build`

#### Scenario: the registry's refusal is reported verbatim

- **Given** a stand-in registry whose upload endpoint refuses with `permission_denied: create_package`
- **When** `push-check` runs
- **Then** it exits non-zero and repeats the registry's own message, saying the build was not started
- **Test:** `tests/test_publish_agent_image.py::test_push_check_proves_the_credential_before_the_build`

#### Scenario: the live registry accepts the exchanged token

- **Given** the live `ghcr.io` and an ambient token
- **When** `python3 scripts/ensure_image.py push-check` runs
- **Then** it reports the upload session accepted (HTTP 201/202) and that the build may proceed
- **Test:** CI `publish-agent-image` dispatch → `make agent-image-push-check`
