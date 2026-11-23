#!/usr/bin/env python3
"""Behavioural tests for scripts/local_endpoint_probe.py — the local-tier outage detector (issue #1352).

The rule: the chain's `local_fallback` tier is the owner's own box, and a silent outage there is
invisible to every gate. The seam probes it with a CAPPED timeout, records the result in the
chain's `measured.local`, and its offline `--check` refuses a missing/drifted record and REPORTS
staleness loudly without touching the endpoint — so auto-merge never depends on a host box.

Every test drives the REAL script end to end against a scratch tree and a REAL local HTTP server
(rule 6m: the only stand-in is the external endpoint; the production code that builds the request
still runs). Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import http.server
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "local_endpoint_probe.py"
CHAIN = ROOT / "agents" / "model_chain.json"

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
    delay: float = 0.0

    def do_POST(self):
        if self.delay:
            time.sleep(self.delay)
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        if self.path.endswith("/chat/completions"):
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


def _server(payload: dict, status: int = 200, delay: float = 0.0):
    _Handler.payload = payload
    _Handler.status = status
    _Handler.delay = delay
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/v1"


OK_PAYLOAD = {"object": "chat.completion", "choices": [{"message": {"content": "pong"}}]}


def _scratch(td: Path, base_url: str) -> Path:
    root = td
    (root / "scripts").mkdir(parents=True)
    (root / "agents").mkdir(parents=True)
    shutil.copy(ROOT / "Makefile", root / "Makefile")
    shutil.copy(SCRIPT, root / "scripts" / "local_endpoint_probe.py")
    data = json.loads(CHAIN.read_text(encoding="utf-8"))
    for row in data["chain"]:
        if row.get("role") == "local_fallback":
            row["base_url"] = base_url
    # Start every scratch tree with NO probe record: the shipped chain now carries one, and
    # each test asserts on the record IT writes.
    measured = data.get("measured") if isinstance(data.get("measured"), dict) else {}
    measured.pop("local", None)
    (root / "agents" / "model_chain.json").write_text(json.dumps(data, indent=2) + "\n",
                                                      encoding="utf-8")
    return root


def run_probe(*args: str, root: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(root / "scripts" / "local_endpoint_probe.py"),
           "--root", str(root), *args]
    return subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)


def chain_of(root: Path) -> dict:
    return json.loads((root / "agents" / "model_chain.json").read_text(encoding="utf-8"))


def local_record(root: Path) -> dict:
    return chain_of(root)["measured"]["local"]


# ---------------------------------------------------------------- behaviour


def test_a_live_endpoint_is_probed_recorded_and_reported():
    with tempfile.TemporaryDirectory() as td:
        srv, url = _server(OK_PAYLOAD)
        try:
            root = _scratch(Path(td), url)
            proc = run_probe("--probe", "--timeout", "5", root=root)
            out = proc.stdout + proc.stderr
            check("a live endpoint probes green", proc.returncode == 0, out[-200:])
            rec = local_record(root)
            check("the result is recorded in measured.local.last_probe",
                  rec["last_probe"]["ok"] is True and rec["last_probe"]["http"] == 200
                  and rec["last_probe"]["endpoint"] == url
                  and rec["last_probe"]["model"] == "qwen3.8-flash-next-iq3_xxs",
                  str(rec)[:200])
            check("the probe is appended to an additive probe_history",
                  len(rec["probe_history"]) == 1
                  and rec["probe_history"][-1]["ok"] is True, str(rec)[:200])
            check("the record names the clock it was taken at", bool(rec["last_probe"]["at"]),
                  str(rec)[:200])
            chk = run_probe("--check", root=root)
            out = chk.stdout + chk.stderr
            check("the offline check is green on a fresh matching record",
                  chk.returncode == 0 and "ok" in out and "STALE" not in out, out[-200:])
            rep = run_probe("--report", root=root)
            check("--report prints the record as data",
                  rep.returncode == 0 and "qwen3.8-flash-next-iq3_xxs" in rep.stdout, rep.stdout[:200])
        finally:
            srv.shutdown()


def test_a_dead_endpoint_is_recorded_as_down_and_the_check_reports_it():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td), "http://127.0.0.1:1/v1")  # nothing listens here
        proc = run_probe("--probe", "--timeout", "2", root=root)
        out = proc.stdout + proc.stderr
        check("a dead endpoint probes exit 1, never a silent clean",
              proc.returncode == 1 and "DOWN" in out, out[-200:])
        rec = local_record(root)
        check("the DOWN result is still recorded (the outage is the signal)",
              rec["last_probe"]["ok"] is False and rec["last_probe"]["http"] == 0,
              str(rec)[:200])
        chk = run_probe("--check", root=root)
        out = chk.stdout + chk.stderr
        check("the offline check REPORTS the down state without failing",
              chk.returncode == 0 and "DOWN" in out, out[-200:])


def test_a_slow_endpoint_is_capped_by_the_timeout_pin():
    with tempfile.TemporaryDirectory() as td:
        srv, url = _server(OK_PAYLOAD, delay=5.0)
        try:
            root = _scratch(Path(td), url)
            started = time.monotonic()
            proc = run_probe("--probe", "--timeout", "1", root=root)
            elapsed = time.monotonic() - started
            out = proc.stdout + proc.stderr
            check("a slow endpoint is a DOWN result, not a hang",
                  proc.returncode == 1 and "DOWN" in out, out[-200:])
            check("the probe is CAPPED near the timeout pin (it does not wait for the server)",
                  elapsed < 4.0, f"elapsed={elapsed:.2f}s")
            check("the recorded latency respects the cap",
                  local_record(root)["last_probe"]["latency_s"] < 4.0,
                  str(local_record(root))[:200])
        finally:
            srv.shutdown()


def test_a_missing_record_is_refused_and_a_drifted_record_is_refused():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td), "http://127.0.0.1:1/v1")
        proc = run_probe("--check", root=root)
        out = proc.stdout + proc.stderr
        check("a chain that was never probed is exit 1, naming the remedy",
              proc.returncode == 1 and "local-endpoint-probe" in out, out[-200:])

    with tempfile.TemporaryDirectory() as td:
        srv, url = _server(OK_PAYLOAD)
        try:
            root = _scratch(Path(td), url)
            run_probe("--probe", "--timeout", "5", root=root)
            data = chain_of(root)
            for row in data["chain"]:
                if row.get("role") == "local_fallback":
                    row["base_url"] = url + "/moved"
            (root / "agents" / "model_chain.json").write_text(
                json.dumps(data, indent=2) + "\n", encoding="utf-8")
            proc = run_probe("--check", root=root)
            out = proc.stdout + proc.stderr
            check("a record that did not follow the chain is exit 1, naming both endpoints",
                  proc.returncode == 1 and "did not follow the chain" in out and "/moved" in out,
                  out[-200:])
        finally:
            srv.shutdown()


def test_a_stale_record_is_reported_loudly_without_failing():
    with tempfile.TemporaryDirectory() as td:
        srv, url = _server(OK_PAYLOAD)
        try:
            root = _scratch(Path(td), url)
            run_probe("--probe", "--timeout", "5", root=root)
            data = chain_of(root)
            stale = "2020-01-01T00:00:00Z"
            data["measured"]["local"]["last_probe"]["at"] = stale
            (root / "agents" / "model_chain.json").write_text(
                json.dumps(data, indent=2) + "\n", encoding="utf-8")
            proc = run_probe("--check", "--max-age-hours", "24", root=root)
            out = proc.stdout + proc.stderr
            check("a stale record is REPORTED loudly (STALE) but does not fail the gate",
                  proc.returncode == 0 and "STALE" in out and "age_h=" in out, out[-200:])
            check("the staleness is measured in hours against the pin",
                  "age_h=" in out and float(out.split("age_h=")[1].split()[0]) > 24, out[-200:])
        finally:
            srv.shutdown()


def test_an_unreadable_chain_is_exit_2_never_a_silent_clean():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td), "http://127.0.0.1:1/v1")
        (root / "agents" / "model_chain.json").write_text('{"chain": [', encoding="utf-8")
        proc = run_probe("--check", root=root)
        out = proc.stdout + proc.stderr
        check("a truncated chain exits 2 UNDECIDABLE", proc.returncode == 2 and "UNDECIDABLE" in out,
              out[-200:])
        (root / "agents" / "model_chain.json").unlink()
        proc = run_probe("--probe", root=root)
        check("a missing chain exits 2 and names the file",
              proc.returncode == 2 and "agents/model_chain.json" in proc.stderr, proc.stderr[-200:])


def test_a_dry_run_probes_without_writing():
    with tempfile.TemporaryDirectory() as td:
        srv, url = _server(OK_PAYLOAD)
        try:
            root = _scratch(Path(td), url)
            before = (root / "agents" / "model_chain.json").read_bytes()
            proc = run_probe("--probe", "--dry-run", "--timeout", "5", root=root)
            out = proc.stdout + proc.stderr
            check("--dry-run announces and writes nothing",
                  proc.returncode == 0 and "DRY RUN" in out
                  and (root / "agents" / "model_chain.json").read_bytes() == before, out[-200:])
        finally:
            srv.shutdown()


def test_the_seam_is_wired_where_it_bites():
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    for pin in ("LOCAL_PROBE_TIMEOUT_SECONDS", "LOCAL_PROBE_MAX_AGE_HOURS", "LOCAL_PROBE_HISTORY_MAX"):
        check(f"the Makefile pins {pin}", f"{pin} ?=" in mk, "")
    check("`make lint` runs local-endpoint-probe-check (so the offline half bites)",
          "local-endpoint-probe-check" in mk.split("lint: ##", 1)[1].split("\n\n", 1)[0], "")
    check("the internal recipe runs the script (no workflow reaches past the Makefile)",
          "_local-endpoint-probe-check:\n\tpython3 scripts/local_endpoint_probe.py --check" in mk, "")
    check("no workflow reaches into scripts/local_endpoint_probe.py directly (rule 6m)",
          not any("local_endpoint_probe" in (ROOT / ".github" / "workflows" / p.name).read_text(encoding="utf-8")
                  for p in (ROOT / ".github" / "workflows").iterdir() if p.suffix == ".yml"), "")
    check("the live probe is NOT wired into a merge gate (auto-merge cannot depend on a host box)",
          "local-endpoint-probe" not in (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text(encoding="utf-8")
          and "local-endpoint-probe" not in mk.split("lint: ##", 1)[1].split("\n\n", 1)[0].replace(
              "local-endpoint-probe-check", ""), "")
    check("this suite is discovered by `make test`", wired(__file__), "")


def test_the_shipped_chain_carries_a_record_and_the_offline_check_is_green():
    proc = run_probe("--check", root=ROOT)
    out = proc.stdout + proc.stderr
    check("the shipped chain carries a recorded local-tier probe", proc.returncode == 0, out[-200:])
    check("the shipped record follows the shipped chain's local tier",
          "FAIL" not in out, out[-200:])
    check("the chain's own gate still passes with the record present",
          run_probe("--check", root=ROOT).returncode == 0, "")


def main() -> int:
    print("local_endpoint_probe (issue #1352): the chain local tier's capped probe + staleness check")
    test_a_live_endpoint_is_probed_recorded_and_reported()
    test_a_dead_endpoint_is_recorded_as_down_and_the_check_reports_it()
    test_a_slow_endpoint_is_capped_by_the_timeout_pin()
    test_a_missing_record_is_refused_and_a_drifted_record_is_refused()
    test_a_stale_record_is_reported_loudly_without_failing()
    test_an_unreadable_chain_is_exit_2_never_a_silent_clean()
    test_a_dry_run_probes_without_writing()
    test_the_seam_is_wired_where_it_bites()
    test_the_shipped_chain_carries_a_record_and_the_offline_check_is_green()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
