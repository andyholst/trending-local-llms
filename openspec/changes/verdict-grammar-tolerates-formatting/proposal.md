# The verdict grammar tolerates the formatting a model actually produces

Issue: [#245](https://github.com/andyholst/trending-local-llms/issues/245)
Capability: `issue-triage`

## Why

The implementer's verdict is answered by a MODEL in `triage.md`, but the parser read
only a bare line — `scripts/issue_verdict.py` matched `^TRIAGE: …$`. A near-miss failed
the whole run AFTER the implementation was done: the measured base refused every one of
these shapes a model actually writes,

```
**TRIAGE: implement**          -> REFUSED: no `TRIAGE:` line
## TRIAGE: implement            -> REFUSED: no `TRIAGE:` line
- TRIAGE: implement             -> REFUSED: no `TRIAGE:` line
**TRIAGE:** implement           -> REFUSED: no `TRIAGE:` line
TRIAGE : implement              -> REFUSED: no `TRIAGE:` line
triage: implement               -> REFUSED: no `TRIAGE:` line
TRIAGE: implement — the reason  -> REFUSED: unknown TRIAGE 'implement — the reason'
TRIAGE: implement.              -> REFUSED: unknown TRIAGE 'implement.'
`TRIAGE: implement`             -> REFUSED: no `TRIAGE:` line
  TRIAGE: implement             -> REFUSED: no `TRIAGE:` line
```

(`python3 -c` against the base module; all eleven refused while the plain line parsed).
The cost of a near-miss is asymmetric and invisible in the run summary: ~20 minutes of
model work is thrown away over decoration, and the run reports a red verdict step with
nothing pushed and no outcome posted. The issue's own "Done when" is exactly this:
*the parser tolerates the formatting a model actually produces.*

## What Changes

- **`scripts/issue_verdict.py`** — `parse()` reads DECORATION, not prose:
  - leading markdown is stripped before the key: `## `, `- `, `> `, `1. `, `**`, `` ` ``, `__`, `~~`, and indentation;
  - the key matches case-insensitively and tolerates a markdown wrapper around the colon (`**TRIAGE:**`, `TRIAGE :`);
  - the verdict is the **first word** of the value with markdown/quote/period decoration stripped, so `TRIAGE: implement — the thread matches the body` reads as `implement`;
  - `REFINED`/`EVIDENCE`/`REASON` tolerate the same decoration, so a bold close keeps its evidence and reason.
- **Refusals are unchanged.** Tolerance is decoration, not guessing: a TRIAGE line whose
  first word is not one of `implement`/`refine`/`close` still exits 2 (`TRIAGE: maybe`),
  a file with no TRIAGE-shaped line still exits 2, a close without EVIDENCE still exits 2,
  and a verdict buried in prose is not read. Two deliberate widenings, both measured:
  when several TRIAGE lines exist and only one names a real verdict, the real one wins (a
  model that restates its decision); and a line that lists the whole grammar
  (`TRIAGE: implement | refine | close`) is the instruction copied back, not a decision,
  so it is skipped — a paste with no decision below it still refuses.
- **`tests/test_issue_triage.py`** — `test_a_decorated_verdict_is_read_and_a_near_miss_is_not_guessed_at`
  drives every measured shape through the real script (implement applies nothing; a
  decorated refine keeps its restatement and label; a decorated close keeps its evidence,
  closes and labels), and keeps three near-misses refused with no write.
- **`ARCHITECTURE.md`** — the `scripts/issue_verdict.py` inventory row says the grammar
  tolerates markdown decoration while keeping its refusals.

## Impact

A run that implemented an issue and answered with a decorated verdict now continues to
its PR instead of failing at the verdict step; the three verdicts keep their meaning and
their labels. No new make target, pipeline job, image or script — the seam stays
`make issue-verdict` → `scripts/issue_verdict.py`. No data, no README, no schema.

## Not covered

- **Multi-line field values.** `EVIDENCE:` on its own line with the proof on the next
  line is NOT read; this change tolerates decoration on one line. That is a separate
  grammar decision (it widens what counts as a field, not how it is decorated).
- **What a verdict MEANS.** `implement`/`refine`/`close` keep their existing effects;
  only how the same words are read changes.
- **The prompt's grammar.** The dispatch still asks for the plain `TRIAGE: …` line; a
  model writing plain text keeps working, and decoration now does too.
