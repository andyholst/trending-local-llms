# The rebuild decision is data, not inline workflow shell

**Issue:** [#208](https://github.com/andyholst/trending-local-llms/issues/208)
**Capability:** `rebuild-decision`

## Why

A bot runs on whatever the `dockerfile-<sha12>` tag resolves to, so *when* that tag
is rebuilt is a behaviour the whole fleet depends on — and it was computed by inline
shell in **two** steps of `refresh-bot.yml` (`date +%u`, three/four
`docker manifest inspect` probes, and the `if [ "$DOW" = "7" ] || …` clauses). No
test could reach it, and this exact rule has already cost the repo a defect: a
merged Dockerfile change stayed inert until the next Sunday while the bots kept
running the old runtime — the reason the hash tag exists at all (#135, #141 for the
test image). A dropped clause or an inverted test would silently stop rebuilding the
toolchain and every gate would stay green.

llgenie moved the equivalent decision behind a script so the workflow calls one
command and the tests drive it.

## What Changes

- **`scripts/ensure_image.py decide [--force <bool>] [--dow <1-7>]`** returns the
  decision as data: `built`, `test_built`, `publish_openspec`, the three tags, a
  `reason` per image, and the four `*_published` probes. The rule is unchanged — base
  on Sunday, when `:latest` or its hash tag is missing, or when forced; test image on
  Sunday, when its hash tag is missing, or when forced (the OpenSpec image keeps its
  own tag-only rule). `published()` still goes through the `docker` CLI, so a test
  fakes it exactly as the other ensure paths do, and the day is an argument.
- **`parse_bool`** reads the force value strictly: `1/true/yes/on` are ON,
  `0/false/no/off/""` are OFF, anything else fails loudly — so an "off" value cannot
  take the rebuild branch (the class issue #227 files against the make-var idiom).
- **`make rebuild-decision`** supplies the day (`date +%u`, now the repo's ONE call
  site for this) and prints the outputs; `refresh-bot.yml`'s `build` and
  `openspec-image` jobs append them to `$GITHUB_OUTPUT` with **`set -o pipefail`**.
  That last part is load-bearing: `cmd | tee` reports *tee's* status to GitHub's
  `bash -e`, so without pipefail a failed decision would be a green step with empty
  outputs and every build below (gated on those outputs) would be skipped.
- **Tests**: `tests/test_ensure_image.py` drives every branch (current / missing tags
  / missing `:latest` / Sunday / forced, each asserting its `reason`) plus the strict
  `FORCE` parsing; `tests/test_workflows.py` asserts the workflow delegates, keeps no
  inline probe or clock, sets pipefail, and — the cross-check that catches a renamed
  key — that **every `steps.decide.outputs.*` the workflow consumes is a key the
  script prints** (which is how `tag` vs `openspec_tag` got caught here).
- Five existing assertions in `tests/test_workflows.py` that pinned the inline shell
  (`HASHED=0`, `[ "$FORCE" = "true" ]` twice, `decide.outputs.tag`) moved to the new
  contract — the rule's *behaviour* is now asserted where the rule lives.
- `ARCHITECTURE.md` (the three job rows, the new target, the script row) and the
  README bullet (through its template) say the decision is data.

## Not covered

- **`AGENTS.md` is untouched** — this change should extend rule 6k's rulebook text
  with the "decision as data" clause and add a section-8 row. The file is protected
  and no approval was given, so it is deliberately not in this change.
- The `published()` fail-open on a registry error (a transient failure reads as "not
  published" and triggers a needless rebuild) — filed as its own issue from this
  change's `findings.md` (rule 6g).
- Publishing the agent image deliberately (#206) and the probe's token flow (#232)
  are separate, already-tracked work.
