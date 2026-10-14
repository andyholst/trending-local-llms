# Proposal: agent-openspec-and-debt-issues

Issue: #172

## Why

Agent work in this repo is tracked only by the GitHub issue it closes. Nothing
in the repository records *what was decided*, *which behaviour the change
pins*, or *what was deliberately not done* — the data-gap analysis files issues
about the data, but a change to the pipeline, the contracts or the search legs
leaves no durable trace beyond a commit message. llgenie solved the same
problem: every change is an OpenSpec change (`proposal.md` + a capability spec
in Given/When/Then + a task checklist), the checklist is validated before the
PR merges, and the analysis every change forces — real gaps and technical debt —
is filed as its OWN issue instead of being folded into the change.

Measured on this repo today: #164 (a refresh PR) had to be rebased twice and its
intent lived only in the PR body; #163 sat invisible because a filing detail had
no owner; nothing lists the changes this repository has made. And a change that
touches the crawler/ingest — the part the product actually is — leaves whatever
else it noticed unsaid.

## What Changes

- **OpenSpec tracking** (ported from llgenie, kept Docker-only — no host npm
  fallback, matching this repo's "one code path" rule):
  `openspec/{config.yaml,Dockerfile,specs/,changes/}` plus the Makefile targets
  `openspec-image`, `openspec-new`, `openspec-validate`, `openspec-status`,
  `openspec-archive`, `openspec-shell`, `openspec-tasks-check`,
  `openspec-index`, `openspec-index-check`, `openspec-check`.
- **The CLI image is published like the others**: `scripts/ensure_image.py`
  grows an `openspec` kind (`ghcr.io/<owner>/trending-local-llms-openspec:openspec-<sha12>`
  from `openspec/Dockerfile`), so `make openspec-*` pulls the published tag or
  builds it — the same decision the base/test images already use (issue #141).
- **`OPENSPEC.md` — the root index.** `scripts/openspec_index.py` renders every
  change directory (active and archived) with its `Issue:`/`PR:` refs, capability
  specs and `ticked/total` tasks into `OPENSPEC.md`; `--check` fails when the file
  is stale, when a change on disk has no row, or when a row no longer matches a
  change. `make openspec-index` regenerates it.
- **`make openspec-check`** = `openspec validate --changes` + no unticked `- [ ]`
  task (`scripts/check_openspec_tasks.py`) + the index check. It runs in
  `qa-validate`'s `validate` job and is what the implementer must pass before it
  pushes.
- **Findings become issues.** `scripts/file_findings.py` reads `findings.md` (the
  implementer's analysis: one `## <title>` section per finding with Evidence /
  Why / Done when, or `- none`), fails loudly when the file is missing or a
  finding is vague (`make findings-check`), and files ONE issue per finding
  (`make file-findings`, label `tech-debt`, dedup by an invisible signature,
  linked back to the issue/PR). The implementer prompt requires it; the bot runs
  it only when the fix loop went green.
- **`AGENTS.md`** gains the durable rules — *spec-tracked change*, *the index*,
  *analysis ships issues, not code* — plus the §6b pipeline text and the §8 guard
  rows for the new stages.
- **`README.md`** documents the new targets and the index.

## Impact

`Makefile`, `scripts/{check_openspec_tasks,openspec_index,file_findings,ensure_image}.py`,
`openspec/**`, `OPENSPEC.md`, `.gitignore`,
`.github/workflows/{qa-validate,refresh-bot,issue-bot}.yml`,
`tests/{test_check_openspec_tasks,test_openspec_index,test_file_findings}.py`,
`tests/test_workflows.py`, `tests/test_ensure_image.py`, `AGENTS.md`, `README.md`.

Data is untouched: no change to `data/**`, no contract change, no search change.

## Not covered

- Machine-enforcing the `- **Test:**` line on every scenario (the rule is stated
  and followed here; a validator for it is its own issue).
- Archiving anything into `openspec/changes/archive/` — the index reads that tree,
  nothing needs archiving yet.
- The data-gap chain itself (`make data-gaps`, `make data-gap-issue`) is
  unchanged; `file-findings` is the code-facing second channel.
