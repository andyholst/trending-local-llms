# Hermes pin freshness: compare the pinned agent version against the upstream channel

Issue: #1091

## Why

The agent version the whole fleet builds is pinned twice — `HERMES_VERSION ?= 0.23.1` in the
Makefile and `ARG HERMES_VERSION="0.23.1"` in the Dockerfile (rule 6k pins the two together,
issue #218) — and the build seam proves `hermes --version` equals the pin, but **nothing
compares the pin with the upstream release channel**. Today a channel move surfaces only at the
next image dispatch/build (#894/#968): no alarm, no tracked issue, nothing that says "the pinned
agent aged". A fleet still building `0.23.1` while upstream ships newer is invisible between
image rebuilds. Rule 6l's model — a quietly aging state must become loud on a sweep — is exactly
what this gap never got. Measured 2026-11-16: channel = `v0.23.1` = the pin, so the check starts
green; the point of wiring it is the day they stop agreeing.

## What Changes

- `scripts/hermes_pin_freshness.py` — the ONE implementation: read BOTH pins back from the tree
  (Makefile `HERMES_VERSION ?=`, Dockerfile `ARG HERMES_VERSION=`; a silent disagreement between
  them is the #218 defect itself and REFUSES with exit 2 before the channel is even consulted),
  read the upstream channel through the real `gh` client (`gh api
  repos/NousResearch/hermes-agent/releases/latest`, or a recorded payload via `--from-file` — the
  same fixture seam `check_branch_protection.py` uses), and decide:
  - channel equal to the pin → print `pin=<v> channel=<v> OK`, exit 0 (no mocks: the verdict is
    produced from recorded payloads or the live API, never a version-parsing stand-in);
  - channel strictly NEWER → file ONE marker-deduplicated `tech-debt` issue (label `tech-debt`,
    the five-section message pattern, the registered drift marker carrying the pair signature,
    deduped across OPEN drift issues) naming the remedy — raise BOTH pins together per #218 —
    then exit 1, loudly;
  - pin AHEAD of channel → report `AHEAD`, exit 0 (reported, never red);
  - channel unreadable → exit 2 naming why — never a silent clean.
- `scripts/bot_markers.py` — register the new marker name in the ONE marker table (rule 6j):
  the `hermes-pin-drift-signature` key in `DEDUP_KEYS` (its acceptance regex is derived from the
  registered key, so `marker_acceptance()` and `canonical_examples()` carry the new family with
  no hand-kept entry — the same mechanism as `queued-run-alarm`); `scripts/hermes_pin_freshness.py`
  renders it through `bot_markers.marker()` (one writer; `tests/test_bot_markers.py` fails when a
  registered marker has no writer, so the registration needs the script to exist — same change).
- `Makefile` — `_hermes-pin-freshness` internal host recipe + public `hermes-pin-freshness`
  target (host-side like `check-branch-protection`/`file-findings`: it needs `gh` + python3, not
  the harness image), registered in `.PHONY`.
- `.github/workflows/queued-alarm.yml` — a `make hermes-pin-freshness REPO=…` step in the alarm
  job (report-and-file, like `make pipeline-failure-issue`): the sweep goes RED when the script
  exits 1 (the channel moved) or 2 (the channel/pins could not be read), mirroring the
  established `if: ${{ !cancelled() }}` alarm-step pattern; files with the DEFAULT token
  (filing needs `issues: write`, rule 6e).
- `ARCHITECTURE.md` — the target row (§4), the script row (§6), the queued-alarm job-step line,
  and the generated §10 inventory block regenerated in the same change via
  `make architecture-refresh` (rule 6h).
- `tests/test_hermes_pin_freshness.py` — planted-fixture tests driving the REAL script (stub `gh`
  on PATH, the permitted external seam; recorded channel payloads), plus the wiring guard: refuse
  a queued-alarm sweep without the step, refuse a step that reaches the script without `make`,
  refuse a marker that is not registered in `bot_markers.py`.

## Impact

- Affected: `scripts/hermes_pin_freshness.py` (new), `scripts/bot_markers.py`, `Makefile`,
  `.github/workflows/queued-alarm.yml`, `ARCHITECTURE.md`, `tests/test_hermes_pin_freshness.py`
  (new), `tests/fixtures/hermes_releases_latest.json` (new recorded payload).
- Unaffected: the image build seam itself (`install_hermes_ci.sh`, the build-time version assert)
  — this check is a sweep-side freshness alarm, never a build gate; qa-validate gains no step
  (rule 6t: the merge gate stays tests/validators only, and this check needs `gh` + network).
- Behaviour change seen by maintainers: the next `queued-alarm` sweep run (dispatch-only cadence,
  issue #1029) goes red — and files one tracked tech-debt issue — the first time the upstream Hermes
  channel passes the pin, instead of the drift surfacing only at the next image build.

## Not covered

- Bumping the pins: the filer never fixes (rule 6g) — the bump is a separate reviewed change per
  issue #218 (raise BOTH together; `_hermes-alias-check` re-derives model pins).
- Other pins (`HERMES_PACKAGE_COMMIT`, `HERMES_CATALOG_COMMIT`): issue #1091 names the agent
  VERSION pin; package/catalog pin freshness stays the image-digest machinery.
- A CI-side version-freshness gate in qa-validate (rule 6t), and any auto-merge behaviour.
- The `refresh-bot` image build itself stays the only place a new version is baked.
