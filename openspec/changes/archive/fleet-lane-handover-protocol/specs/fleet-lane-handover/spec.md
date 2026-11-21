# fleet-lane-handover

## ADDED Requirements

### Requirement: every lane hands over on the issue thread

Every tll lane MUST post a signed handover comment on the issue's OWN thread when
it finishes or stops work, naming the ONE lane that owns the next step:

`BOT <lane> · done #<id> · handover <next-lane|owner|none> · <the one next action>`

`handover` names `tll-planner` (re-triage/dispatch), `tll-implementer` (write),
`tll-tester` (verdict) or `owner` (a human decision); `none` is used only when
the issue is fully done. Progress comments are the record: a lane that works an
issue across sessions posts state at each step, not only the opening claim. A lane
never works outside its remit — it files or comments and hands over.

#### Scenario: every SOUL.md carries the handover shape

- **Given** the seven `agents/tll-*/SOUL.md` files in the tree
- **When** the handover protocol test reads each `SOUL.md`
- **Then** each one carries the signed `· done #<id> · handover <next-lane|owner|none>`
  comment shape, the progress-comment rule and the remit rule
- **Test:** tests/test_fleet_handover_protocol.py::main

#### Scenario: the planner skill carries the dispatch/handover shape

- **Given** `agents/tll-planner/skills/tll-planner/SKILL.md`
- **When** the handover protocol test reads the planner skill
- **Then** it carries the `· dispatch #<id> · lane <lane> · base <sha>` dispatch
  shape and the standing board rule
- **Test:** tests/test_fleet_handover_protocol.py::main
