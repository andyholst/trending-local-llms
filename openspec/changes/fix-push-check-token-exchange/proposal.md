# Proposal: fix-push-check-token-exchange

Issue: #232

## Why

The `publish-agent-image` push probe still fails on every dispatch, now with the
real error. #230 gave the probe step its `GITHUB_TOKEN`, but `push_check()` sends
that token **directly as a Bearer** to `POST /v2/<path>/blobs/uploads/`, and GHCR
does not accept the raw token as a Bearer. Measured on dispatch run
[38681867864](https://github.com/andyholst/trending-local-llms/actions/runs/38681867864):

```
env: { GITHUB_TOKEN: ***, ... }
[push-check] FAIL: the credential cannot push to ghcr.io/andyholst/trending-local-llms: HTTP 403 {"errors":[{"code":"DENIED","message":"invalid token"}]}
```

Measured directly against the live registry:

- `Authorization: Bearer <raw token>` on the upload → HTTP 403 `invalid token`.
- `Authorization: Basic <user:token>` on the upload → HTTP 401 `authentication required`.
- `GET https://ghcr.io/token?scope=repository:<o>/<r>:pull,push&service=ghcr.io`
  (Basic auth) → HTTP 200 `{"token": …}`, then `Bearer <scoped>` on the upload →
  **HTTP 202 Completed**. This is the Docker Registry v2 flow, and exactly what
  `asimov-agent/llgenie`'s `check_push` does.

## What Changes

- **`scripts/ensure_image.py`**: `push_check()` exchanges the ambient token for a
  push-scoped token at `GET {scheme}://{host}/token?scope=repository:{path}:pull,push&service={host}`
  (Basic auth), then POSTs the empty blob upload with `Authorization: Bearer <scoped>`.
  A `_docker_user(host)` helper reads the login's username from the docker config
  (GHCR ignores it but requires it non-empty).
- **`tests/test_publish_agent_image.py`**: the fake registry now serves the token
  endpoint and asserts the upload carries the SCOPED token (proving the exchange),
  not the raw one, and that the token request carries Basic auth.
- A tracked OpenSpec change.

## Impact

The probe now authenticates against GHCR the way a Docker client does. The publish
path (`docker build` / `docker push` after `docker login`) is unchanged.

## Not covered

- Nothing else; this is the one missing exchange.
