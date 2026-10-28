#!/usr/bin/env python3
"""Post-refresh data-gap analysis (issue #115).

Every refresh acquires new data and merges it into `data/models.json`. This
stage asks the question the merge cannot: **what does the store still not
capture** — and files it as a GitHub issue, so the missing dimension is a
tracked work item instead of a paragraph in a PR body.

The flagship gap is memory that is not VRAM. The store records `vram_tier` /
`vram_min` and nothing else, while
  * the CPU and Metal tables are RAM-bound (Apple Silicon is unified memory —
    "VRAM" and system RAM are one pool),
  * llama.cpp partial offload keeps the un-offloaded layers + the KV cache in
    system RAM for every "8-48 GB GPU" entry,
  * MoE offload (Strata) splits experts across GPU / RAM / SSD,
and `skills/gather-data.md` already asks the search agent for "VRAM / RAM" — a
figure the contract (`additionalProperties: false`) prunes silently, which is
why it survives only as free text inside `quant` / `why` / notes.

  data_gap_analysis.py                  # report to stdout
  data_gap_analysis.py --out report.md
  data_gap_analysis.py --baseline FILE  # set the baseline path (default data/gap_baseline.json)
  data_gap_analysis.py --issue          # file ONE issue when the signature changed
  data_gap_analysis.py --write-baseline # record the signature as the baseline, filing nothing
  data_gap_analysis.py --check          # exit 1 when the gap set changed (CI-visible)

The baseline is written on TWO paths: `--issue` records it when it files (so a
day with the same gap set files nothing), and `--write-baseline` records it
WITHOUT filing — the repair for a baseline write lost to a rebase or a refresh
PR closed before it merged, reachable as `make data-gap-baseline`.

Report only by default: it never fails the data PR. Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The refresh run's window block (issue #199) — the ONE composer this and the aggregate
# PR step both use, so an issue filed BY a refresh carries the same block as the PR.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import refresh_run_block  # noqa: E402
# The ONE raw-row -> store-model resolver (rule 6d): the classification below maps
# each captured row to the store id ingest would give it, so it can never disagree
# with the merge about which model a post belongs to.
import update_trending  # noqa: E402
DATA = Path(os.environ.get("TRENDING_DATA_DIR", str(ROOT / "data")))
STORE = DATA / "models.json"
CONTRACT = DATA / "model_contract.json"
SEARCH_CONTRACT = DATA / "search_contract.json"
RAW_DIR = DATA / "raw"
DEFAULT_BASELINE = DATA / "gap_baseline.json"
LABEL = "data-gap-analysis"
LABEL_COLOR = "5319e7"
LABEL_DESCRIPTION = "Post-refresh data-gap analysis (missing requirement dimensions in the store)"

# Requirement dimensions the index SHOULD carry. `key` is the structured key the
# contract must declare for the dimension to be representable at all; `text` is
# how the figure shows up today when it is only prose (measured on the store).

# A capacity that is QUALIFIED as MEMORY is not a weight footprint: `16GB on VRAM`,
# `60GB RAM`, `256GB unified memory` name the machine, not the weights. #213 fixed
# the BARE capacity; this piece closes the same claim when a weights word happens to
# sit nearby — `"MXFP4-engram GGUF, 32K context at fp16, 16GB on VRAM"` put `GGUF`
# within 24 characters of a card's VRAM and was reported as a weights figure (#456).
_WEIGHT_CAPACITY = (r"\d[\d,]*(?:\.\d+)?\s*(?:gb|mb)\b"
                    r"(?!\s*(?:on\s+)?(?:vram|ram|system\s+ram|unified|ddr\d|gddr\d))")

# A context window is a FIGURE the number MODIFIES, never the topic word:
# `80k context`, `256K ctx.`, `262,144-token context`, `context window 131072` and
# `64K kv cache` state one; `context lookup`, `kv-cache q4_0` and a `25K-token
# document reproduction` do not, and `30 tok/s` is throughput. The old pattern
# matched ANY `context`/`kv-cache` word or a bare `NN k`, which reported four models
# as stating a window in prose that is not there (#456).
_CTX_TEXT = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?\s*(?:[km])?\s*[- ]?(?:tokens?\s+)?(?:context(?:\s+window)?|ctx|kv[- ]?cache)\b"
    r"|\b(?:context(?:\s+window)?|ctx|kv[- ]?cache)\b(?:\s+size)?\s*(?:of\s+|[:=]\s*|at\s+)?"
    r"\d[\d,]*(?:\.\d+)?\s*(?:[km]\b|[- ]?(?:tokens?|tok)(?!/s)\b)"
    r"|\b(?:context(?:\s+window)?|ctx)\b(?:\s+size)?\s*(?:of\s+|[:=]\s*|at\s+)?\d{4,}\b",
    re.I)

# `flash` alone is not a storage medium — `Flash Attention` is an attention KERNEL,
# and reading it as an SSD reported `"GPU offload, Flash Attention, 262,144-token
# context"` as a storage requirement (#456).
_STORAGE_MEDIUM = r"(?:ssd|nvme|flash[- ]?(?:storage|memory|drive)|disk|hdd|storage)"
_STORAGE_TEXT = re.compile(
    rf"\b(?:offload\w*|stream\w*|expert\w*|mmap\w*)\b[^.\n]{{0,32}}\b{_STORAGE_MEDIUM}\b"
    rf"|\b{_STORAGE_MEDIUM}\b[^.\n]{{0,32}}\b(?:offload\w*|stream\w*|expert\w*|mmap\w*)\b",
    re.I)

#: Engines that stream experts from storage, so a model measured on one HAS a storage story.
_STREAMING_ENGINES = ("strata",)


def _params_b(model: dict) -> float | None:
    """The parameter count in billions, read from the model's own `params` string."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*B\b", str(model.get("params") or ""), re.I)
    return float(m.group(1)) if m else None


def _is_moe(model: dict) -> bool:
    """MoE, as the store spells it: `35B-A3B` (active params) or the word itself."""
    params = str(model.get("params") or "")
    return bool(re.search(r"\b\d+(?:\.\d+)?B-A\d+(?:\.\d+)?B\b", params, re.I)
                or "moe" in params.lower())


def _applies_storage_offload(model: dict) -> bool:
    """A storage-offload REQUIREMENT only exists for a model that cannot fit otherwise.

    MoE is the case the dimension describes (experts split across GPU/RAM/SSD) and a model in
    the tens of billions is the other; a dense 2B model has no expert to stream and no reason
    to page weights, so counting it "missing storage_offload" filed a gap no post can ever
    close and inflated the rank impact of the dimension (issue #469).
    """
    if _is_moe(model):
        return True
    size = _params_b(model)
    if size is not None and size >= 30:
        return True
    return any(str(e.get("engine") or "").strip().lower() in _STREAMING_ENGINES
               for e in (model.get("engines") or []))


def _applies_always(_model: dict) -> bool:
    """The default: a dimension every model can state (weights, context, engine build)."""
    return True


DIMENSIONS = (
    {
        "key": "system_ram_min",
        "label": "system RAM / unified memory requirement",
        "text": re.compile(r"\b\d+(?:\.\d+)?\s*(?:gb|mb|tb)\b[^.\n]{0,20}\bram\b|\bram\b[^.\n]{0,20}\b\d+(?:\.\d+)?\s*(?:gb|mb)\b", re.I),
        "why": "CPU and Metal tables are RAM-bound; partial offload + KV cache live in system RAM",
    },
    {
        "key": "weight_gb",
        "label": "weight footprint per format + quant",
        # A bare capacity is NOT a weights figure: "RX 9070 XT 16GB" is a card, "M3 Ultra
        # 256GB" is unified memory, "67K-token prompt" is context. Counting those as
        # `unstructured` reported 18 claims that do not exist and sent a backfill hunting for
        # weights in text that never stated one (issue #213). The number must sit next to a
        # weights word, and a capacity qualified as memory is refused whatever is beside it.
        "text": re.compile(
            rf"\b(?:weights?|gguf|quants?|on[- ]disk|file size)\b[^.\n]{{0,24}}\b{_WEIGHT_CAPACITY}"
            rf"|\b{_WEIGHT_CAPACITY}[^.\n]{{0,24}}\b(?:weights?|gguf|quants?|on[- ]disk)\b",
            re.I),
        # `hardware` names the CARD, never the weights (a GPU's VRAM would be read as a
        # footprint the run does not have).
        "skip_fields": ("hardware",),
        "why": "the real budget a run needs before any context is allocated",
    },
    {
        "key": "context_tokens",
        "label": "context window / KV-cache cost",
        "text": _CTX_TEXT,
        "why": "KV cache scales with context and consumes RAM and VRAM alike",
    },
    {
        "key": "storage_offload",
        "label": "storage-offload requirement (experts on SSD)",
        # A storage offload needs a MEDIUM and an offload/streaming wording in the same
        # sentence: "offloaded to the CPU" is a RAM story, "2.1GB on disk" is a file size,
        # and a machine's own SSD is not a requirement of the model. The old pattern
        # (`\bssd\b|\bdisk\b|\boffload`) flagged all of them, so five models were re-filed
        # as a storage gap on every refresh and a reader could not tell a storage
        # requirement from a memory one (issues #413/#367).
        "text": _STORAGE_TEXT,
        # Not every model CAN have one (issue #469): a dense 2B row was counted "missing"
        # on every refresh for a requirement that cannot apply to it.
        "applies": _applies_storage_offload,
        "why": "MoE engines (Strata) run big models by streaming experts from storage",
    },
    {
        "key": "engine_min_version",
        "label": "engine minimum version / required flags",
        "text": re.compile(r"\bflag\b|\bn[-_]gpu[-_]layers\b|\b--\w", re.I),
        "why": "many figures only reproduce on a specific engine build or with explicit flags",
    },
)

# Fields whose free text is scanned for a dimension that has no structured key.
TEXT_FIELDS = ("quant", "hardware", "why")
STALE_DAYS = 30

#: A gap dimension whose issue was CLOSED stays judged for this long (issue #491). The verdict a
#: triage reached is a judgement about the DIMENSION ("this is not implementable from the store"),
#: not about one issue: without this, closing files the same dimension again on the next refresh and
#: the queue's throughput is close operations nobody can keep up with. After this window the claim
#: is re-examined — and a dimension the signature no longer carries is not affected at all.
JUDGED_DAYS = 21


def dimension_of(entry: str) -> str:
    """The dimension a signature entry names: `missing:storage_offload` -> `storage_offload`."""
    return entry.split(":", 1)[1] if ":" in entry else entry


def judged_dimensions(previous: dict | None, as_of: str) -> dict[str, str]:
    """The dimensions still inside their judged window, with the stamp that judged them."""
    out: dict[str, str] = {}
    judged = (previous or {}).get("judged") or {}
    try:
        here = datetime.strptime(as_of, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return out
    for dim, stamp in judged.items():
        try:
            when = datetime.strptime(str(stamp), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
        if (here - when).days < JUDGED_DAYS:
            out[dim] = str(stamp)
    return out


def load(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def contract_keys() -> dict:
    """The keys the contracts can actually hold, so a dimension the store cannot
    represent is reported as a CONTRACT gap (the field is pruned at ingest)."""
    model, measurement = set(), set()
    c = load(CONTRACT, {}) or {}
    items = ((c.get("properties") or {}).get("models") or {}).get("items") or {}
    model = set((items.get("properties") or {}).keys())
    eng = (items.get("properties") or {}).get("engines") or {}
    measurement = set(((eng.get("items") or {}).get("properties") or {}).keys())
    s = load(SEARCH_CONTRACT, {}) or {}
    sitems = ((s.get("properties") or {}).get("models") or {}).get("items") or {}
    return {
        "model": model,
        "measurement": measurement,
        "search_model": set((sitems.get("properties") or {}).keys()),
    }


def _stated(m: dict, key: str) -> bool:
    """Is `key` captured for this model — on its own row OR on any of its measurements?

    #337/#376 deliberately moved a run's footprint onto the measurement (`weight_gb`,
    `context_tokens`, `system_ram_min`, `storage_offload`, `engine_min_version`), and both
    contracts declare every such dimension OPTIONAL on a measurement item. A value that lives
    only there is CAPTURED, and counting it as missing re-filed the same gap issue on every
    refresh — #364 then #376 both topped out at `storage_offload` while the store held it
    (issues #368/#388).
    """
    if m.get(key) not in (None, "", [], {}):
        return True
    return any(e.get(key) not in (None, "", [], {}) for e in (m.get("engines") or []))


def _dim_texts(row: dict, dim: dict) -> list[str]:
    """The free text of ONE row (a store model OR a captured raw row) a dimension scans.

    Free text lives on the row (`quant`/`why`) AND on every measurement (`hardware` is a
    dimension's own `skip_fields` decision), and both shapes are the same in the store and in
    a raw snapshot — so one builder serves both. One field at a time, never a CONCATENATION: a
    "within N characters" pattern applied to joined fields matches two words that never shared
    a sentence (issue #456).
    """
    fields = [f for f in TEXT_FIELDS if f not in dim.get("skip_fields", ())]
    texts = [str(row.get(f, "")) for f in fields]
    texts += [str(e.get(f, "")) for e in (row.get("engines") or []) for f in fields]
    return texts


def captured_text(store: dict, raw_dir: Path = RAW_DIR) -> dict[str, dict[str, list[str]]]:
    """Per STORE model id, the free text of every CAPTURED post, keyed by field.

    The record of what the search actually brought back (`data/raw/*.json`), keyed by the id
    `update_trending.resolve_model_mapping` gives the row — the same resolver ingest uses, so
    the analysis can never attribute a post to a different model than the merge did. The
    values are kept PER FIELD (never one concatenated blob), so a dimension's own
    `skip_fields` and a "within N characters" pattern still only ever match text that shared
    a sentence.

    This is what separates an ACQUISITION gap (no captured post states the figure — only a
    new search can close it) from an INGEST gap (a post states it and the store has no
    structured value). Reported per dimension, never as a reason to invent a value.
    """
    out: dict[str, dict[str, list[str]]] = {}
    if not raw_dir.exists():
        return out
    for path in sorted(raw_dir.glob("*.json")):
        data = load(path, {}) or {}
        for row in data.get("models", []) or []:
            if not isinstance(row, dict):
                continue
            res = update_trending.resolve_model_mapping(row, store)
            if res.get("status") != "existing":
                continue
            bucket = out.setdefault(str(res.get("id")), {})
            sources = [row] + list(row.get("engines") or [])
            for source in sources:
                for f in TEXT_FIELDS:
                    value = source.get(f) if isinstance(source, dict) else None
                    if isinstance(value, str) and value.strip():
                        bucket.setdefault(f, []).append(value)
    return out


def captured_dim_texts(capture: dict, model_id, dim: dict) -> list[str]:
    """The captured text ONE dimension scans for ONE model (its own fields only)."""
    bucket = (capture or {}).get(str(model_id)) or {}
    return [t for f in TEXT_FIELDS if f not in dim.get("skip_fields", ())
            for t in bucket.get(f, [])]


def has_real_post(model: dict) -> bool:
    """Does any of the model's measurements cite a real `…/status/<id>` post?

    The ONE definition of "a post behind this row" for the untraceable-figure class: a
    bare mirror URL and a profile page name no post, so they support no sentence (rule 3,
    `source_post` must be the post itself). `update_trending._is_post_url` is the resolver,
    never a second copy of the URL shape.
    """
    return any(update_trending._is_post_url(str(e.get("source_post", "")))
               for e in (model.get("engines") or []))


#: The class name `make data-gaps` reports and the issue body names. A figure can be
#: STATED in a model's own `why`/`quant` prose and still be untraceable: no captured post
#: states it, so no change can move it into the structured key without breaking the rule
#: that every stored figure traces to a real post (issue #470).
UNTRACEABLE = "untraceable"


def stated_untraceable(store: dict, capture: dict | None = None,
                       raw_dir: Path = RAW_DIR) -> dict[str, list[str]]:
    """Per dimension: model ids whose ONLY statement of the figure no post supports.

    This is its own class, and the reason is the whole point of #470: the analysis used to
    report these models as `unstructured` — "stated in prose only, an ingest job" — which
    reads as structurable work, while the store holds no post for the sentence that states
    it. An ingest job on them can only invent the attribution or delete the prose (rule
    3b), so the fix is a CAPTURE job: a search that brings back the post stating it, or a
    prompt that stops writing a model-level figure no post supports.

    A model is in the class when the dimension's `text` pattern matches the model's OWN
    free text (`why`/`quant`/`hardware`) and NO captured post's text does. A model whose
    captured post DOES state it is an ingest job (`unstructured`/`captured_prose`) and is
    not reported here — the difference is whether the sentence has a post behind it.

    The one implementation of the class: `scripts/validate.py`'s
    `check_untraceable_figures` imports it, so the report and CI cannot disagree (rule 6d).
    """
    if capture is None:
        capture = captured_text(store, raw_dir)
    out: dict[str, list[str]] = {}
    for dim in DIMENSIONS:
        ids = []
        for m in store.get("models") or []:
            if _stated(m, dim["key"]):
                continue
            if not any(dim["text"].search(t) for t in _dim_texts(m, dim)):
                continue                      # states no figure at all — a missing dimension
            if any(dim["text"].search(t) for t in captured_dim_texts(capture, m.get("id", "?"), dim)):
                continue                      # a captured post states it — an INGEST job
            ids.append(m.get("id", "?"))
        out[dim["key"]] = ids
    return out


def unattributed_figures(store: dict) -> dict[str, list[str]]:
    """Per dimension: models whose stated figure has NO real post on the row at all.

    A stricter half of the same defect, and the half CI can FAIL on: the model's prose
    states a requirement figure while every one of its measurements cites a placeholder
    or a profile page. Nothing on the row can ever attribute that sentence, so it must
    never be written (the search prompt says so) and `check_untraceable_figures` refuses
    it. The shipped store holds none of these, so the check is green on history while a
    new one turns the PR red — the shape the issue asks the "validate pair" to stop.
    """
    out: dict[str, list[str]] = {}
    for dim in DIMENSIONS:
        ids = [m.get("id", "?") for m in (store.get("models") or [])
               if not _stated(m, dim["key"])
               and not has_real_post(m)
               and any(dim["text"].search(t) for t in _dim_texts(m, dim))]
        out[dim["key"]] = ids
    return out


def analyse(store: dict, contract: dict, raw_dir: Path = RAW_DIR) -> dict:
    """The gap report: per-dimension coverage, free-text-only mentions, and the
    store/maintenance gaps the refresh cannot see."""
    models = store.get("models") or []
    declared_model = contract["model"] | contract["search_model"]
    declared_measurement = contract["measurement"]
    gaps: list[str] = []          # volatile-ish findings, reported but not signatured
    missing: dict[str, list[str]] = {}   # dimension -> model ids with no structured value
    not_applicable: dict[str, list[str]] = {}   # dimension -> ids the dimension cannot apply to
    unstructured: dict[str, list[str]] = {}
    captured: dict[str, list[str]] = {}   # prose only in the CAPTURE, not in the store text
    not_captured: dict[str, list[str]] = {}   # NO captured post states it — a new search is the fix
    untraceable: dict[str, list[str]] = {}    # store prose states it, NO post states it (#470)
    contract_gaps: dict[str, str] = {}

    # What the search actually brought back, per store id (the record of each real post).
    # One scan for every dimension: this is what tells an ACQUISITION gap from an INGEST gap.
    capture = captured_text(store, raw_dir)

    for dim in DIMENSIONS:
        key = dim["key"]
        if key not in declared_model and key not in declared_measurement:
            contract_gaps[key] = (
                f"`{key}` is not declared in model_contract.json/search_contract.json — "
                f"the value is pruned at ingest, so {dim['label']} cannot be stored")
        applies = dim.get("applies") or _applies_always
        applicable = [m for m in models if applies(m)]
        not_applicable[key] = [m.get("id", "?") for m in models if m not in applicable]
        ids = [m.get("id", "?") for m in applicable if not _stated(m, key)]
        missing[key] = ids
        text_models = []
        capture_only = []
        uncaptured = []
        untraceable_ids = []
        for m in applicable:
            if _stated(m, key):
                continue
            mid = m.get("id", "?")
            # The model's OWN prose (the store side, unchanged) …
            own = any(dim["text"].search(t) for t in _dim_texts(m, dim))
            # … and the CAPTURED post's prose, which the store may have pruned — the same
            # rule, over the text the search actually recorded. Computed once, because the
            # PAIR decides the class: a sentence a captured post states is an INGEST job,
            # a sentence only the store states is UNTRACEABLE (issue #470).
            post = any(dim["text"].search(t) for t in captured_dim_texts(capture, mid, dim))
            if own and post:
                text_models.append(mid)
            elif post:
                capture_only.append(mid)
            elif own:
                # Stated in the store, stated by NO captured post: there is nothing an
                # ingest job can point the structured value at. Its own class, because
                # reporting it as "prose only, an ingest job" sends triage to work no
                # post can close (§ #470).
                untraceable_ids.append(mid)
            # … and neither: no post we ever captured states this figure at all.
            else:
                uncaptured.append(mid)
        unstructured[key] = text_models
        captured[key] = capture_only
        not_captured[key] = uncaptured
        untraceable[key] = untraceable_ids

    # maintenance gaps the merge/sort cannot report
    as_of = None
    gen = store.get("generated_utc")
    if gen:
        as_of = datetime.strptime(gen, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    cutoff = (as_of - timedelta(days=STALE_DAYS)).date() if as_of else None
    stale = []
    for m in models:
        dates = sorted(str(e.get("date", "")) for e in (m.get("engines") or []))
        if cutoff and (not dates or dates[-1] < cutoff.isoformat()):
            stale.append(m.get("id", "?"))
    thin = [f"{m.get('id', '?')}/{e.get('engine', '?')}"
            for m in models for e in (m.get("engines") or [])
            if not e.get("hardware") or not e.get("quant")]
    estimated = [f"{m.get('id', '?')}/{e.get('engine', '?')}:{e.get('tps')}"
                 for m in models for e in (m.get("engines") or [])
                 if "est" in str(e.get("tps", "")).lower()]
    empty_legs = []
    for f in sorted(raw_dir.glob("*.json")) if raw_dir.exists() else []:
        d = load(f, {}) or {}
        if not (d.get("models") or []):
            empty_legs.append(f.name)

    for key, ids in missing.items():
        if ids:
            un = len(not_captured.get(key, []))
            unt = len(untraceable.get(key, []))
            gaps.append(f"{len(ids)}/{len(models)} models have no structured `{key}` "
                        f"({un} not stated by any captured post — a new search is the only fix; "
                        f"{len(ids) - un - unt} stated in prose only — an ingest job; "
                        + (f"{unt} stated but untraceable — no post behind the figure; " if unt else "")
                        + f"e.g. {', '.join(ids[:5])})")
    for key, ids in unstructured.items():
        if ids:
            gaps.append(f"{len(ids)} model(s) name the value only in free text, not in `{key}`: "
                        f"{', '.join(ids[:5])}")
    for key, ids in untraceable.items():
        if ids:
            gaps.append(f"{len(ids)} model(s) state the value in `{key}`'s free text with NO post "
                        f"behind it (untraceable — a capture job, not an ingest job): "
                        f"{', '.join(ids[:5])}")
    if stale:
        gaps.append(f"{len(stale)} model(s) have no measurement in the last {STALE_DAYS} days: "
                    f"{', '.join(stale[:5])}")
    if thin:
        gaps.append(f"{len(thin)} measurement(s) carry no hardware or no quant: {', '.join(thin[:5])}")
    if estimated:
        gaps.append(f"{len(estimated)} measurement(s) are estimates: {', '.join(estimated[:5])}")
    # Empty raw legs are INFORMATIONAL: a per-query write legitimately captures
    # nothing (the query had no hits), so they are reported but never filed as a
    # gap — only a whole refresh with no models at all would be a defect.
    informational = []
    if empty_legs:
        informational.append(f"{len(empty_legs)} raw leg(s) captured 0 models "
                             f"(a query with no hits — informational)")

    # signature = what the STORE cannot hold STRUCTURALLY — one entry per DIMENSION, never
    # one per model (issue #472). It used to be per model (`missing:storage_offload:<id>`),
    # so every model the store gained that lacked the key GREW the signature, the filer read
    # that as "the gap set changed", and it filed the SAME dimension again: 12
    # `storage_offload` issues since 2026-10-15, counts 31 → 38 → 39 → 40 → 41 → 42 → 59,
    # each one triaged to refine/close and re-filed the next day. A dimension now files
    # ONCE and stays one issue until it closes — `already_filed()` still refuses a second
    # while one is open, and a NEW dimension still changes the signature and files.
    # The per-model detail (`missing`, `unstructured`) stays in the report and in the issue
    # BODY, so a human still sees which models and how many.
    signature = sorted(
        [f"contract:{k}" for k in contract_gaps]
        # A dimension with nothing missing is NOT a gap: the list carries the key with an
        # EMPTY list once every model states it, and naming it would keep filing it for ever.
        + [f"missing:{k}" for k in missing if missing[k]]
        + [f"unstructured:{k}" for k in unstructured]
    )
    return {
        "as_of": gen,
        "models": len(models),
        "dimensions": {d["key"]: {"label": d["label"], "why": d["why"]} for d in DIMENSIONS},
        "contract_gaps": contract_gaps,
        "missing": missing,
        "not_captured": not_captured,
        # Its own class, deliberately NOT a signature entry: a signature entry files an
        # issue, and an issue for a sentence no post backs would file the same dimension
        # again every refresh (the #472 churn) while only a new CAPTURE can retire it.
        "untraceable": untraceable,
        "captured_prose": captured,
        "not_applicable": not_applicable,
        "unstructured": unstructured,
        "maintenance": {"stale": stale, "thin_measurements": thin,
                        "estimated": estimated, "empty_raw_legs": empty_legs},
        "findings": gaps,
        "informational": informational,
        "signature": signature,
    }


def rank_impact(report: dict) -> list[tuple[str, int]]:
    """Gaps ranked by how many models they unblock (a dimension that is missing on
    every model outranks a per-model maintenance item)."""
    ranked = []
    for key, ids in report["missing"].items():
        if ids:
            ranked.append((key, len(ids)))
    for key, ids in report["unstructured"].items():
        if ids:
            ranked.append((f"unstructured:{key}", len(ids)))
    return sorted(ranked, key=lambda kv: (-kv[1], kv[0]))


def _gap_kind(report: dict, key: str) -> str:
    """How many of a dimension's models no captured post states, and how many it does.

    THE point of this change: a ranked gap that reads `66 model(s)` looks like ingest work,
    while measured against the captured snapshots 61 of those models' posts state no such
    figure at all — only a new search can close it. `unstructured:<dim>` entries are prose-only
    mentions by construction, so they are an ingest job one and all.
    """
    dim = key.split(":", 1)[1] if key.startswith("unstructured:") else key
    ids = (report.get("missing") or {}).get(dim) if not key.startswith("unstructured:") else None
    if ids is None:
        prose = len((report.get("unstructured") or {}).get(dim) or [])
        return f" — {prose} stated in prose only (ingest gap)" if prose else ""
    un = len((report.get("not_captured") or {}).get(dim) or [])
    unt = len((report.get("untraceable") or {}).get(dim) or [])
    ingest = len(ids) - un - unt
    parts = []
    if un:
        parts.append(f"{un} not stated by any captured post (acquisition gap)")
    if ingest:
        parts.append(f"{ingest} stated in prose only (ingest gap)")
    if unt:
        # Its own kind, never folded into "ingest": no post states the sentence, so a
        # structured value cannot be attributed to one (#470).
        parts.append(f"{unt} stated but untraceable — no post behind the figure (capture gap)")
    return f" — {', '.join(parts)}" if parts else ""


def render(report: dict) -> str:
    lines = [
        "# data-gap analysis",
        "",
        f"- as of: `{report['as_of']}`",
        f"- models: {report['models']}",
        f"- gap signature entries: {len(report['signature'])}",
        "",
        "## Gaps, ranked by models unblocked",
        "",
    ]
    if report.get("baseline_as_of"):
        age = report.get("baseline_age_days")
        when = f"{age} day(s) before this analysis" if age is not None else "age unknown"
        lines.insert(5, f"- baseline: recorded `{report['baseline_as_of']}` ({when})")
    for key, n in rank_impact(report):
        lines.append(f"- **{key}** — {n} model(s)" + _gap_kind(report, key))
    if not report["findings"]:
        lines.append("- none")
    lines += ["", "## Not stated by any captured post (a new search is the only fix)", ""]
    acquisition = {k: v for k, v in (report.get("not_captured") or {}).items() if v}
    for key, ids in sorted(acquisition.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        lines.append(f"- **{key}** — {len(ids)} model(s) no captured post states a figure for: "
                     f"{', '.join(ids[:6])}" + (" …" if len(ids) > 6 else ""))
    if not acquisition:
        lines.append("- none")
    lines += ["", "## Stated in prose only (an ingest job, not a search)", ""]
    ingest = {k: v for k, v in (report.get("unstructured") or {}).items() if v}
    for key, ids in sorted(ingest.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        lines.append(f"- **{key}** — {len(ids)} model(s): " + ", ".join(ids[:6])
                     + (" …" if len(ids) > 6 else ""))
    for key, ids in sorted((report.get("captured_prose") or {}).items()):
        if ids:
            lines.append(f"- **{key}** — {len(ids)} model(s) whose CAPTURED post states it but whose "
                         f"store row does not: " + ", ".join(ids[:6]) + (" …" if len(ids) > 6 else ""))
    if not ingest and not any((report.get("captured_prose") or {}).values()):
        lines.append("- none")
    # The class issue #470 asks for: the store STATES the figure, but no post does, so no
    # ingest change can move it into the structured key without inventing the attribution
    # (`tests/test_data_gap_analysis.py::test_structured_dimensions_trace_to_a_real_post`
    # is the rule it would break). Named as its own job — a CAPTURE job — so nobody reads
    # it as the ingest work the section above describes.
    lines += ["", "## Stated but untraceable (no post behind the figure — a capture job)", ""]
    untraceable = {k: v for k, v in (report.get("untraceable") or {}).items() if v}
    for key, ids in sorted(untraceable.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        lines.append(f"- **{key}** — {len(ids)} model(s) state it in free text and NO captured "
                     f"post does, so there is nothing to attribute the value to: "
                     + ", ".join(ids[:6]) + (" …" if len(ids) > 6 else ""))
    if not untraceable:
        lines.append("- none")
    lines += ["", "## Dimensions that cannot apply (never counted as missing)", ""]
    na = {k: v for k, v in (report.get("not_applicable") or {}).items() if v}
    for key, ids in sorted(na.items()):
        lines.append(f"- **{key}** — {len(ids)} model(s) cannot have one: {', '.join(ids[:6])}"
                     + (" …" if len(ids) > 6 else ""))
    if not na:
        lines.append("- none")
    lines += ["", "## Contract gaps (the store cannot hold the value)", ""]
    for key, why in report["contract_gaps"].items():
        lines.append(f"- {why}")
    if not report["contract_gaps"]:
        lines.append("- none")
    lines += ["", "## Findings", ""]
    lines += [f"- {f}" for f in report["findings"]] or ["- none"]
    return "\n".join(lines) + "\n"


def changed(report: dict, baseline_path: Path) -> tuple[bool, dict | None]:
    previous = load(baseline_path)
    if previous is None:
        return True, None
    return report["signature"] != previous.get("signature", []), previous


def baseline_info(baseline_path: Path, as_of: str) -> dict | None:
    """The recorded baseline's `as_of` and how many days before this analysis it was written.

    The baseline was written and never read (issue #307): it is the dedup key that decides
    whether a gap set is "new", so a stale one suppresses a filing (`signature unchanged`)
    for gaps that describe a month-old store — and nothing in the output said when it was
    recorded or how old it was.
    """
    previous = load(baseline_path) or {}
    recorded_raw = previous.get("as_of")
    if not recorded_raw:
        return None
    info = {"baseline_as_of": recorded_raw, "baseline_age_days": None}
    try:
        recorded = datetime.strptime(recorded_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        here = datetime.strptime(as_of, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return info
    info["baseline_age_days"] = (here - recorded).days
    return info


def write_baseline(report: dict, path: Path, judged: dict[str, str] | None = None) -> None:
    """Record the gap signature — and the dimension verdicts already reached (issue #491)."""
    payload: dict = {"as_of": report["as_of"], "signature": report["signature"]}
    if judged:
        payload["judged"] = dict(sorted(judged.items()))
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def signature_id(report: dict) -> str:
    """A stable id for the gap SET (the issue marker), independent of `as_of`."""
    return hashlib.sha256("\n".join(report["signature"]).encode()).hexdigest()[:12]


def marker(sig: str) -> str:
    """The invisible marker carried in the issue body, searched for on the next run."""
    return f"<!-- data-gap-signature: {sig} -->"


def already_filed(sig: str) -> tuple[str | None, list[dict]]:
    """The URL of an OPEN issue already carrying this gap signature, or None.

    The baseline only reaches the repository through the refresh PR, so between
    filing and that merge every run computes "changed" from the same old baseline
    and would file the same issue again (two crons a day can both do it) — and a
    refresh PR closed without merging would re-file it forever. A CLOSED issue
    does not block: a closed gap-issue means the work was done or dropped, so the
    gap set re-appearing later is new information, not a duplicate (#157).
    """
    out = subprocess.run(
        ["gh", "issue", "list", "--state", "all", "--label", LABEL,
         "--search", f"{sig} in:body", "--json", "number,state,url,closedAt"],
        text=True, capture_output=True)
    if out.returncode != 0:
        raise SystemExit(f"[data-gaps] gh issue list failed: {out.stderr.strip()}")
    try:
        items = json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        items = []
    open_url: str | None = None
    closed: list[dict] = []
    for item in items:
        if item.get("state") == "OPEN" and open_url is None:
            open_url = str(item.get("url") or item.get("number"))
        elif item.get("state") == "CLOSED":
            closed.append(item)
    return open_url, closed


def label_exists() -> bool:
    """Does the repo already carry LABEL?"""
    out = subprocess.run(["gh", "label", "list", "--search", LABEL, "--json", "name"],
                         text=True, capture_output=True)
    if out.returncode != 0:
        raise SystemExit(f"[data-gaps] gh label list failed: {out.stderr.strip()}")
    try:
        return LABEL in {str(l.get("name", "")) for l in json.loads(out.stdout or "[]")}
    except json.JSONDecodeError:
        return False


def ensure_label_exists() -> None:
    """Create LABEL when the repo does not have it yet, or fail loudly.

    GitHub IGNORES a label it does not know instead of refusing the create, so a
    filing made before the label exists lands UNLABELLED while `gh issue create`
    still returns 0 — and `gh issue edit --add-label` then refuses it, which is
    the shape measured on master (issue #277, the same shape #161 recorded): the
    filed issue carried nothing, the step was `continue-on-error`, and BOTH bot
    queues stayed empty while every run reported green. Creating the label first
    is what makes the label land instead of being dropped.
    """
    if label_exists():
        return
    out = subprocess.run(["gh", "label", "create", LABEL, "--color", LABEL_COLOR,
                          "--description", LABEL_DESCRIPTION], text=True, capture_output=True)
    if not label_exists():
        why = (out.stderr or out.stdout or "").strip() or f"gh exited {out.returncode} without a message"
        raise SystemExit(
            f"[data-gaps] the repo does not carry `{LABEL}` and it could not be created — the "
            f"bot chain triggers on that label, so every filing would be invisible; failing "
            f"instead of reporting it. gh said: {why}")


def ensure_label(number: str) -> None:
    """Make the filed issue carry LABEL, or fail loudly (issue #161).

    The label is the trigger of the downstream chain: `issue-bot.yml` reacts to
    newly opened issues, its sweep picks open `data-gap-analysis` ones — one
    implementer per issue. Measured: the CLI created the issue and returned 0
    while applying NO label (the label exists and is appliable to that issue), so
    the filing was invisible to both bots and nothing was red.
    """
    def labels() -> set[str]:
        out = subprocess.run(["gh", "issue", "view", number, "--json", "labels"],
                             text=True, capture_output=True)
        if out.returncode != 0:
            raise SystemExit(f"[data-gaps] gh issue view {number} failed: {out.stderr.strip()}")
        try:
            return {str(l.get("name", "")) for l in json.loads(out.stdout or "{}").get("labels", [])}
        except json.JSONDecodeError:
            return set()

    if LABEL in labels():
        return
    # The label must EXIST before an edit can apply it: GitHub ignores a label it
    # does not know, which is how a filing lands unlabelled while `gh` returns 0.
    ensure_label_exists()
    edit = subprocess.run(["gh", "issue", "edit", number, "--add-label", LABEL],
                          text=True, capture_output=True)
    if LABEL not in labels():
        # `gh`'s OWN diagnosis is the actionable half: measured (issue #277), the
        # refusal is `Resource not accessible by personal access token` because the
        # step ran with a PAT that declares no Issues scope. Swallowing it left
        # "the label did not stick" with no cause and no fix.
        why = (edit.stderr or edit.stdout or "").strip() or f"gh exited {edit.returncode} without a message"
        raise SystemExit(
            f"[data-gaps] issue {number} does not carry `{LABEL}` after re-applying it — the "
            f"bot chain triggers on that label, so this filing would be invisible; failing "
            f"instead of reporting it. gh said: {why}")


def issue_body(report: dict, previous: dict | None) -> tuple[str, str]:
    """The issue body and title for a changed gap set — the ONE implementation the filer uses.

    Split out of `file_issue()` so the text a human reads is testable without a `gh` on PATH:
    it names, per ranked gap, whether it is an ACQUISITION gap (no captured post states the
    figure) or an INGEST gap (a post states it, the store holds no structured value).
    """
    added = sorted(set(report["signature"]) - set((previous or {}).get("signature", [])))
    ranked = rank_impact(report)
    body = [
        "## Goal",
        "",
        "Close the data gaps the refresh acquired but the store does not capture.",
        "Every item below is real data the search sees and the contract drops or",
        "leaves unstructured — never invent a value, and never remove a key",
        "(additive contract changes only; a new key is OPTIONAL, never `required`).",
        "",
        "Each ranked gap says WHICH kind it is: **not stated by any captured post** is an",
        "acquisition gap (the captured snapshots state no such figure for those models, so a",
        "new search is the only fix — the footprint queries in the refresh ask the ranked",
        "models for it), while **stated in prose only** is an ingest job.",
        "",
        "## Ranked gaps",
        "",
    ]
    body += [f"- **{k}** — {n} model(s)" + _gap_kind(report, k) for k, n in ranked] or ["- none"]
    acquisition = {k: v for k, v in (report.get("not_captured") or {}).items() if v}
    if acquisition:
        body += ["", "## Not stated by any captured post (acquisition gap)", ""]
        body += [f"- **{k}** — {len(ids)} model(s): " + ", ".join(ids[:10])
                 + (" …" if len(ids) > 10 else "")
                 for k, ids in sorted(acquisition.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
    untraceable = {k: v for k, v in (report.get("untraceable") or {}).items() if v}
    if untraceable:
        body += ["", "## Stated but untraceable (a capture job, not an ingest job)", "",
                 "The store's own prose states these figures and NO captured post does, so",
                 "there is no post to attribute the structured value to. Structuring them",
                 "would invent the attribution (`tests/test_data_gap_analysis.py::",
                 "test_structured_dimensions_trace_to_a_real_post`), and deleting the prose",
                 "would break additive-only (rule 3b). What closes them is a SEARCH that",
                 "brings back the post stating the figure — and a prompt that stops writing",
                 "a model-level figure no post supports."]
        body += [f"- **{k}** — {len(ids)} model(s): " + ", ".join(ids[:10])
                 + (" …" if len(ids) > 10 else "")
                 for k, ids in sorted(untraceable.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
    body += ["", "## Contract gaps", ""]
    body += [f"- {why}" for why in report["contract_gaps"].values()] or ["- none"]
    if added:
        body += ["", "## New since the last analysis", ""] + [f"- `{a}`" for a in added[:40]]
    body += ["", "## Full report", "", "```", render(report).strip(), "```"]
    # The window of the run that FILED this, at the TOP (issue #199): the same block the
    # refresh PR carries, from the same composer — so an issue filed BY a refresh can be
    # told apart from one filed by an earlier run. "" only when there is no run to
    # describe (a local `make data-gap-issue`); a `gh` read that fails raises instead.
    block = refresh_run_block.current_block()
    if block:
        body = [*block.splitlines(), "", *body]
    # The marker lets the NEXT run recognise this gap set (issue #157). Invisible
    # in the rendered issue, searchable in the body.
    body += ["", marker(signature_id(report))]
    title = (f"data-gap: {ranked[0][0]} ({ranked[0][1]} models)" if ranked else "data-gap: refresh analysis")
    return "\n".join(body), title


def file_issue(report: dict, previous: dict | None) -> str:
    """One issue per changed gap set: `issue_body()`'s text, filed with the label the bots read."""
    text, title = issue_body(report, previous)
    # The label must exist BEFORE the create: GitHub silently ignores an unknown
    # label, so `--label` below would be dropped and the filing would be invisible
    # to both bots while `gh` still exits 0 (issue #277).
    ensure_label_exists()
    out = subprocess.run(
        ["gh", "issue", "create", "--title", f"{title} ({report['as_of']})",
         "--body-file", "-", "--label", LABEL],
        input=text, text=True, capture_output=True)
    if out.returncode != 0:
        raise SystemExit(f"[data-gaps] gh issue create failed: {out.stderr.strip()}")
    url = out.stdout.strip()
    # The label is what the downstream bot chain triggers on; a create that
    # returns 0 without it files an issue nothing will ever implement (#161).
    ensure_label(url.rstrip("/").split("/")[-1])
    return url


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Post-refresh data-gap analysis")
    ap.add_argument("--out", help="write the markdown report here (default stdout)")
    ap.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    ap.add_argument("--issue", action="store_true", help="file ONE issue when the gap set changed")
    ap.add_argument("--check", action="store_true", help="exit 1 when the gap set changed")
    ap.add_argument("--write-baseline", action="store_true",
                    help="record the current gap signature as the baseline (no issue)")
    a = ap.parse_args(argv)

    store = load(STORE)
    if store is None:
        print(f"[data-gaps] {STORE} missing", file=sys.stderr)
        return 1
    report = analyse(store, contract_keys())

    baseline_path = Path(a.baseline)
    is_changed, previous = changed(report, baseline_path)
    # WHICH baseline this run compared against, and how old it is (issue #307). A
    # stale baseline suppresses a filing silently ("signature unchanged"), so its age
    # belongs in the report AND in the run log.
    info = baseline_info(baseline_path, report["as_of"])
    if info:
        report.update(info)
        age = info["baseline_age_days"]
        if age is not None and age >= STALE_DAYS:
            report["findings"] = list(report["findings"]) + [
                f"the gap baseline was recorded {age} days ago ({info['baseline_as_of']}) — "
                f"older than {STALE_DAYS} days: an unchanged gap set files nothing, so "
                f"re-record it with `make data-gap-baseline` if the gaps look stale"]
    text = render(report)
    if a.out:
        Path(a.out).write_text(text)
    else:
        print(text)
    if info:
        age = info["baseline_age_days"]
        print(f"[data-gaps] baseline: recorded {info['baseline_as_of']}"
              + (f" ({age} day(s) before this analysis)" if age is not None else " (age unknown)"),
              file=sys.stderr)
        if age is not None and age >= STALE_DAYS:
            print(f"[data-gaps] baseline is STALE ({age} days, threshold {STALE_DAYS}) — "
                  f"an unchanged gap set files nothing; `make data-gap-baseline` re-records it",
                  file=sys.stderr)
    print(f"[data-gaps] signature {'CHANGED' if is_changed else 'unchanged'} "
          f"({len(report['signature'])} entries, {len(rank_impact(report))} ranked gaps)",
          file=sys.stderr)

    if a.write_baseline:
        write_baseline(report, baseline_path)
        print(f"[data-gaps] baseline written to {baseline_path} ({len(report['signature'])} entries)",
              file=sys.stderr)
    if a.issue and is_changed:
        sig = signature_id(report)
        existing, closed_issues = already_filed(sig)
        judged = dict((previous or {}).get("judged") or {})
        # A CLOSED issue carrying this signature is a JUDGEMENT about the dimensions it named
        # (issue #491): the triage read the thread and decided the gap is not implementable from
        # the store. Remember when, so the next refresh does not file the same dimension again
        # for JUDGED_DAYS.
        for item in closed_issues:
            stamp = str(item.get("closedAt") or "")
            if stamp:
                for entry in report["signature"]:
                    judged[dimension_of(entry)] = stamp
        recent = judged_dimensions({"judged": judged}, report["as_of"])
        undecided = [e for e in report["signature"] if dimension_of(e) not in recent]
        if existing:
            # The baseline reaches master only through the refresh PR, so a second
            # run before that merge (or after a PR was closed) sees the same change:
            # report it, file nothing (issue #157).
            print(f"[data-gaps] gap set {sig} is already filed: {existing} — no duplicate",
                  file=sys.stderr)
        elif not undecided:
            # Every dimension in this set was judged inside its window: re-filing would repeat a
            # decision a human or the reviewer already made (#491).
            for dim, stamp in sorted(recent.items()):
                print(f"[data-gaps] {dim}: judged at {stamp} — not re-filing within "
                      f"{JUDGED_DAYS} days (issue #491)", file=sys.stderr)
            write_baseline(report, baseline_path, judged)
        else:
            url = file_issue(report, previous)
            print(f"[data-gaps] filed {url}", file=sys.stderr)
            write_baseline(report, baseline_path, judged)
    elif a.issue:
        print("[data-gaps] no new gap set — no issue filed", file=sys.stderr)
    elif a.issue:
        print("[data-gaps] no new gap set — no issue filed", file=sys.stderr)
    if a.check and is_changed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
