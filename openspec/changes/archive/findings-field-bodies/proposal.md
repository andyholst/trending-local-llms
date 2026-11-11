# Proposal: findings-field-bodies

Issue: #205 — `tech-debt: A filed finding loses everything after its first line`

## Why

`scripts/file_findings.py` extracted each field with a regex anchored to the marker's
own line:

```python
"Evidence": re.compile(r"^\s*[-*]\s+\*\*Evidence:\*\*\s*(?P<v>.+?)\s*$", re.MULTILINE)
```

`$` with `MULTILINE` stops at the newline, so a field whose detail continues on the
next lines — the normal shape of a real finding — arrives truncated. Measured on issue
#202, filed from this repository:

> `- **Evidence:** \`.github/workflows/issue-bot.yml\`, the \`pick\` job's`

and it stops. The four lines under it (the `if:` condition, the scenario, the reason it
mattered) existed only in `findings.md`, which is gitignored — the one artifact rule 6g
makes durable lost the evidence that made the finding worth filing.

## What Changes

- **A field runs from its marker to the next marker, the next `## ` heading, or a blank
  line**, and its lines are joined into the value. `_fields()` is the one extractor;
  `_FIELD` (four single-line regexes) is gone.
- **A marker must be a bullet carrying a field name** — `- **Evidence:** …` — so an
  indented continuation line that happens to contain `**Why:**` inside prose is never
  mistaken for the next field.
- **`parse()` still defaults every field**, so a finding without a `Signature` falls
  back to the title slug exactly as before.
- **`tests/test_file_findings.py::test_a_multiline_field_keeps_its_continuation_lines`**
  files a finding whose Evidence/Why/Done-when continue on later lines through the REAL
  script (stub `gh`) and asserts each continuation fragment reaches the issue body.

Verified RED against the pre-change `scripts/file_findings.py` (3 fragments missing
from the body; `PASSED 29 | FAILED 3`) and GREEN after (`PASSED 32 | FAILED 0`).

## Impact

`scripts/file_findings.py`, `tests/test_file_findings.py`, this OpenSpec change and the
regenerated `OPENSPEC.md`. No make target, stage, job or image changes
(`ARCHITECTURE.md` unchanged, rule 6h). The issues filed from now on carry the finding's
full text; issues already filed are untouched (never rewritten by automation).

## Not covered

- **Re-filing the truncated issues** (#202 and friends). Their bodies are a human's
  record; the fix applies to what is filed next.
- **Multi-paragraph fields.** A blank line ends a field by design: it is the separator a
  writer already uses between findings, and treating it as content would swallow the
  next section.
