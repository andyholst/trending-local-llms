# Proposal: gateway-error-outage-class

Issue: #1699
PR: #1705

## Why

A live search that reaches the lightbrd mirror and gets a TRANSPORT-level gateway error from it is
indistinguishable, in `zero_hit_verdict`, from a query the pipeline could not classify at all — so
one such error breaks the "every query timed out" arithmetic and a genuinely unreachable mirror is
reported as a query-set problem.

Measured on master: run 45526182085 (push, head `151321c3`) had 34 timeouts plus ONE
`HTTP Error 502: Bad Gateway`. `is_upstream_timeout` recognised only `timed out`/`timeout`/`522`/
`504`/`gateway timeout`, so `timeouts=34 != 35` and the total-outage prong did not fire: `live-smoke`
answered `[error] ... a QUIET SEARCH on a reachable mirror` and FAILED, blocking every open PR's
auto-merge. Six minutes later run 45526708331 (PR #1692) had 35/35 plain timeouts under the SAME code
and printed `[outage] the lightbrd mirror is UNREACHABLE` — identical failure shape, opposite
verdicts (issue #1699).

## What Changes

- **`scripts/update_trending.py`** — `is_upstream_timeout` recognises the gateway-error class of
  transport failure: `502`, `503`, `bad gateway`, `service unavailable`, `gateway error`. The
  verdict arithmetic in `zero_hit_verdict` is untouched.
- **`tests/test_firecrawl_fetch.py`** — the module that owns the fetch client and the verdict gains
  RED-first guards: the recorded shape (34 timeouts + one `HTTP 502`) verdicts `outage`/exit 0, and
  a single genuinely answered query still verdicts `quiet`/exit 1.
- **`ARCHITECTURE.md`** §6 row for `scripts/update_trending.py` names the widened token set.

## Impact

Additive only. `is_upstream_timeout` is consulted in exactly one place — the generic `except` branch
of the per-query fetch loop in `gather_x` — and only WIDENS what counts as a transport failure. A
query that returned a real page (`with_hits`), a Firecrawl refusal, and a partial outage are
unchanged; the partial-outage and refusal prongs still win first. No data, contract, workflow,
Makefile or README change.

## Not covered

- The `zero_hit_verdict` arithmetic itself. It is already correct once the classification is right;
  re-deriving it would weaken the deliberate `failed`-does-not-unmask rule (#296).
- The target's own 5xx ERROR PAGE (`metadata.statusCode >= 500` / Cloudflare's `Error code 5NN`),
  which `fetch_lightbrd` already raises as `UpstreamOutage` and which this change does not touch.
- Other transport failures outside the gateway family (`Connection refused`, DNS): they stay
  `failed`, deliberately — they prove nothing about the mirror either way (#296).
