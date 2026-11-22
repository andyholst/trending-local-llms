# Proposal: cross-machine-coordination

Issue: #1231
PR: #1233

## Why

Two LLM machines work the same repo threads (`asimov@mac` and `tll-implementer` on
`asimov@omarchy`). Identity comments drifted, a red gate sat unreported for 15 minutes (#1222),
and a handover worked only because one machine wrote a signed note (#1228). The owner asked for
a written rule, including a status sync while CI is pending so the other machine can take the
next issue.

## What Changes

- AGENTS.md rule 6u: identity `agent@host`, claim before edit, failure report before fix,
  signed handover, issue-as-ONE-board, and status-while-CI-pending. No gate/pipeline/data change.
- `tests/test_cross_machine_coordination.py` (10 checks) fails on any dropped obligation and
  checks runner discovery; AGENTS.md §8 gains the regression row.

## Impact

Specs: agent-coordination (new). Docs + one test only.

## Verification

10/10; architecture-check green (171 targets); linefeeds green.
