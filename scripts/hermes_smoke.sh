#!/usr/bin/env bash
# hermes_smoke.sh — prove the search alias is ROUTED and ANSWERS, in seconds.
#
# What it checks (and why not "did it say PONG"):
#   - hermes exits 0 within HERMES_SMOKE_TIMEOUT
#   - the reply is non-empty
#   - the output carries no provider-failure signature (wrong/blocked key,
#     another provider answering — the HF_TOKEN -> Hugging Face 403 mis-route,
#     reasoning that burned the whole budget)
# It does NOT require the model to obey: deepseek once answered "Reply with
# exactly PONG" with "No. I'm an AI assistant, not a ping-pong game", which
# failed qa-validate on master although key, alias and routing were fine.
# A failed attempt is retried once (a single transient provider hiccup must
# not kill a 20-minute search leg).
#
# NO SILENT SKIP (issue #209): this step gates a 20-minute search leg, and it used
# to print `SKIP: NOUS_API_KEY not set` and exit 0 — a green result that had proved
# nothing (AGENTS.md: "a skipped test is a loud FAILURE, never a silent skip"). With
# no key the alias cannot be proven and the model cannot be called at all, so the
# run FAILS, naming the missing variable and the consequence. A caller that
# deliberately works without a key may ask for that explicitly with
# LIVE_CHECK_ALLOW_UNCONFIGURED=1, which reports NOT CONFIGURED instead — CI never
# sets it, so no pipeline can go green here without the alias having answered.
#
# Env: HERMES (binary, default hermes — tests point it at a stub),
#      HERMES_SMOKE_TIMEOUT (default 90), HERMES_SMOKE_ATTEMPTS (default 2),
#      LIVE_CHECK_ALLOW_UNCONFIGURED (1 = report the check as unconfigured, exit 0).
set -u
HERMES="${HERMES:-hermes}"
TIMEOUT="${HERMES_SMOKE_TIMEOUT:-90}"
ATTEMPTS="${HERMES_SMOKE_ATTEMPTS:-2}"
PROMPT="Reply with one short sentence confirming you received this message."
# Hermes / provider failure signatures (case-insensitive)
BAD='rejected your API key|Provider said|HTTP [45][0-9][0-9]|can.t be reached|No visible answer was produced|output length limit|is not a hermes command|Traceback'

if [ -z "${NOUS_API_KEY:-}" ]; then
	# The explicit, non-default opt-out: a caller that knowingly runs without a key
	# (an offline developer reproducing the data path) says so out loud.
	if [ "${LIVE_CHECK_ALLOW_UNCONFIGURED:-0}" = "1" ]; then
		echo "[hermes-smoke] NOT CONFIGURED: NOUS_API_KEY is unset, so the alias cannot be proven."
		echo "[hermes-smoke] LIVE_CHECK_ALLOW_UNCONFIGURED=1 was set deliberately — this check did NOT run."
		exit 0
	fi
	echo "[hermes-smoke] FAIL: NOUS_API_KEY is not set."
	echo "[hermes-smoke]   The alias nous-deepseek reads its key from that name (key_env), so routing"
	echo "[hermes-smoke]   cannot be proven and the model cannot be called at all — a green step here"
	echo "[hermes-smoke]   would tell you nothing about the work it gates."
	echo "[hermes-smoke] Set NOUS_API_KEY, or run with LIVE_CHECK_ALLOW_UNCONFIGURED=1 to skip the live"
	echo "[hermes-smoke] check deliberately (CI never sets that flag)."
	exit 1
fi

for ((i = 1; i <= ATTEMPTS; i++)); do
	out=$(timeout "$TIMEOUT" "$HERMES" -z "$PROMPT" -m nous-deepseek --reasoning none 2>&1)
	rc=$?
	echo "$out" | tail -5
	why=""
	if [ "$rc" -ne 0 ]; then
		why="exit $rc$([ "$rc" -eq 124 ] && echo ' (timeout)')"
	elif [ -z "$(echo "$out" | tr -d '[:space:]')" ]; then
		why="empty reply"
	elif echo "$out" | grep -Eiq "$BAD"; then
		why="provider failure: $(echo "$out" | grep -Eio "$BAD" | head -1)"
	fi
	if [ -z "$why" ]; then
		echo "[hermes-smoke] OK: nous-deepseek answered via the configured alias (attempt $i)"
		exit 0
	fi
	echo "[hermes-smoke] attempt $i/$ATTEMPTS failed: $why"
	[ "$i" -lt "$ATTEMPTS" ] && sleep 3
done
echo "[hermes-smoke] FAIL: alias nous-deepseek did not answer cleanly after $ATTEMPTS attempt(s)"
exit 1
