# An implementation PR / issue / commit that follows the message pattern

**Issue:** [#771](https://github.com/andyholst/trending-local-llms/issues/771)
PR: #772
**Capability:** `message-pattern-enforcement`

## Why

The bot-open implementation PR body (`scripts/pr_body.py::render`) carries short
contract paragraphs (Spec-tracked / Additive only / Analysis ships issues /
Auto-merged) but no deterministic **message pattern**, and nothing validates that
a PR body, an issue body, or a commit message follows one. The user-facing
directive is explicit: every issue and PR must be created with `closes <issue>`
and carry **Why / What / How / Benefits / Technical Solution** sections, and CI
must validate that PR body content, issue content, and the commit message follow
this pattern. Today a PR can merge with any prose shape; the repo's own closure
gate (`make pr-closure`, rule 6e) verifies only the closing-keyword binding, never
the sections — so a reviewer reads a different structure on every change and the
`Why`/`What`/`How`/`Benefits`/`Technical Solution` sections that make a change
reviewable appear nowhere by default.

## What Changes

- **`scripts/pr_body.py`** —
  - `MESSAGE_SECTIONS = ("## Why", "## What", "## How", "## Benefits", "## Technical Solution")`;
  - `section_problems(text) -> list[str]`, a deterministic parser: each `##`
    header must appear in order and be followed by at least one non-blank,
    non-header content line;
  - `render(issue, branch)` emits the five sections (kind-appropriate default
    prose) between the existing intro and the single `Closes #<issue>` line, so
    the anchors the current tests assert (`Implements #<n>` first, `Closes
    #<n>` last) are preserved;
  - `main()` gains `--check-body-file <f>`, which runs `section_problems` +
    `pr_closure.check` on a body file and exits 1 listing every problem.
- **`Makefile`** — host `pr-message-check`, `issue-message-check` and
  `commit-message-check` targets (mirror `pr-closure`):
  `@python3 scripts/pr_body.py --check-body-file / --check-issue-file /
  --check-commit-file "$(…)"`, guarded by `-n "$(…)" || usage`.
- **`.github/workflows/pr-closure.yml`** — the existing `closure` job runs
  `make pr-message-check` after `make pr-closure` on every PR, so every PR body is gated on
  `opened`/`edited`/`synchronize`. The same body-on-screen model now also covers the OTHER two
  artifacts the repo composes: a `push` to `master` runs `commit-message-check` on
  `.head_commit.message`, and `issues:opened/edited/reopened` runs `issue-message-check` on an
  issue body that DECLARES the pattern (the `message-pattern-opt-in` marker declared once in
  `scripts/bot_markers.py`), so a
  structured data-gap issue's own schema is never forced through the shape.
- **AGENTS.md** — the message pattern is documented as repo behavior (rule 6e
  region): what the five sections are, that `closes <issue>` binds one reference,
  and that the pipeline validates the PR body and, by construction, the squash
  commit message.
- **`tests/test_pr_message.py`** — standalone house style (no pytest import):
  composer output matches the pattern; a body missing each section / with an
  empty section / out of order is refused; `title()` matches the
  Conventional-Commit shape and names the issue; the `--check-body-file` CLI
  refuses non-conforming and accepts conforming bodies.
- **`ARCHITECTURE.md`** — the `pr-message-check` target row and the regenerated
  §10 block (`make architecture-refresh`).

## Impact

The artifact that decides whether an issue closes on merge now also carries the
reviewable structure a reviewer needs, and the pipeline refuses a PR whose body
skips a required section before auto-merge. The squash **commit message** follows
the pattern by construction: the title comes from `pr_body.title()` (locked by a
test) and the body from the validated PR body. `make pr-message-check` is called
by `pr-closure.yml`, so it is not a target nothing runs (rule 6m), and its code is
reached only through that target (rules 6d/6m). No data, no schema, no README and
no change to the repo's data validators.

## Not covered

- **Rewriting every historical issue body.** Only artifacts the repo composes are
  changed; existing bot-filed issues keep their `## Finding`/`## Origin` shape.
- **Scanning UNMARKED issue bodies.** A data-gap / tech-debt issue has its own structured
  schema (`## Goal` / `## Ranked gaps` / the attribution marker) that does not fit the
  five-section shape and MUST NOT be forced through it. Only an issue that carries the
  invisible `message-pattern-opt-in` marker is validated — so pattern issues are
  enforced at the moment they are filed while legacy structured issues stay green.
- No change to the closing-keyword semantics already owned by `pr_closure.py`
  (rule 6e).
