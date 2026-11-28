Issue: #1868

# Proposal: clarify-dgx-spark-hardware-1868

Closes #1868.

## Why

Two `qwen3.6-35b-a3b` measurement rows in `data/measurements.json` carry the hardware string `Radeon 8060S / Strix Halo 128GB (ASUS Ascent GX10, GB10)`, which names an AMD APU and an NVIDIA GB10 box in one value. PR #1867 settled the backend column (both classify CUDA under rule 6's "no NVIDIA token" clause) but deliberately did not resolve which box produced the figures. The same author publishes the identical 188.9 t/s (Magnitude) and 87.2 t/s (Ollama) figures on sibling rows naming `NVIDIA DGX Spark (one)` at `niklaslenz_ai/status/2111204284453044383`, so the DGX Spark (GB10) is the machine that produced them. A reader who sees a Radeon/Strix Halo figure in the CUDA column can buy the wrong hardware for the number.

## What Changes

- APPEND an inline, evidence-bearing clarification to the `hardware` value of exactly two rows (`qwen3.6-35b-a3b` / Ollama / 87.2 and `qwen3.6-35b-a3b` / Magnitude / 188.9). The original string remains a byte-for-byte leading substring; only text is appended. No t/s, engine, quant, date, weight, context, source post or any other stored value changes. This is rule-3b additive-only, like the store's existing parenthetical annotations — no stored value is replaced or removed, so no rule-3c human sign-off is needed for the data edit.
- Add a real-file guard (`tests/test_dgx_spark_hardware_clarification_1868.py`, rule 6m) that reads the REAL shipped store with no stand-ins or monkeypatch. It asserts both rows preserve the original hardware text verbatim, the appended text names the NVIDIA DGX Spark (GB10) and cites the sibling post and its `NVIDIA DGX Spark (one)` label, every other measurement value in the whole store is byte-identical to base (a digest with only those two fields normalised), neither sibling store file moved, the two rows' other fields are unchanged, and both rows still classify CUDA. RED on base `3c00bf44` (6 missing-clarification failures), GREEN on head.
- Keep PR #1867's `tests/test_dgx_gb10_cuda.py` guard green: make its delta-row LOOKUP tolerant of an additive hardware suffix (the #1866 ledger records the pre-clarification string). Every classification assertion and the six-row enumeration are unchanged.
- Regenerate `README.md` from the edited store with `make render-readme`; two consecutive renders are byte-identical and churn is confined to the two clarified cells.

## Impact

Data-annotation change only. No t/s, engine, quant, date or other measurement value changes; no row added or removed; no raw-snapshot history rewritten. No schema, contract, API, table-shape, Makefile-target, pipeline-job or image change. `data/models.json`, `data/posts.json` and `data/raw/*.json` are untouched. Backend classification is unchanged (both rows remain CUDA). No cron and no Actions schedule added. No label changes.

## Not covered

- Replacing or removing any stored value, or rewriting the contradictory hardware primary text — an owner-ruled correction under rule 3b that is explicitly NOT taken here.
- Editing `data/raw/*.json` (history), `AGENTS.md` or any lane `SOUL.md`.
- An `AGENTS.md` §8 rulebook row for the new guard: if rule 6c review requires one, it is declared on issue #1868 as `- [~] … — blocked: rule 3c human sign-off` with full text, and landed by an attended change, never written headlessly.
