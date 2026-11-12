# Proposal: write-raw-verifies-links

Issue: #644

## Why

`write_raw_snapshot(..., verify_hf=True)` verifies only `_m["hf"]` and
`_f["hf"]` (issue #417), while the same raw payload carries `engine_repo`
(asked for by `ENGINE_ASK`) and `source_post` — values whose dead spellings are
first seen by `check_links_resolve` in `scripts/validate.py`, i.e. two pipelines
later, on the open refresh PR, where fix-bot silently rewrites them and the
prompt never learns (issue #644).

## What Changes

- `write_raw_snapshot` gains a link pass over every engine measurement when
  `verify_hf=True`: a DEFINITIVELY dead `source_post` (HTTP 404/410) refuses the
  measurement (a figure must trace to a real post — rule 2); a definitively dead
  `engine_repo` is stripped from the measurement (the t/s figure stays, the
  engine stays unregistered for `make engine-check` to report to a human).
- One loud `[write-raw] WARN:` per refusal naming the model, the field and the
  refused value; an indeterminate answer (403/429/5xx/transport) keeps the value
  — the same rule `hf_repo_resolves` already follows.
- URL answers are cached per write so repeated links cost one request.

## Impact

- `scripts/update_trending.py` — new `url_resolves()` helper, link pass inside
  `write_raw_snapshot` (already wired: every `--write-raw` leg runs
  `verify_hf=True`; no new make target).
- `tests/test_write_raw_link_verify.py` (new) — runs the real writer against a
  real local HTTP server (rule 6m: external system only).
- `AGENTS.md` §8 gains the guard row.

## Not covered

- Store-side rewriting of already-stored dead links (rule 3b — additive only).
- Rate-limit handling beyond "indeterminate keeps the value".
