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

# The credential the chain names, when it names one. Since issue #1203 the shipped chain runs on
# the `nous` provider (the Portal session) and names NO key_env; `NOUS_API_KEY` stays as the name
# a scratch chain can declare to prove the refusal path below.
KEY_NAME = json.loads(CHAIN.read_text(encoding="utf-8")).get("key_env") or "NOUS_API_KEY"
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
        check("the chain's `nous` config replaced the measured strata-first shape in the live home",
              "provider: nous" in dest.read_text(encoding="utf-8")
              and f"default: {AMC.read_chain(root)[0].primary.model}" in dest.read_text(encoding="utf-8")
              and "qwen3.8-flash-next-q2_0" not in dest.read_text(encoding="utf-8"),
              dest.read_text()[:200])
        check("the local tier survives ONLY as the credential-less local_fallback step (issue #1192)",
              "model: qwen3.8-flash-next-iq3_xxs" in dest.read_text(encoding="utf-8")
              and "default: qwen3.8-flash-next-iq3_xxs" not in dest.read_text(encoding="utf-8"),
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
        # The shipped `nous` chain names NO key_env (the Portal session authenticates it, issue
        # #1203), so the refusal path is proven on a scratch chain that DOES declare one — the
        # container legs' `custom` shape.
        chain_path = root / "agents" / "model_chain.json"
        data = json.loads(chain_path.read_text(encoding="utf-8"))
        data["provider"] = "custom"
        data["base_url"] = "https://inference-api.nousresearch.com/v1"
        data["key_env"] = KEY_NAME
        chain_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        render = subprocess.run([sys.executable, str(root / "scripts" / "agent_model_chain.py"),
                                 "--root", str(root), "--write"], capture_output=True, text=True)
        assert render.returncode == 0, render.stderr

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


def test_the_nous_chain_provisions_with_no_credential_at_all():
    """Issue #1203: the shipped chain authenticates through the Nous Portal session and names no
    `key_env`, so the pre-flight has nothing to check and provisioning is green with no key."""
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        proc = run_provision("--all", "--profiles-home", str(home), root=root, key=None)
        out = proc.stdout + proc.stderr
        check("a `nous` chain with no key_env provisions green (nothing to pre-flight)",
              proc.returncode == 0, f"rc={proc.returncode} {out[-300:]}")
        check("every lane config landed",
              all((home / lane / AMC.CONFIG_REL).is_file()
                  for lane in ("tll-tester", "tll-reviewer")), str(list(home.iterdir())))


def test_a_lane_config_that_drifted_from_the_chain_is_refused_not_copied():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        home.mkdir(parents=True)
        # The chain-drift shape make agent-model-chain-check refuses (#1140): a hand-edited paid
        # model replacing the free primary, in the repository copy that would be provisioned.
        cfg = root / "agents" / "tll-tester" / AMC.CONFIG_REL
        text = cfg.read_text(encoding="utf-8")
        primary = AMC.read_chain(root)[0].primary.model
        drifted = text.replace(f"default: {primary}", "default: some-paid-model")
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
            check(f"{lane}: no credential FIELD is assigned anywhere in it (rule 3e)",
                  not CREDENTIAL_FIELD_RE.search(text), text[:200])
            check(f"{lane}: any key_env it names is an environment NAME, never a value",
                  all(n == KEY_NAME for n in re.findall(r"key_env:\s*(\S+)", text)), text[:200])
        check("no credential VALUE appears in any written file",
              PLACEHOLDER not in "\n".join(
                  p.read_text(encoding="utf-8") for p in home.rglob("*") if p.is_file()), "")
        check("the summary reports the credential NAMES it required (none for a `nous` chain)",
              "credential NAMES required:" in proc.stdout and PLACEHOLDER not in proc.stdout,
              proc.stdout[-300:])


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


def test_a_non_lane_profile_merges_only_the_owned_blocks_and_keeps_every_other_byte():
    """Issue #1192: PROFILE= merges model/model_aliases/fallback_providers; the rest is untouched."""
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        pdir = home / "developer"
        pdir.mkdir(parents=True)
        kept_tail = ("terminal:\n  backend: local\n  cwd: /tmp\n"
                     "auxiliary:\n  vision:\n    provider: auto\n")
        stale = ("# a hand-written home config\nmodel:\n  provider: strata\n"
                 "  default: qwen3.8-flash-next-q2_0\n  base_url: http://127.0.0.1:8080/v1\n"
                 "custom_providers:\n  - name: strata\n    base_url: http://127.0.0.1:8080/v1\n"
                 + kept_tail)
        (pdir / AMC.CONFIG_REL).write_text(stale, encoding="utf-8")
        rendered = AMC.render_text(AMC.read_chain(root)[0])

        proc = run_provision("--profile", "developer", "--profiles-home", str(home), root=root)
        out = proc.stdout + proc.stderr
        check("merging a named non-lane profile exits green", proc.returncode == 0, out[-300:])
        merged = (pdir / AMC.CONFIG_REL).read_text(encoding="utf-8")
        check("the stale strata-first model block is gone; the free primary is the default",
              f"default: {AMC.read_chain(root)[0].primary.model}" in merged
              and "qwen3.8-flash-next-q2_0" not in merged, merged[:200])
        check("every non-owned top-level block survives BYTE-FOR-BYTE (custom_providers, terminal, auxiliary)",
              kept_tail in merged and "custom_providers:\n  - name: strata\n    base_url: http://127.0.0.1:8080/v1\n" in merged
              and "# a hand-written home config\n" in merged, merged[-300:])
        for block in ("model", "model_aliases", "fallback_providers"):
            rchunk = next(c for n, c in __import__("agent_profile_provision")._top_blocks(rendered) if n == block)
            mchunk = next((c for n, c in __import__("agent_profile_provision")._top_blocks(merged) if n == block), None)
            check(f"the merged `{block}:` block IS the rendered chain's block", mchunk == rchunk, block)
        backups = sorted(p.name for p in pdir.iterdir() if p.name.startswith(f"{AMC.CONFIG_REL}.bak-"))
        check("the prior home config is KEPT as a backup (rule 3b)",
              len(backups) == 1 and (pdir / backups[0]).read_text(encoding="utf-8") == stale, str(backups))
        check("the seam names the profile and the destination", "profile=developer" in out and str(pdir) in out,
              out[-200:])

        again = run_provision("--profile", "developer", "--profiles-home", str(home), root=root)
        check("the merge is IDEMPOTENT (a second provision changes no byte)",
              again.returncode == 0
              and (pdir / AMC.CONFIG_REL).read_text(encoding="utf-8") == merged, again.stderr[-200:])

        # The measured live-home shape (architect, 2026-11-21): a NON-owned block immediately
        # before the first owned one, and no model_aliases block at all. A header inserted
        # BETWEEN blocks would ride with the previous block's bytes and change it — refused.
        pdir2 = home / "reviewer"
        pdir2.mkdir(parents=True)
        stale2 = ("display:\n  turn_completion_explainer: true\n"
                  "fallback_providers:\n  - provider: strata\n    model: old-local\n"
                  "model:\n  provider: strata\n  default: qwen3.8-flash-next-q2_0\n"
                  "terminal:\n  backend: local\n")
        (pdir2 / AMC.CONFIG_REL).write_text(stale2, encoding="utf-8")
        proc2 = run_provision("--profile", "reviewer", "--profiles-home", str(home), root=root)
        merged2 = (pdir2 / AMC.CONFIG_REL).read_text(encoding="utf-8")
        names2 = [n for n, _ in __import__("agent_profile_provision")._top_blocks(merged2)]
        check("a non-owned block directly before the first owned block survives byte-for-byte",
              proc2.returncode == 0
              and "display:\n  turn_completion_explainer: true\n" in merged2
              and "terminal:\n  backend: local\n" in merged2
              and names2 == ["", "display", "fallback_providers", "model", "terminal", "model_aliases"],
              proc2.stderr[-200:] + str(names2))


def test_default_names_the_hermes_homes_own_config_and_a_lane_via_profile_is_refused():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        home.mkdir(parents=True)
        (home.parent / AMC.CONFIG_REL).write_text("model:\n  provider: strata\n  default: old\n",
                                                  encoding="utf-8")
        proc = run_provision("--profile", "default", "--profiles-home", str(home), root=root)
        out = proc.stdout + proc.stderr
        check("--profile default writes the Hermes home's OWN config.yaml (beside the profiles root)",
              proc.returncode == 0
              and f"default: {AMC.read_chain(root)[0].primary.model}" in (home.parent / AMC.CONFIG_REL).read_text(encoding="utf-8"),
              out[-300:])
        check("a prior default config is kept as a backup",
              any(p.name.startswith(f"{AMC.CONFIG_REL}.bak-") for p in home.parent.iterdir()), "")

        lane = run_provision("--profile", "tll-tester", "--profiles-home", str(home), root=root)
        check("a fleet lane named via PROFILE= is refused (lanes are whole copies via LANE=)",
              lane.returncode == 2 and "LANE=" in lane.stderr, lane.stderr[-200:])
        missing = run_provision("--profile", "no-such-home", "--profiles-home", str(home), root=root)
        check("a profile home that does not exist is refused — provisioning never creates a profile",
              missing.returncode == 2 and "does not exist" in missing.stderr, missing.stderr[-200:])
        check("no credential VALUE reaches any written file or the seam's output",
              PLACEHOLDER not in out + lane.stdout + lane.stderr + missing.stdout + missing.stderr, "")


def test_check_names_every_stale_home_writes_nothing_and_needs_no_credential():
    """Issue #1204: the read-only drift report names stale homes loudly — the post-refresh state."""
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        # A stale LANE home (whole copy drifted), a stale MERGE home (one owned block drifted),
        # and a clean merge home.
        (home / "tll-tester").mkdir(parents=True)
        (home / "tll-tester" / AMC.CONFIG_REL).write_text("model:\n  provider: strata\n  default: old\n",
                                                          encoding="utf-8")
        stale_dev = home / "developer"
        stale_dev.mkdir(parents=True)
        (stale_dev / AMC.CONFIG_REL).write_text(
            "model:\n  provider: strata\n  default: qwen3.8-flash-next-q2_0\n"
            "terminal:\n  backend: local\n", encoding="utf-8")
        rendered = AMC.render_text(AMC.read_chain(root)[0])
        # The second scratch lane, CLEAN (a whole copy) — proves a clean lane is not named.
        (home / "tll-reviewer").mkdir(parents=True)
        (home / "tll-reviewer" / AMC.CONFIG_REL).write_text(rendered, encoding="utf-8")
        clean = home / "cleanprofile"
        clean.mkdir(parents=True)
        APP = __import__("agent_profile_provision")
        merged, problems = APP.merge_rendered("terminal:\n  backend: local\n", rendered)
        assert not problems, problems
        (clean / AMC.CONFIG_REL).write_text(merged, encoding="utf-8")

        before = {p: p.read_bytes() for p in home.rglob("*.yaml")}
        proc = run_provision("--check", "--all", "--profile", "developer", "--profile", "cleanprofile",
                             "--profiles-home", str(home), root=root, key=None)
        out = proc.stdout + proc.stderr
        check("drift over stale homes exits 1 (a loud report, never a silent pass)",
              proc.returncode == 1, f"rc={proc.returncode} {out[-300:]}")
        check("the report names the stale LANE and its whole-copy drift",
              "STALE lane=tll-tester" in out, out[-400:])
        check("the report names the stale MERGE home and the drifted owned block",
              "STALE profile=developer" in out and "`model:`" in out, out[-400:])
        check("the clean home is not named as stale", "profile=cleanprofile" not in out, out[-400:])
        check("the report needs NO credential (it runs with the key absent)",
              proc.returncode == 1 and "REFUSED" not in out, out[-300:])
        check("the check writes NOTHING — no file changed, no backup created",
              all(p.read_bytes() == b for p, b in before.items())
              and not list(home.rglob("*.bak-*")), "")
        check("the summary names the remedy (re-provision without CHECK=1)",
              "agent-profile-provision" in out and "CHECK=1" in out, out[-300:])


def test_check_is_green_after_provisioning_and_a_missing_home_is_exit_2():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        prov = run_provision("--all", "--profile", "default", "--profiles-home", str(home), root=root)
        check("provisioning the lanes + default succeeds first", prov.returncode == 0, prov.stderr[-200:])
        proc = run_provision("--check", "--all", "--profile", "default",
                             "--profiles-home", str(home), root=root, key=None)
        out = proc.stdout + proc.stderr
        check("the check is GREEN once every home matches the chain",
              proc.returncode == 0 and "CLEAN" in out, out[-300:])
        missing = run_provision("--check", "--profile", "no-such-home",
                                "--profiles-home", str(home), root=root, key=None)
        check("a missing home in a check is exit 2 UNDECIDABLE, never a clean pass",
              missing.returncode == 2 and "does not exist" in missing.stderr, missing.stderr[-200:])


def test_a_declared_lane_append_survives_a_whole_copy_reprovision():
    """Issue #1618: re-provisioning copies whole bytes, so the #1591 block must be in the render."""
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        lane = "tll-tester"
        block = "# owner-authorized 2026-11-24 (issue #1591)\nsecurity:\n  protected_instruction_files: false\n"
        (root / "agents" / lane / "config.append.yaml").write_text(block, encoding="utf-8")
        assert AMC.render(root) == 0
        home = Path(td) / "profiles"
        (home / lane).mkdir(parents=True)
        proc = run_provision("--lane", lane, "--profiles-home", str(home), root=root)
        out = proc.stdout + proc.stderr
        check("a lane with a declared append provisions green", proc.returncode == 0, out[-200:])
        dest = home / lane / AMC.CONFIG_REL
        check("the #1591 setting survives a whole-copy re-provision", block in dest.read_text(),
              dest.read_text()[-200:])
        check("the installed bytes are exactly the rendered lane config",
              dest.read_text() == lane_config(root, lane), "")
        chk = run_provision("--check", "--lane", lane, "--profiles-home", str(home), root=root)
        check("CHECK mode calls the provisioned home CLEAN",
              chk.returncode == 0 and "CLEAN" in chk.stdout, chk.stdout[-200:] + chk.stderr[-200:])


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
    check("the target takes the non-lane PROFILE= comma list (issue #1192), expanded per name",
          "PROFILE ?=" in mk and "comma := ," in mk
          and "$(foreach p,$(subst $(comma), ,$(PROFILE)),--profile $(p))" in mk, "")
    check("the target takes CHECK=1 for the read-only drift report (issue #1204)",
          "CHECK ?=" in mk and "$(if $(CHECK), --check,)" in mk, "")
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
    test_the_nous_chain_provisions_with_no_credential_at_all()
    test_a_lane_config_that_drifted_from_the_chain_is_refused_not_copied()
    test_the_provisioned_config_carries_key_env_NAMES_and_never_a_credential_value()
    test_writing_a_profile_home_is_never_the_default_and_an_unknown_lane_is_refused()
    test_all_provisions_every_fleet_lane_in_the_tree()
    test_a_non_lane_profile_merges_only_the_owned_blocks_and_keeps_every_other_byte()
    test_default_names_the_hermes_homes_own_config_and_a_lane_via_profile_is_refused()
    test_check_names_every_stale_home_writes_nothing_and_needs_no_credential()
    test_check_is_green_after_provisioning_and_a_missing_home_is_exit_2()
    test_a_declared_lane_append_survives_a_whole_copy_reprovision()
    test_the_target_is_wired_to_the_makefile_and_a_pipeline_job()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
