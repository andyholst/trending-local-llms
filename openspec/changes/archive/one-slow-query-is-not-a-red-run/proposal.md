# One slow query is not a red run

**Issue:** [#258](https://github.com/andyholst/trending-local-llms/issues/258) — one slow lightbrd query reds the whole refresh-bot run, though the refresh completed
**Capability:** `search-smoke` (the bounded reachability probe the refresh legs and `live-smoke` run)

## Why

The probe sampled four queries per leg on a 3 s budget, counted **every** miss globally, and exited **2 on the first one**. Measured on scheduled run
[38723723638](https://github.com/andyholst/trending-local-llms/actions/runs/38723723638):

```
guard: success          build: success           search (nvidia): success
openspec-image: success test-image: success      search (cpu):    FAILURE
                                                 search (metal):  success
                                                 search (amd):    success
aggregate: success
```

`search (cpu)` answered **three of four** queries; the fourth was slow on **both** attempts. `aggregate` — which holds the actual work — ran anyway and
succeeded. The run was FAILURE regardless, on a per-query **3 s** budget.

**Why it matters:** `search (cpu)` failing is indistinguishable, to whoever reads the notification, from the mirror being down or the probe being broken. The
maintainer either chases a phantom or stops reading the signal — and a red scheduled run is the *only* thing that draws attention to a genuinely dead source.
It is also self-inflicted noise at two runs a day, which is the shape of a flake.

The probe is a pre-flight **reachability** check, not a completeness check: it samples.

## What Changes

- **`scripts/smoke_search.py`** — `leg_verdict(total, missed)` is the ONE decision function, and the verdict is **per leg**:
  - a **majority** of a leg's queries missing the budget **blocks** the run (an unreachable mirror misses all of them, so it still fails loudly);
  - a **minority** missing does **not** block: the leg passes and the summary says so (`SAMPLED: cpu: 1/4 queries sampled slower than the budget (the rest
    answered, so the mirror is reachable)`), so the distinction is visible **in the run**;
  - a clean leg says nothing, and the "all backends returned HTTP 200" line is no longer printed for a leg that sampled slow (it would be untrue).
  `main()` gains a `probe_fn` seam (default: the real `probe`) so the whole leg can be driven offline — the leg verdict, the summary lines and the exit code
  under test are all production code.
- **`tests/test_smoke_search.py`** — two tests, registered in `main()`:
  - `test_one_slow_query_does_not_red_a_leg` — 1 of 4 does not block (with the note); 4/4, 3/4, 2/3, 3/5, 1/1 DO block; a clean leg is silent; an exact half is
    not a majority.
  - `test_the_run_summary_distinguishes_a_flake_from_a_dead_source` — drives the REAL `main()` over one leg: one slow query → exit 0 + `SAMPLED` + the ratio +
    no "all backends returned HTTP 200"; all slow → exit 2 and "MAJORITY … not a flake".

## Not covered

- **The 3 s budget itself.** The issue offers "scale the probe to what the run needs" *or* "carry the distinction in the status"; this takes the second, which
  is the honest one — a reachability probe *should* sample, and the budget is a separate knob.
- **`_search-smoke` remains the single implementation** (the issue's fourth criterion): no second, differently-implemented reachability path was added — the
  seam is a parameter of the same `main()`, and `probe` is still the only probe.
- **The test file.** The issue names `tests/test_search_budget.py`; the probe's own suite is `tests/test_smoke_search.py` (that is where `probe`, its retry
  policy and its `OUTAGE` label are already locked), so the decision function's tests live there rather than in a second place. Reading the criteria, not the
  filename, is what they ask for — and rule 6d prefers one home.
