# Proposal: findings-mixed-none-refusal

Issue: #1662
PR: #1663

## Why

`scripts/file_findings.py::parse()` short-circuits on any line matching
`^\s*[-*]\s+none\s*$` and returns `([], None)` — "the run found nothing" — BEFORE it
looks for `## <title>` sections. A findings file that records a real finding AND
carries the template's `- none` line is therefore read as EMPTY, silently.

Measured on `origin/master` (`ae574e3c`): `findings/1586.md` carries three complete
findings plus a `- none` line at line 21 and `file_findings.parse()` answers
`([], None)`; `findings/1612.md` (one finding plus `- none`) answers the same. The
same shape was measured on PR #1650 head `a2e3d1e4b` (`findings/1644.md`, one finding
plus `- none`) where `make file-findings ISSUE=1644` printed
`[findings] OK 1644.md: 0 finding(s), all well-formed`.

Consequence: an implementer that runs `make file-findings` after a green fix loop
files NOTHING for a run that did find something, `make findings-check` and
`make findings-check-for-pr` stay green, and rule 6g's "analysis ships ISSUES" is
defeated with no red gate anywhere. A reader who trusts the seam believes the run
was clean.

## What Changes

- `scripts/file_findings.py::parse()` refuses the MIXED shape: when at least one
  `## <title>` section AND a `- none` line are both present, it returns an error
  naming the two conflicting shapes — never a silent clean.
- A `- none`-only file stays a valid empty result; a sections-only file is
  unchanged. Only the self-contradicting file is refused.
- The shipped mixed files (`findings/1586.md`, `findings/1612.md`) drop their stray
  `- none` line so their recorded findings become visible to the filer.

## Impact

- `scripts/file_findings.py` — `parse()` reorders its two checks (sections first,
  then the `- none` short-circuit) and adds the refusal.
- `findings/1586.md`, `findings/1612.md` — one stray template line removed each.
- `tests/test_file_findings.py` — real-parser cases for the mixed/section-only/
  `- none`-only shapes, RED-first against the pre-change parser.
- No contract, data, workflow, schedule or label change.

## Not covered

- The filer's dedup/GitHub behaviour (unchanged; it already reads `parse()`).
- Any new `make` target: the fix rides `make findings-check` /
  `make findings-check-for-pr`, both already wired.
