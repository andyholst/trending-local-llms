# Weekly lane-maintenance pass — cadence, not a timer

This is the runnable checklist for the weekly maintenance pass described in §6 of the canonical
collaboration document, [`docs/fleet-collaboration.md`](fleet-collaboration.md). That document owns
*how the fleet works together*; this one owns *the pass that keeps it honest*. Issue #1834 defines
the pass. The planner executes it; no other lane owns it as a delivery.

## Cadence: the owner starts it, nothing schedules it

The pass has a **weekly cadence**: the planner performs it when the owner starts the fleet, on a
predictable cadence rather than whenever drift happens to be noticed. It is a checklist executed
by a running planner session — **a cadence, not a timer**:

- The owner starts the planner on the host with `hermes -p tll-planner chat`. **No Hermes cron** exists for this fleet: do not create a `cron/jobs.json` entry and do not register a gateway job.
- There is **no new GitHub Actions `schedule:`** for the fleet. Do not add a workflow that runs
  these lanes, and do not edit an existing schedule. The only scheduled pipeline in the tree is the data gatherer; this pass is not that pipeline.
- The pass never dispatches a CI pipeline, pushes `master`, or merges a PR. It reports drift and
  files small issues; `tll-implementer` writes the tree only when the planner names an issue.

## The checklist

Start `hermes -p tll-planner chat` on the host, then work these five steps in order. Copy the list
into the pass record and tick each line as it is done.

- [ ] **1. Fetch, re-read and run the per-host sync check.** From THIS host, run:

      git fetch origin master
      make fleet-host-sync-check BASE=origin/master

      Record the fetched `origin/master` sha. Re-read every lane's host `SOUL.md` and
      `skills/<lane>/SKILL.md` and the in-tree `agents/tll-*/SOUL.md`, `skills/tll-*/SKILL.md` and
      `AGENTS.md` copies they are compared against. The check is run from each host's own
      planner against the freshly fetched repo, not from CI on a timer. Any drift is reported and
      filed as a small `enhancement` issue (step 5) — fix it through `tll-implementer` and the
      in-tree mirror refresh (tracked #696). **Never wipe Hermes runtime stamps and never
      byte-copy a host-ahead note into `master` to force the check green**: host-ahead forward work
      is real work and is reconciled through the write lane, not overwritten.

- [ ] **2. Verify the roster.** Confirm four instances of each delegable lane are present on the
      gateway — `<lane>`, `<lane>-2`, `<lane>-3`, `<lane>-4` — plus one `tll-planner` on each
      machine. Run `hermes -p <name> doctor` for each instance. Report every missing or
      unhealthy instance; do not silently recreate a profile or grant access.

- [ ] **3. Verify the collaboration doc still matches the live protocols.** Read
      `docs/fleet-collaboration.md` against the current lane `SOUL.md` / `SKILL.md` handover
      rules. If the doc has gone stale, file a small `enhancement` issue for the drift; do not
      rewrite the doc on the strength of an unmerged branch.

- [ ] **4. Re-read the board and post the board note.** Read the open fleet issues and PRs, then
      post the signed board note naming the in-progress lanes and the PRs awaiting review. This
      is the state the other hosts and the next pass start from.

- [ ] **5. Record the pass.** Post a signed comment on issue #1834 with: the base sha, the checks
      run (including the exact host-sync command and its verdict), the drift found, issues filed
      and the owner of the next pass. A pass with no comment is a pass nobody can audit.

## What the pass does not do

It does not schedule anything, patch a lane, edit `data/`, edit a workflow, edit the generated
README tables, or edit the root `AGENTS.md`. It does not force a red host-sync check green by
overwriting host state. It hands every fix to `tll-implementer` through a filed issue and a signed
planner dispatch, and it leaves the existing data-sync schedules exactly as they are.
