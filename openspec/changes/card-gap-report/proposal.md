# Proposal: card-gap-report

Issue: #342 — `tech-debt: Only EMPTY tiers are reported as collection gaps — a model with no card evidence at all is silent`

## Why

The card-fit tables place a model only where there is **evidence** (`fits_tier`), so a model
with none is simply absent. The coverage line added with #337 reported models *per tier* and
measurements carrying a footprint, but never named the models that place nowhere — so
"we never measured this on a card" was indistinguishable from "no card can run it", except by
silence.

Measured on the store while fixing this: **25 of 50 models have no card-tier row** — 19
because every figure is Metal or CPU (not a gap at all: those models live in the Metal/CPU
tables), and **6 with a real CUDA/ROCm figure that places nowhere** (`Muse Spark Open`,
`Bonsai 2 4B`, `Qwen3-235B-A22B`, `Qwen3-4B`, `Ornith 1.5`, `GLM-5.2`) — which is exactly the
set a search can close.

## What Changes

- **`update_trending.card_gap_reason(m, registry)`** — ONE definition of "why this model has
  no card row": `None` when it places, `"unified memory / CPU-only"` when every measurement
  is Metal/CPU, `"no card figure collected"` otherwise (a datacenter part, a card above every
  tier, or a run whose hardware names no card).
- **`validate.check_card_gap_report`** (REPORT ONLY, `readme` stage) — prints the count, the
  split by reason, and **names up to 12 models of the actionable kind**; it never fails, and
  an empty or measurement-less store reports instead of raising.
- **`tests/test_card_gap_report.py`** — the two reasons told apart on a fixture (placed /
  Apple Silicon / CPU-only / datacenter / above-tier), the report naming only the actionable
  models, degenerate stores, the real store's own report, and the wiring.

Verified RED against the pre-change tree (both symbols missing → the guard fails naming them)
and GREEN after (`PASSED 17 | FAILED 0`).

## Impact

`scripts/update_trending.py` (one helper), `scripts/validate.py` (one report-only check +
registration), a new test module, this OpenSpec change and the regenerated `OPENSPEC.md`. No
new make target, stage, job or image — `ARCHITECTURE.md` unchanged (rule 6h). `README.md` is
untouched: this is diagnosis, not a table.

## Not covered

- **Collecting the missing figures.** The six named models are a search target; closing them
  is data work (the `QUERY_TOP_N` derivations of rule 6o and a refresh), not this change.
- **Promoting the report to a gate.** A minimum card coverage would fail every refresh for
  models that legitimately cannot place; the report is the honest signal until the searches
  lift the number.
