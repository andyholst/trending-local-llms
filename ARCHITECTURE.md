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

The base image **is** the agent image: it bakes the Hermes CLI and the pinned
`keeltrace/hermes-nerve` plugin, and every bot job runs inside it. Two properties
keep it honest (issue #207):

- **one installer seam** — the Dockerfile installs the CLI through
  `scripts/install_hermes_ci.sh` (`ARG HERMES_INSTALL_URL` / `ARG HERMES_PACKAGE`
  carry the pin, so a mirror or a pinned release needs no Dockerfile edit; the
  script tries an existing `hermes` → the URL → `uv tool install`, and **fails the
  build** when none works, because an agent image without an agent is worse than
  none). `make _setup` runs the same seam, so there is no second
  curl-pipe-bash installer to drift from it.
- **a build-time alias assertion** — after copying the repo the build runs
  `make _setup` (which writes the alias from `HERMES_ALIAS` / `HERMES_MODEL` /
  `NOUS_BASE`) and then `make _hermes-alias-check`, which reads every field back
  and fails the BUILD on a mismatch (a wrong model, a provider that is not
  `custom`, a `key_env` that is not `NOUS_API_KEY`). Measured on #124: without the
  alias Hermes auto-routed to `HF_TOKEN` and died with `HTTP 403` — inside a bot
  run, after the image was published. Only the NAME of the key is written; the key
  arrives at run time (`-e NOUS_API_KEY`, rule 3e).

| Target | What it does |
|---|---|
| `docker-build` | `docker build -t trending-local-llms:latest .` — build the base image unconditionally, which also runs the seam and the alias assertion |
| `docker-test-build` | Build the test image (`Dockerfile.test`) on `$(BASE_IMAGE)` (defaults to the published base) |
| `image-tags` | Print `BASE_TAG` / `TEST_TAG` / `OPENSPEC_TAG` — the content-hash tags the pull-vs-build decision reads (`scripts/ensure_image.py tags`) |
| `image-ensure` | Ensure **both** the base and the test image: pull the published tag for this revision, else build |
| `image-ensure-base` | The base alone (a job that only runs the image needs this) |
| `image-ensure-test` | The test image alone (builds the base first when it is missing) |
| `rebuild-decision` | Print the rebuild decision as data — `built`/`test_built`/`publish_openspec` + the tags and the `reason` — so `refresh-bot` reads a tested unit instead of computing the rule inline (issue #208). The day comes from here (`date +%u`, the repo's one call site); `FORCE=` is parsed strictly (`0`/`false` = OFF) |
| `agent-image-ref` | Print this revision's `dockerfile-<sha12>` tag + the `:latest` ref the bots pull (`ensure_image.py ref`) |
| `agent-image-push-check` | Prove the ambient credential can WRITE the package before the build: one empty blob-upload POST, answered with the registry's own refusal when it cannot (`ensure_image.py push-check`) |
| `publish-agent-image` | Build + push the agent image **only when its hash tag is absent**; pushes both the hash tag and `:latest`. `FORCE=1` rebuilds the same inputs. Run by `publish-agent-image.yml`, guarded to owner/collaborators (issue #206) |
| `setup` | Install/refresh the Hermes CLI **inside the container** — through the ONE seam (`scripts/install_hermes_ci.sh`, the same file the image build runs) — and write the alias (`model.aliases.$(HERMES_ALIAS).*`) from the Makefile's own pins |
| `hermes-alias-check` | Prove the container carries the agent it claims: read every `model.aliases.$(HERMES_ALIAS).*` field back and fail loudly on a mismatch (the image build runs the same `_hermes-alias-check`, so a broken pin never reaches a bot run) |
| `update-hermes` | Re-run the Hermes installer in the container (what the Sunday base rebuild relies on) |
| `requirements` | Compile `requirements.in` → `requirements.txt` with `pip-compile` |
| `generate-requirements` | Same for every `*.in` (runtime + test) — the compiled files are never hand-edited |

### Searches (the crawler)

| Target | What it does |
|---|---|
| `search-nvidia` / `search-metal` / `search-cpu` / `search-amd` | One backend each: `_setup` then the Hermes search prompt for that leg, writing `data/raw/<backend>-<UTC>.json` per query. `HERMES_REASONING=none` (mechanical work). |
| `search` | All four legs in sequence |
| `search-smoke` (`BACKEND=<b>`) | Live reachability: the exact Firecrawl → lightbrd scrape of every query for one backend, 3 s cap per query, one retry on timeout/429/5xx (`scripts/smoke_search.py`) |
| `model-caps` | Live: the pinned model is served, `HERMES_MAX_TOKENS` fits its real cap, `reasoning` is accepted (`scripts/model_caps_check.py`). With no `NOUS_API_KEY` it **FAILS loudly** (issue #209) — the endpoint cannot be read, so a green pre-flight would prove nothing |
| `hermes-smoke` | Live: one real Hermes call through the `nous-deepseek` alias (`scripts/hermes_smoke.sh`) — proves the key/alias/routing before a 20-minute search. With no `NOUS_API_KEY` it **FAILS loudly** (issue #209), naming the variable and the alias it could not prove |
| `pipeline-smoke` | `search-smoke` + `model-caps` + `hermes-smoke` in one go. Both live checks need the key: without it they fail rather than skip, so a green `pipeline-smoke` always means the live path really answered. A developer deliberately running without one sets `LIVE_CHECK_ALLOW_UNCONFIGURED=1`, which turns each check into `NOT CONFIGURED` + exit 0 — **no workflow sets it** (guarded in `tests/test_hermes_smoke.py`) |

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
| `issue-queue` | Print the implementer's queue (oldest first) with each candidate's window, its reviewer-verdict hold **and its decided hold** (`agent:refined`/`agent:closed`, applied by `make issue-verdict`, no TTL — a human clears the label) — the ONE rule both bots read (`scripts/issue_queue.py`) |
| `issue-skip-note` | Say ON the held issue why the sweep skipped it (a FRESH reviewer verdict), one comment per review round — the `pick` job's response to an empty pick (issue #200) |
| `issue-thread` (`ISSUE=` `REPO=`) | Print an issue's WHOLE thread for the implementer (issue #210): title, body, every comment oldest-first with author and ISO8601Z, then the decision instruction — the reviewer already read the whole thread; the implementer read only the body |
| `queued-alarm` (`REPO=` `MINUTES=30` `COMMENT=1`) | The stuck-run alarm (issue #252): `scripts/queued_run_alarm.py` lists the jobs still `queued` past the threshold and, with `COMMENT=1`, leaves ONE deduplicated note per affected run. Exit 1 when a job is stuck. Run by `queued-alarm.yml` |
| `code-review-scan` (`REPO=` `STATIC=1` `JSON=1`) | The code-review bot's checks (issue #253): `scripts/code_review.py scan` reads the tree + the pipelines and prints the findings. No model, writes nothing |
| `code-review-file` (`REPO=` `CAP=3` `DRY=1`) | File ONE issue per NEW finding, marker-deduped and capped per run (`scripts/code_review.py file`). Its whole output is issues — it never edits code, never merges. Run by `code-review-bot.yml` |
| `issue-verdict` (`ISSUE=` `TRIAGE_FILE=`) | Apply the implementer's TRIAGE verdict DETERMINISTICALLY (issue #210): `implement` touches nothing (the run continues to its PR), `refine` posts ONE restatement + `agent:refined`, `close` posts the reason with its cited EVIDENCE, closes and applies `agent:closed`. A close with no EVIDENCE, a refine with no restatement and an unknown verdict exit 2 with no write at all |
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
| `check-secret-output` | Fail when any file prints a secret's VALUE, passes it on a command line, xtraces it, dumps the environment around it, or commits a credential-shaped literal (`scripts/check_secret_output.py`) — the run-time leak shapes gitleaks cannot see |
| `secret-output-report` | Show which files name a secret-shaped variable, and whether any prints it (`scripts/check_secret_output.py report`) |
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

Seven workflows in `.github/workflows/`. Five have a cron: **`refresh-bot.yml`**
(daily), **`issue-bot.yml`** (hourly, `19`), **`issue-review-bot.yml`**
(hourly, `41`), **`queued-alarm.yml`** (twice an hour, `7,37`) and
**`code-review-bot.yml`** (weekly Monday `23 7`, its own slot). GitHub delays
and sometimes **drops** on-the-hour crons, hence the odd minutes (:19, :41,
:07/:37, 17:43, 07:23).

### `.github/workflows/refresh-bot.yml` — the crawler (schedule + owner dispatch)

`concurrency: refresh-bot` (queued, never cancelled: two runs must not open
competing PRs over the same generated files).

| Job | Does |
|---|---|
| `guard` | The owner, a collaborator with `admin`/`maintain`/`write`, or `github-actions[bot]` (the bot itself) — for **both** `github.actor` and `github.triggering_actor`; a `schedule` passes. Every other job needs it, and `aggregate` requires `needs.guard.result == 'success'` |
| `build` | Decide through the ONE tested unit (`make rebuild-decision` → `scripts/ensure_image.py decide`, issue #208) whether the **base** must be rebuilt — `:latest` missing, hash tag unpublished, Sunday, or `force_rebuild` — and push `:latest` + `:dockerfile-<hash>` |
| `test-image` | Same decision (`make rebuild-decision`) for the **test** image → `…-test:latest` + `:test-<hash>` |
| `openspec-image` | Same decision (`make rebuild-decision`, output `publish_openspec`) for the **OpenSpec CLI** image → `…-openspec:latest` + `:openspec-<hash>` |
| `search` | Matrix `[nvidia, metal, cpu, amd]`, `fail-fast: false`: prepare the base image, `_search-smoke`, `model-caps`, `hermes-smoke`, then the Hermes search. Each leg uploads its raw snapshots as artifacts |
| `aggregate` | Runs even when a leg failed: collect the artifacts, `merge-fetch`, `correct-raw`, `qa-report`, `make data-gaps`, `make data-gap-issue` (`continue-on-error`: report-only), then **open a PR** (owner PAT, branch `ci/trending-refresh-<UTC>`) only when there is new data. It never merges: `qa-validate`'s `auto-merge` does |

### `.github/workflows/qa-validate.yml` — PR CI (every PR, push to master, dispatch)

| Job | Does |
|---|---|
| `validate` | `make image-ensure`, `make secret-scan`, `make secret-scan-self-test`, `make check-secret-output`, `make nerve-check`, `make validate` + `validate-search` + `validate-mapped`, `make openspec-check`, `make architecture-check`, `make test` |
| `live-smoke` | Real network, bounded: `search-smoke` per backend, `model-caps`, `hermes-smoke`, `validate-fetch`. An outage here is infra, not data — it never dispatches fix-bot |
| `dispatch-fixbot` | Only when `validate` failed on a same-repo `ci/trending-refresh-*` PR **and** the PR has fewer than 2 `fix-bot:` commits: dispatch `fix-bot` with `pr_number` + `branch` (owner PAT) |
| `auto-merge` | `needs: [validate, live-smoke]`, `if: success()`: squash-merge + delete the branch with `--match-head-commit <validated sha>`. Never on a fork PR, a draft, or `master`; a push after the run started makes the SHA mismatch and the newer run decides |

### `.github/workflows/fix-bot.yml` — the repairer (`workflow_dispatch` only)

| Job | Does |
|---|---|
| `fix` | Guard first (before any secret), resolve the PR (refuses `master`/`main`), checkout the branch with the PAT, `make hermes-smoke`, then `scripts/fix_loop.sh`: run the deterministic checks → green? stop → else write `qa-report.txt` (only the failing check's output) and `make fix`, at most `FIX_ROUNDS` (3) rounds. It commits (`fix-bot: …`) and pushes **only when the loop ends green**; still red → nothing pushed, the failing lines are commented on the PR. `qa-report.txt` is uploaded as an artifact. It never merges |

### `.github/workflows/publish-agent-image.yml` — the agent image (`workflow_dispatch` only)

Publishing the agent image is a **privileged, deliberate act** (issue #206): the
base image bakes the Hermes CLI and the packed nerve plugin, and every bot job
runs inside it, so it must not be a side effect of a data refresh and the
credential must be proven before the ten-minute build.

| Job | Does |
|---|---|
| `guard` | FIRST, before any secret: `github.actor` **and** `github.triggering_actor` must be the owner, a collaborator with `admin`/`maintain`/`write` (`gh api …/collaborators/<u>/permission`), or `github-actions[bot]` (the bot itself); anyone else dies here |
| `publish` | `needs: guard`. Checkout → buildx → `make agent-image-ref` → GHCR login with the **default `GITHUB_TOKEN`** as the triggering actor (a PAT that is not an org member is refused `permission_denied: create_package`; measured again here: the `gh` OAuth token is refused `invalid token` by the registry API) → `make agent-image-push-check` (**before** the build: it starts an empty blob upload, so a credential that cannot write fails in seconds with the registry's own words) → `make publish-agent-image` (no-op when this revision's `dockerfile-<sha12>` tag is already published; `FORCE=1` rebuilds the same inputs) → print the refs |

Triggers are `workflow_dispatch` only — no `schedule`, no `pull_request`, no
`push`, no `workflow_run` — so a refresh can never publish the toolchain and a PR
can never trigger a publish copy. It never merges and never pushes a branch.

### `.github/workflows/queued-alarm.yml` — the stuck-run alarm (schedule + dispatch)

`concurrency: queued-alarm` (queued, never cancelled). A job whose runner label matches nothing
does not fail — it stays `queued` forever, so the run never concludes and every PR's checks sit at
"pending" (issue #252). Deterministic, no model.

| Job | Does |
|---|---|
| `guard` | The same owner/collaborator/bot guard as refresh-bot, plus the `schedule` bypass, before any secret |
| `alarm` | `make queued-alarm REPO=… MINUTES=… COMMENT=1` (`scripts/queued_run_alarm.py`): list the `queued`/`in_progress` runs, flag the jobs queued past the threshold (naming the runner label and the age), and comment ONE marker-deduplicated note per affected run. Exit 1 when a job is stuck, so the scheduled run goes red. It never edits code, never opens a PR, never merges |

### `.github/workflows/code-review-bot.yml` — the tree/pipeline reviewer (weekly + dispatch)

`concurrency: code-review-bot` (queued, never cancelled). It reads the TREE and the PIPELINES and
files ONE issue per real finding (issue #253, mirrors llgenie's #269). **No model anywhere**: every
check is deterministic, so a scan is free and cannot invent a finding.

| Job | Does |
|---|---|
| `guard` | The same owner/collaborator/bot guard as refresh-bot, plus the `schedule` bypass, before any secret |
| `review` | `make code-review-scan` (the checks read the real tree + workflows; writes nothing) → `make code-review-file` (`scripts/code_review.py`: ONE issue per NEW finding, `<!-- code-review:<key> -->` marker dedup, capped per run). It never edits code, never opens a PR, never merges, never comments on anyone's PR |

### `.github/workflows/issue-bot.yml` — the implementer (hourly sweep + owner dispatch)

`concurrency: issue-bot-<issue|sweep>` (a sweep and an `issues` event for the
same issue queue instead of racing).

| Job | Does |
|---|---|
| `guard` | The same owner/collaborator/bot guard as refresh-bot, plus the `schedule` bypass, before any secret |
| `pick` | Sweep only: `make issue-queue` (`scripts/issue_queue.py`) — the OLDEST open `data-gap-analysis` issue with **no** `ci/data-gap-<n>-*` branch, no open PR from one, no live reviewer marker (a fresh `<!-- issue-review: … run=<id> -->`) and **no fresh reviewer VERDICT** (`needs-refinement` / `obsolete` / `duplicate` / `already-fixed`, held while younger than `VERDICT_TTL_HOURS`=24 h *measured from the reviewer's newest marker comment* — a label carries no timestamp, so an old one from a cancelled run releases the issue again; the `review-in-progress` label is likewise advisory) (the queue rule has ONE implementation; the reviewer reads the same target). An empty backlog is a green run that implements nothing |
| `pick` → verdict note | When the pick is empty, `make issue-skip-note` (`scripts/issue_queue.py --skip-note`, default token — the owner PAT cannot comment) posts ONE comment on the held issue carrying `<!-- issue-bot-skip: <ISO8601Z> verdict=<label> since=<reviewer ts> -->`, so "why is nobody implementing this?" is answered where the issue lives, once per review round. It writes NO label and edits NO body — the verdict belongs to the reviewer or a human (issue #200) |
| `implement` | Resolve the issue (must be open) → `issue.md` = the WHOLE thread (`make issue-thread`, issue #210); checkout `master` (PAT); `make image-ensure`; `make hermes-smoke`; **announce the window** (one start comment `<!-- issue-bot-start: <ISO8601Z> -->` naming the branch and the run, posted with the default token BEFORE the body is read — the signal the reviewer defers to); `make implement-issue`; **apply its verdict** (`make issue-verdict`: `implement` continues, `refine` posts ONE restatement + `agent:refined`, `close` posts the reason with its evidence + `agent:closed` — both end the run GREEN with no PR, and the sweep skips a decided issue through the shared queue rule); then, for `implement` only: commit + push `ci/data-gap-<n>-<slug>` (resuming on a re-run, never force-push); **open the PR** (`closes #<n>`, owner PAT so CI runs); run the same fix loop with `REQUIRE_FINDINGS=1`; **file the findings** as their own `tech-debt` issues (`make findings-check` + `make file-findings`, only when the loop is green); comment the outcome on the issue. A run with no implementation is made RED by a named final step |

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
| `guard` | The same owner/collaborator/bot guard as the other pipelines, plus the `schedule` bypass, before any secret |
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
| base `trending-local-llms:latest` | `Dockerfile` (+ `Dockerfile.test` in the hash) | `…/trending-local-llms:dockerfile-<sha12>` | `refresh-bot.yml` `build` **and** `publish-agent-image.yml` (the deliberate path, issue #206) | every `$(DOCKER_RUN)` target, the search legs, `aggregate` |
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
| `scripts/issue_thread.py` | Render an issue's whole thread for the implementer (#210): title, body, every comment oldest-first with author + ISO8601Z, then the decision instruction (`TRIAGE`/`REFINED`/`EVIDENCE`/`REASON`). `--paginate` + `.[]` so a multi-page thread parses |
| `scripts/issue_verdict.py` | Apply the implementer's verdict, deterministically (#210): the grammar with its refusals (close without evidence, refine without a restatement, unknown verdict), ONE comment + a verified label, or a close with the evidence posted. No model, no network beyond the `gh` calls it is told to make |
| `scripts/issue_queue.py` | The implementer's queue, computed once for both bots: pick order, each candidate's implementer window (`window`/`reason`/`started`), the reviewer's markers and run ids |
| `scripts/bot_markers.py` | The ONE definition of every bot start/end marker — its name, its shape, its parser and its writer (issue #197, AGENTS.md rule 6j). Every reader (`scripts/issue_queue.py`) goes through it, so a renamed or reworded marker can never silently read as "no bot has started"; the registry also records which markers are already written and which land with #198/#199. `tests/test_bot_markers.py` holds its table in step with AGENTS.md rule 6j |
| `scripts/issue_review.py` | The reviewer's deterministic core (issue #179): `--pick` (one issue, `body`/`window`/`none`), `--mark`/`--finish` (the `review-in-progress` label + the run-stamped marker), `--guard` (the TOCTOU re-check before a write), `--body-hash` (the proof the window path edited nothing) and `--check-markers` (a rewrite may not drop an invisible dedup marker). It imports `issue_queue` — the queue rule has one implementation |
| `scripts/ensure_image.py` | The single pull-vs-build decision for all three images, and the agent image's publish path: `tags`/`ref` print the refs, `ensure*` pull-or-build, `push-check` proves the credential can write the package before a build, `publish [--force]` builds and pushes both refs only when the hash tag is absent (#206); `decide` returns the rebuild rule as data (#208) |
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
| `scripts/check_secret_output.py` | The no-secret-VALUE guard (`make check-secret-output` / `secret-output-report`): a printed value, a value on a command line, an xtrace, an env dump, a `${{ secrets.X }}` in a `run:` block, a committed credential-shaped literal |
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
