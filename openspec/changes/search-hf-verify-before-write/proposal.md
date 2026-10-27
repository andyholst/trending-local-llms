# Proposal: search-hf-verify-before-write

Issue: (this run's `issue.md` — the input carried no issue number; the measured
failure is refresh PR #416 / fix-bot run 39306663973)

## Why

The search legs wrote a plausible `Qwen/<the model's own name>` for three models
on refresh PR #416, and `make validate` failed the PR with three `raw-hf` 404s.
`fix-bot` then repaired the branch by replacing every guessed id with one that
resolves (`Qwen/Qwopus3.6-35B-A3B-Coder-MTP` →
`Jackrong/Qwopus3.6-35B-A3B-Coder-MTP-GGUF`, and two more). The repair is silent
by design, so the prompt never learns and the next refresh makes the same id up
again — the "fix the class, not the PR" case AGENTS.md names explicitly.

Two halves of the gap are measurable in the tree:

- `.hermes/skills/data-search/SKILL.md` — the preloaded contract — never asks the
  leg to look the `hf` id up. `skills/gather-data.md` §5 describes the lookup,
  but the leg's contract is the project skill (rule 6p), and the skill's rules
  do not include it.
- `scripts/update_trending.py::write_raw_snapshot` collapses a pasted HF URL
  prefix and normalises a bad `id`, but never asks the Hugging Face API whether
  the repo exists. The verification added for #333 runs at **ingest**, and only
  for a NEW model — after the raw snapshot has already been written and the
  refresh has already opened a PR.

So one guessed id costs a whole fix round, and the id is rewritten rather than
refused.

## What Changes

- **`scripts/update_trending.py` — `write_raw_snapshot(..., verify_hf=False)`.**
  With `verify_hf` on, every model `hf` and every `formats[].hf` is checked with
  the existing `hf_repo_resolves` (the one definition, issue #333). A **definitive**
  answer (401/404) refuses the value before it lands: the model row is dropped (or
  the bad format entry is dropped) and one loud `[write-raw] WARN:` line names the
  backend, the model and the refused id, so the leg can look it up and re-run. An
  **indeterminate** answer (429/5xx/transport) keeps the value — a rate-limited API
  must never look like a fabricated id.
- **`scripts/update_trending.py` — `main()` passes `verify_hf=True`** to the
  `--write-raw` call, so the production search path enforces it. The default stays
  `False`, so direct callers (every existing write-raw test) make no request.
- **`scripts/update_trending.py` — `normalize_hf_ref`** routes through
  `hf_id.normalise` after collapsing the `https://huggingface.co/` prefix, so
  `hf.co/...`, `www.huggingface.co/...`, a query string or a trailing slash is
  reduced to `owner/repo` before it is verified. One HF-id definition (rule 6d).
- **`.hermes/skills/data-search/SKILL.md`** — a rule that the `hf` id (and every
  `formats[].hf`) must be the canonical `owner/repo` confirmed with the
  authenticated HF API / `hf search models`; a plausible `owner/model-name` is not
  a lookup, and an id that cannot be confirmed is left out (the `--write-raw` gate
  refuses it and says so).
- **`tests/test_ingest_hf_verify.py`** — write-raw tests against the existing real
  local HF stand-in: a definitive 404 drops the model with a warning naming it, a
  429 keeps it, the default makes no request, the CLI turns verification on, and
  the skill states the lookup.
- **`AGENTS.md` §8** — the row for this guard, and **`ARCHITECTURE.md`** — the
  `scripts/update_trending.py` row now names the write-time check.

## Impact

`scripts/update_trending.py`, `.hermes/skills/data-search/SKILL.md`,
`tests/test_ingest_hf_verify.py`, `AGENTS.md`, `ARCHITECTURE.md`, this OpenSpec
change and `OPENSPEC.md`. No `data/**` change: the gate refuses a fabricated id
before a snapshot is written, and a real model whose id is merely rate-limited is
kept unchanged.

The production path is the `--write-raw` CLI the four search recipes already run;
`main()` turns the check on there, so a guessed id is refused in the leg that made
it rather than in CI two pipelines later. A dropped row is a refusal before it
lands, not a removal from the store (rule 3b) — nothing was ever in the store or
the snapshot to remove.

## Not covered

- **Repairing a refused id.** The leg must look it up and re-run; a repair is a
  verified lookup, never a guess (AGENTS.md §6b). fix-bot keeps its link-repair
  role for a dead link that reaches the store another way.
- **Verifying `engine_repo` or `source_post` at write time.** The same class
  exists for an engine repo, but the issue's acceptance criteria name the HF id;
  it is filed as a finding rather than widened into this change.
- **Normalising an engine name's casing** (`EXLlamaV3` vs `ExLlamaV3`). That is
  the same "written without a lookup" shape on the engine side, but a different
  registry seam; it is filed as a finding.
- **Missing `hf`.** `check_links_present` already fails a model with no HF link;
  this change refuses a *present but unverified* id.
