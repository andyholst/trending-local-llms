#!/usr/bin/env python3
"""test_test_container_identity.py — the suite must say WHOSE uid measured it, and a guard that could not run must say WHAT did not run (issue #1147).

Two measured states this change exists for:

1. `make test` answered "136 modules green" and never said whose uid ran them. `TEST_RUN`
   (Makefile) starts every test container through `scripts/docker_test_run.sh` and passes NO
   `--user`, so the container runs as the image's default user — verified live: `docker exec
   tll-test-3965-16821 id -u` = 0 — while the host `scripts/run_tests.sh` assumes the invoking uid.

2. `tests/test_agent_skills.py`'s permission half printed `SKIP teardown: … permission plant
   bypassed (uid 0 — DAC_OVERRIDE …)` and returned, so its module exited 0 — measured in CI:
   qa-validate run 44551541279, 135 modules green, where the planted mode-0o000 tree was removed
   cleanly by uid 0 and the guard then died on its own cleanup `chmod`. A green run carried a
   half-covered guard and the verdict said nothing about it.

3. (issue #1173) the builders BUILD and RETURN the gap line; `coverage_gap.announce` is the seam's
   ONLY print of it. Measured in the test container: the real container has `hermes` on PATH, so
   `tests/test_agent_skills.py` declared nothing legitimately, yet `make test` answered
   `coverage-gap 2 declared` — two PHANTOM gaps printed by the builders themselves at demo call
   sites. A builder that prints makes every call site — including a guard test's own demonstration
   — leak a gap into the runner's count, so the phantom class is removed AT THE SEAM: a call that
   never announced declares nothing, and a real half must announce to be counted.

The contract now: `scripts/coverage_gap.py` defines the identity line, the declared-gap prefix and
the bypass phrase ONCE (rule 6d); the runner reads them from the seam, prints the identity, scans
EVERY module's output (including a passing one, whose output used to be deleted unread), refuses a
bypass that never travelled inside the declared seam, and names declared gaps in the verdict; and
`make test` refuses a capture that never carried the identity line.

Every check below runs the REAL product (the bash runner, the wrapper script, the real `make`
recipe) with only external stand-ins (a stub `docker` on PATH, a planted fixture test dir) — rule 6m.

Run:  python3 tests/test_test_container_identity.py   or   make test
"""

from __future__ import annotations

import ast
import contextlib
import json
import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "run_tests.sh"
WRAPPER = ROOT / "scripts" / "docker_test_run.sh"
SEAM = ROOT / "scripts" / "coverage_gap.py"
MAKEFILE = ROOT / "Makefile"
sys.path.insert(0, str(ROOT / "scripts"))
import coverage_gap  # noqa: E402  (the ONE seam; this test imports it, never re-spells it)

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"ok   {name}")
    else:
        _FAIL += 1
        print(f"FAIL {name}")
        if detail:
            print(detail)


def _seam(flag: str) -> str:
    """Ask the seam for one of its strings (so this test never keeps its own copy)."""
    r = subprocess.run([sys.executable, str(SEAM), flag], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise AssertionError(f"seam {flag} refused: {r.stderr}")
    return r.stdout.strip()


def _run_runner(dirp: Path, extra_env: dict | None = None) -> tuple[int, str]:
    env = dict(os.environ)
    env.update(extra_env or {})
    r = subprocess.run(["bash", str(RUNNER), str(dirp)], capture_output=True, text=True,
                       timeout=600, env=env)
    return r.returncode, r.stdout + r.stderr


def _green_module() -> str:
    return "print('ok planted')\nraise SystemExit(0)\n"


# ---------------------------------------------------------------- the identity line

def test_the_runner_names_the_identity_it_measured() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "test_a_ok.py").write_text(_green_module())
        invoker = f"{os.getuid()}:{os.getgid()}"
        rc, out = _run_runner(d, {"TLL_INVOKING_UID": invoker})
    check("identity: the runner prints the seam's identity line before any verdict",
          coverage_gap.IDENTITY_PREFIX in out, out[:400])
    check("identity: the line names the uid the suite actually measured",
          f"container uid={os.getuid()}" in out, out[:400])
    check("identity: the line names the uid that invoked it, and says whether they are the same",
          f"invoking uid={invoker}" in out and "run-as=invoking uid" in out, out[:400])
    check("identity: exits 0 (the identity line is a report, not a failure)", rc == 0, out[:400])


def test_the_identity_line_distinguishes_a_container_uid_from_the_invoker() -> None:
    """A container run (uid 0 vs invoker 501) must be VISIBLE on the line, not inferred."""
    # A pair the process CANNOT already be (gid+1 differs from the live gid in both the
    # container uid-0 case and the host uid case), so the seam must report the mismatch.
    mismatched = f"{os.getuid()}:{os.getgid() + 1}"
    line = subprocess.run(
        [sys.executable, str(SEAM), "--identity-line"], capture_output=True, text=True, timeout=60,
        env={**os.environ, "TLL_INVOKING_UID": mismatched},
    ).stdout.strip()
    check("identity: when the runner is NOT the invoker the line states the mismatch",
          coverage_gap.IDENTITY_PREFIX in line
          and f"invoking uid={mismatched}" in line
          and "run-as=image default user, NOT the invoking uid" in line, line)
    stripped = {k: v for k, v in os.environ.items() if k != "TLL_INVOKING_UID"}
    real = subprocess.run([sys.executable, str(SEAM), "--identity-line"],
                          capture_output=True, text=True, timeout=60, env=stripped).stdout.strip()
    check("identity: with no invoker forwarded the line says so instead of guessing",
          "invoking uid=unset" in real and "run-as=unknown (no invoking uid forwarded)" in real,
          real)


# ---------------------------------------------------------------- declared coverage gaps

def test_a_declared_gap_in_a_GREEN_module_reaches_the_verdict() -> None:
    """A passing module that declares a gap must be COUNTED, not deleted unread with its output."""
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "test_a_ok.py").write_text(_green_module())
        planted = (
            "import sys\n"
            f"sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
            "import coverage_gap\n"
            "coverage_gap.announce(coverage_gap.declare_bypass_gap('planted permission half', 'the filesystem did not honour the plant'))\n"
            "print('ok planted')\n"
        )
        (d / "test_b_declares.py").write_text(planted)
        rc, out = _run_runner(d)
    check("declared gap: the module stays green (a gap is honest, not a failure)", rc == 0, out[:500])
    check("declared gap: a PASSING module's gap was read before its output was deleted",
          "[harness] coverage-gap 1 declared" in out, out[:600])
    check("declared gap: the verdict names which guard did not run, beside the identity that ran it",
          "planted permission half" in out and "container uid=" in out, out[:600])


def test_a_bypass_that_never_declared_its_gap_turns_the_runner_red() -> None:
    """The old shape (a bare SKIP inside a module that exits 0) is now a refusal."""
    phrase = _seam("--phrase")  # from the seam, never spelled here
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "test_a_ok.py").write_text(_green_module())
        (d / "test_b_bare_skip.py").write_text(
            f"print('  SKIP guard: {phrase} (uid 0)')\nraise SystemExit(0)\n"
        )
        rc, out = _run_runner(d)
    check("undeclared bypass: a green rc over an undeclared bypass now goes RED", rc == 1, out[:500])
    check("undeclared bypass: the refusal names the module and the issue",
          "test_b_bare_skip.py" in out and "issue #1147" in out, out[:600])
    check("undeclared bypass: the refusal says what the fix is (the declared seam)",
          "never as a bare SKIP" in out and "scripts/coverage_gap.py" in out, out[:600])
    check("undeclared bypass: the verdict line still exists (the runner always states one)",
          "undeclared-bypass report(s) FAILED" in out, out[:600])


def test_a_declared_and_an_undeclared_line_in_one_module_are_separated() -> None:
    """The seam prefix decides which half is honest; the wording alone cannot launder a SKIP."""
    phrase = _seam("--phrase")
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        planted = (
            "import sys\n"
            f"sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
            "import coverage_gap\n"
            "coverage_gap.announce(coverage_gap.declare_gap('planted declared half', 'reported inside the seam'))\n"
            f"print('  SKIP another guard: {phrase}')\n"
            "print('ok planted')\n"
        )
        (d / "test_a_both.py").write_text(planted)
        rc, out = _run_runner(d)
    check("mixed output: the undeclared half still refuses the run", rc == 1, out[:500])
    check("mixed output: the refusal points at the bare line, not at the declared one",
          "planted declared half" not in out.split("FAIL")[-1], out[-600:])


# ---------------------------------------------------------------- one definition, no copies

def test_the_runner_reads_the_phrases_from_the_seam_and_never_spells_them() -> None:
    runner_src = RUNNER.read_text(encoding="utf-8")
    wrapper_src = WRAPPER.read_text(encoding="utf-8")
    seam_src = SEAM.read_text(encoding="utf-8")
    check("seam: the runner calls the seam for all three strings",
          "--gap-prefix" in runner_src and "--phrase" in runner_src and "--identity-line" in runner_src,
          runner_src[:400])
    for src_name, src in (("scripts/run_tests.sh", runner_src), ("scripts/docker_test_run.sh", wrapper_src)):
        check(f"seam: {src_name} does not re-spell the bypass phrase",
              coverage_gap.BYPASS_PHRASE not in src, src[:300])
        check(f"seam: {src_name} does not re-spell the gap prefix",
              coverage_gap.GAP_PREFIX not in src, src[:300])
    check("seam: the seam is the only definition of the three strings",
          seam_src.count(f'GAP_PREFIX = "{coverage_gap.GAP_PREFIX}"') == 1
          and seam_src.count(f'BYPASS_PHRASE = "{coverage_gap.BYPASS_PHRASE}"') == 1
          and seam_src.count(f'IDENTITY_PREFIX = "{coverage_gap.IDENTITY_PREFIX}"') == 1,
          seam_src[:300])
    check("seam: a runner whose seam is unreadable fails LOUD (exit 2), never vacuously clean",
          "exit 2" in runner_src and "cannot read" in runner_src, runner_src[:600])


def test_the_runner_refuses_loudly_when_the_seam_script_is_gone() -> None:
    """A missing seam is a harness failure, not a suite that silently skips the new gate."""
    with tempfile.TemporaryDirectory() as td:
        tree = Path(td)
        (tree / "scripts").mkdir()
        shutil.copy(RUNNER, tree / "scripts" / "run_tests.sh")  # no coverage_gap.py beside it
        (tree / "tests").mkdir()
        (tree / "tests" / "test_a_ok.py").write_text(_green_module())
        r = subprocess.run(["bash", str(tree / "scripts" / "run_tests.sh")],
                           capture_output=True, text=True, timeout=120)
    check("seam-missing: exit 2 naming the seam (never a silent green)",
          r.returncode == 2 and "coverage_gap.py" in (r.stdout + r.stderr), f"rc={r.returncode}")


# ---------------------------------------------------------------- the container seam

def _stub_docker(bin_dir: Path, argv_file: Path) -> Path:
    script = bin_dir / "docker"
    script.write_text(
        "#!/bin/sh\n"
        f'printf "%s\\n" "$@" >> {argv_file}\n'
        'if [ "$1" = "run" ]; then printf "%s\\n" "[test] 1 module(s) passed"; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_the_container_wrapper_names_and_forwards_the_invoking_identity() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        argv_file = tmp / "docker-argv.txt"
        _stub_docker(bin_dir, argv_file)
        env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"}
        r = subprocess.run(["bash", str(WRAPPER), "--rm", "image:tag", "make", "test"],
                           capture_output=True, text=True, timeout=180, env=env, cwd=str(tmp))
        argv = argv_file.read_text(encoding="utf-8").splitlines() if argv_file.exists() else []
    check("wrapper: the run names the identity it starts under",
          "[harness] docker_test_run identity:" in (r.stdout + r.stderr), (r.stdout + r.stderr)[:300])
    forwarded = [line for line in argv if line.startswith("TLL_INVOKING_UID=")]
    check("wrapper: the invoking uid is forwarded INTO the container by NAME",
          "-e" in argv and forwarded == [f"TLL_INVOKING_UID={os.getuid()}:{os.getgid()}"],
          "\n".join(argv[:20]))
    run_lines = [line for line in WRAPPER.read_text(encoding="utf-8").splitlines()
                 if line.lstrip().startswith("docker run")]
    check("wrapper: the wrapper never invents --user (the container keeps the image default uid)",
          "--user" not in argv and bool(run_lines) and not any("--user" in line for line in run_lines),
          "\n".join(argv[:20]) + " || " + " ".join(run_lines))
    check("wrapper: the argv it forwards is the caller's argv unchanged",
          "image:tag" in argv and "make" in argv and "test" in argv, "\n".join(argv[:20]))


# ---------------------------------------------------------------- the make test seam

def _test_recipe(makefile_src: str) -> str:
    lines = makefile_src.splitlines()
    out: list[str] = []
    for i, line in enumerate(lines):
        if line == "test:":
            for follow in lines[i + 1:]:
                if follow.startswith("\t"):
                    out.append(follow)
                else:
                    break
            break
    if not out:
        raise AssertionError("no `test:` recipe found in the Makefile")
    return "\n".join(out)


def _fixture_make(tmp: Path, stub: Path) -> Path:
    mk = tmp / "Makefile"
    mk.write_text(
        "SHELL := /bin/bash\n"
        f"TEST_RUN := bash {stub}\n"
        ".PHONY: test\ntest:\n" + _test_recipe(MAKEFILE.read_text(encoding="utf-8")) + "\n",
        encoding="utf-8",
    )
    return mk


def _stub_run(tmp: Path, lines, rc: int) -> Path:
    script = tmp / "stub_run.sh"
    body = "#!/bin/sh\n"
    for line in lines:
        body += f"printf '%s\\n' \"{line}\"\n"
    body += f"exit {rc}\n"
    script.write_text(body, encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_make_test_refuses_a_capture_that_never_named_its_identity() -> None:
    """The measured host-side half: verdict lines arrived, the identity line never did."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        stub = _stub_run(tmp_p, ["[test] ok test_a.py", "[test] 1 module(s) passed"], 0)
        r = subprocess.run(["make", "-f", str(_fixture_make(tmp_p, stub)), "test"],
                           capture_output=True, text=True, timeout=180)
    check("make test: rc 0 + verdict lines + NO identity line is a RED gate",
          r.returncode != 0, f"rc={r.returncode} stderr={r.stderr[:200]}")
    check("make test: the refusal names the missing identity and the issue",
          "suite identity line" in r.stderr and "issue #1147" in r.stderr, r.stderr[:400])


def test_make_test_reports_declared_coverage_gaps_in_its_own_verdict() -> None:
    gap_line = (f"{coverage_gap.GAP_PREFIX} planted permission half: the container is uid 0 "
                "and the plant was walked through")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_p = Path(tmp)
        stub = _stub_run(tmp_p, [
            "[test] ok test_a.py",
            "[harness] suite identity: container uid=0 gid=0 invoking uid=501:20 "
            "run-as=image default user, NOT the invoking uid",
            f"[harness] coverage-gap 1 declared; {coverage_gap.IDENTITY_PREFIX} container uid=0",
            gap_line,
            "[test] 1 module(s) passed",
        ], 0)
        r = subprocess.run(["make", "-f", str(_fixture_make(tmp_p, stub)), "test"],
                           capture_output=True, text=True, timeout=180)
    check("make test: a declared gap stays GREEN", r.returncode == 0, f"rc={r.returncode} {r.stderr[:200]}")
    check("make test: the harness verdict COUNTS the declared gaps it captured",
          "1 declared coverage-gap report(s)" in r.stderr, r.stderr[:400])
    check("make test: the suite's own stream (identity + gap) stays visible on stdout",
          coverage_gap.IDENTITY_PREFIX in r.stdout and coverage_gap.GAP_PREFIX in r.stdout,
          r.stdout[:400])


# ---------------------------------------------------------------- the guard that reports its own bypass

def test_the_permission_half_guard_reports_through_the_seam_not_as_a_bare_skip() -> None:
    src = (ROOT / "tests" / "test_agent_skills.py").read_text(encoding="utf-8")
    check("guard: the teardown permission half declares its gap through the seam",
          "coverage_gap.announce(coverage_gap.declare_bypass_gap(" in src, src[:300])
    check("guard: the bare SKIP print of the bypass is gone from the tree",
          'print(f"  SKIP teardown' not in src and coverage_gap.BYPASS_PHRASE not in src, src[:400])
    check("guard: the always-checked half is still named as the contract it keeps",
          "still locks its contract" in src, src[:400])


def test_an_external_binary_gap_keeps_a_host_run_green_and_is_counted() -> None:
    """Issue #1154: a guard whose half needs a CLI this identity lacks declares the gap.

    The probe binary is one GUARANTEED absent (`tll-absent-cli-1171` ships nowhere): the test
    container HAS a real `hermes`, so probing `hermes` here made this guard green on the host
    and red in the container — an environment-dependent assertion, the very trap the seam
    exists to remove (measured on issue #1171's branch, both checks failed in the container
    while passing on the host). The real-`hermes` half is still driven below with `PATH` cut.
    """
    probe = "tll-absent-cli-1171"
    guard = "absent-CLI half (issue #1154)"
    # The builder is QUIET (issue #1173): a guard test's own demonstration call cannot leak a
    # phantom gap into the verdict any more — the old shape printed this line into the module's
    # stream and the runner counted it (`coverage-gap 2 declared` in a container that declared
    # nothing). Only the real halves announce.
    line = coverage_gap.external_binary_gap(
        guard, probe, "a host `make test` has no agent CLI")
    check("binary gap: the line travels inside the declared-gap seam",
          line.startswith(coverage_gap.GAP_PREFIX + " ") and coverage_gap.BYPASS_PHRASE in line, line)
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "test_a_ok.py").write_text(_green_module())
        planted = (
            "import sys\n"
            f"sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
            "import coverage_gap\n"
            f"coverage_gap.announce(coverage_gap.external_binary_gap({guard!r}, {probe!r},\n"
            "                                       'a host `make test` has no agent CLI'))\n"
            "print('ok planted')\n"
        )
        (d / "test_b_binary_gap.py").write_text(planted)
        rc, out = _run_runner(d)
    check("binary gap: the module stays green (a declared half is honest, not a failure)",
          rc == 0, out[:500])
    check("binary gap: the runner counts it and names the guard that did not run",
          "[harness] coverage-gap 1 declared" in out and guard in out,
          out[:600])
    src = (ROOT / "tests" / "test_agent_skills.py").read_text(encoding="utf-8")
    check("binary gap: the skills module declares the register half through the seam, announcing it",
          "coverage_gap.external_binary_gap(" in src and "coverage_gap.announce(gap_line)" in src
          and 'shutil.which("hermes")' not in src, src[:400])
    # The REAL module, driven with the CLI's directory stripped from PATH (rule 6m: the guard
    # runs the real code, not a stand-in): it must stay green and declare the half.
    keep = [p for p in os.environ.get("PATH", "").split(os.pathsep)
            if p and not (Path(p) / "hermes").exists()]
    env = {**os.environ, "PATH": os.pathsep.join(keep)}
    proc = subprocess.run([sys.executable, str(ROOT / "tests" / "test_agent_skills.py")],
                          capture_output=True, text=True, timeout=300, env=env)
    check("binary gap: the real module stays green with the CLI absent and declares the half",
          proc.returncode == 0 and coverage_gap.GAP_PREFIX in proc.stdout
          and "hermes-skills register half" in proc.stdout,
          proc.stdout[-400:] + proc.stderr[-200:])


def test_the_seam_declares_several_external_binaries_in_one_line_and_probes_them() -> None:
    """Issue #1171: a module driving N CLIs declares them in ONE line, naming only the missing."""
    src = (ROOT / "scripts" / "coverage_gap.py").read_text(encoding="utf-8")
    check("multi-binary: the seam accepts a sequence, not one name",
          "binary: str | Sequence[str]" in src and "isinstance(binary, str)" in src, src[:300])
    with tempfile.TemporaryDirectory() as td:
        stub = Path(td) / "present-cli"
        stub.write_text("#!/bin/sh\n", encoding="utf-8")
        stub.chmod(0o755)
        env = {**os.environ, "PATH": td + os.pathsep + os.environ.get("PATH", "")}
        # Drive the REAL seam in a subprocess with a stub on PATH (rule 6m: the guard runs the
        # real code, not a stand-in) — `present-cli` exists, `absent-cli` does not. The builders
        # are QUIET (issue #1173): the missing half is visible only through announce().
        prog = (
            "import sys; sys.path.insert(0, %r)\n"
            "import coverage_gap\n"
            "line = coverage_gap.external_binary_gap('two-CLI half', "
            "('present-cli', 'absent-cli'), 'a host run lacks one of them')\n"
            "coverage_gap.announce(line)\n"
            "print('LINE=' + repr(line))\n"
            "empty = coverage_gap.external_binary_gap('all-present half', "
            "('present-cli',), 'never declared')\n"
            "coverage_gap.announce(empty)\n"
            "print('EMPTY=' + repr(empty))\n"
        ) % str(ROOT / "scripts")
        proc = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True,
                              timeout=120, env=env)
        out = proc.stdout + proc.stderr
    check("multi-binary: one line names ONLY the missing CLI",
          "LINE=" in out and "`absent-cli`" in out and "`present-cli`" not in out
          and "two-CLI half" in out, out[-500:])
    check("multi-binary: the line travels inside the declared-gap seam",
          coverage_gap.GAP_PREFIX in out and coverage_gap.BYPASS_PHRASE in out, out[-500:])
    check("multi-binary: a single missing CLI keeps the singular wording",
          "CLI is not on PATH" in out or "CLIs are not on PATH" in out, out[-500:])
    check("multi-binary: every binary present declares NOTHING and returns ''",
          "EMPTY=''" in out
          and sum(1 for l in out.splitlines() if l.startswith(coverage_gap.GAP_PREFIX)) == 1,
          out[-500:])


def test_a_present_but_broken_cli_is_a_real_failure_not_a_declared_gap() -> None:
    """Issue #1172: presence is PRESUMED usability — a broken CLI is a REAL failure, never a gap.

    The two states a guard must not confuse: `hermes` ABSENT (a coverage gap the seam declares,
    the module stays green) and `hermes` PRESENT but failing (a defect in the half that drives it
    — the module goes red with the CLI's own error, which is the honest signal).
    """
    src = (ROOT / "scripts" / "coverage_gap.py").read_text(encoding="utf-8")
    check("#1172: the boundary is named in the seam, not left to a reader",
          "PRESENCE_IS_PRESUMED_USABLE = True" in src and "def external_binary_usable(" in src,
          src[:300])
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        stub = d / "hermes"
        stub.write_text("#!/bin/sh\necho 'HTTP 401: Your API key is invalid' >&2\nexit 1\n",
                        encoding="utf-8")
        stub.chmod(0o755)
        skills = d / "skills"
        skills.mkdir()
        (skills / "demo").mkdir()
        env = {**os.environ, "PATH": str(d) + os.pathsep + os.environ.get("PATH", "")}
        # (a) the REAL seam, in a subprocess with the broken CLI on PATH (rule 6m). The builder
        # is quiet (issue #1173); what matters here is that a PRESENT CLI declares nothing.
        prog = (
            "import sys; sys.path.insert(0, %r)\n"
            "import coverage_gap\n"
            "line = coverage_gap.external_binary_gap('register half', 'hermes', 'why')\n"
            "coverage_gap.announce(line)\n"
            "print('LINE=' + repr(line))\n"
            "print('USABLE=' + repr(coverage_gap.external_binary_usable('hermes')))\n"
        ) % str(ROOT / "scripts")
        p = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True,
                           timeout=120, env=env)
        out = p.stdout + p.stderr
        # (b) the REAL register script driven by that same broken CLI.
        home = d / "home"
        home.mkdir()
        reg = subprocess.run([sys.executable, str(ROOT / "scripts" / "hermes_skills_register.py"),
                              "--home", str(home), "--dir", str(skills)],
                             capture_output=True, text=True, timeout=120, env=env)
    check("#1172: the seam declares NOTHING for a present-but-broken CLI",
          "LINE=''" in out and coverage_gap.GAP_PREFIX not in out, out[-400:])
    check("#1172: presence is reported usable — the seam probes presence, not health",
          "USABLE=True" in out, out[-400:])
    check("#1172: the real register half goes RED on the broken CLI (a real failure)",
          reg.returncode == 2 and "failed" in (reg.stderr + reg.stdout).lower(),
          f"rc={reg.returncode} {reg.stderr[-300:]}")
    check("#1172: and it prints NO declared-gap line (a gap would launder the failure)",
          coverage_gap.GAP_PREFIX not in (reg.stdout + reg.stderr), reg.stdout[-200:])


def test_the_gap_builders_return_quietly_and_only_announce_prints() -> None:
    """The builders BUILD and RETURN; they print NOTHING (issue #1173). `announce` is the seam's
    only print of a gap line — the phantom-gap class is removed at the seam, not at a call site
    (issue #1178's redirect_stdout left the builder printing, so the next demo leaked again).

    Drives the REAL seam in a subprocess whose PATH lacks `tll-absent-cli-1173`: the builders are
    called WITHOUT any redirect, their returns are named in repr, and the subprocess's own stream
    must carry no GAP_PREFIX line until announce runs. RED on the old seam, whose builders printed.
    """
    prog = (
        "import sys, json; sys.path.insert(0, %r)\n"
        "import coverage_gap\n"
        "a = coverage_gap.declare_gap('built not announced', 'a builder must not print')\n"
        "b = coverage_gap.declare_bypass_gap('bypass not announced', 'quiet by contract')\n"
        "c = coverage_gap.external_binary_gap('binary half', 'tll-absent-cli-1173', 'absent')\n"
        "print('RET ' + json.dumps([a, b, c]))\n"
        "coverage_gap.announce(c)\n"
    ) % str(ROOT / "scripts")
    p = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, timeout=120)
    out = p.stdout + p.stderr
    rets = [l for l in out.splitlines() if l.startswith("RET ")]
    built = json.loads(rets[0][4:]) if len(rets) == 1 else None
    check("#1173: the three builders RETURN three lines carrying the seam's prefix",
          built is not None
          and len(built) == 3
          and all(isinstance(x, str) and coverage_gap.GAP_PREFIX in x for x in built),
          out[-500:])
    pre = out.split("RET ", 1)[0]
    check("#1173: the builders printed NOTHING into the stream (the phantom class at the seam)",
          not any(l.startswith(coverage_gap.GAP_PREFIX) for l in pre.splitlines()), pre[:400])
    post = out.split("RET ", 1)[1]
    check("#1173: announce is what puts the gap on the stream — exactly once",
          sum(1 for l in post.splitlines() if l.startswith(coverage_gap.GAP_PREFIX)) == 1
          and "binary half" in post and coverage_gap.BYPASS_PHRASE in post, post[:400])


def test_a_call_that_never_announced_declares_nothing_to_the_runner() -> None:
    """The phantom class ITSELF against the REAL runner (issue #1173: `coverage-gap 2 declared` in
    a container whose real halves declared nothing). A planted module calls the builders for an
    absent CLI — exactly the demo shape the guards used — keeps the returns, and never announces:
    the module stays green and the runner names NO gap. A sibling module announces once and is
    counted exactly once. RED on the old seam: the un-announced calls printed, and the runner
    counted their prints.
    """
    quiet = (
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
        "import coverage_gap\n"
        "a = coverage_gap.declare_gap('demo half one', 'a demonstration')\n"
        "b = coverage_gap.declare_gap('demo half two', 'another demonstration')\n"
        "c = coverage_gap.external_binary_gap('demo absent CLI', 'tll-absent-cli-1173q',\n"
        "                                     'a host `make test` has no such CLI')\n"
        "print('KEPT=' + repr(bool(a and b and c)))\n"
        "print('ok quiet')\n"
    )
    announced = (
        "import sys\n"
        f"sys.path.insert(0, {str(ROOT / 'scripts')!r})\n"
        "import coverage_gap\n"
        "coverage_gap.announce(coverage_gap.external_binary_gap(\n"
        "    'announced half', 'tll-absent-cli-1173a', 'the half really did not run'))\n"
        "print('ok announced')\n"
    )
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "test_a_quiet_calls.py").write_text(quiet)
        rc_q, out_q = _run_runner(d)
    check("#1173: a module whose calls never announced stays green",
          rc_q == 0, out_q[:500])
    check("#1173: and the runner names NO declared gap for it — the phantom is impossible",
          coverage_gap.GAP_PREFIX not in out_q and "[harness] coverage-gap" not in out_q,
          out_q[:600])
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "test_a_announced.py").write_text(announced)
        rc_a, out_a = _run_runner(d)
    check("#1173: an announced gap is still counted — exactly once, naming its guard",
          rc_a == 0 and "[harness] coverage-gap 1 declared" in out_a and "announced half" in out_a,
          out_a[:600])


def test_the_seam_prints_gap_lines_only_through_announce_and_the_real_halves_announce() -> None:
    """Source half (rule 6d): the seam's ONLY build-time print of a string carrying GAP_PREFIX is
    inside `announce`, the GAP_PREFIX constant is assigned exactly once, and every real declaration
    site — both halves in tests/test_agent_skills.py — reads as `announce(declare_…(...))`. RED on
    the old seam: `declare_gap` printed the line itself, and the real halves called the printing
    builder directly.
    """
    tree = ast.parse((ROOT / "scripts" / "coverage_gap.py").read_text(encoding="utf-8"))
    gap_names = {"declare_gap", "declare_bypass_gap", "external_binary_gap"}
    prefix = str(next(c.value.value for c in ast.walk(tree)
                      if isinstance(c, ast.Assign) and isinstance(c.targets[0], ast.Name)
                      and c.targets[0].id == "GAP_PREFIX" and isinstance(c.value, ast.Constant)))

    def gap_emitter(func: ast.AST) -> bool:
        """True if a print inside `func` can emit a gap line: it prints a constant carrying the
        prefix, or prints a name the function built from a gap expression — an f-string starting
        with GAP_PREFIX or a call of one of the builders (the OLD declare_gap shape) — or prints a
        PARAMETER (the new announce(line) shape: the gap line arrives through the signature, and
        this is the seam's one permitted print path)."""
        argnode = getattr(func, "args", None)
        params = {a.arg for a in (getattr(argnode, "args", []) or [])} | {
            a.arg for a in (getattr(argnode, "posonlyargs", []) or [])}
        gap_bound = set()
        for node in ast.walk(func):
            if (isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id in gap_names):
                gap_bound.add(node.targets[0].id)
            if (isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.JoinedStr) and node.value.values
                    and isinstance(node.value.values[0], ast.FormattedValue)
                    and isinstance(node.value.values[0].value, ast.Name)
                    and node.value.values[0].value.id == "GAP_PREFIX"):
                gap_bound.add(node.targets[0].id)
        for call in ast.walk(func):
            if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                    and call.func.id == "print"):
                continue
            for arg in call.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                        and prefix in arg.value:
                    return True
                if isinstance(arg, ast.Name) and (arg.id in gap_bound or arg.id in params):
                    return True
        return False

    emitters = [n.name for n in tree.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and gap_emitter(n)]
    check("#1173: the ONLY seam function that can print a gap line is announce()",
          emitters == ["announce"], str(emitters))

    src = (ROOT / "tests" / "test_agent_skills.py").read_text(encoding="utf-8")
    skills_tree = ast.parse(src)
    skills_announced = []   # builder names announced directly: announce(coverage_gap.declare_…(…))
    announced_lines = set()
    for call in ast.walk(skills_tree):
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr == "announce"
                and call.args and isinstance(call.args[0], ast.Call)
                and isinstance(call.args[0].func, ast.Attribute)
                and call.args[0].func.attr in gap_names):
            skills_announced.append(call.args[0].func.attr)
            announced_lines.add(call.lineno)
            announced_lines.add(call.args[0].lineno)
    # the QUIET-builder contract (issue #1173): a declaration site may hold a builder's return in
    # a name and announce it on a later line — every builder call line must be an announce line
    # (directly, or via announce(<name>) of the name that holds the builder's return).
    name_from_builder: dict[str, set[int]] = {}
    for node in ast.walk(skills_tree):
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr in gap_names
                and node.targets and isinstance(node.targets[0], ast.Name)):
            name_from_builder[node.targets[0].id] = set(
                range(node.value.lineno, getattr(node.value, "end_lineno", node.value.lineno) + 1))
    for call in ast.walk(skills_tree):
        if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr == "announce" and call.args
                and isinstance(call.args[0], ast.Name)
                and call.args[0].id in name_from_builder):
            announced_lines |= name_from_builder[call.args[0].id]
            announced_lines.add(call.lineno)
    bare = []
    for call in ast.walk(skills_tree):
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr in gap_names):
            continue
        lines = set(range(call.lineno, getattr(call, "end_lineno", call.lineno) + 1))
        if not (lines & announced_lines):
            bare.append((call.func.attr, call.lineno))
    check("#1173: the real halves announce through the seam (the CLI half announces only when "
          "the CLI is absent — the strip-PATH run in this suite locks the declared shape)",
          set(skills_announced) <= gap_names and "coverage_gap.announce(gap_line)" in src,
          str(skills_announced))
    check("#1173: no real declaration site calls a builder without announcing it",
          not bare, str(bare))


def main() -> int:
    print("test suite identity + coverage-gap seam (#1147) — real runner, real wrapper, real make recipe")
    test_the_runner_names_the_identity_it_measured()
    test_the_identity_line_distinguishes_a_container_uid_from_the_invoker()
    test_a_declared_gap_in_a_GREEN_module_reaches_the_verdict()
    test_a_bypass_that_never_declared_its_gap_turns_the_runner_red()
    test_a_declared_and_an_undeclared_line_in_one_module_are_separated()
    test_an_external_binary_gap_keeps_a_host_run_green_and_is_counted()
    test_the_seam_declares_several_external_binaries_in_one_line_and_probes_them()
    test_a_present_but_broken_cli_is_a_real_failure_not_a_declared_gap()
    test_the_gap_builders_return_quietly_and_only_announce_prints()
    test_a_call_that_never_announced_declares_nothing_to_the_runner()
    test_the_seam_prints_gap_lines_only_through_announce_and_the_real_halves_announce()
    test_the_runner_reads_the_phrases_from_the_seam_and_never_spells_them()
    test_the_runner_refuses_loudly_when_the_seam_script_is_gone()
    test_the_container_wrapper_names_and_forwards_the_invoking_identity()
    test_make_test_refuses_a_capture_that_never_named_its_identity()
    test_make_test_reports_declared_coverage_gaps_in_its_own_verdict()
    test_the_permission_half_guard_reports_through_the_seam_not_as_a_bare_skip()
    print(f"\n{_PASS} passed, {_FAIL} failed")
    return 0 if _FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
