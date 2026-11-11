# Proposal: skip-note-every-hold

Issue: #204 — `tech-debt: The skip note covers ONE held issue per run`

## Why

`post_skip_note` sorted the fresh-verdict holds and then noted exactly one:

```python
row = held[0]
```

So with two issues held by a reviewer verdict, the sweep commented on the first and
said **nothing** about the second — the state the note exists to prevent ("why is nobody
working on this?"). The note is idempotent per `since=`, already reads the marker
through `bot_markers` (rule 6j) and never writes a label, so the only defect was the
`held[0]` slice.

## What Changes

- **Every held issue is noted, bounded by `MAX_SKIP_NOTES` (10).** Each issue gets its
  own comment (its own `since=`, so idempotence is per issue per round); when more than
  the bound are held, the run says how many remain for the next sweep rather than
  silently dropping them.
- **The run reports what it did**: `skip notes: N posted, M already noted (K held by a
  fresh verdict)`, so a sweep's effect is visible in the log.
- **`tests/test_issue_review.py::test_the_skip_note_covers_every_held_issue`**: two
  issues with their own fresh verdicts and reviewer markers must each get exactly one
  note (each carrying its own timestamp), and a second run in the same round must post
  nothing new.

Verified RED against the pre-change queue (5 failures — only #163 noted) and GREEN
after (`PASSED 70 | FAILED 0`).

## Impact

`scripts/issue_queue.py` (the note walk + one constant), its test module, this OpenSpec
change and the regenerated `OPENSPEC.md`. Same one implementation the workflow calls
(`make issue-skip-note`); no make target, stage, job or image changes
(`ARCHITECTURE.md` unchanged, rule 6h).

## Not covered

- **The hold's own ceiling** (#203) — a re-review that keeps re-dating the verdict still
  holds an issue indefinitely; that is a separate judgement about the reviewer's window,
  not about how many notes a sweep posts.
- **Noting issues held for a REASON OTHER than a verdict** (reviewer working, implementer
  recently active): the note is specifically the verdict-hold's explanation.
