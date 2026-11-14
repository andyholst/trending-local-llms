#!/usr/bin/env bash
# run_tests.sh — the ONE test runner (issues #176, #192 and #890).
#
# Every `tests/test_*.py` is a SCRIPT: it prints `ok`/`FAIL` lines and exits
# non-zero on its own failures. They are not pytest tests (no asserts, no
# fixtures), so the old `_test` recipe's `python3 -m pytest tests/ -q
# 2>/dev/null || (31 explicit calls)` was a dead branch: pytest is not in the
# test image, its stderr was discarded, and the suite that actually ran was a
# hand-maintained chain where a new module could be invisible.
#
# This runner is the chain, in ONE place: it discovers the modules, runs each in
# its own process, and runs ALL of them even after a failure, showing each
# failing module's output and finishing with the full red list once (#890: an
# operator must not re-run the suite several times to discover every red).
#
# Usage:
#   scripts/run_tests.sh [--list] [TESTS_DIR]
#
#   --list      print the modules it would run, one per line, and exit 0
#   TESTS_DIR   the directory holding test_*.py (default: the repo's tests/)
#
# Exit: 0 = every module passed, 1 = at least one failed (each one's output is
# shown and the summary names all of them), 2 = usage.
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
failed=()
for t in "${modules[@]}"; do
	name="$(basename "$t")"
	out="$(mktemp)"
	if python3 "$t" >"$out" 2>&1; then
		ran=$((ran + 1))
		# (issue #911) a PASSING module leaves a trace in the stream: the old
		# runner discarded a passing module's output entirely, so a fully green
		# suite was ONE line — and a capture that lost the container's stdout
		# looked identical to a clean run. `[test] ok <module>` makes every
		# collected module observable, and the host wrapper counts them.
		echo "[test] ok $name"
		rm -f "$out"
		continue
	fi
	echo "=== FAIL: $name ==="
	cat "$out"
	rm -f "$out"
	# (issue #890) do NOT stop at the first red: collect every failing module,
	# show each one's output above, and report the FULL red list once at the end.
	failed+=("$name")
done
if [ "${#failed[@]}" -gt 0 ]; then
	echo "[test] ${ran} module(s) passed, ${#failed[@]} FAILED: ${failed[*]}"
	exit 1
fi
echo "[test] $ran module(s) passed"
