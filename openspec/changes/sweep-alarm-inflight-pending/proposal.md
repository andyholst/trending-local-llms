# A sweep still in flight is PENDING, not a false red

**Issues:** [#801](https://github.com/andyholst/trending-local-llms/issues/801)
**Capability:** `alarms`

## Why

`make sweep-alarm` grades the newest `schedule` delivery of the weekly sweep. When that delivery
has **not concluded yet** — the run list reports it as `in_progress` — the fresh-delivery branch
treats *any* non-`success` conclusion as the #498 verdict “a sweep that ran and did not succeed
delivered nothing”, and the alarm goes red on a sweep that is simply **still running**. Measured:
`queued-alarm` #88 (run 43049550731, job 130622645547) at 15:33Z judged the sweep started at
15:19Z — 14 minutes into its usual 15–30+ minutes — as a failed delivery; #87 (06:59Z) and #86
(2026-11-05) red the same way. The sweep #88 judged later **succeeded** (issue-bot #445, 19:03Z).
An alarm that cries the wrong wolf every Wednesday destroys the signal rule 6l/issue #497 built:
a genuinely dropped or failed sweep no longer stands out.

## What Changes

- **`scripts/sweep_alarm.py`** — the fresh-delivery branch grows a third state. A delivery whose
  conclusion is in flight (`in_progress` / `queued`) and whose age is within
  `--inflight-cap-hours` (new flag, default 3) returns a **PENDING** verdict: printed loudly as
  PENDING with the run URL, **exit 0** — the next alarm delivery re-grades it. Past the cap the
  same delivery FAILs, named as a run still in flight beyond the cap (a hung sweep is loud).
  Concluded `failure` / `cancelled` keep the exact #498 fresh-red verdict; `success` stays OK.
- **`tests/test_sweep_alarm.py`** — new scenarios: fresh `in_progress` → PENDING/0 (pure decision
  and real CLI through the stub `gh`); `in_progress` past the cap → exit 1 naming it; the
  #498 fresh-red scenarios stay exactly as they are (no weakening).
- **`AGENTS.md` §8** — the `test_sweep_alarm` guard row extended with the two new failure modes
  (review-required, rule 3c; declared in a comment on #801).

## Impact

- `queued-alarm` stops going red mid-sweep; the weekly Wednesday alarm keeps its real signals
  (dropped slot, concluded failure, hung delivery) untouched.
- No Makefile target, workflow job or script is added or renamed; `make sweep-alarm` stays the
  single entry (rules 6d/6m unchanged).

## Not covered

- Filing an issue from a failed main-pipeline **log** (diagnose-and-file behavior) — tracked as
  issue #802, its own reviewed change.
- Moving the alarm's schedule after the sweep window — recorded as a finding on this change,
  filed, not fixed here (rule 6g).
