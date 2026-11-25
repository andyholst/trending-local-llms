# Proposal: live-pr-body-preflight-1710

Issue: #1710

## Why

Rule 6e makes the PR body the artifact that DECIDES which issue a squash closes, and #1704
added a merge-time hold so a body the gate refuses can no longer be squashed. The AUTHORING
path is still advisory: §7b tells a lane to run
`python3 scripts/pr_body.py --check-body-file <f> --branch <b>` before a push, but nothing
mechanically refuses a claim or a handover of a branch whose live body fails that gate.
Measured on the artifact that exposed the class: PR #1696 squashed as `8184e59d` with a body
that this exact command refuses offline:

```text
[pr-message-check] REFUSED: fix/owed-row-prose-quotes-1690 — missing required section(s):
  ## Why, ## What, ## How, ## Benefits, ## Technical Solution
exit 1
```

A lane that never runs the check keeps producing held PRs and human nudges; the hold is the
correct backstop, not the fix for the class.

## What Changes

1. `scripts/pr_body.py` gains ONE preflight seam, `--check-live-pr <n>`: it reads the PR's own
   `body` and `headRefName` with a single `gh pr view` call (both fields already in the
   `gh_json_fields` contract) and feeds the text through the SAME `_problems_for` parser the
   webhook gate uses — no second message-pattern view. A failed or unreadable gh read RAISES,
   so a preflight that cannot read the artifact is loud (exit 2), never a silent clean.
2. `make pr-message-check` accepts a third input shape, `PR=<n>`, which forwards to that seam.
   The target is already called by `pr-closure.yml` and by `qa-validate`'s merge hold, so no
   workflow changes and no new make target are needed — the preflight is reachable from a
   lane's own push/handover path through the Makefile (rule 6m).
3. `tests/test_pr_message.py` gains a guard driving the REAL CLI and the REAL make target with
   a stub `gh` on PATH (the only stand-in is the external CLI): a conforming live body passes
   with exactly one recorded gh field set; a body missing a section is refused and named; a
   failed gh read exits 2; and both verdicts hold through `make pr-message-check PR=<n>`.
4. `ARCHITECTURE.md`'s hand-maintained rows for `pr-message-check` and `scripts/pr_body.py`
   describe the live-PR input.

## Impact

- `scripts/pr_body.py`, `Makefile`, `tests/test_pr_message.py`, `ARCHITECTURE.md`.
- No workflow, no schedule, no LLM call, no data-store or contract change.
- No rulebook edit: the lane-side preflight is reachable mechanically; the §7b prose already
  asks lanes to check the body before a push.

## Not covered

- Installing a git `pre-push` hook in each host worktree: host-local state is not versioned
  and cannot be gated by CI.
- Rewording the merge-time hold (#1704): a held PR is the correct backstop for a body that
  slips past a lane; this change reduces how often that backstop fires.
- Forcing the five-section shape on refresh/architecture bodies: they implement no issue and
  stay exempt, exactly as in the CI gate.
