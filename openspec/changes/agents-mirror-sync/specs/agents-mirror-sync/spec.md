# agents-mirror-sync

## ADDED Requirements

### Requirement: the in-tree fleet mirror matches the current host profiles, including the two new lanes

Each fleet lane's `agents/<profile>/SOUL.md` and `agents/<profile>/skills/<profile>/SKILL.md`
are the in-tree records of the host Hermes profile for that lane. They MUST match the
CURRENT host profile content (post-#690 delivery rules and post-#703 Standing
rules / CLAIM-READ-REPORT behavior), not a stale pre-lift copy. All seven lane
directories — `tll-planner`, `tll-architect`, `tll-tester`, `tll-reviewer`,
`tll-security`, `tll-implementer`, `tll-pr-rebase` — carry the current host SOUL + skill
(after the repo-mandated trailing-newline normalization). The README fleet table lists
all seven lanes, including the two added rows `tll-tester` (tests PRs against the issue
acceptance criteria and reports evidence) and `tll-pr-rebase` (rebases a conflicting PR
onto master, does not merge). The change is docs-only.

WHEN a mirror resync PR lands,
THEN every `agents/<profile>/SOUL.md` + `skills/<profile>/SKILL.md` equals that lane's
current host file (normalized newline) and the README fleet table lists all seven lanes.

#### Scenario: all seven lane directories carry the current host content

- **Given** the current host SOUL + skill for each of the seven lanes and the committed pre-lift mirror
- **When** those files are re-copied into `agents/<profile>/` and committed
- **Then** each `agents/<profile>/SOUL.md` and `skills/<profile>/SKILL.md` byte-matches its host source modulo the repo-mandated final newline
- **Test:** none (docs mirror; verified by tree write + `git` diff during authoring)

#### Scenario: the two new lanes are added to the fleet

- **Given** the fleet gained `tll-tester` and `tll-pr-rebase`
- **When** the mirror resync lands
- **Then** `agents/tll-tester/` and `agents/tll-pr-rebase/` exist with their current host SOUL + skill, and the README fleet table lists both with their lane roles
- **Test:** none (docs; README rows + directories verified in the PR diff)

#### Scenario: the mirror stays docs-only

- **Given** the change is a mirror resync
- **When** it lands
- **Then** no code, schema, data, workflow, cron, or GitHub Actions schedule file changes (diff is confined to `agents/`, `OPENSPEC.md`, and this change dir)
- **Test:** none (diff scope asserted in the PR)
