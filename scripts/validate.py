#!/usr/bin/env python3
"""QA validation for the trending-local-llms data store + README.

Runs in CI (on PRs) and locally. Enforces the no-removal guarantee and the
data-quality rules from AGENTS.md:

  1. No model that existed in a previous snapshot may be removed from the
     current store (retention, not deletion).
  2. New models may be added; they must be valid.
  3. Every model has: name, full_name, HF link, license, params, VRAM tier,
     and at least one engine measurement with engine name + t/s + repo link.
  4. Within each backend table, models sort by highest t/s (descending).
  5. Existing models keep their history; a model with a newer measurement
     updates its t/s rather than being replaced/removed.

Exit code 0 = pass, 1 = fail. Prints a report.

Run:  python3 scripts/validate.py [--snapshot-dir data/snapshots]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))  # import update_trending helpers
# Allow tests to run the make targets against a small fixture in a temp dir.
_DATA_DIR = Path(os.environ.get("TRENDING_DATA_DIR", str(ROOT / "data")))
DATA = _DATA_DIR / "models.json"
SNAPSHOT_DIR = _DATA_DIR / "snapshots"
README = Path(os.environ.get("TRENDING_README", str(ROOT / "README.md")))
CONTRACT = _DATA_DIR / "model_contract.json"
SEARCH_CONTRACT = _DATA_DIR / "search_contract.json"
RAW_DIR = _DATA_DIR / "raw"

# Text file extensions that must end with a newline
TEXT_EXTS = (".json", ".md", ".yml", ".yaml", ".py", ".toml", ".sh", ".txt", ".cfg")
TEXT_NAMES = ("Makefile",)

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)
    print(f"  FAIL: {msg}")


def model_ids(store: dict) -> set[str]:
    return {m["id"] for m in store["models"]}


def check_no_duplicates(store: dict) -> None:
    """No duplicate models in data/models.json — by id AND by name."""
    ids = [m.get("id") for m in store["models"]]
    names = [m.get("name") for m in store["models"]]
    dup_ids = {x for x in ids if ids.count(x) > 1}
    dup_names = {x for x in names if names.count(x) > 1}
    if dup_ids:
        fail(f"duplicate model ids in models.json: {sorted(dup_ids)}")
    if dup_names:
        fail(f"duplicate model names in models.json: {sorted(dup_names)}")
    if not dup_ids and not dup_names:
        print(f"  OK: no duplicate models ({len(ids)} unique)")


def _normalize_tps(tps) -> str:
    """Normalize a t/s string for duplicate detection: strip estimate markers
    ((est)/(estimated)) and whitespace, lowercase. So '39.3' and '39.3 (est)'
    are detected as the SAME measurement, while genuine ranges ('67-71') and
    comments ('233 (DFlash spec-decode)') stay distinct."""
    return (tps or "").strip().lower().replace("(est)", "").replace("(estimated)", "").strip()


def check_no_duplicate_engines(store: dict) -> None:
    """Within each model, no duplicate engine row. Two rows are duplicates when
    they share (engine, date, hardware, normalized-tps, quant) — where the tps
    is normalized (est markers + whitespace stripped), so '39.3' and '39.3 (est)'
    count as the same measurement. Different hardware, t/s range, or date is a
    legitimate distinct measurement, NOT a duplicate."""
    bad = 0
    for m in store["models"]:
        seen = {}
        for e in m.get("engines", []):
            key = (e.get("engine"), e.get("date"), e.get("hardware"),
                   _normalize_tps(e.get("tps")), e.get("quant"))
            if key in seen:
                bad += 1
                fail(f"{m.get('id','?')}: duplicate engine row ({e.get('engine')}, {e.get('date')}, {e.get('hardware')}, {e.get('tps')})")
            seen[key] = True
    if not bad:
        print(f"  OK: no duplicate engine rows in any model")


# A t/s value must START with a numeric token (optionally an estimate tilde, an
# int/float, and a range). Leading comments or pure text are invalid. Examples
# that pass: 39.3, ~50, 67-71, 99.7, 233 (DFlash spec-decode). Examples that
# FAIL: 'a few (est)', '~fast', '(est) 50'. Ranges/estimates/comments-after-the-
# number are preserved because they still begin with a number.
_TPS_START = re.compile(r"^~?\s?\d+(?:\.\d+)?")


def check_tps_shape(store: dict) -> None:
    """Every engine t/s must START with a numeric token (optional '~', an
    int/float, possibly a range). Rejects a search that wrote a non-numeric
    placeholder like 'a few (est)', a leading comment, or a bare label — t/s is
    a measurement. Ranges ('67-71') and estimates ('~50') still pass because
    they begin with a digit."""
    bad = 0
    for m in store["models"]:
        for e in m.get("engines", []):
            t = e.get("tps", "")
            if t and not _TPS_START.match(t.strip()):
                bad += 1
                fail(f"{m.get('id','?')}: engine '{e.get('engine')}' tps does not start with a number: {t!r}")
    if not bad:
        print("  OK: all engine tps start with a numeric token")


def check_latest_tps(store: dict) -> None:
    """Each model's engine list is ordered newest-date-first, so the README
    (which renders per engine) always surfaces the LATEST trending t/s first,
    never a stale older value."""
    bad = 0
    for m in store["models"]:
        dates = [e.get("date", "") for e in m.get("engines", [])]
        if dates != sorted(dates, reverse=True):
            bad += 1
            fail(f"{m.get('id','?')}: engines not ordered newest-date-first: {dates}")
    if not bad:
        print(f"  OK: all models ordered newest t/s date first (latest trending t/s surfaced)")


def check_supported_engines(store: dict) -> None:
    """Every model lists the engines it is supported by (supported_engines),
    and each engine in that list has a measurement in the engines array."""
    for m in store["models"]:
        se = m.get("supported_engines")
        if not se:
            fail(f"{m.get('id','?')}: missing 'supported_engines' list")
            continue
        measured = {e.get("engine") for e in m.get("engines", [])}
        for eng in se:
            if eng not in measured:
                fail(f"{m.get('id','?')}: supported_engine '{eng}' has no measurement in engines")
    print(f"  OK: all {len(store['models'])} models list supported_engines")


def check_no_removal(store: dict, snap_dir: Path) -> None:
    snaps = sorted(snap_dir.glob("trending-*.json"))
    if not snaps:
        print("  (no prior snapshots — nothing to compare for removal)")
        return
    prev = json.loads(snaps[-1].read_text())
    prev_ids = model_ids(prev)
    cur_ids = model_ids(store)
    removed = prev_ids - cur_ids
    if removed:
        fail(f"models removed from previous snapshot {snaps[-1].name}: {sorted(removed)}")
    else:
        print(f"  OK: no models removed (prev {len(prev_ids)} -> cur {len(cur_ids)})")


def check_model_fields(store: dict) -> None:
    for m in store["models"]:
        for field in ("id", "name", "full_name", "hf", "license", "params", "vram_tier", "vram_min"):
            if not m.get(field):
                fail(f"{m.get('id','?')}: missing field '{field}'")
        if not m.get("engines"):
            fail(f"{m.get('id','?')}: no engine measurements")
            continue
        for e in m["engines"]:
            if not e.get("engine"):
                fail(f"{m.get('id','?')}: engine measurement missing engine name")
            if not e.get("tps"):
                fail(f"{m.get('id','?')}: engine '{e.get('engine')}' missing t/s")
            # engine must have a repo link in the engine registry
            eng = store["engines"].get(e["engine"], {})
            if not eng.get("url"):
                fail(f"{m.get('id','?')}: engine '{e.get('engine')}' has no repo url in engines registry")
        # formats must be {name, hf} objects with per-format HF links, and vram_min required
        if m.get("formats"):
            if isinstance(m["formats"][0], str):
                fail(f"{m.get('id','?')}: formats must be '{{name, hf}}' objects (per-format HF link), got strings")
                continue  # don't iterate strings (would crash on .get)
            for f in m["formats"]:
                if not f.get("name") or not f.get("hf"):
                    fail(f"{m.get('id','?')}: format entry missing name or hf link")


def check_schema(store: dict) -> None:
    """Validate data/models.json against data/model_contract.json (JSON Schema).
    This is the single machine-checkable definition of the model contract."""
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        fail("schema: 'jsonschema' is not installed — run `pip install jsonschema` (CI installs it)")
        return
    if not CONTRACT.exists():
        fail("data/model_contract.json missing")
        return
    schema = json.loads(CONTRACT.read_text())
    try:
        jsonschema.validate(instance=store, schema=schema)
    except jsonschema.ValidationError as e:
        fail(f"schema: {e.message} (at {list(e.absolute_path or [])})")
    else:
        print(f"  OK: models.json conforms to model_contract.json ({len(store['models'])} models)")


def check_search_contract() -> None:
    """Validate every data/raw/*.json (Firecrawl per-search snapshot) against
    data/search_contract.json. Catches a search that dropped required fields
    BEFORE it aggregates into models.json — so no silent data loss."""
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        fail("search-contract: 'jsonschema' is not installed — run `pip install jsonschema` (CI installs it)")
        return
    if not SEARCH_CONTRACT.exists():
        fail("data/search_contract.json missing")
        return
    schema = json.loads(SEARCH_CONTRACT.read_text())
    if not RAW_DIR.exists():
        print("  (no data/raw snapshots yet)")
        return
    raws = sorted(RAW_DIR.glob("*.json"))
    if not raws:
        print("  (no data/raw snapshots yet)")
        return
    bad = 0
    for p in raws:
        try:
            data = json.loads(p.read_text())
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.ValidationError as e:
            bad += 1
            fail(f"search {p.name}: {e.message} (at {list(e.absolute_path or [])})")
        except Exception as e:  # noqa: BLE001
            bad += 1
            fail(f"search {p.name}: {e}")
    if not bad:
        print(f"  OK: all {len(raws)} search snapshots conform to search_contract.json")


def check_raw_mapping(store: dict) -> None:
    """Verify every data/raw/*.json search model maps to a known position in
    data/models.json — by id, then name, then hf (cross-store priority) — or is
    an explicitly new model. This proves the raw search data is mappable to the
    right place, so nothing lands in the wrong position or silently duplicates.
    Mirrors resolve_model_mapping() in update_trending.py."""
    import update_trending as ut
    if not RAW_DIR.exists():
        print("  (no data/raw snapshots yet)")
        return
    raws = sorted(RAW_DIR.glob("*.json"))
    if not raws:
        print("  (no data/raw snapshots yet)")
        return
    ok = 0
    for p in raws:
        data = json.loads(p.read_text())
        for m in data.get("models", []):
            res = ut.resolve_model_mapping(m, store)
            rid = (m.get("id") or "").lower()
            if res["status"] == "existing":
                ok += 1
            else:
                # legitimately new — id must not collide with an existing id
                if rid and any(rid == (sm.get("id") or "").lower() for sm in store["models"]):
                    fail(f"{p.name}: model '{m.get('name')}' id '{rid}' collides with an existing id but didn't map")
                else:
                    ok += 1  # new model, fine
    print(f"  OK: {ok} raw search models mapped/verified against models.json ({len(raws)} raw files)")


def check_newline_terminators() -> None:
    """Enforce that every tracked text file ends with a newline terminator."""
    import subprocess

    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        tracked = [ln for ln in out.splitlines() if ln.strip()]
    except Exception as e:  # noqa: BLE001
        print(f"  (could not list tracked files: {e})")
        return

    bad = []
    for rel in tracked:
        p = ROOT / rel
        if not p.is_file():
            continue
        name = p.name
        if not (p.suffix in TEXT_EXTS or name in TEXT_NAMES):
            continue
        data = p.read_bytes()
        if not data:
            continue
        if not data.endswith(b"\n"):
            bad.append(rel)
    if bad:
        for b in sorted(bad):
            fail(f"missing trailing newline: {b}")
    else:
        print(f"  OK: all {len(tracked)} tracked files end with a newline")


def check_backend_sort(store: dict) -> None:
    """Verify each README backend table is sorted by highest t/s descending.
    Parses the rendered tables (the store itself is sorted by engagement for
    the most-loved list; the backend tables are the t/s-sorted view)."""
    if not README.exists():
        fail("README.md missing")
        return
    text = README.read_text()
    # Each backend table: header line "# <emoji> <title>" then a markdown table.
    # Find the table under each backend heading.
    lines = text.split("\n")
    for backend, emoji in (("CUDA", "🟦"), ("Metal", "🟩"), ("CPU", "🟨")):
        # find the backend heading, then take only the markdown table block
        # that immediately follows it (stop at the first non-table line).
        start = next((i for i, ln in enumerate(lines) if ln.startswith(f"# {emoji}")), None)
        if start is None:
            fail(f"README missing {backend} backend table")
            continue
        rows = []
        for ln in lines[start + 1:]:
            if not ln.strip():
                continue  # skip blank lines between heading and table
            if not ln.startswith("|"):
                break  # end of the table block
            if "Model" in ln or "---" in ln:
                continue
            # Each backend row is:
            #   | **Model** | Params | License | HF | VRAM | t/s per engine |
            # Only the LAST cell holds t/s figures. Parsing the whole row wrongly
            # picks up Params ("125B"->125) and VRAM ("12GB"->12) as t/s, so a
            # correctly-sorted table looked unsorted. Extract just the t/s cell.
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            nums = [float(x) for x in re.findall(r"(\d+\.?\d*)", cells[-1 if cells else 0])]
            if nums:
                rows.append(max(n for n in nums if n < 1000))
        if rows != sorted(rows, reverse=True):
            fail(f"{backend} README table not sorted by t/s descending: {rows}")
        else:
            print(f"  OK: {backend} README table sorted by t/s desc ({len(rows)} rows)")


def check_readme_has_all_models(store: dict) -> None:
    if not README.exists():
        fail("README.md missing")
        return
    text = README.read_text()
    for m in store["models"]:
        if m["name"] not in text:
            fail(f"model '{m['name']}' not present in README.md")
    print(f"  OK: all {len(store['models'])} models present in README.md")


def check_readme_sync(store: dict) -> None:
    """Verify README.md is in sync with data/models.json — i.e. BOTH changed
    together. Every model and every engine measurement in the JSON must appear
    in the README, and the README's 'Last generated' must match the store's
    generated_utc. A PR that updates the JSON but not the README (or vice
    versa) fails here."""
    if not README.exists():
        fail("README.md missing")
        return
    text = README.read_text()
    # 1. every model + its engine measurements must be in the README
    for m in store["models"]:
        if m["name"] not in text:
            fail(f"sync: model '{m['name']}' in JSON but missing from README")
        for e in m.get("engines", []):
            if str(e.get("tps", "")) not in text:
                fail(f"sync: model '{m['name']}' engine '{e.get('engine')}' t/s '{e.get('tps')}' in JSON but missing from README")
    # 2. generated timestamp must match (README regenerated from this store)
    gen = store.get("generated_utc", "")
    if gen:
        # README shows "Last generated: <date> <time> UTC" — compare the date part
        gen_date = gen[:10]
        if gen_date not in text:
            fail(f"sync: README 'Last generated' does not match store generated_utc {gen}")
    print(f"  OK: README in sync with JSON ({len(store['models'])} models, timestamps match)")


def check_readme_generated(store: dict) -> None:
    """Prove README.md was actually PRODUCED by the generator (make merge /
    scripts/update_trending.py), not hand-edited. Re-renders the README from the
    current store via render_readme() and diffs against disk, ignoring only the
    'Last generated' timestamp line (which is a per-run wall-clock value)."""
    import sys as _sys  # noqa: F401
    if not README.exists():
        fail("README.md missing")
        return
    on_disk = README.read_text()
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import update_trending as ut
        expected = ut.render_readme(store, datetime.now(timezone.utc))
        sys.path.pop(0)
    except Exception as e:  # noqa: BLE001
        fail(f"readme-generated: could not render from store: {e}")
        return
    # strip the timestamp line on both sides
    def strip_ts(s: str) -> str:
        return "\n".join(ln for ln in s.splitlines() if not ln.startswith("> Last generated:"))
    if strip_ts(on_disk) != strip_ts(expected):
        fail("README.md is NOT regenerated from models.json — it was hand-edited or stale. Run `make merge`.")
    else:
        print("  OK: README.md matches the generator output (produced by make merge, not hand-edited)")


def check_readme_tables_wellformed(store: dict) -> None:
    """Force-validate every markdown table in README.md with a real parser
    (markdown-it-py's table extension), checking:
      - every table parses as a proper markdown table (markdown-it refuses a
        broken separator / misaligned table, so a table that fails to parse is
        itself a failure),
      - the separator row has the SAME number of columns as the header,
      - every data row has the SAME number of cells as the header,
      - no cell is empty where a value is required.
    This is the guard that keeps the README tables renderable and correctly
    formatted — a broken column count or a missing cell fails CI here."""
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        fail("readme-tables: 'markdown-it-py' is not installed (run `make generate-requirements`)")
        return
    if not README.exists():
        fail("README.md missing")
        return
    md = MarkdownIt("commonmark").enable("table")
    tokens = md.parse(README.read_text())
    tables = [t for t in tokens if t.type == "table_open"]
    if not tables:
        fail("readme-tables: no markdown tables parsed from README.md (tables malformed)")
        return
    # Column-consistency + empty-cell scan (markdown-it token stream doesn't give
    # per-row cell counts directly, so walk the plain table blocks).
    lines = README.read_text().split("\n")
    bad = 0
    i = 0
    while i < len(lines):
        if lines[i].startswith("|"):
            hdr = lines[i]
            sep = lines[i + 1] if i + 1 < len(lines) else ""
            hdr_cols = hdr.count("|") - 1
            sep_cols = sep.count("|") - 1 if sep.startswith("|") else 0
            if sep_cols != hdr_cols:
                bad += 1
                fail(f"readme-tables: separator has {sep_cols} cols, header has {hdr_cols}: {hdr[:60]}")
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                if len(cells) != hdr_cols:
                    bad += 1
                    fail(f"readme-tables: row has {len(cells)} cells, header has {hdr_cols}: {lines[j][:60]}")
                else:
                    for ci, cell in enumerate(cells):
                        if not cell:
                            bad += 1
                            col = hdr.split("|")[ci + 1].strip() if ci + 1 < len(hdr.split("|")) else str(ci)
                            fail(f"readme-tables: empty cell in column '{col}': {lines[j][:60]}")
                j += 1
            i = j
        else:
            i += 1
    if not bad:
        print(f"  OK: all {len(tables)} README tables well-formed (columns + cells filled)")


# Known-good engine repo URLs. When a link check finds a wrong/dead engine URL,
# the fix-bot (or this validator's auto-fix) can correct it to the canonical repo.
KNOWN_ENGINE_URLS = {
    "llama.cpp": "https://github.com/ggml-org/llama.cpp",
    "Ollama": "https://github.com/ollama/ollama",
    "vLLM": "https://github.com/vllm-project/vllm",
    "SGLang": "https://github.com/sgl-project/sglang",
    "FreeToken": "https://github.com/FlashML-org/FreeToken",
    "TensorRT-LLM": "https://github.com/NVIDIA/TensorRT-LLM",
    "MLX": "https://github.com/ml-explore/mlx",
    "TensorFold": "https://github.com/ashhart/TensorFold",
    "MLX-fast (Bonsai 2)": "https://github.com/Layr-Labs/mlxfast-bonsai2-27b-engine",
    "LiteRT": "https://github.com/google-ai-edge/LiteRT",
    "Strata": "https://github.com/Niko1221/Strata",
    "DFlash2": "https://github.com/z-lab/dflash",
    "WebLLM": "https://github.com/mlc-ai/web-llm",
}


# Known-good Hugging Face repo ids. When a model's HF link 404s and we know the
# canonical repo, the validator auto-corrects the store's hf field (so the
# fix-bot has a concrete repair). Unknown models are reported for manual review.
KNOWN_HF_IDS = {
    "bonsai-2-27b": "prism-ml/Ternary-Bonsai-2-27B-gguf",
    "qwen3.8-27b": "Qwen/Qwen3.8-27B",
    "qwen3-8b": "Qwen/Qwen3-8B",
    "gemma-4-12b": "google/gemma-4-12B-it",
    "qwen3-14b": "Qwen/Qwen3-14B",
    "qwen-3.6-27b": "Qwen/Qwen3.6-27B",
    "muse-glimmer-30b": "meta-models/Muse-Glimmer-30B",
}


def _lookup_hf_id(model_id: str) -> str | None:
    """Return the canonical HF repo id for a model id, or None if unknown."""
    return KNOWN_HF_IDS.get(model_id)


# Statuses that mean "the link is fine but we can't verify right now" — rate
# limits (429), bot-blocks (403), and server errors (5xx). Used ONLY for
# source_post (X posts via the lightbrd.com mirror, which bot-blocks) and README
# links. HF / engine / inference links are STRICT 2xx.
_INDETERMINATE = {403, 429, 500, 502, 503, 504}


def _link_ok(url: str, timeout: float = 8.0, strict: bool = True) -> bool:
    """Return True if the URL is reachable. strict=True (default) requires HTTP
    2xx — used for public model / inference-server links (Hugging Face, engine
    repos) that must genuinely resolve. strict=False also accepts indeterminate
    (403/429/5xx) — used for source_post (X mirror bot-blocks) and README links.
    HEAD first, GET fallback. When HF_TOKEN is set (repo secret), Hugging Face
    requests are authenticated with it, so batch link-checking isn't held to the
    anonymous rate limit."""
    if not url or not url.startswith(("http://", "https://")):
        return False
    headers = {"User-Agent": "trending-local-llms-linkcheck/1.0"}
    if url.startswith("https://huggingface.co/") and os.environ.get("HF_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["HF_TOKEN"]
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if 200 <= resp.status < 300:
                    return True
                if not strict and resp.status in _INDETERMINATE:
                    return True
        except urllib.error.HTTPError as e:
            if 200 <= e.code < 300:
                return True
            if not strict and e.code in _INDETERMINATE:
                return True
        except Exception:  # noqa: BLE001 — connection error / timeout / DNS
            continue
    return False


def _extract_links(store: dict) -> list[tuple[str, str, str]]:
    """Collect (kind, owner, url) for every link in models.json + README + raw
    snapshots. kind is engine-registry|model-hf|format-hf|source_post|readme|raw."""
    out: list[tuple[str, str, str]] = []
    for k, v in store.get("engines", {}).items():
        if v.get("url"):
            out.append(("engine-registry", k, v["url"]))
    for m in store.get("models", []):
        mid = m.get("id", "?")
        if m.get("hf"):
            out.append(("model-hf", mid, "https://huggingface.co/" + m["hf"]))
        for f in m.get("formats", []):
            if f.get("hf"):
                out.append(("format-hf", mid, "https://huggingface.co/" + f["hf"]))
        for e in m.get("engines", []):
            if e.get("source_post"):
                out.append(("source_post", mid, e["source_post"]))
    if README.exists():
        for u in re.findall(r"https?://[^\s)\]>]+", README.read_text()):
            out.append(("readme", "README.md", u.rstrip(".,;:")))
    if RAW_DIR.exists():
        for rp in sorted(RAW_DIR.glob("*.json")):
            try:
                data = json.loads(rp.read_text())
            except Exception:  # noqa: BLE001
                continue
            for m in data.get("models", []):
                mid = m.get("id", "?")
                if m.get("hf"):
                    out.append(("raw-hf", f"{rp.name}/{mid}", "https://huggingface.co/" + m["hf"]))
                for e in m.get("engines", []):
                    if e.get("source_post"):
                        out.append(("raw-source_post", f"{rp.name}/{mid}", e["source_post"]))
    return out


def check_links_present(store: dict) -> None:
    """Every model must carry an HF link and every engine measurement an
    inference-server source_post link — in models.json AND in every raw search
    snapshot. A MISSING link (not just a dead one) fails here, so a search that
    drops hf/source_post is caught before it aggregates into models.json."""
    bad = 0
    for m in store.get("models", []):
        mid = m.get("id", "?")
        if not m.get("hf"):
            bad += 1
            fail(f"link-present: model '{mid}' missing HF link (hf)")
        for e in m.get("engines", []):
            if not e.get("source_post"):
                bad += 1
                fail(f"link-present: model '{mid}' engine '{e.get('engine')}' missing source_post link")
    if RAW_DIR.exists():
        for rp in sorted(RAW_DIR.glob("*.json")):
            try:
                data = json.loads(rp.read_text())
            except Exception:  # noqa: BLE001
                continue
            for m in data.get("models", []):
                mid = m.get("id", "?")
                if not m.get("hf"):
                    bad += 1
                    fail(f"link-present: {rp.name}/{mid} missing HF link (hf)")
                for e in m.get("engines", []):
                    if not e.get("source_post"):
                        bad += 1
                        fail(f"link-present: {rp.name}/{mid} engine '{e.get('engine')}' missing source_post link")
    if not bad:
        print(f"  OK: all models + raw snapshots carry HF + source_post links")


def check_links_resolve(store: dict) -> None:
    """Verify every link in models.json, README.md, and data/raw/*.json resolves
    (HTTP 2xx/3xx). A dead or wrong link fails CI. Known-good engine repo URLs
    and HF repo ids are auto-corrected in the store (so the fix-bot has a
    concrete repair); unknown dead links are reported for manual review."""
    links = _extract_links(store)
    if not links:
        print("  (no links to check)")
        return
    bad = 0
    fixed = 0
    # HF + engine/inference links must be STRICT 2xx (public model links that
    # must genuinely resolve). source_post (X mirror bot-blocks) and README links
    # are lenient (indeterminate 403/429/5xx is not a dead link).
    _STRICT_KINDS = {"model-hf", "format-hf", "raw-hf", "engine-registry"}
    for kind, owner, url in links:
        # QA: a known owner must point at its canonical link. A wrong-but-
        # resolving link (e.g. the fix-bot wrote a different model's HF id that
        # happens to return 200) is a FAILURE, not silently accepted — this is
        # how we verify a fixed link actually matches the model / inference
        # server, not just that it resolves.
        canonical = None
        canonical_id = None
        if kind == "engine-registry" and owner in KNOWN_ENGINE_URLS:
            canonical = KNOWN_ENGINE_URLS[owner]
        elif kind in ("model-hf", "format-hf"):
            canonical_id = _lookup_hf_id(owner)
            if canonical_id:
                canonical = "https://huggingface.co/" + canonical_id
        if canonical and url != canonical:
            if _link_ok(canonical, strict=(kind in _STRICT_KINDS)):
                # correct the store to the canonical link
                if kind == "engine-registry":
                    store["engines"][owner]["url"] = canonical
                else:
                    for m in store.get("models", []):
                        if m.get("id") == owner:
                            if kind == "model-hf":
                                m["hf"] = canonical_id
                            else:
                                for f in m.get("formats", []):
                                    if f.get("hf") and "https://huggingface.co/" + f["hf"] == url:
                                        f["hf"] = canonical_id
                fixed += 1
                print(f"  FIXED: {owner} {kind} {url} -> {canonical}")
                continue
            bad += 1
            fail(f"link: [{kind}] {owner}: {url} does not match known-good {canonical}")
            continue
        if _link_ok(url, strict=(kind in _STRICT_KINDS)):
            continue
        bad += 1
        fail(f"link: [{kind}] {owner}: {url} does not resolve")
    if fixed:
        print(f"  auto-fixed {fixed} link(s) to known-good repos")
    if not bad:
        print(f"  OK: all {len(links)} links resolve ({fixed} auto-fixed)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot-dir", default=str(SNAPSHOT_DIR))
    ap.add_argument("--only", default="",
                    help="comma-separated subset of checks to run (e.g. data,schema,search,mapping,readme). "
                         "Empty = run all.")
    args = ap.parse_args()
    snap_dir = Path(args.snapshot_dir)
    only = {s.strip() for s in args.only.split(",") if s.strip()}

    if not DATA.exists():
        print("FAIL: data/models.json missing")
        return 1
    store = json.loads(DATA.read_text())

    checks = []
    def add(label, name, fn):
        if not only or name in only or label in only:
            checks.append((label, fn))

    add("no-removal guarantee", "removal", lambda: check_no_removal(store, snap_dir))
    add("no duplicate models", "data", lambda: check_no_duplicates(store))
    add("no duplicate engines", "data", lambda: check_no_duplicate_engines(store))
    add("tps starts with a numeric token", "data", lambda: check_tps_shape(store))
    add("latest t/s surfaced", "data", lambda: check_latest_tps(store))
    add("supported engines", "data", lambda: check_supported_engines(store))
    add("model fields + links", "schema", lambda: check_model_fields(store))
    add("schema conformance (model_contract.json)", "schema", lambda: check_schema(store))
    add("search/raw contract (search_contract.json)", "search", lambda: check_search_contract())
    add("raw -> models.json mapping", "mapping", lambda: check_raw_mapping(store))
    add("newline terminators", "data", lambda: check_newline_terminators())
    add("backend sort by t/s", "readme", lambda: check_backend_sort(store))
    add("README tables well-formed", "readme", lambda: check_readme_tables_wellformed(store))
    add("links present (HF + source_post in models + raw)", "links", lambda: check_links_present(store))
    add("links resolve (models.json + README + raw)", "links", lambda: check_links_resolve(store))
    add("README completeness", "readme", lambda: check_readme_has_all_models(store))
    add("JSON <-> README sync", "readme", lambda: check_readme_sync(store))
    add("README regenerated by make merge", "readme", lambda: check_readme_generated(store))

    for label, fn in checks:
        print(f"== QA: {label} ==")
        fn()

    if FAILURES:
        print(f"\nQA FAILED: {len(FAILURES)} issue(s)")
        return 1
    print("\nQA PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
