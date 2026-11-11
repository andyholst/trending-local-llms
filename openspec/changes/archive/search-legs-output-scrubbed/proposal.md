# The public agent targets redact their own stream — the search legs and the fix loop included

**Issue:** [#355](https://github.com/andyholst/trending-local-llms/issues/355)
**Capability:** `bot-agent-run-safety` (the same capability as the merged #351 change)

## Why

#351's code merged as PR #352 and its rule as PR #354, but two legs were left printing the agent's
stream raw — and one of them had already printed a credential-shaped string:

```
38902898149  search (nvidia)  export FIRECRAWL_API_KEY=<key>
38959544994  search (metal)   1. Export it in the shell I'm using — `export FIRECRAWL_API_KEY=fc-xxx`
39063620912  search (amd)     … add FIRECRAWL_API_KEY=<key>
39024041477  search (nvidia)  export FIRECRAWL_API_KEY=fc-xxx   # or fill line 200 of /root/.hermes/.env
```

Those are the agent's own PROSE, written while explaining how to supply the key after Firecrawl auth
failed; the matched strings were `<key>`, `…`, `fc-xxx` — longest 7 characters, where a live key is
30+. **Nothing leaked that time.** The shape is one paste from a real value in a public log, and the
prompt those legs run tells the agent to build a `Authorization: Bearer <FIRECRAWL_API_KEY>` header
from the key in its environment — so the paste is exactly what a future run might do.

Two structural escapes kept the merged guard blind to them:

1. `refresh-bot.yml:299` is `run: make search-${{ matrix.backend }}` — the MATRIX form, which the
   guard's literal target list never matched.
2. `scripts/fix_loop.sh:76-82` runs `"$MAKE" fix 2>&1 | tee "$log"` — a `make` call made from inside
   a tracked shell script, which the guard's workflow-`run:`-block rule never reads.

## What Changes

**The redaction moves into the Makefile's PUBLIC targets** — the one seam every caller shares:

- `Makefile` gains `HERMES_LOG` / `HERMES_LOG_SCRUBBED` / `HERMES_LOG_TAIL` and ONE
  `define scrubbed_run`: run the command into `$(HERMES_LOG)`, print only
  `python3 scripts/scrub_log.py … --tail $(HERMES_LOG_TAIL)`, then `exit` with the command's own
  status. Applied to `search-nvidia`, `search-metal`, `search-cpu`, `search-amd`, `search` and
  `fix` — so a workflow step, `fix_loop.sh` and a human all get it by calling `make`, and a new leg
  cannot forget it.
- `scripts/check_secret_output.py` — the rule becomes about the TARGET, not the caller:
  - `agent-target-does-not-scrub`: every target in `AGENT_TARGETS_TO_SCRUB` must redact in its own
    recipe.
  - `scrub-seam-does-not-redact`: the seam must still call `scripts/scrub_log.py`, or one edited
    function would silently un-cover every target that trusts it.
  - `agent-stream-printed-raw` no longer fires for a self-scrubbing target, and now also matches the
    dynamic form (`make search-${{ … }}`, `make search-$…`) — covered when every leg self-scrubs.
- `.gitignore` — the captured log and its redacted copy.
- Tests: the shipped targets scrub (real Makefile); a target that lost the seam is refused; a
  gutted seam is refused; the matrix step is covered / re-opened; and the REAL seam driven through
  `make` against a command that prints the value — the console shows the mask, and a failing command
  keeps its status.
- `AGENTS.md` §3d/§8, `ARCHITECTURE.md`, `OPENSPEC.md`.

## Impact

`make search-<backend>`, `make search` and `make fix` print a bounded, redacted tail instead of the
agent's whole conversation; their exit statuses are unchanged (a red leg stays red). Six new guard
conditions, all falsified on fixtures. No data, README or contract change.

## Not covered

- `make hermes-smoke` — a bounded routing probe whose reply is the point; the exemption is stated in
  the guard's comment and `AGENTS.md`.
- `implement-issue` / `review-issue*` keep their workflow-step capture + redaction (PR #352): each
  target has exactly ONE owner of its stream, so the seam is not applied twice.
