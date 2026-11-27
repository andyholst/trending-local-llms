# Host Hermes fleet

The triage planner is `tll-planner`. The owner starts the fleet on the host with `hermes -p tll-planner chat`. The planner checks that the data sync is honest and dispatches the other lanes with an issue comment. It does not implement and it does not merge.

For how the fleet works together end to end — the issue-thread board, signed claim/dispatch/handover formats, each lane's responsibility, four instances per delegable lane and the weekly cadence-not-timer pass — see the canonical [fleet collaboration doc](../docs/fleet-collaboration.md).

There is no `trending-local-llm-issue-implementer` profile. Do not recreate it.

| Profile | Lane |
| --- | --- |
| `tll-planner` | Triage. Data-sync check and dispatch. |
| `tll-architect` | Proposes a clearer aggregation. Does not implement. |
| `tll-security` | Watches code and container images. Files the finding. |
| `tll-reviewer` | Finds gaps in the data and the logic. Files the gap. |
| `tll-tester` | Tests each pull request against the issue acceptance criteria. Reports the evidence. |
| `tll-pr-rebase` | Rebases a conflicting pull request onto master. Does not merge. |
| `tll-implementer` | Lands one dispatched issue, including a red pull request the planner names. |
| `tll-docs` | Keeps the repo's prose in step with its code: contract docs, the store architecture page, doc gaps left by delivered PRs. |

No profile in this fleet has a Hermes cron. Existing GitHub Actions schedules stay as they are. Each lane's `SOUL.md` and `skills/<profile>/SKILL.md` in this tree are the copy of the host profile.
