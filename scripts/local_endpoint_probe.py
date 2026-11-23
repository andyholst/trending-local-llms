#!/usr/bin/env python3
"""Record a capped live probe of the fleet chain's LOCAL tier endpoint (issue #1352).

The chain's `local_fallback` tier (issue #1192) points at the owner's own box. When that box
goes silent a lane blocks until its own client timeout before the paid last resort, and neither
the outage nor the recovery is visible to any gate: `make agent-model-chain-check` is a static
shape/render gate and stayed green through both states (measured, issue #1194). This seam is the
detector, in two halves:

- `--probe` (live, host-run) reads the `local_fallback` step's OWN endpoint and model from
  `agents/model_chain.json` (the ONE chain, issue #1140), POSTs a one-token chat completion
  with a CAPPED timeout, and records the result in the chain's `measured.local` — `last_probe`
  plus an additive `probe_history` (rule 3b: a row is only ever appended). The local tier is
  credential-less (issue #1192), so no key is read, named or printed.
- `--check` (offline, CI-run through `make lint`) reads that record. It REFUSES a missing
  record, or one whose endpoint/model no longer matches the chain (a real drift: the chain
  moved and the record did not), and REPORTS staleness loudly (`STALE age=…`) without ever
  touching the endpoint — so auto-merge cannot depend on a host box (issue #1352).

Exit codes: 0 probed ok / record present and matching, 1 the endpoint is down or the record is
missing or drifted, 2 the chain or the record cannot be read (never a silent clean).
`--dry-run` probes and prints without writing; `--report` prints the record and exits 0.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAIN_REL = "agents/model_chain.json"
LOCAL_ROLE = "local_fallback"
EXIT_OK, EXIT_PROBLEM, EXIT_UNDECIDABLE = 0, 1, 2

# The ONE pins — the Makefile carries the same values and `--check` refuses a tree whose pins
# drifted, so the cap and the staleness window cannot be weakened silently.
PIN_NAMES = ("LOCAL_PROBE_TIMEOUT_SECONDS", "LOCAL_PROBE_MAX_AGE_HOURS", "LOCAL_PROBE_HISTORY_MAX")
DEFAULT_PINS = {"LOCAL_PROBE_TIMEOUT_SECONDS": 20, "LOCAL_PROBE_MAX_AGE_HOURS": 24,
                "LOCAL_PROBE_HISTORY_MAX": 50}
PIN_RE = re.compile(r"^(LOCAL_PROBE_[A-Z_]+)\s*\?=\s*(\S+)\s*$", re.M)


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def stamp(now: dt.datetime | None = None) -> str:
    return (now or utc_now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_pins(root: Path) -> tuple[dict[str, int], list[str]]:
    """Read the Makefile's LOCAL_PROBE_* pins; a missing pin falls back to the script default."""
    path = root / "Makefile"
    if not path.is_file():
        return dict(DEFAULT_PINS), ["Makefile is missing — the probe pins cannot be read"]
    found = {name: int(value) for name, value in PIN_RE.findall(path.read_text(encoding="utf-8"))
             if value.isdigit()}
    pins = dict(DEFAULT_PINS)
    pins.update(found)
    problems = [f"Makefile no longer pins {name}" for name in PIN_NAMES if name not in found]
    return pins, problems


def read_chain(root: Path) -> tuple[dict | None, list[str]]:
    """Read `agents/model_chain.json`. Returns (data, fatal) — a fatal means exit 2."""
    path = root / CHAIN_REL
    if not path.is_file():
        return None, [f"{CHAIN_REL} is missing — the local tier has no source to probe"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"{CHAIN_REL} is not readable JSON: {exc}"]
    if not isinstance(data, dict):
        return None, [f"{CHAIN_REL} is not a JSON object"]
    return data, []


def local_tier(data: dict) -> tuple[dict | None, str]:
    """The chain's ONE `local_fallback` step — its OWN endpoint and bare server model id."""
    rows = data.get("chain")
    if not isinstance(rows, list):
        return None, "the chain carries no `chain` list"
    tiers = [row for row in rows if isinstance(row, dict) and row.get("role") == LOCAL_ROLE]
    if not tiers:
        return None, f"the chain carries no role={LOCAL_ROLE} tier — nothing local to probe"
    tier = tiers[0]
    base_url = str(tier.get("base_url") or "").strip()
    model = str(tier.get("model") or "").strip()
    if not base_url or not model:
        return None, f"the {LOCAL_ROLE} tier names no base_url/model of its own"
    return {"alias": str(tier.get("alias") or LOCAL_ROLE), "base_url": base_url, "model": model}, ""


def probe(base_url: str, model: str, timeout: int, now: dt.datetime | None = None) -> dict:
    """POST a one-token chat completion with a CAPPED timeout. Never raises."""
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": "ping"}],
                       "max_tokens": 1}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    started = time.monotonic()
    result = {"at": stamp(now), "endpoint": base_url, "model": model,
              "http": 0, "latency_s": 0.0, "ok": False, "error": None}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result["http"] = resp.status
            payload = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        result["http"] = exc.code
        result["error"] = f"HTTP {exc.code}"
        payload = ""
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        payload = ""
    result["latency_s"] = round(time.monotonic() - started, 3)
    if result["http"] == 200:
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            parsed = None
        choices = parsed.get("choices") if isinstance(parsed, dict) else None
        if isinstance(choices, list) and choices:
            result["ok"] = True
        else:
            result["error"] = "HTTP 200 but the payload carries no `choices` list"
    elif result["error"] is None:
        result["error"] = f"HTTP {result['http']} answered no chat completion"
    return result


def record(root: Path, result: dict, history_max: int) -> tuple[bool, list[str]]:
    """Write `measured.local.last_probe` + append `probe_history`. Additive; returns (written, fatal)."""
    data, fatal = read_chain(root)
    if fatal:
        return False, fatal
    assert data is not None
    measured = data.get("measured") if isinstance(data.get("measured"), dict) else {}
    local = measured.get("local") if isinstance(measured.get("local"), dict) else {}
    history = [row for row in local.get("probe_history") or [] if isinstance(row, dict)]
    local["last_probe"] = result
    if not any(_same_probe(row, result) for row in history[-1:]):
        history.append(result)
    if history_max > 0 and len(history) > history_max:
        history = history[-history_max:]
    local["probe_history"] = history
    measured["local"] = local
    data["measured"] = measured
    (root / CHAIN_REL).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True, []


def _same_probe(a: dict, b: dict) -> bool:
    """Two probe rows are the same RESULT when everything but the clock agrees."""
    keys = ("endpoint", "model", "http", "ok", "error")
    return all(a.get(k) == b.get(k) for k in keys)


def parse_stamp(value: object) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def staleness(record: dict, max_age_hours: int, now: dt.datetime | None = None) -> tuple[float, bool]:
    """Age in hours and whether it exceeds the pin. An unparseable stamp is callers' problem."""
    moment = parse_stamp(record.get("at"))
    if moment is None:
        return float("inf"), True
    age = ((now or utc_now()) - moment).total_seconds() / 3600.0
    return round(age, 2), age > max_age_hours


def check(root: Path, max_age_hours: int) -> int:
    data, fatal = read_chain(root)
    if fatal:
        for line in fatal:
            print(f"[local-probe] UNDECIDABLE: {line}", file=sys.stderr)
        return EXIT_UNDECIDABLE
    assert data is not None
    tier, problem = local_tier(data)
    if problem:
        print(f"[local-probe] UNDECIDABLE: {problem}", file=sys.stderr)
        return EXIT_UNDECIDABLE
    assert tier is not None
    measured = data.get("measured") if isinstance(data.get("measured"), dict) else {}
    local = measured.get("local") if isinstance(measured.get("local"), dict) else {}
    record_ = local.get("last_probe")
    if not isinstance(record_, dict) or not record_.get("at"):
        print(f"[local-probe] FAIL: {CHAIN_REL} carries no measured.local.last_probe — "
              f"the local tier has never been probed (run `make local-endpoint-probe`)", file=sys.stderr)
        return EXIT_PROBLEM
    if record_.get("endpoint") != tier["base_url"] or record_.get("model") != tier["model"]:
        print(f"[local-probe] FAIL: the recorded probe is for "
              f"{record_.get('endpoint')!r}/{record_.get('model')!r} but the chain's "
              f"{LOCAL_ROLE} tier is {tier['base_url']!r}/{tier['model']!r} — the record did not "
              f"follow the chain; re-run `make local-endpoint-probe`", file=sys.stderr)
        return EXIT_PROBLEM
    age, stale = staleness(record_, max_age_hours)
    state = "ok" if record_.get("ok") else "DOWN"
    flag = " STALE" if stale else ""
    print(f"[local-probe] {state} last probe {record_.get('at')} "
          f"http={record_.get('http')} age_h={age} stale={stale}{flag} "
          f"endpoint={record_.get('endpoint')} model={record_.get('model')}")
    return EXIT_OK


def report(root: Path) -> int:
    data, fatal = read_chain(root)
    if fatal:
        for line in fatal:
            print(f"[local-probe] UNDECIDABLE: {line}", file=sys.stderr)
        return EXIT_UNDECIDABLE
    assert data is not None
    measured = data.get("measured") if isinstance(data.get("measured"), dict) else {}
    local = measured.get("local") if isinstance(measured.get("local"), dict) else {}
    record_ = local.get("last_probe")
    history = [row for row in local.get("probe_history") or [] if isinstance(row, dict)]
    if not isinstance(record_, dict):
        print("[local-probe] no recorded probe")
        return EXIT_PROBLEM
    print(json.dumps({"last_probe": record_, "probe_history_rows": len(history)},
                     indent=2, sort_keys=True))
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe", action="store_true", help="probe the local tier and record it (default)")
    ap.add_argument("--check", action="store_true", help="offline: verify the record, report staleness")
    ap.add_argument("--report", action="store_true", help="print the recorded probe")
    ap.add_argument("--dry-run", action="store_true", help="probe and print, write nothing")
    ap.add_argument("--root", default=str(ROOT), help="repository root to read (tests plant a scratch tree)")
    ap.add_argument("--timeout", type=int, default=None, help="probe timeout in seconds")
    ap.add_argument("--max-age-hours", type=int, default=None, help="staleness window for --check")
    ap.add_argument("--history-max", type=int, default=None, help="probe_history cap")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    pins, pin_problems = read_pins(root)
    timeout = args.timeout if args.timeout is not None else pins["LOCAL_PROBE_TIMEOUT_SECONDS"]
    max_age = args.max_age_hours if args.max_age_hours is not None else pins["LOCAL_PROBE_MAX_AGE_HOURS"]
    history_max = args.history_max if args.history_max is not None else pins["LOCAL_PROBE_HISTORY_MAX"]

    if args.check:
        for problem in pin_problems:
            print(f"[local-probe] FAIL: {problem}", file=sys.stderr)
        rc = check(root, max_age)
        if pin_problems and rc == EXIT_OK:
            return EXIT_PROBLEM
        return rc
    if args.report:
        return report(root)

    data, fatal = read_chain(root)
    if fatal:
        for line in fatal:
            print(f"[local-probe] UNDECIDABLE: {line}", file=sys.stderr)
        return EXIT_UNDECIDABLE
    assert data is not None
    tier, problem = local_tier(data)
    if problem:
        print(f"[local-probe] UNDECIDABLE: {problem}", file=sys.stderr)
        return EXIT_UNDECIDABLE
    assert tier is not None
    result = probe(tier["base_url"], tier["model"], timeout)
    state = "ok" if result["ok"] else "DOWN"
    print(f"[local-probe] {state} http={result['http']} latency_s={result['latency_s']} "
          f"endpoint={result['endpoint']} model={result['model']}"
          + (f" error={result['error']}" if result["error"] else ""))
    if args.dry_run:
        print("[local-probe] DRY RUN: nothing written")
        return EXIT_OK if result["ok"] else EXIT_PROBLEM
    written, fatal = record(root, result, history_max)
    if fatal:
        for line in fatal:
            print(f"[local-probe] UNDECIDABLE: {line}", file=sys.stderr)
        return EXIT_UNDECIDABLE
    assert written
    print(f"[local-probe] recorded in {CHAIN_REL} measured.local "
          f"(history cap {history_max})")
    return EXIT_OK if result["ok"] else EXIT_PROBLEM


if __name__ == "__main__":
    raise SystemExit(main())
