---
name: data-search
description: Use when a trending-local-llms refresh leg must scrape X posts for one backend from the lightbrd.com mirror and write per-query raw snapshots — never a bulk payload, never a fabricated figure.
version: 1.0.0
author: Asimov Agent
license: CC-BY-4.0
metadata:
  hermes:
    tags: [trending-local-llms, refresh, search, firecrawl, lightbrd]
---

# One backend's refresh search

This is the leg that turns X posts into `data/raw/<backend>-<UTC>.json`. Four legs run in
parallel (`nvidia`, `metal`, `cpu`, `amd`); each is given its own keyword list and writes only its
own snapshots.

## Inputs

- **The prompt's parameters**, which this run carries: the `backend` name, the backend's keyword
  list, the trending-model queries, the engine rules (`$(ENGINE_ASK)`), the footprint rules
  (`$(DIM_ASK)`) and the exact `--write-raw` command to run.
- **`AGENTS.md`** — the repository's rules, especially §3 (data source), §3d (no credential in a
  log) and §2.3b (additive only).
- **`skills/gather-data.md`** — the exact scrape technique and query shapes.

## Output

- **One raw snapshot per query**, written immediately after that query:
  `python3 scripts/update_trending.py --write-raw <backend> < payload.json`. Each call writes its
  own `data/raw/<backend>-<UTC>.json` (same-second writes get `-2`, `-3`).
- Nothing else. Do not touch `data/models.json`, do not regenerate the README, do not commit, do
  not push, do not merge — the aggregate stage does that.

## Rules

- **The mirror is lightbrd.com and nothing else.** `POST https://api.firecrawl.dev/v1/scrape` with
  the `Authorization: Bearer` header carrying the value of `FIRECRAWL_API_KEY`, which you read
  from the environment **by name**; the body is
  `{"url":"https://lightbrd.com/search?f=tweets&q=<urlencoded>","formats":["markdown"]}`.
- **Make that call from the TERMINAL tool — never from `execute_code`.** The terminal child is the
  only one that receives the credential (issue #359); Hermes scrubs every secret-named variable from
  an `execute_code` child, `_HERMES_FORCE_` included, so the header is empty there and the call
  returns `401` (issue #362). `web_extract` / `web_search` cannot send the key either. The only
  supported Python route is the snapshot write, `python3 scripts/update_trending.py --write-raw
  <backend>`, which reads the key in-process.
- **One query at a time.** Scrape a query, extract its models, write that snapshot, then move on.
  Never collect every query into one payload: a reply is capped at 65,536 tokens and a bulk
  payload loses the whole leg.
- **Last three days, ranked by interactions then t/s.** Record the engine, the model, the
  hardware, the quant and the figure.
- **`tps` is a clean number.** No embedded text or comments — context like `DFlash spec-decode`
  belongs in `quant`/`hardware`. Generation/decode t/s only, never prompt-processing or prefill.
- **`source_post` is the post itself** — `https://lightbrd.com/<user>/status/<id>`, never the bare
  mirror URL or a profile page — and that post's likes, comments, reshares and views go on the
  same measurement as integers.
- **Never fabricate.** A figure must trace to a post you actually read; if it cannot, leave the
  key unset and say so. Never write a snapshot that no real scrape backs.
- **Never remove a model.** Additive only, in the snapshots as in the store.
- **Never print the key, in any spelling**, and never write it into a file, a snapshot or a
  summary — AGENTS.md rule 3d: a value found in a log is rotated, not excused.
