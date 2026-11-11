# A marker written outside the registry is caught

**Issue:** [#474](https://github.com/andyholst/trending-local-llms/issues/474)
**Capability:** `bot-markers`

## Why

The bot-marker guard checks one direction: every REGISTERED marker has a writer. Nothing checked
that every marker the tree WRITES is registered — and that drift already happened.
`scripts/issue_verdict.py` wrote `<!-- issue-bot-verdict: <kind> <ISO8601Z> -->` since #210 and
`bot_markers.marker_name("issue-bot", "verdict")` raised `KeyError: unknown bot marker
issue-bot/verdict` until #477, exactly when a READER needed that stamp (the decided hold in #449
carries no timestamp of its own).

A renamed or newly invented marker raises nothing: the reader finds no stamp and concludes the
opposite of what happened. Rule 6j names the registry as the ONE place the names live, so a marker
outside it is drift by definition.

## What Changes

- **`tests/test_bot_markers.py`** — `test_every_marker_the_tree_writes_is_registered` scans every
  tracked text file for `<!-- … -->` marker literals and fails on a name that belongs to a
  REGISTERED FAMILY but is not declared. Families are **derived** from the registry, so a new bot
  added there widens the guard by itself; a name outside every family (the `data-gap-signature` /
  `tech-debt-signature` dedup keys, `queued-run-alarm`) is not a bot window and is left alone.
  Placeholders and shell expressions (`${{ … }}`, `<…>`) are skipped, so prose about a marker is
  not a finding.
- Three checks: a planted `issue-bot-not-a-registered-marker` **is** caught (the reverse of the
  existing guard), a dedup key and an alarm marker are **not** flagged, and the real tree declares
  every literal it writes.

## Impact

A writer that invents or renames a marker now fails `make test` naming the family it broke, instead
of silently desynchronising from every reader.

## Not covered (out of scope)

- The scan reads the files the test already knows how to find (workflows, `scripts/`, `tests/`,
  `AGENTS.md`, `ARCHITECTURE.md`, `Makefile`); a marker written from a NEW directory is not seen.
  Filed as a finding.
