#!/usr/bin/env python3
"""tests/test_agent_profile_provision.py — issue #1142: the fleet chain reaches the profile home that RUNS a lane.

Issue #1140 built the rendering half: `agents/model_chain.json` is the ONE source and
`make agent-profile-model-render` writes `agents/tll-<lane>/config.yaml` from it, and
`make agent-model-chain-check` refuses a fleet config that does not match. Issue #1142 measured the
missing half: NO seam copied that rendered config into the Hermes profile home a lane actually runs.
On the machine that runs the lanes, `~/.hermes/profiles/tll-architect/config.yaml` said
`provider: strata`, `default: qwen3.8-flash-next-q2_0`, `base_url: http://127.0.0.1:8080/v1`, all
seven `tll-*` homes carried the same shape, and `printenv | grep -c NOUS_API_KEY` printed `0` — the
gate enforced the chain inside the repository while the live profiles ran a different config.
"Green in the repo, wrong on the machine" is the defect this suite locks.

The guards run the REAL `scripts/agent_profile_provision.py` end to end against a scratch tree and a
scratch profile home, with the credential supplied ONLY as a named environment variable (rule 6m: no
stand-in replaces the seam; the only external system here is the filesystem, which is real):

  1. a lane's rendered config COPIES into `<profiles-home>/tll-<lane>/config.yaml`, byte-identical
     to what the chain renders, and the config that was there is KEPT as a `config.yaml.bak-<UTC>`
     backup (rule 3b — a stored file is never destroyed);
  2. when a `key_env` the chain names is ABSENT the seam REFUSES (exit 2), names the VARIABLE, and
     writes NOTHING into the profile home — a keyless lane would otherwise fail inside a model call
     instead of at a gate (rule 3e, `scripts/require_env.py`, issue #357);
  3. a lane config that has DRIFTED from the chain is refused, not copied: a live home must never
     receive what `make agent-model-chain-check` would red;
  4. no credential VALUE is ever read or printed — the seam names variables only;
  5. writing a profile home is never a default (no `--lane`/`--all` is a refusal) and an unknown
     lane is a refusal that names the fleet;
  6. the target is wired to the Makefile AND to a pipeline job (rules 6d/6m).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import agent_model_chain as AMC  # noqa: E402  (the ONE chain renderer, rule 6d)
from wiring import wired  # noqa: E402  (a test must be discovered by `make test`, rule 6d)

SCRIPT = ROOT / "scripts" / "agent_profile_provision.py"
CHAIN = ROOT / "agents" / "model_chain.json"

# The credential the shipped chain names (agents/model_chain.json: "key_env": "NOUS_API_KEY").
KEY_NAME = json.loads(CHAIN.read_text(encoding="utf-8"))["key_env"]
# A placeholder that is NOT a credential shape: the seam must never print it, and `make secret-scan`
# must never see it (it lives only in a subprocess environment, never in a tracked file).
PLACEHOLDER = "present-not-measured"

# A line that ASSIGNS a credential field (same grammar as tests/test_agent_model_chain.py: prose
# that merely MENTIONS a credential is not a finding).
CREDENTIAL_FIELD_RE = re.compile(r'(?im)^\s*["\']?(api_key|apikey|authorization|password|token)["\']?\s*[:=]')

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


# ---------------------------------------------------------------- fixtures


def _scratch(td: Path) -> Path:
    """A fresh tree carrying the seam, its ONE chain source and two rendered fleet lanes."""
    root = td
    (root / "scripts").mkdir(parents=True)
    (root / "agents").mkdir(parents=True)
    shutil.copy(ROOT / "Makefile", root / "Makefile")
    for name in ("agent_model_chain.py", "require_env.py", "agent_profile_provision.py"):
        shutil.copy(ROOT / "scripts" / name, root / "scripts" / name)
    shutil.copy(CHAIN, root / "agents" / "model_chain.json")
    for lane in ("tll-tester", "tll-reviewer"):
        d = root / "agents" / lane
        d.mkdir(parents=True)
        (d / "SOUL.md").write_text("# lane\n", encoding="utf-8")
    render = subprocess.run([sys.executable, str(root / "scripts" / "agent_model_chain.py"),
                             "--root", str(root), "--write"], capture_output=True, text=True)
    assert render.returncode == 0, render.stderr
    return root


def run_provision(*args: str, root: Path, key: str | None = PLACEHOLDER) -> subprocess.CompletedProcess:
    """Run the REAL seam; the credential arrives ONLY as a named variable in its environment."""
    env = dict(os.environ)
    env.pop(KEY_NAME, None)
    if key is not None:
        env[KEY_NAME] = key
    cmd = [sys.executable, str(root / "scripts" / "agent_profile_provision.py"),
           "--root", str(root), *args]
    return subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, env=env)


def lane_config(root: Path, lane: str) -> str:
    return (root / "agents" / lane / AMC.CONFIG_REL).read_text(encoding="utf-8")


# ------------------------------------------------------------------ guards


def test_a_lane_config_copies_into_the_profile_home_and_the_prior_file_is_kept():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        lane_home = home / "tll-tester"
        lane_home.mkdir(parents=True)
        # The measured live-home shape (issue #1142): a config the chain never renders.
        stale = ("model:\n  provider: strata\n  default: qwen3.8-flash-next-q2_0\n"
                 "  base_url: http://127.0.0.1:8080/v1\n")
        (lane_home / AMC.CONFIG_REL).write_text(stale, encoding="utf-8")

        proc = run_provision("--lane", "tll-tester", "--profiles-home", str(home), root=root)
        out = proc.stdout + proc.stderr
        check("provisioning a named lane exits green", proc.returncode == 0, out[-200:])
        dest = lane_home / AMC.CONFIG_REL
        check("the profile home's config is BYTE-IDENTICAL to what the chain renders",
              dest.read_text(encoding="utf-8") == lane_config(root, "tll-tester"), "")
        check("the chain's free-primary config replaced the measured strata/local shape in the live home",
              "provider: custom" in dest.read_text(encoding="utf-8")
              and "provider: strata" not in dest.read_text(encoding="utf-8")
              and "qwen3.8-flash-next-q2_0" not in dest.read_text(encoding="utf-8"),
              dest.read_text()[:200])
        backups = sorted(p.name for p in lane_home.iterdir()
                         if p.name.startswith(f"{AMC.CONFIG_REL}{'.bak-'}"))
        check("the prior config is KEPT as a config.yaml.bak-<UTC> backup (rule 3b, never destroyed)",
              len(backups) == 1 and (lane_home / backups[0]).read_text(encoding="utf-8") == stale,
              str(backups))
        check("the seam names the lane, the destination and the backup it kept",
              f"lane=tll-tester" in out and str(dest) in out and backups[0] in out, out[-200:])
        check("an untouched sibling lane home is NOT written",
              not (home / "tll-reviewer").exists(), "")


def test_provisioning_refuses_without_the_credential_the_chain_names_and_writes_nothing():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        home.mkdir(parents=True)

        proc = run_provision("--all", "--profiles-home", str(home), root=root, key=None)
        out = proc.stdout + proc.stderr
        check("absent credential -> exit 2 (a loud refusal, never a degraded lane)",
              proc.returncode == 2, f"rc={proc.returncode} {out[-200:]}")
        check("the refusal NAMES the variable the chain requires", KEY_NAME in out, out[-300:])
        check("the refusal says NO credential VALUE was read",
              "value" in out.lower(), out[-300:])
        check("NOTHING was written into the profile home",
              list(home.iterdir()) == [], str(list(home.iterdir())))
        check("the placeholder value never reaches stdout or stderr",
              PLACEHOLDER not in out, "")


def test_a_lane_config_that_drifted_from_the_chain_is_refused_not_copied():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        home.mkdir(parents=True)
        # The chain-drift shape make agent-model-chain-check refuses (#1140): a hand-edited paid
        # model replacing the free primary, in the repository copy that would be provisioned.
        cfg = root / "agents" / "tll-tester" / AMC.CONFIG_REL
        text = cfg.read_text(encoding="utf-8")
        drifted = text.replace("default: meituan/longcat-2.5:free", "default: some-paid-model")
        assert drifted != text, "the fixture edit must actually change the lane config"
        cfg.write_text(drifted, encoding="utf-8")

        proc = run_provision("--all", "--profiles-home", str(home), root=root)
        out = proc.stdout + proc.stderr
        check("a drifted lane config is refused (exit 2), never copied into a live home",
              proc.returncode == 2, f"rc={proc.returncode} {out[-200:]}")
        check("the refusal names the lane it refused", "tll-tester" in out, out[-300:])
        check("the profile home stayed empty — a config the gate would red never lands there",
            list(home.iterdir()) == [], str(list(home.iterdir())))


def test_the_provisioned_config_carries_key_env_NAMES_and_never_a_credential_value():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        proc = run_provision("--all", "--profiles-home", str(home), root=root)
        check("both lanes provision", proc.returncode == 0, proc.stderr[-200:])
        for lane in ("tll-tester", "tll-reviewer"):
            text = (home / lane / AMC.CONFIG_REL).read_text(encoding="utf-8")
            check(f"{lane}: the file names the credential by NAME (key_env)",
                  f"key_env: {KEY_NAME}" in text, text[:200])
            check(f"{lane}: no credential FIELD is assigned anywhere in it (rule 3e)",
                  not CREDENTIAL_FIELD_RE.search(text), text[:200])
        check("no credential VALUE appears in any written file",
              PLACEHOLDER not in "\n".join(
                  p.read_text(encoding="utf-8") for p in home.rglob("*") if p.is_file()), "")
        check("the summary prints the credential NAMES it required",
              f"NAMES required: {KEY_NAME}" in proc.stdout, proc.stdout[-300:])


def test_writing_a_profile_home_is_never_the_default_and_an_unknown_lane_is_refused():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        home.mkdir(parents=True)

        none = run_provision("--profiles-home", str(home), root=root)
        check("no --lane and no --all is a REFUSAL (writing a live home is never a default)",
              none.returncode == 2, f"rc={none.returncode}")
        check("the refusal names both accepted forms",
              "LANE=" in none.stderr and "ALL=1" in none.stderr, none.stderr[-300:])
        check("nothing was written", list(home.iterdir()) == [], "")

        bogus = run_provision("--lane", "tll-nope", "--profiles-home", str(home), root=root)
        check("an unknown lane is refused (exit 2)", bogus.returncode == 2, f"rc={bogus.returncode}")
        check("the refusal names the unknown lane and the real fleet",
              "tll-nope" in bogus.stderr and "tll-tester" in bogus.stderr, bogus.stderr[-300:])
        check("an unknown lane writes nothing", list(home.iterdir()) == [], "")

        dry = run_provision("--all", "--dry-run", "--profiles-home", str(home), root=root)
        check("--dry-run proves the chain, the credential and every config, writing nothing",
              dry.returncode == 0 and "DRY RUN" in dry.stdout and list(home.iterdir()) == [],
              dry.stdout[-200:] + dry.stderr[-200:])


def test_all_provisions_every_fleet_lane_in_the_tree():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        proc = run_provision("--all", "--profiles-home", str(home), root=root)
        check("--all provisions every fleet lane the tree carries",
              proc.returncode == 0 and all(
                  (home / lane / AMC.CONFIG_REL).read_text(encoding="utf-8") == lane_config(root, lane)
                  for lane in ("tll-tester", "tll-reviewer")), proc.stderr[-200:])
        check("the lanes come from the TREE (agents/tll-*/), never a hand-kept list (rule 6d)",
              f"provisioned {len(AMC.fleet_lanes(root))} lane" in proc.stdout,
              proc.stdout[-300:])


def test_the_target_is_wired_to_the_makefile_and_a_pipeline_job():
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("the Makefile defines the internal recipe (the seam, not a second copy)",
          "_agent-profile-provision:\n\tpython3 scripts/agent_profile_provision.py" in mk, "")
    check("the public target delegates to the internal recipe",
          "agent-profile-provision: ##" in mk
          and "_agent-profile-provision" in mk.split("agent-profile-provision: ##", 1)[1][:400], "")
    check("the target takes the lane and profiles-home the issue names (LANE= / ALL= / PROFILES_HOME=)",
          "LANE ?=" in mk and "ALL ?=" in mk and "PROFILES_HOME ?=" in mk
          and "--profiles-home $(PROFILES_HOME)" in mk, "")
    qa = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text(encoding="utf-8")
    check("qa-validate RUNS the seam (rule 6m: a target CI runs, never only a human)",
          "make agent-profile-provision" in qa, "")
    check("the CI invocation targets a runner temp home, never a real profile home",
          'PROFILES_HOME="$RUNNER_TEMP' in qa, "")
    check("no workflow reaches into scripts/agent_profile_provision.py past the Makefile (rule 6m)",
          not any("agent_profile_provision" in (ROOT / ".github" / "workflows" / p.name)
                  .read_text(encoding="utf-8")
                  for p in (ROOT / ".github" / "workflows").iterdir() if p.suffix == ".yml"), "")
    check("the seam has a row in the ARCHITECTURE script table (rule 6h)",
          "scripts/agent_profile_provision.py" in (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8"), "")
    check("this suite is discovered by `make test`", wired(__file__), "")


def main() -> int:
    print(f"agent_profile_provision (issue #1142): credential NAME required by the chain: {KEY_NAME}")
    test_a_lane_config_copies_into_the_profile_home_and_the_prior_file_is_kept()
    test_provisioning_refuses_without_the_credential_the_chain_names_and_writes_nothing()
    test_a_lane_config_that_drifted_from_the_chain_is_refused_not_copied()
    test_the_provisioned_config_carries_key_env_NAMES_and_never_a_credential_value()
    test_writing_a_profile_home_is_never_the_default_and_an_unknown_lane_is_refused()
    test_all_provisions_every_fleet_lane_in_the_tree()
    test_the_target_is_wired_to_the_makefile_and_a_pipeline_job()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
