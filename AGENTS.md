# AGENTS.md — Operating behavior for agents in this repo

This file defines how any agent (a coding agent, a Hermes refresh session, or
an AI maintainer) behaves when working in **trending-local-llms**. Read it
before doing anything. If a contributor reverts a change and points here, that
change violated one of these rules.

## 1. What this repo is

A living index of **open-weight LLMs** that people actually run locally,
ranked by **real X engagement** and **measured t/s per inference engine**. Every
figure is community-reported on X (actual posts, not vendor claims), with the
hardware, quant and engine it was measured on. Data spans a rolling window but
retains 30 days of history.

## 2. Hard rules (non-negotiable)

1. **Never push to `master`/`main` directly — by manual action or automation.**
   Every change lands on a **feature branch** and is merged via a **PR reviewed
   by a human**. The CI pipeline may *open* PRs but must never *merge* them.
2. **Never fabricate data.** No engagement number, like count, or t/s figure
   may be invented. It must trace to a **real X post** (via the lightbrd.com
   mirror technique in `skills/gather-data.md`) or be marked explicitly as
   `(est)` / `estimated` when it is a reasonable projection from quant size.
3. **Never wipe history.** If a model stops trending or gets no new updates,
   it stays in the data store and the README — it just sorts **further down**.
   Only remove a model with an explicit human decision (e.g. confirmed dead
   repo / wrong model).
4. **Engagement-first, t/s second.** In the "most loved" rank: models are
   ranked by 7-day X engagement (likes/comments/views/interactions), with
   highest t/s as the tie-breaker **within** a rank. Do not reorder the whole
   table purely by t/s.
5. **t/s is always per engine.** A bare "40 tok/s" with no engine is not a
   valid entry. Format: `t/s (engine, hardware/quant)`.
5b. **Every entry carries its links.** Each model row must include its Hugging
   Face link, and every engine measurement must link to the engine's repo
   (or the specific model/draft repo that produced the figure when that is
   more precise, e.g. a DFlash2 draft). No bare engine name without a link
   in the generated tables or the engine guide.
6. **Backends are equal categories, not primary/secondary.** NVIDIA (CUDA),
   Apple (Metal), and CPU each render as a **first-class table**. A model
   measured on multiple backends appears under each with its own engine + t/s.
   The headline scope is GPU models serving **8–48 GB VRAM** (consumer/
   workstation); CPU and Metal tables exist alongside, not demoted below it.
   Do not pull in datacenter-only multi-TB models as top-line entries.
6b. **Change the data/format/contract → update the tests, in the same change.**
   Any edit to a contract (`model_contract.json`, `search_contract.json`), a
   data format (models.json model shape, raw search-snapshot shape), the README
   template, or a validator rule MUST update the corresponding tests in the
   same commit so `make test` still passes. The contract shape lives in per-file
   helpers — `good_store()`/`store()`/`sample_store()`/`cuda_table()` — so a
   format change is a one-place edit that ripples to all assertions. When a
   requirement changes, update the fixture helper(s) plus any test that asserts
   on the changed field; never leave a test suite that only matches the old
   contract. CI runs `make test` on every pipeline, so a contract change without
   a test update goes red and must not be merged.
6c. **The pipeline is code too — test it, not just the data.** Every failure
   that reached CI so far was in the orchestration layer (a Makefile recipe, a
   reasoning budget, a token scope, an approval gate, a shell loop), which data
   tests cannot see. Any change to the `Makefile` hermes recipes, the
   `.github/workflows/*.yml` wiring, `scripts/fix_loop.sh` or the live smoke
   targets MUST keep (or extend) the guards in §8 green in the same change. A
   regression fixed without a test that FAILS on the old code is not fixed.
   Verify a new guard by running it against the old file (`git show
   origin/master:<file>`) and confirming it goes red.

## 3. Data source & collection

- X content comes from the **lightbrd.com mirror** (`lightbrd.com/search?f=tweets&q=...`),
  NOT x.com directly (bot-walled) or Nitter (mostly dead). See
  `skills/gather-data.md` for exact queries and the extraction method.
- For each post, record: author, timestamp, text, **likes / comments / views /
  interactions**, and any measured t/s figure with its hardware + quant.
- **`source_post` must be the post itself** — `https://lightbrd.com/<user>/status/<id>`,
  never the bare mirror URL or a profile page — and the post's likes /
  comments / reshares / views go on the same measurement as integers. A
  placeholder URL or missing counts scores the minimum 1 in `score_7d`, so the
  ranking degrades to a post count. `make validate` prints a report-only
  **post-signal coverage** line (store + each raw snapshot) so this is visible.
- When the mirror is unreachable, **preserve last-known data** — never blank
  the store or README. The pipeline must fail gracefully.

## 4. Data store & regeneration model

The README is **generated**, not hand-maintained:

- `data/models.json` — canonical store. One row per model with: id, name, full
  name, HF link, license, params, type (LLM / GGUF / other), VRAM tier,
  backend(s), **supported_engines** (list of engines the model is supported by),
  and a list of **per-engine t/s measurements**, each with date, engine,
  hardware, quant, and the engagement + source post URL of the newest post
  supporting it. **No duplicate models** (by id or name). The exact JSON schema
  is documented in `data/MODEL_CONTRACT.md` — read it before adding/editing a
  model.
- `scripts/update_trending.py` — fetches new X data, merges it into the store,
  applies 7-day trending sort + 30-day retention, then regenerates `README.md`.
- **`Makefile` is the single source of truth for every stage** — CI and local
  runs use the exact same targets, and **every public `make X` runs inside the
  Docker container** (Python deps + Hermes CLI baked in; the repo is
  bind-mounted at `/workspace`, so all data writes back to the host). Internal
  `_`-prefixed recipes hold the host commands; the public names are docker
  wrappers. Targets: `make docker-build` (build the image once),
  `make setup`, `make search-nvidia|search-metal|search-cpu`
  (the three separate searches, each writing its own
  `data/raw/<backend>-<UTC>.json`), `make search` (all three), `make merge`
  (ingest raw → models.json + README + snapshot), `make validate` (QA),
  `make validate-search|validate-mapped|validate-readme` (stages), `make test`
  (unit tests), `make fix` (correct a red CI with Hermes), and `make refresh`
  (the full pipeline = setup + search + merge + validate + test, in one
  container). Live smoke targets (real network, bounded, skip cleanly without
  keys): `make search-smoke [BACKEND=nvidia|metal|cpu]` (the exact Firecrawl →
  lightbrd scrape of every search query, **3 s cap per query**),
  `make hermes-smoke` (one real Hermes call through the `nous-deepseek` alias
  with every key the pipeline passes, incl. `HF_TOKEN`), and
  `make pipeline-smoke` (both). `make docker-test-build` builds the test image
  (needs the base from `make docker-build` or a GHCR pull). Run after
  `make docker-build` with `NOUS_API_KEY=... FIRECRAWL_API_KEY=... make refresh`.
- **Hermes invocation (every `hermes -z` recipe).** One logical shell command:
  the `-z "..."` line MUST end with ` \` so `-m nous-deepseek --reasoning
  $(HERMES_REASONING) --yolo` stays on the same command. Without it make runs
  the model flags as a separate command and Hermes starts with NO alias — it
  then auto-routes to whatever provider key is in the env (`HF_TOKEN` →
  Hugging Face → HTTP 403), which silently broke every fix-bot run. Every call
  passes an explicit `--reasoning` level: `HERMES_REASONING := low` for the
  mechanical searches, `HERMES_FIX_REASONING := medium` for fix-bot. Raising
  `max_tokens` does NOT fix "No visible answer was produced … reasoning
  consumed the entire budget" — the model just reasons longer; lowering the
  reasoning level does. Prose inside a prompt uses single quotes; only the
  JSON body uses `\"`.
- **Base image is built ONCE and pulled, never rebuilt per-run.** The base
  image (`ghcr.io/andyholst/trending-local-llms:latest` — Python deps + Hermes
  CLI baked in) is **built and pushed to GHCR only by `refresh-bot.yml`**, and
  only when it does not exist yet or it is **Sunday** (weekly Hermes update).
  Every other pipeline that uses the base image — `qa-validate.yml` (PR CI) and
  `fix-bot.yml` — **pulls** it from GHCR and **only builds the TEST image**
  (`Dockerfile.test`, base + current `requirements-test.txt`) on each run. They
  must never rebuild the base image locally. The GHCR image is public, so no
  login is needed to pull it.
- **Snapshots:** every refresh writes a timestamped snapshot to
  `data/snapshots/trending-<UTC>.json` (full store). This is the history that
  proves no model was ever removed and lets the README be rebuilt from any
  point.
- **QA/validation:** `scripts/validate.py` runs in CI (`.github/workflows/
  qa-validate.yml`) on PRs and pushes. It enforces: (1) no model removed vs the
  previous snapshot, (2) every model has name/full_name/HF link/license/params/
  VRAM + at least one engine measurement with engine name + t/s + repo link,
  (3) each README backend table is sorted by highest t/s descending, (4) every
  model in the store appears in the README, (5) every README **markdown table is
  well-formed** (parsed with `markdown-it-py`: separator column count == header,
  every data row == header, no empty cells), (6) **every link resolves** — from
  `data/models.json` (engine registry, model HF, per-format HF, source_post),
  `data/raw/*.json` search snapshots, and `README.md`, HEAD/GET-checked; a
  404/410 or connection error fails CI (403/429/5xx are indeterminate), and a
  known-good engine repo URL that was wrong is auto-corrected in the store.
  `check_readme_tables_wellformed` + `check_links_resolve` are registered in the
  `make validate` stages so a malformed table or a dead/wrong link in any new
  raw snapshot, the store, or the README fails CI. This is a **validation**
  action, not a data-gathering bot.
- **Ingest is contract-driven.** `normalize_model` / `ingest_raw_snapshots`
  prune a model's top-level `engagement` to exactly the keys declared in
  `data/model_contract.json` (read at runtime — no second list to drift) and
  coerce counters to non-negative ints. The search contract leaves that object
  open, the store contract closes it; without the prune, one extra key the
  search agent writes (it was `reshares`, on every model) turns every refresh
  PR red on a schema error. Real recurring keys are declared in BOTH contracts
  (additive); stray keys are dropped and logged as `[ingest] … pruned`.
- **Never hand-edit the generated tables.** Fix the template or the data store
  instead, then regenerate. The "How to contribute" section points contributors
  at the store, not direct table edits.

## 5. Sort rules

1. **Trending (last 7 days, has new engagement):** on top, ranked by engagement.
2. **Recent (last 30 days, no new engagement):** retained, grouped below.
3. **Stale (>30 days, no new updates):** retained, sorted furthest down — old
   t/s and supported engines still shown, clearly marked with the measurement
   date so a reader knows it is not current.

**How the trend is computed** (`recompute_7d_engagement`, run on every sort):

- **Posts.** `engagement.seen_posts` keeps every real post (`…/status/<id>`)
  ever seen; placeholder posts (`https://lightbrd.com/`, profile pages, non-X
  links) are DERIVED — rebuilt from the model's current measurements on every
  sort, keyed url + date + engine + hardware + quant. Never key on `tps`:
  `merge_engines` rewrites it (`60-91` → `91`) and that used to mint a
  duplicate post on every refresh (Bonsai showed 9 posts for 5). A real post
  re-scanned across overlapping 3-day windows counts once. Posts older than 30
  days are pruned; the model row never is.
- **Buzz** (`buzz_7d`, alias `score_7d`) = Σ over posts in the last 7 days of
  `1 + 0.5·log2(1 + likes + 2·comments + 3·reshares) + 0.25·log10(1 + views)`.
  Breadth first: every post counts ≥ 1 and unknown counts read as 0 (never a
  penalty), so a post with ≤ 10 interactions is worth < 4 posts, while a
  5,000-like post (~8) can still lead. Never make this linear again — one
  lightly-engaged post outranked nine posts that way.
- **Speed** (`speed_bonus`) = `log2(1 + t/s ÷ 10)` of the model's fastest
  **in-scope** measurement, only while it has posts in the window. In scope =
  consumer/workstation hardware: GPUs with ≤ 48 GB total VRAM (explicit
  `NN GB`, a known-card table incl. laptop variants, `Nx` multiplied), every
  Apple Silicon and CPU measurement. Datacenter parts (H100/H200/A100/B200/
  GB200/MI300…) or > 48 GB never earn speed. 10 t/s → +1, 70 → +3, 150 → +4.
- **`trend_score` = buzz + speed.** Order: band (trending → recent → stale) →
  `trend_score` → `posts_7d` → peak t/s (`_tps_core`, max of a range) → name.
  `posts_7d` = distinct posts in 7 days (`last_7d_likes` mirrors it).
- The README is rendered **as of `generated_utc`** (not the wall clock), so the
  validator's re-render is byte-stable days after merge.

## 5b. README layout (generated by `render_readme`)

Every section uses the same `measurement_backend(e, registry)` (CUDA / Metal /
CPU from explicit Apple/CPU hardware first, then the engine registry's
`backend` when it names ONE backend, then the built-in engine map, then
keywords; CUDA only as the last resort) and
`best_measurement()` (highest t/s core, newest date on a tie), so no two tables
can disagree about where a figure belongs.

1. **❤️ Most loved** — one row per model in rank order: model (HF link, full
   name · params · license), status (🔥 / 🕑 / 💤 + last seen), **Trend**
   (`trend_score`, with `buzz · N posts · speed +X (t/s, hardware)` beneath),
   the **best** t/s for each of CUDA / Metal / CPU with engine
   link · hardware · quant (`+N more` when there are others), VRAM, why. No
   `#` rank column — rank is row order.
2. **🧭 Which inference engine runs what** — models × engines that have at
   least one measurement; each cell is the best t/s per backend on that engine.
3. **🟦 / 🟨 / 🟩 backend tables** — numeric `Peak t/s` column (the sort key
   the validator reads by header name) + every measurement as
   `engine **t/s** · hardware · quant · date`, best first.
4. **⚙️ Engine guide** — engine link, backend, models measured, best for.

Free text in cells is pipe-escaped (`\|`); the table validator splits on
unescaped pipes only.

## 6. Refresh workflow — GitHub Actions invoking the Hermes CLI

The refresh is driven by the **GitHub Actions pipelines** (`refresh-bot.yml`,
`fix-bot.yml`), which invoke the **Hermes CLI** (deepseek-v4-flash-0731 via the
Nous portal, using the repo's `NOUS_PORTAL_API_TOKEN` secret). The agent loads
this `AGENTS.md` and the `gather-data` skill, then:

1. Runs the **three search groups** against **lightbrd.com only**, fetched via
   the Firecrawl scrape API (`FIRECRAWL_API_KEY`) — NVIDIA/CUDA, Metal/MLX, and
   CPU (see `skills/gather-data.md`), last-3-day
   window. **One search at a time** to keep context small: run a query, capture
   its results, then move to the next — never hold all results in context at
   once. Each search writes its own timestamped raw snapshot to
   `data/raw/<backend>-<UTC>.json`.
2. After gathering, **reviews the captured data** and updates `data/models.json`
   via `resolve_model_mapping` (id → name → hf) + `ingest_raw_snapshots`:
   adds new models, updates existing models' t/s + engagement, and **never
   removes any existing model**.
3. Applies the 7-day trending / 30-day retention sort and regenerates
   `README.md` via `scripts/update_trending.py`; writes a timestamped snapshot.
4. Commits on a **feature branch** and opens a **PR** to `master` for manual
   review, using the owner-scoped PAT (`FIXBOT_DISPATCH_TOKEN`) for the push
   and `gh pr create` — never the default `GITHUB_TOKEN` (see §6b). It never
   pushes to or merges `master` itself.

## 6b. Three pipelines (refresh → validate → fix)

- **`refresh-bot.yml`** — the **bot** pipeline. Scheduled (daily) + manual
  dispatch (owner only). Per backend (nvidia / metal / cpu, parallel matrix):
  3 s reachability smoke → Hermes routing smoke → Hermes search. Then
  `aggregate` (runs even if a leg failed): merge → soft validate → **opens a PR
  only when there is new data**, authored by the owner PAT so qa-validate
  starts without an approval click. It does NOT dispatch fix-bot — that is
  qa-validate's job, after it has validated. Never auto-merges.
- **`qa-validate.yml`** — the **PR CI** pipeline. Runs on every PR (including
  workflow-only PRs — the wiring is under test), push to master, or dispatch.
  Three jobs:
  - `validate` — deterministic: `make validate`, `validate-search`,
    `validate-mapped`, `test`. This is the only job fix-bot is asked to repair.
  - `live-smoke` — real network, bounded: `make search-smoke BACKEND=<b>` for
    nvidia, metal, cpu (3 s cap per query), `make hermes-smoke`, and
    `make validate-fetch` (real search, `--require-hits`). An outage here is
    infra, not data, so it never dispatches fix-bot.
  - `dispatch-fixbot` — only when `validate` failed on a same-repo
    `ci/trending-refresh-*` PR: dispatches fix-bot with `pr_number` + `branch`
    using the owner PAT, unless the PR already has 2 `fix-bot:` commits (a fix
    that didn't stick → manual review, no loop).
- **`fix-bot.yml`** — the **fix** pipeline. `workflow_dispatch` ONLY (no
  `workflow_run`: it double-fired with the dispatch and was suppressed for bot
  PRs). One run per PR (`concurrency`). Resolves the PR (refuses
  `master`/`main`), checks out the branch with the PAT, runs `make
  hermes-smoke`, then `scripts/fix_loop.sh`: run the deterministic checks →
  green? stop → else write `qa-report.txt` and `make fix` (the `_fix` prompt
  reads that report first) → re-check, at most `FIX_ROUNDS` (3) Hermes
  attempts. It commits (`fix-bot: …`, git identity set) and pushes with the
  PAT **only when the loop ends green** — the PAT push re-triggers
  qa-validate. Still red → nothing is pushed and the failing lines are
  commented on the PR. Either way a human reviews and merges.

**Tokens.** `FIXBOT_DISPATCH_TOKEN` is a fine-grained PAT scoped to this repo
only: Actions R/W, Contents R/W, Pull requests R/W. It is used for (1) the
refresh PR push + creation, (2) qa-validate's fix-bot dispatch, (3) fix-bot's
checkout, push and PR comment. The default `GITHUB_TOKEN` cannot do any of
these usefully: a PR it creates is authored by `github-actions[bot]` and every
`pull_request` run on it waits for approval; a push it makes starts no
workflows; and it gets `HTTP 403 Resource not accessible by integration` when
dispatching another workflow (no run is created, so there is nothing to
approve).

**Link-repair behavior for fix-bot (when CI reports a dead/wrong link).** The
CI link validator (`scripts/validate.py` `check_links_present` +
`check_links_resolve`) only **reports** which link failed — it never calls the
LLM. The fix-bot is the one that repairs. For each failing link it MUST search
for the correct one and verify it resolves before writing:

- **Model / format Hugging Face link** (`model-hf`, `format-hf`, `raw-hf`):
  find the canonical repo id via the Hugging Face CLI / `huggingface_hub`
  (e.g. `hf search models <name>` or the HF API
  `https://huggingface.co/api/models?search=<name>`), then confirm
  `https://huggingface.co/<id>` returns 200.
- **Engine / inference-server link** (`engine-registry`, `source_post`): do a
  regular Firecrawl web search (`FIRECRAWL_API_KEY`) for the engine's canonical
  repo URL and confirm it resolves. Known-good engine repos are in
  `KNOWN_ENGINE_URLS` in `scripts/validate.py`.
- Only write a link the fix-bot has actually verified resolves. If it cannot
  find a verified replacement, it leaves the link and reports it in the PR body
  for manual review — it never invents a URL.
- It updates `data/models.json` (and the raw snapshot if the wrong link came
  from `data/raw/*.json`), then regenerates `README.md` via
  `scripts/update_trending.py`. See `skills/gather-data.md` §3 for the exact
  search technique.

Contract evolution for fix-bot: when validation fails because the search
agent now emits a **new key/value that the data genuinely needs** (a new
engine, backend, format, engagement field, or top-level metadata that is
real and would be lost by pruning), fix-bot SHOULD update the contract
(`data/search_contract.json` and/or `data/model_contract.json`) to declare it,
**and update the corresponding tests in the same change** (rule 6b — the
contract shape lives in the per-file helpers, so a format change is a
one-place edit that ripples to all assertions). Only add a key when it is
real, traceable data — never to paper over a malformed snapshot. If a new key
is noise (a one-off artifact of a bad prompt), PRUNE it via
`self_correct_raw` instead of widening the contract. Distinguish the two: a
key that recurs across multiple backends/runs and carries real value → widen
the contract + tests; a stray/empty/malformed key → prune. Manual review is
still required before either lands.

**Contract versioning — additive vs breaking changes.** The contract is
versioned so OLD data can always be validated against the OLD contract and
NEW data against the NEW contract:

- **Additive change (backward-compatible):** adding a NEW key, a new enum
  value, or widening a constraint does NOT break existing data. Update the
  SAME contract file in place (`data/search_contract.json` /
  `data/model_contract.json`) and the tests in the same change. Old snapshots
  still validate (they simply lack the new optional key). No version bump.

- **Breaking change (backward-incompatible):** removing or renaming an
  existing key, changing a key's type, or removing an enum value makes OLD
  data fail the NEW contract. Do NOT edit the existing file in place. Instead
  create a NEW versioned contract — `data/search_contract.v2.json` /
  `data/model_contract.v2.json` (and so on for v3, v4, …) — that declares the
  new shape, and keep the old file untouched so old snapshots still validate
  against it. Update the validator (`scripts/validate.py`) and the tests to
  pick the right contract per data set: old raw snapshots / old models.json
  validate against the old contract, new ones against the new. The
  `generated_utc` timestamp (or a `contract_version` field) is what routes a
  snapshot to the correct contract version.

Rule of thumb: if every existing record still conforms after the change, it
is additive → edit in place. If any existing record would now fail, it is
breaking → new `*.vN.json` contract + validator/test routing. Never silently
re-validate old data against a changed contract.

Flow: bot refreshes + opens PR (PAT) → qa-validate (`validate` + `live-smoke`)
→ if `validate` is red, qa-validate dispatches fix-bot → fix-bot loops until
green (≤3 Hermes rounds) and pushes (PAT) → qa-validate re-runs → green → human
merges. Red after the loop → PR comment, manual review. Max 2 fix-bot pushes
per PR.

**Fix the class, not the PR.** If the same validation failure shows up on
consecutive refresh PRs (same field, same kind of wrong link, same missing
engine), it is a defect in the search prompt, the contract, or the ingest
code. Fix it there, with a test, instead of letting fix-bot patch every PR.

Rules for the refresh run:
- **Only lightbrd.com** is used for X signal — no other X source.
- If the mirror is unreachable, **preserve last-known data**; never blank the
  store or README. Report the failure in the PR/commit instead.
- The PR body states what changed, how many models were added/updated for
  trending, and that manual review is required before merge.
- The Nous token is read from the repo secret `NOUS_PORTAL_API_TOKEN`; never
  hardcode it in files or commit it.

## 7. Style

- Terse, factual tables. No marketing fluff.
- One specific engine per t/s measurement (llama.cpp, Ollama, vLLM, SGLang,
  MLX, TensorFold, FreeToken, TensorRT-LLM, LiteRT, Strata, MLX-fast, DFlash2).
- Mark estimates as `(est)`. Note hardware on every figure.
- Attribute each model to its real creator/community source; do not republish
  one person's private curation as your own.

## 8. Regression guards (what each test catches)

Run `make test` (all deterministic guards) and, with keys, `make
pipeline-smoke validate-fetch` (live). Each guard exists because the failure
actually happened.

| Guard | Catches |
|---|---|
| `tests/test_hermes_prompts.py` — prompt shell strings | an unescaped `"` in a `-z` prompt closing the string early (every search dies) |
| `tests/test_hermes_prompts.py` — trailing `\` + `make -n` | a `hermes -z` recipe whose `-m nous-deepseek …` line runs as a separate command (Hermes without alias → HF 403) |
| `tests/test_hermes_prompts.py` — `--reasoning` on every call | a search burning its whole output budget on reasoning and writing no snapshot |
| `tests/test_engagement_contract.py` | raw → ingest → store failing `model_contract.json` (the real PR #50 snapshot with model-level `reshares` is the fixture); stray keys not pruned; ingest and contract key lists drifting |
| `tests/test_fix_loop.py` | fix loop aborting on the first red check, never stopping when green, ignoring the round cap, losing the failure report |
| `tests/test_workflows.py` | refresh PR authored by `github-actions[bot]` (approval gate); fix-bot dispatched before validation or with `GITHUB_TOKEN`; a `workflow_run` trigger on fix-bot; push not gated on green; no git identity; pushes with a token that doesn't re-trigger CI; missing live smoke per backend; any workflow pushing/merging master |
| `tests/test_smoke_search.py` | smoke query lists drifting from the Makefile search prompts |
| `tests/test_readme_render.py` | engagement rank inert or post-count-only; placeholder URLs collapsing posts; legacy rows never scoring; range parsed by its first number; CPU figures under CUDA; most-loved not showing the true best per backend; engine matrix listing unmeasured engines; backend tables without hardware/quant or unsorted; escaped pipes breaking the table check; README re-render drifting with the wall clock |
| `tests/test_post_signal.py` | a registry-only engine (e.g. Mac-only) with blank hardware landing in the CUDA table; renderer and validator classifying differently; search prompts not asking for the `…/status/<id>` URL + per-post counts; the coverage report failing CI |
| `tests/test_trend_score.py` | one lightly-engaged post outranking many posts (real refresh-#58 fixture: Qwen3.8 1 post vs Bonsai); a viral post no longer able to lead; speed ignored or earned by datacenter / > 48 GB parts; VRAM parsing; duplicate placeholder posts after a `tps` rewrite; real posts lost; README Trend cell; validator not catching a reordered table or a wrong score |
| `check_readme_ranking` (validate, readme stage) | most-loved rows not in the store's trend order; a Trend cell not showing the stored `trend_score` / post count |
| `check_post_signal` (validate, report only) | how much of `score_7d` rests on real post URLs and engagement counts, per raw snapshot and for the store |
| `check_readme_measurements` (validate, readme stage) | a measurement missing from — or rendered in the wrong — backend table row; a most-loved cell that is not the best for its backend |
| `make search-smoke` (live, 3 s/attempt, 1 retry on timeout/429/5xx) | lightbrd mirror / Firecrawl key down, per backend. An uncached scrape can miss 3 s once (Firecrawl finishes and caches it server-side), so a transient miss gets ONE more 3 s attempt; auth errors (401/403) never retry. Retry policy unit-tested in `tests/test_smoke_search.py` |
| `make hermes-smoke` (live) | dead Nous key, broken alias, Hermes routing to another provider |
| `make validate-fetch` (live) | the search returning 0 model hits |

When you add a stage or fix a pipeline bug, add its row here and its test in
the same change (rule 6c).
