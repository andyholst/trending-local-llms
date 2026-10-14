#!/usr/bin/env bash
# Run the QA targets of a refresh and tell apart the two kinds of "not zero":
#
#   * the check RAN and has findings  -> report them, keep going, exit 0.
#     A data-quality finding must not stop the merged data from landing as a PR
#     for review (qa-validate flags it, fix-bot repairs it on the branch).
#   * the check COULD NOT RUN         -> fail the job, exit 1.
#     `docker run` exits 125 when the image is missing / the daemon refused it,
#     and 127 is "command not found": neither says anything about the DATA, so a
#     green job must not be reported from them. Measured (run 38542951338, job
#     aggregate): every image-dependent QA target died with
#     "Unable to find image 'trending-local-llms-test:latest' locally" and the
#     `|| echo` guards turned that into a green job.
#
# `make` reports a failed recipe as its own exit 2, so the recipe's status is
# read from its output ("make: *** [Makefile:450: data-gaps] Error 125") together
# with the docker messages that say the image never came up.
#
# Usage:  qa_report.sh <target> [target ...]
set -uo pipefail

# `make[1]:` too: a sub-make (MAKEFLAGS inherited) prefixes the message that way.
CANNOT_RUN_RE='Unable to find image|pull access denied|Cannot connect to the Docker daemon|docker: Error response from daemon|make(\[[0-9]+\])?: \*\*\* .*Error (125|127)'
failed=0
for target in "$@"; do
  echo "== qa-report: make ${target} =="
  out="$(make "${target}" 2>&1)"
  rc=$?
  printf '%s\n' "${out}"
  if [ "${rc}" -eq 0 ]; then
    continue
  fi
  if printf '%s' "${out}" | grep -qE "${CANNOT_RUN_RE}"; then
    echo "::error::qa-report: \`make ${target}\` could not run (no image / no such command) — a harness failure, not a data finding"
    failed=1
  else
    echo "[qa-report] make ${target} reported findings (rc=${rc}); data still lands for review"
  fi
done
if [ "${failed}" -ne 0 ]; then
  echo "qa-report: at least one target could not run — the QA pass did NOT run, failing" >&2
  exit 1
fi
echo "qa-report: every QA target ran (findings above are reports, not harness failures)"
