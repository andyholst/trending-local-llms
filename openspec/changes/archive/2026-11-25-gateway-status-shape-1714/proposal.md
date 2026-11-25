# Proposal: gateway-status-shape-1714

Issue: #1714
PR: #1717

## Why

`scripts/update_trending.py::is_upstream_timeout` classifies a transport failure by bare substring tokens, including the digit sequences `"522"`, `"504"`, `"502"` and `"503"`. Since #1707 made `timeouts > 0` the sole discriminator of the transport outage prong in `zero_hit_verdict`, any all-failed run whose reason text merely contains one of those digit sequences is excused as a non-blocking `outage` (exit 0). `live-smoke` gates `auto-merge`, so a false-positive classification removes that gate for a genuine query-set regression: `RuntimeError("parsed 502 bytes from the page")` currently classifies as a gateway timeout.

## What Changes

- Replace the bare digit tokens in `is_upstream_timeout` with an HTTP status SHAPE matcher: `HTTP Error 502`, `HTTP 522`, `statusCode: 502`, `502 Bad Gateway`, `502 Server Error`. The measured run-45526182085 shape (`34 × read timeout + HTTP Error 502: Bad Gateway`) stays recognised; an incidental digit sequence in prose does not.
- Add a RED-first guard in `tests/test_firecrawl_fetch.py` proving an incidental `502`/`503`/`504`/`522` is not a timeout, that the real HTTP shapes still are, and that a run whose only gateway-looking digits are incidental stays `quiet`/exit 1.
- Keep the existing timeout family guards (read timeout, gateway error wording, `#1699` mixed shape) green.

## Impact

No data format, contract, image, workflow, schedule or rulebook change. Only the transport-failure classifier narrows: a reason string with an incidental status number no longer excuses a quiet search. Genuine gateway status wording still counts, so a real unreachable mirror keeps the non-blocking `outage` verdict. The docstring of `is_upstream_timeout` is updated, so the generated `ARCHITECTURE.md` §10 inventory is regenerated in this change.

## Not covered

- No change to `zero_hit_verdict`'s discriminator, the refused/quiet verdicts, `gather_x`'s counters, or `live-smoke`'s majority rule.
- No CI dispatch, no merge, no master push, no collaborator grant.
