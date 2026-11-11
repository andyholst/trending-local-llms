# Proposal: ingest-names-a-dead-hf-link

Issue: #333

## Why

PR #330 added `muse-spark-open` with `hf: "meta-models/Muse-Spark-Open"`. The real
repository is `meta-models/Muse-Spark-Open-816B-A42B` — the size/active-parameter
suffix had been dropped from a post that named the model in prose. `make validate`
caught it, as designed:

```
FAIL: link: [model-hf] muse-spark-open: https://huggingface.co/meta-models/Muse-Spark-Open does not resolve
FAIL: link: [format-hf] …
FAIL: link: [raw-hf] metal-20261017-102009.json/muse-spark-open: …
```

But that is the **first** moment anyone sees it — after the refresh has already
opened a PR, whose only repairer is a bot round (and, on that run, a bot round
that could not start, #331). Nothing between "the search agent wrote an
`owner/repo`" and "CI HEAD/GETs every link" checks the id, so one guessed id is
the whole cost of a red refresh.

## What Changes

- **`scripts/update_trending.py` — `hf_repo_resolves(repo_id)`.** `True` when the
  HF API answers, `False` only on a **definitive** 401/404, `None` when the check
  cannot tell (no id, transport error, 403/429/5xx). A rate-limited or briefly
  down API must never be reported as a bad link — the point is to name a guessed
  id, not to add a flaky failure.
- **`note_unresolved_hf(model)`** — one loud line naming the id and the model,
  for a death-case `hf` and any distinct `format-hf`: `[ingest] HF hf
  'meta-models/Muse-Spark-Open' does NOT resolve (muse-spark-open) — the link
  check will fail this PR`.
- **`ingest_raw_snapshots(..., verify_hf=False)`** — the check runs only for
  models **added** this merge (an update costs no request), and only when
  `verify_hf` is on. `main()` passes `verify_hf=True`, so the production merge
  does it; the default keeps every existing ingest test hermetic (no network).
- **`HF_MODEL_API`** — the endpoint seam (tests point it at a real local HTTP
  server), modelled on `FIRECRAWL_SCRAPE_URL`.
- **`tests/test_ingest_hf_verify.py`** (new) — a real local HF stand-in: 200/404/401/429/500
  classification, the loud line for a dead new model and silence for a good one,
  no request for an existing model, and no request at all under the default.

## Impact

`scripts/update_trending.py`, `tests/test_ingest_hf_verify.py` (new), `Makefile`
(the `_test` chain), `ARCHITECTURE.md` (the script's row), the OpenSpec change +
`OPENSPEC.md`. No `data/**` change — this adds no value to the store, only a
report in the run that produced it.

Deliberately **report-only**: a guessed id costs a fix round, not a blocked
refresh, which matches how the pipeline already treats a data-quality finding
(`qa-report` reports, the PR still lands, fix-bot repairs). Failing the merge
would let one bad id — or one HF outage — stop a refresh that is otherwise fine.

## Not covered

- **Repairing the id.** The issue asks for visibility, and a repair must be
  verified, not guessed (AGENTS.md §6b link-repair rules). fix-bot already owns
  that, and now can actually run (#332).
- **Verifying every link, not just `hf`.** `source_post` and engine repos are
  also HEAD/GET-checked by `check_links_resolve`; doing them at ingest would be a
  request per measurement, which is not what this change is about.
- **Blocking on a dead id.** See above — report-only by design.
