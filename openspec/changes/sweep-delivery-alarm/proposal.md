# Proposal: sweep-delivery-alarm

Issue: #497 (measured: the hourly sweep asks GitHub for 24 slots a day and gets ~5)

## Why

`issue-bot.yml` carries `cron: "19 * * * *"` and takes ONE issue per delivery. The deliveries
actually recorded on 2026-10-19 → 2026-10-21 were **3–6 hours apart** (01:41:54 ← 3h17 ←
22:24:00 FAILED ← 3h53 ← 18:31:58 ← 4h52 ← …), so the hourly queue drains at ~5 issues a day, not
24 — and nothing anywhere says so. `queued-alarm` cannot see it: it reads runs that EXIST, and a
slot GitHub never created has no run to look at. `refresh-bot` learned this once already and
carries a backup slot; the sweep never got one.

Since #496 the sweep also reads `tech-debt`, so its queue holds 48 open issues and takes one per
delivery. A stale delivery is indistinguishable from a healthy one.

## What Changes

- **A second schedule slot** on `issue-bot.yml` (`49 * * * *`, alongside `19 * * * *`). The
  workflow-level `concurrency: issue-bot-<…>` already serialises the sweeps, and a run with
  nothing to do is a green no-op, so the spare slot costs nothing and buys coverage against the
  drop.
- **`scripts/sweep_alarm.py` + `make sweep-alarm`**: reads the newest `schedule` run of the sweep
  and FAILS (exit 1) when it is older than `MAX_AGE_HOURS` (default 3), naming the age, how many
  `:19` slots were missed, the gaps it can see, and the last delivery's conclusion (so "red on
  every run" is visible too). No delivery at all is its own verdict, and an unreadable `gh` read
  exits 2 — a tool that cannot read never reports a pass. Read-only: it comments nothing and
  dispatches nothing.
- **Wired where the repo wires alarms**: called from `queued-alarm.yml` (twice hourly), the
  pipeline that already exists for "something is stuck" — the decision lives in the script, the
  target is the only entry point (rules 6d/6m).
- **Tests**: the measured 3–6 h sequence as a fixture (a 4.8 h old delivery is stale, 5 slots
  missed, gaps 3.3/3.87/4.87/5.93 h), "no delivery is a verdict", "a red last delivery is
  named", the three CLI exit codes against a stub `gh`, and the wiring (two slots, the target,
  the workflow step after its checkout).

## Impact

`.github/workflows/issue-bot.yml`, `.github/workflows/queued-alarm.yml`, `Makefile`
(`sweep-alarm`), `scripts/sweep_alarm.py`, `tests/test_sweep_alarm.py`, `ARCHITECTURE.md` (§3 row
+ the §10 inventory), `OPENSPEC.md`. No new job, image or permission: `queued-alarm.yml` already
holds `actions: read` and a checkout.

## Not covered

- **`AGENTS.md` §6b/§8 rows** for the second slot and the alarm — a protected file, whose write is
  refused in this environment; tracked on #494 together with the rows #496 owes (rule 3c).
- **Renaming the implementer's branch** `ci/data-gap-<n>-<slug>` → `ci/issue-<n>-<slug>`. It is
  label-agnostic now that `tech-debt` is queued, but `pr_closure` matches `^ci/data-gap-<n>-` and
  a rename without extending that matcher would refuse every implementer PR; filed separately.
- **Making GitHub deliver on time.** A second slot plus an alarm makes a drop visible and
  survivable; it does not stop the drop.
