#!/usr/bin/env python3
"""Does the SHIPPED agent step stream its agent LIVE — masked before the console, rc intact? (issue #629)

`make implement-issue` used to be captured whole (`> implement.log 2>&1`) and scrubbed only after
the agent ended: the step printed NOTHING for the whole leg, the raw log sat in the runner's
workspace the entire time, and "is the implementer working?" was unanswerable until the run was
over. The shipped shape is the live seam (#591): the TARGET pipes its whole stream through
`scripts/scrub_log.py --stream`, so every line reaches the job console masked AS IT IS PRODUCED,
and the step keeps the agent's own rc.

Every assertion drives the workflow's OWN `run:` text (read from the file, never a copy) and the
REAL Makefile recipe, against a stub `docker`/`make` on PATH standing in for the container
(rule 6m: an external system may be stubbed; the shipped shell around it is not).

secret-output: test value — the marker the guard looks for: the credential-shaped string below is
a deliberate, non-live test value (`sk-` + the alphabet), which is exactly what the marker is for.

NO-SKIP POLICY: a missing prerequisite is a LOUD FAILURE, never a skip.

Wired into `make test` (rule 6d). Runs as a plain script — the runner is scripts/run_tests.sh, the
test image carries no test runner at all (issue #176).
"""
from __future__ import annotations

import base64
import os
import select
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts"))
from wiring import wired  # noqa: E402  (issues #176/#192)
import check_secret_output as cso  # noqa: E402  (the guard's OWN list, not a copy)

SCRUB = ROOT / "scripts" / "scrub_log.py"

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


FAKE_VALUE = "NEVER-PRINT-THIS-0123456789"
FAKE_TOKEN = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"

#: (workflow file, step name in that file, public target the step runs)
SHIPPED_AGENT_STEPS = (
    ("issue-bot.yml", "Implement the issue", "implement-issue"),
    ("issue-review-bot.yml", "Refine the issue (Hermes, through make)", "review-issue"),
    ("issue-review-bot.yml", "Review as a reply (Hermes, through make)", "review-issue-window"),
)


def _step_snippet(workflow: str, step_name: str) -> str:
    """The step's `run:` text, read from the workflow file itself (a test asserting a copy would
    keep passing after the workflow regressed). Parsed by hand: no YAML, runs on the host."""
    lines = (ROOT / ".github" / "workflows" / workflow).read_text().splitlines()
    start = next(i for i, ln in enumerate(lines) if f"- name: {step_name}" in ln)
    run_at = next(i for i in range(start, len(lines)) if lines[i].strip().startswith("run:"))
    indent = len(lines[run_at]) - len(lines[run_at].lstrip())
    body: list[str] = []
    for line in lines[run_at + 1:]:
        if line.strip() and (len(line) - len(line.lstrip())) <= indent:
            break
        body.append(line)
    dedent = indent + 2
    return "\n".join(ln[dedent:] if ln.strip() else "" for ln in body)


def _stub_dir(td: Path, agent_body: str, rc: int, targets: tuple[str, ...]) -> Path:
    """A `make` on PATH standing in for the container target (rule 6m): it streams the agent
    THROUGH THE SHIPPED SEAM SHAPE — the real `scrub_log.py --stream` writing the same raw +
    scrubbed captures the shipped target writes — then returns the agent's rc (pipefail)."""
    bindir = td / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    (td / "scripts").mkdir(exist_ok=True)
    for f in ("scrub_log.py", "check_secret_output.py"):
        shutil.copy(ROOT / "scripts" / f, td / "scripts" / f)
    stub = bindir / "make"
    conds = " || ".join(f'[ "$1" = "{t}" ]' for t in targets)
    stub.write_text(f"""#!/bin/sh
if {conds}; then
  bash -o pipefail -c '{{ {agent_body}; }} 2>&1 | python3 {SCRUB} --stream --raw agent-run.log --out agent-run.scrubbed.log'
  exit $?
fi
exit 0
""")
    stub.chmod(0o755)
    return bindir


def _run_snippet(snippet: str, bindir: Path, td: Path):
    """Run the SHIPPED step text as bash, with the stub `make` on PATH and the fake value in the
    environment. Returns (console, github_output_text, process, first_line_seen_while_running)."""
    out = td / "github_output"
    env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}", GITHUB_OUTPUT=str(out),
               NOUS_API_KEY=FAKE_VALUE)
    p = subprocess.Popen(["bash", "-c", snippet], env=env, cwd=str(td),
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    console: list[str] = []
    seen_while_running = False
    while True:
        ready, _, _ = select.select([p.stdout], [], [], 15)
        if not ready:
            break
        line = p.stdout.readline()
        if not line:
            break
        console.append(line)
        if not seen_while_running and "agent-line-one" in line and p.poll() is None:
            seen_while_running = True
    p.wait(timeout=30)
    return "".join(console), out.read_text() if out.exists() else "", p, seen_while_running


def test_the_shipped_steps_stream_their_targets_uncaptured():
    for workflow, step_name, target in SHIPPED_AGENT_STEPS:
        snip = _step_snippet(workflow, step_name)
        check(f"{workflow} '{step_name}': runs `make {target}` UNCAPTURED",
              f"make {target}\n" in snip and f"make {target} >" not in snip, snip[:200])
        check(f"{workflow} '{step_name}': no post-mortem capture file",
              "> implement.log" not in snip and "> review.log" not in snip, snip[:200])
        check(f"{workflow} '{step_name}': no after-the-fact scrub (the target owns it live)",
              "make scrub-log" not in snip, snip[:200])
        check(f"{workflow} '{step_name}': the agent's own rc is captured",
              "rc=$?" in snip, snip[:200])


def test_the_shipped_targets_own_the_live_seam():
    mk = (ROOT / "Makefile").read_text()
    for target in ("implement-issue", "review-issue", "review-issue-window"):
        check(f"make: `{target}` pipes its stream through the live seam",
              f'$(call scrubbed_run,$(DOCKER_RUN) sh -c "make _setup && make _{target}")' in mk,
              "")
        check(f"guard: `{target}` is in the guard's own scrub list (rule 6d, one list)",
              target in cso.AGENT_TARGETS_TO_SCRUB, str(cso.AGENT_TARGETS_TO_SCRUB))
        check(f"guard: `{target}`'s RECIPE really scrubs (agent-target-does-not-scrub stays armed)",
              cso.public_target_scrubs(mk, target), "")


def test_a_line_reaches_the_console_while_the_agent_is_still_running():
    """The Done-when for #629: with the shipped step + shipped seam shape, line 1 is readable
    BEFORE the agent process exits — the post-mortem shape printed nothing until the end."""
    agent = ('echo "agent-line-one"; sleep 2; echo "agent-line-two"; '
             f'echo "agent: header Bearer $NOUS_API_KEY shape {FAKE_TOKEN}"; exit 7')
    for workflow, step_name, target in SHIPPED_AGENT_STEPS[:1]:
        td = Path(tempfile.mkdtemp())
        bindir = _stub_dir(td, agent, rc=7, targets=(target,))
        console, gh_out, p, seen_while_running = _run_snippet(
            _step_snippet(workflow, step_name), bindir, td)
        check(f"{workflow}: the FIRST agent line reached the console before the agent exited",
              seen_while_running, console[:300])
        check(f"{workflow}: the LATER lines still arrive (no truncation at exit)",
              "agent-line-two" in console, console[:300])
        check(f"{workflow}: rc=7 is reported through the pipe (implemented=false)",
              "rc=7" in gh_out and "implemented=false" in gh_out, gh_out[:200])
        check(f"{workflow}: the step itself stays exit 0 (the job's loud step owns the verdict)",
              p.returncode == 0, str(p.returncode))


def test_the_live_console_carries_no_value_in_any_spelling():
    agent = ('echo "agent-line-one"; echo "agent: the key is $NOUS_API_KEY"; '
             f'echo "agent: bearer $NOUS_API_KEY and shape {FAKE_TOKEN}"; exit 7')
    td = Path(tempfile.mkdtemp())
    bindir = _stub_dir(td, agent, rc=7, targets=("implement-issue",))
    console, gh_out, _p, _seen = _run_snippet(
        _step_snippet("issue-bot.yml", "Implement the issue"), bindir, td)
    for label, needle in (("raw", FAKE_VALUE), ("token shape", FAKE_TOKEN),
                          ("url-encoded", urllib.parse.quote(FAKE_VALUE, safe="")),
                          ("base64", base64.b64encode(FAKE_VALUE.encode()).decode())):
        check(f"stream: the {label} spelling never reached the console while streaming",
              needle not in console, console[:300])
    check("stream: the masked line is still readable (*** not a dropped line)",
          "***" in console and "agent: bearer" in console, console[:300])
    raw = td / "agent-run.log"
    scrubbed = td / "agent-run.scrubbed.log"
    check("stream: the raw capture the seam wrote keeps the value (the log stays whole)",
          raw.is_file() and FAKE_VALUE in raw.read_text(), "")
    check("stream: the redacted artifact the seam wrote does NOT",
          scrubbed.is_file() and FAKE_VALUE not in scrubbed.read_text(), "")


def test_the_reviewer_steps_keep_the_detach_contract():
    """rc=3 (Hermes detaching for input) must still exit the step red with the named error — the
    refactor must not silently swallow it (`exit $rc`)."""
    agent = 'echo "agent-line-one"; exit 3'
    td = Path(tempfile.mkdtemp())
    bindir = _stub_dir(td, agent, rc=3, targets=("review-issue", "review-issue-window"))
    snip = _step_snippet("issue-review-bot.yml", "Refine the issue (Hermes, through make)")
    console, _gh, p, _seen = _run_snippet(snip, bindir, td)
    check("review step: rc=3 propagates out of the step (exit $rc)",
          p.returncode == 3, str(p.returncode))
    check("review step: the detach is named in the log (::error:: with #549)",
          "::error::" in console and "#549" in console, console[:300])


def test_the_suite_is_wired_into_make_test():
    check("wiring: this suite is in `make test`", wired(__file__), "")


def main() -> int:
    print("live agent stream through the shipped step (issue #629)")
    test_the_shipped_steps_stream_their_targets_uncaptured()
    test_the_shipped_targets_own_the_live_seam()
    test_a_line_reaches_the_console_while_the_agent_is_still_running()
    test_the_live_console_carries_no_value_in_any_spelling()
    test_the_reviewer_steps_keep_the_detach_contract()
    test_the_suite_is_wired_into_make_test()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
