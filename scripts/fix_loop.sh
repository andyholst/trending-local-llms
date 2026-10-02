#!/usr/bin/env bash
# fix_loop.sh — the fix-bot's repair loop (runs on the CI runner / host).
#
#   check -> (green? stop) -> hermes fix with the exact failure report -> re-check
#
# Each round runs the SAME deterministic checks qa-validate runs (make validate,
# validate-search, validate-mapped, test) and writes their full output to
# $QA_REPORT. When anything is red, `make fix` runs Hermes with that report
# (the _fix prompt tells it to read qa-report.txt first), then the loop
# re-checks. It stops as soon as the checks are green, and gives up after
# $FIX_ROUNDS fix attempts.
#
# Exit codes: 0 = green (data is safe to push), 1 = still red after all rounds.
# It never commits or pushes — the workflow pushes ONLY on exit 0.
#
# Env:
#   FIX_ROUNDS  max Hermes fix attempts (default 3)
#   QA_REPORT   report path, bind-mounted into the container (default qa-report.txt)
#   MAKE        make binary (default make) — tests point this at a recorder
set -uo pipefail

ROUNDS="${FIX_ROUNDS:-3}"
REPORT="${QA_REPORT:-qa-report.txt}"
MAKE="${MAKE:-make}"
# Fast -> slow; stop at the FIRST red check (its output is what Hermes needs).
# The full unit suite (make test, ~minutes) only runs once everything else is
# green — it used to run before every Hermes round.
CHECKS=(validate-search validate-mapped validate)

run_checks() {
	: >"$REPORT"
	local t
	for t in "${CHECKS[@]}" test; do
		echo "=== make $t ===" >>"$REPORT"
		if ! "$MAKE" "$t" >>"$REPORT" 2>&1; then
			echo "=== make $t: FAILED ===" >>"$REPORT"
			return 1
		fi
	done
	return 0
}

# Real failures only: validator 'FAIL:' lines from the checks, the unit-test
# 'FAIL <name>' lines and suite totals — NOT the 'FAIL: m1 ...' lines negative
# tests print from their fixtures inside the 'make test' section.
summary() {
	awk '
		/^=== make test ===/ { in_test = 1; next }
		/^=== make / { in_test = 0 }
		in_test && /^  FAIL [^:]/ { print; next }
		in_test && /PASSED [0-9]+ \| FAILED [1-9]/ { print; next }
		in_test && /Traceback|Error:/ { print; next }
		!in_test && /FAIL|FAILED ===|Error|Traceback/ && !/FAILED 0/ { print }
	' "$REPORT" | head -40 || true
}

for ((round = 1; round <= ROUNDS; round++)); do
	echo "--- fix-bot round $round/$ROUNDS: running checks ---"
	if run_checks; then
		echo "[fix-loop] GREEN after $((round - 1)) fix round(s)"
		exit 0
	fi
	echo "[fix-loop] checks RED — failures:"
	summary
	echo "--- fix-bot round $round/$ROUNDS: hermes fix (reads $REPORT) ---"
	"$MAKE" fix || echo "[fix-loop] make fix exited non-zero; re-checking anyway"
done

echo "--- fix-bot: final check after $ROUNDS fix round(s) ---"
if run_checks; then
	echo "[fix-loop] GREEN after $ROUNDS fix round(s)"
	exit 0
fi
echo "[fix-loop] still RED after $ROUNDS fix round(s) — leaving for manual review"
summary
exit 1
