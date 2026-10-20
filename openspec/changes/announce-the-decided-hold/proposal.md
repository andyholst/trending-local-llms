# Proposal: announce-the-decided-hold

Issue: #449 (the owner's ruling: the decided hold stays a HUMAN decision — it must be announced, never expired)

## Why

`agent:refined` / `agent:closed` is the implementer's own verdict, and `issue_queue.py`
holds an issue that carries one **with no TTL**, on purpose. The owner's ruling is that this
stays so: a label carries no timestamp, and releasing a decision is a human's act.

The defect is the SILENCE around it. Measured on sweep run `39388480833`:

```
[issue-queue] candidates=4 windows_open=4
issue=266 position=-1 ... reason=decided:agent:refined ...
issue=329 ... issue=347 ... issue=415 ...
data-gap backlog empty: every open labelled issue has an implementer, or a fresh reviewer verdict holds it.
```

Every row had `verdict_fresh=0 has_implementer=0` — nothing held them but the label — and
`make issue-skip-note` then printed *"no fresh verdict holds the queue — nothing to note"*,
because `post_skip_note` selected only `verdict_fresh == 1` rows. So the entire data-gap
queue was parked, the sweep reported a green empty backlog, and the issue thread said
nothing. Both bots (implementer and reviewer) read the same queue, so both went quiet.

A second, structural cause: the implementer already WRITES a marker the shared registry did
not know — `<!-- issue-bot-verdict: refine <TS> -->` (`scripts/issue_verdict.py`, since
#210). Rule 6j says the marker names and shapes live in ONE place (`scripts/bot_markers.py`),
and this one was not in it, so no reader could date a decided hold from it.

## What Changes

- **`scripts/bot_markers.py` registers `issue-bot/verdict`** in `REGISTRY` and `WRITTEN`, and
  the ONE parser learns its shape: `<!-- <name>: [<field> ]<ISO8601Z> [run=<id>] -->`
  (`field` is `refine` / `close`). Other markers are unaffected (asserted).
- **`scripts/issue_queue.py` dates the decided hold**: `decided_since` is the newest
  `issue-bot-verdict` stamp on the thread, and the row prints it.
- **`post_skip_note` announces BOTH holds**: the reviewer's fresh verdict (as before) and the
  implementer's decision — one comment per round, idempotent on `since`, never a label edit,
  saying in as many words that the hold has **NO expiry** and needs a human (refine + remove
  the label, or close). The bounded walk and the per-round dedup are reused unchanged.
- **`AGENTS.md` §6j**: the marker table gains `issue-bot-verdict`, and the rule states that a
  decided hold is a human's decision with no expiry, which is exactly why the sweep must
  announce it.
- **Tests**: a decided hold produces exactly ONE note naming the label, the human action and
  the marker stamp; the existing verdict-hold tests and the marker round-trip still pass.

## Impact

`scripts/bot_markers.py`, `scripts/issue_queue.py`, `AGENTS.md` (§6j), the review test module,
`OPENSPEC.md`, this change. No new target, stage, job or image: `make issue-skip-note` already
runs in the implementer's `pick` job.

## Not covered

- **The hold is NOT given a TTL.** That was the alternative and the owner rejected it: the
  decision stays a human's. If a decision is ever meant to expire, that is a new change with
  its own rule.
- **No notification channel is added.** The note lands on the ISSUE (where the human who can
  release it reads it); pinging a person elsewhere is outside this repo's scope.
- **`agent:closed`** is announced by the same path but its issues are closed, so the note is
  only visible if one is reopened — deliberately not special-cased.
