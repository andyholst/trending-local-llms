# An unchecked scan is not a clean scan

**Issue:** [#309](https://github.com/andyholst/trending-local-llms/issues/309) — the run-count check is still credential-gated, so a scan can still say "no findings" unrun
**Capability:** `code-review-scan` (the bot's deterministic checks)

## Why

#278 and #311 fixed the *secrets* check, but the sibling read was left with the same flaw. Measured by reading `main()` and confirmed against production (run 38876843174, where the runs read **succeeded**):

```python
if runs is None:
    print("[code-review] NOTE: the run-count check is unavailable here (the Actions API
           refused the read); run the bot with a token that can read them.", file=sys.stderr)
…
print(render(items))     # "no findings"
return 0                 # <-- GREEN
```

When the workflow/run-count read is refused, `findings()` skips `check_workflow_never_ran`
(`if runs is not None`), the scan prints `no findings`, and it exits **0**. A stderr NOTE beside
a success is not a signal: **"checked and clean" and "could not check" look identical**, which is
exactly the defect the whole family of loudness fixes exists to remove (#209's silently-SKIPping
live checks, #292/#293's quiet search, #278's skipped secrets check).

It is latent today — in production the runs read is answered, so the check does run — but a
permission change would silently reduce the bot's coverage while every run reported success.

## What Changes

- **`scripts/code_review.py`** — `main()` records a **coverage gap** when a check could not run.
  The gap is named in the scan's own output (`UNCHECKED: 1 check(s) did NOT run this scan — …`)
  and the scan **exits non-zero**, so an unchecked scan can never be mistaken for a clean one.
  `--static-only` is exempt **by design**: it does not ask for the API checks at all, which is a
  different thing from asking and being refused, so it still exits 0.
- **`tests/test_code_review.py`** — three tests, in `main()`:
  - a refused runs read **fails** the scan, names the check and denies the clean bill of health
    (RED on master: exit 0, no mention);
  - a fully-run scan **stays green** and does not claim an unchecked check (the gate must not
    fire on a healthy run, or it becomes noise the operator learns to ignore);
  - `--static-only` exits 0, because it never asked.

## Not covered

- **The `AGENTS.md` §8 row** (rule 6c) remains owed for `tests/test_code_review.py` and is already
  tracked by #310; `AGENTS.md` is a protected rule file whose write approval has not returned.
  This change adds no new row obligation beyond it.
- **Making the check credential-free** (the issue's other option) is not attempted: "has this
  workflow ever run?" cannot be answered from the tree, so the honest fix is that an unanswerable
  check is loud rather than silent. If a credential-free substitute is wanted, that is a new
  decision and its own change.
- **#231** (a `workflow_dispatch`-only pipeline can ship broken because PR CI never executes it)
  is the reason a red weekly run is the *only* signal this bot has — and remains open.
