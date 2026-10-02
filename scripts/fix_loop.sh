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
#
# Reasoning budget: `make fix` runs Hermes with HERMES_FIX_REASONING (low).
# deepseek-v4-flash still burns its whole 65,536-token output cap on reasoning
# at `low` in some rounds ('No visible answer was produced ... reasoning
# consumed the entire budget') and writes nothing — 2 of 3 rounds on PR #80.
# When that signature shows up, the SAME round is retried once with
# HERMES_FIX_REASONING=none (0 reasoning tokens) instead of wasting the round.
set -uo pipefail

ROUNDS="${FIX_ROUNDS:-3}"
REPORT="${QA_REPORT:-qa-report.txt}"
MAKE="${MAKE:-make}"
# Fast -> slow; stop at the FIRST red check (its output is what Hermes needs).
# The full unit suite (make test, ~minutes) only runs once everything else is
# green — it used to run before every Hermes round.
CHECKS=(validate-search validate-mapped validate)
BUDGET_SIG='reasoning consumed the entire budget|No visible answer was produced'

# The report holds ONLY the failing check's output (plus the list of checks
# that passed). The passing checks also run unit suites whose negative tests
# print fixture 'FAIL: m1 ...' lines; keeping them buried the one real failure
# below 40 noise lines and fed them to Hermes as if they were failures.
run_checks() {
	: >"$REPORT"
	local t out passed=()
	out="$(mktemp)"
	for t in "${CHECKS[@]}" test; do
		if "$MAKE" "$t" >"$out" 2>&1; then
			passed+=("$t")
			continue
		fi
		{
			echo "checks passed: ${passed[*]:-none}"
			echo "=== make $t ==="
			cat "$out"
			echo "=== make $t: FAILED ==="
		} >>"$REPORT"
		rm -f "$out"
		return 1
	done
	rm -f "$out"
	echo "checks passed: ${passed[*]}" >>"$REPORT"
	return 0
}

# One Hermes fix attempt; retried in the same round with reasoning off when
# the model spent its whole output budget thinking.
run_fix() {
	local log rc
	log="$(mktemp)"
	"$MAKE" fix 2>&1 | tee "$log"
	rc=${PIPESTATUS[0]}
	if [ "$rc" != "0" ] && grep -Eq "$BUDGET_SIG" "$log"; then
		echo "[fix-loop] reasoning used the whole output budget; retrying this round with HERMES_FIX_REASONING=none"
		"$MAKE" fix HERMES_FIX_REASONING=none
		rc=$?
	fi
	rm -f "$log"
	return "$rc"
}

# Real failures only: validator 'FAIL:' lines from the checks, the unit-test
# 'FAIL <name>' lines and suite totals — NOT the 'FAIL: m1 ...' lines negative
# tests print from their fixtures. Unit-test output starts at the first
# '  ok  <name>' line (validate-search / validate-mapped run suites too).
summary() {
	awk '
		/^=== make test ===/ { in_test = 1; next }
		/^=== make / { in_test = 0 }
		/^  ok  / { in_test = 1; next }
		in_test && /^  FAIL [^:]/ { print; next }
		in_test && /PASSED [0-9]+ \| FAILED [1-9]/ { print; next }
		in_test && /Traceback|Error:|FAILED ===/ { print; next }
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
	run_fix || echo "[fix-loop] make fix exited non-zero; re-checking anyway"
done

echo "--- fix-bot: final check after $ROUNDS fix round(s) ---"
if run_checks; then
	echo "[fix-loop] GREEN after $ROUNDS fix round(s)"
	exit 0
fi
echo "[fix-loop] still RED after $ROUNDS fix round(s) — leaving for manual review"
summary
exit 1
