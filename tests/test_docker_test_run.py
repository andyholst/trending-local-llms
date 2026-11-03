#!/usr/bin/env python3
"""The TEST_RUN client removes its container when it dies (issue #720)."""
from __future__ import annotations

import os
import signal
import stat
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "docker_test_run.sh"

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


def test_make_test_goes_through_the_wrapper():
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    start = mk.find("TEST_RUN :=")
    body = mk[start:mk.find("\n\n", start)]
    check("TEST_RUN starts the wrapper", "bash scripts/docker_test_run.sh" in body, body)
    check("TEST_RUN still asks docker to remove a container that exits", "--rm" in body, body)
    check("TEST_RUN still mounts the worktree and the test image",
          '-v "$$PWD":/workspace' in body and "$(TEST_IMAGE)" in body, body)
    for flag in ("-e NOUS_API_KEY", "-e FIRECRAWL_API_KEY", "-e HF_TOKEN",
                 "-e $(NERVE_KEY_ENV)", "$(AGENT_SHELL_FORWARD)"):
        check(f"TEST_RUN still forwards {flag}", flag in body, body)
    text = SCRIPT.read_text(encoding="utf-8")
    check("wrapper names the container", '--name "$name"' in text, text)
    check("wrapper removes that name", 'docker rm -f "$name"' in text, text)
    check("wrapper watches from its own session", "setsid" in text, text)


def _fake_docker(bin_dir: Path) -> None:
    path = bin_dir / "docker"
    path.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$*\" >> \"$DOCKER_LOG\"\n"
        "if [ \"$1\" = run ]; then\n"
        "  sleep 30\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def test_a_killed_client_removes_the_container():
    with tempfile.TemporaryDirectory() as tmp:
        bin_dir = Path(tmp) / "bin"
        bin_dir.mkdir()
        log = Path(tmp) / "docker.log"
        _fake_docker(bin_dir)
        env = {**os.environ, "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}", "DOCKER_LOG": str(log)}
        proc = subprocess.Popen(
            ["bash", str(SCRIPT), "--rm", "trending-local-llms-test:latest", "make", "_test"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 3
        started = False
        while time.monotonic() < deadline:
            if log.is_file() and log.read_text(encoding="utf-8").startswith("run "):
                started = True
                break
            time.sleep(0.05)
        check("the wrapper reached docker run", started, log.read_text(encoding="utf-8") if log.is_file() else "no log")
        os.kill(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)
        removed = False
        text = ""
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            text = log.read_text(encoding="utf-8") if log.is_file() else ""
            if "rm -f tll-test-" in text:
                removed = True
                break
            time.sleep(0.1)
        check("a killed client removes the named container", removed, text)
        names = []
        for line in text.splitlines():
            if line.startswith("run "):
                parts = line.split()
                if "--name" in parts:
                    names.append(parts[parts.index("--name") + 1])
        check("the removal names the container this run started",
              bool(names) and any(f"rm -f {name}" in text for name in names), text)


def main() -> int:
    test_make_test_goes_through_the_wrapper()
    test_a_killed_client_removes_the_container()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
