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

Issue #417 adds the WRITE-time half of the same seam: the same check runs inside
`write_raw_snapshot(..., verify_hf=True)` — what `--write-raw` passes — so a
guessed `owner/model` is refused in the leg that made it, before the snapshot
lands and the refresh PR is open, and the leg's log says which id it refused.
The last test pins the OTHER half of the repair: the `data-search` skill the four
legs preload asks for the lookup instead of a plausible guess.

Run:  python3 tests/test_ingest_hf_verify.py   or   make test
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import threading
from datetime import datetime, timezone
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


# --------------------------------------------------- the write-raw seam -------

def write_and_read(payload: dict, backend: str = "amd", **kw) -> dict:
    """Run `write_raw_snapshot` against a temp raw dir and return what landed."""
    with tempfile.TemporaryDirectory() as td:
        saved_dir, saved_now = UT.RAW_DIR, UT.now_utc
        UT.RAW_DIR = Path(td)
        UT.now_utc = lambda: datetime(2026, 10, 27, 12, 0, 0, tzinfo=timezone.utc)
        try:
            path = UT.write_raw_snapshot(backend, payload, **kw)
            return json.loads(Path(path).read_text())
        finally:
            UT.RAW_DIR, UT.now_utc = saved_dir, saved_now


def test_write_raw_refuses_an_unverified_hf():
    """A guessed id is refused in the leg that made it, not by CI later."""
    def run(base):
        _HF.status_for = {"/api/models/gone/model": 404,
                          "/api/models/good/model": 200}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            data = write_and_read({
                "backend": "amd",
                "models": [
                    {"id": "bad-model", "name": "Bad", "hf": "gone/model"},
                    {"id": "good-model", "name": "Good", "hf": "good/model"},
                ],
            }, backend="amd", verify_hf=True)
        return data, buf.getvalue()

    data, out = _with_api(run)
    ids = [m["id"] for m in data["models"]]
    check("write-raw: a 404 model is refused", "bad-model" not in ids, ids)
    check("write-raw: the model that resolves survives", "good-model" in ids, ids)
    check("write-raw: the warning names the backend, model and id",
          "amd" in out and "bad-model" in out and "gone/model" in out, out)
    check("write-raw: the good model is not named in a warning",
          "good/model" not in out, out)


def test_write_raw_drops_a_bad_format_only():
    """A bad `formats[].hf` costs that format, not the whole model."""
    def run(base):
        _HF.status_for = {"/api/models/good/model": 200,
                          "/api/models/gone/format": 404}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            data = write_and_read({
                "backend": "cpu",
                "models": [{
                    "id": "m", "name": "M", "hf": "good/model",
                    "formats": [{"name": "GGUF", "hf": "gone/format"},
                                {"name": "MLX", "hf": "good/model"}],
                }],
            }, backend="cpu", verify_hf=True)
        return data, buf.getvalue()

    data, out = _with_api(run)
    m = data["models"][0]
    check("write-raw: the model survives a bad format", m["id"] == "m", m)
    check("write-raw: only the bad format entry is dropped",
          [f["name"] for f in m["formats"]] == ["MLX"], m["formats"])
    check("write-raw: the warning names the format and the model",
          "gone/format" in out and "GGUF" in out and "m" in out, out)


def test_write_raw_keeps_an_indeterminate_hf():
    """A 429 is not a fabricated id: keep it and refuse nothing."""
    def run(base):
        _HF.status_for = {"/api/models/busy/model": 429}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            data = write_and_read({
                "backend": "metal",
                "models": [{"id": "busy-model", "name": "Busy", "hf": "busy/model"}],
            }, backend="metal", verify_hf=True)
        return data, buf.getvalue()

    data, out = _with_api(run)
    check("write-raw: a 429 keeps the model", data["models"][0]["id"] == "busy-model", data)
    check("write-raw: a 429 prints no refusal", "refused" not in out, out)


def test_write_raw_default_makes_no_request():
    """Direct callers stay hermetic: the check is opt-in."""
    def run(base):
        _HF.status_for = {"/api/models/gone/model": 404}
        _HF.seen = []
        data = write_and_read({
            "backend": "nvidia",
            "models": [{"id": "bad-model", "name": "Bad", "hf": "gone/model"}],
        })  # verify_hf defaults to False
        return data, list(_HF.seen)

    data, seen = _with_api(run)
    check("write-raw: the default makes no request", seen == [], seen)
    check("write-raw: the default keeps the model", data["models"][0]["id"] == "bad-model", data)


def test_write_raw_cli_turns_on_verification():
    """The `--write-raw` CLI is the production path and must turn the check on."""
    src = (ROOT / "scripts" / "update_trending.py").read_text()
    check("write-raw: main() passes verify_hf=True",
          "write_raw_snapshot(args.write_raw, payload, verify_hf=True)" in src, "")


def test_write_raw_normalises_hf_co_urls():
    """A full link is reduced to its id before it is verified."""
    def run(base):
        _HF.status_for = {"/api/models/Qwen/Qwen3-14B": 200}
        _HF.seen = []
        data = write_and_read({
            "backend": "amd",
            "models": [{"id": "qwen3-14b", "name": "Qwen3-14B",
                        "hf": "https://hf.co/Qwen/Qwen3-14B"}],
        }, backend="amd", verify_hf=True)
        return data, list(_HF.seen)

    data, seen = _with_api(run)
    check("write-raw: hf.co link -> repo id",
          data["models"][0]["hf"] == "Qwen/Qwen3-14B", data["models"][0].get("hf"))
    check("write-raw: the API was asked for the repo id",
          any(u.endswith("/Qwen/Qwen3-14B") for u in seen), seen)


def test_the_search_skill_requires_the_hf_lookup():
    """The leg's preloaded contract asks for the lookup, not a plausible guess."""
    text = (ROOT / ".hermes" / "skills" / "data-search" / "SKILL.md").read_text()
    check("skill: names the authenticated HF API lookup",
          "https://huggingface.co/api/models?search=<name>" in text, "")
    check("skill: says the id is looked up, never guessed",
          "looked up, never guessed" in text, "")
    check("skill: says an unverified id is left out",
          "leave `hf` out" in text, "")


def main() -> int:
    print("ingest HF link verification (#333) + the write-raw refusal (#417)")
    test_only_a_definitive_answer_is_a_finding()
    test_a_dead_repo_is_named_and_a_good_one_is_silent()
    test_only_new_models_cost_a_request()
    test_the_default_makes_no_request()
    test_main_passes_verify_hf()
    test_write_raw_refuses_an_unverified_hf()
    test_write_raw_drops_a_bad_format_only()
    test_write_raw_keeps_an_indeterminate_hf()
    test_write_raw_default_makes_no_request()
    test_write_raw_cli_turns_on_verification()
    test_write_raw_normalises_hf_co_urls()
    test_the_search_skill_requires_the_hf_lookup()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
