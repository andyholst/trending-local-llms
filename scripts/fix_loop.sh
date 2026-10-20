#!/usr/bin/env bash
# fix_loop.sh — the fix-bot's repair loop (runs on the CI runner / host).
#
#   check -> (green? stop) -> hermes fix with the exact failure report -> re-check
#
# Each round runs the SAME deterministic checks qa-validate runs (make validate,
# validate-search, validate-mapped, openspec-check, findings-check, test) and
# writes their full output to
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
# the pinned deepseek flash SKU still burns its whole 65,536-token output cap on reasoning
# at `low` in some rounds ('No visible answer was produced ... reasoning
# consumed the entire budget') and writes nothing — 2 of 3 rounds on PR #80.
# When that signature shows up, the SAME round is retried once with
# HERMES_FIX_REASONING=none (0 reasoning tokens) instead of wasting the round.
set -uo pipefail

ROUNDS="${FIX_ROUNDS:-3}"
REPORT="${QA_REPORT:-qa-report.txt}"
# Notes the loop itself records between rounds (a timed-out round, a round that made
# no progress: issue #383). `run_checks` truncates $REPORT at the start of every
# round, so these are accumulated here and folded into $REPORT by the NEXT
# run_checks — otherwise the note is wiped before anyone can see it.
# It lives OUTSIDE the checkout (issue #390). `$REPORT.notes` put the file in the
# repo root, where the bot's `git add -A` commit step picked it up: PR #387 carries
# an empty `qa-report.txt.notes` it never meant to add, and a NON-empty one would
# publish the loop's own diagnostics (a hung round, a round that made no progress)
# into the repository. Scratch state of the loop is not repository content.
NOTES="$(mktemp "${TMPDIR:-/tmp}/fix-loop-notes.XXXXXX")"
trap 'rm -f "$NOTES"' EXIT
MAKE="${MAKE:-make}"
# Bound ONE Hermes round (issue #383). The loop used to run `make fix` with no time
# limit at all, so a round that never returned was killed by the JOB's
# `timeout-minutes: 120` instead of by the loop: 1 h 58 m of one 2 h budget went on
# round 1 of 3, the loop's own failure path (report, PR comment, window close) never
# ran, and the PR was left with nothing (measured on run 39124432576). 1800 s keeps
# FIX_ROUNDS rounds plus their checks comfortably inside a 2 h job.
FIX_TIMEOUT="${HERMES_FIX_TIMEOUT:-1800}"
# The branch a red PR must be measured against (issue #383): a refresh PR is usually
# red because the BASE moved, not because its own data is wrong.
BASE="${FIX_BASE:-master}"
FIX_BASE_MERGE="${FIX_BASE_MERGE:-1}"
# A CONFLICTED base merge is a REPAIR, not a reason to give up (issue #475): the hunks are
# written here, a Hermes round resolves them, and the merge is completed — or aborted at the
# very end, so a branch that could not be resolved is never pushed half-merged.
CONFLICT_REPORT="$(mktemp "${TMPDIR:-/tmp}/fix-loop-conflict.XXXXXX")"
BASE_CONFLICT_PENDING=0
# Fast -> slow; stop at the FIRST red check (its output is what Hermes needs).
# The full unit suite (make test, ~minutes) only runs once everything else is
# green — it used to run before every Hermes round.
CHECKS=(lint validate-search validate-mapped openspec-check architecture-check)
# An IMPLEMENTATION run must also have recorded what it found (AGENTS.md,
# "analysis ships issues, not code"): issue-bot sets REQUIRE_FINDINGS=1, so a
# missing findings.md is a red check Hermes has to fix. fix-bot repairs a data
# PR nobody implemented by hand, so it does not demand the file.
[ "${REQUIRE_FINDINGS:-0}" = "1" ] && CHECKS+=(findings-check)
CHECKS+=(validate)
BUDGET_SIG='reasoning consumed the entire budget|No visible answer was produced'

# The report holds ONLY the failing check's output (plus the list of checks
# that passed). The passing checks also run unit suites whose negative tests
# print fixture 'FAIL: m1 ...' lines; keeping them buried the one real failure
# below 40 noise lines and fed them to Hermes as if they were failures.
run_checks() {
	: >"$REPORT"
	# An unresolved base merge is RED by definition (issue #475): the tree carries conflict
	# markers, so no check on it means anything. This also keeps a lenient/stubbed check from
	# reporting the branch GREEN while `git` still has an unmerged index.
	if [ "${BASE_CONFLICT_PENDING:-0}" = "1" ]; then
		{
			echo "=== base merge conflict: unresolved ==="
			echo "unmerged paths: $(git diff --name-only --diff-filter=U 2>/dev/null | tr '\n' ' ')"
			[ -s "$CONFLICT_REPORT" ] && cat "$CONFLICT_REPORT"
		} >>"$REPORT"
		[ -s "$NOTES" ] && cat "$NOTES" >>"$REPORT"
		return 1
	fi
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
		[ -s "$NOTES" ] && cat "$NOTES" >>"$REPORT"
		# A pending base-merge conflict is part of what this round must fix (issue #475).
		[ "${BASE_CONFLICT_PENDING:-0}" = "1" ] && [ -s "$CONFLICT_REPORT" ] && cat "$CONFLICT_REPORT" >>"$REPORT"
		rm -f "$out"
		return 1
	done
	rm -f "$out"
	[ -s "$NOTES" ] && cat "$NOTES" >>"$REPORT"
	echo "checks passed: ${passed[*]}" >>"$REPORT"
	return 0
}

# One Hermes fix attempt, BOUNDED (issue #383), retried in the same round with
# reasoning off when the model spent its whole output budget thinking.
# `timeout` kills the round and returns 124; the round is then REPORTED, never left
# to the job's own `timeout-minutes` (measured: 1 h 58 m inside round 1 of 3).
TIMEOUT_RC=124
run_fix() {
	local log rc
	log="$(mktemp)"
	timeout "$FIX_TIMEOUT" "$MAKE" fix 2>&1 | tee "$log"
	rc=${PIPESTATUS[0]}
	if [ "$rc" = "$TIMEOUT_RC" ]; then
		echo "[fix-loop] round TIMED OUT after ${FIX_TIMEOUT}s (HERMES_FIX_TIMEOUT) — the LOOP aborted it, not the job limit"
		{
			echo
			echo "=== make fix: TIMED OUT after ${FIX_TIMEOUT}s (HERMES_FIX_TIMEOUT) ==="
			echo "[fix-loop] one Hermes round is bounded so a hung round cannot eat the job budget; this round produced no fix."
		} >>"$NOTES"
		rm -f "$log"
		return "$TIMEOUT_RC"
	fi
	if [ "$rc" != "0" ] && grep -Eq "$BUDGET_SIG" "$log"; then
		echo "[fix-loop] reasoning used the whole output budget; retrying this round with HERMES_FIX_REASONING=none"
		timeout "$FIX_TIMEOUT" "$MAKE" fix HERMES_FIX_REASONING=none
		rc=$?
		[ "$rc" = "$TIMEOUT_RC" ] && echo "[fix-loop] the reasoning-off retry also timed out after ${FIX_TIMEOUT}s"
	fi
	rm -f "$log"
	return "$rc"
}

# Bring the BASE into the branch BEFORE any LLM round (issue #383; AGENTS.md §6n:
# "bring a behind branch up to date before you push"). A red refresh PR is usually
# red because the BASE moved — a contract, a prompt, an ingest rule — and no repair
# of the branch's own tree can fix a rule the branch does not have. Never fatal and
# never destructive: a fetch or merge that cannot happen leaves the branch as it was.
merge_base() {
	if [ "$FIX_BASE_MERGE" != "1" ]; then
		echo "[fix-loop] base merge disabled (FIX_BASE_MERGE=$FIX_BASE_MERGE)"
		return 0
	fi
	git rev-parse --git-dir >/dev/null 2>&1 || { echo "[fix-loop] not a git checkout — skipping the base merge"; return 0; }
	# `actions/checkout` clones shallow, and a shallow history cannot be counted.
	if [ "$(git rev-parse --is-shallow-repository 2>/dev/null || echo false)" = "true" ]; then
		git fetch --unshallow origin "$BASE" >/dev/null 2>&1 || true
	fi
	if ! git fetch --no-tags origin "$BASE" >/dev/null 2>&1; then
		echo "[fix-loop] cannot fetch origin/$BASE — continuing without the base merge"
		return 0
	fi
	local behind
	behind="$(git rev-list --count "HEAD..FETCH_HEAD" 2>/dev/null || echo 0)"
	if [ "${behind:-0}" = "0" ]; then
		echo "[fix-loop] branch is up to date with origin/$BASE"
		return 0
	fi
	echo "[fix-loop] branch is $behind commit(s) behind origin/$BASE — merging the base in BEFORE any LLM round"
	if git merge --no-edit FETCH_HEAD >/dev/null 2>&1; then
		echo "[fix-loop] merged origin/$BASE ($behind commit(s)) — a failure the base already fixed now needs no LLM round"
	else
		local conflicted
		conflicted="$(git diff --name-only --diff-filter=U 2>/dev/null | tr '\n' ' ')"
		echo "[fix-loop] merging origin/$BASE CONFLICTED in: ${conflicted:-<unreadable>} — a Hermes round resolves it (issue #475)"
		{
			echo "=== base merge conflict: origin/$BASE moved while this branch was open ==="
			echo "Resolve these paths, keep BOTH sides' intent, and remove every conflict marker:"
			echo "  ${conflicted:-<git could not list them>}"
			echo
			echo "Generated artifacts (data/models.json, README.md, data/snapshots/*) are"
			echo "REGENERATED, never hand-merged: keep this branch's copy and re-run the"
			echo "generator, or keep the base's and re-run make merge. Never leave a conflict"
			echo "marker inside the store or the README."
			echo
			for f in $(git diff --name-only --diff-filter=U 2>/dev/null); do
				echo "===== $f ====="
				awk '/^<<<<<<< /,/^>>>>>>> /' "$f" 2>/dev/null | head -80
				echo
			done
		} >"$CONFLICT_REPORT" 2>&1 || true
		BASE_CONFLICT_PENDING=1
	fi
	return 0
}

# A stable signature of the failure the REPORT describes, so a round that leaves it
# byte-identical can be detected (issue #383).
failure_signature() { printf '%s' "$1" | sha256sum | cut -d' ' -f1; }

# Did the round change this tree at all? Only asked inside a git checkout, so the
# control-flow fixtures (which are not git repositories) never trip it.
tree_unchanged() {
	git rev-parse --git-dir >/dev/null 2>&1 || return 1
	[ -z "$(git status --porcelain 2>/dev/null)" ]
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

# The base FIRST (issue #383): a red refresh PR is usually red because the base
# moved, and a failure the base already fixed must cost ZERO LLM rounds.
merge_base

prev_sig=""
for ((round = 1; round <= ROUNDS; round++)); do
	echo "--- fix-bot round $round/$ROUNDS: running checks ---"
	if run_checks; then
		if [ "$round" = "1" ]; then
			echo "[fix-loop] GREEN on the branch with the base merged — the base already carries the fix; no LLM round needed"
		else
			echo "[fix-loop] GREEN after $((round - 1)) fix round(s)"
		fi
		exit 0
	fi
	echo "[fix-loop] checks RED — failures:"
	summary
	sig="$(failure_signature "$(cat "$REPORT")")"
	# A round that changed NOTHING must not buy the next one (issue #383): the same
	# failure twice, with the tree untouched, is a fix that did not stick.
	if [ "$round" -gt 1 ] && [ "$sig" = "$prev_sig" ] && tree_unchanged; then
		echo "[fix-loop] round $((round - 1)) fixed nothing: the failure is byte-identical and the tree is unchanged — stopping instead of spending round $round"
		{ echo "[fix-loop] round $((round - 1)) made no progress: the failing check and the tree are unchanged."; } >>"$REPORT"
		summary
		exit 1
	fi
	prev_sig="$sig"
	echo "--- fix-bot round $round/$ROUNDS: hermes fix (reads $REPORT) ---"
	run_fix || echo "[fix-loop] make fix exited non-zero; re-checking anyway"
	# The conflict the round was asked to resolve (issue #475): if every conflicted path is
	# clean now, COMPLETE the merge, so the branch carries the base and the next check runs on
	# the real tree. If it is still conflicted, the next round gets it again.
	if [ "${BASE_CONFLICT_PENDING:-0}" = "1" ]; then
		if [ -z "$(git diff --name-only --diff-filter=U 2>/dev/null)" ]; then
			git add -A >/dev/null 2>&1 || true
			git -c core.editor=true commit --no-edit -q >/dev/null 2>&1 || true
			echo "[fix-loop] the base merge conflict is resolved — merge completed"
			BASE_CONFLICT_PENDING=0
		else
			echo "[fix-loop] still conflicted in: $(git diff --name-only --diff-filter=U 2>/dev/null | tr '\n' ' ')"
		fi
	fi
done

echo "--- fix-bot: final check after $ROUNDS fix round(s) ---"
if run_checks; then
	echo "[fix-loop] GREEN after $ROUNDS fix round(s)"
	exit 0
fi
echo "[fix-loop] still RED after $ROUNDS fix round(s) — leaving for manual review"
# A merge that could not be resolved is ABORTED, so the workflow's push can never carry a
# tree with conflict markers in it (issue #475): a half-merged branch is worse than a red PR.
if [ "${BASE_CONFLICT_PENDING:-0}" = "1" ]; then
	git merge --abort >/dev/null 2>&1 || true
	echo "[fix-loop] the base merge could not be resolved in $ROUNDS round(s) — aborted it, so nothing half-merged is pushed"
	{ echo "[fix-loop] the base merge could not be resolved — aborted; the branch is unchanged."; } >>"$REPORT"
fi
summary
exit 1
