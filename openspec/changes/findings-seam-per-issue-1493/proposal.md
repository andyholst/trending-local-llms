# Proposal: findings-seam-per-issue-1493

Issue: #1493

## Why

`findings.md` was tracked at the repo root and every implementation run APPENDED its
own `## <title>` section to it. ONE shared append point means EVERY landing
implementation PR invalidates the merge commit of EVERY other open one: measured on
this lane's PR #1488 inside a single run, master `198901c7` → `9c15447` → `6924f02`
each appended a section and each move answered
`CONFLICT (content): Merge conflict in findings.md`, and GitHub's `auto-merge` refused
twice (`Pull request #1488 is not mergeable: the merge commit cannot be cleanly
created`). A test-only change took three rebase + full-validate rounds (~70 min of CI)
to land, and the same class silently red'ed PR #1491 later that hour.

Reproduced RED-first on a scratch clone of this base: two sibling branches that each
append a section to the root file do not merge (`git merge` exits non-zero naming
`findings.md`), while the same two branches writing `findings/<issue>.md` merge cleanly
in both orders.

## What Changes

- The analysis artifact becomes PER ISSUE: `findings/<issue>.md`. `scripts/file_findings.py`
  resolves it through ONE order — an explicit `--path` wins; else `--issue`; else the
  issue the branch encodes (`pr_closure.implemented_issue`, the ONE parser); else the
  legacy root file, so an old caller still reads what it wrote.
- The shared root file leaves the tracked tree and moves to `findings/history.md`, so the
  fleet's finding record stays readable while nothing can append to it; a stray root
  `findings.md` is gitignored (never committed) but stays OFF the bot working-file list,
  because nothing writes it anymore.
- `make findings-check` forwards `ISSUE=` so the bot paths and `REQUIRE_FINDINGS`' fix
  loop resolve the per-issue file; `qa-validate`'s shape-aware gate already passes the
  branch, which encodes the same issue. The implementer/reviewer skills, prompts and the
  pipeline comments name the new path.
- New guard suite `tests/test_findings_seam.py`: the REAL resolver (distinct issues →
  distinct files, branch → issue), the REAL CLI on a per-issue file, a scratch-repo proof
  that two siblings touching different issues merge cleanly in BOTH orders, the RED-first
  premise that the old shared append point conflicts, and the tree facts (root untracked,
  history present, stray ignored).

## Impact

Non-breaking and additive. No schema, contract, data shape, table, image or schedule
change; `findings-check-for-pr` keeps its shape predicate and its exempt shapes, and the
plain gate is byte-compatible for every existing caller. Two sibling implementation PRs
now touch disjoint files, so neither invalidates the other's merge commit — the
queue-wide red class (#1359) loses its commonest trigger. Existing findings keep their
history in-tree; future findings accumulate one file per issue, which is also easier to
read than one ever-growing root file.

## Not covered

- No merge-driver / union-merge change: the file leaves the diff entirely instead of
  asking GitHub to union it.
- No AGENTS.md write. The §6g sentence still names the pre-#1493 root path and the §8
  guard row for the new suite is owed; a headless leg may not write that protected file
  (rule 3c), so both are declared as a blocked task box plus an owed-row finding, never
  edited here.
- No change to `file_findings`' dedup, label, origin or owed-row rendering; no model
  call, no CI dispatch, no merge, no `master` push, no collaborator grant.
