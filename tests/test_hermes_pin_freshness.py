#!/usr/bin/env python3
"""The Hermes pin-freshness check (issue #1091, AGENTS.md rule 6k).

Drives the REAL `scripts/hermes_pin_freshness.py` end to end against a stub `gh` on PATH —
an EXTERNAL system, the only permitted stand-in (rule 6m): the pin reads, the version
comparison, the verdict lines, the marker-deduped filing and the exit codes are all executed
by the product. The upstream channel is planted as a recorded payload (the same fixture seam
`check_branch_protection.py`'s FROM_FILE uses), and the REAL recorded payload in
`tests/fixtures/hermes_releases_latest.json` is compared against the REAL Makefile/Dockerfile
pins so the seam itself stays honest.

The state this locks: the Makefile `HERMES_VERSION ?=` and the Dockerfile `ARG HERMES_VERSION`
pin the agent every image bakes (rule 6k, issue #218), but nothing compared them against the
upstream channel — a channel move surfaced only at the next image dispatch/build, with no
tracked home (issue #1091). The check must: refuse a pin disagreement loudly BEFORE consulting
the channel; go red + file ONE marker-deduplicated tech-debt issue naming the #218 remedy when
the channel is strictly newer; report (not red) when the pin is ahead; exit 2 — never a silent
clean — when the channel cannot be read; and the queued-alarm sweep must reach it ONLY through
`make hermes-pin-freshness`.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import bot_markers as bm  # noqa: E402  (rule 6j: the marker table, imported never re-spelled)

SCRIPT = ROOT / "scripts" / "hermes_pin_freshness.py"
QUEUE_WF = ROOT / ".github" / "workflows" / "queued-alarm.yml"
MAKEFILE = ROOT / "Makefile"
DOCKERFILE = ROOT / "Dockerfile"
RECORDED_CHANNEL = ROOT / "tests" / "fixtures" / "hermes_releases_latest.json"
REPO = "octo/repo"

#: Planted pins/channel so the verdicts are arithmetic, not a race with the live channel.
PLANT_PIN = "0.10.0"
PLANT_CHANNEL_NEWER = "v0.11.0"
PLANT_CHANNEL_OLDER = "v0.9.0"

#: A planted Makefile + Dockerfile pair sharing one pin (the rule-6k shape).
PLANT_MAKEFILE = """# planted Makefile (test fixture)
HERMES_VERSION ?= {pin}
"""
PLANT_DOCKERFILE = """# planted Dockerfile (test fixture)
ARG HERMES_VERSION="{pin}"
"""

STUB_GH = """#!/usr/bin/env bash
# Stub `gh` for tests/test_hermes_pin_freshness.py: canned answers keyed off the subcommand,
# everything it files captured under $HPFSTUB_DIR. The product under test never sees a mock —
# only this external stand-in for the GitHub API (rule 6m).
set -uo pipefail
d="$HPFSTUB_DIR"
printf '%s\\n' "$*" >> "$d/calls.log"
case "$1" in
  api)
    # The channel release endpoint: no planted payload means the channel is UNREADABLE —
    # the state that must produce exit 2, never a silent clean.
    case " $* " in
      *" repos/NousResearch/hermes-agent/releases/latest "*)
        if [ -f "$d/channel.json" ]; then cat "$d/channel.json"; exit 0; fi
        echo "gh: HTTP 404: Not Found (no releases)" >&2; exit 1 ;;
      *) echo "stub gh: unhandled api: $*" >&2; exit 1 ;;
    esac ;;
  issue)
    case "$2" in
      list)
        if [ -f "$d/issues.json" ]; then cat "$d/issues.json"; else echo "[]"; fi; exit 0 ;;
      create)
        title=""; body=""; prev=""
        for a in "$@"; do
          if [ "$prev" = "--title" ]; then title="$a"; fi
          if [ "$prev" = "--body" ]; then body="$a"; fi
          prev="$a"
        done
        n=$(python3 - "$d" "$title" "$body" <<'PY'
import json, sys, pathlib
d = pathlib.Path(sys.argv[1]); title = sys.argv[2]; body = sys.argv[3]
p = d / "issues.json"
issues = json.loads(p.read_text()) if p.exists() else []
num = max([i["number"] for i in issues], default=1000) + 1
issues.append({"number": num, "state": "OPEN", "title": title, "body": body,
               "url": f"https://github.com/octo/repo/issues/{num}"})
p.write_text(json.dumps(issues))
print(num)
PY
)
        echo "https://github.com/octo/repo/issues/$n"; exit 0 ;;
      *) echo "stub gh: unhandled: $*" >&2; exit 1 ;;
    esac ;;
  *) echo "stub gh: unhandled: $*" >&2; exit 1 ;;
esac
"""

_checks_passed = 0
_checks_failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global _checks_passed, _checks_failed
    if ok:
        _checks_passed += 1
        print(f"  ok   {name}")
    else:
        _checks_failed += 1
        print(f"  FAIL {name}" + (f"\n       {detail}" if detail else ""))


def make_scene(tmp: Path, channel: dict | None, issues: list | None = None,
               pin: str = PLANT_PIN) -> dict:
    """Stub bin + canned data; planted pins so no test races the live channel."""
    bindir = tmp / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    stub = bindir / "gh"
    stub.write_text(STUB_GH)
    stub.chmod(0o755)
    canned = tmp / "canned"
    canned.mkdir(parents=True, exist_ok=True)
    if channel is not None:
        (canned / "channel.json").write_text(json.dumps(channel))
    if issues is not None:
        (canned / "issues.json").write_text(json.dumps(issues))
    (tmp / "Makefile").write_text(PLANT_MAKEFILE.format(pin=pin))
    (tmp / "Dockerfile").write_text(PLANT_DOCKERFILE.format(pin=pin))
    env = dict(os.environ)
    env["PATH"] = f"{bindir}{os.pathsep}{env['PATH']}"
    env["HPFSTUB_DIR"] = str(canned)
    return env


def run_check(env: dict, tmp: Path | None = None, *extra: str) -> subprocess.CompletedProcess:
    argv = [sys.executable, str(SCRIPT), "--repo", REPO]
    if tmp is not None:
        argv += ["--makefile", str(tmp / "Makefile"), "--dockerfile", str(tmp / "Dockerfile")]
    proc = subprocess.run(argv + list(extra), capture_output=True, text=True, timeout=120,
                          env=env)
    return proc


def filed_issues(tmp: Path) -> list:
    p = tmp / "canned" / "issues.json"
    return json.loads(p.read_text()) if p.exists() else []


def gh_calls(tmp: Path) -> str:
    p = tmp / "canned" / "calls.log"
    return p.read_text() if p.exists() else ""


def test_channel_equal_to_pin_prints_ok_and_exits_green() -> None:
    print("\nequal: channel == pin -> `pin=<v> channel=<v> OK`, exit 0, no filing")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, {"tag_name": PLANT_PIN, "name": "Hermes Agent", "published_at": "2026-11-10T01:42:15Z"})
        proc = run_check(env, tmp)
        check("exit 0", proc.returncode == 0, proc.stderr)
        check("prints `pin=<v> channel=<v> OK`",
              re.search(r"pin=0\.10\.0 channel=0\.10\.0 OK", proc.stdout), proc.stdout)
        check("files nothing", len(filed_issues(tmp)) == 0, gh_calls(tmp))


def test_channel_newer_goes_red_files_one_tech_debt_issue_naming_the_remedy() -> None:
    print("\nnewer: channel strictly newer -> exit 1 + ONE tech-debt issue naming the #218 remedy")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, {"tag_name": PLANT_CHANNEL_NEWER})
        proc = run_check(env, tmp)
        check("exit 1 (loud)", proc.returncode == 1, f"rc={proc.returncode}\n{proc.stdout}{proc.stderr}")
        check("stdout names the DRIFT verdict", "DRIFT" in proc.stdout, proc.stdout)
        issues = filed_issues(tmp)
        check("exactly ONE issue filed", len(issues) == 1, json.dumps(issues))
        if issues:
            body, title = issues[0]["body"], issues[0]["title"]
            check("title names pin + channel", "0.10.0" in title and "0.11.0" in title, title)
            check("body carries the registered drift marker",
                  f"<!-- {bm.PIN_DRIFT_SIGNATURE_KEY}: hermes-pin-0.11.0 -->" in body, body)
            check("body names the remedy: raise BOTH pins together per #218",
                  "#218" in body and "HERMES_VERSION" in body, body)
            check("body carries the evidence pair (Makefile + Dockerfile lines)",
                  "Makefile:2" in body and 'ARG HERMES_VERSION="0.10.0"' in body, body)
        # DRY=1 (the --dry-run preview): the drift reports but files nothing.
        proc2 = run_check(env, tmp, "--dry-run")
        check("--dry-run reports the drift but files nothing",
              proc2.returncode == 1 and "filing skipped" in proc2.stdout
              and len(filed_issues(tmp)) == 1, proc2.stdout)


def test_the_drift_filing_is_marker_deduped_across_re_runs() -> None:
    print("\ndedup: the same drifted channel is filed once across sweeps; a CLOSED issue re-opens the filing")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, {"tag_name": PLANT_CHANNEL_NEWER})
        first = run_check(env, tmp)
        check("first sweep files one issue", first.returncode == 1 and len(filed_issues(tmp)) == 1,
              gh_calls(tmp))
        second = run_check(env, tmp)
        check("re-run still exits 1 (the drift is still real)", second.returncode == 1,
              f"rc={second.returncode}")
        check("re-run files NOTHING new (marker dedup on the open issue)",
              len(filed_issues(tmp)) == 1, json.dumps(filed_issues(tmp)))
        check("re-run says `already-filed=<url>`", "already-filed=" in second.stdout, second.stdout)
        # A closed drift issue does not block a fresh sweep forever (the data-gap dedup lesson):
        issues = filed_issues(tmp)
        issues[0]["state"] = "CLOSED"
        (tmp / "canned" / "issues.json").write_text(json.dumps(issues))
        third = run_check(env, tmp)
        check("a CLOSED drift issue does not suppress a still-live drift",
              third.returncode == 1 and len(filed_issues(tmp)) == 2, json.dumps(filed_issues(tmp)))
        check("the dedup search ran through gh issue list", "issue list" in gh_calls(tmp), "")


def test_pin_ahead_of_channel_is_reported_not_red() -> None:
    print("\nahead: pin newer than channel -> reported, exit 0, no filing")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, {"tag_name": PLANT_CHANNEL_OLDER})
        proc = run_check(env, tmp)
        check("exit 0 (a reported state, never red)", proc.returncode == 0, proc.stderr)
        check("stdout reports AHEAD", "AHEAD" in proc.stdout, proc.stdout)
        check("files nothing", len(filed_issues(tmp)) == 0, gh_calls(tmp))


def test_unreadable_channel_is_a_loud_exit_two_never_a_clean() -> None:
    print("\nunreadable: the channel cannot be read -> exit 2 naming why, never a silent clean")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, None)  # no channel.json -> the stub refuses `gh api`
        proc = run_check(env, tmp)
        check("exit 2", proc.returncode == 2, f"rc={proc.returncode}")
        check("it never prints OK", "OK" not in proc.stdout, proc.stdout)
        check("stderr names the unreadable channel",
              "could not be read" in proc.stderr, proc.stderr)
        check("files nothing", len(filed_issues(tmp)) == 0, gh_calls(tmp))


def test_pin_disagreement_between_makefile_and_dockerfile_refuses_before_the_channel_is_read() -> None:
    print("\npins: Makefile != Dockerfile -> loud refusal (exit 2) BEFORE the channel is consulted")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, {"tag_name": PLANT_CHANNEL_NEWER}, pin=PLANT_PIN)
        (tmp / "Dockerfile").write_text(PLANT_DOCKERFILE.format(pin="0.10.1"))
        proc = run_check(env, tmp)
        check("exit 2 (the #218 defect itself)", proc.returncode == 2, f"rc={proc.returncode}")
        check("the message names both pins", "0.10.0" in proc.stderr and "0.10.1" in proc.stderr,
              proc.stderr)
        check("it names the rule-6k remedy (raise BOTH together)", "BOTH" in proc.stderr, proc.stderr)
        check("the channel was NEVER consulted", "api" not in gh_calls(tmp), gh_calls(tmp))
        check("nothing was filed", len(filed_issues(tmp)) == 0, "")


def test_recorded_channel_payload_is_compared_against_the_real_pins() -> None:
    print("\nrecorded: the REAL fixture payload vs the REAL Makefile/Dockerfile pins (rule 6m seam)")
    check("the recorded payload exists", RECORDED_CHANNEL.is_file(), str(RECORDED_CHANNEL))
    payload = json.loads(RECORDED_CHANNEL.read_text())
    check("the recorded payload carries a real tag_name", bool(str(payload.get("tag_name") or "").strip()),
          "")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, None)  # a live gh would be refused; --from-file must be used instead
        # The env carries the stub PATH, so a broken --from-file path would show up as a
        # refused gh api call rather than a real network read.
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", REPO, "--from-file", str(RECORDED_CHANNEL)],
            capture_output=True, text=True, timeout=120, env=env)
        check("green against the real pins (OK today, AHEAD after a pin bump)",
              proc.returncode == 0 and ("OK" in proc.stdout or "AHEAD" in proc.stdout),
              f"rc={proc.returncode}\n{proc.stdout}{proc.stderr}")
        check("--from-file never calls gh api", "api" not in gh_calls(tmp), gh_calls(tmp))


def _alarm_problems(text: str) -> list:
    """The wiring guard (rule 6m): the sweep must call `make hermes-pin-freshness`, and no
    workflow may reach the script past the Makefile."""
    problems = []
    doc = yaml.safe_load(text)
    steps = doc["jobs"]["alarm"]["steps"]
    pin_steps = [s for s in steps if "hermes-pin-freshness" in str(s.get("run", ""))]
    if not pin_steps:
        problems.append("the queued-alarm sweep has no hermes-pin-freshness step")
    for s in steps:
        run = str(s.get("run", ""))
        if "hermes-pin-freshness" in run and "make hermes-pin-freshness" not in run:
            problems.append(f"step {s.get('name')!r} reaches hermes-pin-freshness without make")
    for s in pin_steps:
        env = s.get("env") or {}
        if "github.token" not in str(env.get("GH_TOKEN", "")):
            problems.append(f"step {s.get('name')!r} does not file with the default token")
        if "FIXBOT_DISPATCH_TOKEN" in str(env):
            problems.append(f"step {s.get('name')!r} reaches the owner PAT")
    return problems


def test_queued_alarm_sweep_calls_the_target_and_a_makeless_step_is_refused() -> None:
    print("\nwiring: queued-alarm calls `make hermes-pin-freshness`; a missing step or a "
          "script-past-the-Makefile step is REFUSED (rule 6m)")
    text = QUEUE_WF.read_text(encoding="utf-8")
    problems = _alarm_problems(text)
    check("queued-alarm.yml carries the make-wired step", problems == [], problems)
    # The guard must be able to fail: the same scan RED on a step that skips `make`…
    makeless = text.replace("run: make hermes-pin-freshness REPO=", "run: python3 scripts/hermes_pin_freshness.py --repo ")
    planted = _alarm_problems(makeless)
    check("a step reaching the script without make is REFUSED", bool(planted), planted)
    # …and RED on a sweep that dropped the step entirely.
    dropped = re.sub(r"      - name: Fail loudly when the Hermes agent pin.*?repository \}\}\"\n",
                     "", text, flags=re.S)
    planted = _alarm_problems(dropped)
    check("a sweep without the step is REFUSED", bool(planted) and "no hermes-pin-freshness step" in " ".join(planted), planted)
    # No workflow anywhere may name the script directly (rule 6m).
    direct = []
    for wf in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        if "hermes_pin_freshness.py" in wf.read_text(encoding="utf-8"):
            direct.append(wf.name)
    check("no workflow reaches scripts/hermes_pin_freshness.py past the Makefile", direct == [], direct)
    # The Makefile recipe is the ONLY path to the script, and `make -n` proves the wiring.
    mk = MAKEFILE.read_text(encoding="utf-8")
    check("the Makefile defines the public target and the internal recipe",
          "\nhermes-pin-freshness:" in mk and "_hermes-pin-freshness:" in mk, "")
    check("the internal recipe is the only thing naming the script",
          "_hermes-pin-freshness:\n\tpython3 scripts/hermes_pin_freshness.py" in mk.replace("\r\n", "\n"),
          "")
    r = subprocess.run(["make", "-n", "hermes-pin-freshness", "REPO=o/r"], cwd=ROOT,
                       capture_output=True, text=True, timeout=60)
    check("make -n runs the script with --repo", r.returncode == 0
          and "hermes_pin_freshness.py --repo \"o/r\"" in r.stdout, r.stdout)
    r = subprocess.run(["make", "-n", "hermes-pin-freshness", "REPO=o/r", "DRY=1"], cwd=ROOT,
                       capture_output=True, text=True, timeout=60)
    check("make honours DRY=1 as --dry-run", "--dry-run" in r.stdout, r.stdout)


def test_the_drift_marker_is_registered_in_bot_markers() -> None:
    print("\nregistry: the drift marker is a registered dedup key in scripts/bot_markers.py (rule 6j)")
    check("the key is registered in DEDUP_KEYS", bm.PIN_DRIFT_SIGNATURE_KEY in bm.DEDUP_KEYS,
          str(bm.DEDUP_KEYS))
    acc = bm.marker_acceptance()
    check("the registry accepts the writer's rendering",
          bm.PIN_DRIFT_SIGNATURE_KEY in acc
          and acc[bm.PIN_DRIFT_SIGNATURE_KEY].search(
              "<!-- hermes-pin-drift-signature: hermes-pin-0.11.0 -->"), "")
    check("a placeholder rendering is still accepted as the family shape",
          any(bm.PIN_DRIFT_SIGNATURE_KEY in ex for ex in bm.canonical_examples()), "")
    # The writer renders it through the registered name, never a re-spelled literal copy.
    src = SCRIPT.read_text(encoding="utf-8")
    spellings = re.findall(r"<!-- hermes-pin-drift-signature", src)
    check("the script spells the marker only through the registered name",
          not spellings, f"{len(spellings)} literal re-spellings")


def main() -> int:
    print("hermes pin freshness: the pinned agent vs the upstream channel (issue #1091)")
    test_channel_equal_to_pin_prints_ok_and_exits_green()
    test_channel_newer_goes_red_files_one_tech_debt_issue_naming_the_remedy()
    test_the_drift_filing_is_marker_deduped_across_re_runs()
    test_pin_ahead_of_channel_is_reported_not_red()
    test_unreadable_channel_is_a_loud_exit_two_never_a_clean()
    test_pin_disagreement_between_makefile_and_dockerfile_refuses_before_the_channel_is_read()
    test_recorded_channel_payload_is_compared_against_the_real_pins()
    test_queued_alarm_sweep_calls_the_target_and_a_makeless_step_is_refused()
    test_the_drift_marker_is_registered_in_bot_markers()
    print(f"\nPASSED {_checks_passed} | FAILED {_checks_failed}")
    return 0 if _checks_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
