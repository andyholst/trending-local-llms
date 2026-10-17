# Proposal: engine-meta-capture-at-ingest

Issue: #334

## Why

`tests/test_engine_registry.py` proves the classifier never refuses a registered
engine, using **real GitHub metadata captured offline** in
`tests/fixtures/github_meta.json` — and it requires that fixture to cover *every*
engine in the store's registry.

`register_new_engines` already fetches exactly that metadata from `/repos` at
ingest, to classify the repo — and then discards it. So the one event that
creates the requirement (a refresh auto-registers an engine) is also the event
that breaks the suite:

```
FAIL reality: metadata captured for TokenSpeed  [lightseekorg/tokenspeed]
FAIL reality: metadata captured for Magnitude   [magnitudedev/magnitude]
PASSED 180 | FAILED 2
```

Measured on PR #330, which registered both. `make validate` was **green** — the
link failures were a separate defect — so the only signal was `make test`, and
the fix was a hand edit of the fixture. The next new engine reds the next
refresh the same way.

## What Changes

- **`scripts/engine_registry.py` — `capture_meta(store, path, fetch)`.** Records
  `full_name` / `description` / `topics` for every **registered** engine whose
  slug is missing from the fixture, sorted, preserving `_source` and existing
  entries. It writes only what is missing, never invents an entry for a repo it
  could not read (a failed fetch is a loud `WARN`), and is idempotent. The slug
  and the metadata come from the same `repo_slug` / `fetch_repo_meta` pair the
  registry already uses, so there is one definition of both.
- **A `--capture-meta` CLI mode** on that script (it already had a `main()` for
  `--check-raw`), plus `--meta-file` for tests.
- **`make engine-meta-capture`** (host-side CLI wrapper + `_engine-meta-capture`
  recipe) — rule 6d: a script mode nothing calls is dead code.
- **`refresh-bot.yml` `aggregate`** runs it **after `merge-fetch`** (the merge is
  what registers the engine) and before `qa-report` (which runs `make test`), so
  a refresh keeps its own PR green instead of leaving the fixture behind.
- **`tests/test_engine_registry.py`** — the new test drives the REAL `capture_meta`
  against a real temp fixture with a real fetch callable (an external system
  stand-in, per rule 6m), and asserts the wiring (a make target exists, and the
  workflow calls it after the merge).
- **`ARCHITECTURE.md`** — the new target's row, the aggregate job's step, and the
  script's row (rule 6h).

## Impact

`scripts/engine_registry.py`, `Makefile` (one public target + its `_` recipe),
`.github/workflows/refresh-bot.yml` (one step), `tests/test_engine_registry.py`,
`ARCHITECTURE.md`, the OpenSpec change + `OPENSPEC.md`. No `data/**` change: on
the current store `--capture-meta` prints `OK: the offline fixture already covers
every registered engine`, so this change is a no-op on today's tree and only
acts when a refresh gains an engine.

An `AGENTS.md` §8 row is owed for the new guard, and **could not be written** —
the file is protected (the same wall as #212/#310). It is recorded in
`findings.md` for review.

## Not covered

- **Verifying a new model's `hf` at ingest** — issue #333, deliberately separate:
  a network call per new model is a different decision from recording metadata
  the registry already fetched.
- **A fixture entry for an engine whose repo the API could not read.** The
  capture refuses to invent one; that engine stays a loud `WARN` and remains a
  `make test` failure on purpose, because a fabricated description would defeat
  the classifier test it exists to serve.
- **Re-capturing an entry that already exists.** GitHub descriptions and topics
  drift; refreshing every entry on every run would make the fixture churn on
  every refresh (the conflict surface in #301). Only missing engines are added.
