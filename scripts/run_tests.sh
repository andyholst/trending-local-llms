#!/usr/bin/env bash
# run_tests.sh — the ONE test runner (issues #176 and #192).
#
# Every `tests/test_*.py` is a SCRIPT: it prints `ok`/`FAIL` lines and exits
# non-zero on its own failures. They are not pytest tests (no asserts, no
# fixtures), so the old `_test` recipe's `python3 -m pytest tests/ -q
# 2>/dev/null || (31 explicit calls)` was a dead branch: pytest is not in the
# test image, its stderr was discarded, and the suite that actually ran was a
# hand-maintained chain where a new module could be invisible.
#
# This runner is the chain, in ONE place: it discovers the modules, runs each in
# its own process, and STOPS at the first failure with that module's full output
# (the fix loop needs the first red, not a wall of them).
#
# Usage:
#   scripts/run_tests.sh [--list] [TESTS_DIR]
#
#   --list      print the modules it would run, one per line, and exit 0
#   TESTS_DIR   the directory holding test_*.py (default: the repo's tests/)
#
# Exit: 0 = every module passed, 1 = one failed (its output is shown), 2 = usage.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dir="$here/../tests"
list=0
for arg in "$@"; do
	case "$arg" in
		--list) list=1 ;;
		-*) echo "usage: run_tests.sh [--list] [TESTS_DIR]" >&2; exit 2 ;;
		*) dir="$arg" ;;
	esac
done

shopt -s nullglob
modules=("$dir"/test_*.py)
shopt -u nullglob
if [ "${#modules[@]}" -eq 0 ]; then
	echo "[test] FAIL: no tests/test_*.py under $dir" >&2
	exit 1
fi
if [ "$list" = "1" ]; then
	printf '%s\n' "${modules[@]}"
	exit 0
fi

ran=0
for t in "${modules[@]}"; do
	name="$(basename "$t")"
	out="$(mktemp)"
	if python3 "$t" >"$out" 2>&1; then
		ran=$((ran + 1))
		rm -f "$out"
		continue
	fi
	echo "=== FAIL: $name ==="
	cat "$out"
	rm -f "$out"
	echo "[test] $ran module(s) passed, $name FAILED — stopping at the first red (its output is above)"
	exit 1
done
echo "[test] $ran module(s) passed"
