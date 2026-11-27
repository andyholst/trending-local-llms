#!/usr/bin/env python3
"""Behavioural tests for scripts/free_model_refresh.py — the weekly live free-tier refresh (issue #1195).

The rule: the chain's free tier is a LIVE truth. The refresh reads `GET <base_url>/models` with
the credential by NAME, keeps every `:free` id with its real context_length, updates ONLY the
free steps (survivors keep order/aliases, new ids append, retired ids drop), NEVER touches the
local_fallback tier or the paid last_resort, records the read in `measured`, and writes nothing
when the set is unchanged. An absent credential or a failed read is a loud exit 2, never a
silent clean; a live set with no free model at all is a refused refresh (exit 1).

Every test drives the REAL script end to end against a scratch tree and a REAL local HTTP
server (rule 6m: the only stand-in is the external endpoint; the production code that builds
the request still runs). Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)
import fleet_chain_fixtures as F  # noqa: E402  (issues #1744/#1745: derive, never freeze)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "free_model_refresh.py"
CHAIN = ROOT / "agents" / "model_chain.json"
KEY_NAME = "NOUS_API_KEY"
PLACEHOLDER = "present-not-measured"

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


# ---------------------------------------------------------------- fixtures


class _Handler(http.server.BaseHTTPRequestHandler):
    payload: dict = {}
    status: int = 200

    def do_GET(self):
        if self.path.endswith("/models"):
            body = json.dumps(self.payload).encode()
            self.send_response(self.status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def _server(payload: dict, status: int = 200):
    _Handler.payload = payload
    _Handler.status = status
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/v1"


def _models(free: list[tuple[str, int]], paid: tuple[str, ...] = ("deepseek/deepseek-v4-flash-0731",)) -> dict:
    data = [{"id": mid, "context_length": ctx} for mid, ctx in free]
    data += [{"id": mid, "context_length": 1048576} for mid in paid]
    return {"object": "list", "data": data}


# Issues #1744/#1745: the fixture is DERIVED from the shipped chain at test time. A frozen
# catalogue literal here is exactly what reddened three keeper PRs on every live refresh.
SHIPPED = F.read_chain(CHAIN)
SHIPPED_FREE = F.free_steps(SHIPPED)
SHIPPED_PRIMARY = F.primary_step(SHIPPED)


def _scratch(td: Path, base_url: str) -> Path:
    root = td
    (root / "scripts").mkdir(parents=True)
    (root / "agents").mkdir(parents=True)
    shutil.copy(ROOT / "Makefile", root / "Makefile")
    for name in ("free_model_refresh.py", "require_env.py", "agent_model_chain.py"):
        shutil.copy(ROOT / "scripts" / name, root / "scripts" / name)
    data = json.loads(CHAIN.read_text(encoding="utf-8"))
    data["base_url"] = base_url
    (root / "agents" / "model_chain.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return root


def run_refresh(*args: str, root: Path, key: str | None = PLACEHOLDER) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop(KEY_NAME, None)
    if key is not None:
        env[KEY_NAME] = key
    cmd = [sys.executable, str(root / "scripts" / "free_model_refresh.py"), "--root", str(root), *args]
    return subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, env=env)


def chain_of(root: Path) -> dict:
    return json.loads((root / "agents" / "model_chain.json").read_text(encoding="utf-8"))


def non_free(root: Path) -> list[dict]:
    return [e for e in chain_of(root)["chain"] if e["role"] not in ("primary", "fallback")]


# ---------------------------------------------------------------- behaviour


def test_a_new_free_model_is_appended_with_its_live_context_and_the_non_free_tiers_survive():
    with tempfile.TemporaryDirectory() as td:
        srv, url = _server(_models(SHIPPED_FREE + [("newlab/new-model:free", 55555)]))
        try:
            root = _scratch(Path(td), url)
            before_non_free = non_free(root)
            proc = run_refresh("--write", root=root)
            out = proc.stdout + proc.stderr
            check("a new free model refreshes green", proc.returncode == 0, out[-200:])
            data = chain_of(root)
            free = [e for e in data["chain"] if e["role"] in ("primary", "fallback")]
            check("the new id is appended as a fallback with its LIVE context_window",
                  any(e["model"] == "newlab/new-model:free" and e["context_window"] == 55555
                      and e["role"] == "fallback" for e in free), str(free[-2:]))
            check("the new alias is generated, lowercase and unique",
                  len({e["alias"] for e in data["chain"]}) == len(data["chain"])
                  and all(e["alias"].startswith("free-") for e in free if e["model"] == "newlab/new-model:free"),
                  str([e["alias"] for e in free]))
            check("the local_fallback tier and the paid last_resort are UNTOUCHED",
                  non_free(root) == before_non_free, str(non_free(root)))
            check("the primary is still the first free step", free[0]["role"] == "primary", str(free[0]))
            check("the measured block records the refresh read (rule 2)",
                  data["measured"]["at"] and "GET /v1/models" in data["measured"]["how"]
                  and data["measured"]["refresh_history"][-1]["added"] == ["newlab/new-model:free"],
                  str(data["measured"])[:200])
            check("the refresh is announced by name", "added free-new-model" in out, out[-200:])
        finally:
            srv.shutdown()


def test_a_retired_free_model_drops_and_a_retired_primary_hands_over():
    with tempfile.TemporaryDirectory() as td:
        # Derive both the dropped step and the successor from the shipped chain, so the
        # case follows the live catalogue instead of a frozen id/alias/context snapshot.
        retired_model = SHIPPED_PRIMARY["model"]
        successor_model = SHIPPED_FREE[1][0]
        srv, url = _server(_models(SHIPPED_FREE[1:]))  # the shipped primary is gone
        try:
            root = _scratch(Path(td), url)
            proc = run_refresh("--write", root=root)
            out = proc.stdout + proc.stderr
            check("a retired primary refreshes green", proc.returncode == 0, out[-200:])
            data = chain_of(root)
            free = [e for e in data["chain"] if e["role"] in ("primary", "fallback")]
            check("the retired id is gone from the chain",
                  all(e["model"] != retired_model for e in data["chain"]), str(free))
            check("the first survivor becomes the primary",
                  free[0]["model"] == successor_model and free[0]["role"] == "primary", str(free[0]))
            check("the retirement is announced and recorded",
                  f"retired {SHIPPED_PRIMARY['alias']}" in out
                  and data["measured"]["refresh_history"][-1]["retired"] == [retired_model],
                  out[-200:])
            check("the paid pin stays LAST", data["chain"][-1]["role"] == "last_resort", str(data["chain"][-1]))
        finally:
            srv.shutdown()


def test_an_unchanged_live_set_writes_nothing():
    with tempfile.TemporaryDirectory() as td:
        srv, url = _server(_models(SHIPPED_FREE))
        try:
            root = _scratch(Path(td), url)
            before = (root / "agents" / "model_chain.json").read_bytes()
            proc = run_refresh("--write", root=root)
            out = proc.stdout + proc.stderr
            check("an unchanged set is a green no-op", proc.returncode == 0 and "no change" in out, out[-200:])
            check("the chain file is BYTE-IDENTICAL after a no-op",
                  (root / "agents" / "model_chain.json").read_bytes() == before, "")
        finally:
            srv.shutdown()


def test_a_context_drift_follows_the_live_read():
    with tempfile.TemporaryDirectory() as td:
        # Drift a survivor, never a frozen id: whichever free model the chain currently ships
        # last is the one whose context this case proves follows the live read.
        drift_model = SHIPPED_FREE[-1][0]
        drifted = [(mid, 999999 if mid == drift_model else ctx) for mid, ctx in SHIPPED_FREE]
        srv, url = _server(_models(drifted))
        try:
            root = _scratch(Path(td), url)
            proc = run_refresh("--write", root=root)
            check("a context drift refreshes green", proc.returncode == 0, proc.stderr[-200:])
            survivor = next(e for e in chain_of(root)["chain"] if e["model"] == drift_model)
            check("the surviving model's context_window follows the live read",
                  survivor["context_window"] == 999999, str(survivor))
        finally:
            srv.shutdown()


def test_an_absent_credential_or_a_failed_read_is_exit_2_and_writes_nothing():
    with tempfile.TemporaryDirectory() as td:
        srv, url = _server(_models(SHIPPED_FREE + [("newlab/new-model:free", 55555)]))
        try:
            root = _scratch(Path(td), url)
            before = (root / "agents" / "model_chain.json").read_bytes()
            proc = run_refresh("--write", root=root, key=None)
            out = proc.stdout + proc.stderr
            check("absent credential -> exit 2", proc.returncode == 2, f"rc={proc.returncode}")
            check("the refusal NAMES the variable", KEY_NAME in out, out[-200:])
            check("nothing was written", (root / "agents" / "model_chain.json").read_bytes() == before, "")
            check("no credential VALUE is printed", PLACEHOLDER not in out, "")
        finally:
            srv.shutdown()

    with tempfile.TemporaryDirectory() as td:
        srv, url = _server(_models(SHIPPED_FREE), status=500)
        try:
            root = _scratch(Path(td), url)
            before = (root / "agents" / "model_chain.json").read_bytes()
            proc = run_refresh("--write", root=root)
            out = proc.stdout + proc.stderr
            check("a failed read -> exit 2 UNDECIDABLE, never a silent clean",
                  proc.returncode == 2 and "UNDECIDABLE" in out, out[-200:])
            check("a failed read writes nothing", (root / "agents" / "model_chain.json").read_bytes() == before, "")
        finally:
            srv.shutdown()

    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td), "http://127.0.0.1:1/v1")  # nothing listens here
        before = (root / "agents" / "model_chain.json").read_bytes()
        proc = run_refresh("--write", root=root)
        check("an unreachable endpoint -> exit 2, nothing written",
              proc.returncode == 2 and (root / "agents" / "model_chain.json").read_bytes() == before,
              proc.stderr[-200:])


def test_a_live_set_with_no_free_model_or_no_context_is_refused():
    with tempfile.TemporaryDirectory() as td:
        srv, url = _server(_models([]))
        try:
            root = _scratch(Path(td), url)
            before = (root / "agents" / "model_chain.json").read_bytes()
            proc = run_refresh("--write", root=root)
            out = proc.stdout + proc.stderr
            check("no free model live -> exit 1 refusal (the free tier may not be emptied)",
                  proc.returncode == 1 and "REFUSED" in out, out[-200:])
            check("the refusal writes nothing", (root / "agents" / "model_chain.json").read_bytes() == before, "")
        finally:
            srv.shutdown()

    with tempfile.TemporaryDirectory() as td:
        payload = {"data": [{"id": "x/y:free"}]}  # free id, NO context_length
        srv, url = _server(payload)
        try:
            root = _scratch(Path(td), url)
            proc = run_refresh("--write", root=root)
            check("a free id without a measured context_length -> exit 2 (rule 2)",
                  proc.returncode == 2 and "context_length" in proc.stderr, proc.stderr[-200:])
        finally:
            srv.shutdown()


def test_a_dry_run_plans_without_writing_and_the_refreshed_chain_passes_the_real_gate():
    with tempfile.TemporaryDirectory() as td:
        srv, url = _server(_models(SHIPPED_FREE + [("newlab/new-model:free", 55555)]))
        try:
            root = _scratch(Path(td), url)
            before = (root / "agents" / "model_chain.json").read_bytes()
            proc = run_refresh("--dry-run", root=root)
            out = proc.stdout + proc.stderr
            check("--dry-run announces the plan and writes nothing",
                  proc.returncode == 0 and "DRY RUN" in out
                  and (root / "agents" / "model_chain.json").read_bytes() == before, out[-200:])

            run_refresh("--write", root=root)
            # Issue #1798: the weekly refresh must keep the judge's fallback alias list in
            # step with the free tier it just changed, or the real gate below refuses it.
            refreshed = chain_of(root)
            aliases = refreshed["auxiliary"]["goal_judge"]["fallback_aliases"]
            free_aliases = [e["alias"] for e in refreshed["chain"]
                            if e.get("role") in ("primary", "fallback")]
            check("the refreshed chain keeps every free step on the judge fallback",
                  all(a in aliases for a in free_aliases), f"aliases={aliases} free={free_aliases}")
            # Restore the shipped chain's OWN read fields when it names them: the
            # refreshed chain must satisfy the REAL offline gate (shape, pins,
            # credential NAMES). A `nous` chain names neither — the stub was only
            # the transport (issue #1203), so leave those fields absent.
            data = chain_of(root)
            shipped = json.loads(CHAIN.read_text(encoding="utf-8"))
            for field in ("base_url", "key_env"):
                if field in shipped:
                    data[field] = shipped[field]
                else:
                    data.pop(field, None)  # the stub's transport is not part of the shipped chain
            (root / "agents" / "model_chain.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            sys.path.insert(0, str(root / "scripts"))
            import importlib
            amc = importlib.import_module("agent_model_chain")
            importlib.reload(amc)
            chain, fatal = amc.read_chain(root)
            pins, pin_problems = amc.read_makefile_pins(root)
            problems = amc.chain_problems(chain, pins) + pin_problems
            check("the refreshed chain passes the REAL chain gate offline (shape + pins + NAMES)",
                  fatal is None and not problems, str(fatal) + str(problems))
        finally:
            srv.shutdown()


def test_the_pr_body_is_a_keeper_with_no_closing_keyword():
    with tempfile.TemporaryDirectory() as td:
        srv, url = _server(_models(SHIPPED_FREE + [("newlab/new-model:free", 55555)]))
        try:
            root = _scratch(Path(td), url)
            run_refresh("--write", root=root)
            env = dict(os.environ)
            env["RUN_URL"] = "https://example.invalid/run/1"
            proc = subprocess.run([sys.executable, str(root / "scripts" / "free_model_refresh.py"),
                                   "--root", str(root), "--pr-body"],
                                  capture_output=True, text=True, env=env)
            body = proc.stdout
            check("--pr-body prints a keeper body naming the read and the change",
                  proc.returncode == 0 and "newlab/new-model:free" in body
                  and "https://example.invalid/run/1" in body, body[:200])
            check("the keeper body carries NO closing keyword (it implements no issue)",
                  "closes #" not in body.lower() and "fixes #" not in body.lower(), body[:200])
            check("the keeper body refs the refresh issue", "#1195" in body, body[:200])
        finally:
            srv.shutdown()


def test_the_seam_is_wired_where_it_bites():
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("the Makefile defines the internal recipe and the public target",
          "_free-model-refresh:\n\tpython3 scripts/free_model_refresh.py" in mk
          and "free-model-refresh: ##" in mk, "")
    rb = (ROOT / ".github" / "workflows" / "refresh-bot.yml").read_text(encoding="utf-8")
    check("refresh-bot (the ONLY scheduled pipeline, rule 6t) runs `make free-model-refresh`",
          "make free-model-refresh" in rb, "")
    check("the refresh lands through the shared keeper seam, never a direct push",
          "keeper-pr" in rb and "ci/free-model-refresh" in rb, "")
    check("no OTHER workflow gains a schedule for the refresh (rule 6t)",
          not any("free_model_refresh" in (ROOT / ".github" / "workflows" / p.name).read_text(encoding="utf-8")
                  for p in (ROOT / ".github" / "workflows").iterdir()
                  if p.suffix == ".yml" and p.name != "refresh-bot.yml"), "")
    check("this suite is discovered by `make test`", wired(__file__), "")


def test_fixtures_follow_the_chain_not_a_frozen_catalogue():
    """Issues #1744/#1745: the fixtures must follow the shipped data, not a snapshot of it.

    A synthetic chain whose free ids/aliases are absent from every frozen literal REDs the old
    hardcoded shape (no derivation existed) and GREENs this one. It also proves the shipped
    fixture is derived from the shipped chain on THIS revision — the exact assertion the
    keeper head failed when the live catalogue retired two models.
    """
    synthetic = {"chain": [
        {"model": "synthetic-zeta/alpha:free", "alias": "free-zeta", "role": "primary", "context_window": 11111},
        {"model": "synthetic-eta/beta:free", "alias": "free-eta", "role": "fallback", "context_window": 22222},
        {"model": "local-model", "alias": "local-x", "role": "local_fallback", "context_window": 4096},
        {"model": "paid/model", "alias": "paid-x", "role": "last_resort", "context_window": 8192},
    ]}
    check("free-step fixture follows a synthetic chain",
          F.free_steps(synthetic) == [("synthetic-zeta/alpha:free", 11111),
                                      ("synthetic-eta/beta:free", 22222)])
    check("primary fixture follows a synthetic chain",
          F.primary_step(synthetic)["model"] == "synthetic-zeta/alpha:free")
    check("alias order follows a synthetic chain",
          F.alias_order(synthetic) == ["free-zeta", "free-eta", "local-x", "paid-x"])
    check("fallback model order follows a synthetic chain",
          F.fallback_models(synthetic) == ["synthetic-eta/beta:free", "local-model", "paid/model"])
    check("the shipped fixture is derived from the shipped chain, not frozen",
          SHIPPED_FREE == F.free_steps(SHIPPED), str(SHIPPED_FREE))


def main() -> int:
    print("free_model_refresh (issue #1195): the weekly live free-tier refresh")
    test_a_new_free_model_is_appended_with_its_live_context_and_the_non_free_tiers_survive()
    test_a_retired_free_model_drops_and_a_retired_primary_hands_over()
    test_an_unchanged_live_set_writes_nothing()
    test_a_context_drift_follows_the_live_read()
    test_an_absent_credential_or_a_failed_read_is_exit_2_and_writes_nothing()
    test_a_live_set_with_no_free_model_or_no_context_is_refused()
    test_a_dry_run_plans_without_writing_and_the_refreshed_chain_passes_the_real_gate()
    test_the_pr_body_is_a_keeper_with_no_closing_keyword()
    test_the_seam_is_wired_where_it_bites()
    test_fixtures_follow_the_chain_not_a_frozen_catalogue()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
