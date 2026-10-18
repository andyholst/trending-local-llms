#!/usr/bin/env python3
"""Does the redactor really keep a secret VALUE off the console? This file is its proof.

`scripts/scrub_log.py` exists because a bot's agent stream IS the job's console log: GitHub masks
the secret values it *registers*, so a transformed one (URL-encoded, base64, a slice) sails past a
mask (rule 3d, issues #346/#351). Every assertion here drives the REAL script — no stub, no copy of
its logic — against a REAL environment value, through the CLI a workflow runs.

secret-output: test value — the marker the guard looks for: the credential-shaped string below is a
deliberate, non-live test value (`sk-` + the alphabet), which is exactly what the marker is for.

NO-SKIP POLICY: a missing prerequisite is a LOUD FAILURE, never a skip.

Wired into `make test` (rule 6d). Runs as a plain script (the test image's pytest path is dead,
issue #176) and under pytest.
"""
from __future__ import annotations

import base64
import os
import subprocess
import tempfile
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "scrub_log.py"

_PASS = 0
_FAIL = 0

#: A fake credential VALUE. Not a real key: it is what the environment carries in these tests, so
#: the redactor has something real to redact. Never printed by the assertions themselves.
FAKE_VALUE = "NEVER-PRINT-THIS-0123456789"
#: A token-SHAPED literal, for the case where a value reaches the log without entering this
#: process's environment (a child printed one it read elsewhere).
FAKE_TOKEN = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"


def check(name, cond, detail=""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _run(log_body: str, extra: list[str] | None = None, tmp: Path | None = None):
    """Drive the SHIPPED script through its CLI, with the fake value in the environment."""
    td = tmp or Path(tempfile.mkdtemp())
    src = td / "implement.log"
    src.write_text(log_body)
    env = dict(os.environ, NOUS_API_KEY=FAKE_VALUE)
    out = td / "implement.scrubbed.log"
    cmd = ["python3", str(SCRIPT), "--in", str(src), "--out", str(out), "--tail", "40"]
    if extra:
        cmd += extra
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return r, src, out


def test_every_spelling_of_the_value_is_replaced():
    """The measured leak surface: a value can arrive raw, URL-encoded or base64-encoded."""
    raw = FAKE_VALUE
    quoted = urllib.parse.quote(FAKE_VALUE, safe="")
    b64 = base64.b64encode(FAKE_VALUE.encode()).decode()
    body = (f"agent says: the key is {raw}\n"
            f"agent fetches: /v1?key={quoted}\n"
            f"agent posts: {{\"key\": \"{b64}\"}}\n"
            f"agent prints a token shape: {FAKE_TOKEN}\n"
            f"and a bearer header: Authorization: Bearer {FAKE_TOKEN}\n"
            "harmless line\n")
    r, _, out = _run(body)
    console = r.stdout + r.stderr
    artifact = out.read_text()
    check("scrub-log: exits 0 on a normal log", r.returncode == 0, r.stderr[-200:])
    for label, needle in (("raw", raw), ("url-encoded", quoted), ("base64", b64),
                          ("token shape", FAKE_TOKEN)):
        check(f"scrub-log: the {label} spelling never reaches the console", needle not in console,
              console[:200])
        check(f"scrub-log: nor the redacted artifact ({label})", needle not in artifact,
              artifact[:200])
    check("scrub-log: the redaction COUNT is reported (never a value)",
          "redaction(s)" in console and FAKE_VALUE not in console, console[:200])
    check("scrub-log: the harmless line survives", "harmless line" in console)


def test_the_value_is_never_printed_nor_a_fragment_of_it():
    """A mask that printed first/last characters would still be a leak (rule 3d)."""
    r, _, out = _run(f"prefix {FAKE_VALUE} suffix\n")
    console = r.stdout + r.stderr
    check("scrub-log: the first 4 characters are not printed", FAKE_VALUE[:4] not in console,
          repr(console))
    check("scrub-log: the last 4 characters are not printed", FAKE_VALUE[-4:] not in console,
          repr(console))
    check("scrub-log: the mask is a fixed marker", "***" in out.read_text(), out.read_text())


def test_the_printed_output_is_bounded_to_the_tail():
    body = "".join(f"line {i}\n" for i in range(1, 201))
    r, _, out = _run(body)
    # only the log's OWN lines: the omission note is printed with the same `[agent] ` prefix.
    printed = [l for l in r.stdout.splitlines() if l.startswith("[agent] line ")]
    check("scrub-log: at most the requested tail is printed", len(printed) <= 40, len(printed))
    check("scrub-log: the newest lines are the ones printed", "line 200" in r.stdout, r.stdout[-200:])
    check("scrub-log: the REDACTED artifact holds the whole log",
          out.read_text().count("line ") == 200, out.read_text().count("line "))
    check("scrub-log: the omission is stated, never silent", "omitted" in r.stdout, r.stdout[-200:])


def test_a_missing_log_is_loud():
    """A capture that cannot be read must never look like a clean run."""
    td = Path(tempfile.mkdtemp())
    env = dict(os.environ, NOUS_API_KEY=FAKE_VALUE)
    r = subprocess.run(["python3", str(SCRIPT), "--in", str(td / "nope.log"), "--tail", "5"],
                       capture_output=True, text=True, env=env)
    check("scrub-log: a missing log exits non-zero", r.returncode == 2, r.returncode)
    check("scrub-log: and names the path", "nope.log" in r.stderr, r.stderr[-200:])


def test_an_empty_log_is_not_an_error():
    r, _, _ = _run("")
    check("scrub-log: an empty log is fine (exit 0)", r.returncode == 0, r.stderr[-200:])


def test_a_short_value_is_not_shredded():
    """MIN_VALUE_LEN exists so replacing a 1–3 character value cannot shred the whole log."""
    td = Path(tempfile.mkdtemp())
    src = td / "implement.log"
    src.write_text("the agent printed a 3-character value\n")
    env = dict(os.environ, NOUS_API_KEY="abc")
    r = subprocess.run(["python3", str(SCRIPT), "--in", str(src), "--tail", "5"],
                       capture_output=True, text=True, env=env)
    check("scrub-log: a too-short value is not treated as a secret to replace",
          "the agent printed a 3-character value" in r.stdout, r.stdout)


def test_the_environment_carries_no_other_spelling():
    """The redactor reads the value from the environment BY NAME; it must cover every name."""
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    import check_secret_output as cso
    import scrub_log

    env = {name: f"{name}-VALUE-0123456789" for name in cso.SECRET_VARS}
    found = scrub_log.environment_values(env)
    for name in cso.SECRET_VARS:
        value = env[name]
        check(f"scrub-log: {name}'s value is a spelling the redactor replaces",
              value in found, sorted(found)[:3])
    check("scrub-log: the name list is the guard's list, not a second copy",
          set(env) == set(cso.SECRET_VARS), "")


def _impl_step_snippet() -> str:
    """The implement step's `run:` text, read from the workflow file itself.

    Read from the file (not a copy) so the assertions below apply to whatever the step REALLY is:
    a test asserting a copy would keep passing after the workflow regressed. Parsed by hand so the
    suite needs no YAML at all (it also runs on the host).
    """
    lines = (ROOT / ".github" / "workflows" / "issue-bot.yml").read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if "- name: Implement the issue" in l)
    run_at = next(i for i in range(start, len(lines)) if lines[i].strip().startswith("run:"))
    indent = len(lines[run_at]) - len(lines[run_at].lstrip())
    body: list[str] = []
    for line in lines[run_at + 1:]:
        if line.strip() and (len(line) - len(line.lstrip())) <= indent:
            break
        body.append(line)
    return "\n".join(l[10:] if l.startswith(" " * 10) else l for l in body)


def _stub_make(bindir: Path, out: Path, rc: int) -> str:
    """A `make` on PATH that stands in for the EXTERNAL command (rule 6m): it prints an agent
    stream carrying the value in three spellings, and delegates `scrub-log` to the REAL script."""
    bindir.mkdir(parents=True, exist_ok=True)
    stub = bindir / "make"
    stub.write_text(f"""#!/bin/sh
if [ "$1" = "implement-issue" ]; then
  echo "agent: reading the post"
  echo "agent: sending header Authorization: Bearer $NOUS_API_KEY"
  echo "agent: the key is $NOUS_API_KEY"
  echo "agent: a token shape {FAKE_TOKEN}"
  echo "agent: done"
  exit {rc}
fi
if [ "$1" = "scrub-log" ]; then
  shift
  FILE=""; LOG_OUT=""; TAIL="40"
  for a in "$@"; do
    case "$a" in
      FILE=*) FILE="${{a#FILE=}}" ;;
      LOG_OUT=*) LOG_OUT="${{a#LOG_OUT=}}" ;;
      TAIL=*) TAIL="${{a#TAIL=}}" ;;
    esac
  done
  exec python3 "{SCRIPT}" --in "$FILE" --out "$LOG_OUT" --tail "$TAIL"
fi
echo "stub make: unexpected target $1" >&2
exit 1
""")
    stub.chmod(0o755)
    out.write_text("")
    return str(bindir)


def test_the_shipped_implement_step_prints_no_value_in_any_spelling():
    """The end-to-end proof for issue #351: run the workflow's OWN implement step against a stub
    `make` whose agent stream carries the value raw, in a Bearer header and as a token shape, and
    require that NONE of it reaches the step's console output — while the rc contract and the
    redacted artifact still work."""
    snippet = _impl_step_snippet()
    check("step: the shipped implement step captures the agent stream",
          "make implement-issue > implement.log" in snippet, snippet[:200])
    check("step: and prints only the redactor's output",
          "make scrub-log FILE=implement.log" in snippet, snippet[:200])
    td = Path(tempfile.mkdtemp())
    out = td / "github_output"
    bindir = _stub_make(td / "bin", out, rc=0)
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", GITHUB_OUTPUT=str(out),
               NOUS_API_KEY=FAKE_VALUE)
    r = subprocess.run(["bash", "-e", "-c", snippet], env=env, cwd=str(td),
                       capture_output=True, text=True)
    console = r.stdout + r.stderr
    check("step: exits 0 on a normal run", r.returncode == 0, r.stderr[-300:])
    for label, needle in (("raw", FAKE_VALUE), ("Bearer header", FAKE_VALUE),
                          ("token shape", FAKE_TOKEN),
                          ("url-encoded", urllib.parse.quote(FAKE_VALUE, safe="")),
                          ("base64", base64.b64encode(FAKE_VALUE.encode()).decode())):
        check(f"step: the {label} spelling never reaches the step's console output",
              needle not in console, console[:300])
    check("step: the agent's harmless lines still show (the log is useful)",
          "agent: reading the post" in console, console[:300])
    check("step: the redacted artifact exists and is redacted",
          (td / "implement.scrubbed.log").is_file()
          and FAKE_VALUE not in (td / "implement.scrubbed.log").read_text(), "")
    check("step: the rc contract is intact (rc + implemented in $GITHUB_OUTPUT)",
          "rc=0" in out.read_text() and "implemented=true" in out.read_text(), out.read_text())


def test_the_shipped_implement_step_still_reports_a_failed_run():
    """A run that produced no implementation must stay RED: rc != 0 → `implemented=false`, which
    the job's loud-failure step turns into a failing run."""
    snippet = _impl_step_snippet()
    td = Path(tempfile.mkdtemp())
    out = td / "github_output"
    bindir = _stub_make(td / "bin", out, rc=2)
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", GITHUB_OUTPUT=str(out),
               NOUS_API_KEY=FAKE_VALUE)
    r = subprocess.run(["bash", "-e", "-c", snippet], env=env, cwd=str(td),
                       capture_output=True, text=True)
    check("step: a failed implementation is reported as implemented=false",
          "rc=2" in out.read_text() and "implemented=false" in out.read_text(), out.read_text())
    check("step: and no value leaks even on the failure path",
          FAKE_VALUE not in (r.stdout + r.stderr), (r.stdout + r.stderr)[:300])


def test_the_seam_prints_only_the_redacted_tail_and_keeps_the_status():
    """The REAL `scrubbed_run` seam, extracted from the Makefile and driven through make against a
    command that prints the value (issue #355).

    This is the seam `make search-<backend>` and `make fix` now use, so the console a workflow step
    or `fix_loop.sh` shows is this: the mask, never the value — and a command that fails must keep
    its status, or a red leg would report green.
    """
    import re
    import shutil

    mk = (ROOT / "Makefile").read_text()
    seam = re.search(r"^define scrubbed_run\n.*?^endef\n", mk, re.M | re.S).group(0)
    td = Path(tempfile.mkdtemp())
    (td / "scripts").mkdir()
    for f in ("scrub_log.py", "check_secret_output.py"):
        shutil.copy(ROOT / "scripts" / f, td / "scripts" / f)
    (td / "Makefile").write_text(
        "HERMES_LOG      := hermes-run.log\nHERMES_LOG_SCRUBBED := hermes-run.scrubbed.log\nHERMES_LOG_TAIL ?= 60\n\n" + seam +
        "\nleaky:\n\t$(call scrubbed_run,echo \"the key is $$NOUS_API_KEY\")\n"
        "failing:\n\t$(call scrubbed_run,exit 3)\n")
    env = dict(os.environ, NOUS_API_KEY=FAKE_VALUE)
    r = subprocess.run(["make", "leaky"], cwd=str(td), env=env, capture_output=True, text=True)
    console = r.stdout + r.stderr
    check("seam: the value never reaches make's console", FAKE_VALUE not in console, console[:200])
    check("seam: the redacted tail IS printed", "the key is ***" in console, console[:300])
    check("seam: a green command exits 0", r.returncode == 0, r.returncode)
    check("seam: the REDACTED copy is written for the artifact", (td / "hermes-run.scrubbed.log").is_file(), "")
    r2 = subprocess.run(["make", "failing"], cwd=str(td), env=env, capture_output=True, text=True)
    check("seam: a failing command keeps its exit status (a red leg stays red)",
          r2.returncode != 0, r2.returncode)


def test_the_target_is_wired_into_the_repo():
    """A script no target names runs nowhere (rule 6d)."""
    mk = (ROOT / "Makefile").read_text()
    check("make: `scrub-log` target exists", "scrub-log:" in mk, "")
    check("make: it is in .PHONY", ".PHONY: scrub-log" in mk, "")
    check("make: it runs the shipped script", "scripts/scrub_log.py" in mk, "")
    wf = (ROOT / ".github" / "workflows" / "issue-bot.yml").read_text()
    check("workflow: the implement step prints only the redactor's output",
          "make scrub-log FILE=implement.log" in wf, "")
    check("workflow: the raw capture is never uploaded (only the redacted one)",
          "implement.scrubbed.log" in wf and "implement.log\n" not in wf.split("upload-artifact")[-1].split("if-no-files-found")[0], "")


def main() -> int:
    print("agent-log redactor (scripts/scrub_log.py, issue #351)")
    test_every_spelling_of_the_value_is_replaced()
    test_the_value_is_never_printed_nor_a_fragment_of_it()
    test_the_printed_output_is_bounded_to_the_tail()
    test_a_missing_log_is_loud()
    test_an_empty_log_is_not_an_error()
    test_a_short_value_is_not_shredded()
    test_the_environment_carries_no_other_spelling()
    test_the_shipped_implement_step_prints_no_value_in_any_spelling()
    test_the_shipped_implement_step_still_reports_a_failed_run()
    test_the_seam_prints_only_the_redacted_tail_and_keeps_the_status()
    test_the_target_is_wired_into_the_repo()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
