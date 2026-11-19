#!/usr/bin/env bash
# docker_test_run.sh — remove the test container when the client dies.
#
# `docker run --rm` removes a container only after that container exits. The
# client that starts `make test` (and every other TEST_RUN target) is often
# killed by a tool timeout. The container then stays up, and `make` inside can
# spin after it was signaled. This wrapper names the run and removes it when
# the wrapper itself is gone, including a SIGKILL of the wrapper.
#
# Usage: scripts/docker_test_run.sh [docker-run arguments...]
# Exit: the exit code of `docker run`.
set -u

name="tll-test-$$-${RANDOM}"
self=$$

# A separate session, so a process-group kill of this wrapper does not take
# the watcher with it. When the wrapper pid is gone, the container is removed.
setsid bash -c '
  name=$1
  self=$2
  while kill -0 "$self" 2>/dev/null; do
    sleep 1
  done
  docker rm -f "$name" >/dev/null 2>&1 || true
' bash "$name" "$self" >/dev/null 2>&1 &
watcher=$!

cleanup() {
  kill "$watcher" 2>/dev/null || true
  docker rm -f "$name" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM HUP

# (issue #1147) Name the identity this container STARTS under, and forward it IN as a variable
# NAME (never a value with meaning): this seam is how every TEST_RUN container is started and it
# passes no `--user`, so the container runs as the image's default user — measured `id -u` = 0 in
# tll-test-3965-16821 — while the uid on this line is whoever ran `make test`.
# scripts/coverage_gap.py reads TLL_INVOKING_UID back INSIDE the container and prints both halves
# on the suite identity line, so a green verdict states which identity executed it.
invoking_uid="$(id -u):$(id -g)"
echo "[harness] docker_test_run identity: invoking uid:gid=$invoking_uid; the container runs as the image default user unless --user is passed" >&2

docker run --name "$name" -e "TLL_INVOKING_UID=$invoking_uid" "$@"
rc=$?
exit "$rc"
