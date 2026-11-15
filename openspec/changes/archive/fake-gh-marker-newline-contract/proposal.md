# Proposal: fake-gh-marker-newline-contract

Issue: #1002 — "The fake-gh `issue create` stubs and the final-marker newline
PR: #1003
are a latent coupling" (tech-debt).

## Why

The data-gap filer's issue body carries its invisible dedup marker on the LAST
line (`body += ["", marker(signature_id(report))]`, then `"\n".join(body)` —
so the emitted body ended with `...\n<!-- data-gap-signature: <sig> -->` and
NO trailing newline). The fake `gh` `issue create` stubs in
`tests/test_data_gap_analysis.py` (`_GH_STUB`, `_GH_STUB_LABELS`) consume that
body and must see that final marker line. That is a coupling with an UNWRITTEN
contract: a body renderer that trims the final newline, or a consumer that
reads line-by-line (`while read`) without a terminating newline, silently drops
the last claimed entry's dedup marker — a quiet re-file risk indistinguishable
from the #996 class this issue fixes (measured on `5efd9a0b6f6d`, the
`unstructured:weight_gb` marker, absent from the store).

This change makes the contract EXPLICIT on both sides: the product guarantees
the trailing newline, the stubs document that they rely on it, and a shared
test asserts the body ends with a newline so neither side regresses alone.

## What Changes

1. `scripts/data_gap_analysis.py::issue_body` returns a body that ENDS with a
   trailing newline (`"\n".join(body) + "\n"`), so the marker line is always a
   complete, terminated line — with an inline comment naming the contract.
2. `tests/test_data_gap_analysis.py::_GH_STUB` and `::_GH_STUB_LABELS` each
   gain a comment on the `issue create` arm stating that they rely on the
   product body ending in a newline (the marker being the final line).
3. The suite gains a shared newline assertion test proving `issue_body`
   output ends with `\n` and that the final marker line survives — locks the
   contract so a renderer that trims it (or a stub that stops consuming it)
   turns red alone.

## Not Covered

- Not changing the marker format or the dedup search (`already_filed` uses
  `gh issue list --search "<sig> in:body"` — unaffected; GitHub's search
  indexes a body whether or not it ends in a newline).
- Not re-working the stubs' extraction (`$(cat)` + `sed`); only documenting
  the newline contract they share with the renderer.
- Additive only (rule 3b): no data-key is removed, renamed or narrowed; no
  value is shrunk; this is code + tests + docs, nothing in the store.

## Impact

- No public `make` target, stage, pipeline job or image changes (ARCHITECTURE.md
  §10 untouched; no new script).
- The body string handed to `gh issue create --body-file -` ends in `\n`
  instead of not — harmless to `gh` and to the stub (which `$(cat)`s it).
- The `test_data_gap_analysis.py` suite already runs in `make test`; the new
  assertion rides that existing wiring (rule 6d — no new target needed).
