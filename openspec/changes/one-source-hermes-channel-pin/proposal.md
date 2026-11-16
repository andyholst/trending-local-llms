# Change: one-source-hermes-channel-pin

Issue: #1094

## Why

`scripts/hermes_pin_freshness.py` hard-codes its own `CHANNEL_REPO =
"NousResearch/hermes-agent"` (line 39) while the install seam names the vendor
install URL in the Makefile's pin block (`HERMES_INSTALL_URL ?=`) and the
Dockerfile `ARG` — a second copy of the channel identity outside the block rule
6k says carries the pins. An upstream repo move requires editing a script
literal the Dockerfile, the Makefile and `test_install_hermes_ci.py`'s pairing
assertion never see: the pin block moves, the check silently keeps querying the
old repo, and its failure mode is `channel unreadable` (exit 2) naming a repo
that no longer exists. Rule 6d: one definition, no second spelling.

## What Changes

- The Makefile's install-pin block gains `HERMES_CHANNEL_REPO ?=
  NousResearch/hermes-agent` beside `HERMES_INSTALL_URL` / `HERMES_VERSION` —
  the ONE spelling of the upstream release channel in the repository.
- `scripts/hermes_pin_freshness.py` DERIVES the channel repo by reading that
  Makefile line (the same seam it already uses to read `HERMES_VERSION`); the
  literal `CHANNEL_REPO` and every mention of the vendor repo name in the script
  are removed. A Makefile without the pin refuses loudly (exit 2), never a
  fallback literal.
- `tests/test_hermes_pin_freshness.py` plants a channel pin so the whole suite
  proves the derivation (the recorded `gh api` endpoint must be the planted
  repo), refuses a Makefile missing the pin, and fails if the script re-spells
  the channel literal.

## Impact

- `Makefile` (one new variable in the existing pin block)
- `scripts/hermes_pin_freshness.py`
- `tests/test_hermes_pin_freshness.py`
- `ARCHITECTURE.md` generated inventory block (docstring-derived, regenerated
  via `make architecture-refresh`)

Not covered: changing the channel's VALUE (still an explicit edit to the Makefile
pin block, reviewed like any pin change); the `HERMES_PACKAGE` spelling (the
package name is the installer's, not the channel API's); any new cadence for the
freshness check (issue #1093 tracks that separately).
