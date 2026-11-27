# How the tll fleet works together

This is the canonical, reader-facing description of the host fleet: who starts it, where its
state lives, what each lane owns, and how a work item moves from a claim to a reviewed PR.
The short profile table in [`agents/README.md`](../agents/README.md) points here; the
normative rulebook is `AGENTS.md` §7b (lifecycle, delegation, divergence gate) and §8 (the
regression guards). When they disagree, the rulebook wins — file the drift, do not silently
edit this document to match an unmerged branch.

The fleet is started by the **owner**, on a host. There is no Hermes cron in the fleet and no
new GitHub Actions `schedule:` for it: the single scheduled pipeline in the repository is the
data gatherer, and the fleet's cadence is work the planner performs when the owner starts it,
not a timer. An agent never dispatches a CI pipeline, merges a PR, pushes the base branch or
grants collaborator/repository access.

## 1. The owner starts the fleet

```
hermes -p tll-planner chat
```

The planner is the single dispatcher and stays ONE instance. It checks the fetched base, reads
the issue board, and dispatches lanes with signed comments on the **issue thread**. It does not
implement, does not push a branch and does not merge. Every other lane is started by a planner
dispatch naming the issue, the lane, the base sha, the done criteria and the handover target.
Before it spawns a lane the planner runs `make dispatch-check ISSUE=<n>`: a CLOSED issue, an
already-merged bound PR, a more than three active lanes, an overlapping `--claim` path or a
newer working claim held on another host is refused (exit 1) or undecidable (exit 2).

## 2. The board is each issue's own thread

A pull request is a delivery artifact, never a handover. The ONE shared board across machines
is the **issue's own comment thread**; a PR comment mirrors it but transfers no ownership.
Every work comment is signed with the lane and the machine id:

```
BOT <lane> (host <user>@<hostname>) · <verb> #<id> · …
```

`<user>@<hostname>` is the machine id only (`asimov@omarchy`, `asimov@mac`). Never a full host
name, LocalHostName or hardware name, and never a GitHub login as a machine identity: two hosts
may comment under the same bot account. A reader takes the **newest signed comment** on the
thread as state — an older handover is the state that was read before any action.

## 3. Lane roster and responsibility

| Lane | Owns | Never |
| --- | --- | --- |
| `tll-planner` | Triage, dispatch, the weekly maintenance pass, reading the newest comments to delegate | Implements, pushes a branch, merges |
| `tll-implementer` | The ONLY tree writer: one named issue in its own worktree/branch/PR | Works two issues in one branch, edits another lane's branch |
| `tll-architect` | Designs and files findings; keeps wiki/docs claims fresh | Edits code as a delivery |
| `tll-reviewer` | Finds gaps, reviews PRs, posts verdicts on the issue | Rewrites an issue body during an implementer window |
| `tll-tester` | Verdicts backed by real runs at the exact head | Reports a green expectation instead of a green gate |
| `tll-security` | Finding scans and container-image scans | Patches what it finds |
| `tll-docs` | Prose and contract docs, the store architecture page, doc gaps | Edits `data/`, a workflow or the generated README tables |
| `tll-pr-rebase` | Rebases a conflicting bot PR onto the fetched base | Merges, or rewrites a human-owned branch |

Every lane stays inside its remit. A gap it notices becomes a finding filed as its own issue and
handed over — never a fix smuggled into the change that found it.

## 4. Lifecycle of a work item

1. **Claim before edit**, on the issue: `BOT <lane> · working on #<id> · branch <ref|none> · blocked on <x|none> · next <y>`. A claim includes the machine id and the fetched base sha. Wait and re-read: the claim is won by being the newest after the settle window (`CLAIM_SETTLE_SECONDS`, 180 s), not by being first. A newer claim from another host wins — stop, hand the prepared work over on the thread, and do not open a competing PR.
2. **Dispatch** from the planner: `BOT tll-planner · dispatch #<id> · lane <lane> · base <sha> · done <criteria> · handover <next> · answering <comment-id>`. A dispatch with no handover target is not a dispatch.
3. **Work**: one issue, one worktree, one branch. The implementer changes locally and pushes; CI verifies. Only the fast offline checks run on the host before the push — the full `make validate`, `make test` and `make live-smoke` are CI-only. Never pre-run the containerised suite on the host to prove a green you have not pushed.
4. **PR delivery** on the issue: `BOT <lane> · pr #<id> · PR #<n> · base <sha> · handover tll-reviewer · <next>`. PRs open READY, never draft, with exactly one closing keyword bound to their issue. The title carries the change and `Closes #<id>`, and the body repeats its own `Closes #<id>` line — never title-only, never body-only — so the squash closes the issue. Every PR is a small, single-purpose, non-breaking delivery for one issue (#690): no schema, contract, API, table or data-shape break, no unrelated churn, no dead code — split a breaking change or flag the conflict on the issue before writing any code.
5. **Review** on the same issue: `BOT <lane> · reviewing #<id> · PR #<n> · handover <tll-implementer|owner>`. A red check hands back to the implementer; a human decision hands to the owner.
6. **Close** the loop: `BOT <lane> · done #<id> · handover <...>`. `handover none` is posted only when the issue is fully done; it is not a handover to another lane. Cleanup verifies the issue's state back and that the OpenSpec change is archived.
7. **While waiting** for a test or CI gate, post ONE status note with the machine stamp and doing / waiting-for / can-help-with fields, then continue with the next actionable item. Never idle-wait or poll a background run to fill time; the next cron tick is a work boundary, not a status update.

## 5. Four instances per delegable lane

The fleet scales to **four instances of each delegable lane**: the template `<lane>` plus
`<lane>-2`, `<lane>-3` and `<lane>-4` on the gateway. The planner stays a single instance.
All instances of a lane obey the same remit and the same signed-comment formats — a human must
not be able to tell which clone picked up an item.

Instances self-claim from the issue comments: read the full thread, take the newest state, and
only a signed handover moves an item between lanes. `make dispatch-check` enforces the active
lane ceiling (default 3) and refuses overlapping claims; the claim-twice race guard (post the
claim, wait, re-read) stops two hosts or two clones from writing one issue. One worktree and one
branch per claimed issue, with a lease-checked push. On a master merge, re-fetch, rebase your
own open PRs and regenerate `OPENSPEC.md` on each head.

## 6. Weekly maintenance pass — cadence, not a timer

The owner starts the pass on the planner; it is a checklist the planner executes, never a cron
and never a new Actions `schedule:`. The runnable checklist is
[`docs/weekly-lane-maintenance.md`](weekly-lane-maintenance.md) (issue #1834). Each pass:

1. `git fetch origin master`, record the sha, re-read every lane's host `SOUL.md` and
   `skills/<lane>/SKILL.md` plus the in-tree `agents/` mirrors, and run
   `make fleet-host-sync-check BASE=origin/master` **from this host**. Report the drift; file a
   small `enhancement` issue for it and fix through `tll-implementer` and the in-tree mirrors —
   never wipe Hermes runtime stamps or byte-copy a host-ahead note to force green.
2. Verify the roster: four instances of every delegable lane plus the single planner; report
   missing or unhealthy instances.
3. Verify that this collaboration document still matches the live protocols; file a small
   issue for any drift.
4. Re-read open fleet issues and PRs; post the board note with in-progress lanes and PRs
   awaiting review.
5. Record the pass with a signed comment on the companion issue: base sha, checks run, drift
   found, issues filed, next pass owner.

The pass keeps the mirrors and the roster honest across hosts without a timer: drift is caught
on a predictable cadence, and the protocol stays followable as the fleet grows.
