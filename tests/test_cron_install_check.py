#!/usr/bin/env python3
"""Offline tests for scripts/cron_install_check.py (issues #1270/#1409)."""
from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cic", ROOT / "scripts/cron_install_check.py")
assert spec is not None and spec.loader is not None
cic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cic)

PASSED = FAILED = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
    else:
        FAILED += 1
        print(f"  FAIL {label} {detail}".rstrip())


@contextlib.contextmanager
def env(**updates):
    """Set/unset environment variables for the duration of a block."""
    saved = {key: os.environ.get(key) for key in updates}
    for key, value in updates.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def run_main(argv: list[str]) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = cic.main(argv)
    return rc, out.getvalue()


def fleet_jobs() -> list[dict]:
    return [
        {"id": "w", "name": "tll-watch-monitor", "enabled": True, "no_agent": True,
         "script": "watch-job.py", "workdir": "/repo"},
        {"id": "a", "name": "tll-watch-agent", "enabled": True,
         "monitor_script": "agent-monitor.py", "workdir": "/repo"},
    ]


def write_jobs(path: Path, jobs: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"jobs": jobs}), encoding="utf-8")
    return path


def write_wrappers(wd: Path, watchdog_state: str = "watch.json",
                   agent_state: str = "agent.json") -> Path:
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "watch-job.py").write_text(
        f'STATE = "{watchdog_state}"\nHEARTBEAT_SECONDS = 0\n'
        'run("watch_monitor.py", --gh)\n', encoding="utf-8")
    (wd / "agent-monitor.py").write_text(
        f'STATE = "{agent_state}"\nHEARTBEAT_SECONDS = 900\n'
        'run("watch_monitor.py", --gh --heartbeat-seconds 900)\n', encoding="utf-8")
    return wd


def write_detector(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("C: R: M: H:\n", encoding="utf-8")
    return path


def write_install(home: Path, profile: str, jobs: list[dict]) -> tuple[Path, Path]:
    """A named-profile Hermes home carrying cron/jobs.json + scripts/."""
    root = home / ".hermes" / "profiles" / profile
    jf = write_jobs(root / "cron" / "jobs.json", jobs)
    return jf, write_wrappers(root / "scripts")


def baseline(tmp: Path) -> tuple[Path, Path, Path]:
    jf = write_jobs(tmp / "jobs.json", fleet_jobs())
    wd = write_wrappers(tmp / "wrappers", "watch-monitor-mac.json", "agent-mac.json")
    det = write_detector(tmp / "scripts" / "watch_monitor.py")
    return jf, det, wd


def test_baseline_and_every_refusal(tmp: Path) -> None:
    jf, detector, wd = baseline(tmp)
    jobs = cic.load_jobs(jf)
    check("baseline installation is clean", not cic.problems(jobs, detector, wd),
          str(cic.problems(jobs, detector, wd)))

    cases = {
        "disabled watchdog": lambda j: j[0].__setitem__("enabled", False),
        "missing monitor gate": lambda j: j[1].pop("monitor_script"),
        "missing workdir": lambda j: j[0].pop("workdir"),
        "two watchdogs": lambda j: j.append(dict(j[0], id="w2")),
        "agent wrapper lost heartbeat": lambda j: (wd / "agent-monitor.py").write_text(
            'STATE = "agent-mac.json"\nrun("watch_monitor.py", --gh)\n'),
        "watchdog gained heartbeat": lambda j: (wd / "watch-job.py").write_text(
            'STATE = "watch-monitor-mac.json"\nHEARTBEAT_SECONDS = 900\n'
            'run("watch_monitor.py", --gh)\n'),
    }
    for name, break_it in cases.items():
        j = copy.deepcopy(jobs)
        break_it(j)
        check(f"refused: {name}", bool(cic.problems(j, detector, wd)), name)

    (wd / "watch-job.py").write_text('STATE = "agent-mac.json"\n')
    check("refused: shared state file", bool(cic.problems(jobs, detector, wd)))
    (wd / "watch-job.py").write_text('STATE = "watch-monitor-mac.json"\nrun("other.py")\n')
    check("refused: wrapper without repo detector", bool(cic.problems(jobs, detector, wd)))
    detector.write_text("C:\n")
    check("refused: detector lost R/M markers", bool(cic.problems(jobs, detector, wd)))


def test_hermes_homes_order(tmp: Path) -> None:
    home = tmp / "home"
    alpha = home / ".hermes" / "profiles" / "alpha"
    beta = home / ".hermes" / "profiles" / "beta"
    alpha.mkdir(parents=True)
    beta.mkdir(parents=True)
    plain = cic.hermes_homes(home=home, env_home="")
    check("homes: ~/.hermes first, then profiles sorted",
          [h.name for h in plain] == [".hermes", "alpha", "beta"], str(plain))
    named = cic.hermes_homes(home=home, env_home=str(alpha))
    check("homes: $HERMES_HOME first and never repeated",
          [h.name for h in named] == ["alpha", ".hermes", "beta"], str(named))


def test_discovery_skips_an_empty_jobs_file(tmp: Path) -> None:
    home = tmp / "home"
    empty = write_jobs(home / ".hermes" / "profiles" / "alpha" / "cron" / "jobs.json", [])
    full, _ = write_install(home, "beta", fleet_jobs())
    path, jobs = cic.discover_jobs(cic.hermes_homes(home=home, env_home=""))
    check("discovery skips the empty profile and takes the one with jobs",
          path == full and len(jobs) == 2, f"path={path}")
    only_empty, only_jobs = cic.discover_jobs([empty.parent.parent])
    check("discovery reports the empty file when nothing carries jobs",
          only_empty == empty and only_jobs == [], f"path={only_empty}")


def test_discovery_without_jobs_is_clean(tmp: Path) -> None:
    home = tmp / "home"
    (home / ".hermes" / "profiles" / "alpha").mkdir(parents=True)
    path, jobs = cic.discover_jobs(cic.hermes_homes(home=home, env_home=""))
    check("no jobs anywhere -> (None, [])", path is None and jobs == [], f"path={path}")


def test_clean_shell_discovers_the_profile_install(tmp: Path) -> None:
    home = tmp / "home"
    jf, _ = write_install(home, "alpha", fleet_jobs())
    det = write_detector(tmp / "repo" / "scripts" / "watch_monitor.py")
    with env(HOME=str(home), HERMES_HOME=None, HERMES_SESSION_PROFILE=None, CRON_JOBS=None):
        rc, out = run_main(["--detector", str(det)])
    check("clean shell reports OK 2 job(s)", rc == 0 and "[cron-install] OK 2 job(s)" in out, out)
    check("clean shell read the discovered profile jobs file", jf.is_file(), str(jf))


def test_host_with_no_jobs_fails_cleanly(tmp: Path) -> None:
    home = tmp / "home"
    (home / ".hermes").mkdir(parents=True)
    det = write_detector(tmp / "repo" / "scripts" / "watch_monitor.py")
    with env(HOME=str(home), HERMES_HOME=None, HERMES_SESSION_PROFILE=None, CRON_JOBS=None):
        rc, out = run_main(["--detector", str(det)])
    check("no jobs -> exit 1", rc == 1, out)
    check("no jobs -> the existing watchdog refusal",
          "expected exactly 1 no-agent watchdog job, found 0" in out, out)
    check("no jobs -> no FileNotFoundError", "FileNotFoundError" not in out, out)
    check("no jobs -> no traceback", "Traceback" not in out, out)


def test_explicit_overrides_still_work(tmp: Path) -> None:
    jf, detector, wd = baseline(tmp)
    with env(HOME=str(tmp / "empty"), HERMES_HOME=None, CRON_JOBS=None):
        rc, out = run_main(["--jobs", str(jf), "--wrappers", str(wd), "--detector", str(detector)])
    check("explicit --jobs/--wrappers -> OK 2 job(s)",
          rc == 0 and "[cron-install] OK 2 job(s)" in out, out)


def test_explicit_missing_jobs_is_a_clean_failure(tmp: Path) -> None:
    det = write_detector(tmp / "repo" / "scripts" / "watch_monitor.py")
    with env(HOME=str(tmp / "empty"), HERMES_HOME=None, CRON_JOBS=None):
        rc, out = run_main(["--jobs", str(tmp / "nope.json"), "--detector", str(det)])
    check("explicit missing --jobs -> exit 1", rc == 1, out)
    check("explicit missing --jobs -> FileNotFoundError, no traceback",
          "FileNotFoundError" in out and "Traceback" not in out, out)


def test_no_network_or_subprocess_import() -> None:
    src = (ROOT / "scripts" / "cron_install_check.py").read_text(encoding="utf-8")
    banned = [m for m in ("socket", "urllib", "requests", "http.client", "subprocess")
              if f"import {m}" in src]
    check("the checker imports no network or subprocess module", not banned, str(banned))


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        test_baseline_and_every_refusal(tmp / "a")
        test_hermes_homes_order(tmp / "b")
        test_discovery_skips_an_empty_jobs_file(tmp / "c")
        test_discovery_without_jobs_is_clean(tmp / "d")
        test_clean_shell_discovers_the_profile_install(tmp / "e")
        test_host_with_no_jobs_fails_cleanly(tmp / "f")
        test_explicit_overrides_still_work(tmp / "g")
        test_explicit_missing_jobs_is_a_clean_failure(tmp / "h")
        test_no_network_or_subprocess_import()
    print(f"PASSED {PASSED} | FAILED {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
