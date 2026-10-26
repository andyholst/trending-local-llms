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

**What the guard proves — and what it does not** (issue #182). It compares
**names and two structure claims**, never prose:

* every public `make` target, every workflow file and every script is named here
  (and §6 gives each script a role), and nothing named here is gone;
* every stage a Makefile target passes to `scripts/validate.py --only` is a stage
  the validator registers, and every registered stage is selected by one such list
  (both sides read from `scripts/validate.py` itself, by AST);
* every job §4 claims for a workflow — its `Job` table rows and its bold job
  bullets — is a real `jobs:` key of that workflow, every real job is claimed, and
  every workflow has a §4 section of its own (one parser:
  `scripts/architecture_bot.workflow_jobs`).

It **cannot read prose**: a sentence that is wrong about a real target (`make
merge` runs in the test image), a step renamed inside a job, or a claim about an
image's contents all pass. That boundary is deliberate — the paragraph a reader
needs is the one a generator cannot write — so "the guard keeps this file true"
means exactly the three bullets above and no more.

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
10. [The living inventory (generated)](#10-the-living-inventory-generated)

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
| `search-nvidia` / `search-metal` / `search-cpu` / `search-amd` | One backend each: first the loud credential + backend pre-flight (`_search-preflight`: `require_env.py FIRECRAWL_API_KEY`, then the existing `search-smoke` — issue #357 — then `agent-shell-keys-check` for `FIRECRAWL_API_KEY` and `HF_TOKEN`, proving the AGENT's shell can see both — issue #359/#363), then `_setup` and the Hermes search prompt for that leg, writing `data/raw/<backend>-<UTC>.json` per query. `HERMES_REASONING=none` (mechanical work). The whole command runs through the `scrubbed_run` seam, so only a bounded, REDACTED tail of the agent's conversation reaches the console (issue #355) |
| `search` | All four legs in sequence, through the same seam |
| `query-coverage` (`TOP=<n>`) | Report which of the top-N trending models the search queries name — the hand-curated set vs the full set (curated + derived), one line per model — and **FAIL** when one is named by none, so a stale or broken derivation is loud and separable from "the query ran and found nothing" (issue #264). Runs in `_validate-search` |
| `search-smoke` (`BACKEND=<b>`) | Live reachability: the exact Firecrawl → lightbrd scrape of every query for one backend, 3 s cap per query, one retry on timeout/429/5xx (`scripts/smoke_search.py`) |
| `model-caps` | Live: the pinned model is served, `HERMES_MAX_TOKENS` fits its real cap, `reasoning` is accepted (`scripts/model_caps_check.py`). With no `NOUS_API_KEY` it **FAILS loudly** (issue #209) — the endpoint cannot be read, so a green pre-flight would prove nothing |
| `hermes-smoke` | Live: one real Hermes call through the `nous-deepseek` alias (`scripts/hermes_smoke.sh`) — proves the key/alias/routing before a 20-minute search. With no `NOUS_API_KEY` it **FAILS loudly** (issue #209), naming the variable and the alias it could not prove |
| `pipeline-smoke` | `search-smoke` + `model-caps` + `hermes-smoke` in one go. Both live checks need the key: without it they fail rather than skip, so a green `pipeline-smoke` always means the live path really answered. A developer deliberately running without one sets `LIVE_CHECK_ALLOW_UNCONFIGURED=1`, which turns each check into `NOT CONFIGURED` + exit 0 — **no workflow sets it** (guarded in `tests/test_hermes_smoke.py`) |

### Merge / ingest

| Target | What it does |
|---|---|
| `merge` | `scripts/update_trending.py`: ingest the `data/raw/*` snapshots **newer than the store's `generated_utc`** into the store — an older snapshot is already folded in, so it is skipped, and one this code cannot date is always merged (issue #175, `--since <ISO8601Z>` overrides the derived boundary) — sort, regenerate `README.md`, write a snapshot |
| `render-readme` | Render `README.md` from the store **as of its own `generated_utc`** and nothing else: no raw ingest, no `generated_utc` bump, no snapshot (issue #195). A template/docs change uses this, so its PR carries the README and no store churn; the README keeps the `> Last generated:` line it already had, so a re-run is a no-op. `make merge` remains the path for new data |
| `merge-fetch` | The same **plus** a direct Firecrawl→lightbrd fetch (`--fetch`) — used by the refresh aggregate |
| `correct-raw` | `scripts/self_correct_raw.py`: prune stray keys / fill `last_seen` in `data/raw/*` so validation sees contract-conforming data |
| `engine-check` | Report every engine mentioned in the raw snapshots that is not registered, and the decision ingest will make (`scripts/engine_registry.py`) |
| `engine-meta-capture` | Record GitHub metadata (`full_name`, `description`, `topics`) for every registry engine the OFFLINE test fixture `tests/fixtures/github_meta.json` lacks (`scripts/engine_registry.py --capture-meta`, issue #334). Writes only what is missing and never invents an entry it could not read; the refresh aggregate runs it right after the merge that registers a new engine |

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
| `refresh-run-block` | Print the current refresh run's WINDOW (issue #199): the marker line + `started=` + each leg's start + `aggregate=`, all from the run's REAL job timestamps read via `gh api` (`scripts/refresh_run_block.py`). Host-run, like `data-gap-issue`: `gh` lives on the runner, not in the image (#150). `aggregate` embeds it as the PR body; `make data-gap-issue` embeds it in the gap issue |
| `data-gap-issue` | File **one** issue (label `data-gap-analysis`) when the gap set changed vs `data/gap_baseline.json`; writes the new baseline. Host-side: filing needs `gh` (issue #150) |
| `data-gap-baseline` | The filer's REPAIR half (issue #174): record the current gap signature as `data/gap_baseline.json` **without** filing an issue — the fix for a baseline write lost to a rebase or a refresh PR closed before it merged. Host-side, like `data-gap-issue` (it writes the file as the caller, never as root through the mount), and deliberately NOT in the refresh pipeline: run there it would set the baseline to the current set every run and silently stop the analysis filing anything |

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
| `openspec-archive-check` | Fail when an ACTIVE change's `PR:` line names a MERGED PR — the change should have been archived in that PR (`scripts/openspec_archive_check.py`; host-side, needs `gh`) |
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
| `issue-pick` | Print the ONE `key=value` line a sweep reads — `issue=<n>`, or `issue=` when nothing is takeable (`scripts/issue_queue.py --pick`). The producer names its own pick, so no workflow re-derives it with a `sed`/`awk` of the queue row; its reasoning goes to stderr (issues #547/#548) |
| `issue-skip-note` | Say ON the held issue why the sweep skipped it (a FRESH reviewer verdict), one comment per review round — the `pick` job's response to an empty pick (issue #200) |
| `issue-thread` (`ISSUE=` `REPO=`) | Print an issue's WHOLE thread for the implementer (issue #210): title, body, every comment oldest-first with author and ISO8601Z, then the decision instruction — the reviewer already read the whole thread; the implementer read only the body |
| `sweep-alarm` (`REPO=` `MAX_AGE_HOURS=3`) | The delivery alarm (issue #497): `scripts/sweep_alarm.py` reads the newest `schedule` run of `issue-bot.yml` and exits 1 when it is older than `MAX_AGE_HOURS`, naming the age, the missed `:19` slots, the gaps and the last conclusion (2 when GitHub cannot be read). A dropped cron has no run to look at, so `queued-alarm` cannot see it. Run by `queued-alarm.yml` |
| `freshness-alarm` (`REPO=` `MAX_AGE_HOURS=`) | Fail when the newest committed snapshot is older than the window (default 14 h — one missed twice-daily slot), naming the age, the newest scheduled refresh run and the remedy (issue #452). An alarm over the ARTIFACT: a cron GitHub DROPPED leaves no run row for any other alarm to read (`scripts/freshness_alarm.py`) |
| `queued-alarm` (`REPO=` `MINUTES=30` `COMMENT=1`) | The stuck-run alarm (issue #252): `scripts/queued_run_alarm.py` lists the jobs still `queued` past the threshold and, with `COMMENT=1`, leaves ONE deduplicated note per affected run. Exit 1 when a job is stuck. Run by `queued-alarm.yml` |
| `pr-health` (`REPO=` `COMMENT=1`) | The silent-PR alarm (issue #442): an OPEN PR GitHub cannot merge (`CONFLICTING`) gets NO `pull_request` runs at all — its checks are ABSENT, not failed — and a PR whose head commit has no runs is a pipeline that never started. `scripts/pr_health.py` lists the open non-draft PRs, keeps the two reasons apart, prints the head branch and, with `COMMENT=1`, leaves ONE deduplicated note naming the fix (`make worktree-resume` → merge the base → `git push origin HEAD:refs/heads/<PR head>` — the measured #436 shape, where a repair went to a differently-named local branch). Exit 1 when a PR is silent. Run by `pr-health.yml` |
| `code-review-scan` (`REPO=` `STATIC=1` `JSON=1`) | The code-review bot's checks (issue #253): `scripts/code_review.py scan` reads the tree + the pipelines and prints the findings. No model, writes nothing |
| `code-review-file` (`REPO=` `CAP=3` `DRY=1`) | File ONE issue per NEW finding, marker-deduped and capped per run (`scripts/code_review.py file`). Its whole output is issues — it never edits code, never merges. Run by `code-review-bot.yml` |
| `issue-state` (`ISSUE=` `REPO=`) | The issue a run was working is still open? (issue #520) `scripts/issue_verdict.py --state`: exit 0 = open, 4 = **closed** (a merged PR finished it while the run was in flight — a GREEN outcome, with one comment), 2 = unreadable (never a pass). Used by `issue-bot`'s final failure step before it declares a run red |
| `issue-verdict` (`ISSUE=` `TRIAGE_FILE=`) | Apply the implementer's TRIAGE verdict DETERMINISTICALLY (issue #210): `implement` touches nothing (the run continues to its PR), `refine` posts ONE restatement + `agent:refined`, `close` posts the reason with its cited EVIDENCE, closes and applies `agent:closed`. A close with no EVIDENCE, a refine with no restatement and an unknown verdict exit 2 with no write at all |
| `review-issue-pick` | Choose the ONE issue a review run works: `action=`, `issue=`, `path=`, `reason=`. Per-candidate diagnostics are `candidate=<n> position=…` lines, so the only `issue=` line is the action's and carries the NUMBER alone (issue #344). Every `ISSUE=` target below shares the internal `_review-issue-number` guard, which refuses a value that is not digits instead of reaching argparse |
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
| `architecture-check` | Fail when a public make target, a workflow file or a script is missing from this file, or when this file names something that no longer exists (`scripts/architecture_check.py`) — and when the generated inventory block (§10) no longer matches the tree (`scripts/architecture_bot.py --check`, issue #479). Two structural claims are checked too (issue #182): every `--only` stage list of the `validate*` targets against `scripts/validate.py`'s stage map (both directions), and every job §4 claims for a workflow against that workflow's real `jobs:` keys (both directions, plus "no §4 section"). Prose is NOT read — see the boundary at the top of this file |
| `architecture-refresh` | Regenerate the inventory block in §10 from the tree itself: every workflow's triggers/crons/jobs and the `make` targets each job calls, the product end to end, one line per script from its own docstring, and the README sections a refresh rewrites (`scripts/architecture_bot.py --write`, issue #479). Host target, stdlib only; `architecture-bot.yml` runs it daily and opens a PR only when the block changed |

### PR lifecycle (rule 6e)

| Target | What it does |
|---|---|
| `git-identity` | Set the repository's committer identity from its ONE definition (`scripts/agent_identity.py`, issue #325): every committing job calls this seam instead of hand-keeping the same two `git config` lines, the authorship guard reads the same module's allowed sets, and a change to the address is one edit. Host target — `git config` is host-side, no image |
| `pr-body` (`ISSUE=<n>` `BRANCH=<head branch>`) | Print the IMPLEMENTATION PR body the issue-bot opens (issue #287): the whole text GitHub parses for the closure, composed by `scripts/pr_body.py` instead of a workflow heredoc. The single `Closes #<n>` claim comes from the same module and is read back by `scripts/pr_closure.py`; a branch that encodes a different issue is REFUSED (exit 2, empty stdout). The recipe is `@`-silenced, so the workflow can redirect it straight into `pr-body.md`. Runs on the runner's own `python3`, like `refresh-run-block` |
| `pr-closure` (`PR_EVENT=<event json>` · or `BRANCH=<head> BODY_FILE=<pr body>`) | Fail when the PR does not close the issue its branch implements (`scripts/pr_closure.py`, issue #284): a closing keyword whose clause chains a second reference is refused (`Closes #1 and #2` would close only #1), a branch issue with no keyword bound to it is refused, and a PR whose branch implements no issue must not close one (the refresh PR references its tracking issue). In CI the default reads `$GITHUB_EVENT_PATH` by PATH — nothing is interpolated into a `run:` block. A non-PR event is a green no-op. Runs in `qa-validate`'s `validate` job |
| `verify-closure` (`PR=<n>` `REPO=<owner/name>`) | After a merge, PROVE the issue the body claimed to close actually closed (`scripts/verify_closure.py`, issue #288): `pr-closure` PREDICTS the closure from GitHub's parser semantics, and PR #272 shows the difference (`Closes #271 and #276` closed #271, left #276 open, every job green). Reads the merged PR's own `closingIssuesReferences` (fetching an issue's state when the reference omits it), retries briefly because GitHub's close trails the merge call, exits 1 naming the issue and its state, and is LOUD when `gh` itself fails. A PR that closes nothing is not a failure. Read-only; runs as the last step of `auto-merge` |

### Lint

| Target | What it does |
|---|---|
| `lint` | Fail closed when a tracked text file does not end with a newline (`scripts/lint_linefeeds.py`) or a tracked Python module raises a `SyntaxWarning` on compile (`scripts/lint_syntax.py`); both use `git ls-files` as the file set. It ALSO runs `make check-agent-skills` (`scripts/check_agent_skills.py`), so a bot leg that lost its project skill reds the same gate. The FIRST step of `qa-validate`'s `validate` job and the first check in `scripts/fix_loop.sh` |
| `lint-fix` | Append exactly one newline to each offending file (idempotent) — the repair half, with `.editorconfig` as the editor-side rule |
| `reset-working-files` | Unstage the bot's working files (`issue.md`, `pr-body.md`, `findings.md`, `implement.log`, …) before `git add -A`, from the ONE list `scripts/issue_bot_working_files.txt`; called by both bots' commit steps (issue #543) |
| `check-working-files` | Fail when a name in that list is not gitignored — a name that is not ignored can be staged by any other step (`scripts/reset_working_files.py --check`); runs in `make lint` (issue #543) |
| `check-conflict-markers` | Fail when a tracked file carries a git conflict block (`<<<<<<<`, `=======`, `|||||||`, `>>>>>>>` at the start of a line), naming every path and line; `git ls-files` is the file set, binary files are skipped and ignored/untracked files are never scanned (`scripts/check_conflict_markers.py`). Both bot commit steps run it immediately BEFORE `git add -A`, and `make lint` runs it too — a marker in a parsed file makes every later `make` fail (issue #588) |
| `check-agent-skills` | Fail when a `hermes -z` leg preloads no skill, names one that does not exist, preloads a skill whose frontmatter `name` disagrees with its directory or that lost `## Inputs`/`## Output`/`## Rules`, inlines the unattended contract, or grew past its pointer budget — and when the `Makefile` lost the seam documentation or the registration target (`scripts/check_agent_skills.py`, issue #549) |
| `agent-skills-report` | Print every leg with its prompt size and preloaded skills, and every skill's frontmatter, plus whether `AGENTS.md` already states the owed rule for it (report-only) |
| `hermes-skills-register` | Register this checkout's `.hermes/skills` in the container's Hermes home so `hermes -s <name>` resolves (`scripts/hermes_skills_register.py`); `_setup` runs it and reads it back with `_hermes-skills-check` |

### The bots' contracts live in project skills (issue #549)

| Skill | Which leg preloads it | What it is |
|---|---|---|
| `.hermes/skills/bot-unattended` | every leg, beside its own | The unattended contract, written ONCE: never ask a question, never wait for input, decide from the input and write only the file your own skill names. `--yolo --accept-hooks` answers shell and hook prompts but NOT the agent's `clarify`, so a run that asks exits 3 with the tree untouched |
| `.hermes/skills/data-search` | `_search-nvidia`, `_search-metal`, `_search-cpu`, `_search-amd` | One backend's refresh search: lightbrd.com through the Firecrawl scrape API with the key read by NAME, one query at a time, per-query `--write-raw`, clean `tps`, the exact `source_post` with its engagement counters, never fabricate |
| `.hermes/skills/issue-implement` | `_implement-issue` | Triage `issue.md` against the fetched tree first (implement / refine / close-with-evidence), then OpenSpec-first, additive-only, findings-as-issues, the gates |
| `.hermes/skills/issue-review` | `_review-issue`, `_review-issue-window` | The reviewer's two paths: refine the body, or reply once with evidence while the body is off-limits; markers survive, no `gh` writes |
| `.hermes/skills/pr-fix` | `_fix` | Repair a red PR from `qa-report.txt`: the failing checks, never the report, never a weakened test, contract evolution and link repair |

The directory is registered in the container's Hermes home by `_setup`
(`scripts/hermes_skills_register.py`, read back by `_hermes-skills-check`), and each leg's inline
prompt is a pointer plus that run's parameters — `scripts/check_agent_skills.py` fails a leg that
breaks any of it.

### Where work starts — the base is fetched and asserted (rule 6n, issue #271)

| Target | What it does |
|---|---|
| `base-check` (`BASE=<branch>`) | Fetch `origin/<base>` and **FAIL** unless this checkout IS the fetched tip — a fresh `actions/checkout` is the latest `origin/master` only by accident of the runner, and a stale base is otherwise indistinguishable from a fresh one (`scripts/worktree_base.py check`). Host target: git and its credentials live on the runner, not in a container that would write into the shared `.git`. Runs as the first step of `issue-bot`'s `implement` job and of `refresh-bot`'s `aggregate` — the two jobs that cut a branch |
| `branch-adopt` (`BRANCH=` `BASE=`) | The COMMIT-time half of rule 6n (issue #500): `scripts/worktree_base.py adopt` cuts or attaches the issue's branch from the CURRENT `HEAD` **without** re-asserting the base, reporting `behind_base=N` — the base was asserted at the start of the run, and re-asserting it after 25 minutes of work discarded a finished implementation. Used by `issue-bot.yml`'s commit step |
| `base-rebase` (`BRANCH=` `BASE=`) | Bring the branch's commits onto the fetched tip (issue #500): `worktree_base.py rebase` rebases, treats up-to-date as a no-op, and on a **conflict aborts and exits 3** so every commit survives and the caller still pushes (the PR's fix loop repairs the conflict). A dirty tree is refused |
| `base-advance` (`BASE=<branch>`) | Fetch `origin/<base>` and **fast-forward this CLEAN checkout onto it** — the CI shape for a job that has written nothing yet (issue #448): `refresh-bot`'s `aggregate` asserts its base after ~40 min of searching while `master` routinely merges, so the strict refusal threw a whole refresh away (run 39329834698: 4/4 legs green, HEAD 2 commits behind). Refuses a dirty tree or a HEAD with commits the base does not have (`scripts/worktree_base.py advance`). Host target like `base-check`, and runs as the first step of `refresh-bot`'s `aggregate` |
| `refresh-sync` (`BASE=`) | Publish a refresh on the base as it is NOW (issue #177): every file a refresh PR carries is generated and every merge rewrites it, so a branch cut from a base the queue has left is a whole-file conflict waiting for `auto-merge` (PR #164: rebased twice in one hour, then `GraphQL: Pull Request has merge conflicts` while the checks were green). `scripts/refresh_base.py sync` fetches the base and, when the tree is behind it, resets the GENERATED files onto the tip while KEEPING the run's raw snapshots and `data/gap_baseline.json` — the caller then re-runs `make merge SINCE=<oldest raw this run gathered>` so the store, README and baseline are RE-DERIVED on that base instead of applied from an older one. Refuses a dirty path outside the generated set and a HEAD with commits of its own; prints `sync=current|reset`, `base_sha`, `raw_floor`. Host target, like its `base-*` kin. Run by `refresh-bot`'s commit step |
| `refresh-require-tip` (`BASE=`) | The guard that stops a queued refresh from opening a PR against a `master` it has already left (issue #177): `scripts/refresh_base.py require-tip` fetches the base and FAILS unless it is already contained in `HEAD`, naming the repair (`make refresh-sync && make merge`). Run by `refresh-bot` after the commit, BEFORE the push and the PR — a stale branch fails the run loudly instead of going conflicting after its checks are green |
| `worktree-new` (`BRANCH=<kebab> [BASE=master] [IN_PLACE=1] [DIR=<path>]`) | Start a NEW branch at the fetched tip, in a **worktree** at `../<repo>-wt/<kebab>` (default) or in place (`IN_PLACE=1`, the CI shape — a fresh runner checkout IS the working copy). Refuses an existing branch rather than re-cutting it, refuses a worktree inside the repository (the pipelines stage with `git add -A`), refuses the base branch as a target, and proves the caller's HEAD, branch and local base branch are untouched (`scripts/worktree_base.py new`) |
| `worktree-resume` (`BRANCH=<kebab> [BASE=master] [IN_PLACE=1] [DIR=<path>]`) | Resume an existing branch (a re-run): **fetch it first**, then attach. A bare `git checkout <branch>` cannot work in a clone that fetched one ref (`pathspec … did not match any file(s) known to git` — the measured #271 failure). Reuses the worktree that already holds the branch, reports `behind_base=`, and refuses to reset a branch carrying commits that are not on the remote (never `-B` on the worktree path) (`scripts/worktree_base.py resume`) |

### Secrets / credentials

| Target | What it does |
|---|---|
| `secret-scan` | gitleaks over the working tree incl. staged files (pinned image + `.gitleaks.toml`); non-zero blocks a push |
| `secret-scan-history` | The same over full git history (needs a real clone; refuses a worktree) |
| `secret-scan-self-test` | Plant a fake credential and require gitleaks to catch it (`scripts/secret_scan_self_test.py`) — a scanner that silently does nothing fails |
| `check-secret-output` | Fail when any file prints a secret's VALUE, passes it on a command line, xtraces it, dumps the environment around it, or commits a credential-shaped literal (`scripts/check_secret_output.py`) — the run-time leak shapes gitleaks cannot see |
| `secret-output-report` | Show which files name a secret-shaped variable, and whether any prints it (`scripts/check_secret_output.py report`) |
| `scrub-log` | Redact a captured agent log and print at most a bounded tail, never the raw stream (`FILE=… [LOG_OUT=…] [TAIL=40]`, `scripts/scrub_log.py`) — the secret VALUES are read from the environment **by name** (one list, in `check_secret_output.py`) and every spelling of each (raw, URL-encoded, base64) plus every credential SHAPE becomes `***`; the REDACTED whole log is what a bot uploads as its artifact |
| `check-commit-authorship` | Fail when a commit's author/committer identity, or a crediting trailer in its message, is not an allowed one (`scripts/check_commit_authorship.py`) — the only identities are Andy Holst and Asimov Agent (issue #317) |
| `commit-authorship-report` | Show every commit in the range with its author, committer and subject (`scripts/check_commit_authorship.py report`) |
| `nerve-check` | Prove the nerve plugin's credential is wired by NAME only, that the plugin is pinned, and that a run without the key fails loudly (`scripts/nerve_key_check.py`) |
| `agent-shell-keys-check` | Prove every credential a container receives is visible in the AGENT's shell (`scripts/agent_shell_keys_check.py`, issue #359): runs a command through Hermes's own terminal environment in the bot image and fails, naming the variable, when a key set in the container reads EMPTY there. Hermes strips provider credentials from its terminal on purpose, so the run wrappers forward each key of the ONE `AGENT_SHELL_KEYS` list as `-e _HERMES_FORCE_<NAME>` (by name, exported from `<NAME>` on the host). Every search leg's pre-flight runs it for `FIRECRAWL_API_KEY` and `HF_TOKEN` (issue #363: the legs verify a model's Hugging Face link, which an unauthenticated lookup answers rate-limited) |

### Bots / tests / full runs

| Target | What it does |
|---|---|
| `implement-issue` | The implementer prompt: `_setup` + `_implement-issue` in ONE container. Requires the OpenSpec change (created first, indexed, gate green), the `findings.md` analysis, and the `ARCHITECTURE.md` update |
| `fix` | Repair a red CI: `_setup`, `correct-raw`, the Hermes fix prompt (reads `qa-report.txt`), `_merge` — through the `scrubbed_run` seam, so a caller (the fix loop, a human) sees only a bounded, REDACTED tail of the agent's conversation (issue #355) |
| `test` | The whole unit suite in the test image (`_test` → `scripts/run_tests.sh`) |
| `refresh` | The full pipeline in one container: setup, search, merge, validate, test |
| `all` | Alias for `refresh` |

---

## 4. The pipelines

Eleven workflows in `.github/workflows/`. Seven have a cron: **`refresh-bot.yml`**
(daily `06:00`, backup `17:43`), **`issue-bot.yml`** (hourly, `19`),
**`issue-review-bot.yml`** (hourly, `41`), **`queued-alarm.yml`** (twice an hour,
`7,37`), **`pr-health.yml`** (twice an hour, `23,53`),
**`code-review-bot.yml`** (weekly Monday `23 7`, its own slot) and
**`architecture-bot.yml`** (daily `05:13`, issue #479). GitHub delays and
sometimes **drops** on-the-hour crons, hence the odd minutes (:13, :19, :41,
:07/:37, :23/:53, 17:43, 07:23). The other four are event- or dispatch-driven:
`qa-validate.yml` (`pull_request`/`push`/dispatch), `fix-bot.yml` and
`publish-agent-image.yml` (dispatch only) and `pr-closure.yml` (`pull_request`).

The **living inventory** of every pipeline — its triggers, its jobs and the
`make` targets those jobs call, with the Makefile's own description of each — is
generated, not written by hand: §10 is derived from the tree by
`scripts/architecture_bot.py` (`make architecture-refresh`), refreshed hourly by
`architecture-bot.yml` — which also regenerates `OPENSPEC.md` (`make openspec-index`, issue #526)
— and gated by `make architecture-check`. What follows is
the prose that explains *why* each pipeline exists; §10 is the part that cannot
drift.

### `.github/workflows/architecture-bot.yml` — the generated documents' keeper (hourly `13` + dispatch)

`concurrency: architecture-bot` (queued, never cancelled). `ARCHITECTURE.md` is part of
every change (rule 6h), but its mechanical half — which bot has which job, which `make`
target each job calls, how a model reaches `README.md` — rots silently: prose is only
noticed when a name is *missing* (`scripts/architecture_check.py`), never when a
description has moved on. **No model anywhere**: the block is derived from the tree, so
the bot cannot invent a claim about the system.

| Job | Does |
|---|---|
| `guard` | The same owner/collaborator/bot guard as the other bots, plus the `schedule` bypass, as the FIRST job (rule 6j) |
| `refresh` | `needs: guard`. Checkout master with the owner PAT → `make base-check` (rule 6n: the branch is cut from the fetched tip, never assumed) → `make architecture-refresh` (`scripts/architecture_bot.py --write`: every workflow's triggers/crons/jobs + the `make` targets each calls, the product end to end, one line per script from its own docstring, the README sections a refresh rewrites) → `make architecture-check` (the WHOLE document, not only the block) → when the block changed, commit `docs(architecture): …` on `ci/architecture-<UTC ending in Z>`, push, and open a PR whose body carries NO closing keyword (it implements no issue, and `pr_closure` refuses a claim over an issue it does not implement). A run where the block already matches the tree is a GREEN no-op: no branch, no PR |

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
| `aggregate` | Runs even when a leg failed: collect the artifacts, `make base-advance` (the base `ci/trending-refresh-<UTC>` is cut from is FETCHED and, since the four search legs run for ~40 min while `master` merges, the clean checkout is ADVANCED onto it — issue #448; rule 6n), `merge-fetch`, `engine-meta-capture` (the merge is what auto-registers an engine; its GitHub metadata is recorded into the offline test fixture so this PR is not red on `make test`, #334), `correct-raw`, `qa-report`, `make data-gaps`, `make data-gap-issue` (`continue-on-error`: report-only), then **open a PR** (owner PAT, branch `ci/trending-refresh-<UTC>`) only when there is new data — and that PR body LEADS with the run's WINDOW (`make refresh-run-block`, issue #199: the marker + `started=` + each leg's start + `aggregate=`, from the run's real job timestamps), so an in-flight refresh is readable from the PR itself. It never merges: `qa-validate`'s `auto-merge` does |

### `.github/workflows/qa-validate.yml` — PR CI (every PR, push to master, dispatch)

| Job | Does |
|---|---|
| `guard` | FIRST job (issue #279): owner / write+ collaborator / `github-actions[bot]` for BOTH actor and triggering actor; a `pull_request`/`push` run is admitted outright (GitHub starts it for the repository itself, and a PR must be validated whatever its author). The 30-minute network-bound DISPATCH is what this guards |
| `validate` | `make lint`, `make check-commit-authorship` (only Andy Holst / Asimov Agent author, commit or co-author — issue #317; its checkout uses `fetch-depth: 0` because the guard reads a range), `make pr-closure` (the PR closes the issue its branch implements, rule 6e), `make image-ensure`, `make secret-scan`, `make secret-scan-self-test`, `make check-secret-output`, `make nerve-check`, `make validate` + `validate-search` + `validate-mapped`, `make openspec-check`, `make openspec-archive-check` (the lifecycle guard: an active change may not name a merged PR, rule 6f — its own step because `gh` lives on the host, not in the agent container), `make architecture-check`, `make test` |
| `live-smoke` | Real network, bounded: `search-smoke` per backend, `model-caps`, `hermes-smoke`, `agent-shell-keys-check` (the real secrets are visible in the agent's shell, issue #359), `validate-fetch`. An outage here is infra, not data — it never dispatches fix-bot |
| `dispatch-fixbot` | Only when `validate` failed on a same-repo `ci/trending-refresh-*` PR **and** the PR has fewer than 2 `fix-bot:` commits: dispatch `fix-bot` with `pr_number` + `branch` (owner PAT) |
| `auto-merge` | `needs: [validate, live-smoke]`, `if: success()`: squash-merge + delete the branch with `--match-head-commit <validated sha>`. Never on a fork PR, a draft, or `master`; a push after the run started makes the SHA mismatch and the newer run decides, and then runs `make verify-closure` so a body whose keyword did not bind leaves a RED run (issue #288) |

### `.github/workflows/fix-bot.yml` — the repairer (`workflow_dispatch` only)

| Job | Does |
|---|---|
| `guard` | The owner, a collaborator with `admin`/`maintain`/`write`, or `github-actions[bot]`, for **both** `github.actor` and `github.triggering_actor`. Its own FIRST job, declaring **no secret at all** — a job-level `env:` holding `secrets.*` is materialised when the JOB starts, so a guard that is only the first *step* of the secret-carrying job is not "before any secret" (rule 6j, issue #259) |
| `fix` | `needs: [guard]`, so a refused caller means this job never starts and its four secrets are never materialised. Resolve the PR (refuses `master`/`main`), then announce the repair window ON the PR (`<!-- fix-bot-start: <ISO8601Z> run=<id> -->` + branch + run URL, default `github.token`, body on stdin — so it lands BEFORE the branch is read, and no scratch file exists for `git add -A` to commit), checkout the branch with the PAT, `make hermes-smoke`, then `scripts/fix_loop.sh`: run the deterministic checks → green? stop → else write `qa-report.txt` (only the failing check's output) and `make fix`, at most `FIX_ROUNDS` (3) rounds. It commits (`fix-bot: …`) and pushes **only when the loop ends green**; still red → nothing pushed, the failing lines are commented on the PR. `qa-report.txt` is uploaded as an artifact. It never merges |

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

### `.github/workflows/pr-closure.yml` — the closure check on the artifact it reads (PR only)

`make pr-closure`'s input is the PR **body**, and a body changes without a new commit
(issue #290). `qa-validate` triggers on GitHub's default `pull_request` types, so an edit was
never re-checked and a body that broke its closure kept a green check.

- **`guard`** — the FIRST job (rule 6j); `pull_request` is a repository event, so it is admitted
  outright (the same clause `qa-validate`'s guard carries).
- **`closure`** (`needs: guard`) — `actions/checkout` then `make pr-closure`, which reads the
  webhook payload by path (`$GITHUB_EVENT_PATH`, the Makefile's `PR_EVENT` default); an
  `edited` event carries the **new** body, so the verdict always describes what is on screen.

Two jobs, seconds long, read-only (no push, no comment, no merge). Its own pipeline on purpose:
adding `edited` to `qa-validate` would re-run the image builds, the unit suite and the
30-minute network-bound `live-smoke` — a real Firecrawl spend — because a sentence changed.

### `.github/workflows/pr-health.yml` — the silent-PR alarm (twice an hour, `23,53`)

A conflicting PR runs no workflows at all (issue #442), so `gh pr checks` answers "no checks
reported" and nothing distinguishes it from a quiet queue.

- **`guard`** — the FIRST job (rule 6j); the scheduled run passes it by design.
- **`sweep`** (`needs: guard`) — `actions/checkout`, then `make pr-health REPO=… COMMENT=1`. The
  comment uses the DEFAULT token (`pull-requests: write`, rule 6b). Exit 1 when a PR is silent, so
  the scheduled run goes red.

### `.github/workflows/queued-alarm.yml` — the stuck-run alarm (schedule + dispatch)

`concurrency: queued-alarm` (queued, never cancelled). A job whose runner label matches nothing
does not fail — it stays `queued` forever, so the run never concludes and every PR's checks sit at
"pending" (issue #252). Deterministic, no model.

| Job | Does |
|---|---|
| `guard` | The same owner/collaborator/bot guard as refresh-bot, plus the `schedule` bypass, before any secret |
| `alarm` | Two steps, no other job: `make queued-alarm REPO=… MINUTES=… COMMENT=1` (`scripts/queued_run_alarm.py`) — list the `queued`/`in_progress` runs, flag the jobs queued past the threshold (naming the runner label and the age), and comment ONE marker-deduplicated note per affected run; exit 1 when a job is stuck, so the scheduled run goes red — then `make sweep-alarm REPO=… MAX_AGE_HOURS=3`, so a sweep the cron never delivered is red here too (issue #497). It never edits code, never opens a PR, never merges. The silent-PR sweep (`make pr-health`) is its own pipeline, `pr-health.yml`, below |

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
| `pick` | Sweep only: `make issue-pick` (`scripts/issue_queue.py --pick`) — prints the ONE line the step copies (`issue=<n>` / `issue=`), with its reasoning on stderr, so no `sed`/`awk` re-derives the row; the queue itself is the OLDEST open `data-gap-analysis` issue with **no** `ci/data-gap-<n>-*` branch, no open PR from one, no live reviewer marker (a fresh `<!-- issue-review: … run=<id> -->`) and **no fresh reviewer VERDICT** (`needs-refinement` / `obsolete` / `duplicate` / `already-fixed`, held while younger than `VERDICT_TTL_HOURS`=24 h *measured from the reviewer's newest marker comment* — a label carries no timestamp, so an old one from a cancelled run releases the issue again; the `review-in-progress` label is likewise advisory) (the queue rule has ONE implementation; the reviewer reads the same target). An empty backlog is a green run that implements nothing |
| `pick` → verdict note | On EVERY sweep (never only when the pick is empty, issue #202), `make issue-skip-note` (`scripts/issue_queue.py --skip-note`, default token — the owner PAT cannot comment) posts ONE comment on the held issue carrying `<!-- issue-bot-skip: <ISO8601Z> verdict=<label> since=<reviewer ts> -->`, so "why is nobody implementing this?" is answered where the issue lives, once per review round. It writes NO label and edits NO body — the verdict belongs to the reviewer or a human (issue #200) |
| `implement` | Resolve the issue (must be open) → `issue.md` = the WHOLE thread (`make issue-thread`, issue #210); checkout `master` (PAT); **assert the base it will cut from** (`make base-check`, rule 6n — a fresh `actions/checkout` is the latest `origin/master` only by accident of the runner); `make image-ensure`; `make hermes-smoke`; **announce the window** (one start comment `<!-- issue-bot-start: <ISO8601Z> -->` naming the branch and the run, posted with the default token BEFORE the body is read — the signal the reviewer defers to); `make implement-issue`; **apply its verdict** (`make issue-verdict`: `implement` continues, `refine` posts ONE restatement + `agent:refined`, `close` posts the reason with its evidence + `agent:closed` — both end the run GREEN with no PR, and the sweep skips a decided issue through the shared queue rule); then, for `implement` only: commit + push `ci/data-gap-<n>-<slug>` (resuming on a re-run, never force-push); **open the PR** (`closes #<n>`, owner PAT so CI runs); run the same fix loop with `REQUIRE_FINDINGS=1`; **file the findings** as their own `tech-debt` issues (`make findings-check` + `make file-findings`, only when the loop is green); comment the outcome on the issue. A run with no implementation is made RED by a named final step |

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
| `review` | Resolve the issue (must be open); checkout `master`; `make image-ensure`; `make hermes-smoke`; write `issue.md` (`gh issue view --comments`, `id: thread` — every step that consumes it is gated on `steps.thread.outcome == 'success'`); **open the window** (`make review-issue-mark` → `review-in-progress` label + `<!-- issue-review: <ISO8601Z> run=<id> -->`); **re-check it** (`make review-issue-guard`, the TOCTOU guard) and route: **`body`** → `make review-issue` (Hermes refinines `issue-body.md`), `make review-issue-check-markers` (no invisible dedup marker may vanish), publish the body only when it changed (clearing `needs-refinement`) + ONE summary comment; **`window`** → `make review-issue-window` (the body is OFF-LIMITS), PROVE the body hash is unchanged, then post ONE bounded reply carrying the marker. Both paths: file the findings as their own `tech-debt` issues (`make findings-check` + `make file-findings`) and close the window (`make review-issue-finish`, `always()` **and only when `mark` succeeded**, so a run that never opened one never closes one). No `comment.md` → the run is RED |

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
| `scripts/update_trending.py` | The engine of the repo: `ingest_raw_snapshots` (merges only the snapshots newer than the `since` boundary `main()` derives from the store's `generated_utc`; `raw_snapshot_stamp`/`parse_utc_stamp` are the one definition of a snapshot's capture instant, issue #175), `normalize_model`, `merge_engines`, `sort_models`, `recompute_7d_engagement`, `render_readme` (the README template lives here), `write_snapshot`; a NEW model's Hugging Face repo is resolved against the HF API during `main()`'s merge and a dead id is named loudly (`hf_repo_resolves`/`note_unresolved_hf`, issue #333 — indeterminate answers are never a finding, and `HF_MODEL_API` is the test seam); CLI `--fetch`, `--dry-run`, `--write-raw <backend>`, `--require-hits`, `--since <ISO8601Z>` |
| `scripts/validate.py` | The QA stages: `data`, `schema`, `mapping`, `removal`, `readme`, `links`, plus report-only checks (post-signal coverage). Every `check_*` is registered in a stage, and every stage appears in a Makefile `--only` list (rule 6d) |
| `scripts/engine_registry.py` | Engine classification + auto-registration at ingest (`classify_repo`, `register_new_engines`), non-engine lists, `KNOWN_ENGINE_URLS`; `--check-raw DIR` reports what ingest will decide, `--capture-meta` records a registered engine's GitHub metadata into the offline test fixture (`capture_meta`, issue #334) |
| `scripts/data_gap_analysis.py` | The post-refresh gap analysis (§3) — `analyse`, `rank_impact`, `render`, `file_issue`, `ensure_label`. The issue body LEADS with the refresh run's window block (#199) |
| `scripts/refresh_run_block.py` | The refresh run's WINDOW block (#199): `render` is pure (a fixed fixture renders the exact expected block), `fetch` reads the run's REAL job timestamps via `gh api`, `current_block()` is the one composer both the PR body and the gap issue embed. Its marker line comes from `scripts/bot_markers.py`, so the shared parser reads it |
| `scripts/check_openspec_tasks.py` | Fails an active OpenSpec change with an unticked task box |
| `scripts/openspec_index.py` | Renders / verifies the root `OPENSPEC.md` from `openspec/changes/**`; `discover()` takes the changes directory (the lifecycle guard reads the same layout through it) |
| `scripts/openspec_archive_check.py` | The lifecycle's end (rule 6f, issue #183): fails when an ACTIVE change's `PR:` line names a MERGED pull request, naming the change, the PR and the two commands (`make openspec-archive`, `make openspec-index`); skips a change with no `PR:` line and archived changes; exits 2 — never 0 — when the GitHub read fails. PR state via `gh api …/pulls/<n> --jq .merged` |
| `scripts/file_findings.py` | Parses `findings.md` and files one `tech-debt` issue per finding (deduped, linked, label re-verified) — used by the implementer AND by the reviewer |
| `scripts/check_agent_skills.py` | The bots' contract gate (issue #549): every `hermes -z` leg must preload a project skill and `bot-unattended`; the named skill must exist with a matching frontmatter `name` and `## Inputs`/`## Output`/`## Rules`; no recipe may inline the unattended contract; a leg's prompt stays under the pointer budget; the `Makefile` keeps the seam and its registration target. `check` exits 1 on any finding, `report` prints every leg and skill |
| `scripts/hermes_skills_register.py` | Register the checkout's `.hermes/skills` in the Hermes home so `hermes -s <name>` resolves — through `hermes config get/set` (the repo's Python has no PyYAML), idempotent, `--check` verifies without writing, exit 2 on a missing CLI or directory (issue #549) |
| `scripts/issue_thread.py` | Render an issue's whole thread for the implementer (#210): title, body, every comment oldest-first with author + ISO8601Z, then the decision instruction (`TRIAGE`/`REFINED`/`EVIDENCE`/`REASON`). `--paginate` + `.[]` so a multi-page thread parses |
| `scripts/issue_verdict.py` | Apply the implementer's verdict, deterministically (#210): the grammar with its refusals (close without evidence, refine without a restatement, unknown verdict), ONE comment + a verified label, or a close with the evidence posted. Reads the decoration a model actually writes — leading markdown, a wrapped or spaced colon, a case-different key, emphasis/quotes around the value and a trailing reason after the verdict word (#245) — while an unknown verdict still refuses. No model, no network beyond the `gh` calls it is told to make |
| `scripts/issue_queue.py` | The implementer's queue, computed once for both bots: pick order, each candidate's implementer window (`window`/`reason`/`started`), the reviewer's markers and run ids |
| `scripts/bot_markers.py` | The ONE definition of every bot start/end marker — its name, its shape, its parser and its writer (issue #197, AGENTS.md rule 6j). Every reader (`scripts/issue_queue.py`) goes through it, so a renamed or reworded marker can never silently read as "no bot has started"; the registry also records which markers are already written and which land with #198/#199. `tests/test_bot_markers.py` holds its table in step with AGENTS.md rule 6j |
| `scripts/issue_review.py` | The reviewer's deterministic core (issue #179): `--pick` (one issue, `body`/`window`/`none`), `--mark`/`--finish` (the `review-in-progress` label + the run-stamped marker), `--guard` (the TOCTOU re-check before a write), `--body-hash` (the proof the window path edited nothing) and `--check-markers` (a rewrite may not drop an invisible dedup marker). It imports `issue_queue` — the queue rule has one implementation |
| `scripts/ensure_image.py` | The single pull-vs-build decision for all three images, and the agent image's publish path: `tags`/`ref` print the refs, `ensure*` pull-or-build, `push-check` proves the credential can write the package before a build, `publish [--force]` builds and pushes both refs only when the hash tag is absent (#206); `decide` returns the rebuild rule as data (#208) |
| `scripts/architecture_check.py` | This document's guard: every public target, workflow and script is described here (and nothing stale is), every `--only` stage list matches the validator's stage map, and every job §4 claims is a real one (issues #178, #182) |
| `scripts/issue_bot_working_files.txt` | The ONE list of the files a bot run writes at the repository root and that must never be staged, committed or pushed (issue #543) |
| `scripts/reset_working_files.py` | Unstages the bot's working files from the list `scripts/issue_bot_working_files.txt` (`make reset-working-files`), and asserts every name on it is gitignored (`--check`, `make check-working-files`, in `make lint`) |
| `scripts/check_conflict_markers.py` | Refuses a merge-conflict block in a tracked file (`make check-conflict-markers`), called by both bots before `git add -A`; `git ls-files` is the file set, binary and ignored files are never findings |
| `scripts/lint_linefeeds.py` | The trailing-newline lint (`make lint`) and its repair (`make lint-fix`); `git ls-files` is the file set, binary/empty files are never findings |
| `scripts/lint_syntax.py` | The syntax-warning lint (`make lint`, issue #190): every tracked `*.py` module must compile without a `SyntaxWarning`; compiled from source so no import side effect runs, the tracked-file set so an untracked module is never a finding |
| `scripts/self_correct_raw.py` | Prunes stray keys / fills `last_seen` in `data/raw/*` before validation. Writes a snapshot only when it actually changed it and then refreshes its `generated_utc`, so a corrected snapshot is re-merged by the next `make merge` instead of being skipped as old (issue #175) |
| `scripts/hf_id.py` | One HF-identifier definition (a URL-shaped `hf` is reduced to `owner/repo`) |
| `scripts/qa_report.sh` | Runs the aggregate's QA targets; a *finding* is reported, a target that could not run fails the run |
| `scripts/run_tests.sh` | The ONE unit-test runner (`make test` → `_test`, issues #176/#192): discovers `tests/test_*.py`, runs each in its own process, and stops at the FIRST red with that module's own output (`--list` prints what it would run; a directory with no modules is red) |
| `scripts/fix_loop.sh` | The fix loop's control flow (check → report → `make fix`, ≤ `FIX_ROUNDS`, reasoning-budget retry). `REQUIRE_FINDINGS=1` makes it demand the analysis file |
| `scripts/hermes_smoke.sh` | The routing smoke (passes on a refusal-free answer through the alias; retries once) |
| `scripts/hermes_update_needed.sh` | Decides whether the baked Hermes install needs a refresh |
| `scripts/model_caps_check.py` | The live model-capability check (`make model-caps`) |
| `scripts/nerve_key_check.py` | The nerve credential wiring guard (`make nerve-check`) |
| `scripts/agent_shell_keys_check.py` | The agent-shell credential guard (`make agent-shell-keys-check`, issue #359): drives Hermes's real `LocalEnvironment` and reports, per key, whether the container's value is visible in the agent's shell — lengths only, never a value; a key missing from the container is a loud exit 2 |
| `scripts/secret_scan_self_test.py` | Proves gitleaks catches a planted credential |
| `scripts/check_secret_output.py` | The no-secret-VALUE guard (`make check-secret-output` / `secret-output-report`): a printed value, a value on a command line, an xtrace, an env dump, a `${{ secrets.X }}` in a `run:` block, a committed credential-shaped literal, a captured agent stream with no redactor (`raw-agent-log-captured`), a step printing a captured log (`raw-agent-log-printed`), and a Python script that reads a key value and prints it (issue #351) |
| `scripts/require_env.py` | The loud credential pre-flight (`_search-preflight`, issue #357): fails (exit 2) when a named environment variable is missing or EMPTY — the shape a missing GitHub secret takes at run time — naming the variable and how to set it, and never printing a value. `--allow-unconfigured` is a loud local opt-out that reports NOT CONFIGURED |
| `scripts/scrub_log.py` | The agent-log redactor (`make scrub-log`): replaces every spelling of every secret VALUE present in the environment — read by NAME, never echoed — plus every credential shape with `***`, writes the REDACTED whole log to `--out`, and prints at most a bounded tail |
| `scripts/agent_identity.py` | The agent identity's ONE definition (issue #325): `AGENT_NAME`/`AGENT_EMAIL`, the `ALLOWED_NAMES`/`ALLOWED_EMAILS` the authorship guard imports, and `--git-config` (the body of `make git-identity`) |
| `scripts/check_commit_authorship.py` | The commit-authorship guard (`make check-commit-authorship` / `commit-authorship-report`, issue #317): every commit's author AND committer identity must be Andy Holst / Asimov Agent / the repo's own `github-actions[bot]`, and every crediting trailer in the message must name one of those. It reads the identity because GitHub SYNTHESIZES the squash `Co-authored-by:` from it — the message alone misses the measured leak (`054b0c8`). Default range `origin/master..HEAD`; an unreadable range exits 2 |
| `scripts/pr_closure.py` | Does this PR close the issue it implements (rule 6e, issue #284)? Reads the head branch and the body from the webhook payload by PATH (never interpolated into a `run:` block), derives the issue the branch implements (`ci/data-gap-<n>-<slug>`; a `ci/trending-refresh-*` branch implements none), and refuses a closing keyword that chains a second reference, a branch issue with no keyword bound to it, or a closing keyword on a PR that implements no issue. Code is not a claim — a keyword inside a fenced block or an inline code span is ignored, because GitHub links nothing there (measured: this change's own PR). Reached only through `make pr-closure` (rules 6d/6m) |
| `scripts/pr_body.py` | Composes the issue-bot implementation PR body (issue #287): the text that decides whether the issue closes on merge is now a target's output (`make pr-body ISSUE=… BRANCH=…`), not a YAML heredoc — so a test runs it, `make pr-closure` reads the same text, and the wording no longer claims every change is a data-gap one. Imports `pr_closure.implemented_issue()` so the composer and the guard derive the branch's issue the same way, and refuses a branch that implements a different issue than the body closes. Reached only through `make pr-body` (rules 6d/6m) |
| `scripts/worktree_base.py` | Where work starts (rule 6n, issue #271): `check` fetches the base and fails unless this checkout IS the fetched tip; `new` starts a branch at that tip in a worktree (`../<repo>-wt/<kebab>`) or in place, refusing an existing branch, a worktree inside the repo, and the base branch as a target; `resume` fetches an existing branch before attaching, reuses its worktree, reports `behind_base=`, and never resets a branch with commits that are not on the remote; `advance` fast-forwards a CLEAN checkout onto the fetched tip for a job that has written nothing yet (`refresh-bot`'s `aggregate`, issue #448), refusing a dirty tree or a diverged HEAD. Every worktree path proves the caller's HEAD, branch and local base branch are untouched. Reached only through `make base-check` / `base-advance` / `worktree-new` / `worktree-resume` (rules 6d/6m) |
| `scripts/query_coverage.py` | CLI over the query-coverage rule: `--queries` prints the derived model queries the four search prompts append as `$(MODEL_QUERIES)`; the default run prints the coverage report and exits 1 when a top-N trending model is named by no query. The rule itself — which query names which model — has ONE implementation in `scripts/update_trending.py` (rule 6d), so the prompts, the guard and its tests can never disagree (issue #264) |
| `scripts/smoke_search.py` | The per-query reachability smoke with its retry policy |
| `scripts/architecture_bot.py` | The LIVING half of this document (issue #479, rule 6h): derives §10 from the tree — every workflow's triggers/crons/jobs and the `make` targets each job calls, the product end to end, one line per script, the `README.md` sections a refresh rewrites. `--write` regenerates between the markers, `--check` fails on a stale block, and a flow step the tree no longer backs is refused (never written). Reached only through `make architecture-refresh` / `architecture-check` (rules 6d/6m); the daily `architecture-bot.yml` runs both |
| `scripts/code_review.py` | The code-review bot's decision half (issue #253): `scan` runs DETERMINISTIC checks over the tree and the pipelines (no model, writes nothing), `file` opens ONE issue per NEW finding with a `<!-- code-review:<key> -->` dedup marker, capped per run. Analysis only — it never edits code, never merges, never comments on anyone's PR |
| `scripts/env_int.py` | ONE reading of a numeric SETTING (issue #487): `env_int`/`env_float` treat unset **or** blank (`""`, `"   "`) as the default — the shape an unconditionally-forwarded make variable takes at run time — and a non-numeric value raises `EnvSettingError` naming the variable and what it held (a typo is never silently the default). Every `int`/`float` environment read in `scripts/` goes through it; a bare `int(os.environ…)` fails `tests/test_pr_health.py` |
| `scripts/pr_health.py` | The silent-PR alarm (issue #442) and its repair half (issue #475): lists open non-draft PRs, flags every one that is `CONFLICTING` or has NO check runs on its head commit (a conflicting PR runs no workflows at all), names the fix, and — `--repair` — dispatches `fix-bot` for a silent `ci/…` PR, capped at `MAX_FIXBOT_COMMITS` fix-bot commits per PR. `--comment` leaves ONE deduplicated note per affected PR; read-only apart from that. Exit 1 when any PR is silent, so the scheduled sweep goes red |
| `scripts/freshness_alarm.py` | The stale-index alarm (`make freshness-alarm`, issue #452): measures the newest `data/snapshots/trending-*.json` by the timestamp IN ITS NAME (never mtime) and fails when it is older than `MAX_AGE_HOURS`. Read-only |
| `scripts/queued_run_alarm.py` | The stuck-run alarm (issue #252): reads the repo's `queued`/`in_progress` runs (a run whose jobs are ALL queued reports `queued`, the state this exists for), flags every job queued past `--minutes` with its runner label and age, comments ONE `<!-- queued-run-alarm -->`-deduped note per affected run, and exits 1 so the scheduled run goes red. A runner label that matches nothing never FAILS a job, so nothing else sees it |
| `scripts/sweep_alarm.py` | The dropped-cron alarm (issue #497): GitHub silently skips scheduled slots, and a slot it never created has no run for `queued-alarm` to read — so this reads the ARTIFACT (the newest `schedule` delivery of the sweep) and exits non-zero when it is older than `--max-age-hours` (default 3), printing the age, the slots that should have run and the gaps it can see, plus the last run's conclusion |
| `scripts/refresh_base.py` | Publishes a refresh on the base as it is NOW (issue #177, extended by #500/#501): a refresh PR is entirely generated files that every other merge rewrites, so `sync` fetches the base and resets/rebases the clean checkout onto it, while `require-tip` refuses to publish when the checkout is not the fetched tip. Adopts the bot's own branch rather than cutting a new one, so a moved `master` cannot discard the run's work |
| `scripts/verify_closure.py` | After a MERGE, proves the issue the PR body claimed to close actually closed (issue #288): reads the merged PR's own `closingIssuesReferences` (fetching an issue's state when the reference omits it), retries briefly because GitHub's close trails the merge call, and is LOUD when `gh` itself fails. `pr-closure` PREDICTS the closure, this proves it; a PR that closes nothing is not a failure. Read-only, last step of `auto-merge` |
| `scripts/install_hermes_ci.sh` | The ONE way the Hermes CLI enters this repo's image (issue #207): already installed → `HERMES_INSTALL_URL` → `uv tool install`, else **FAIL the build** — an agent image without an agent must not be produced. The Dockerfile build and `make _setup` run the same seam (a second curl-pipe-bash installer is a defect), and no credential is ever baked: the pin lives in `ARG HERMES_INSTALL_URL` / `ARG HERMES_PACKAGE` and the key arrives at run time (rule 3e) |

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
GitHub issue  →  its own worktree, cut off the freshly fetched origin/master
                 (`make worktree-new BRANCH=<kebab>` → ../<repo>-wt/<kebab>;
                  `make base-check` asserts the base — rule 6n; never the user's
                  checkout, never `master` itself, never a re-cut branch)
              →  OpenSpec change  openspec/changes/<name>/  (proposal · spec with
                 Given/When/Then scenarios, each with a - **Test:** line · tasks)
              →  code + tests (+ ARCHITECTURE.md, AGENTS.md §8, README via its template)
              →  PR (closes #<issue>; qa-validate runs validate + live-smoke)
              →  the change's PR: # line is recorded, and the PR that completes it
                 runs `make openspec-archive NAME=<change>` + `make openspec-index`
                 (the change moves to openspec/changes/archive/, listed as archived)
              →  green  →  auto-merge (squash, branch deleted)
              →  OPENSPEC.md regenerated (the change is listed)  +  findings filed
                 as their own issues (tech-debt)
```

`make openspec-check` is the gate a change must pass before its PR is ready;
`make openspec-index` keeps `OPENSPEC.md` as the one file that lists every change
this repo has ever made.

A change's life ENDS in the PR that completes it: once its `PR: #<n>` line is
known, that PR runs `make openspec-archive NAME=<change>` (moving the directory
to `openspec/changes/archive/<name>`) and `make openspec-index`, so the archive
and the regenerated index land in one commit — the merge is still `auto-merge`'s.
`make openspec-archive-check` enforces it: every ACTIVE change's `PR:` line is
read, and a PR GitHub reports as merged fails the check (qa-validate's `validate`
job runs it with `pull-requests: read`). A change with no `PR:` line cannot be
asserted about and is skipped; an archived change is the expected state.

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

---

## 10. The living inventory (generated)

The block below is **derived from the tree itself** by `scripts/architecture_bot.py` and
rewritten by `make architecture-refresh` — the hourly `architecture-bot.yml` runs it and
opens a PR only when the block actually changed. The same bot keeps `OPENSPEC.md` current
(issue #526): a squash merge of two concurrent `openspec/changes/**` entries keeps one index
file and leaves the other change's row out, which reds every `qa-validate` push run on master
until something regenerates it, so the keeper gates on either file and commits both. It is the mechanical half of this
document: every pipeline with the triggers, jobs and `make` targets that make it up, the
product end to end (how an X post becomes a `README.md` row), one line per script from
that script's own docstring, and the README sections a refresh rewrites. Every reference
in it is verified against the tree by `make architecture-check`, which fails when the
block is stale — so a change that adds a target, a workflow, a script or a README section
either regenerates this block or turns CI red.

Do not edit between the markers by hand: change the code it describes, then run the target.

<!-- architecture-bot:begin -->
_Generated from the tree itself by `scripts/architecture_bot.py` (`make architecture-refresh`); `.github/workflows/architecture-bot.yml` regenerates it daily and opens a PR only when it changed. Do not edit this block by hand — change the code it describes and run the target._

### Bots in the tree (11 pipelines, 165 make targets, 54 files in `scripts/`)

Every pipeline, what starts it, the jobs it runs and the `make` targets those jobs call (with the Makefile's own description of each target).

#### `.github/workflows/architecture-bot.yml` — architecture-bot

- **when:** cron `13 * * * *`, `workflow_dispatch`
- **jobs:** `guard`, `refresh` (needs `guard`)
- **calls:** `make base-check` — Fail unless this checkout IS the freshly fetched <BASE> (CI runs it before it cuts a branch); `make architecture-refresh` — Regenerate ARCHITECTURE.md's inventory block from the tree (rule 6h, issue #479); `make openspec-index` — Regenerate the root OPENSPEC.md index from openspec/changes/**; `make architecture-check` — Fail when ARCHITECTURE.md misses a make target, a workflow or a script — or its generated inventory is stale (rule 6h); `make git-identity`; `make check-commit-authorship` — CI: fail when a commit's author/committer identity or a crediting trailer is not an allowed one (issue #317)

#### `.github/workflows/code-review-bot.yml` — code-review-bot

- **when:** cron `23 7 * * 1`, `workflow_dispatch`
- **jobs:** `guard`, `review` (needs `guard`)
- **calls:** `make code-review-scan` — The code-review bot's checks: tree + pipelines -> findings (REPO=<owner/name>, STATIC=1 skips the checks that read the GitHub API, JSON=1 machine output; writes nothing); `make code-review-file` — File ONE issue per NEW code-review finding, capped per run (REPO=<owner/name>, CAP= issues per run, DRY=1 previews) — never edits code, never merges

#### `.github/workflows/fix-bot.yml` — fix-bot

- **when:** `workflow_dispatch`
- **jobs:** `guard`, `fix` (needs `guard`)
- **calls:** `make image-ensure`; `make hermes-smoke`; `make git-identity`; `make check-conflict-markers` — Fail when a tracked file carries a merge-conflict block (issue #588); `make reset-working-files` — Unstage the bot's working files (one list: $(WORKING_FILES); issue #543); `make lint` — Fail when a tracked text file does not end with a newline, a tracked Python module raises a SyntaxWarning, or a bot leg lost its project skill; `make validate-search`; `make validate-mapped`; `make openspec-check` — CI gate: every active change validates, every task ticked, the index current; `make architecture-check` — Fail when ARCHITECTURE.md misses a make target, a workflow or a script — or its generated inventory is stale (rule 6h); `make test`; `make fix`; `make findings-check` — Fail when findings.md is missing or a finding lacks evidence / why / done-when

#### `.github/workflows/issue-bot.yml` — issue-bot

- **when:** cron `19 * * * *`, `49 * * * *`, `issues`, `workflow_dispatch`
- **jobs:** `guard`, `pick` (needs `guard`), `implement` (needs `guard`, `pick`)
- **calls:** `make issue-pick` — Print the ONE key=value line a sweep reads (`issue=<n>` or `issue=`; issues #547/#548); `make issue-skip-note` — Say on the held issue why the sweep skipped it (one comment per review round); `make base-check` — Fail unless this checkout IS the freshly fetched <BASE> (CI runs it before it cuts a branch); `make image-ensure`; `make hermes-smoke`; `make issue-thread` — Print an issue's whole thread for the implementer (ISSUE=<n>, REPO=<owner/name>); `make issue-state` — Print the issue's state: exit 0 = open, 4 = closed, 2 = unreadable (ISSUE=<n>, REPO=) (issue #520); `make scrub-log` — Redact a captured agent log and print at most a bounded tail, never the raw stream (FILE=… [LOG_OUT=…] [TAIL=40]); `make check-secret-output` — CI: fail when any file prints a secret's VALUE, passes it on a command line, xtraces it, dumps the environment around it, or commits a credential-shaped literal; `make implement-issue`; `make issue-verdict` — Apply the implementer's TRIAGE verdict from triage.md (ISSUE=<n>, TRIAGE_FILE=<path>); `make git-identity`; `make check-conflict-markers` — Fail when a tracked file carries a merge-conflict block (issue #588); `make branch-adopt` — Cut or attach BRANCH at COMMIT time, reporting behind_base=N and asserting NO base (issue #500) (BRANCH=, BASE=); `make reset-working-files` — Unstage the bot's working files (one list: $(WORKING_FILES); issue #543); `make base-rebase` — Fetch the base and rebase BRANCH onto it; a conflict KEEPS the work and still SUCCEEDS (`base_rebase=conflict`) (BRANCH=, BASE=); `make pr-body` — Print the implementation PR body for ISSUE=<n> [BRANCH=<head branch>]; `make findings-check` — Fail when findings.md is missing or a finding lacks evidence / why / done-when; `make file-findings` — File ONE issue per finding in findings.md (host-side: needs gh + the repo); `make lint` — Fail when a tracked text file does not end with a newline, a tracked Python module raises a SyntaxWarning, or a bot leg lost its project skill; `make validate-search`; `make validate-mapped`; `make openspec-check` — CI gate: every active change validates, every task ticked, the index current; `make architecture-check` — Fail when ARCHITECTURE.md misses a make target, a workflow or a script — or its generated inventory is stale (rule 6h); `make test`; `make fix`

#### `.github/workflows/issue-review-bot.yml` — issue-review-bot

- **when:** cron `41 * * * *`, `workflow_dispatch`
- **jobs:** `guard`, `pick` (needs `guard`), `review` (needs `guard`, `pick`)
- **calls:** `make review-issue-guard` — Re-check that ISSUE= may still be written (PATH=body|window); `make review-issue-pick` — Choose the ONE issue this review run works (action=/issue=/path=); `make image-ensure`; `make hermes-smoke`; `make review-issue-mark` — Open the reviewer's window on ISSUE= (PATH=body|window); `make review-issue`; `make scrub-log` — Redact a captured agent log and print at most a bounded tail, never the raw stream (FILE=… [LOG_OUT=…] [TAIL=40]); `make review-issue-check-markers` — Fail when FILE= dropped an invisible marker from ISSUE='s body; `make review-issue-window`; `make review-issue-body-hash` — Print the body hash of ISSUE= (proves the window path edited nothing); `make findings-check` — Fail when findings.md is missing or a finding lacks evidence / why / done-when; `make file-findings` — File ONE issue per finding in findings.md (host-side: needs gh + the repo); `make review-issue-finish` — Close the reviewer's window on ISSUE=

#### `.github/workflows/pr-closure.yml` — pr-closure

- **when:** `pull_request`
- **jobs:** `guard`, `closure` (needs `guard`)
- **calls:** `make pr-closure` — Fail when this PR does not close the issue its branch implements (rule 6e)

#### `.github/workflows/pr-health.yml` — pr-health

- **when:** cron `23,53 * * * *`, `workflow_dispatch`
- **jobs:** `guard`, `sweep` (needs `guard`)
- **calls:** `make pr-health`

#### `.github/workflows/publish-agent-image.yml` — publish-agent-image

- **when:** `workflow_dispatch`
- **jobs:** `guard`, `publish` (needs `guard`)
- **calls:** `make agent-image-ref` — Print the GHCR refs of the agent image for this revision's Dockerfile; `make agent-image-push-check` — CI: prove the ambient credential can PUSH the agent image, before the build; `make publish-agent-image` — Build + push the agent image when its hash tag is absent (FORCE=1 rebuilds the same inputs)

#### `.github/workflows/qa-validate.yml` — qa-validate

- **when:** `pull_request`, `push`, `workflow_dispatch`
- **jobs:** `guard`, `validate` (needs `guard`), `live-smoke` (needs `guard`), `dispatch-fixbot` (needs `validate`), `auto-merge` (needs `validate`, `live-smoke`)
- **calls:** `make lint` — Fail when a tracked text file does not end with a newline, a tracked Python module raises a SyntaxWarning, or a bot leg lost its project skill; `make check-commit-authorship` — CI: fail when a commit's author/committer identity or a crediting trailer is not an allowed one (issue #317); `make pr-closure` — Fail when this PR does not close the issue its branch implements (rule 6e); `make image-ensure`; `make secret-scan`; `make secret-scan-self-test`; `make check-secret-output` — CI: fail when any file prints a secret's VALUE, passes it on a command line, xtraces it, dumps the environment around it, or commits a credential-shaped literal; `make nerve-check`; `make validate`; `make validate-search`; `make validate-mapped`; `make openspec-check` — CI gate: every active change validates, every task ticked, the index current; `make openspec-archive-check` — Fail when an ACTIVE change names a MERGED PR (rule 6f; host-side: needs gh); `make architecture-check` — Fail when ARCHITECTURE.md misses a make target, a workflow or a script — or its generated inventory is stale (rule 6h); `make test`; `make search-smoke`; `make model-caps`; `make hermes-smoke`; `make agent-shell-keys-check` — Prove every container credential is visible in the AGENT's shell (Hermes strips them; issue #359); `make validate-fetch`; `make verify-closure`

#### `.github/workflows/queued-alarm.yml` — queued-alarm

- **when:** cron `7,37 * * * *`, `workflow_dispatch`
- **jobs:** `guard`, `alarm` (needs `guard`)
- **calls:** `make queued-alarm` — Report jobs stuck in `queued` far too long, and optionally comment once per affected run (REPO=<owner/name>, MINUTES=30, COMMENT=1); `make sweep-alarm` — Fail loudly when the hourly issue sweep has not been DELIVERED (REPO=<owner/name>, MAX_AGE_HOURS=3); `make freshness-alarm` — Fail when the newest refresh snapshot is older than MAX_AGE_HOURS (issue #452)

#### `.github/workflows/refresh-bot.yml` — refresh-bot

- **when:** cron `0 6 * * *`, `43 17 * * *`, `workflow_dispatch`
- **jobs:** `guard`, `build` (needs `guard`), `test-image` (needs `guard`, `build`), `openspec-image` (needs `guard`), `search` (needs `build`), `aggregate` (needs `guard`, `build`, `search`)
- **calls:** `make rebuild-decision` — Print built/test_built/publish_openspec + tags + reasons (FORCE=<bool>, DOW=<1-7>); `make image-ensure-base`; `make _search-smoke`; `make model-caps`; `make hermes-smoke`; `make search-*`; `make engine-check`; `make base-advance` — Fetch <BASE> and fast-forward this clean checkout onto it (a job that has written nothing yet); `make image-ensure`; `make merge-fetch`; `make test`; `make engine-meta-capture` — Capture GitHub metadata for registry engines the offline test fixture lacks; `make correct-raw`; `make qa-report`; `make data-gaps`; `make data-gap-issue`; `make git-identity`; `make merge`; `make refresh-sync` — Move a refresh's generated tree onto the fetched <BASE>, keeping its raw snapshots (issue #177); `make refresh-require-tip` — Fail unless the refresh branch contains the freshly fetched <BASE> (issue #177); `make refresh-run-block`

### The product, end to end

How a model gets from an X post to a `README.md` row. Every step below is a real target and a real artifact (`make architecture-check` fails when one is gone).

| Stage | Runs | Reads | Writes | Why it is that way |
|---|---|---|---|---|
| 1. Search | make search | lightbrd.com mirror, via the Firecrawl scrape API | data/raw/<backend>-<UTC>.json | One leg per backend (`SEARCH_LEGS`: nvidia, metal, cpu, amd — `search-<backend>` runs one); every call writes its own snapshot, so a later call never overwrites an earlier one. |
| 2. Ingest | make merge | data/raw/*.json | data/models.json | `scripts/update_trending.py` folds the raw snapshots into the store (`ingest_raw_snapshots`): adds models and measurements, fills absent keys and never removes or shrinks one (rule 3b). |
| 3. Rank | make merge | data/models.json | trend_score / buzz_7d (derived fields in the store) | `recompute_7d_engagement` scores the last 7 days of real posts (`buzz`) plus the fastest in-scope measurement (`speed`), then `sort_models` orders trending → recent → stale (rule 4: engagement first, t/s as the tie-breaker). |
| 4. Render | make merge (or make render-readme for a template-only change) | data/models.json | README.md | `render_readme(store, as_of=generated_utc)` rewrites every table — most loved, pick-your-card, engine matrix, the four backend tables, the engine guide — so the README is never hand-edited. |
| 5. Snap | make merge | data/models.json | data/snapshots/trending-<UTC>.json | The full store after each merge; it is what proves no model was ever removed (`check_no_removal`) or lost a value (`check_no_value_loss`). |

### `README.md` — the sections a refresh rewrites

- Trending Local LLMs
- 🔥 Trending for your card — low end first
- ❤️ Most loved open-weight models on X (ranked by trend: 7-day buzz + speed)
- 🖥️ Pick your card — what fits your VRAM
- 🧭 Which inference engine runs what
- 🟦 CUDA — NVIDIA GPUs (8–48 GB)
- 🟪 ROCm — AMD GPUs (8–48 GB)
- 🟨 CPU — no GPU
- 🟩 Metal — Apple Silicon (unified memory)
- ⚙️ Inference engine / server guide
- How to contribute
- License

`README.md` is generated, never hand-edited (`AGENTS.md` §5b): a change goes into the store or the renderer's template, then `make merge` or `make render-readme`.

### Every script

One line each, taken from the script's own docstring.

- `scripts/agent_identity.py` — ONE definition of the repository's agent identity (issue #325).
- `scripts/agent_shell_keys_check.py` — Prove that every credential a container receives is visible in the AGENT's shell.
- `scripts/architecture_bot.py` — Keep ARCHITECTURE.md's living inventory true to the tree (issue #479, rule 6h).
- `scripts/architecture_check.py` — Keep ARCHITECTURE.md true to the repository (rule 6h, issue #178).
- `scripts/bot_markers.py` — ONE definition of every bot start/end marker — its name, its shape, its parser, its writer
- `scripts/check_agent_skills.py` — Guard the bots' Hermes project skills (issue #549).
- `scripts/check_commit_authorship.py` — commit-authorship guard — `make check-commit-authorship` (issue #317).
- `scripts/check_conflict_markers.py` — Fail when a tracked file carries a merge-conflict block (issue #588).
- `scripts/check_openspec_tasks.py` — Ensure active OpenSpec changes have ALL task checkboxes completed.
- `scripts/check_secret_output.py` — No secret VALUE may reach a log, a summary or a process list — for every key, not just one.
- `scripts/code_review.py` — A code-review bot for this repo: read the TREE and the PIPELINES, file ONE issue per finding
- `scripts/data_gap_analysis.py` — Post-refresh data-gap analysis (issue #115).
- `scripts/engine_registry.py` — Engine registry: classify + auto-register new inference engines at ingest.
- `scripts/ensure_image.py` — Prepare the runner images for THIS revision — one code path, CI and local.
- `scripts/env_int.py` — Read an integer setting from the environment — EMPTY means MISSING (issue #487).
- `scripts/file_findings.py` — File ONE GitHub issue per finding an implementation run recorded.
- `scripts/fix_loop.sh` — fix_loop.sh — the fix-bot's repair loop (runs on the CI runner / host).
- `scripts/freshness_alarm.py` — An alarm over the ARTIFACT, not over the run (issue #452).
- `scripts/hermes_skills_register.py` — Register the checkout's `.hermes/skills` with Hermes, so `hermes -s <name>` resolves (issue #549).
- `scripts/hermes_smoke.sh` — hermes_smoke.sh — prove the search alias is ROUTED and ANSWERS, in seconds.
- `scripts/hermes_update_needed.sh` — Decide whether a Hermes update should run on this invocation.
- `scripts/hf_id.py` — One definition of a Hugging Face identifier: `owner/repo`.
- `scripts/install_hermes_ci.sh` — install_hermes_ci.sh — the ONE way the Hermes CLI enters this repo's image.
- `scripts/issue_bot_working_files.txt` — (no docstring)
- `scripts/issue_queue.py` — The implementer's queue — ONE implementation, read by both bots (issue #179).
- `scripts/issue_review.py` — The issue reviewer's deterministic core (issue #179).
- `scripts/issue_thread.py` — Render an issue's WHOLE thread for the implementer (issue #210).
- `scripts/issue_verdict.py` — Apply the implementer's TRIAGE verdict (issue #210).
- `scripts/lint_linefeeds.py` — Every tracked text file ends with a newline (issue #186).
- `scripts/lint_syntax.py` — No tracked Python module raises a `SyntaxWarning` (issue #190).
- `scripts/model_caps_check.py` — Live model-catalog guard for the Hermes search/fix model.
- `scripts/nerve_key_check.py` — The nerve-plugin credential guard (issue #120).
- `scripts/openspec_archive_check.py` — An ACTIVE OpenSpec change must not name a MERGED pull request (issue #183).
- `scripts/openspec_index.py` — Generate / verify the root OpenSpec index (`OPENSPEC.md`).
- `scripts/pr_body.py` — The implementation PR body is COMPOSED by a target, never spelled in a workflow heredoc
- `scripts/pr_closure.py` — Does this PR close the issue it implements? (issue #284, AGENTS.md rule 6e)
- `scripts/pr_health.py` — Report OPEN pull requests that are SILENT — and say what to do about it (issue #442).
- `scripts/qa_report.sh` — Run the QA targets of a refresh and tell apart the two kinds of "not zero":
- `scripts/query_coverage.py` — Do the searches ask for the models we rank? (issue #264)
- `scripts/queued_run_alarm.py` — Report jobs that have been queued far too long, so a stuck runner is loud (issue #252).
- `scripts/refresh_base.py` — Publish a refresh on the base as it is NOW, never on a stale one (issue #177).
- `scripts/refresh_run_block.py` — The refresh run's WINDOW as a machine-readable block (issue #199).
- `scripts/require_env.py` — Fail LOUDLY when an environment variable a leg needs is missing or empty.
- `scripts/reset_working_files.py` — Unstage the bot's working files, from ONE list (issue #543).
- `scripts/run_tests.sh` — run_tests.sh — the ONE test runner (issues #176 and #192).
- `scripts/scrub_log.py` — Redact a captured agent log before any of it reaches a bot job's console.
- `scripts/secret_scan_self_test.py` — Prove the secret scan actually detects a credential (issue #122).
- `scripts/self_correct_raw.py` — Self-correct raw search snapshots so they conform to data/search_contract.json.
- `scripts/smoke_search.py` — Bounded reachability smoke for the four Hermes search targets.
- `scripts/sweep_alarm.py` — Fail loudly when the hourly sweep has not been DELIVERED (issue #497).
- `scripts/update_trending.py` — Update the trending-local-llms data store and regenerate README.md.
- `scripts/validate.py` — QA validation for the trending-local-llms data store + README.
- `scripts/verify_closure.py` — Did the issue a merged PR claimed to close ACTUALLY close? (issue #288)
- `scripts/worktree_base.py` — Where does work start? (issue #271, AGENTS.md rule 6n)
<!-- architecture-bot:end -->

