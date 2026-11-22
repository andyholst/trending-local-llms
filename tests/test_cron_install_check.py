#!/usr/bin/env python3
"""Offline tests for scripts/cron_install_check.py (issue #1270)."""
from __future__ import annotations

import importlib.util
import json
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


def baseline(tmp: Path) -> tuple[Path, Path, Path]:
    jobs = [
        {"id": "w", "name": "tll-watch-monitor-mac", "enabled": True, "no_agent": True,
         "script": "watch-job.py", "workdir": "/repo"},
        {"id": "a", "name": "tll-comment-trigger", "enabled": True,
         "monitor_script": "agent-monitor.py", "workdir": "/repo"},
    ]
    jf = tmp / "jobs.json"; jf.write_text(json.dumps(jobs))
    wd = tmp / "wrappers"; wd.mkdir()
    (wd / "watch-job.py").write_text('STATE = "watch-monitor-mac.json"\nrun("watch_monitor.py", --gh)\n')
    (wd / "agent-monitor.py").write_text('STATE = "agent-mac.json"\nrun("watch_monitor.py", --gh)\n')
    det = tmp / "scripts"; det.mkdir()
    (det / "watch_monitor.py").write_text("C: R: M:\n")
    return jf, det / "watch_monitor.py", wd


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        jf, detector, wd = baseline(Path(td))
        jobs = cic.load_jobs(jf)
        check("baseline installation is clean", not cic.problems(jobs, detector, wd), str(cic.problems(jobs, detector, wd)))

        import copy
        cases = {
            "disabled watchdog": lambda j: j[0].__setitem__("enabled", False),
            "missing monitor gate": lambda j: j[1].pop("monitor_script"),
            "missing workdir": lambda j: j[0].pop("workdir"),
            "two watchdogs": lambda j: j.append(dict(j[0], id="w2")),
        }
        for name, break_it in cases.items():
            j = copy.deepcopy(jobs); break_it(j)
            check(f"refused: {name}", bool(cic.problems(j, detector, wd)), name)

        (wd / "watch-job.py").write_text('STATE = "agent-mac.json"\n')
        check("refused: shared state file", bool(cic.problems(jobs, detector, wd)))
        (wd / "watch-job.py").write_text('STATE = "watch-monitor-mac.json"\nrun("other.py")\n')
        check("refused: wrapper without repo detector", bool(cic.problems(jobs, detector, wd)))
        detector.write_text("C:\n")
        check("refused: detector lost R/M markers", bool(cic.problems(jobs, detector, wd)))

    print(f"PASSED {PASSED} | FAILED {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
