# Proposal: timeout-prong-neutral-failed-1707

Issue: #1707

## Why

`zero_hit_verdict` has two outage prongs that classify the same unreachable-mirror shape in opposite directions. The error-page prong accepts a neutral `failed` query beside a proven outage (issue #296). The timeout prong instead requires `timeouts + outage == queries`, so `34 × read timeout + 1 × Connection refused` (queries=35, failed=35, timeouts=34) is reported as a QUIET SEARCH (exit 1) and reds `live-smoke` on every open PR, while the same shape expressed as error pages is an out-of-scope outage (exit 0). A `failed` query proves nothing about the mirror either way; it must not condemn a transport outage.

## What Changes

- In `scripts/update_trending.py::zero_hit_verdict`, replace the timeout prong's `(timeouts + outage == queries)` discriminator with the SAME discriminator the error-page prong uses: at least one recognised transport failure, no answered query, no hit, no refusal. Non-timeout `failed` queries are then neutral — they neither excuse nor condemn the outage, and are still reported in the verdict lines.
- Add RED-first guards in `tests/test_firecrawl_fetch.py` pairing the timeout shape against the error-page shape, and a parity guard that keeps the two prongs on one discriminator. The existing partial-timeout and single-gateway-error guards stay green.

## Impact

No data format, contract, image, workflow or rulebook change. Only the classification of the all-transport-failure boundary moves: a mirror that answered no query and produced no hit and no refusal keeps the non-blocking `outage`/exit-0 verdict regardless of whether the transport failures were timeouts, gateway errors, or a mix with unclassifiable `failed` queries. A partial outage (any answered query) stays `quiet`/exit-1.

## Not covered

- No change to the refused/quiet verdicts, to `is_upstream_timeout`'s token set, to `gather_x`'s counters, or to `live-smoke`'s majority rule.
- No CI dispatch, no merge, no master push, no collaborator grant.
