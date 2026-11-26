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
import hermes_pin_freshness as hpf  # noqa: E402  (rule 6d: the pin readers, imported never re-spelled)

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

#: A planted Makefile + Dockerfile pair sharing one pin (the rule-6k shape), and
#: the channel pin the check must READ from it (issue #1094 — the planted repo is
#: deliberately NOT the vendor repo so a hard-coded channel cannot pass).
PLANT_CHANNEL_REPO = "octo/planted-hermes-channel"
PLANT_MAKEFILE = """# planted Makefile (test fixture)
HERMES_VERSION ?= {pin}
HERMES_CHANNEL_REPO ?= octo/planted-hermes-channel
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
      *" repos/octo/planted-hermes-channel/releases/latest "*)
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
        # issue #1094: the endpoint queried is the DERIVED Makefile channel, not a
        # channel baked into the script (the stub serves ONLY the planted repo).
        check("the gh api call names the planted Makefile channel",
              f"repos/{PLANT_CHANNEL_REPO}/releases/latest" in gh_calls(tmp), gh_calls(tmp))
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
            check("body evidence names the DERIVED channel repo",
                  f"repos/{PLANT_CHANNEL_REPO}/releases/latest" in body, body)
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


def one_release_problems(makefile: Path, dockerfile: Path, payload: Path) -> list[str]:
    """The agreement the shipped tree must satisfy, read through the gate's OWN parsers (rule 6d).

    `hermes_pin_freshness.read_pins` is the only reader of the two pin spellings and
    `channel_tag` the only reader of a recorded payload, so this guard can never drift from
    what `make hermes-pin-freshness` itself compares (issue #1161).
    """
    mk_pin, mk_line, df_pin, df_line = hpf.read_pins(makefile, dockerfile)
    recorded = hpf.channel_tag(str(payload), "unused/planted-channel")
    if hpf.compare(mk_pin, df_pin) == 0 and hpf.compare(mk_pin, recorded) == 0:
        return []
    return [
        "the release spellings disagree: "
        f"{makefile.name}:{mk_line} `HERMES_VERSION ?= {mk_pin}` vs "
        f"{dockerfile.name}:{df_line} `ARG HERMES_VERSION=\"{df_pin}\"` vs "
        f"{payload.name} `tag_name: {recorded}` — a pin raise and its recorded channel payload "
        "land in ONE change (rule 6b, issue #218)"
    ]


def test_the_shipped_pins_and_the_recorded_payload_name_one_release() -> None:
    print("\nagreement: the REAL pins and the REAL recorded payload name ONE release (issue #1161)")
    shipped = one_release_problems(MAKEFILE, DOCKERFILE, RECORDED_CHANNEL)
    check("the shipped Makefile pin, Dockerfile ARG and recorded payload name one release",
          not shipped, "; ".join(shipped))

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        raised_mk = tmp / "Makefile"
        raised_df = tmp / "Dockerfile"
        raised_mk.write_text(PLANT_MAKEFILE.format(pin="0.23.3"))
        raised_df.write_text(PLANT_DOCKERFILE.format(pin="0.23.3"))
        lagging = tmp / "hermes_releases_latest.json"
        lagging.write_text(json.dumps({"tag_name": "v0.23.2"}))
        problems = one_release_problems(raised_mk, raised_df, lagging)
        check("a payload the pin raise left behind is refused naming all three spellings",
              len(problems) == 1 and "0.23.3" in problems[0] and "v0.23.2" in problems[0],
              str(problems))
        ahead = tmp / "ahead.json"
        ahead.write_text(json.dumps({"tag_name": "v0.23.4"}))
        ahead_problems = one_release_problems(raised_mk, raised_df, ahead)
        check("a payload ahead of the pins is refused too (the guard is arithmetic, not a snapshot)",
              len(ahead_problems) == 1 and "v0.23.4" in ahead_problems[0], str(ahead_problems))
        agreeing = tmp / "agree.json"
        agreeing.write_text(json.dumps({"tag_name": "v0.23.3"}))
        check("a planted pin+payload that name one release is green",
              not one_release_problems(raised_mk, raised_df, agreeing), "")


def _pin_problems(refresh_text: str, queued_text: str) -> list:
    """The wiring guard (rule 6m, issue #1093): the ONE scheduled pipeline must call
    `make hermes-pin-freshness` in a job gated by `guard` that can file the issue, the dispatched
    sweep must NOT own it any more, and no workflow may reach the script past the Makefile."""
    problems = []
    doc = yaml.safe_load(refresh_text)
    job = (doc.get("jobs") or {}).get("pin-freshness")
    if not job:
        problems.append("refresh-bot.yml has no pin-freshness job")
        return problems
    if "guard" not in (job.get("needs") or []):
        problems.append("the pin-freshness job does not need the guard (rule 6j)")
    perms = job.get("permissions") or {}
    if str(perms.get("issues", "")).lower() != "write":
        problems.append("the pin-freshness job cannot file the drift issue (permissions: issues: write)")
    if str(perms.get("contents", "")).lower() != "read":
        problems.append("the pin-freshness job does not name its contents scope")
    steps = job.get("steps") or []
    pin_steps = [s for s in steps if "hermes-pin-freshness" in str(s.get("run", ""))]
    if len(pin_steps) != 1:
        problems.append(f"the pin-freshness job runs the target {len(pin_steps)} times, expected exactly 1")
    for s in steps:
        run = str(s.get("run", ""))
        if "hermes_pin_freshness" in run and "make hermes-pin-freshness" not in run:
            problems.append(f"step {s.get('name')!r} reaches the script without make")
    for s in pin_steps:
        env = s.get("env") or {}
        if "github.token" not in str(env.get("GH_TOKEN", "")):
            problems.append(f"step {s.get('name')!r} does not file with the default token")
        if "FIXBOT_DISPATCH_TOKEN" in str(env):
            problems.append(f"step {s.get('name')!r} reaches the owner PAT")
    # The cadence home is decided (issue #1093): the dispatch-only sweep may not re-adopt it.
    queued = yaml.safe_load(queued_text)
    for name, j in (queued.get("jobs") or {}).items():
        for s in j.get("steps") or []:
            if "hermes-pin-freshness" in str(s.get("run", "")):
                problems.append(f"queued-alarm.yml job {name!r} still runs the step the owner moved "
                                "to the scheduled pipeline")
    return problems


def test_the_scheduled_pipeline_calls_the_target_and_a_makeless_step_is_refused() -> None:
    print("\nwiring: refresh-bot.yml (the one scheduled pipeline, rule 6t) calls "
          "`make hermes-pin-freshness` (issue #1093); a missing step, an ungated job, a job that "
          "cannot file the issue, a cadence creeping back into the dispatch-only sweep, or a "
          "script-past-the-Makefile step is REFUSED (rules 6j/6m)")
    refresh = (ROOT / ".github" / "workflows" / "refresh-bot.yml").read_text(encoding="utf-8")
    queued = QUEUE_WF.read_text(encoding="utf-8")
    problems = _pin_problems(refresh, queued)
    check("refresh-bot.yml carries the make-wired pin-freshness job", problems == [], problems)
    # The guard must be able to fail: the same scan RED on a step that skips `make`…
    makeless = refresh.replace("run: make hermes-pin-freshness REPO=",
                               "run: python3 scripts/hermes_pin_freshness.py --repo ")
    planted = _pin_problems(makeless, queued)
    check("a step reaching the script without make is REFUSED", bool(planted), planted)
    # …RED on a pipeline that dropped the job entirely…
    dropped = re.sub(r"  pin-freshness:\n.*?repository \}\}\"\n\n", "", refresh, flags=re.S)
    planted = _pin_problems(dropped, queued)
    check("a scheduled pipeline without the job is REFUSED",
          bool(planted) and "no pin-freshness job" in " ".join(planted), planted)
    # …RED when the job skips the guard…
    ungated = refresh.replace("  pin-freshness:\n    needs: guard", "  pin-freshness:")
    planted = _pin_problems(ungated, queued)
    check("a pin-freshness job that skips the guard is REFUSED",
          bool(planted) and "does not need the guard" in " ".join(planted), planted)
    # …RED when it cannot file the issue it exists to file…
    unfileable = refresh.replace("    permissions:\n      contents: read\n      issues: write\n",
                                 "    permissions:\n      contents: read\n")
    planted = _pin_problems(unfileable, queued)
    check("a pin-freshness job that cannot write the issue is REFUSED",
          bool(planted) and "cannot file the drift issue" in " ".join(planted), planted)
    # …and RED when the cadence creeps back into the dispatch-only sweep (issue #1093).
    crept = queued.replace(
        "      - name: Fail loudly when master's branch protection is missing or weakened",
        "      - name: Fail loudly when the Hermes agent pin lags (issue #1091)\n"
        "        env:\n          GH_TOKEN: ${{ github.token }}\n"
        "        run: make hermes-pin-freshness REPO=\"${{ github.repository }}\"\n"
        "      - name: Fail loudly when master's branch protection is missing or weakened")
    planted = _pin_problems(refresh, crept)
    check("the step re-adopted by the dispatch-only sweep is REFUSED",
          bool(planted) and "moved to the scheduled pipeline" in " ".join(planted), planted)
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


def test_the_channel_repo_is_derived_from_the_makefile_pin_block() -> None:
    print("\nchannel: the repo is READ from the Makefile install-pin block (issue #1094) — "
          "the script carries no literal, a missing pin is a loud refusal, and a different "
          "pin value changes the endpoint queried")
    # 1. The script names the channel repo NOWHERE; the Makefile is the only spelling.
    src = SCRIPT.read_text(encoding="utf-8")
    check("the script carries no channel-repo literal",
          "NousResearch/hermes-agent" not in src, "a baked channel spelling remains")
    mk = MAKEFILE.read_text(encoding="utf-8")
    check("the repository Makefile pins HERMES_CHANNEL_REPO exactly once",
          mk.count("HERMES_CHANNEL_REPO ?=") == 1, f"count={mk.count('HERMES_CHANNEL_REPO ?=')}")
    check("no other script spells the channel repo",
          [p.name for p in (ROOT / "scripts").glob("*.py")
           if "NousResearch/hermes-agent" in p.read_text(encoding="utf-8")] == [], "")
    # 2. A planted Makefile WITHOUT the pin refuses loudly, before the channel is consulted.
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, {"tag_name": PLANT_CHANNEL_NEWER})
        (tmp / "Makefile").write_text("# planted Makefile with no channel pin\n"
                                      "HERMES_VERSION ?= 0.10.0\n")
        proc = run_check(env, tmp)
        check("exit 2 naming the missing pin",
              proc.returncode == 2 and "HERMES_CHANNEL_REPO" in proc.stderr,
              f"rc={proc.returncode}\n{proc.stderr}")
        check("the channel was NEVER consulted", "api" not in gh_calls(tmp), gh_calls(tmp))
        check("nothing was filed", len(filed_issues(tmp)) == 0, "")
    # 3. The recipe passes the knob explicitly: `--channel-repo` is forwarded verbatim,
    #    proof the Makefile's value — not a baked default — reaches `gh api`.
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, {"tag_name": PLANT_PIN})
        proc = run_check(env, None, "--channel-repo", "octo/moved-channel")
        check("the recipe shape passes the knob",
              '--channel-repo "$(HERMES_CHANNEL_REPO)"' in MAKEFILE.read_text(encoding="utf-8"),
              "hermes-pin-freshness recipe does not expand the knob")
        check("the gh api call names the MOVED channel",
              "repos/octo/moved-channel/releases/latest" in gh_calls(tmp), gh_calls(tmp))
        check("a channel the stub does not serve is UNREADABLE (exit 2), never OK",
              proc.returncode == 2 and "OK" not in proc.stdout,
              f"rc={proc.returncode}\n{proc.stdout}")


def run_record(env: dict, to: Path, *extra: str) -> subprocess.CompletedProcess:
    """Drive the recorder (issue #1163): `--record TO --channel-repo <Makefile pin>`."""
    argv = [sys.executable, str(SCRIPT), "--record", str(to),
            "--channel-repo", PLANT_CHANNEL_REPO]
    return subprocess.run(argv + list(extra), capture_output=True, text=True, timeout=120, env=env)


def test_the_recorder_writes_the_live_payload_through_the_one_seam() -> None:
    print("\nrecord: `make hermes-pin-channel-record` writes the payload the ONE seam reads")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        payload = {"tag_name": "v0.11.0", "published_at": "2026-11-20T00:34:38Z",
                   "name": "Hermes Agent"}
        env = make_scene(tmp, payload)
        out = tmp / "recorded.json"
        proc = run_record(env, out)
        check("exit 0", proc.returncode == 0, proc.stderr)
        check("stdout names the written tag and published_at",
              "tag=v0.11.0" in proc.stdout and "published_at=2026-11-20T00:34:38Z" in proc.stdout,
              proc.stdout)
        written = json.loads(out.read_text())
        check("the written payload carries the channel's tag_name",
              written.get("tag_name") == "v0.11.0", out.read_text()[:120])
        check("the written payload carries the channel's published_at",
              written.get("published_at") == "2026-11-20T00:34:38Z", out.read_text()[:120])
        check("the bytes written are EXACTLY what gh served — never an authored document",
              out.read_text() == json.dumps(payload) + "\n", out.read_text()[:160])
        check("the gh api call names the channel the Makefile pin derives",
              f"repos/{PLANT_CHANNEL_REPO}/releases/latest" in gh_calls(tmp), gh_calls(tmp))
        # The seam is the SAME one the freshness check reads: a payload the check would
        # refuse (no tag_name) must be refused by the recorder too.
        env2 = make_scene(tmp, {"name": "no tag here"})
        proc2 = run_record(env2, out)
        check("a payload with no tag_name is refused (the ONE seam), nothing written",
              proc2.returncode == 2 and "no `tag_name`" in proc2.stderr
              and json.loads(out.read_text()).get("tag_name") == "v0.11.0", proc2.stderr)


def test_a_failed_read_leaves_the_old_fixture_byte_identical() -> None:
    print("\nrecord-failure: no gh / no network -> exit 2 BEFORE any write, the old fixture untouched")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        env = make_scene(tmp, None)  # the stub refuses `gh api` — the unreadable-channel state
        out = tmp / "recorded.json"
        out.write_text('{"tag_name":"v0.10.0"}\n')
        before = out.read_bytes()
        proc = run_record(env, out)
        check("exit 2", proc.returncode == 2, f"rc={proc.returncode}")
        check("stderr says the read failed and that nothing was written",
              "could not be read" in proc.stderr and "nothing written" in proc.stderr, proc.stderr)
        check("the old fixture is byte-identical", out.read_bytes() == before, "")
        check("no .tmp litter is left behind", not (tmp / "recorded.json.tmp").exists(), "")
        # A missing channel PIN in the Makefile is refused before gh is consulted.
        (tmp / "Makefile").write_text("HERMES_VERSION ?= 0.10.0\n")
        proc2 = subprocess.run(
            [sys.executable, str(SCRIPT), "--record", str(out), "--makefile", str(tmp / "Makefile")],
            capture_output=True, text=True, timeout=120, env=env)
        check("a Makefile with no channel pin refuses loudly (exit 2), still nothing written",
              proc2.returncode == 2 and "HERMES_CHANNEL_REPO" in proc2.stderr
              and out.read_bytes() == before, proc2.stderr)


def test_the_recorder_is_wired_into_the_refresh_pipeline_and_the_makefile() -> None:
    print("\nrecord-wiring: the target is Makefile-only and a CI job runs it (rule 6m, issue #1163)")
    mk = MAKEFILE.read_text(encoding="utf-8")
    check("the Makefile defines the public target and the internal recipe",
          "\nhermes-pin-channel-record:" in mk and "_hermes-pin-channel-record:" in mk, "")
    check("the internal recipe is the only thing naming --record",
          "_hermes-pin-channel-record:\n\tpython3 scripts/hermes_pin_freshness.py --record" in mk, "")
    r = subprocess.run(["make", "-n", "hermes-pin-channel-record",
                        "TO=tests/fixtures/hermes_releases_latest.json"], cwd=ROOT,
                       capture_output=True, text=True, timeout=60)
    check("make -n runs the script with --record and the Makefile's channel pin",
          r.returncode == 0
          and '--record "tests/fixtures/hermes_releases_latest.json"' in r.stdout
          and '--channel-repo "' in r.stdout and '--channel-repo ""' not in r.stdout, r.stdout)
    check("make refuses a missing TO before any recipe runs", subprocess.run(
        ["make", "hermes-pin-channel-record"], cwd=ROOT,
        capture_output=True, text=True, timeout=60).returncode != 0, "")
    refresh = (ROOT / ".github" / "workflows" / "refresh-bot.yml").read_text(encoding="utf-8")
    check("refresh-bot.yml runs make hermes-pin-channel-record",
          "make hermes-pin-channel-record TO=tests/fixtures/hermes_releases_latest.json" in refresh,
          "")
    check("no workflow reaches the recorder past the Makefile",
          [wf.name for wf in sorted((ROOT / ".github" / "workflows").glob("*.yml"))
           if "hermes_pin_freshness.py" in wf.read_text(encoding="utf-8")] == [], "")
    # The guard must be able to fail: a pipeline that dropped the recorder step is refused.
    dropped = refresh.replace(
        "          make hermes-pin-channel-record TO=tests/fixtures/hermes_releases_latest.json\n", "")
    check("a refresh pipeline without the recorder step is REFUSED",
          "make hermes-pin-channel-record TO=tests/fixtures/hermes_releases_latest.json"
          not in dropped and dropped != refresh, "")
    # The refresh PR's commit must carry the fixture, or the recorded payload never lands.
    add_line = [ln for ln in refresh.splitlines() if ln.strip().startswith("git add ")][0]
    check("the refresh PR's git add carries the recorded payload fixture",
          "tests/fixtures/hermes_releases_latest.json" in add_line, add_line)


def test_the_aggregate_job_gives_the_pin_recorder_a_token() -> None:
    """Issue #1747: `gh api` in Actions refuses without GH_TOKEN (rc=4).

    The channel recorder runs inside the aggregate job of refresh-bot.yml. A public
    read still needs a token in Actions; the default github.token is enough and the
    owner PAT is deliberately not used for this read (AGENTS.md rule 6b).
    """
    refresh = (ROOT / ".github" / "workflows" / "refresh-bot.yml").read_text(encoding="utf-8")
    lines = refresh.splitlines()
    step = next(i for i, line in enumerate(lines)
                if "make hermes-pin-channel-record TO=" in line)
    headers = [i for i, line in enumerate(lines[:step]) if re.match(r"^  [A-Za-z0-9_-]+:$", line)]
    job = max(headers)
    block = "\n".join(lines[job:step])
    check("the recorder lives in the aggregate job", lines[job].strip() == "aggregate:",
          lines[job])
    check("the aggregate job gives the pin recorder GH_TOKEN from github.token",
          "GH_TOKEN: ${{ github.token }}" in block, block[-300:])
    check("the recorder never borrows the owner PAT for a public read",
          "GH_TOKEN: ${{ secrets.FIXBOT_DISPATCH_TOKEN }}" not in block, block[-300:])


def main() -> int:
    print("hermes pin freshness: the pinned agent vs the upstream channel (issue #1091)")
    test_channel_equal_to_pin_prints_ok_and_exits_green()
    test_channel_newer_goes_red_files_one_tech_debt_issue_naming_the_remedy()
    test_the_drift_filing_is_marker_deduped_across_re_runs()
    test_pin_ahead_of_channel_is_reported_not_red()
    test_unreadable_channel_is_a_loud_exit_two_never_a_clean()
    test_pin_disagreement_between_makefile_and_dockerfile_refuses_before_the_channel_is_read()
    test_recorded_channel_payload_is_compared_against_the_real_pins()
    test_the_shipped_pins_and_the_recorded_payload_name_one_release()
    test_the_channel_repo_is_derived_from_the_makefile_pin_block()
    test_the_scheduled_pipeline_calls_the_target_and_a_makeless_step_is_refused()
    test_the_drift_marker_is_registered_in_bot_markers()
    test_the_recorder_writes_the_live_payload_through_the_one_seam()
    test_a_failed_read_leaves_the_old_fixture_byte_identical()
    test_the_recorder_is_wired_into_the_refresh_pipeline_and_the_makefile()
    test_the_aggregate_job_gives_the_pin_recorder_a_token()
    print(f"\nPASSED {_checks_passed} | FAILED {_checks_failed}")
    return 0 if _checks_failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
