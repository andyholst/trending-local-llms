# The implementer reads the whole thread and decides

**Issue:** [#210](https://github.com/andyholst/trending-local-llms/issues/210)
**Capability:** `issue-triage`

## Why

The comment thread is part of the specification, and the two bots disagreed about
it: the reviewer was told to *"review the WHOLE thread, not just the body"*, while
the implementer's input was built from the title and body only —

```bash
gh api "repos/$REPO/issues/$ISSUE" --jq '.title, "", .body' > issue.md
```

So an issue whose fifth comment narrowed the request was implemented wrongly, an
issue a merged PR had already satisfied burned one of the run's worth of budget, and
an ambiguous issue got a confident guess — because the only outcomes available were
"implement" or "fail". There was no way for the bot to say *this needs refinement*
or *this is obsolete, here is the proof*.

llgenie closed this loop (#261, merged #262): the dispatch fetches the issue **with
comments**, renders the thread, and the implementer answers with a machine-read
verdict that a deterministic step applies.

## What Changes

- **`scripts/issue_thread.py`** (`make issue-thread`) renders the implementer's
  input: title, body, **every comment oldest-first with author and ISO8601Z**, then
  the decision instruction (`TRIAGE:` / `REFINED:` / `EVIDENCE:` / `REASON:`). An
  issue with no comments says so in words — never an empty `issue.md` — and an
  unreadable issue exits 2 instead of writing nothing.
- **`scripts/issue_verdict.py`** (`make issue-verdict`) applies the verdict
  deterministically, with no model:
  - `TRIAGE: implement` → **nothing**; the run continues to commit, push and open
    its PR exactly as before;
  - `TRIAGE: refine` + `REFINED: <restatement>` → **ONE** comment carrying the
    restatement and the `agent:refined` label; no PR, no code change;
  - `TRIAGE: close` + `EVIDENCE: <file:line, a command, a measurement>` +
    `REASON: <why>` → the reason with its cited evidence posted, the issue closed,
    the `agent:closed` label applied.
  - **Refusals, loudly (exit 2, nothing written):** a `close` with no `EVIDENCE`
    block, a `refine` with no restatement, a missing or unknown `TRIAGE`. Closing
    without proof is how a real gap gets buried; a verdict nobody understands must
    not be guessed at. The label is re-read after `--add-label` (the #161 lesson:
    it can exit 0 having applied nothing) and its absence is fatal, because the
    label is what the sweep reads.
- **The sweep skips a decided issue** — `agent:refined` / `agent:closed` are a hold
  in the SHARED queue rule (`scripts/issue_queue.py`, `make issue-queue`), reported
  as `reason=decided:<label>`. No TTL: the verdict is a deliberate statement, and a
  human clearing the label is the release. No second copy of the rule in shell.
- **The workflow** renders the thread before reading it, runs `make issue-verdict`
  after the implementation (with `set -o pipefail`, so a refused verdict cannot look
  green), and gates the push, the PR, the fix loop, the outcome comment **and the
  "no implementation" red step** on `verdict == 'implement'`. A refine or a close is
  therefore a **green, honest outcome with no PR**, not a failed run.
- **The prompt** requires `triage.md` and states the grammar, and the gates it used
  to run unconditionally are scoped to `TRIAGE: implement`.
- `tests/test_issue_triage.py` (text via a stubbed `gh`, the script run for real),
  the queue case in `tests/test_issue_review.py`, `ARCHITECTURE.md` and the README
  (through its template).

## Not covered

- **`AGENTS.md` untouched**: this change should add the triage rule (rule 6k's
  text) and a section-8 row; the file is protected and no approval was given, so it
  is deliberately not here.
- Refining an *issue body* is still the reviewer's job (#179); this decides what the
  implementer does, and a `refine` verdict posts a comment instead of editing text.
- #232's token exchange, #231's dispatch-only blind spot and #235's fail-open probe
  are separate, already-tracked work.
