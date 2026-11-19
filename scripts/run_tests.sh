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

# (issue #839) The suite must not litter the checkout with bytecode copies of its
# credential fixtures: `tests/__pycache__/*.pyc` embed the planted FAKE secrets of
# the secret-scan tests, and every filesystem walker over the checkout (secret-scan
# today, any byte-level gate tomorrow) re-reads them — the exact false-leak source
# issue #836 filed. One export here covers every caller: the container `_test`
# recipe, the host, and direct `scripts/run_tests.sh` invocations.
export PYTHONDONTWRITEBYTECODE=1


here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dir="$here/../tests"

# (issue #1147) The verdict must say WHOSE uid it measured, and a guard that could not run must
# say WHAT did not run. Both strings come from scripts/coverage_gap.py — the ONE definition —
# because a runner that keeps its own copy of the bypass phrase drifts silently (rule 6d): the
# container `make test` runs in is uid 0 (TEST_RUN passes no --user; measured `id -u` = 0 in
# tll-test-3965-16821) while the host runner assumes the invoking uid, and qa-validate run
# 44551541279 went green over a permission-plant guard that never executed.
seam="$here/coverage_gap.py"
gap_prefix=$(python3 "$seam" --gap-prefix) || { echo "[harness] FAIL: cannot read the gap prefix from $seam (issue #1147)" >&2; exit 2; }
bypass_phrase=$(python3 "$seam" --phrase) || { echo "[harness] FAIL: cannot read the bypass phrase from $seam (issue #1147)" >&2; exit 2; }
identity=$(python3 "$seam" --identity-line) || { echo "[harness] FAIL: cannot read the identity line from $seam (issue #1147)" >&2; exit 2; }

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
# The identity line belongs to a RUN verdict, not to `--list` (whose whole stdout is the
# module list — tests/test_ci_wiring.py compares it to the files on disk, so a stray line
# there is a phantom module).
echo "$identity"

ran=0
failed=()
gaps=()
undeclared=()

# (issue #1147) a guard that could not execute declares WHAT did not run, and a PASSING module's
# output used to be deleted unread (`rm -f "$out"` right after the trace) — so the scan runs while
# the file still exists, for a green module as well as a red one.
scan_output() {
	local name="$1" file="$2" line
	while IFS= read -r line; do
		case "$line" in
			"$gap_prefix "*) gaps+=("$name|$line") ;;
			*"$bypass_phrase"*) undeclared+=("$name|$line") ;;
		esac
	done < "$file"
}

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
		scan_output "$name" "$out"
		echo "[test] ok $name"
		rm -f "$out"
		continue
	fi
	echo "=== FAIL: $name ==="
	cat "$out"
	scan_output "$name" "$out"
	rm -f "$out"
	# (issue #890) do NOT stop at the first red: collect every failing module,
	# show each one's output above, and report the FULL red list once at the end.
	failed+=("$name")
done
if [ "${#failed[@]}" -gt 0 ]; then
	echo "[test] ${ran} module(s) passed, ${#failed[@]} FAILED: ${failed[*]}"
	exit 1
fi
# (issue #1147) a bypass reported WITHOUT the declared gap seam is a defect, not a note: the
# measured state was qa-validate run 44551541279, green, where a permission plant was walked
# through by DAC_OVERRIDE and the only trace was a SKIP inside a module that exited 0.
if [ "${#undeclared[@]}" -gt 0 ]; then
	echo "[test] ${ran} module(s) passed, ${#undeclared[@]} undeclared-bypass report(s) FAILED (issue #1147)"
	for l in "${undeclared[@]}"; do
		echo "[harness] FAIL ${l%%|*}: ${l#*|} — a bypass must travel inside the declared gap seam (scripts/coverage_gap.py), never as a bare SKIP" >&2
	done
	exit 1
fi
# A DECLARED gap stays green and is named in the verdict: the honest state of a suite that ran as
# uid 0 is "this half did not run here", stated once, where every reader of the run sees it.
if [ "${#gaps[@]}" -gt 0 ]; then
	echo "[harness] coverage-gap ${#gaps[@]} declared; ${identity}"
	for l in "${gaps[@]}"; do
		echo "  ${l#*|}"
	done
fi
echo "[test] $ran module(s) passed"
