# The data-gap filing lands on an issue the bots can actually see

**Issue:** [#277](https://github.com/andyholst/trending-local-llms/issues/277)
**Capability:** `data-gap-filing` (the post-refresh analysis that files ONE issue holding the gap set)

## Why

Measured on `master` `13c99fa` while live-testing each bot pipeline:

- refresh-bot run **38802740520** (aggregate job) died at
  `make data-gap-issue` with
  `issue 266 does not carry \`data-gap-analysis\` after re-applying it — the bot chain
  triggers on that label, so this filing would be invisible`.
- Issue **#266** exists, is authored by the owner PAT, and carries **no label**
  (`gh issue view 266 --json labels` → `[]`). The same-second timeline shows a
  create that returned 0 — the shape issue #161 recorded once already.
- Both downstream queues were therefore EMPTY on every run:

  ```
  $ make issue-queue
  [issue-queue] repo=andyholst/trending-local-llms now=2026-10-16T00:45:51Z gap=3h candidates=0 windows_open=0
  $ make review-issue-pick
  action=none
  reason=all-deferred
  ```

  so `issue-bot`'s `implement` job and `issue-review-bot`'s `review` job were
  **skipped** (runs 38831429078, 38831362736) — green pipelines doing nothing.
- The same defect re-filed one gap set twice (#246 at 11:12, #266 at 21:10): the
  dedup search filters by `--label`, so an unlabelled filing is invisible to it
  as well.
- The step is `continue-on-error: true` (by design: the analysis must never fail
  the data PR), so the failure was reported nowhere.

Root cause: the step passed `GH_TOKEN: ${{ secrets.FIXBOT_DISPATCH_TOKEN }}`. That
PAT is deliberately scoped Actions/Contents/Pull-requests/Workflows with **no
Issues scope** — AGENTS.md §6b states that issue reads, comments and labels use
the default `github.token` with `permissions: issues: write`, and #124 already
measured this PAT being refused for a comment. Two things follow: the label is
dropped on create (GitHub ignores a label it does not know instead of refusing
the whole call), and the repair path (`gh issue edit --add-label`) cannot fix it.
`ensure_label`'s own message hid `gh`'s diagnosis, so the failure named no cause.

## What Changes

- `refresh-bot.yml`'s `aggregate` job declares `permissions: issues: write` (plus
  the `contents`/`pull-requests` the job already needs) and files the gap issue
  with the **default** token.
- `code-review-bot.yml`'s issue-filing step moves to the default token too — the
  same class: a step that WRITES an issue must use a token that can write issues.
  (Its scan step keeps the PAT: `gh secret list` needs admin, which is issue #278's
  own subject.)
- `scripts/data_gap_analysis.py` creates the label when the repo does not have it
  yet (`gh label list` → `gh label create`) before it relies on it, and both the
  create-verification and the edit-verification now quote `gh`'s own stderr
  instead of only the conclusion.
- Tests, in the same change (rule 6b/6c): a **class** guard in
  `tests/test_workflows.py` (`test_issue_writes_use_the_default_token`) fails on
  ANY step in ANY workflow that writes an issue without the token that can write
  one, or in a job that does not declare `issues: write`; and
  `tests/test_data_gap_analysis.py` gains
  `test_the_filer_creates_the_label_the_bots_trigger_on` plus a stderr assertion
  on the loud path.
- `AGENTS.md` §4's data-gap bullet and §6b's token paragraph say which token files
  the gap issue and why (protected file — review-required, rule 3c).

## Not covered

- **The exact PAT refusal is not reproduced locally** (no read access to the PAT
  from a workstation), so the fix is verified by construction plus a live run:
  the label-first behaviour is now proven by test, and the token is the one that
  performs issue writes elsewhere successfully. The next refresh-bot run is the
  end-to-end confirmation, and it is reported on #277.
- The `data-gap-analysis` label itself: the two issues filed before the fix (#246,
  #266) were re-labelled by hand; nothing here converges historical issues.
- `code-review-bot`'s secrets check being SKIPPED for lack of admin (#278).
