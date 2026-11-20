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
            "coverage_gap.declare_bypass_gap('planted permission half', 'the filesystem did not honour the plant')\n"
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
            "coverage_gap.declare_gap('planted declared half', 'reported inside the seam')\n"
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
          "coverage_gap.declare_bypass_gap(" in src, src[:300])
    check("guard: the bare SKIP print of the bypass is gone from the tree",
          'print(f"  SKIP teardown' not in src and coverage_gap.BYPASS_PHRASE not in src, src[:400])
    check("guard: the always-checked half is still named as the contract it keeps",
          "still locks its contract" in src, src[:400])


def main() -> int:
    print("test suite identity + coverage-gap seam (#1147) — real runner, real wrapper, real make recipe")
    test_the_runner_names_the_identity_it_measured()
    test_the_identity_line_distinguishes_a_container_uid_from_the_invoker()
    test_a_declared_gap_in_a_GREEN_module_reaches_the_verdict()
    test_a_bypass_that_never_declared_its_gap_turns_the_runner_red()
    test_a_declared_and_an_undeclared_line_in_one_module_are_separated()
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
