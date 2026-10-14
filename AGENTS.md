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
   Every change lands on a **feature branch** and is merged via a **PR**. A PR
   is **auto-merged** (squash, feature branch deleted) by qa-validate's
   `auto-merge` job ONLY when `validate` AND `live-smoke` are green on the
   exact head commit; a red PR stays open for a human. No workflow may merge
   from anywhere else, use `--admin`, or push to `master`.
2. **Never fabricate data.** No engagement number, like count, or t/s figure
   may be invented. It must trace to a **real X post** (via the lightbrd.com
   mirror technique in `skills/gather-data.md`) or be marked explicitly as
   `(est)` / `estimated` when it is a reasonable projection from quant size.
3. **Never wipe history.** If a model stops trending or gets no new updates,
   it stays in the data store and the README — it just sorts **further down**.
   Only remove a model with an explicit human decision (e.g. confirmed dead
   repo / wrong model).
3b. **Additive only — never remove a key or a value.** In `data/models.json`,
   `data/raw/*.json`, `data/snapshots/*.json` and the contract files an
   existing key is never removed or renamed, and no existing value is ever
   shrunk, by any automation: keys may only be ADDED (optional — never added to
   a contract's `required`), a measurement's t/s may only be RAISED, the
   engagement counters may only GROW, and `backends` / `supported_engines` /
   `formats` may only gain members. Loss is a defect, not a simplification: a
   field the search asks for but the contract refuses (its `additionalProperties:
   false` prunes it) is dropped SILENTLY, so widening a contract additively —
   with the tests, rule 6b — is the fix, never a deletion. A genuine removal is
   a human decision; for a contract it is a new `data/*_contract.vN.json` (§6b),
   never an edit in place. Enforced by
   `scripts/validate.py::check_no_value_loss` (`make validate`,
   `make validate-data`).
3c. **An issue that changes this file's behaviour must say so.** If a filed
   issue requires AGENTS.md to change (a new stage, a new rule, a changed
   pipeline contract), the issue MUST carry a comment stating exactly which
   section changes and why, and that part of the work is review-required — a
   reviewer signs off on the AGENTS.md diff before the implementation merges.
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
   AMD (ROCm), Apple (Metal), and CPU each render as a **first-class table**. A model
   measured on multiple backends appears under each with its own engine + t/s.
   The headline scope is GPU models serving **8–48 GB VRAM** (consumer/
   workstation) on NVIDIA and AMD alike; CPU and Metal tables exist alongside,
   not demoted below it. **AMD is classified by hardware, never by engine
   name**: a figure whose hardware names an AMD GPU/APU (Radeon, RX 7900 XTX,
   R9700, Strix Halo / Ryzen AI Max, ROCm, HIP …, and no NVIDIA token) is ROCm,
   whichever engine ran it (llama.cpp, Ollama, vLLM, SGLang, Strata). Vulkan is
   cross-vendor: it goes in `quant`, and Vulkan on an RTX card stays CUDA. Do
   not invent API-suffixed pseudo-engines (`llama.cpp (Vulkan)`, `vLLM (ROCm)`)
   — they split one engine's figures across names.
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

6d. **No dead code — every Python entry point is wired to the Makefile.** A new
   script, subcommand or validator check MUST be reachable from a `make` target
   that CI actually runs: either **bundled** into an existing stage (a validator
   check is registered in `scripts/validate.py`'s stage map in `main()` AND that
   stage appears in a `_validate-*` recipe's `--only` list) or **added as its own
   target** following the same pattern (internal `_name` host recipe + public
   docker-wrapper target, plus the CI job that calls it). A function or script
   nothing calls is a defect, not a spare part: the validator's registrations also
   carry the stage->target mapping in a comment, and
   `tests/test_validate.py::test_every_check_is_wired_to_a_stage_and_a_makefile_target`
   fails on a `check_*` no stage registers, on a stage no `--only` list selects,
   and proves `--only <stage>` really executes the check. Every `--only` list in
   the Makefile is the contract; a check reachable only by accident (bundled into
   no list, run by nothing) fails this test.

6e. **An agent-implemented issue ends in a monitored, green, squashed PR.** An
   issue filed by the analysis (`data-gap-analysis`) is implemented by
   `issue-bot.yml`: the agent works on a feature branch cut from `master` with
   the tests and the AGENTS.md row in the same branch, **opens the PR**
   (`closes #<issue>`, owner PAT so CI really runs), then **monitors the
   pipeline that PR triggered and fixes it until every check is green** — one
   implementer per issue (`concurrency: issue-bot-<n>`), never a parallel run for
   the same objective. The merge is a **squash merge with a proper Conventional
   Commit message** (qa-validate's `auto-merge` job performs it once `validate`
   and `live-smoke` are green); a run that stops at "branch pushed" is a defect.
   The agent never merges, never pushes `master`, and never invents a value to
   close a gap — an unverifiable one is reported on the issue instead.

3d. **Secrets never enter the repo — `make secret-scan` before every push.**
   No key, token, webhook URL or credential of any kind may be written into a
   tracked file (data, prompts in the `Makefile`, `skills/`, tests, workflows,
   AGENTS.md, README). The rule is enforced, not assumed:
   - `make secret-scan` runs **gitleaks** (MIT, the most widely adopted FOSS
     secret scanner; pinned image `ghcr.io/gitleaks/gitleaks:v8.30.1`) over the
     working tree — staged files included — with `.gitleaks.toml`. **An agent
     MUST run it before every push, and a non-zero exit BLOCKS the push.**
   - `make secret-scan-history` scans full git history (catches a value deleted
     later, which a working-tree scan cannot see). It needs a real clone and
     refuses a git worktree loudly instead of reporting a fake clean.
   - `make secret-scan-self-test` plants a well-formed FAKE credential and
     REQUIRES gitleaks to flag it, then requires a clean fixture to pass: a
     scanner that silently does nothing fails this.
   - CI runs `make secret-scan` + `make secret-scan-self-test` as the FIRST steps
     of qa-validate's `validate` job, so a planted secret turns the PR red.
   - A finding is fixed by **removing the value and rotating the key**, never by
     widening `.gitleaks.toml`: an allowlist entry is for a documented
     PLACEHOLDER (with a comment saying why) — a real value is never allowlisted.
   - The runtime story is unchanged and separate: keys reach a process only as
     `-e` env at run time (see §6b), never baked into an image or a config.

3e. **A credential reaches Hermes by NAME only, under the name the consumer
   actually reads.** Every key arrives as `-e <ENV_NAME>` on the `docker run`
   (`DOCKER_RUN` / `TEST_RUN`), and the only thing written to configuration is a
   name (`key_env`) or a non-secret setting — never a value: no `ENV`/`ARG` in an
   image layer, no `COPY`ed `config.yaml`/`.env`, no literal in a
   `hermes config set` argument. For a PLUGIN's credential, the name is the one
   its **pinned source resolves**, never a name we guessed: `hermes plugins
   install <owner>/<repo> --ref <commit>` (pinned, like the catalog), then wire
   that name. Measured for the nerve plugin (`keeltrace/hermes-nerve`,
   `hermes_nerve/client.py`): `PROVIDER_API_KEY_ENV = {openrouter:
   OPENROUTER_API_KEY, typesafe: TYPESAFE_API_KEY, opencode: OPENCODE_API_KEY}`.
   The provider is the one the SETUP runs, read from
   `plugins.entries.nerve.settings.jev_provider` (`HERMES_NERVE_PROVIDER` as the
   env override) — never the plugin's own default: production here runs
   `typesafe` (+ `typesafe_model = jev-latest`), so the pipeline pins `typesafe`
   and forwards `TYPESAFE_API_KEY`. Wiring the default (`openrouter`) forwards a
   name production never sets, and **there is no `JEV_KEY`** at all, so either
   mistake registers a variable nothing reads and the plugin keeps failing on its
   real name. A run without the key must fail **loudly** (the plugin raises), never
   degrade to another provider — that is how an HF 403 once hid a broken alias
   (§4/§6b). `make nerve-check` (`scripts/nerve_key_check.py`, guarded by
   `tests/test_nerve_key_wiring.py`) proves the pin, the name and the absence of
   any literal, and runs in `qa-validate`'s `validate` job (rule 6d).

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
  `make setup`, `make search-nvidia|search-metal|search-cpu|search-amd`
  (the four separate searches, each writing its own
  `data/raw/<backend>-<UTC>.json`), `make search` (all four), `make merge`
  (ingest raw → models.json + README + snapshot), `make validate` (QA),
  `make validate-search|validate-mapped|validate-readme` (stages), `make test`
  (unit tests), `make fix` (correct a red CI with Hermes), and `make refresh`
  (the full pipeline = setup + search + merge + validate + test, in one
  container). Live smoke targets (real network, bounded, skip cleanly without
  keys): `make search-smoke [BACKEND=nvidia|metal|cpu|amd]` (the exact Firecrawl →
  lightbrd scrape of every search query, **3 s cap per query**),
  `make hermes-smoke` (one real Hermes call through the `nous-deepseek` alias
  with every key the pipeline passes, incl. `HF_TOKEN`), and
  `make pipeline-smoke` (both). `make docker-test-build` builds the test image on
  the base it is given — `BASE_IMAGE=$(IMAGE)` for the base you just built,
  otherwise the published `ghcr.io/andyholst/trending-local-llms:latest` it
  defaults to. Run after
  `make docker-build` with `NOUS_API_KEY=... FIRECRAWL_API_KEY=... make refresh`.
- **Hermes invocation (every `hermes -z` recipe).** One logical shell command:
  the `-z "..."` line MUST end with ` \` so `-m nous-deepseek --reasoning
  $(HERMES_REASONING) --yolo` stays on the same command. Without it make runs
  the model flags as a separate command and Hermes starts with NO alias — it
  then auto-routes to whatever provider key is in the env (`HF_TOKEN` →
  Hugging Face → HTTP 403). Prose inside a prompt uses single quotes; only the
  JSON body uses `\"`.
- **Model budget (measured, not assumed).** The pinned model is
  `deepseek/deepseek-v4.1-flash`.
  The **65,536**-token cap was measured on the PREVIOUS pin of the same family
  (`/v1/models` → `max_completion_tokens`); V4.1 Flash declares no
  `max_completion_tokens`, so `HERMES_MAX_TOKENS := 65536` stays conservative
  until it is re-measured — a larger `max_tokens` is accepted SILENTLY and
  clamped, which is how 384000 once hid the real cap. The flash SKU thinks by
  default and only takes a generic `reasoning` switch: effort `low` still
  spends reasoning tokens (a Metal search burned the whole cap: "No visible
  answer was produced … reasoning consumed the entire budget"), while
  `--reasoning none` sends `enabled: false` → 0 reasoning tokens. So the
  searches run `HERMES_REASONING := none` (they are mechanical) and fix-bot
  `HERMES_FIX_REASONING := low`. `low` still burnt the whole cap in 2 of 3
  fix rounds on PR #80, so `scripts/fix_loop.sh` retries the SAME round once
  with `HERMES_FIX_REASONING=none` when Hermes reports that signature (the
  docker `fix` wrapper forwards the variable into the container). The search prompts write each query's models
  right after that query (`--write-raw <backend>`, one small file per call;
  same-second writes get `-2`, `-3`) — never one big end-of-run payload.
  `make model-caps` (live, in `live-smoke` and before every refresh search)
  fails if the model isn't served, `max_tokens` exceeds its real cap, or it
  doesn't accept `reasoning`. Re-check the catalog when changing the model.
- **Routing smoke tests routing, not obedience.** `scripts/hermes_smoke.sh`
  passes when Hermes answers through the alias (exit 0, non-empty, no
  provider-failure signature) and retries once. Never require an exact reply
  word — deepseek answered "Reply with exactly PONG" with "No. I'm an AI
  assistant, not a ping-pong game" and failed qa-validate on master.
- **Base image follows its Dockerfile; a published base is pulled, never rebuilt
  per-run.** The base image (`ghcr.io/andyholst/trending-local-llms:latest` —
  Python deps + Hermes CLI + the pinned plugins baked in) is **built and pushed
  to GHCR by `refresh-bot.yml`** when it does not exist, when **Sunday** arrives
  (weekly Hermes update), or **when the Dockerfile hash it was built from is not
  published** — each build also publishes `:<repo>:dockerfile-<sha12>` of
  `Dockerfile` + `Dockerfile.test`, so a merged Dockerfile change (a new pinned
  plugin, a new apt package) is live on the next refresh instead of waiting for
  Sunday (issue #135). Owner dispatch may set `force_rebuild=true` to republish
  on demand.
  A pipeline that uses the base **pulls it only when that hash tag exists**;
  otherwise it **builds the base from source** for that run
  (`qa-validate.yml`; measured: the nerve plugin is installed by the Dockerfile,
  so validating against a stale base silently degraded the credential guard).
  It then layers the TEST image on that base **explicitly**
  (`make docker-test-build BASE_IMAGE=trending-local-llms:latest` —
  `Dockerfile.test` takes its `FROM` as a build arg, so a cached GHCR pull can
  never stand in for the revision's own base). `fix-bot.yml` still pulls.
  The GHCR image is public, so no login is needed to pull it.
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
  `check_no_value_loss` additionally fails any key, measurement, t/s or counter
  that existed in the newest snapshot and is gone from the store (additive
  only — §2.3b), which the JSON Schema alone cannot see.
  `check_readme_tables_wellformed` + `check_links_resolve` are registered in the
  `make validate` stages so a malformed table or a dead/wrong link in any new
  raw snapshot, the store, or the README fails CI. This is a **validation**
  action, not a data-gathering bot.
- **New engines are registered at ingest, not by fix-bot.** An engine is an
  inference runtime or server that loads the weights (llama.cpp, MLX, vLLM,
  Ollama, …). Harnesses, agent frameworks, plugins, chat apps/UIs and
  benchmarks are NOT engines and must never be in the registry. The search
  prompts say so and ask, for an engine not registered yet, for
  `engine_repo` = its `https://github.com/<owner>/<repo>` from the post, or —
  when the post links no repo — from ONE Firecrawl web search whose repo name
  matches the engine and resolves (never invented). At ingest `scripts/engine_registry.py` fetches the repo
  metadata, `classify_repo` decides engine / not-engine / unknown from the
  description, topics and name — STRONG not-engine signals (harness, agent
  framework, plugin, leaderboard, eval/benchmark suite, dataset) always win;
  APP signals (chat/web UI, frontend, desktop/mobile app) win unless the repo
  description calls itself an inference server/engine/runtime (mlx-serve: 'LLM
  inference server … Swift frontend macOS app' was refused on PR #80); a bare
  'benchmark' only counts when there is no engine
  signal ('MLX inference speedup benchmark engine' is an engine) — and only an
  **engine** is registered (also refused: a name the registry pattern forbids,
  and conflicting `engine_repo` values for one engine): backend from its measurements, `auto: true`, note
  "Auto-registered from <source_post> — <description>". not-engine, unknown,
  unreachable and missing repos are never registered — validation keeps
  failing for a human / fix-bot. `engine_repo` is stripped before the store.
  `make engine-check` reports every unregistered engine in the raw snapshots
  and the decision ingest will make; it runs right after each refresh search
  and in the aggregate, so a new engine shows in the refresh run, not first at
  PR CI. `check_engine_kind` fails a registry entry that is a known non-engine
  (`NON_ENGINE_REPOS` / `NON_ENGINE_NAMES` in `scripts/engine_registry.py` —
  add one whenever a harness slips through, e.g. `deepseek-ai/deepseek-harness`
  from refresh PR #72) or an `auto` entry without a cited source.
- **Model-specific engine forks (`engine_aliases`).** When a model only runs
  on a fork of an engine, register the fork as its own engine (name + repo URL
  + backend + note) and declare on the model
  `"engine_aliases": {"<posted name>": "<fork registry name>"}`. Example:
  Ternary Bonsai 2's `PTQ1_0`/`PQ2_0` GGUFs are rejected by stock llama.cpp,
  so Bonsai 2 27B maps `llama.cpp` → `llama.cpp (PrismML fork)`
  (https://github.com/PrismML-Eng/llama.cpp). The alias is applied on ingest —
  to the stored AND the incoming rows before `merge_engines`, or the two sides
  don't match and figures duplicate — and on every sort, so the search agent
  can keep writing what the post says. Add the fork URL to
  `KNOWN_ENGINE_URLS`; `check_engine_aliases` fails a leftover un-aliased
  measurement, an unregistered target, or a wrong fork URL.
- **Backends follow the measurements.** `backends` is never narrowed, but
  ingest (`sync_backends`, for existing AND new models) adds every backend a
  model's measurements render in, with the same `measurement_backend` the
  README uses — an existing model that gains its first Radeon figure gets
  `ROCm`. A registry engine's `backend` lists every backend it runs on, joined
  in the canonical order CUDA, ROCm, CPU, Metal (`join_backends`; the contract
  enum is exactly those combinations). The search legs are ONE list,
  `update_trending.SEARCH_LEGS` (`nvidia`, `metal`, `cpu`, `amd`) — adding a
  leg means wiring it everywhere `tests/test_amd_backend.py` checks.
- **Ingest is contract-driven.** `normalize_model` / `ingest_raw_snapshots`
  prune a model's top-level `engagement` to exactly the keys declared in
  `data/model_contract.json` (read at runtime — no second list to drift) and
  coerce counters to non-negative ints. The search contract leaves that object
  open, the store contract closes it; without the prune, one extra key the
  search agent writes (it was `reshares`, on every model) turns every refresh
  PR red on a schema error. Real recurring keys are declared in BOTH contracts
  (additive); stray keys are dropped and logged as `[ingest] … pruned`.
- **Stage -> target mapping.** `make validate` (`_validate`) runs **every** stage
  (no `--only`); `make validate-data` runs `data,removal`; `make validate-mapped`
  runs `data,schema,mapping,removal`; `make validate-search` runs `search,mapping`;
  `make validate-readme` runs `readme`; `make validate-links` runs `links`. Every
  stage a check is registered under MUST appear in at least one `--only` list
  (§2 rule 6d). CI's `qa-validate` `validate` job runs `make validate`,
  `make validate-search`, `make validate-mapped` and `make test`.
- **Post-refresh data-gap analysis (issue #115).** Every refresh also asks what
  the acquired data still does NOT capture and files it as a tracked issue:
  `make data-gaps` prints the report, `make data-gap-issue` files **one** issue
  (label `data-gap-analysis`) when the gap set changed vs `data/gap_baseline.json`
  — a day with the same gaps files nothing. Report-only: it never fails the data
  PR. The flagship gap is memory that is not VRAM: the store has `vram_tier` /
  `vram_min` and nothing else, while the CPU and Metal tables are RAM-bound
  (Apple Silicon is unified memory), llama.cpp partial offload keeps the
  un-offloaded layers + KV cache in system RAM, and MoE offload (Strata) splits
  experts across GPU/RAM/SSD — and `skills/gather-data.md` already asks the search
  agent for "VRAM / RAM", a figure the contract (`additionalProperties: false`)
  prunes. A dimension the contract cannot hold is reported as a **contract gap**
  (add the key OPTIONALLY, never as `required`, per §6b); a figure that exists
  only as free text inside `quant`/`why`/`hardware` is reported as
  **unstructured**, never as captured. `scripts/data_gap_analysis.py`, wired into
  `refresh-bot.yml`'s `aggregate` job and tested by
  `tests/test_data_gap_analysis.py`.
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
  `NN GB`, a known-card table incl. laptop variants and Radeon cards, `Nx`
  multiplied — a standalone 1–2 digit count only, so the `x` of `7900 XTX` is
  never a multiplier), every Apple Silicon, AMD APU (Strix Halo / Ryzen AI,
  Radeon 8060S …; judged by platform like a Mac) and CPU measurement.
  Datacenter parts (H100/H200/A100/B200/GB200, AMD Instinct MI210/MI250/MI300/
  MI355…) or > 48 GB never earn speed. 10 t/s → +1, 70 → +3, 150 → +4.
- **`trend_score` = buzz + speed.** Order: band (trending → recent → stale) →
  `trend_score` → `posts_7d` → peak t/s (`_tps_core`, max of a range) → name.
  `posts_7d` = distinct posts in 7 days (`last_7d_likes` mirrors it).
- The README is rendered **as of `generated_utc`** (not the wall clock), so the
  validator's re-render is byte-stable days after merge. Tests must do the
  same: never pass `datetime.now()` / `utcnow()` / `today()` as the
  `render_readme` as-of. A wall-clock render passes for a week, then turns
  master red once the fixture ages out of the 7-day band (issue #88). Check
  date-relative tests under `faketime <future date>` in the test image.

## 5b. README layout (generated by `render_readme`)

Every section uses the same `measurement_backend(e, registry)` (CUDA / Metal /
CPU / ROCm: explicit Apple hardware → explicit CPU-only wording → AMD GPU
hardware → CPU hardware, then the engine registry's `backend` when it names ONE
backend, then the built-in engine map, then keywords; CUDA only as the last
resort) and
`best_measurement()` (highest t/s core, newest date on a tie), so no two tables
can disagree about where a figure belongs.

1. **❤️ Most loved** — one row per model in rank order: model (HF link, full
   name · params · license), status (🔥 / 🕑 / 💤 + last seen), **Trend**
   (`trend_score`, with `buzz · N posts · speed +X (t/s, hardware)` beneath),
   the **best** t/s for each of CUDA / Metal / CPU / ROCm (`BACKENDS` order) with engine
   link · hardware · quant (`+N more` when there are others), VRAM, why. No
   `#` rank column — rank is row order.
2. **🧭 Which inference engine runs what** — models × engines that have at
   least one measurement; each cell is the best t/s per backend on that engine.
3. **🟦 CUDA / 🟪 ROCm / 🟨 CPU / 🟩 Metal backend tables** — numeric `Peak t/s` column (the sort key
   the validator reads by header name) + every measurement as
   `engine **t/s** · hardware · quant · date`, best first.
4. **⚙️ Engine guide** — engine link, backend, models measured, best for.

Free text in cells is pipe-escaped (`\|`); the table validator splits on
unescaped pipes only.

## 6. Refresh workflow — GitHub Actions invoking the Hermes CLI

The refresh is driven by the **GitHub Actions pipelines** (`refresh-bot.yml`,
`fix-bot.yml`), which invoke the **Hermes CLI** (deepseek-v4.1-flash via the
Nous portal, using the repo's `NOUS_PORTAL_API_TOKEN` secret). The agent loads
this `AGENTS.md` and the `gather-data` skill, then:

1. Runs the **four search groups** against **lightbrd.com only**, fetched via
   the Firecrawl scrape API (`FIRECRAWL_API_KEY`) — NVIDIA/CUDA, AMD/ROCm, Metal/MLX, and
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
4. Commits on a **feature branch** and opens a **PR** to `master` (auto-merged
   by qa-validate once green), using the owner-scoped PAT (`FIXBOT_DISPATCH_TOKEN`) for the push
   and `gh pr create` — never the default `GITHUB_TOKEN` (see §6b). It never
   pushes to or merges `master` itself.

## 6b. Three pipelines (refresh → validate → fix)

- **`refresh-bot.yml`** — the **bot** pipeline. Scheduled (daily, 06:00 UTC +
  a 17:43 UTC backup slot — GitHub delays/drops on-the-hour crons) + manual
  dispatch (owner only). Per backend (nvidia / metal / cpu / amd, parallel matrix):
  3 s reachability smoke → Hermes routing smoke → Hermes search. Then
  `aggregate` (runs even if a leg failed): merge → soft validate → **opens a PR
  only when there is new data**, authored by the owner PAT so qa-validate
  starts without an approval click. It does NOT dispatch fix-bot — that is
  qa-validate's job, after it has validated. It never merges; qa-validate's
  `auto-merge` does, once the PR is green.
- **`qa-validate.yml`** — the **PR CI** pipeline. Runs on every PR (including
  workflow-only PRs — the wiring is under test), push to master, or dispatch.
  Four jobs:
  - `validate` — deterministic: `make validate`, `validate-search`,
    `validate-mapped`, `test`. This is the only job fix-bot is asked to repair.
  - `live-smoke` — real network, bounded: `make search-smoke BACKEND=<b>` for
    nvidia, metal, cpu, amd (3 s cap per query), `make hermes-smoke`, and
    `make validate-fetch` (real search, `--require-hits`). An outage here is
    infra, not data, so it never dispatches fix-bot.
  - `dispatch-fixbot` — only when `validate` failed on a same-repo
    `ci/trending-refresh-*` PR: dispatches fix-bot with `pr_number` + `branch`
    using the owner PAT, unless the PR already has 2 `fix-bot:` commits (a fix
    that didn't stick → manual review, no loop).
  - `auto-merge` — `needs: [validate, live-smoke]`, `if: success()` on a
    same-repo, non-draft `pull_request` (never `master`/`main`): `gh pr merge
    --squash --delete-branch --match-head-commit <validated sha>` with the
    owner PAT (a `GITHUB_TOKEN` merge would start no master CI). A push after
    the run started makes the SHA mismatch → no merge; the newer run decides.
- **`fix-bot.yml`** — the **fix** pipeline. `workflow_dispatch` ONLY (no
  `workflow_run`: it double-fired with the dispatch and was suppressed for bot
  PRs). One run per PR (`concurrency`). Resolves the PR (refuses
  `master`/`main`), checks out the branch with the PAT, runs `make
  hermes-smoke`, then `scripts/fix_loop.sh`: run the deterministic checks →
  green? stop → else write `qa-report.txt` (ONLY the failing check's output +
  the list of checks that passed) and `make fix` (the `_fix` prompt reads that
  report first) → re-check, at most `FIX_ROUNDS` (3) Hermes attempts. It
  commits (`fix-bot: …`, git identity set) and pushes with the PAT **only when
  the loop ends green** — the PAT push re-triggers qa-validate. The commit
  step stages with a plain `git add -A`: `qa-report.txt` / `comment.md` are
  gitignored, and naming an ignored path in the pathspec (`':!qa-report.txt'`)
  makes git exit 1 — every green fix was lost that way until PR #80. Still red
  → nothing is pushed and the failing lines are commented on the PR; the PR
  comment reads the push step's outcome, so a failed push is never reported
  as 'pushed'. `qa-report.txt` is uploaded as a run artifact. A pushed fix
  re-runs qa-validate, which auto-merges if green; still red → a human.

- **`issue-bot.yml`** — the **implementer** pipeline (rule 6e, issues #113 / #127).
  Trigger surface is `issues: [opened]` carrying the `data-gap-analysis` label
  (what `make data-gap-issue` files), a **backlog sweep** (`schedule: cron
  '19 */6 * * *'` — every 6 h, off the hour), and an owner `workflow_dispatch`
  (an issue number, or empty to sweep). The `pick` job (schedule only) chooses the
  OLDEST open labelled issue with **no implementer yet** — no
  `ci/data-gap-<n>-*` branch and no open PR from one — and an empty backlog is a
  green run that implements nothing. The `implement` job serves all paths
  (`needs: [guard, pick]`, `always()` + `needs.guard.result == 'success'`) with a
  **job-level** `concurrency: issue-bot-issue-<n>`, so a sweep and an
  `issues: opened` event for the SAME issue queue instead of racing: one
  implementer per issue, across paths. Its `guard` job runs FIRST (owner / write collaborator, actor AND
  triggering actor, names from `env:` — a stranger's issue starts nothing), and
  `implement` needs it. It resolves the issue (must be open),
  writes it to `issue.md`, checks out `master` with the owner PAT, pulls the base
  image, runs `make hermes-smoke`, implements through `make implement-issue` (the
  prompt in the Makefile: implement EXACTLY that issue, additive only, never
  fabricate a value, wire every addition to a make target per rule 6d), pushes
  `ci/data-gap-<n>-<slug>` (resuming it on a re-run — never a force-push), opens
  the PR against `master` with `closes #<n>`, then runs the SAME fix loop as
  fix-bot against that PR and pushes only when green, and comments the outcome on
  the issue. It never merges — qa-validate's `auto-merge` squash-merges.
  Two failures measured on its first real run (#124, run 38502619350) are now
  guarded by `tests/test_workflows.py::test_issue_bot`: (1) `make implement-issue`
  MUST run `_setup` in the SAME container as the hermes call — without the alias
  Hermes auto-routes to whatever key is in the env (`HF_TOKEN` -> Hugging Face ->
  `HTTP 403`); (2) the outcome comment MUST use the default `github.token` with
  `permissions: issues: write`, because the owner PAT is scoped to
  Actions/Contents/Pull-requests only (`Resource not accessible by personal access
  token (addComment)`). A run whose implementation did not happen is made RED by a
  named final step — never a green run with nothing to review. A THIRD measured
  failure (#120, run 38509118147): the branch push was rejected because the
  implementation edits `.github/workflows/**` and the PAT lacks `Workflows: R/W`;
  the bot now detects that, reports the missing permission on the issue and stays
  red on purpose, and it strips scratch artifacts (`*.patch`, `*.rej`, `*.orig`)
  — a change written into a patch file is not an implementation. A rejected push
  also uploads the committed work as the `issue-implementation-patch` artifact
  (`git am` it once the permission is granted), so 30 minutes of agent work are
  never thrown away with the ephemeral runner.

**Who can run what** (owner + collaborators only):
- **Workflows.** `workflow_dispatch` / re-run already require write access;
  the workflows enforce it themselves too, so it never depends on a setting:
  - refresh-bot: a first `guard` job. The daily `schedule` passes; a dispatch
    or re-run passes only when BOTH `github.actor` and
    `github.triggering_actor` are the repository owner or a collaborator with
    `write` / `maintain` / `admin` (checked via the collaborator-permission
    API; `read`, `triage`, non-collaborators and API errors are refused).
    `build` needs `guard`, `search` needs `build`, and `aggregate` runs only if
    `needs.guard.result == 'success' && needs.build.result == 'success'` (it
    still tolerates a failed search leg — never a bare `if: always()` there:
    it ran with secrets on a refused guard). `concurrency: refresh-bot,
    cancel-in-progress: false` queues overlapping runs.
  - fix-bot: the same guard is its FIRST step, before any secret is read.
    qa-validate dispatches it with the owner PAT, so the auto-fix loop runs.
  - Guard scripts read names from `env:`, never inline `${{ }}` (injection).
  The real guard scripts are executed in `tests/test_workflows.py` against a
  stub `gh` for every caller type.
- **PRs / issues / comments.** Repository interaction limit
  **`collaborators_only`** (set via `PUT /repos/{o}/{r}/interaction-limits`):
  only the owner and collaborators can open PRs or issues or comment. GitHub
  caps it at six months — **it expires 2027-04-02 and must be renewed**
  (`gh api -X PUT repos/andyholst/trending-local-llms/interaction-limits -f
  limit=collaborators_only -f expiry=six_months`).
- **Forks.** A public repo cannot disable forking; with the interaction limit
  a fork cannot open a PR here. Fork PR approval is
  **`all_external_contributors`**, and fork PR runs get no secrets and a
  read-only token; `dispatch-fixbot` only acts on same-repo
  `ci/trending-refresh-*` branches.

**Tokens.** `FIXBOT_DISPATCH_TOKEN` is a fine-grained PAT scoped to this repo
only: Actions R/W, Contents R/W, Pull requests R/W, **Workflows R/W**. The last
one is not optional: an issue-bot implementation may legitimately edit
`.github/workflows/**` (rule 6d wiring), and a PAT without it has its push
rejected — `refusing to allow a Personal Access Token to create or update workflow
… without \`workflow\` scope` (measured on #120, run 38509118147). The bot detects
that rejection, leaves the run RED on purpose and explains the missing permission
on the issue instead of dying at `git push`. Issue reads and comments use the
default `github.token` with `permissions: issues: write` (the PAT has no Issues
scope). It is used for (1) the
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

This is the same rule §2.3b states for the DATA: an additive contract change
makes a new optional key survive ingest, and `check_no_value_loss` (validate,
`removal` stage) then keeps it — a key or a value that was in the previous
snapshot can never disappear from the store again, whatever the contract says.

Flow: bot refreshes + opens PR (PAT) → qa-validate (`validate` + `live-smoke`)
→ if `validate` is red, qa-validate dispatches fix-bot → fix-bot loops until
green (≤3 Hermes rounds) and pushes (PAT) → qa-validate re-runs → green →
`auto-merge` squash-merges + deletes the branch. Red after the loop → PR comment, manual review. Max 2 fix-bot pushes
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
  trending, and that it is auto-merged once qa-validate is green.
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
| `tests/test_engine_registry.py` (offline: `tests/fixtures/github_meta.json` = real GitHub metadata of every registered engine; `ENGINE_REGISTRY_META_FILE` switches `fetch_repo_meta` to it) | the classifier refusing ANY registered engine (it refused MLX-fast); a new engine needing a fix-bot round instead of registering at ingest; a harness / agent framework / app / benchmark / unknown / unreachable / non-GitHub repo being registered (classification table + real refresh-#72 snapshot: `quillan.cpp` registered, `DeepSeekHarness` refused); `engine_repo` leaking into the store; `check_engine_kind` passing a registered harness; `engine-check` failing instead of reporting |
| `check_engine_kind` (validate, data stage) | a registry entry that is a known non-engine, or an `auto` entry without a cited source |
| `tests/test_fix_loop.py` | fix loop aborting on the first red check, never stopping when green, ignoring the round cap, losing the failure report; running the slow unit suite before the validate checks are green; negative-test fixture lines ('FAIL: m1 …') polluting the failure summary |
| `tests/test_workflows.py` | refresh PR authored by `github-actions[bot]` (approval gate); fix-bot dispatched before validation or with `GITHUB_TOKEN`; a `workflow_run` trigger on fix-bot; push not gated on green; no git identity; pushes with a token that doesn't re-trigger CI; missing live smoke per backend; any workflow pushing master or merging outside qa-validate's `auto-merge` job; `auto-merge` running on red / draft / fork PRs, without `live-smoke`, with `GITHUB_TOKEN`, `--admin`, without `--delete-branch` or without `--match-head-commit`; refresh-bot with a single on-the-hour cron (GitHub delayed it ~6 h / dropped it) |
| `tests/test_workflows.py` — `test_fix_bot_push_behaviour` (runs the REAL commit step in a temp clone with the repo `.gitignore`) | the PR #80 loss: green loop, then `git add -A -- . ':!qa-report.txt'` exits 1 on an ignored path and nothing is pushed; qa-report.txt/comment.md committed; the PR comment claiming 'pushed' after a failed push; no qa-report artifact |
| `tests/test_fix_loop.py` — budget + report | `--reasoning low` burning the whole output cap and wasting the round (no same-round retry with `none`); an ordinary fix failure retried with reasoning off; passing checks' fixture noise in qa-report.txt / the summary |
| `tests/test_engine_registry.py` — `test_app_bundled_inference_server`, `test_search_prompts_look_up_missing_repos` | a real inference server that ships a GUI (mlx-serve, oMLX) refused as an app; a chat UI that merely supports an engine accepted; search prompts not asking for one verified repo lookup when the post links none |
| `make nerve-check` + `tests/test_nerve_key_wiring.py` (rule 3e) | a plugin credential wired under a NAME the plugin's pinned source does not read (e.g. `JEV_KEY` for `keeltrace/hermes-nerve`) or under a PROVIDER the setup does not run (the plugin's own default `openrouter` instead of production's `typesafe`) — the mapping is `jev_provider` → `OPENROUTER_API_KEY` / `TYPESAFE_API_KEY` / `OPENCODE_API_KEY`, so a mismatch forwards a variable nothing reads and the plugin keeps failing on its real name; the plugin not pinned by commit; a key baked into the image (`ENV`/`ARG`), copied in a `config.yaml`/`.env`, or passed as a literal to `hermes config set`; a run without the key degrading instead of failing loudly; the check not wired into a make target CI runs (rule 6d) |
| `make secret-scan` + `tests/test_secret_scan.py` (rule 3d) | a credential shape reaching a push or a PR (gitleaks over the working tree incl. staged files, `.gitleaks.toml`); a widened allowlist that exempts a REAL value instead of a documented placeholder; the scan or its self-test missing from qa-validate's `validate` job (rule 6d); the history scan reporting a fake clean in a worktree it cannot read; the self-test no longer proving that a planted credential IS detected (`make secret-scan-self-test` — a scanner that silently does nothing is a false green) |
| `tests/test_workflows.py` — `test_issue_bot` (rules 6e/6d) | the implementer bot reacting to anything but a NEWLY-created `data-gap-analysis` issue, the 6-hourly sweep or owner dispatch (a PR, a comment, a push, a `workflow_run`, a label-less issue); the sweep picking an issue that already has a branch/PR instead of the oldest unhandled one; two implementers for one issue (a concurrency key not keyed by the issue number, on either path); `make implement-issue` not running `_setup` in the same container as the hermes call (measured: alias missing → `HF_TOKEN` → `HTTP 403`); the outcome comment using the owner PAT instead of the default token (`Resource not accessible by personal access token (addComment)`); a run with no implementation staying green; a raw `hermes` call in the workflow instead of `make implement-issue`; a PR opened with `GITHUB_TOKEN` (held for approval) or against the wrong base; a missing `closes #<issue>`; the bot merging a PR itself; implementing a CLOSED issue; a re-run that force-pushes instead of resuming the issue's branch; the fix loop missing or the fix push not gated on green; no outcome comment on the issue |
| `tests/test_workflows.py` — trigger guards | a refresh-bot job not gated by `guard`; `aggregate` able to run on a refused guard; a guard that ignores `triggering_actor` or inlines `${{ }}`; fix-bot reading a secret before its guard; no refresh `concurrency`; the real guard scripts allowing a read/triage collaborator, a non-collaborator or a stranger's re-run, or refusing the owner, a write+ collaborator or the schedule |
| `tests/test_smoke_search.py` | smoke query lists drifting from the Makefile search prompts |
| `tests/test_validate_readme.py` — `test_readme_generated_*` + `test_readme_generated_tests_are_clock_independent` (issue #88) | a hand-edited / stale README passing `check_readme_generated`; a test rendering the expected README from the wall clock instead of the store's `generated_utc` (the fixture aged out of the 7-day band on 2026-10-05 and master went red, run 37247105182); the AST guard rejects any `render_readme(..., now()/utcnow()/today())` under `tests/` |
| `tests/test_readme_render.py` | engagement rank inert or post-count-only; placeholder URLs collapsing posts; legacy rows never scoring; range parsed by its first number; CPU figures under CUDA; most-loved not showing the true best per backend; engine matrix listing unmeasured engines; backend tables without hardware/quant or unsorted; escaped pipes breaking the table check; README re-render drifting with the wall clock |
| `tests/test_post_signal.py` | a registry-only engine (e.g. Mac-only) with blank hardware landing in the CUDA table; renderer and validator classifying differently; search prompts not asking for the `…/status/<id>` URL + per-post counts; the coverage report failing CI |
| `tests/test_trend_score.py` | one lightly-engaged post outranking many posts (real refresh-#58 fixture: Qwen3.8 1 post vs Bonsai); a viral post no longer able to lead; speed ignored or earned by datacenter / > 48 GB parts; VRAM parsing; duplicate placeholder posts after a `tps` rewrite; real posts lost; README Trend cell; validator not catching a reordered table or a wrong score |
| `tests/test_engine_aliases.py` | a model that needs a fork (Bonsai 2 → PrismML llama.cpp) linked to the stock engine; aliases not applied on sort or ingest; stored + raw rows duplicating when only one side is aliased; aliases leaking to other models; search prompts not mentioning forks |
| `tests/test_amd_backend.py` (issue #76) | AMD hardware falling to the CUDA default or CPU (`Ryzen 5 7600 + RX 7800 XT`, Strata/vLLM on a Radeon); bare `amd` / `hip` / `vulkan` read as AMD; `RX 7900 XTX 24GB` read as 189,600 GB (`xtx` as a multiplier); a host CPU read as an RX card; Instinct earning speed / Strix Halo not; a Radeon row merged with a Ryzen CPU row; ROCm table / most-loved column / matrix cell missing; validator skipping an unsorted, missing or misplaced ROCm table; an existing model gaining an AMD figure without `ROCm` in `backends`; an AMD-only engine registered as CUDA; contract enums drifting from `BACKENDS` / `join_backends`; the amd leg missing from the Makefile, either workflow, the smoke, the contract or self-correct (one list: `SEARCH_LEGS`) |
| `check_backends_cover_measurements` (validate, data stage) | a model whose measurements render in a backend table its `backends` does not list (ingest + `normalize_model` now sync it via `sync_backends`) |
| `check_engine_aliases` (validate, data stage) | a measurement still on the aliased-away engine name; an alias target missing from the registry or with the wrong repo URL |
| `check_no_value_loss` (validate, `removal` stage) + `tests/test_validate.py::test_no_value_loss` | a key, a measurement group, a t/s or an engagement counter that was in the previous snapshot disappearing from the store. `check_no_removal` only compares model IDS and the contract only sees a missing REQUIRED key, so `engagement.seen_posts`, the computed trend fields, a measurement's `hardware`/`quant`/counters — and 12 of bonsai-2-27b's 13 measurements — could be deleted with `make validate` green (both measured on master before this guard). Additive changes (new key, new measurement, extra backend, raised t/s or counter) must never fire it |
| `tests/test_data_gap_analysis.py` (issue #115) | the analysis not running from `make data-gaps` / `make data-gap-issue` or the `aggregate` job (rule 6d — a script no target calls); a dimension the contract cannot hold not reported as a contract gap; free text (`quant: "1432 MB peak RAM"`, on the model OR a measurement) counted as stored data instead of unstructured; a second issue filed for an unchanged gap set; a volatile item (an `(est)` figure, an empty raw leg) changing the issue-triggering signature; the report failing a data PR |
| `tests/test_validate.py::test_every_check_is_wired_to_a_stage_and_a_makefile_target` (rule 6d) | a `check_*` in `scripts/validate.py` that no stage in `main()` registers, a stage that no Makefile `--only` list selects, and the `--only removal` call path itself — i.e. a validator function that exists but the CI pipeline never executes (a dead function, or a check wired into no make target) |
| `check_readme_ranking` (validate, readme stage) | most-loved rows not in the store's trend order; a Trend cell not showing the stored `trend_score` / post count |
| `check_post_signal` (validate, report only) | how much of `score_7d` rests on real post URLs and engagement counts, per raw snapshot and for the store |
| `check_readme_measurements` (validate, readme stage) | a measurement missing from — or rendered in the wrong — backend table row; a most-loved cell that is not the best for its backend |
| `make search-smoke` (live, 3 s/attempt, 1 retry on timeout/429/5xx) | lightbrd mirror / Firecrawl key down, per backend. An uncached scrape can miss 3 s once (Firecrawl finishes and caches it server-side), so a transient miss gets ONE more 3 s attempt; auth errors (401/403) never retry. Retry policy unit-tested in `tests/test_smoke_search.py` |
| `tests/test_search_budget.py` | searches not running with reasoning off; `HERMES_MAX_TOKENS` above the 65,536 bound; a stale model pin (`HERMES_MODEL` not the current SKU, or the retired SKU string left in any of Makefile / AGENTS.md / README.md / `skills/` / `scripts/` / `.github/workflows/` / `tests/` — the scan is by directory + suffix, so a new file is covered without editing the guard); prompts building one big payload instead of writing per query; same-second raw writes overwriting each other; `model_caps_check` logic (cap overrun, missing model, no `reasoning`) |
| `tests/test_hermes_smoke.py` | the routing smoke failing on a refusal reply (real CI false negative) or passing an HF 403 / provider error / empty reply / timeout; no retry |
| `check_readme_engine_links` (validate, readme stage) | a README engine link that differs from the registry, or a registry URL that differs from `KNOWN_ENGINE_URLS` |
| `make model-caps` (live) | model not served, `max_tokens` above the real cap (silent clamp), model can't switch reasoning off |
| `make hermes-smoke` (live) | dead Nous key, broken alias, Hermes routing to another provider |
| `make validate-fetch` (live) | the search returning 0 model hits |

When you add a stage or fix a pipeline bug, add its row here and its test in
the same change (rule 6c).
