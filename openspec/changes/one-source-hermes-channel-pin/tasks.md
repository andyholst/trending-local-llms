# Tasks — issue #1094: the Hermes release channel has ONE spelling (the Makefile pin block)

## Makefile pin block (the single source)

- [x] `HERMES_CHANNEL_REPO ?= NousResearch/hermes-agent` added beside `HERMES_INSTALL_URL` /
      `HERMES_VERSION` in the install-pin block (Makefile:126)
- [x] `_hermes-pin-freshness` recipe forwards the knob: `--channel-repo "$(HERMES_CHANNEL_REPO)"`
      (a real `$(NAME)` read — the rule 6m knob guard sees an operator override move the value)

## scripts/hermes_pin_freshness.py (no baked channel literal)

- [x] `CHANNEL_REPO` literal and every vendor-repo mention REMOVED from the script
- [x] `read_channel_repo()`: a direct invocation reads the same `HERMES_CHANNEL_REPO ?=` line from
      `--makefile`; a Makefile without it refuses with exit 2 naming the pin, BEFORE `gh api` runs
- [x] `channel_tag`, `issue_body` and `file_drift_issue` take the derived `channel_repo`; the filed
      issue's evidence quotes the derived `repos/<channel>/releases/latest`

## Tests (RED on the old script, per rule 6c)

- [x] `PLANT_MAKEFILE` carries the channel pin and the `gh` stub serves ONLY the planted repo's
      endpoint — every existing scenario now proves the derivation (old code dies: `channel
      unreadable` exit 2 against the planted tree)
- [x] Drift scenario asserts the `gh api` argv AND the filed body name the planted channel repo
- [x] `test_the_channel_repo_is_derived_from_the_makefile_pin_block`: the script carries no channel
      literal, the Makefile pins it exactly once, no other `scripts/*.py` re-spells it, a pinless
      Makefile exits 2 without consulting `gh api`, and `--channel-repo` forwarding moves the endpoint
- [x] `python3 tests/test_hermes_pin_freshness.py` green (56/0)

## Docs + gates

- [x] `ARCHITECTURE.md` §6 target row + §6 script row updated; `make architecture-refresh` +
      `make architecture-check` green
- [x] `queued-alarm.yml` step comment names the derived channel pin
- [x] `make lint` green (knob guard: `HERMES_CHANNEL_REPO` has a real reader)
