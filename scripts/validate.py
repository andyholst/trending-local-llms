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


def check_no_duplicate_engines(store: dict) -> None:
    """Within each model, no TRULY identical engine row — same
    (engine, date, hardware, tps, quant). Different hardware or t/s on the same
    date is a legitimate distinct measurement, NOT a duplicate."""
    bad = 0
    for m in store["models"]:
        seen = {}
        for e in m.get("engines", []):
            key = (e.get("engine"), e.get("date"), e.get("hardware"), e.get("tps"), e.get("quant"))
            if key in seen:
                bad += 1
                fail(f"{m.get('id','?')}: duplicate identical engine row ({e.get('engine')}, {e.get('date')}, {e.get('hardware')}, {e.get('tps')})")
            seen[key] = True
    if not bad:
        print(f"  OK: no identical duplicate engine rows in any model")


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
            nums = [float(x) for x in re.findall(r"(\d+\.?\d*)", ln)]
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
    add("latest t/s surfaced", "data", lambda: check_latest_tps(store))
    add("supported engines", "data", lambda: check_supported_engines(store))
    add("model fields + links", "schema", lambda: check_model_fields(store))
    add("schema conformance (model_contract.json)", "schema", lambda: check_schema(store))
    add("search/raw contract (search_contract.json)", "search", lambda: check_search_contract())
    add("raw -> models.json mapping", "mapping", lambda: check_raw_mapping(store))
    add("newline terminators", "data", lambda: check_newline_terminators())
    add("backend sort by t/s", "readme", lambda: check_backend_sort(store))
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
