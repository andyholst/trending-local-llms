# A refine's restatement is posted whole, or refused

**Issue:** [#450](https://github.com/andyholst/trending-local-llms/issues/450)
**Capability:** `issue-bot-verdict`

## Why

`scripts/issue_verdict.py` reads `REFINED:` with a single-line regex
(`_FIELD["REFINED"]`, `(?P<v>.+?)\s*$`, `re.MULTILINE`). A restatement is a SENTENCE, and
the model wraps it, so the value was cut at the first newline and the run posted:

```
The issue's top-ranked gap cannot be implemented as written, and the
```

— a fragment ending on `and the`. The `refine` path exists to hand a human (or the next
sweep) something they can APPLY; a truncated restatement is worse than none, because it
looks like a decision, carries `agent:refined`, and cannot be acted on.

Nothing caught it: every `REFINED:` fixture in the suite is a single line, and the only
guard was "not empty".

## What Changes

- **`scripts/issue_verdict.py`**
  - `restatement()` reads the `REFINED:` value continuation-aware: it runs to the next
    key line (`EVIDENCE`/`REASON`/`TRIAGE`) or a blank line AFTER the value began, and the
    lines are joined into one sentence.
  - `_ends_mid_sentence()` refuses a value that stops on a word no sentence ends with
    (`the`, `and`, `of`, `that`, `which`, `is` …) or on a trailing `,`/`-`/`—`/`(` —
    naming the tail so the refusal is diagnosable.
  - The refusal happens BEFORE any write: no comment, no `agent:refined` label.
- **`tests/test_issue_triage.py`** — two cases: a wrapped restatement must reach the
  comment whole; the measured truncated value must be refused with nothing posted, while a
  complete one-line restatement (`scope it to the ROCm table only`) still passes, so the
  guard is not a length gate.
- **`AGENTS.md`** §8 — the guard row (review-required, rule 3c).

## Impact

The implementer's verdict path only. A refine that produced a usable restatement behaves
exactly as before; a cut one now fails loudly instead of publishing a fragment. No data,
README or ranking change.

## Not covered (out of scope)

- `EVIDENCE:` and `REASON:` keep the single-line reader. An evidence block that wraps is a
  separate case (the evidence only has to name one checkable token, and the first line
  carries it), filed as a finding.
- The `#450` wording in the refine prompt is unchanged: the model is already asked for one
  restatement, and the parser is where a cut must not survive.
