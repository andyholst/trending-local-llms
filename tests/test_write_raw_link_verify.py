#!/usr/bin/env python3
"""Issue #644: the write-time link check covers more than `hf`.

`write_raw_snapshot(..., verify_hf=True)` verified `_m["hf"]` and `_f["hf"]`
only (issue #417), while the same payload carries `source_post` and
`engine_repo` — whose dead spellings were first seen by `check_links_resolve`
two pipelines later, on the open refresh PR, where the only repairer rewrote
them silently and the prompt never learned.

Proves (against a REAL local HTTP server the real urllib client talks to —
rule 6m: an external system, never a mock of the product):
  1. A DEFINITIVELY dead `source_post` (404) refuses that engine measurement,
     loudly, naming the model, the field and the refused value.
  2. A definitively dead `engine_repo` (404) is stripped while the figure and
     its live source_post survive.
  3. Indeterminate answers (503/429) keep every value — a flaky target must
     never look like a fabricated link.
  4. verify_hf=False makes NO request at all.
  5. One URL costs one request per write (the per-write cache).

Run:  python3 tests/test_write_raw_link_verify.py   or   make test
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


# ------------------------------------------------- the external system -------

_SERVER: ThreadingHTTPServer | None = None
_SEEN: list[tuple[str, str]] = []
_STATUS: dict[str, int] = {}


class _Links(BaseHTTPRequestHandler):
    def _answer(self):
        _SEEN.append((self.command, self.path))
        code = _STATUS.get(self.path, 200)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(b"{}")

    do_GET = do_HEAD = _answer

    def log_message(self, *a):
        pass


def _server_url(path: str) -> str:
    return f"http://127.0.0.1:{_SERVER.server_address[1]}{path}"


@contextlib.contextmanager
def links_server(status: dict[str, int]):
    global _SERVER, _SEEN, _STATUS
    _SEEN = []
    _STATUS = {"/api/models/org/test": 200, **status}
    _SERVER = ThreadingHTTPServer(("127.0.0.1", 0), _Links)
    threading.Thread(target=_SERVER.serve_forever, daemon=True).start()
    saved = os.environ.get("HF_MODEL_API")
    os.environ["HF_MODEL_API"] = f"http://127.0.0.1:{_SERVER.server_address[1]}/api/models"
    try:
        yield _server_url
    finally:
        if saved is not None:
            os.environ["HF_MODEL_API"] = saved
        else:
            os.environ.pop("HF_MODEL_API", None)
        _SERVER.shutdown()
        _SERVER.server_close()
        _SERVER = None


def write_and_read(payload: dict, backend: str = "amd", **kw) -> dict:
    with tempfile.TemporaryDirectory() as td:
        saved_dir, saved_now = UT.RAW_DIR, UT.now_utc
        UT.RAW_DIR = Path(td)
        UT.now_utc = lambda: datetime(2026, 10, 27, 12, 0, 0, tzinfo=timezone.utc)
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                path = UT.write_raw_snapshot(backend, payload, **kw)
                out = buf.getvalue()
            return json.loads(Path(path).read_text()), out
        finally:
            UT.RAW_DIR, UT.now_utc = saved_dir, saved_now


def payload_with(url, engines):
    return {"backend": "amd", "models": [{
        "id": "test-model", "name": "Test Model", "hf": "org/test",
        "engines": engines(url),
    }]}


def test_dead_source_post_refuses_the_measurement():
    with links_server({"/post/dead": 404, "/post/alive": 200}) as url:
        store, out = write_and_read(payload_with(
            url, lambda u: [
                {"engine": "llama.cpp", "tps": 40.0, "source_post": u("/post/dead")},
                {"engine": "ollama", "tps": 30.0, "source_post": u("/post/alive")},
            ]), verify_hf=True)
        engs = store["models"][0]["engines"]
        check("write-raw: the measurement with the dead post is refused",
              all(e.get("source_post") != url("/post/dead") for e in engs), engs)
        check("write-raw: the live measurement survives",
              any(e.get("source_post") == url("/post/alive") for e in engs), engs)
        check("write-raw: the refusal names model, field and refused value",
              "refused measurement on model 'test-model'" in out
              and "source_post" in out and "/post/dead" in out, out)


def test_dead_engine_repo_is_stripped_and_the_figure_kept():
    with links_server({"/repo/dead": 404, "/post/alive": 200}) as url:
        store, out = write_and_read(payload_with(
            url, lambda u: [
                {"engine": "newthing", "tps": 55.0, "source_post": u("/post/alive"),
                 "engine_repo": u("/repo/dead")},
            ]), verify_hf=True)
        engs = store["models"][0]["engines"]
        check("write-raw: the figure survives a dead engine_repo",
              len(engs) == 1 and engs[0]["tps"] == 55.0, engs)
        check("write-raw: the dead engine_repo key is gone",
              "engine_repo" not in engs[0], engs)
        check("write-raw: the strip names the refused repo URL",
              "refused engine_repo" in out and "/repo/dead" in out, out)


def test_indeterminate_answers_keep_the_values():
    with links_server({"/post/lim": 503, "/repo/lim": 429}) as url:
        store, out = write_and_read(payload_with(
            url, lambda u: [
                {"engine": "llama.cpp", "tps": 12.0, "source_post": u("/post/lim"),
                 "engine_repo": u("/repo/lim")},
            ]), verify_hf=True)
        engs = store["models"][0]["engines"]
        check("write-raw: a 503/429 never looks fabricated — both values kept",
              len(engs) == 1 and engs[0].get("source_post") == url("/post/lim")
              and engs[0].get("engine_repo") == url("/repo/lim"), engs)
        check("write-raw: nothing was refused", "refused" not in out, out)


def test_verify_hf_false_does_not_check_links():
    with links_server({"/post/dead": 404}) as url:
        store, out = write_and_read(payload_with(
            url, lambda u: [
                {"engine": "llama.cpp", "tps": 40.0, "source_post": u("/post/dead")},
            ]), verify_hf=False)
        engs = store["models"][0]["engines"]
        check("write-raw: verify_hf=False makes no request and changes nothing",
              _SEEN == [] and engs[0]["source_post"] == url("/post/dead"),
              (_SEEN, engs))


def test_one_url_costs_one_request_per_write():
    with links_server({"/post/alive": 200}) as url:
        u = url("/post/alive")
        payload = {"backend": "amd", "models": [
            {"id": f"m{i}", "name": f"M{i}", "hf": f"org/m{i}",
             "engines": [{"engine": "llama.cpp", "tps": 1.0, "source_post": u},
                         {"engine": "ollama", "tps": 2.0, "source_post": u}]}
            for i in range(3)]}
        write_and_read(payload, verify_hf=True)
        posts = [s for s in _SEEN if s[1] == "/post/alive"]
        check("write-raw: six measurements, one HEAD (per-write cache)",
              len(posts) == 1, _SEEN)


if __name__ == "__main__":
    for fn in (test_dead_source_post_refuses_the_measurement,
               test_dead_engine_repo_is_stripped_and_the_figure_kept,
               test_indeterminate_answers_keep_the_values,
               test_verify_hf_false_does_not_check_links,
               test_one_url_costs_one_request_per_write):
        print(f"== {fn.__name__}")
        fn()
    print(f"\nPASS {_PASS} | FAIL {_FAIL}")
    sys.exit(1 if _FAIL else 0)
