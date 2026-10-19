#!/usr/bin/env python3
"""The gap baseline's age is reported (issue #307).

`data/gap_baseline.json` is the dedup key: `changed()` compares its `signature` and a
match files nothing. Its `as_of` was written by `write_baseline()` and read by nobody,
so a baseline left behind by a rebase or a closed refresh PR silently suppressed the
filing for as long as it stayed put — with nothing in the report or the run log saying
when it had been recorded.

These tests drive the REAL script (`scripts/data_gap_analysis.py`) through its CLI and
its own functions — no mocks.

Run:  python3 tests/test_data_gap_baseline_age.py   or   make test
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "data_gap_analysis.py"
STORE = ROOT / "data" / "models.json"
BASELINE = ROOT / "data" / "gap_baseline.json"

_PASS = 0
_FAIL = 0


def check(name, cond, detail: object = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name}" + (f"  [{detail}]" if detail else ""))


def _module():
    spec = importlib.util.spec_from_file_location("data_gap_analysis", SCRIPT)
    assert spec and spec.loader, SCRIPT
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_age_is_measured_from_the_baseline_as_of():
    mod = _module()
    info_fn = getattr(mod, "baseline_info", None)
    check("baseline: the script reads the baseline's age (issue #307)", callable(info_fn), mod)
    if not callable(info_fn):
        return
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "gap_baseline.json"

        # Given a baseline recorded 40 days before the analysis
        path.write_text(json.dumps({"as_of": "2026-09-09T00:00:00Z", "signature": ["a"]}),
                        encoding="utf-8")
        old = info_fn(path, "2026-10-19T00:00:00Z")

        # Then  the age is that gap, and the recorded stamp is kept
        check("baseline: the recorded as_of is reported",
              old and old["baseline_as_of"] == "2026-09-09T00:00:00Z", old)
        check("baseline: the age is measured in days",
              old and old["baseline_age_days"] == 40, old)

        # Given a baseline recorded yesterday
        path.write_text(json.dumps({"as_of": "2026-10-18T00:00:00Z", "signature": ["a"]}),
                        encoding="utf-8")
        fresh = mod.baseline_info(path, "2026-10-19T00:00:00Z")
        check("baseline: a fresh one is 1 day old", fresh and fresh["baseline_age_days"] == 1, fresh)

        # Given an unreadable stamp, or no baseline at all
        path.write_text(json.dumps({"as_of": "not-a-date", "signature": []}), encoding="utf-8")
        broken = mod.baseline_info(path, "2026-10-19T00:00:00Z")
        check("baseline: an unparseable stamp reports an unknown age, never a crash",
              broken and broken["baseline_age_days"] is None, broken)
        check("baseline: a missing file reports nothing",
              mod.baseline_info(Path(td) / "nope.json", "2026-10-19T00:00:00Z") is None, "")


def test_render_carries_the_baseline_line():
    mod = _module()
    report = {"as_of": "2026-10-19T00:00:00Z", "models": 1, "signature": [], "findings": [],
              "contract_gaps": {}, "missing": {}, "unstructured": {},
              "baseline_as_of": "2026-09-09T00:00:00Z", "baseline_age_days": 40}
    text = mod.render(report)
    check("render: the baseline's stamp and age are in the report",
          "- baseline: recorded `2026-09-09T00:00:00Z` (40 day(s) before this analysis)" in text,
          text[:300])
    report.pop("baseline_as_of")
    check("render: no baseline line when there is no baseline",
          "baseline:" not in mod.render(report), "")


def test_the_run_log_shouts_when_the_baseline_is_stale():
    """The CLI, on the real store, with a baseline older than STALE_DAYS."""
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "gap_baseline.json"
        # Same signature as the current analysis, so nothing would be filed — the
        # exact state this issue is about: a silent "unchanged" from a stale key.
        current = json.loads(BASELINE.read_text(encoding="utf-8"))
        current["as_of"] = "2026-08-01T00:00:00Z"
        path.write_text(json.dumps(current), encoding="utf-8")

        proc = subprocess.run([sys.executable, str(SCRIPT), "--baseline", str(path)],
                              cwd=ROOT, capture_output=True, text=True)

    check("stale: exit 0 (a stale baseline is reported, not fatal)", proc.returncode == 0,
          proc.stdout[-300:] + proc.stderr[-300:])
    check("stale: the log names the baseline's age",
          "baseline: recorded 2026-08-01T00:00:00Z" in proc.stderr, proc.stderr[-400:])
    check("stale: the log shouts STALE and how to fix it",
          "baseline is STALE" in proc.stderr and "make data-gap-baseline" in proc.stderr,
          proc.stderr[-400:])
    check("stale: the report says the same thing where the issue reads it",
          "baseline: recorded `2026-08-01T00:00:00Z`" in proc.stdout
          and "re-record it with `make data-gap-baseline`" in proc.stdout, proc.stdout[:600])


def test_a_fresh_baseline_is_not_called_stale():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "gap_baseline.json"
        current = json.loads(BASELINE.read_text(encoding="utf-8"))
        # Re-recorded from THIS store, i.e. the shape a normal refresh writes.
        path.write_text(json.dumps(current), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(SCRIPT), "--baseline", str(path)],
                              cwd=ROOT, capture_output=True, text=True)

    check("fresh: exit 0", proc.returncode == 0, proc.stderr[-200:])
    check("fresh: the log still reports WHICH baseline was used",
          "baseline: recorded" in proc.stderr, proc.stderr[-300:])
    check("fresh: it is not called stale", "baseline is STALE" not in proc.stderr, proc.stderr[-300:])


def main() -> int:
    if not STORE.exists() or not BASELINE.exists():
        print("SKIP: data/models.json or data/gap_baseline.json missing")
        return 0
    print("data-gap baseline age (issue #307)")
    test_age_is_measured_from_the_baseline_as_of()
    test_render_carries_the_baseline_line()
    test_the_run_log_shouts_when_the_baseline_is_stale()
    test_a_fresh_baseline_is_not_called_stale()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
