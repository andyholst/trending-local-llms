# Proposal: registry-hiccup-is-not-absence

Issue: #235 — `tech-debt: \`published()\` reads a registry hiccup as "not published", so a transient outage rebuilds the toolchain`

## Why

Every pull-vs-build decision in `scripts/ensure_image.py` goes through one predicate:

```python
def published(ref: str) -> bool:
    return subprocess.run(["docker", "manifest", "inspect", ref], ...).returncode == 0
```

A non-zero exit is treated as "the tag does not exist". But `docker manifest inspect`
exits non-zero for two very different facts:

- **the tag is absent** (`manifest unknown`, `no such manifest`, `not found`), and
- **the registry could not answer** (a network error, a 5xx, a rate limit, an auth hiccup).

The second was read as the first, so a transient outage made `ensure-base` / `ensure-test` /
`ensure-openspec` **build from the checked-out tree** — an expensive rebuild of the
toolchain, and, on the publish path, a chance to overwrite a perfectly good tag with a
build of whatever revision happened to be present. `decide` (the rebuild rule the workflow
prints) inherited the same guess.

## What Changes

- **`published()` returns two facts: present (True) and ABSENT (False)**, and raises
  `RegistryUnknown` for anything else — the decision is made on docker's own wording
  (`manifest unknown` / `no such manifest` / `not found`), never on a bare exit code.
- **`main()` turns that into a loud exit 1**, printing docker's own words: “the registry
  did not say the tag is absent, so this is not a reason to build or push — retry when the
  registry answers”. Both `ensure-*` and `decide` go through it, so a workflow's rebuild
  decision fails instead of guessing.
- **The test stub learns to fail like a registry**: `FAKE_DOCKER_MANIFEST_ERROR` makes
  `manifest inspect` print that message and exit 1, and the absent case now prints the real
  `manifest unknown:` wording.
- **`tests/test_ensure_image.py::test_a_registry_hiccup_is_a_loud_failure_not_a_rebuild`**:
  a hiccup on `ensure-base` exits non-zero, names docker's message, and **builds nothing**;
  the same call with a genuinely absent tag still builds; `decide` refuses to decide.

Verified RED against the pre-change script (5 failures — it rebuilt on the hiccup and
`decide` decided) and GREEN after (`PASSED 83 | FAILED 0`).

## Impact

`scripts/ensure_image.py` (one predicate, one exception, a dispatching `main`),
`tests/test_ensure_image.py`, this OpenSpec change and the regenerated `OPENSPEC.md`. The
public behaviour is unchanged when the registry answers; it fails where it used to guess.
No make target, stage, job or image changes (`ARCHITECTURE.md` unchanged, rule 6h).

## Not covered

- **Retrying the probe.** A retry could absorb a one-second hiccup, but the pipelines
  already re-run; the defect was the SILENT wrong answer, not the missing retry.
- **`base_ready()` / `docker image inspect`** — that asks the local daemon, not the
  registry, and has no absence/unknown ambiguity of the same kind.
