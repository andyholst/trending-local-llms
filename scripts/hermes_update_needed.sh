#!/usr/bin/env bash
# Decide whether a Hermes update should run on this invocation.
#
# Logic: update when it's SUNDAY (day-of-week == 7) OR UPDATE_HERMES=1 is
# explicitly forced. Otherwise skip (the Docker image bakes Hermes at build
# time, and the image is rebuilt weekly on Sunday, so a per-run update is
# wasted).
#
# Reads the REAL system clock via `date +%u` (1=Mon..7=Sun). Tests set the
# internal clock with libfaketime so the real date logic is exercised for
# every day of the week — no logic mocks.
#
# Prints "1" (update) or "0" (skip). Exit code is always 0.

DOW="$(date +%u)"
if [ "$DOW" = "7" ] || [ "${UPDATE_HERMES:-0}" = "1" ]; then
    echo "1"
else
    echo "0"
fi
