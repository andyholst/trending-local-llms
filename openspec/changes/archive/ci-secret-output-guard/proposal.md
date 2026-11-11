# Proposal: ci-secret-output-guard

Issue: #219

## Why

`make secret-scan` (gitleaks) only catches a committed credential **value**. It
cannot see the ways a legitimate secret's *value* leaks at run time, which is
the class of leak `asimov-agent/llgenie` guards with
`scripts/check_secret_output.py` (#283) and this repo does **not**:

- `echo "$NOUS_API_KEY"` — the value reaches the log stream.
- `docker run -e KEY=$KEY` / `--build-arg KEY=$KEY` — the value lands in the
  process list (`ps`) and any `--debug` output, for every user of the host.
- `${{ secrets.X }}` interpolated inside a `run:` block — it becomes part of the
  script text and its output, instead of riding in `env:`.
- `set -x` in a shell file that also reads a secret — xtrace prints every
  expansion.
- a bare `env` / `printenv` whose output reaches a log.
- a credential-shaped literal committed to the tree.

The measurement is already in: llgenie's guard, adapted to this repo's key set
(`NOUS_API_KEY, NOUS_PORTAL_API_TOKEN, GH_TOKEN, GITHUB_TOKEN,
FIXBOT_DISPATCH_TOKEN, HF_TOKEN, TYPESAFE_API_KEY, FIRECRAWL_API_KEY`), was run
over this repo's tree and reports **0 violations today**. But nothing enforces
that going forward: a one-line regression (an echo of a token, a `-e KEY=$KEY`,
a `${{ secrets.X }}` in a `run:`) would ship green, and this repo runs the same
payloads in `refresh-bot.yml`, `issue-bot.yml`, `issue-review-bot.yml`,
`fix-bot.yml` and `qa-validate.yml`.

## What Changes

- **`scripts/check_secret_output.py`** — the guard, ported from llgenie's and
  adapted to this repo's secret-shaped variables (name-only; a value never
  appears in the source). Pure stdlib + host filesystem scan, like `make lint`:
  host and container agree.
- **`tests/test_secret_output.py`** — one test per rule: each leak shape is
  broken on a fixture (one violation, the right rule id), and the guard is then
  run over THIS repository, because a rule the repo itself violates is not a
  rule. No-skip policy: a missing prerequisite is a loud failure.
- **`make check-secret-output`** (the gate) and **`make secret-output-report`**
  (what each file does with a secret-shaped variable) — both named in
  `ARCHITECTURE.md` (rule 6h).
- **Wired where it bites** (rule 6d): a step in `qa-validate`'s `validate` job
  next to `make secret-scan`, and `tests/test_secret_output.py` in `make test`.
- **AGENTS.md**: extends rule **3d** (the no-committed-credential rule) to name
  the no-VALUE-leaks convention, plus a §8 guard row. Comment on #219
  documents the sections (rule 3c, review-required).

## Impact

Compatibility: additive — a new guard and a new step; no existing behaviour
changes. The clean tree stays green; only a future regression goes red, which is
the point.

## Not covered

Detecting a **defined-but-unused** repo secret (a workflow that references a
secret the repo does not define in its settings) is a separate analysis issue,
not this change.
