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


def _hermes_prompt_ok(line: str) -> tuple[bool, str]:
    """Validate a make-recipe `hermes -z "..."` line: the prompt body between the
    -z double-quotes must contain only BACKSLASH-escaped quotes (the JSON `\\"`),
    never an unescaped `"` — an unescaped quote closes the -z string early and
    turns the rest of the prompt into stray args (hermes errors out). The line
    must also END with a `\\` continuation: without it make runs the next recipe
    line (`-m <alias> --yolo`) as a SEPARATE command, so hermes starts with no
    model alias and auto-picks whatever provider key is in the env (HF_TOKEN ->
    Hugging Face 403). This is a dry-run guard: validate the prompt shell string
    BEFORE the hermes LLM call."""
    import re as _re
    line = line.lstrip()
    m = _re.match(r'hermes\s+[^"]*?"(.*)"\s*\\?\s*$', line, _re.DOTALL)
    if not m:
        return False, "no hermes -z \"...\" form"
    if not line.rstrip().endswith("\\"):
        return False, "missing trailing \\ continuation (the -m <alias> line would run as a separate command)"
    body = m.group(1)
    for i, ch in enumerate(body):
        if ch == '"' and not (i > 0 and body[i - 1] == "\\"):
            return False, f"unescaped quote in prompt body at offset {i}"
    return True, ""


def check_hermes_prompts() -> None:
    """Validate every `hermes -z "..."` prompt in the Makefile (the 4 search +
    fix-bot prompts). A prompt whose -z body has an unescaped quote breaks the
    shell command (hermes errors: '... is not a hermes command') and silently
    kills every search. Dry-run the prompt strings before they reach the LLM."""
    import re as _re
    makefile = ROOT / "Makefile"
    if not makefile.exists():
        fail("hermes-prompts: Makefile missing")
        return
    bad = 0
    prompts = 0
    for line in makefile.read_text().splitlines():
        if not _re.match(r"\t?hermes -z", line):
            continue
        prompts += 1
        ok, why = _hermes_prompt_ok(line)
        if not ok:
            bad += 1
            fail(f"hermes-prompts: bad prompt: {why}: {line.strip()[:60]}...")
    if not bad:
        print(f"  OK: all {prompts} hermes -z prompts are valid shell strings (dry-run)")


# A t/s value must be a CLEAN number: optional estimate tilde, a number, an
# optional range, and an optional "(est)" suffix — NOTHING ELSE. Any embedded
# text (comments, "decode", "DFlash spec-decode") is INVALID: t/s is a numeric
# measurement, and the descriptive context belongs in quant/hardware/note, not
# in the tps string. Valid: 39.3, ~50, 67-71, 35.5-43.7, 99.7, 22 (est). Invalid:
# '233 (DFlash spec-decode), 74.9 stock', '~237 decode', '~38 (1 user)',
# 'a few (est)', '52-60 output / 1250 prompt'.
_TPS_CLEAN = re.compile(r"^~?\s?\d+(?:\.\d+)?(?:-\d+(?:\.\d+)?)?(?:\s*\(est\))?$")


def check_tps_shape(store: dict) -> None:
    """Every engine t/s must be a CLEAN numeric value (optional '~', int/float,
    optional range, optional '(est)' suffix) with NO embedded text. Rejects a
    search that wrote a numeric placeholder mixed with prose or comments —
    t/s is a measurement, context belongs in quant/hardware/note."""
    bad = 0
    for m in store["models"]:
        for e in m.get("engines", []):
            t = e.get("tps", "")
            if t and not _TPS_CLEAN.match(t.strip()):
                bad += 1
                fail(f"{m.get('id','?')}: engine '{e.get('engine')}' tps is not a clean number: {t!r}")
    if not bad:
        print("  OK: all engine tps are clean numeric values")


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


def check_engine_kind(store: dict) -> None:
    """Only INFERENCE ENGINES belong in the registry. Fails an entry whose url
    or name is a known non-engine (scripts/engine_registry.NON_ENGINE_REPOS /
    NON_ENGINE_NAMES — e.g. deepseek-ai/deepseek-harness, an agent harness that
    fix-bot registered as a CPU engine on refresh PR #72), and an auto-registered
    entry (auto: true) whose note doesn't cite where it came from."""
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import engine_registry as er
    finally:
        sys.path.pop(0)
    bad = 0
    for name, v in store.get("engines", {}).items():
        slug = er.repo_slug(v.get("url", ""))
        if slug in er.NON_ENGINE_REPOS or re.sub(r"[^a-z0-9]", "", name.lower()) in er.NON_ENGINE_NAMES:
            bad += 1
            fail(f"engine-kind: '{name}' ({v.get('url')}) is not an inference engine (harness/app/benchmark) — "
                 f"do not register it; record the runtime the post actually used")
        if v.get("auto") and "Auto-registered" not in (v.get("note") or ""):
            bad += 1
            fail(f"engine-kind: auto-registered '{name}' must cite its source in the note")
    if not bad:
        print(f"  OK: all {len(store.get('engines', {}))} registered engines are inference engines")


def check_engine_aliases(store: dict) -> None:
    """A model's engine_aliases ({posted name: registry name}) must point at a
    registered engine with a known-good repo URL, and NO measurement or
    supported engine on that model may still carry the aliased-away name —
    otherwise the README links the stock engine for a model that needs a fork
    (Bonsai 2 'llama.cpp' figures linked to ggml-org/llama.cpp, which rejects
    its PTQ1_0/PQ2_0 files)."""
    reg = store.get("engines", {})
    bad = 0
    for m in store.get("models", []):
        for src, dst in (m.get("engine_aliases") or {}).items():
            if dst not in reg or not reg[dst].get("url"):
                bad += 1
                fail(f"{m.get('id','?')}: engine alias '{src}' -> '{dst}' is not a registered engine with a url")
            elif KNOWN_ENGINE_URLS.get(dst) and reg[dst]["url"] != KNOWN_ENGINE_URLS[dst]:
                bad += 1
                fail(f"{m.get('id','?')}: alias target '{dst}' url {reg[dst]['url']} != known-good {KNOWN_ENGINE_URLS[dst]}")
            left = [e.get("tps") for e in m.get("engines", []) if e.get("engine") == src]
            if left or src in (m.get("supported_engines") or []):
                bad += 1
                fail(f"{m.get('id','?')}: engine '{src}' should be '{dst}' (engine_aliases) but still appears: {left}")
    if not bad:
        print("  OK: engine aliases resolve to registered forks; no aliased-away engine left")


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
        peak_col = None
        for ln in lines[start + 1:]:
            if not ln.strip():
                continue  # skip blank lines between heading and table
            if not ln.startswith("|"):
                break  # end of the table block
            if "---" in ln:
                continue
            cells = [c.strip() for c in _split_row(ln)]
            if cells and cells[0] == "Model":
                # Current layout has a dedicated numeric 'Peak t/s' column: read
                # it BY HEADER NAME, so hardware text in the measurements cell
                # ('RTX 5090') can never be read as t/s.
                peak_col = cells.index("Peak t/s") if "Peak t/s" in cells else None
                continue
            if peak_col is not None and peak_col < len(cells):
                nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", cells[peak_col])]
                if nums:
                    rows.append(max(nums))
                continue
            # Legacy layout: only the LAST cell holds t/s figures. Parsing the
            # whole row picks up Params ("125B"->125) and VRAM ("12GB"->12).
            cell = cells[-1] if cells else ""
            # The last cell is "engine tps (YYYY-MM-DD); engine tps (date); ...".
            # Strip the embedded dates FIRST so the YEAR (2026) is not counted as
            # t/s, then take the max tps WITHOUT any <1000 bound — a legitimate
            # 1000+ t/s (e.g. spec-decode 1250) must count.
            # Drop markdown link TARGETS first: an engine repo URL carries
            # digits (github.com/Niko1221/Strata -> 1221 read as t/s, which
            # flagged a correctly-sorted refresh PR as unsorted).
            cell = re.sub(r"\]\([^)]*\)", "]", cell)
            no_dates = re.sub(r"\(\d{4}-\d{2}-\d{2}\)", "", cell)
            nums = [float(x) for x in re.findall(r"(\d+\.?\d*)", no_dates)]
            if nums:
                rows.append(max(nums))
        if rows != sorted(rows, reverse=True):
            fail(f"{backend} README table not sorted by t/s descending: {rows}")
        else:
            print(f"  OK: {backend} README table sorted by t/s desc ({len(rows)} rows)")


def _split_row(line: str) -> list[str]:
    """Split a markdown table row on unescaped pipes."""
    return re.split(r"(?<!\\)\|", line.strip().strip("|"))


def _readme_sections(text: str) -> dict[str, list[str]]:
    """Map each top-level backend heading / the most-loved heading to the table
    rows that follow it."""
    sections: dict[str, list[str]] = {}
    cur = None
    for ln in text.split("\n"):
        if ln.startswith("# 🟦"):
            cur = "CUDA"
        elif ln.startswith("# 🟩"):
            cur = "Metal"
        elif ln.startswith("# 🟨"):
            cur = "CPU"
        elif ln.startswith("## ❤️"):
            cur = "loved"
        elif ln.startswith("#"):
            cur = None
        elif cur and ln.startswith("|") and "---" not in ln:
            sections.setdefault(cur, []).append(ln)
    return sections


def check_readme_measurements(store: dict) -> None:
    """Every engine measurement appears in ITS OWN backend table (the one
    update_trending.measurement_backend assigns), in its model's row, with its
    engine name and its exact t/s in bold — and the most-loved row shows the
    true best t/s for each backend. A substring check ('50' anywhere in the
    README) let a measurement rendered in the wrong table, or dropped, pass."""
    if not README.exists():
        fail("README.md missing")
        return
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import update_trending as ut
    finally:
        sys.path.pop(0)
    sec = _readme_sections(README.read_text())
    bad = 0

    def row_for(rows: list[str], name: str) -> str:
        return next((r for r in rows if f"**{name}**" in _split_row(r)[0]), "")

    for m in store["models"]:
        for e in m.get("engines", []):
            b = ut.measurement_backend(e, store.get("engines", {}))
            row = row_for(sec.get(b, []), m["name"])
            if not row:
                bad += 1
                fail(f"readme-measurements: {m['name']} has a {b} measurement but no row in the {b} table")
                continue
            if f"**{e.get('tps')}**" not in row or e.get("engine", "") not in row:
                bad += 1
                fail(f"readme-measurements: {m['name']} {e.get('engine')} {e.get('tps')} t/s missing from its {b} row")
        loved = row_for(sec.get("loved", []), m["name"])
        if not loved:
            bad += 1
            fail(f"readme-measurements: {m['name']} missing from the most-loved table")
            continue
        cells = _split_row(loved)
        for idx, b in ((3, "CUDA"), (4, "Metal"), (5, "CPU")):
            best = ut.best_measurement([e for e in m.get("engines", []) if ut.measurement_backend(e, store.get("engines", {})) == b])
            cell = cells[idx].strip() if idx < len(cells) else ""
            want = f"**{best['tps']}**" if best else "—"
            if not cell.startswith(want):
                bad += 1
                fail(f"readme-measurements: most-loved {b} cell for {m['name']} should start with {want!r}, got {cell[:40]!r}")
    if not bad:
        print("  OK: every measurement is in its own backend row; most-loved shows the best per backend")


def _as_of(store: dict) -> datetime:
    gen = store.get("generated_utc", "")
    try:
        return datetime.strptime(gen, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def check_readme_engine_links(store: dict) -> None:
    """Every engine linked in README.md points at that engine's registry URL,
    and every registry URL for a known engine is its known-good repo. Guards
    the Bonsai 2 case (a figure linked to stock llama.cpp instead of the
    PrismML fork) and any renderer change that links the wrong repo."""
    if not README.exists():
        fail("README.md missing")
        return
    reg = store.get("engines", {})
    bad = 0
    for name, url in re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", README.read_text()):
        if name in reg and reg[name].get("url") != url:
            bad += 1
            fail(f"readme-engine-links: [{name}] links {url}, registry says {reg[name].get('url')}")
    for name, v in reg.items():
        if KNOWN_ENGINE_URLS.get(name) and v.get("url") != KNOWN_ENGINE_URLS[name]:
            bad += 1
            fail(f"readme-engine-links: registry {name} url {v.get('url')} != known-good {KNOWN_ENGINE_URLS[name]}")
    if not bad:
        print("  OK: every README engine link matches the registry and the known-good repo")


def check_readme_ranking(store: dict) -> None:
    """The most-loved table must be in EXACTLY the trend order the store sorts
    to (band -> trend_score -> posts_7d -> peak t/s -> name, as of
    generated_utc), and each Trend cell must show that model's trend_score and
    post count. Catches a renderer that orders by something else, a hand
    reorder, or a displayed score that isn't the one used to rank."""
    if not README.exists():
        fail("README.md missing")
        return
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import update_trending as ut
    finally:
        sys.path.pop(0)
    models = ut.sort_models(json.loads(json.dumps(store.get("models", []))), _as_of(store))
    rows = [r for r in _readme_sections(README.read_text()).get("loved", [])
            if not _split_row(r)[0].strip().startswith("Model")]
    names = [re.sub(r"^\[\*\*(.*?)\*\*\].*$", r"\1", _split_row(r)[0].strip()) for r in rows]
    want = [m["name"] for m in models]
    bad = 0
    if names != want:
        bad += 1
        fail(f"readme-ranking: most-loved order {names} != trend order {want}")
    for m, r in zip(models, rows):
        cells = _split_row(r)
        cell = cells[2].strip() if len(cells) > 2 else ""
        eng = m.get("engagement", {})
        score = f"**{ut._fmt_num(eng.get('trend_score', 0))}**"
        posts = eng.get("posts_7d", 0)
        if not cell.startswith(score) or (posts and f"{posts} post" not in cell):
            bad += 1
            fail(f"readme-ranking: {m['name']} Trend cell should show {score} and {posts} post(s), got {cell[:60]!r}")
    if not bad:
        print(f"  OK: most-loved table is in trend order; {len(rows)} Trend cells match the store")


def post_signal_coverage(models: list[dict]) -> tuple[int, int, int]:
    """(measurements, with a real …/status/<id> source_post, with any engagement count)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import update_trending as ut
    finally:
        sys.path.pop(0)
    total = real = counted = 0
    for m in models:
        for e in m.get("engines", []):
            total += 1
            real += bool(ut._is_post_url(e.get("source_post", "")))
            counted += any(int(float(e.get(k) or 0)) > 0 for k in ("likes", "comments", "reshares", "views"))
    return total, real, counted


def check_post_signal(store: dict) -> None:
    """REPORT ONLY (never fails): how much of the engagement ranking rests on
    real per-post data. A measurement whose source_post is a placeholder
    (https://lightbrd.com/, a profile page) or that carries no counts scores the
    minimum 1 in score_7d, so low coverage means the rank is close to a plain
    post count. Old data is legitimately placeholder-only, hence a warning."""
    def line(label, models):
        total, real, counted = post_signal_coverage(models)
        if not total:
            return
        pct = lambda n: f"{100 * n / total:.0f}%"
        flag = "OK" if real == total and counted == total else "WARN"
        print(f"  {flag}: post-signal {label}: {real}/{total} ({pct(real)}) real post URLs, "
              f"{counted}/{total} ({pct(counted)}) with engagement counts")
    line("store", store.get("models", []))
    if RAW_DIR.exists():
        for f in sorted(RAW_DIR.glob("*.json")):
            try:
                line(f"raw/{f.name}", json.loads(f.read_text()).get("models", []))
            except Exception as e:  # noqa: BLE001
                print(f"  WARN: post-signal raw/{f.name}: unreadable ({e})")


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
        # Render as of the store's own generation time: status bands and the
        # 7-day score are date-relative, so re-rendering with the wall clock
        # would flag a correct README as stale a few days after it merged.
        as_of = datetime.now(timezone.utc)
        gen = store.get("generated_utc", "")
        if gen:
            try:
                as_of = datetime.strptime(gen, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        expected = ut.render_readme(json.loads(json.dumps(store)), as_of)
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
            # split on UNESCAPED pipes only: GFM renders '\|' as a literal pipe
            hdr_cols = len(_split_row(hdr))
            sep_cols = len(_split_row(sep)) if sep.startswith("|") else 0
            if sep_cols != hdr_cols:
                bad += 1
                fail(f"readme-tables: separator has {sep_cols} cols, header has {hdr_cols}: {hdr[:60]}")
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                cells = [c.strip() for c in _split_row(lines[j])]
                if len(cells) != hdr_cols:
                    bad += 1
                    fail(f"readme-tables: row has {len(cells)} cells, header has {hdr_cols}: {lines[j][:60]}")
                else:
                    for ci, cell in enumerate(cells):
                        if not cell:
                            bad += 1
                            hcells = _split_row(hdr)
                            col = hcells[ci].strip() if ci < len(hcells) else str(ci)
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
    "llama.cpp (PrismML fork)": "https://github.com/PrismML-Eng/llama.cpp",
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
    add("hermes prompts are valid shell (dry-run)", "data", lambda: check_hermes_prompts())
    add("latest t/s surfaced", "data", lambda: check_latest_tps(store))
    add("supported engines", "data", lambda: check_supported_engines(store))
    add("engine aliases (model-specific forks)", "data", lambda: check_engine_aliases(store))
    add("registry holds only inference engines", "data", lambda: check_engine_kind(store))
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
    add("measurements in their backend rows", "readme", lambda: check_readme_measurements(store))
    add("post-signal coverage (report only)", "data", lambda: check_post_signal(store))
    add("most-loved in trend order", "readme", lambda: check_readme_ranking(store))
    add("README engine links", "readme", lambda: check_readme_engine_links(store))
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
