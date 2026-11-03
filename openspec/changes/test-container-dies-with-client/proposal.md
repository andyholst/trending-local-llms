# The test container dies with its client

Issue: #720

## Why

`make test` and the other `TEST_RUN` targets use `docker run --rm`. That flag removes the container only after the container exits. A tool timeout that kills the client leaves the container running. Measured on 2026-11-03: two `make _test` containers stayed up for hours after the client was gone, and `make` inside was spinning.

## What Changes

- `scripts/docker_test_run.sh` names the container and removes it when the client process dies, including a SIGKILL of that client.
- `TEST_RUN` goes through that wrapper. The mounts, the forwarded credentials, and `--rm` stay.
- `tests/test_docker_test_run.py` kills the client and requires the named container to be removed.

## Impact

A finished or killed `make test` / `make validate` run does not leave a container behind. No workflow and no schedule changes.
