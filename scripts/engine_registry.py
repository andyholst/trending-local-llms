#!/usr/bin/env python3
"""Engine registry: classify + auto-register new inference engines at ingest.

A search that finds a measurement on an engine missing from the registry used
to fail only at PR CI ("engine 'X' has no repo url in engines registry") and
cost a fix-bot LLM round that repeated the search — and nothing stopped a
harness / agent framework / app from being registered as an inference engine
(refresh PR #72: 'DeepSeekHarness' -> deepseek-ai/deepseek-harness, "Everything
is a Plugin", an agent harness).

Now the search agent records the engine's GitHub repo as `engine_repo` on the
measurement, and at ingest:
  - classify_repo(meta) -> ("engine" | "not-engine" | "unknown", reason) from
    the GitHub repo's description, topics and name. A not-engine signal always
    wins over an engine signal.
  - register_new_engines() registers a NEW engine only when its engine_repo is
    a reachable github.com repo classified "engine" (backend inferred from its
    measurements, note cites the source post, auto=true). "not-engine" and
    "unknown" are NEVER registered: validation keeps failing and a human /
    fix-bot decides.
  - engine_repo is stripped from measurements (the store contract never sees it).

CLI (report only, never fails):
  python3 scripts/engine_registry.py --check-raw data/raw   # unregistered engines in raw snapshots
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Known NOT-inference-engine repos / names. The validator (check_engine_kind)
# fails a registry entry that matches; extend when one slips through.
NON_ENGINE_REPOS = {
    "deepseek-ai/deepseek-harness",
}
NON_ENGINE_NAMES = {
    "deepseekharness",
}

# STRONG not-engine signals always win: these repos are never inference
# engines even when they mention one ("chat UI that supports llama.cpp").
_NOT_ENGINE = re.compile(
    r"\b(harness|agent(?:ic)? framework|agents? sdk|agent platform|plugins?|plug-ins?|chat ?ui|web ?ui|"
    r"frontend|front-end|desktop app|mobile app|chat app|chatbot app|benchmark(?:ing)? suite|benchmarks for|"
    r"leaderboard|eval(?:uation)? (?:framework|harness|suite)|prompt library|awesome list|dataset)\b", re.I)
# WEAK not-engine signal: a bare 'benchmark' only counts when there is no
# engine signal — 'MLX inference speedup benchmark engine' (MLX-fast Bonsai 2,
# a registered engine) is an engine.
_WEAK_NOT_ENGINE = re.compile(r"\bbenchmark(?:s|ing)?\b", re.I)
_ENGINE = re.compile(
    r"\b(inference (?:engine|server|runtime|framework|library)|llm (?:inference|serving|runtime|engine)|"
    r"serving (?:engine|framework|system)|model serving|runtime for (?:llms?|language models)|"
    r"gguf|ggml|llama\.cpp|bitnet|cuda kernels?|metal kernels?|quantized inference|"
    r"speculative decoding|token(?:s)? per second|tensorrt|mlx|onnx runtime|vllm|sglang)\b", re.I)


def repo_slug(url: str) -> str | None:
    """'https://github.com/Owner/Repo(.git)(/...)' -> 'owner/repo' (lowercase); else None."""
    m = re.match(r"^https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:[/?#].*)?$",
                 (url or "").strip())
    return f"{m.group(1)}/{m.group(2)}".lower() if m else None


def classify_repo(meta: dict | None, name: str = "") -> tuple[str, str]:
    """Decide whether a GitHub repo is an inference engine.
    `meta` is the GitHub repo JSON (full_name, description, topics) or None."""
    if not meta:
        return "unknown", "no repo metadata"
    slug = (meta.get("full_name") or "").lower()
    if slug in NON_ENGINE_REPOS or re.sub(r"[^a-z0-9]", "", name.lower()) in NON_ENGINE_NAMES:
        return "not-engine", "listed in NON_ENGINE_REPOS / NON_ENGINE_NAMES"
    text = " ".join([meta.get("full_name") or "", meta.get("description") or "",
                     " ".join(t.replace("-", " ") for t in (meta.get("topics") or []))])
    neg = _NOT_ENGINE.search(text)
    if neg:
        return "not-engine", f"repo describes a {neg.group(0).lower()!r}, not an inference engine"
    pos = _ENGINE.search(text)
    if pos:
        return "engine", f"repo describes {pos.group(0).lower()!r}"
    weak = _WEAK_NOT_ENGINE.search(text)
    if weak:
        return "not-engine", f"repo describes a {weak.group(0).lower()!r} and no inference engine"
    return "unknown", "no inference-engine signal in description/topics"


# Registry key pattern — single source: data/model_contract.json propertyNames.
def _registry_name_pattern() -> re.Pattern:
    try:
        c = json.loads((ROOT / "data" / "model_contract.json").read_text())
        return re.compile(c["properties"]["engines"]["propertyNames"]["pattern"])
    except Exception:  # noqa: BLE001
        return re.compile(r"^[A-Za-z0-9 ._()-]+$")


def fetch_repo_meta(url: str) -> dict | None:
    """GitHub repo metadata for a github.com URL, or None (not GitHub / 404 /
    error). Offline mode: ENGINE_REGISTRY_META_FILE points at a JSON
    {"repos": {"owner/repo": meta}} cache (tests and dry runs)."""
    slug = repo_slug(url)
    if not slug:
        return None
    cache = os.environ.get("ENGINE_REGISTRY_META_FILE")
    if cache:
        repos = {k.lower(): v for k, v in json.loads(Path(cache).read_text()).get("repos", {}).items()}
        return repos.get(slug)
    req = urllib.request.Request(f"https://api.github.com/repos/{slug}",
                                 headers={"Accept": "application/vnd.github+json",
                                          "User-Agent": "trending-local-llms-engine-registry"})
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def _infer_backend(measurements: list[dict]) -> str:
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import update_trending as ut
    finally:
        sys.path.pop(0)
    seen = []
    for e in measurements:
        b = ut.measurement_backend(e)
        if b not in seen:
            seen.append(b)
    if len(seen) == 1:
        return seen[0]
    if set(seen) <= {"CUDA", "Metal"}:
        return "CUDA / Metal"
    return "CUDA / CPU / Metal"


def register_new_engines(store: dict, models: list[dict], fetch=fetch_repo_meta) -> list[dict]:
    """Register NEW engines found in raw `models` when their engine_repo is a
    reachable GitHub repo classified as an inference engine. Strips
    engine_repo from every measurement. Returns one decision per new engine:
    {engine, repo, decision: registered|not-engine|unknown|no-repo|unreachable, reason}."""
    reg = store.setdefault("engines", {})
    by_engine: dict[str, list[tuple[dict, dict]]] = {}
    for m in models:
        for e in m.get("engines", []) or []:
            name = e.get("engine")
            if name and name not in reg:
                by_engine.setdefault(name, []).append((m, e))
    out = []
    name_ok = _registry_name_pattern()
    for name, rows in by_engine.items():
        repos = [e.get("engine_repo") for _, e in rows if e.get("engine_repo")]
        repo = repos[0] if repos else ""
        meas = [e for _, e in rows]
        post = next((e.get("source_post") for e in meas if e.get("source_post")), "")
        slugs = sorted({repo_slug(r) or r for r in repos})
        if not name_ok.match(name):
            out.append({"engine": name, "repo": repo, "decision": "invalid-name",
                        "reason": f"engine name does not match the registry pattern {name_ok.pattern}"})
            continue
        if len(slugs) > 1:
            out.append({"engine": name, "repo": ", ".join(slugs), "decision": "conflict",
                        "reason": "measurements give different engine_repo values"})
            continue
        if not repo:
            out.append({"engine": name, "repo": "", "decision": "no-repo",
                        "reason": "search did not record engine_repo"})
            continue
        if not repo_slug(repo):
            out.append({"engine": name, "repo": repo, "decision": "unknown",
                        "reason": "engine_repo is not a github.com repository URL"})
            continue
        meta = fetch(repo)
        if meta is None:
            out.append({"engine": name, "repo": repo, "decision": "unreachable",
                        "reason": "GitHub repo not found / unreachable"})
            continue
        kind, why = classify_repo(meta, name)
        if kind != "engine":
            out.append({"engine": name, "repo": repo, "decision": kind, "reason": why})
            continue
        url = "https://github.com/" + (meta.get("full_name") or repo_slug(repo) or "")
        desc = (meta.get("description") or "").strip()
        reg[name] = {
            "backend": _infer_backend(meas),
            "url": url,
            "note": (f"Auto-registered from {post}" if post else "Auto-registered")
                    + (f" — {desc[:120]}" if desc else ""),
            "auto": True,
        }
        out.append({"engine": name, "repo": url, "decision": "registered", "reason": why})
    for m in models:
        for e in m.get("engines", []) or []:
            e.pop("engine_repo", None)
    return out


def check_raw(raw_dir: Path, store: dict, fetch=fetch_repo_meta) -> list[dict]:
    """Report (never write) what register_new_engines would decide for the raw snapshots."""
    models = []
    for f in sorted(raw_dir.glob("*.json")):
        try:
            models += json.loads(f.read_text()).get("models", [])
        except Exception:  # noqa: BLE001
            continue
    shadow = {"engines": dict(store.get("engines", {}))}
    return register_new_engines(shadow, json.loads(json.dumps(models)), fetch=fetch)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-raw", metavar="DIR", required=True)
    ap.add_argument("--store", default=str(Path(os.environ.get("TRENDING_DATA_DIR", ROOT / "data")) / "models.json"))
    args = ap.parse_args()
    store = json.loads(Path(args.store).read_text())
    decisions = check_raw(Path(args.check_raw), store)
    if not decisions:
        print("[engine-check] OK: every engine in the raw snapshots is registered (or auto-registrable)")
        return 0
    for d in decisions:
        flag = "OK  " if d["decision"] == "registered" else "WARN"
        print(f"[engine-check] {flag} {d['engine']!r}: {d['decision']} — {d['reason']}"
              + (f" ({d['repo']})" if d["repo"] else ""))
    bad = [d for d in decisions if d["decision"] != "registered"]
    if bad:
        print(f"[engine-check] {len(bad)} engine(s) will FAIL validation unless registered by a human or fix-bot "
              f"(harnesses/apps/benchmarks must not be registered).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
