# ARCHITECTURE.md — how this repository works

**What this file is.** `AGENTS.md` is the *rulebook*: what must and must not
happen. **This** file *describes* the system — every `make` target, every
pipeline job, every image, every script and the data flow between them — so a
reader (or an agent starting work) does not have to reconstruct it from four
workflow files and a 55-target Makefile.

**It is part of the change.** Rule 6h: any change that adds, renames or removes a
make target, a stage, a pipeline job or an image MUST update this file in the
same change. That obligation is enforced, not aspirational: `make
architecture-check` (run by `qa-validate`'s `validate` job, by the fix loop and —
through `tests/test_architecture.py` — by `make test`) fails when a public target, a workflow file or a script in the repo
is not described here — or when this file describes something that no longer
exists.

**Contents**

1. [What the repository produces](#1-what-the-repository-produces)
2. [Data flow and contracts](#2-data-flow-and-contracts)
3. [Every `make` target](#3-every-make-target)
4. [The pipelines](#4-the-pipelines)
5. [The images](#5-the-images)
6. [The scripts](#6-the-scripts)
7. [Guards](#7-guards)
8. [The life of a change](#8-the-life-of-a-change)
9. [Known gaps](#9-known-gaps)

---

## 1. What the repository produces

A living index of **open-weight LLMs people actually run locally**: `README.md`,
regenerated from `data/models.json`, ranking models by **real X engagement**
(7-day, from the lightbrd.com mirror) with **measured t/s per engine** on the
hardware/quant they were measured on. The store is canonical; the README is
generated and never hand-edited.

Four first-class backend tables (CUDA / ROCm / CPU / Metal) each carry their own
measurements; every figure traces to a `…/status/<id>` post URL.

---

## 2. Data flow and contracts

```
        (4 searches, one per backend)              data/raw/<backend>-<UTC>.json
Firecrawl → lightbrd.com mirror  ─────────────────►│  (one snapshot per call,
                                                   │   never overwritten:
                                                   │   same-second writes get -2, -3)
                                                   ▼
                             make merge  =  scripts/update_trending.py
                                                   │
   ingest_raw_snapshots (additive: adds models,    │
   merges measurements, fills absent keys,         │
   never removes, never shrinks)                   ▼
                                        data/models.json   (canonical store)
                                                   │
                             sort_models + recompute_7d_engagement
                                                   │
                                        render_readme(store, as_of)
                                                   ▼
                    README.md (generated)   +   data/snapshots/trending-<UTC>.json
```

* **`data/raw/*.json`** — one file per search call, per backend
  (`nvidia`, `metal`, `cpu`, `amd`). Shape: `data/search_contract.json`.
* **`data/models.json`** — the canonical store: one row per model with id, name,
  HF link, license, params, type, VRAM tier, `backends`, `supported_engines`,
  the requirement dimensions (`system_ram_min`, `weight_gb`, `context_tokens`,
  `storage_offload`, `engine_min_version` — all optional), an `engines[]` list of
  per-engine measurements and derived trend fields. Shape:
  `data/model_contract.json` (documented in `data/MODEL_CONTRACT.md`).
* **`data/snapshots/trending-<UTC>.json`** — the full store at every merge. This
  is what proves nothing was ever removed (`check_no_removal`,
  `check_no_value_loss`).
* **`data/gap_baseline.json`** — the gap signature that was last *filed* as an
  issue (written by `make data-gap-issue`, read by the next analysis run).
* **`OPENSPEC.md`** — generated index of every OpenSpec change (see §8).
* **Contracts** are versioned additively: a new *optional* key edits the same
  file; a breaking change adds `*.vN.json` and the validator routes old data to
  the old contract (AGENTS.md §6b).

---

## 3. Every `make` target

Every public target is a **docker wrapper**; the `_`-prefixed recipes it calls
hold the host command. `$(DOCKER_RUN)` runs the **base image**
(`trending-local-llms:latest`), `$(TEST_RUN)` the **test image**
(`trending-local-llms-test:latest`). Nothing runs on the host except what needs
`gh` + the repo itself.

### Images / setup

| Target | What it does |
|---|---|
| `docker-build` | `docker build -t trending-local-llms:latest .` — build the base image unconditionally |
| `docker-test-build` | Build the test image (`Dockerfile.test`) on `$(BASE_IMAGE)` (defaults to the published base) |
| `image-tags` | Print `BASE_TAG` / `TEST_TAG` / `OPENSPEC_TAG` — the content-hash tags the pull-vs-build decision reads (`scripts/ensure_image.py tags`) |
| `image-ensure` | Ensure **both** the base and the test image: pull the published tag for this revision, else build |
| `image-ensure-base` | The base alone (a job that only runs the image needs this) |
| `image-ensure-test` | The test image alone (builds the base first when it is missing) |
| `setup` | Install/refresh the Hermes CLI **inside the container** and write the `nous-deepseek` alias (`model.aliases.nous-deepseek.*`) |
| `update-hermes` | Re-run the Hermes installer in the container (what the Sunday base rebuild relies on) |
| `requirements` | Compile `requirements.in` → `requirements.txt` with `pip-compile` |
| `generate-requirements` | Same for every `*.in` (runtime + test) — the compiled files are never hand-edited |

### Searches (the crawler)

| Target | What it does |
|---|---|
| `search-nvidia` / `search-metal` / `search-cpu` / `search-amd` | One backend each: `_setup` then the Hermes search prompt for that leg, writing `data/raw/<backend>-<UTC>.json` per query. `HERMES_REASONING=none` (mechanical work). |
| `search` | All four legs in sequence |
| `search-smoke` (`BACKEND=<b>`) | Live reachability: the exact Firecrawl → lightbrd scrape of every query for one backend, 3 s cap per query, one retry on timeout/429/5xx (`scripts/smoke_search.py`) |
| `model-caps` | Live: the pinned model is served, `HERMES_MAX_TOKENS` fits its real cap, `reasoning` is accepted (`scripts/model_caps_check.py`) |
| `hermes-smoke` | Live: one real Hermes call through the `nous-deepseek` alias (`scripts/hermes_smoke.sh`) — proves the key/alias/routing before a 20-minute search |
| `pipeline-smoke` | `search-smoke` + `model-caps` + `hermes-smoke` in one go |

### Merge / ingest

| Target | What it does |
|---|---|
| `merge` | `scripts/update_trending.py`: ingest `data/raw/*` into the store, sort, regenerate `README.md`, write a snapshot |
| `merge-fetch` | The same **plus** a direct Firecrawl→lightbrd fetch (`--fetch`) — used by the refresh aggregate |
| `correct-raw` | `scripts/self_correct_raw.py`: prune stray keys / fill `last_seen` in `data/raw/*` so validation sees contract-conforming data |
| `engine-check` | Report every engine mentioned in the raw snapshots that is not registered, and the decision ingest will make (`scripts/engine_registry.py`) |

### Validation (QA)

| Target | What it does |
|---|---|
| `validate` | The full QA run (`--only` = no filter): every stage of `scripts/validate.py` |
| `validate-data` | Stage subset `data,removal` |
| `validate-schema` | Stage subset `schema` |
| `validate-mapped` | Stage subset `data,schema,mapping,removal` (run by CI + the fix loop) |
| `validate-search` | Stage subset `search,mapping` (raw snapshots + search contract) |
| `validate-readme` | Stage subset `readme` (tables well-formed, measurements rendered, ranking) |
| `validate-links` | Stage subset `links` (every link HEAD/GET-checked) |
| `validate-fetch` | Live: a real search that must return hits (`--require-hits`) |
| `qa-report` | `scripts/qa_report.sh` — run the aggregate's QA targets and report **findings** while failing on a target that could not run at all (issue #147) |

### Data-gap analysis

| Target | What it does |
|---|---|
| `data-gaps` | Report what the store still does not capture (missing/unsctructured requirement dimensions, contract gaps), ranked (`scripts/data_gap_analysis.py`) |
| `data-gap-issue` | File **one** issue (label `data-gap-analysis`) when the gap set changed vs `data/gap_baseline.json`; writes the new baseline. Host-side: filing needs `gh` (issue #150) |

### OpenSpec (spec-tracked changes)

| Target | What it does |
|---|---|
| `openspec-image` | Ensure the CLI image (pull the published hash tag, else build from `openspec/Dockerfile`) |
| `openspec-new` (`NAME=`) | `openspec new change <NAME>` — create a tracked change |
| `openspec-validate` (`NAME=`) | `openspec validate <NAME>` for one change |
| `openspec-status` | `openspec status` — every change and its progress |
| `openspec-archive` (`NAME=`) | Move a completed change to `openspec/changes/archive/<NAME>` |
| `openspec-shell` | Interactive shell in the repo with the CLI available |
| `openspec-tasks-check` (`NAME=`) | Fail while an ACTIVE change has an unticked `- [ ]` (`scripts/check_openspec_tasks.py`) |
| `openspec-index` | Regenerate the root `OPENSPEC.md` (`scripts/openspec_index.py --write`) |
| `openspec-index-check` | Fail when `OPENSPEC.md` is stale or a change has no row |
| `openspec-check` | The gate: `openspec validate --changes` + the task check + the index check |

### Findings → issues (rule 6g)

| Target | What it does |
|---|---|
| `findings-check` | Parse `findings.md`; fail loudly when the analysis is missing or a finding lacks Evidence / Why / Done-when (`scripts/file_findings.py --check`) |
| `file-findings` (`ISSUE=`/`PR=`) | File ONE `tech-debt` issue per finding, deduped by signature (`scripts/file_findings.py --file`) |

### The implementer's queue and the issue reviewer (issue #179)

| Target | What it does |
|---|---|
| `issue-queue` | Print the implementer's queue (oldest first) with each candidate's window — the ONE rule both bots read (`scripts/issue_queue.py`) |
| `review-issue-pick` | Choose the ONE issue a review run works: `action=`, `issue=`, `path=`, `reason=` |
| `review-issue-mark` (`ISSUE=` `PATH=`) | Open the reviewer's window: the `review-in-progress` label (+ the marker comment on the `body` path); prints `marker_iso=` and `body_sha=` |
| `review-issue-guard` (`ISSUE=` `PATH=`) | The TOCTOU re-check before any write: exit 0 only while the window still allows that path |
| `review-issue-body-hash` (`ISSUE=`) | The body hash — the proof the `window` path edited nothing |
| `review-issue-check-markers` (`ISSUE=` `FILE=`) | Fail when the rewritten body dropped an invisible marker from the live body |
| `review-issue-finish` (`ISSUE=`) | Close the reviewer's window (remove the label) |
| `review-issue` | The refinement prompt in the container (`_setup` + `_review-issue`) — never implements, never pushes |
| `review-issue-window` | The reply prompt in the container (`_setup` + `_review-issue-window`) — an implementer has started, so the body is off-limits |

### This document

| Target | What it does |
|---|---|
| `architecture-check` | Fail when a public make target, a workflow file or a script is missing from this file, or when this file names something that no longer exists (`scripts/architecture_check.py`) |

### Lint

| Target | What it does |
|---|---|
| `lint` | Fail closed when a tracked text file does not end with a newline (`scripts/lint_linefeeds.py`, `git ls-files` as the file set). The FIRST step of `qa-validate`'s `validate` job and the first check in `scripts/fix_loop.sh` |
| `lint-fix` | Append exactly one newline to each offending file (idempotent) — the repair half, with `.editorconfig` as the editor-side rule |

### Secrets / credentials

| Target | What it does |
|---|---|
| `secret-scan` | gitleaks over the working tree incl. staged files (pinned image + `.gitleaks.toml`); non-zero blocks a push |
| `secret-scan-history` | The same over full git history (needs a real clone; refuses a worktree) |
| `secret-scan-self-test` | Plant a fake credential and require gitleaks to catch it (`scripts/secret_scan_self_test.py`) — a scanner that silently does nothing fails |
| `nerve-check` | Prove the nerve plugin's credential is wired by NAME only, that the plugin is pinned, and that a run without the key fails loudly (`scripts/nerve_key_check.py`) |

### Bots / tests / full runs

| Target | What it does |
|---|---|
| `implement-issue` | The implementer prompt: `_setup` + `_implement-issue` in ONE container. Requires the OpenSpec change (created first, indexed, gate green), the `findings.md` analysis, and the `ARCHITECTURE.md` update |
| `fix` | Repair a red CI: `_setup`, `correct-raw`, the Hermes fix prompt (reads `qa-report.txt`), `_merge` |
| `test` | The whole unit suite in the test image (`_test`) |
| `refresh` | The full pipeline in one container: setup, search, merge, validate, test |
| `all` | Alias for `refresh` |

---

## 4. The pipelines

Five workflows in `.github/workflows/`. Three have a cron: **`refresh-bot.yml`**
(daily), **`issue-bot.yml`** (hourly, `19`) and **`issue-review-bot.yml`**
(hourly, `41`). GitHub delays and sometimes **drops**
on-the-hour crons, hence the odd minutes (:19, :41, 17:43).

### `.github/workflows/refresh-bot.yml` — the crawler (schedule + owner dispatch)

`concurrency: refresh-bot` (queued, never cancelled: two runs must not open
competing PRs over the same generated files).

| Job | Does |
|---|---|
| `guard` | Owner / write-collaborator only, for **both** `github.actor` and `github.triggering_actor`; a `schedule` passes. Every other job needs it, and `aggregate` requires `needs.guard.result == 'success'` |
| `build` | Decide (`scripts/ensure_image.py tags`) whether the **base** must be rebuilt — missing, hash tag unpublished, Sunday, or `force_rebuild` — and push `:latest` + `:dockerfile-<hash>` |
| `test-image` | Same decision for the **test** image → `…-test:latest` + `:test-<hash>` |
| `openspec-image` | Same decision for the **OpenSpec CLI** image → `…-openspec:latest` + `:openspec-<hash>` |
| `search` | Matrix `[nvidia, metal, cpu, amd]`, `fail-fast: false`: prepare the base image, `_search-smoke`, `model-caps`, `hermes-smoke`, then the Hermes search. Each leg uploads its raw snapshots as artifacts |
| `aggregate` | Runs even when a leg failed: collect the artifacts, `merge-fetch`, `correct-raw`, `qa-report`, `make data-gaps`, `make data-gap-issue` (`continue-on-error`: report-only), then **open a PR** (owner PAT, branch `ci/trending-refresh-<UTC>`) only when there is new data. It never merges: `qa-validate`'s `auto-merge` does |

### `.github/workflows/qa-validate.yml` — PR CI (every PR, push to master, dispatch)

| Job | Does |
|---|---|
| `validate` | `make image-ensure`, `make secret-scan`, `make secret-scan-self-test`, `make nerve-check`, `make validate` + `validate-search` + `validate-mapped`, `make openspec-check`, `make architecture-check`, `make test` |
| `live-smoke` | Real network, bounded: `search-smoke` per backend, `model-caps`, `hermes-smoke`, `validate-fetch`. An outage here is infra, not data — it never dispatches fix-bot |
| `dispatch-fixbot` | Only when `validate` failed on a same-repo `ci/trending-refresh-*` PR **and** the PR has fewer than 2 `fix-bot:` commits: dispatch `fix-bot` with `pr_number` + `branch` (owner PAT) |
| `auto-merge` | `needs: [validate, live-smoke]`, `if: success()`: squash-merge + delete the branch with `--match-head-commit <validated sha>`. Never on a fork PR, a draft, or `master`; a push after the run started makes the SHA mismatch and the newer run decides |

### `.github/workflows/fix-bot.yml` — the repairer (`workflow_dispatch` only)

| Job | Does |
|---|---|
| `fix` | Guard first (before any secret), resolve the PR (refuses `master`/`main`), checkout the branch with the PAT, `make hermes-smoke`, then `scripts/fix_loop.sh`: run the deterministic checks → green? stop → else write `qa-report.txt` (only the failing check's output) and `make fix`, at most `FIX_ROUNDS` (3) rounds. It commits (`fix-bot: …`) and pushes **only when the loop ends green**; still red → nothing pushed, the failing lines are commented on the PR. `qa-report.txt` is uploaded as an artifact. It never merges |

### `.github/workflows/issue-bot.yml` — the implementer (hourly sweep + owner dispatch)

`concurrency: issue-bot-<issue|sweep>` (a sweep and an `issues` event for the
same issue queue instead of racing).

| Job | Does |
|---|---|
| `guard` | The same owner/collaborator guard as refresh-bot, before any secret |
| `pick` | Sweep only: `make issue-queue` (`scripts/issue_queue.py`) — the OLDEST open `data-gap-analysis` issue with **no** `ci/data-gap-<n>-*` branch, no open PR from one and no live reviewer marker (a fresh `<!-- issue-review: … run=<id> -->`; the `review-in-progress` label is advisory) (the queue rule has ONE implementation; the reviewer reads the same target). An empty backlog is a green run that implements nothing |
| `implement` | Resolve the issue (must be open) → `issue.md`; checkout `master` (PAT); `make image-ensure`; `make hermes-smoke`; **announce the window** (one start comment `<!-- issue-bot-start: <ISO8601Z> -->` naming the branch and the run, posted with the default token BEFORE the body is read — the signal the reviewer defers to); `make implement-issue`; commit + push `ci/data-gap-<n>-<slug>` (resuming on a re-run, never force-push); **open the PR** (`closes #<n>`, owner PAT so CI runs); run the same fix loop with `REQUIRE_FINDINGS=1`; **file the findings** as their own `tech-debt` issues (`make findings-check` + `make file-findings`, only when the loop is green); comment the outcome on the issue. A run with no implementation is made RED by a named final step |

**Tokens.** `FIXBOT_DISPATCH_TOKEN` (fine-grained PAT: Actions, Contents, Pull
requests R/W) is used where a push or a dispatch must re-trigger CI; the default
`github.token` is used for issue reads/comments (`issues: write`) and for the
findings filing — the PAT cannot comment. No workflow pushes `master`; only
`auto-merge` merges, and only through a green PR.

### `.github/workflows/issue-review-bot.yml` — the reviewer (hourly sweep + owner dispatch)

`concurrency: issue-review-bot` (whole runs queue) plus a per-issue group
(`issue-review-issue-<n>`) so two reviews of one issue queue instead of racing.

| Job | Does |
|---|---|
| `guard` | The same owner/collaborator guard as the other pipelines, before any secret |
| `pick` | `make review-issue-pick`: ONE issue per run — the oldest candidate whose implementer window is CLOSED (`action=review path=body`), else the oldest started issue the reviewer has not answered (`action=window`), else `action=none` (a green no-op). A forced dispatch re-uses the guard to choose the path |
| `review` | Resolve the issue (must be open); checkout `master`; `make image-ensure`; `make hermes-smoke`; write `issue.md` (`gh issue view --comments`); **open the window** (`make review-issue-mark` → `review-in-progress` label + `<!-- issue-review: <ISO8601Z> run=<id> -->`); **re-check it** (`make review-issue-guard`, the TOCTOU guard) and route: **`body`** → `make review-issue` (Hermes refinines `issue-body.md`), `make review-issue-check-markers` (no invisible dedup marker may vanish), publish the body only when it changed (clearing `needs-refinement`) + ONE summary comment; **`window`** → `make review-issue-window` (the body is OFF-LIMITS), PROVE the body hash is unchanged, then post ONE bounded reply carrying the marker. Both paths: file the findings as their own `tech-debt` issues (`make findings-check` + `make file-findings`) and close the window (`make review-issue-finish`, `always()`). No `comment.md` → the run is RED |

`permissions: issues: write, contents: read` — the reviewer never pushes, opens a
branch or merges, and never holds the owner PAT (it comments with
`github.token`, like issue-bot's outcome comment). The quiet window is
`REVIEW_GAP_HOURS := 3` in the Makefile: one constant for both bots — a run in
flight, implementer activity younger than the gap, or the issue within the
implementer's next 3 hourly sweeps all keep the body off-limits.

---

## 5. The images

| Image | Built from | Tag on GHCR | Who publishes | Consumers |
|---|---|---|---|---|
| base `trending-local-llms:latest` | `Dockerfile` (+ `Dockerfile.test` in the hash) | `…/trending-local-llms:dockerfile-<sha12>` | `refresh-bot.yml` `build` | every `$(DOCKER_RUN)` target, the search legs, `aggregate` |
| test `trending-local-llms-test:latest` | `Dockerfile.test` on the base + `requirements-test.txt` | `…-test:test-<sha12>` | `refresh-bot.yml` `test-image` | every `$(TEST_RUN)` target (`validate*`, `test`, `data-gaps`, `nerve-check`) |
| openspec `trending-local-llms-openspec:latest` | `openspec/Dockerfile` (Node + pinned `@fission-ai/openspec`) | `…-openspec:openspec-<sha12>` | `refresh-bot.yml` `openspec-image` | every `openspec-*` target (`make openspec-check` in CI) |

The rule is the same for all three: **the tag names the content it was built
from**, so a pipeline pulls the published tag for *this* revision and otherwise
builds it — one code path via `scripts/ensure_image.py` (`ensure`,
`ensure-base`, `ensure-test`, `ensure-openspec`, `tags`). A Dockerfile change is
therefore inert only until its own hash tag is published, not until the next
Sunday.

Credentials never enter an image: every key reaches a process as `-e <ENV_NAME>`
at run time (the name the consumer actually resolves), never as `ENV`, never in
`config.yaml`, never as a literal.

---

## 6. The scripts

| Script | Role |
|---|---|
| `scripts/update_trending.py` | The engine of the repo: `ingest_raw_snapshots`, `normalize_model`, `merge_engines`, `sort_models`, `recompute_7d_engagement`, `render_readme` (the README template lives here), `write_snapshot`; CLI `--fetch`, `--dry-run`, `--write-raw <backend>`, `--require-hits` |
| `scripts/validate.py` | The QA stages: `data`, `schema`, `mapping`, `removal`, `readme`, `links`, plus report-only checks (post-signal coverage). Every `check_*` is registered in a stage, and every stage appears in a Makefile `--only` list (rule 6d) |
| `scripts/engine_registry.py` | Engine classification + auto-registration at ingest (`classify_repo`, `register_new_engines`), non-engine lists, `KNOWN_ENGINE_URLS` |
| `scripts/data_gap_analysis.py` | The post-refresh gap analysis (§3) — `analyse`, `rank_impact`, `render`, `file_issue`, `ensure_label` |
| `scripts/check_openspec_tasks.py` | Fails an active OpenSpec change with an unticked task box |
| `scripts/openspec_index.py` | Renders / verifies the root `OPENSPEC.md` from `openspec/changes/**` |
| `scripts/file_findings.py` | Parses `findings.md` and files one `tech-debt` issue per finding (deduped, linked, label re-verified) — used by the implementer AND by the reviewer |
| `scripts/issue_queue.py` | The implementer's queue, computed once for both bots: pick order, each candidate's implementer window (`window`/`reason`/`started`), the reviewer's markers and run ids |
| `scripts/issue_review.py` | The reviewer's deterministic core (issue #179): `--pick` (one issue, `body`/`window`/`none`), `--mark`/`--finish` (the `review-in-progress` label + the run-stamped marker), `--guard` (the TOCTOU re-check before a write), `--body-hash` (the proof the window path edited nothing) and `--check-markers` (a rewrite may not drop an invisible dedup marker). It imports `issue_queue` — the queue rule has one implementation |
| `scripts/ensure_image.py` | The single pull-vs-build decision for all three images |
| `scripts/architecture_check.py` | This document's guard: every public target, workflow and script is described here (and nothing stale is) |
| `scripts/lint_linefeeds.py` | The trailing-newline lint (`make lint`) and its repair (`make lint-fix`); `git ls-files` is the file set, binary/empty files are never findings |
| `scripts/self_correct_raw.py` | Prunes stray keys / fills `last_seen` in `data/raw/*` before validation |
| `scripts/hf_id.py` | One HF-identifier definition (a URL-shaped `hf` is reduced to `owner/repo`) |
| `scripts/qa_report.sh` | Runs the aggregate's QA targets; a *finding* is reported, a target that could not run fails the run |
| `scripts/fix_loop.sh` | The fix loop's control flow (check → report → `make fix`, ≤ `FIX_ROUNDS`, reasoning-budget retry). `REQUIRE_FINDINGS=1` makes it demand the analysis file |
| `scripts/hermes_smoke.sh` | The routing smoke (passes on a refusal-free answer through the alias; retries once) |
| `scripts/hermes_update_needed.sh` | Decides whether the baked Hermes install needs a refresh |
| `scripts/model_caps_check.py` | The live model-capability check (`make model-caps`) |
| `scripts/nerve_key_check.py` | The nerve credential wiring guard (`make nerve-check`) |
| `scripts/secret_scan_self_test.py` | Proves gitleaks catches a planted credential |
| `scripts/smoke_search.py` | The per-query reachability smoke with its retry policy |

---

## 7. Guards

`AGENTS.md` §8 is the authoritative table (which test catches which failure and
why it exists). Quick pointers: the data/README contracts are guarded by
`tests/test_validate*.py`, `tests/test_engagement_contract.py`,
`tests/test_readme_render.py`, `tests/test_trend_score.py`; the sorting and
backend rules by `tests/test_amd_backend.py`, `tests/test_post_signal.py`,
`tests/test_engine_aliases.py`, `tests/test_engine_registry.py`; the pipelines by
`tests/test_workflows.py`, `tests/test_fix_loop.py`, `tests/test_ensure_image.py`;
the spec/architecture/index rules by `tests/test_check_openspec_tasks.py`,
`tests/test_openspec_index.py`, `tests/test_file_findings.py`,
`tests/test_architecture.py`; secrets by `tests/test_secret_scan.py`.

---

## 8. The life of a change

```
GitHub issue  →  feature branch (+ worktree off latest master)
              →  OpenSpec change  openspec/changes/<name>/  (proposal · spec with
                 Given/When/Then scenarios, each with a - **Test:** line · tasks)
              →  code + tests (+ ARCHITECTURE.md, AGENTS.md §8, README via its template)
              →  PR (closes #<issue>; qa-validate runs validate + live-smoke)
              →  green  →  auto-merge (squash, branch deleted)
              →  OPENSPEC.md regenerated (the change is listed)  +  findings filed
                 as their own issues (tech-debt)
```

`make openspec-check` is the gate a change must pass before its PR is ready;
`make openspec-index` keeps `OPENSPEC.md` as the one file that lists every change
this repo has ever made.

---

## 9. Known gaps

Filed, not fixed (each is its own issue, per rule 6g):

* `--write-baseline` in `data_gap_analysis.py` is reachable from no target (#174).
* `make merge` re-ingests **every** raw snapshot on every run (#175).
* The `python3 -m pytest tests/` path is dead inside the test image — the suite
  only runs through `_test`'s fallback chain (#176).
* Overlapping refresh PRs conflict on the generated store/README/baseline every
  time `master` moves (#177).
* No bot reviews an issue that nobody has opened a PR for (#179).
