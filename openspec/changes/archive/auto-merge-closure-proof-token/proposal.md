# Proposal: auto-merge-closure-proof-token

Issue: #1677
PR: #1680

## Why

`qa-validate`'s `auto-merge` job squashes a green PR and then runs `make verify-closure`
to prove the issue the body claimed actually closed. That proof ran INSIDE the squash
step, whose step-env is `GH_TOKEN: ${{ secrets.FIXBOT_DISPATCH_TOKEN }}` — the owner PAT,
which declares Actions / Contents / Pull-requests / Workflows and NO Issues scope
(AGENTS.md §6b).

The proof needs the Issues scope: GitHub's `closingIssuesReferences` never carries a
`state` field (measured on PRs #1658 and #1670), so `scripts/verify_closure.py::
open_references` always falls through to `gh issue view <n> --json state`. Under the PAT
that call answers `HTTP 401: Bad credentials`, so a run whose squash had ALREADY landed
concluded `failure`:

```text
run 45512193546  head b77307ca  [verify-closure] FAIL: gh issue view 1668 --json state
                      HTTP 401: Bad credentials (https://api.github.com/graphql)
run 45477830451               same step, exit 1
success contrast: run 45507820535 auto-merge=success
```

Nothing was blocked — issue #1668 closed two seconds after the merge — but a concluded-
`failure` run of a main pipeline is what the §6r/#1376 failure filer acts on, so a
completed delivery reads as a red pipeline.

## What Changes

- Run the closure proof in its OWN `auto-merge` step, immediately after the squash step
  and under the same `if:` gate, carrying `GH_TOKEN: ${{ github.token }}` — the default
  token, which has the Issues scope the read needs (the do-not-merge label step already
  proves that token reaches the issues API).
- Declare `issues: read` and `pull-requests: read` on the `auto-merge` job so the proof's
  token can read BOTH the closing references (`gh pr view`) and the issue states
  (`gh issue view`).
- Leave the squash path byte-identical: same `gh pr merge --squash --delete-branch
  --match-head-commit` command, same owner PAT, same `--subject`/`--body-file`.
- Add a RED-first guard (`tests/test_verify_closure.py`) that refuses a closure proof
  running under the owner PAT or without the two read scopes, and pins the squash's PAT
  path and flags.
- Declare the owed `AGENTS.md` §8 guard row for that test (rule 3c: the rulebook is
  protected and a headless leg cannot write it) in `findings/1677.md`, with the matching
  `- [~] … blocked:` task box.

## Impact

No data format, contract, image or pipeline-trigger change. The squash command, its
credential and its gates are untouched; only the post-squash verification read moves to
a credential that can perform it. A merged, closed, green master stops reporting a red
`auto-merge` run.

## Not covered

- No change to `scripts/verify_closure.py` itself: the script is credential-agnostic and
  correctly fails loudly when `gh` cannot answer. Making its failure name the credential
  it used is left as a separate finding.
- No change to any other caller of `make verify-closure` (it is host-side too).
- No new schedule, no merge, no `master` push.
