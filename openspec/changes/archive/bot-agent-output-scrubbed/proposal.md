# A bot's agent run is non-interactive, and its console output is redacted before it is printed

**Issue:** [#351](https://github.com/andyholst/trending-local-llms/issues/351)
**Capability:** `bot-agent-run-safety`

## Why

The implementer's agent run stopped on an input prompt and **detached**, then the run
reported a red job whose only diagnosis was "no implementation":

```
23:40:48  hermes -z "Load AGENTS.md for rules. …" -m nous-deepseek --reasoning low --yolo
23:51:09  Input required; detached without cancelling. Resume this session interactively.
23:51:09  make: *** [Makefile:786: _implement-issue] Error 3
23:51:10  make: *** [Makefile:798: implement-issue] Error 2
23:51:11  ##[error]issue-bot produced no implementation for #347 (make implement-issue rc=2)
```

Measured once, on run [39079759124](https://github.com/andyholst/trending-local-llms/actions/runs/39079759124):
**10 min 21 s** of agent work, an `issue-bot-start` marker and an outcome comment on #347,
and no branch and no PR. The reason (which prompt, which tool, which decision asked for
input) is nowhere in the log — the same shape as #346, one level up: there the *shell*
died and skipped every later step, here the *agent* dies and the pipeline can only say
it produced nothing.

Two separate defects, one run:

1. **`--yolo` is not a blank cheque.** `hermes --help` (measured, pinned CLI
   `v0.22.1+104`): `--yolo` is *"Bypass all dangerous command approval prompts"*, and
   `--accept-hooks` — *"Auto-approve any unseen shell hooks"* — is a **separate flag that
   NO recipe in this repo passes** (`Makefile:359,364,369,374,421,786,901,918` all end
   `--yolo` only). Any approval channel outside "dangerous command" stops a `-z` run, and
   the stop is a detach that names nothing.
2. **The agent's stdout IS the job's console log.** `make implement-issue` writes the
   agent's whole stream straight into the step log. GitHub masks the secret values it
   *registers*; a transformed one (base64, a URL fragment, a slice) sails past — rule
   3d's whole point, and the class #346 opened. Today nothing in the tree proves a bot's
   agent output carries no credential VALUE, and nothing bounds how much of it is
   printed.

## What Changes

- **`Makefile`** — ONE non-interactive flag set, so a recipe cannot carry half of it:
  ```make
  HERMES_NONINTERACTIVE := --yolo --accept-hooks
  ```
  every `hermes -z` recipe's continuation line ends `$(HERMES_NONINTERACTIVE)`.
- **`scripts/scrub_log.py`** (new) — redact before anything reaches the console: read the
  secret VALUES from the environment **by name only**, replace every occurrence (raw,
  URL-encoded, base64) with `***`, redact token *shapes* (`ghp_…`, `github_pat_…`, `sk-…`,
  `Bearer <token>`), write the redacted full log to a file, and print at most the last
  `--tail N` lines. Nothing is ever printed unredacted; a missing log is loud.
- **`.github/workflows/issue-bot.yml`** — the implement step captures the agent's output
  to a gitignored file instead of the step log, then prints ONLY `make scrub-log`'s
  bounded, redacted tail; the uploaded QA artifact is the REDACTED log. The `rc` handling
  and the loud failure stay exactly as they are.
- **`scripts/check_secret_output.py`** — three new rules (issues #346/#351):
  - `raw-agent-log-captured`: a `run:` block that redirects a stream into a log file MUST call the
    redactor in the same block (capture alone is one edit from printing it).
  - `raw-agent-log-printed`: no step may print a captured log (`cat`/`head`/`tail`/`grep` …).
  - `agent-stream-printed-raw`: a `run:` block that executes an agent target
    (`implement-issue`, `review-issue`, `review-issue-window`, `search-*`) with its stream going
    straight to the console is refused — this is the rule the reviewer's two paths violated.
  - plus a Python rule: a script that reads a key value out of the environment
    (`os.environ[...]` / `os.getenv(...)`) and prints it — or a slice of it — is refused, since no
    shell-shaped rule can see `print(key)`. Presence-only forms (`bool(x)`, `len(x)`, `is None`,
    `not x`, `x ==`) are not findings.
- **`.github/workflows/issue-review-bot.yml`** — the reviewer's two agent paths (`body` and
  `window`) take the same capture + redact shape.
- **`tests/test_scrub_log.py`** (new) — the redactor driven with a REAL environment value and a log
  carrying it raw, URL-encoded, base64 and as a token shape (none may survive); the tail cap; the
  redacted out-file; the loud missing file; the empty log; a too-short value not shredding the log;
  and the SHIPPED implement step executed end to end against a stub `make` whose agent stream leaks
  in three spellings — nothing may reach the step's console output.
- **`tests/test_hermes_prompts.py`** — every `hermes -z` recipe must pass the whole
  non-interactive set, and the variable must really carry both flags.
- **`tests/test_workflows.py`** — the implement step captures + scrubs, prints the scrubbed
  tail, and uploads the redacted log — never the raw one.
- **`AGENTS.md`** (§3d bullet, §8 rows) and **`ARCHITECTURE.md`** (the new targets),
  `OPENSPEC.md` index.

## Impact

An implementer run reaches `Commit + push` → `Open the PR` → outcome comment instead of
detaching on an input prompt, and no secret VALUE can reach a bot job's console log
through the agent's stream — the console shows a bounded, redacted tail. The guard is a
new **exit condition** on `make check-secret-output` (the first steps of qa-validate's
`validate` job), verified to go red on the pre-change tree. No data, no README, no
contract, no schema.

## Not covered

- **Why** the input was requested (which tool/prompt) is not reproduced here: the pinned
  CLI does not name it in the log. This change makes the run proceed non-interactively
  and makes the failure visible; attributing a future request to a specific tool stays
  with the CLI.
- **#344** (the reviewer's pick parsing) and **#345** (a hand-filed `tech-debt` issue gets
  a green no-op) — the other two bot defects, their own changes.
- The `refresh-bot`, `fix-bot` and `issue-review-bot` agent streams are not captured +
  scrubbed here (they are mechanical or read-only legs); the guard rule makes the same
  capture safe when it lands, and `$(HERMES_NONINTERACTIVE)` applies to all of them at
  once.
- No behaviour change to what a verdict MEANS, and no change to the `rc` contract: a run
  that produced no implementation is still RED.
