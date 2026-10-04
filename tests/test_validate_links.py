#!/usr/bin/env python3
"""Unit tests for the link-resolution validator (check_links_resolve).

Covers:
  - _extract_links pulls links from models.json (engine registry, model HF,
    format HF, source_post), README, and raw search snapshots.
  - _link_ok resolves a real URL (HTTP 2xx/3xx) and rejects a dead one.
  - a strict (HF / engine) link that is rate-limited (429) / 5xx / timing out
    is retried with backoff and, if it never settles, reported UNVERIFIED — a
    warning, not a dead link (PRs #83 / #84 went red on ~40 HF repos that all
    exist because 429s were counted as "does not resolve").
  - each URL is probed once per run (models.json + raw snapshots repeat them).
  - check_links_resolve FAILS on a dead link and auto-corrects a known-good
    engine URL that was wrong in the store.

Run:  python3 tests/test_validate_links.py   or   make test
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate as V  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def store() -> dict:
    return {
        "engines": {
            "llama.cpp": {"backend": "CUDA", "note": "x", "url": "https://github.com/ggml-org/llama.cpp"},
            "Ollama": {"backend": "CUDA", "note": "x", "url": "https://github.com/ollama/ollama"},
        },
        "models": [{
            "id": "qwen3-14b", "name": "Qwen3 14B", "full_name": "Qwen3-14B", "type": "LLM",
            "formats": [{"name": "GGUF", "hf": "Qwen/Qwen3-14B"}], "license": "Apache 2.0",
            "params": "14B", "hf": "Qwen/Qwen3-14B", "vram_tier": "9GB", "vram_min": "8GB",
            "backends": ["CUDA"], "supported_engines": ["llama.cpp"],
            "engines": [{"engine": "llama.cpp", "tps": "50", "date": "2026-09-28",
                         "source_post": "https://github.com/ggml-org/llama.cpp"}],
            "why": "w", "engagement": {"likes": 1, "comments": 0, "views": 1, "last_7d_likes": 1},
            "last_seen": "2026-09-28",
        }],
    }


def test_extract_links_covers_all_sources():
    """_extract_links must pull engine-registry, model-hf, format-hf, source_post,
    README, and raw-snapshot links."""
    s = store()
    links = V._extract_links(s)
    kinds = {k for k, _, _ in links}
    check("extract: engine-registry links present", "engine-registry" in kinds)
    check("extract: model-hf links present", "model-hf" in kinds)
    check("extract: format-hf links present", "format-hf" in kinds)
    check("extract: source_post links present", "source_post" in kinds)
    # README + raw need temp files
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        (td / "README.md").write_text("see [llama.cpp](https://github.com/ggml-org/llama.cpp) and https://example.com/x")
        (td / "raw").mkdir()
        (td / "raw" / "nvidia-1.json").write_text(json.dumps({
            "backend": "nvidia", "generated_utc": "2026-09-28T10:00:00Z",
            "models": [{"id": "m1", "name": "M1", "hf": "org/m1",
                        "engines": [{"engine": "llama.cpp", "tps": "1", "date": "2026-09-28",
                                     "source_post": "https://lightbrd.com/raw"}]}],
        }))
        saved_r, saved_raw = V.README, V.RAW_DIR
        V.README, V.RAW_DIR = td / "README.md", td / "raw"
        try:
            links2 = V._extract_links(s)
        finally:
            V.README, V.RAW_DIR = saved_r, saved_raw
        kinds2 = {k for k, _, _ in links2}
        check("extract: README links present", "readme" in kinds2)
        check("extract: raw-snapshot links present", "raw-hf" in kinds2 or "raw-source_post" in kinds2)


def test_link_ok_resolves_real_url():
    """A real, reachable URL passes; a dead URL fails. Skips (does not fail) if
    the network is unavailable in the test environment, so CI can't flake."""
    live = V._link_ok("https://github.com/ggml-org/llama.cpp")
    if not live:
        print("  skip link_ok live-network test (github unreachable in this env)")
        return
    check("link_ok: github resolves", live)
    check("link_ok: dead URL fails", not V._link_ok("https://github.com/this-repo-does-not-exist-xyz123/definitely-not-here"))


def _run_hermetic(s):
    """Run check_links_resolve with V.README pointed at a temp file containing
    only resolvable links and V.RAW_DIR at an EMPTY temp dir, so the real
    README's / raw snapshots' (possibly dead) links don't leak into the test."""
    import tempfile as _t
    with _t.TemporaryDirectory() as td:
        td = Path(td)
        rp = td / "README.md"
        rp.write_text("see [llama.cpp](https://github.com/ggml-org/llama.cpp)")
        rawdir = td / "raw"
        rawdir.mkdir()
        saved_r, saved_raw = V.README, V.RAW_DIR
        V.README, V.RAW_DIR = rp, rawdir
        try:
            V.FAILURES.clear()
            V._LINK_CACHE.clear()
            V.check_links_resolve(s)
        finally:
            V.README, V.RAW_DIR = saved_r, saved_raw
    return [m for m in V.FAILURES if m.startswith("link:")]


def _stub_link_ok(resolvable):
    """Patch V._link_ok to return True only for URLs in `resolvable` — hermetic,
    so CI can't flake on HF/GitHub blocking datacenter IPs. The resolution tests
    exercise the validator's LOGIC, not the live network."""
    import unittest.mock as mock
    return mock.patch.object(V, "_link_ok", side_effect=lambda url, *a, **k: url in resolvable)


def test_check_links_resolve_passes_valid_store():
    """A store whose links all resolve passes (no FAILURES)."""
    s = store()
    ok = {
        "https://github.com/ggml-org/llama.cpp",
        "https://github.com/ollama/ollama",
        "https://huggingface.co/Qwen/Qwen3-14B",
    }
    with _stub_link_ok(ok):
        errs = _run_hermetic(s)
    check("links: valid store passes", len(errs) == 0, json.dumps(errs))


def _run_with_raw(s, raw_payload):
    """Point V.README + V.RAW_DIR at temp files (README only resolves; raw holds
    the given payload) and run check_links_resolve, returning its FAILURES."""
    import tempfile as _t
    with _t.TemporaryDirectory() as td:
        td = Path(td)
        rp = td / "README.md"
        rp.write_text("see [llama.cpp](https://github.com/ggml-org/llama.cpp)")
        rawdir = td / "raw"
        rawdir.mkdir()
        (rawdir / "nvidia-1.json").write_text(json.dumps(raw_payload))
        saved_r, saved_raw = V.README, V.RAW_DIR
        V.README, V.RAW_DIR = rp, rawdir
        try:
            V.FAILURES.clear()
            V.check_links_resolve(s)
        finally:
            V.README, V.RAW_DIR = saved_r, saved_raw
    return [m for m in V.FAILURES if m.startswith("link:")]


def test_check_links_resolve_catches_dead_link():
    """A dead link in the store FAILS the check. Use a dead source_post (not an
    engine URL, which would be auto-fixed to a known-good repo)."""
    s = store()
    s["models"][0]["engines"][0]["source_post"] = "https://github.com/this-repo-does-not-exist-xyz123/nope"
    ok = {
        "https://github.com/ggml-org/llama.cpp",
        "https://github.com/ollama/ollama",
        "https://huggingface.co/Qwen/Qwen3-14B",
    }
    with _stub_link_ok(ok):
        errs = _run_hermetic(s)
    check("links: dead link is caught", any("source_post" in e for e in errs), json.dumps(errs))


def test_invalid_link_in_raw_snapshot_is_caught():
    """A NEW search snapshot (data/raw/*.json) carrying a dead source_post or a
    wrong HF id must FAIL check_links_resolve — the same check that guards
    models.json and README. This closes the raw -> models -> README link gap."""
    s = {}  # empty store; the failure must come from the raw snapshot alone
    raw_bad_post = {"backend": "nvidia", "generated_utc": "2026-09-28T10:00:00Z", "models": [{
        "id": "m1", "name": "M1", "full_name": "M1", "type": "LLM",
        "license": "Apache 2.0", "params": "1B", "hf": "org/m1",
        "vram_tier": "1GB", "vram_min": "1GB", "backends": ["CUDA"],
        "engines": [{"engine": "llama.cpp", "tps": "12", "date": "2026-09-28",
                     "source_post": "https://github.com/this-repo-does-not-exist-xyz123/nope"}],
        "last_seen": "2026-09-28",
    }]}
    ok = {"https://github.com/ggml-org/llama.cpp"}
    with _stub_link_ok(ok):
        errs = _run_with_raw(s, raw_bad_post)
    check("links: dead source_post in NEW raw snapshot is caught",
          any("raw-source_post" in e for e in errs), json.dumps(errs))

    raw_bad_hf = {"backend": "nvidia", "generated_utc": "2026-09-28T10:00:00Z", "models": [{
        "id": "m2", "name": "M2", "full_name": "M2", "type": "LLM",
        "license": "Apache 2.0", "params": "1B", "hf": "zzz-non-existent-org/nope-model",
        "vram_tier": "1GB", "vram_min": "1GB", "backends": ["CUDA"],
        "engines": [{"engine": "llama.cpp", "tps": "12", "date": "2026-09-28",
                     "source_post": "https://github.com/ggml-org/llama.cpp"}],
        "last_seen": "2026-09-28",
    }]}
    with _stub_link_ok(ok):
        errs = _run_with_raw(s, raw_bad_hf)
    check("links: wrong HF id in NEW raw snapshot is caught",
          any("raw-hf" in e for e in errs), json.dumps(errs))


def test_check_links_resolve_autofixes_known_engine_url():
    """A wrong engine URL that we know the canonical repo for is auto-corrected
    in the store (so the fix-bot has a concrete repair)."""
    s = store()
    s["engines"]["llama.cpp"]["url"] = "https://github.com/wrong-owner/llama.cpp"
    ok = {
        "https://github.com/ggml-org/llama.cpp",  # canonical resolves
        "https://github.com/ollama/ollama",
        "https://huggingface.co/Qwen/Qwen3-14B",
    }
    with _stub_link_ok(ok):
        _run_hermetic(s)
    check("links: known engine url auto-corrected",
          s["engines"]["llama.cpp"]["url"] == "https://github.com/ggml-org/llama.cpp",
          s["engines"]["llama.cpp"]["url"])


def _run_present(store, raw_payload=None):
    """Point V.RAW_DIR at a temp dir (optionally holding a raw snapshot) and run
    check_links_present, returning its FAILURES."""
    import tempfile as _t
    with _t.TemporaryDirectory() as td:
        td = Path(td)
        rawdir = td / "raw"
        rawdir.mkdir()
        if raw_payload is not None:
            (rawdir / "nvidia-1.json").write_text(json.dumps(raw_payload))
        saved = V.RAW_DIR
        V.RAW_DIR = rawdir
        try:
            V.FAILURES.clear()
            V.check_links_present(store)
        finally:
            V.RAW_DIR = saved
    return list(V.FAILURES)


def test_links_present_catches_missing_links():
    """A model or raw snapshot that is MISSING its HF link or its engine's
    source_post link must FAIL check_links_present — the presence guard that
    catches bad search data before it aggregates."""
    # store model missing hf
    s = store()
    s["models"][0].pop("hf")
    errs = _run_present(s)
    check("present: model missing HF link is caught",
          any("missing HF link" in e for e in errs), json.dumps(errs))
    # store engine missing source_post
    s = store()
    s["models"][0]["engines"][0].pop("source_post")
    errs = _run_present(s)
    check("present: engine missing source_post is caught",
          any("missing source_post" in e for e in errs), json.dumps(errs))
    # raw snapshot missing hf
    raw = {"backend": "nvidia", "generated_utc": "2026-09-28T10:00:00Z", "models": [{
        "id": "m1", "name": "M1", "full_name": "M1", "type": "LLM",
        "license": "Apache 2.0", "params": "1B", "vram_tier": "1GB", "vram_min": "1GB",
        "backends": ["CUDA"],
        "engines": [{"engine": "llama.cpp", "tps": "12", "date": "2026-09-28",
                     "source_post": "https://github.com/ggml-org/llama.cpp"}],
        "last_seen": "2026-09-28"}]}  # no hf
    errs = _run_present({}, raw)
    check("present: raw snapshot missing HF link is caught",
          any("missing HF link" in e for e in errs), json.dumps(errs))
    # raw snapshot engine missing source_post
    raw = {"backend": "nvidia", "generated_utc": "2026-09-28T10:00:00Z", "models": [{
        "id": "m1", "name": "M1", "full_name": "M1", "type": "LLM",
        "license": "Apache 2.0", "params": "1B", "hf": "org/m1",
        "vram_tier": "1GB", "vram_min": "1GB", "backends": ["CUDA"],
        "engines": [{"engine": "llama.cpp", "tps": "12", "date": "2026-09-28"}],  # no source_post
        "last_seen": "2026-09-28"}]}
    errs = _run_present({}, raw)
    check("present: raw engine missing source_post is caught",
          any("missing source_post" in e for e in errs), json.dumps(errs))
    # a complete store + raw passes
    errs = _run_present(store())
    check("present: complete store passes", len(errs) == 0, json.dumps(errs))


def test_hf_id_autofix_known_model():
    """A model whose HF link 404s but whose canonical HF id we know is
    auto-corrected in the store (so the fix-bot has a concrete repair)."""
    s = store()  # id 'qwen3-14b' is in KNOWN_HF_IDS
    s["models"][0]["hf"] = "wrong-owner/nope-model"
    ok = {
        "https://github.com/ggml-org/llama.cpp",
        "https://github.com/ollama/ollama",
        "https://huggingface.co/Qwen/Qwen3-14B",  # canonical HF resolves
    }
    with _stub_link_ok(ok):
        _run_hermetic(s)
    check("links: known HF id auto-corrected",
          s["models"][0]["hf"] == "Qwen/Qwen3-14B", s["models"][0]["hf"])


class FakeResp:
    def __init__(self, status):
        self.status = status
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def _http_error(code, retry_after=None):
    import email.message
    import urllib.error
    h = email.message.Message()
    if retry_after is not None:
        h["Retry-After"] = str(retry_after)
    return urllib.error.HTTPError("https://example.com/x", code, "x", h, None)


def _urlopen_seq(responses):
    """urlopen stub: each call pops the next item — an int status (returned as a
    response, like a 2xx) or an exception instance (raised, like urllib does
    for 4xx/5xx). Records the calls so tests can count probes."""
    calls = []
    seq = list(responses)

    def fake(req, timeout=None):
        calls.append((req.get_method(), req.full_url))
        item = seq.pop(0) if len(seq) > 1 else seq[0]
        if isinstance(item, BaseException):
            raise item
        return FakeResp(item)
    return fake, calls


def test_link_ok_strict_2xx():
    """Strict _link_ok is True ONLY for HTTP 2xx. 403/404 are dead at once.
    429/5xx are retried (backoff, no real sleep here) and, still failing, are
    not OK — but they are UNVERIFIED, not dead (see the next test)."""
    import unittest.mock as mock
    for status, expect in [(200, True), (403, False), (404, False),
                           (429, False), (500, False), (503, False)]:
        V._LINK_CACHE.clear()
        with mock.patch.object(V, "_sleep", lambda s: None), \
             mock.patch("urllib.request.urlopen", side_effect=_urlopen_seq([_http_error(status) if status >= 400 else status])[0]):
            got = V._link_ok("https://example.com/x")
        check(f"link_ok: HTTP {status} -> {expect}", got == expect, f"got {got}")
    # lenient mode (source_post / README): 403/429/5xx is NOT a dead link
    for status, expect in [(200, True), (403, True), (429, True), (503, True), (404, False)]:
        V._LINK_CACHE.clear()
        with mock.patch("urllib.request.urlopen", side_effect=_urlopen_seq([_http_error(status) if status >= 400 else status])[0]):
            got = V._link_ok("https://example.com/x", strict=False)
        check(f"link_ok lenient: HTTP {status} -> {expect}", got == expect, f"got {got}")


def test_strict_rate_limit_is_retried_then_unverified_not_dead():
    """Regression for PRs #83/#84: HF answered 429 to a burst of link checks
    and validate reported real repos as dead. A 429 that clears is OK; a 429
    that never clears is UNVERIFIED (warned, not failed); a 404 stays DEAD and
    is not retried."""
    import unittest.mock as mock
    url = "https://huggingface.co/Qwen/Qwen3-8B"
    slept = []
    # 429 (Retry-After 7) then 200 -> ok, honoured Retry-After, 2 probes
    V._LINK_CACHE.clear()
    fake, calls = _urlopen_seq([_http_error(429, retry_after=7), 200])
    with mock.patch.object(V, "_sleep", slept.append), mock.patch("urllib.request.urlopen", side_effect=fake):
        ok = V._link_ok(url)
    check("retry: 429 then 200 -> ok", ok, f"calls={calls}")
    check("retry: Retry-After honoured", slept == [7.0], f"slept={slept}")
    check("retry: 429 does not also burn a GET", len(calls) == 2, f"calls={calls}")
    # 429 forever -> not ok, but unverified (not dead)
    V._LINK_CACHE.clear()
    fake, calls = _urlopen_seq([_http_error(429)])
    with mock.patch.object(V, "_sleep", lambda s: None), mock.patch("urllib.request.urlopen", side_effect=fake):
        dead = V._link_dead(url, strict=True)
    check("retry: persistent 429 is NOT dead", not dead)
    check("retry: persistent 429 is unverified", V._unverified(url))
    check("retry: bounded attempts", len(calls) == V._LINK_RETRIES + 1, f"{len(calls)} calls")
    # 404 -> dead immediately, no retry, no sleep
    V._LINK_CACHE.clear()
    slept.clear()
    fake, calls = _urlopen_seq([_http_error(404)])
    with mock.patch.object(V, "_sleep", slept.append), mock.patch("urllib.request.urlopen", side_effect=fake):
        dead = V._link_dead("https://huggingface.co/org/nope", strict=True)
    check("404: dead", dead)
    check("404: no retry / no sleep", len(calls) == 1 and not slept, f"calls={calls} slept={slept}")
    # DNS failure -> dead (a typo'd host is a real dead link)
    import socket
    import urllib.error
    V._LINK_CACHE.clear()
    fake, calls = _urlopen_seq([urllib.error.URLError(socket.gaierror(-2, "Name or service not known"))])
    with mock.patch.object(V, "_sleep", lambda s: None), mock.patch("urllib.request.urlopen", side_effect=fake):
        dead = V._link_dead("https://no-such-host.invalid/x", strict=True)
    check("dns: unresolvable host is dead", dead and len(calls) == 1, f"calls={calls}")


def test_each_url_probed_once_per_run():
    """models.json + raw snapshots repeat the same HF repo many times (86 HF
    links / 15 unique on master). Each URL must be probed once per run, or a
    full validate bursts past the HF rate limit."""
    import unittest.mock as mock
    V._LINK_CACHE.clear()
    fake, calls = _urlopen_seq([200])
    with mock.patch("urllib.request.urlopen", side_effect=fake):
        for _ in range(10):
            V._link_ok("https://huggingface.co/Qwen/Qwen3-14B")
    check("cache: 10 checks of one URL -> 1 probe", len(calls) == 1, f"{len(calls)} probes")


def test_rate_limited_store_does_not_fail_validation():
    """End to end through check_links_resolve: every HF link answers 429 for
    the whole run (the #83/#84 state). No 'does not resolve' failures — they
    are unverified warnings. A genuinely dead (404) HF link in the same run
    still fails."""
    import unittest.mock as mock
    s = store()
    s["models"].append({"id": "gone", "hf": "org/gone", "formats": [], "engines": []})

    def fake(req, timeout=None):
        u = req.full_url
        if u == "https://huggingface.co/org/gone":
            raise _http_error(404)
        if u.startswith("https://huggingface.co/"):
            raise _http_error(429)
        return FakeResp(200)
    with mock.patch.object(V, "_sleep", lambda s: None), mock.patch("urllib.request.urlopen", side_effect=fake):
        errs = _run_hermetic(s)
    rate_limited = [e for e in errs if "huggingface.co/" in e and "org/gone" not in e]
    check("rate-limited HF links are not reported dead", not rate_limited, json.dumps(rate_limited))
    check("a real 404 HF link still fails in the same run",
          any("org/gone" in e and "does not resolve" in e for e in errs), json.dumps(errs))


def test_wrong_but_resolving_link_is_corrected():
    """A known model whose HF link points at a DIFFERENT valid repo (it resolves)
    but not the canonical one is auto-corrected — QA that a fixed link matches
    the model, not just that it resolves."""
    s = store()  # id 'qwen3-14b' canonical Qwen/Qwen3-14B
    s["models"][0]["hf"] = "Qwen/Qwen3-8B"  # valid but wrong
    ok = {
        "https://github.com/ggml-org/llama.cpp",
        "https://github.com/ollama/ollama",
        "https://huggingface.co/Qwen/Qwen3-8B",   # wrong link resolves
        "https://huggingface.co/Qwen/Qwen3-14B",  # canonical resolves
    }
    with _stub_link_ok(ok):
        _run_hermetic(s)
    check("links: wrong-but-resolving HF link auto-corrected to canonical",
          s["models"][0]["hf"] == "Qwen/Qwen3-14B", s["models"][0]["hf"])


def test_wrong_but_resolving_link_fails_when_canonical_unverifiable():
    """If a known model's HF link is wrong but resolves, and the canonical is
    NOT verifiable, the link FAILS (reported for manual review) rather than
    silently passing — the fix-bot must search differently."""
    s = store()
    s["models"][0]["hf"] = "Qwen/Qwen3-8B"  # valid but wrong
    ok = {
        "https://github.com/ggml-org/llama.cpp",
        "https://github.com/ollama/ollama",
        "https://huggingface.co/Qwen/Qwen3-8B",  # wrong link resolves
        # canonical NOT in ok -> unverifiable
    }
    with _stub_link_ok(ok):
        errs = _run_hermetic(s)
    check("links: wrong-but-resolving link fails when canonical unverifiable",
          any("does not match known-good" in e for e in errs), json.dumps(errs))


def main() -> int:
    print("link-resolution validator (models.json + README + raw snapshots)")
    test_extract_links_covers_all_sources()
    test_link_ok_resolves_real_url()
    test_link_ok_strict_2xx()
    test_strict_rate_limit_is_retried_then_unverified_not_dead()
    test_each_url_probed_once_per_run()
    test_rate_limited_store_does_not_fail_validation()
    test_wrong_but_resolving_link_is_corrected()
    test_wrong_but_resolving_link_fails_when_canonical_unverifiable()
    test_check_links_resolve_passes_valid_store()
    test_check_links_resolve_catches_dead_link()
    test_invalid_link_in_raw_snapshot_is_caught()
    test_check_links_resolve_autofixes_known_engine_url()
    test_links_present_catches_missing_links()
    test_hf_id_autofix_known_model()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
