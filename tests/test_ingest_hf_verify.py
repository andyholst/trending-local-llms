#!/usr/bin/env python3
"""Issue #333: a refresh names a NEW model's Hugging Face repo that does not
resolve, in the run that produced it.

`check_links_resolve` already fails the PR on a dead link, but that is the first
moment anyone sees it — by then the refresh has opened a PR whose only repairer
is a bot round. On PR #330 a single truncated repo id
(`meta-models/Muse-Spark-Open`) was found by CI, hours after the search wrote it.

Proves:
  1. Only a DEFINITIVE answer (401/404) is a finding. A 500 or a 429 is
     indeterminate — a rate-limited or briefly-down API must never be reported
     as a bad link.
  2. A new model with a dead repo prints one loud line naming the id; a model
     that resolves prints nothing.
  3. Only NEW models are checked — an update to an existing model costs no
     request.
  4. The default (`verify_hf=False`) makes NO request at all, so the suite's
     ingest tests stay hermetic.
  5. The seam defaults to the real Hugging Face API.

Run:  python3 tests/test_ingest_hf_verify.py   or   make test
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402

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


class _HF(BaseHTTPRequestHandler):
    """A real local Hugging Face API stand-in: /api/models/<id> -> a status."""

    status_for: dict[str, int] = {}
    seen: list[str] = []

    def do_GET(self):  # noqa: N802
        _HF.seen.append(self.path)
        code = _HF.status_for.get(self.path, 200)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"id": self.path.rsplit("/", 1)[-1]}).encode())

    def log_message(self, *a):  # silence the server
        pass


def _serve() -> tuple[ThreadingHTTPServer, str]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _HF)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/api/models"


def _with_api(fn):
    """Run `fn(base_url)` with HF_MODEL_API pointed at a fresh local server."""
    httpd, base = _serve()
    saved = os.environ.get("HF_MODEL_API")
    os.environ["HF_MODEL_API"] = base
    try:
        return fn(base)
    finally:
        httpd.shutdown()
        if saved is None:
            os.environ.pop("HF_MODEL_API", None)
        else:
            os.environ["HF_MODEL_API"] = saved


def base_store() -> dict:
    return {"generated_utc": "2026-10-02T00:00:00Z",
            "engines": {"llama.cpp": {"backend": "CUDA", "note": "x",
                                      "url": "https://github.com/ggml-org/llama.cpp"}},
            "models": []}


def raw_model(mid: str, hf: str) -> dict:
    return {"id": mid, "name": mid, "full_name": mid, "type": "LLM", "license": "MIT",
            "params": "8B", "hf": hf, "vram_tier": "8GB", "vram_min": "8GB",
            "backends": ["CUDA"], "last_seen": "2026-10-01",
            "engines": [{"engine": "llama.cpp", "tps": "40", "hardware": "RTX 3060",
                         "quant": "Q4", "date": "2026-10-01",
                         "source_post": "https://lightbrd.com/u/status/" + mid}]}


def ingest(store: dict, raws: dict[str, dict], **kw):
    with tempfile.TemporaryDirectory() as td:
        rdir = Path(td)
        for name, payload in raws.items():
            (rdir / name).write_text(json.dumps(payload))
        saved = UT.RAW_DIR
        UT.RAW_DIR = rdir
        try:
            return UT.ingest_raw_snapshots(store, **kw)
        finally:
            UT.RAW_DIR = saved


# ---------------------------------------------------------------- the check --

def test_only_a_definitive_answer_is_a_finding():
    def run(base):
        _HF.status_for = {
            "/api/models/good/model": 200,
            "/api/models/gone/model": 404,
            "/api/models/private/model": 401,
            "/api/models/busy/model": 429,
            "/api/models/broken/model": 500,
        }
        return {k: UT.hf_repo_resolves(k) for k in
                ("good/model", "gone/model", "private/model", "busy/model", "broken/model")}

    got = _with_api(run)
    check("resolve: a 200 repo answers True", got["good/model"] is True, got)
    check("resolve: a 404 repo is a definitive False", got["gone/model"] is False, got)
    check("resolve: a 401 repo is a definitive False", got["private/model"] is False, got)
    check("resolve: a 429 is indeterminate (None), never a bad-link claim",
          got["busy/model"] is None, got)
    check("resolve: a 500 is indeterminate (None)", got["broken/model"] is None, got)
    check("resolve: a value that is not owner/repo is not checked",
          UT.hf_repo_resolves("no-slash") is None and UT.hf_repo_resolves(None) is None, "")


def test_a_dead_repo_is_named_and_a_good_one_is_silent():
    def run(base):
        _HF.status_for = {"/api/models/gone/model": 404}
        _HF.seen = []
        store = base_store()
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ingest(store, {"cpu-20261003-120000.json": {
                "backend": "cpu", "generated_utc": "2026-10-03T12:00:00Z",
                "models": [raw_model("dead", "gone/model"), raw_model("live", "good/model")]}},
                verify_hf=True)
        return buf.getvalue()

    out = _with_api(run)
    check("ingest: the dead NEW model's repo is named loudly",
          "'gone/model' does NOT resolve" in out and "dead" in out, out)
    check("ingest: the model that resolves is NOT named",
          "good/model" not in out, out)


def test_only_new_models_cost_a_request():
    def run(base):
        _HF.status_for = {}
        _HF.seen = []
        store = base_store()
        store["models"] = [dict(raw_model("existing", "org/existing"),
                                supported_engines=["llama.cpp"])]
        ingest(store, {"cpu-20261003-120000.json": {
            "backend": "cpu", "generated_utc": "2026-10-03T12:00:00Z",
            "models": [raw_model("existing", "org/existing")]}}, verify_hf=True)
        return list(_HF.seen)

    seen = _with_api(run)
    check("ingest: an existing model costs no request (only NEW ones are verified)",
          seen == [], seen)


def test_the_default_makes_no_request():
    def run(base):
        _HF.seen = []
        store = base_store()
        ingest(store, {"cpu-20261003-120000.json": {
            "backend": "cpu", "generated_utc": "2026-10-03T12:00:00Z",
            "models": [raw_model("fresh", "gone/model")]}})
        return list(_HF.seen)

    saved = os.environ.pop("HF_MODEL_API", None)
    try:
        # no seam: if the default verified, this would hit the real API. It must
        # not — the suite's ingest tests rely on verify_hf defaulting to off.
        check("ingest: the seam defaults to the real Hugging Face endpoint",
              UT.HF_MODEL_API == "https://huggingface.co/api/models", UT.HF_MODEL_API)
    finally:
        if saved is not None:
            os.environ["HF_MODEL_API"] = saved
    seen = _with_api(run)
    check("ingest: verify_hf defaults to OFF — a direct call makes no request",
          seen == [], seen)


def test_main_passes_verify_hf():
    """The production path is `main()`, so the CLI must turn the check ON."""
    src = (ROOT / "scripts" / "update_trending.py").read_text()
    check("cli: main() calls ingest with verify_hf=True",
          "ingest_raw_snapshots(store, since=since, verify_hf=True)" in src, "")
    mk = (ROOT / "Makefile").read_text()
    check("cli: the merge targets go through that script", "scripts/update_trending.py" in mk, "")


def main() -> int:
    print("ingest HF link verification (#333)")
    test_only_a_definitive_answer_is_a_finding()
    test_a_dead_repo_is_named_and_a_good_one_is_silent()
    test_only_new_models_cost_a_request()
    test_the_default_makes_no_request()
    test_main_passes_verify_hf()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
