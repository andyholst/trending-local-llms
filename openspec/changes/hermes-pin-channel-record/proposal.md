# hermes-pin-channel-record — a wired recorder for the release-channel fixture

Issue: #1163

## Why

`make test`'s offline half asserts the Hermes pin against a recorded payload,
`tests/fixtures/hermes_releases_latest.json`. Nothing wrote that file: `grep -n
"hermes_releases_latest" Makefile scripts/*.py` named only the fixture as an INPUT, so a pin
raise had to hand-copy `gh api repos/<channel>/releases/latest` into it — and the precedent
raise (`git show dbd041c4 --stat`) did the same. Hand-copying a registry payload is the step
that silently goes stale or wrong, and a stale fixture makes the offline gate assert against
a release the repository no longer ships. Rule 6m also forbids a bot or workflow reaching
into `scripts/*.py` directly, so there was no wired, reviewable way to refresh it at all.

## What Changes

- `scripts/hermes_pin_freshness.py` gains ONE read seam, `read_channel()`, that returns
  `(payload, raw text)`; `channel_tag()` and the new recorder both go through it, so the
  freshness check and the recorder can never read differently.
- `--record PATH` writes the payload the seam READ (the live `gh api` stdout — never an
  authored document, and never a re-serialisation that could drift) to `PATH` via a temp file
  + rename. A failed read (no `gh`, no network, a payload with no `tag_name`/`published_at`)
  raises BEFORE any write → exit 2, the old fixture byte-identical.
- `make hermes-pin-channel-record TO=<path>` (internal `_hermes-pin-channel-record`) is the
  ONLY path to the script's recorder, host-side like the other gh-bound verifiers.
- `refresh-bot.yml` runs the recorder beside `make engine-meta-capture` (issue #334's
  recorder — the same precedent) and the refresh PR's `git add` carries the fixture, so the
  recorded payload lands in a PR instead of a hand paste.
- `tests/test_hermes_pin_freshness.py` proves the written bytes are exactly what `gh` served,
  that the payload carries `tag_name` and `published_at`, that a failed read leaves the old
  fixture byte-identical with no `.tmp` litter, and that the target is Makefile-only and
  CI-wired.

## Impact

- New public target `hermes-pin-channel-record`; ARCHITECTURE.md §6 names it (rule 6h).
- No change to `make hermes-pin-freshness`, its verdicts or its wiring; `--repo` becomes
  optional ONLY when `--record` is given.
- Not covered: recording any other channel payload, or a `--check` mode comparing the live
  payload against the committed fixture (the recorder landing in the refresh PR is the fix).
