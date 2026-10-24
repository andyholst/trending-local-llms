# Proposal: pr-body-composer

Issue: #287 — `tech-debt: The PR body is assembled by inline workflow shell, so its text is not covered by any target`

**Capability:** `pr-body-composition`

## Why

`.github/workflows/issue-bot.yml:444` built the implementer's PR body with
`cat > pr-body.md <<'BODY'` and appended the closing keyword at line 463 with
`printf '\ncloses #%s\n' "$ISSUE"`. That body is the artifact that DECIDES whether the
issue closes on merge (AGENTS.md rule 6e) — GitHub parses exactly this text — and it was
the only PR artifact in the pipeline with no target behind it:

- no test could RUN it. The text lives inside a YAML block, so the only possible
  assertion is a substring one, which is the weakness #289 removed from the closure
  check (a marker word, not the claim). Nothing proved the body the workflow really
  hands to `gh pr create --body-file` closes the issue its branch implements.
- `make pr-closure` could only read a body a shell had already written; there is no
  seam to render the same body locally and compare.
- the wording was frozen to one kind of issue: it said "the filed data-gap issue from
  the post-refresh analysis" even when the implementer was working a `tech-debt` issue
  (the sweep takes both labels, rule 6j), because a heredoc cannot branch on the issue.

## What Changes

- **`scripts/pr_body.py`** — the ONE composer. `render(issue, branch)` returns the whole
  body; `closing_line(issue)` is the single `Closes #<n>` claim; `main()` takes
  `--issue <n> [--branch <b>]` and writes the body to stdout. It imports
  `pr_closure.implemented_issue()` — the pipeline's own derivation of "which issue does
  this branch implement" — and REFUSES (exit 2, empty stdout, reason on stderr) when the
  branch encodes a different issue, because a body that closes the wrong issue is exactly
  what `make pr-closure` exists to catch and it must never be produced in the first place.
- **`Makefile`** — `make pr-body ISSUE=<n> [BRANCH=<branch>]` prints the body. Both recipe
  lines are `@`-silenced: the workflow redirects this target's stdout into `pr-body.md`,
  so an echoed command line must never become part of the PR body.
- **`.github/workflows/issue-bot.yml`** — the "Open the PR" step calls
  `make --no-print-directory pr-body ISSUE="$ISSUE" BRANCH="$BRANCH" > pr-body.md` and
  hands that file to `gh pr create --body-file`. No heredoc, no `printf`. The
  `--no-print-directory` flag keeps make's sub-make banner out of the body.
- **`tests/test_pr_body.py`** — drives the REAL composer, the REAL make recipe and the
  SHIPPED workflow step (only `gh`, an external system, stubbed — rule 6m), then hands the
  body the step produced to `scripts/pr_closure.py`, so the composer and the guard cannot
  drift. It also locks the refusal (mismatched branch) and proves the closure parser still
  refuses the two real failure shapes.
- **`tests/test_workflows.py`** — `_run_issue_pr_step()` executes the step in the checkout
  so the real `make pr-body` recipe runs; `pr-body.md` is gitignored and removed after.
- **`ARCHITECTURE.md`**, **AGENTS.md §8** and the regenerated **`OPENSPEC.md`**.

## Impact

The implementer's PR body can now be rendered locally (`make pr-body ISSUE=… BRANCH=…`),
is closed by exactly the issue it names, and the wording no longer claims every change is
a data-gap one. `make pr-body` is called by the workflow that owns the artifact, so it is
not a target nothing runs (rule 6m), and its script is reached only through that target
(rules 6d/6m). No data, no README, no schema, no behaviour change to the pipeline's gates.

## Not covered

- **The PR TITLE is still inline** in the same step (`--title "feat(data-gap): implement
  the #$ISSUE gap analysis item"`). It is not the artifact GitHub parses for the closure
  and this issue names the BODY, so the title is left alone and filed as its own finding
  (rule 6g) rather than widened into here.
- **The refresh PR body** (`refresh-bot.yml`) and the **architecture PR body**
  (`architecture-bot.yml`) are also inline `run:` text, but neither implements an issue and
  neither carries a closing keyword this change's composer would produce. They are their
  own finding, not this change.
- No change to the body's *policy* statements (spec-tracked / additive-only / analysis
  ships issues / auto-merge): the same sentences are reproduced by the composer.
