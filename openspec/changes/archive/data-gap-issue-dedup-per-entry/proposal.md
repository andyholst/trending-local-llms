# Proposal: data-gap-issue-dedup-per-entry

Issue: #996 — "The data-gap filer's signature is a whole-SET hash, so one volatile
PR: #1000
`starved_leg` entry re-files the entire persistent gap set — three identical
`context_tokens` issues in five hours".

## Why

`scripts/data_gap_analysis.py::signature_id()` hashes the **whole** signature list
(`missing:context_tokens`, `starved_leg:cpu`, … as one string), and
`already_filed()` searches issue bodies for that single whole-set hash. A
`starved_leg` entry is volatile by design (issue #856) — it appears, disappears
and reappears with each search round, while the five persistent dimensions that
share the set never change. When the volatile entry flips, the whole-set hash
changes, `already_filed()` finds no open issue carrying the NEW hash (the existing
one carries the OLD hash), and the filer re-files the entire set — the identical
persistent dimensions — as a fresh issue. Measured 2026-11-15: #981 (00:52Z),
#991 (04:51Z) and #994 (05:54Z) are all titled `data-gap: context_tokens (69
models)`, open, with three different signatures whose only real difference is the
volatile `starved_leg`/`reask_estimate` entries. Each one consumes a sweep's
implementer on a duplicate — the exact re-file loop issue #472 was filed to end.

## What Changes

- Dedup is per signature **ENTRY**, not per SET: each entry
  (`missing:context_tokens`, `starved_leg:cpu`, …) carries its **own** marker in
  the issue body (`<!-- data-gap-signature: <entry_id> -->`, one per entry), and
  `already_filed()` is consulted per entry.
- A refresh re-files ONLY the entries with no open issue: the persistent
  dimensions stay one open issue until closed, a starved leg still files once
  while starved.
- `scripts/data_gap_analysis.py`: `entry_id()` (a single entry's hash), `marker()`
  now takes an entry id, `already_filed()` consults one entry, `issue_body()` /
  `file_issue()` emit one marker per claimed entry, and the `--issue` path in
  `main()` decides per entry.
- `issue_body()` returns a body ending in a newline (so a line-oriented stub /
  reader never drops the final marker).
- `tests/test_data_gap_analysis.py`: the fake `gh` stubs record every marker an
  issue carries (not just the first), and a planted test proves two runs whose
  signature differs ONLY by a fluctuating `starved_leg` entry produce NO second
  filing of the persistent dimensions.

## Not covered

- No data change, no contract change (additive-only untouched): the issue markers
  and baseline stay `data-gap-signature`, the label stays `data-gap-analysis`.
- The already-open duplicates (#981/#991/#994), filed under the OLD whole-set
  scheme, are triaged to one by the reviewer — explicit in the issue's Done-when,
  this change only prevents FUTURE re-filing.
- `signature_id()` (the whole-set hash) is kept as a helper — it still detects
  "the gap STATE changed as a whole" for callers that ask (e.g.
  `tests/test_ingest_refusal_ledger.py`) — but it no longer drives dedup.
