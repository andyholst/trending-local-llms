# Proposal: fix-publish-latest-tag

Issue: #232

## Why

Fixing the publish probe (the token exchange, #232 merged earlier) let the
`publish-agent-image` pipeline finally reach the build — and revealed a second
defect in the publish path itself. On dispatch run
[38683713224](https://github.com/andyholst/trending-local-llms/actions/runs/38683713224):

```
$ docker push ghcr.io/andyholst/trending-local-llms:dockerfile-42cda1a4de10
dockerfile-42cda1a4de10: digest: sha256:53a044… size: 3258
$ docker push ghcr.io/andyholst/trending-local-llms:latest
tag does not exist: ghcr.io/andyholst/trending-local-llms:latest
```

`publish()` tagged the image only with the local `IMAGE` and the hash tag
(`docker build -t <IMAGE> -t <tag>`), then pushed `latest_tag()` — the registry
`:latest` ref — which was **never tagged**, so real docker refuses it. The push
aborted the run via `CalledProcessError`.

The reason the bug survived review is the fake `docker` in the tests: it accepted
ANY subcommand, so `docker push <untagged ref>` "succeeded" there while real
docker returns `tag does not exist`.

## What Changes

- **`scripts/ensure_image.py`**: `publish()` builds with `-t latest_tag()` too, so
  the `:latest` ref it pushes has a local tag.
- **`tests/test_ensure_image.py`**: the fake `docker` stub now records every tag a
  `build -t` / `tag` creates and REFUSES to `push` a ref that was never tagged
  (printing `tag does not exist`, like real docker) — the second alarm that would
  have caught this.
- A tracked OpenSpec change.

## Impact

`publish` now pushes both refs (the hash tag and `:latest`) without the
`tag does not exist` refusal. The publish path is otherwise unchanged.

## Not covered

- The probe's token exchange — already merged as its own change
  (`fix-push-check-token-exchange`, #232).
