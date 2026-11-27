#!/usr/bin/env python3
"""Behavioural tests for scripts/agent_model_chain.py and the fleet model chain (issue #1140).

The rule: `agents/model_chain.json` is the ONE source of the model chain every Hermes fleet lane
runs on — the free primary FIRST, the free fallbacks in list order, the pinned paid model LAST —
each lane's Hermes profile config is rendered from it, and `make agent-model-chain-check` refuses
a config that drifted, a chain that lost its shape, a last resort that is not the Makefile's
pinned model/alias, and any credential VALUE (only `key_env` NAMES, rule 3e).

Every test drives the REAL script (and, for one test, the real `make` target) against a planted
scratch tree or against this repository. No stand-in replaces the system under test (rule 6m).

Wired into `make test` (rule 6d).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from wiring import wired  # noqa: E402  (issues #176/#192)
import fleet_chain_fixtures as F  # noqa: E402  (issues #1744/#1745: derive, never freeze)

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "agent_model_chain.py"
CHAIN = ROOT / "agents" / "model_chain.json"
LANES = sorted(d.name for d in (ROOT / "agents").iterdir()
               if d.is_dir() and d.name.startswith("tll-") and (d / "SOUL.md").is_file())

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
    """A fresh tree carrying the ONE source, the seam and two fleet lanes."""
    root = td
    (root / "scripts").mkdir(parents=True)
    (root / "agents").mkdir(parents=True)
    shutil.copy(ROOT / "Makefile", root / "Makefile")
    shutil.copy(SCRIPT, root / "scripts" / "agent_model_chain.py")
    shutil.copy(CHAIN, root / "agents" / "model_chain.json")
    for lane in ("tll-tester", "tll-reviewer"):
        d = root / "agents" / lane
        d.mkdir(parents=True)
        (d / "SOUL.md").write_text("# lane\n", encoding="utf-8")
    run("--write", root=root)
    return root


def run(*args: str, root: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPT), *(a for a in args if a)]
    if root is not None:
        cmd += ["--root", str(root)]
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)


def _chain_json(root: Path) -> dict:
    return json.loads((root / "agents" / "model_chain.json").read_text(encoding="utf-8"))


CREDENTIAL_FIELD_RE = re.compile(r'(?im)^\s*["\']?(api_key|apikey|authorization|password|token)["\']?\s*[:=]')
KEY_ENV_RE = re.compile(r'key_env["\']?\s*[:=]\s*["\']?([A-Za-z0-9_]+)')


def credential_field_lines(text: str) -> list[int]:
    # Lines that ASSIGN a credential field; prose that merely MENTIONS one is not a finding.
    return [text[:m.start()].count(chr(10)) + 1 for m in CREDENTIAL_FIELD_RE.finditer(text)]


def key_env_names(text: str) -> list[str]:
    return [m.group(1) for m in KEY_ENV_RE.finditer(text)]


def _write_chain(root: Path, data: dict) -> None:
    (root / "agents" / "model_chain.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- behaviour


def test_the_shipped_chain_renders_every_lane_config_and_the_gate_is_green():
    """Given this repository, `--check` is green and names every lane it verified."""
    res = run("--check")
    out = res.stdout + res.stderr
    check("the shipped tree passes `--check`", res.returncode == 0, out[-300:])
    check("the OK line counts every fleet lane", f"{len(LANES)} lane config(s)" in out,
          f"lanes={LANES} out={out[-200:]}")
    check("the chain order is reported primary-first, local tier before the paid pin, last-resort last",
          "in order " + " -> ".join(F.alias_order(_chain_json(ROOT))) in out,
          out[-200:])


def test_every_free_step_comes_before_the_paid_last_resort():
    """The chain itself: a free primary, free fallbacks, the pinned paid model LAST."""
    data = _chain_json(ROOT)
    chain = data["chain"]
    roles = [e["role"] for e in chain]
    check("exactly one primary, one last_resort, at least one fallback",
          roles.count("primary") == 1 and roles.count("last_resort") == 1
          and roles.count("fallback") >= 1,          str(roles))
    check("the last_resort is the LAST entry", roles[-1] == "last_resort",          str(roles))
    check("the primary is the FIRST entry", roles[0] == "primary",          str(roles))
    free = [e for e in chain if e["role"] in ("primary", "fallback")]
    check("every primary/fallback step is a `:free` model",
          all(e["model"].endswith(":free") for e in free),
          str([e["model"] for e in free if not e["model"].endswith(":free")]))
    # The local tier (issue #1192): credential-less, its OWN endpoint, after free, before the pin.
    locals_ = [e for e in chain if e["role"] == "local_fallback"]
    check("the chain carries exactly one local_fallback tier", len(locals_) == 1, str(locals_))
    if locals_:
        loc = locals_[0]
        li = chain.index(loc)
        check("the local tier sits AFTER every free step and BEFORE the last resort",
              all(i < li for i, e in enumerate(chain) if e["role"] in ("primary", "fallback"))
              and li == len(chain) - 2, str([e["role"] for e in chain]))
        check("the local tier names its OWN provider/base_url, not the chain's remote endpoint",
              loc.get("provider") and loc.get("base_url") and loc["base_url"] != data.get("base_url"),
              str(loc))
        check("the local tier is credential-less (no key_env) and names a BARE server model id",
              "key_env" not in loc and "/" not in loc["model"], str(loc))
    mk = (ROOT / "Makefile").read_text()
    pinned_model = [line.split(":=", 1)[1].strip() for line in mk.splitlines()
                    if line.startswith("HERMES_MODEL :=")][0]
    pinned_alias = [line.split(":=", 1)[1].strip() for line in mk.splitlines()
                    if line.startswith("HERMES_ALIAS :=")][0]
    last = chain[-1]
    check("the last resort is the Makefile's pinned model", last["model"] == pinned_model,
          f"{last['model']} vs {pinned_model}")
    check("the last resort alias is the Makefile's pinned alias", last["alias"] == pinned_alias,
          f"{last['alias']} vs {pinned_alias}")
    check("the chain provider is the built-in `nous` provider (issue #1203)",
          data["provider"] == "nous", str(data.get("provider")))
    check("the `nous` chain names NO key_env (the Portal session authenticates it)",
          not data.get("key_env"), str(data.get("key_env")))
    check("no chain entry carries a credential field",
          not any(k in e for e in chain for k in ("api_key", "apikey", "token", "secret")))
    check("every chain step names a context_window it was measured with",
          all(isinstance(e.get("context_window"), int) and e["context_window"] > 0 for e in chain))
    check("the chain states how its model ids were measured (rule 2)",
          bool(data.get("measured", {}).get("how")), str(data.get("measured")))


def test_the_local_tier_is_guarded_like_every_other_tier():
    """Issue #1192: every way the credential-less local tier can break its contract is refused.

    Each case is RED on the pre-change seam (which knew no local_fallback role at all).
    """
    def _local(d):
        return next(e for e in d["chain"] if e["role"] == "local_fallback")

    cases = {
        "two local tiers": lambda d: d["chain"].insert(-1, dict(_local(d), alias="local-copy")),
        "a local tier before the free fallbacks": lambda d: d["chain"].insert(1, d["chain"].pop(-2)),
        "a local tier after the last resort": lambda d: d["chain"].append(d["chain"].pop(-2)),
        "a local tier carrying key_env": lambda d: _local(d).update({"key_env": "NOUS_API_KEY"}),
        "a local tier naming the chain's remote endpoint": lambda d: _local(d).update({"base_url": "https://inference-api.nousresearch.com/v1"}),
        "a local tier with no provider of its own": lambda d: _local(d).pop("provider"),
        "a local tier with no base_url of its own": lambda d: _local(d).pop("base_url"),
        "a local tier naming a provider/model id instead of a bare server id": lambda d: _local(d).update({"model": "strata/qwen3.8-flash-next-iq3_xxs"}),
        "a local tier carrying an api_key value": lambda d: _local(d).update({"api_key": "not-a-credential-placeholder"}),
    }
    for name, mutate in cases.items():
        with tempfile.TemporaryDirectory() as td:
            root = _scratch(Path(td))
            data = _chain_json(root)
            mutate(data)
            _write_chain(root, data)
            res = run("--check", root=root)
            out = res.stdout + res.stderr
            check(f"chain with {name} is refused", res.returncode == 1, out[-200:])
            check(f"the refusal for {name} is stated in words",
                  "[model-chain] FAIL" in out, out[-200:])


def test_a_nous_step_carrying_base_url_or_key_env_is_refused():
    """Issue #1203: a `nous` alias carrying `base_url`/`key_env` is re-routed to `custom` and
    answers HTTP 401 on inference (measured on this host), so the gate refuses the shape."""
    for field, value in (("base_url", "https://inference-api.nousresearch.com/v1"),
                         ("key_env", "NOUS_API_KEY")):
        with tempfile.TemporaryDirectory() as td:
            root = _scratch(Path(td))
            data = _chain_json(root)
            data["chain"][0][field] = value          # the PRIMARY, a `nous` step
            _write_chain(root, data)
            res = run("--check", root=root)
            out = res.stdout + res.stderr
            check(f"a nous step carrying {field} is refused", res.returncode == 1, out[-200:])
            check(f"the {field} refusal names the measured 401", "401" in out, out[-300:])


def test_the_rendered_config_carries_the_runtime_fallback_order_and_a_credential_less_local_alias():
    """The rendered lane config is the RUNTIME order: fallback_providers walks free -> local -> paid."""
    rendered = run("--report")  # proves the chain reads; the bytes come from the shipped config
    text = (ROOT / "agents" / LANES[0] / "config.yaml").read_text(encoding="utf-8")
    check("the report runs green on the shipped chain", rendered.returncode == 0,
          rendered.stdout + rendered.stderr)
    # Issues #1744/#1750: every needle is DERIVED from the shipped chain, never frozen.
    chain = _chain_json(ROOT)
    local_model = F.local_model(chain)
    local_provider_needle = f"provider: {F.local_provider(chain)}"
    local_endpoint_needle = f"base_url: {F.local_endpoint(chain)}"
    fb = text.split("fallback_providers:", 1)[1] if "fallback_providers:" in text else ""
    fb = re.split(r"(?m)^[A-Za-z_][\w-]*:", fb, maxsplit=1)[0]
    models = re.findall(r"(?m)^    model: (\S+)", fb)
    check("fallback_providers lists every non-primary step in chain order",
          models == F.fallback_models(chain), str(models))
    entries = re.split(r"(?m)^  - ", fb)[1:]
    local_entries = [e for e in entries if local_model in e]
    check("the local fallback entry is credential-less (no key_env) and names its own endpoint",
          len(local_entries) == 1 and "key_env" not in local_entries[0]
          and local_endpoint_needle in local_entries[0]
          and local_provider_needle in local_entries[0], str(local_entries))
    remote_entries = [e for e in entries if local_model not in e]
    check("every remote fallback entry is a `nous` step with NO key_env (issue #1203)",
          remote_entries and all("key_env" not in e and "provider: nous" in e for e in remote_entries),
          str(remote_entries))
    alias_block = (text.split(f"  {F.local_alias(chain)}:", 1)[1]
                   .split(f"\n  {F.paid_alias(chain)}:", 1)[0])
    check("the local alias block carries its own provider/base_url and NO key_env",
          local_provider_needle in alias_block and local_endpoint_needle in alias_block
          and "key_env" not in alias_block, alias_block)


def test_the_rendered_goal_judge_pins_the_served_local_model():
    """Issue #1798: goal_judge uses the chain's local model and a Nous fallback_chain.

    An explicit auxiliary provider does not walk fallback_providers, so the rendered
    judge repeats every other chain step — every :free Nous model, including the
    free primary, then the paid last resort — and leaves model.default on the free primary.
    """
    chain = _chain_json(ROOT)
    text = (ROOT / "agents" / LANES[0] / "config.yaml").read_text(encoding="utf-8")
    judge = text.split("auxiliary:", 1)[1] if "auxiliary:" in text else ""
    judge = re.split(r"(?m)^[A-Za-z_][\w-]*:", judge, maxsplit=1)[0]
    hops = [e["model"] for e in chain["chain"] if e["role"] != "local_fallback"]
    hop_models = re.findall(r"(?m)^        model: (\S+)", judge)
    check("goal_judge is present and pinned to the chain's local model",
          "goal_judge:" in judge
          and f"model: {F.local_model(chain)}" in judge
          and f"provider: {F.local_provider(chain)}" in judge
          and f"base_url: {F.local_endpoint(chain)}" in judge, judge[:400])
    free_ids = [e["model"] for e in chain["chain"] if str(e["model"]).endswith(":free")]
    check("goal_judge fallback_chain is every Nous step except the local tier, with no key_env",
          hop_models == hops and "key_env" not in judge, str(hop_models))
    check("goal_judge fallback_chain names every Nous :free model",
          all(model in hop_models for model in free_ids), str(free_ids))
    check("model.default stays the free primary",
          F.default_line(chain) in text.split("model_aliases:", 1)[0], text[:200])


def test_local_tier_fixtures_follow_the_chain_not_a_frozen_snapshot():
    """Issue #1750: local-tier fixtures must follow the shipped data, not a snapshot.

    A synthetic chain whose local model/alias/provider/endpoint are absent from every
    old literal REDs the frozen shape and GREENs this one. The shipped derived needles
    are also proved present in the rendered config, so the guard pins the real seam.
    """
    synthetic = {"chain": [
        {"model": "synthetic-free/one:free", "alias": "free-one", "role": "primary", "context_window": 11111},
        {"model": "synthetic-free/two:free", "alias": "free-two", "role": "fallback", "context_window": 22222},
        {"model": "synthetic-local/model-xyz", "alias": "local-synthetic", "role": "local_fallback",
         "provider": "synthetic-provider", "base_url": "http://127.0.0.1:9999/v1", "context_window": 4096},
        {"model": "synthetic-paid/model", "alias": "paid-synthetic", "role": "last_resort", "context_window": 8192},
    ]}
    check("local model fixture follows a synthetic chain",
          F.local_model(synthetic) == "synthetic-local/model-xyz")
    check("local alias fixture follows a synthetic chain",
          F.local_alias(synthetic) == "local-synthetic")
    check("local provider fixture follows a synthetic chain",
          F.local_provider(synthetic) == "synthetic-provider")
    check("local endpoint fixture follows a synthetic chain",
          F.local_endpoint(synthetic) == "http://127.0.0.1:9999/v1")
    check("paid alias fixture follows a synthetic chain",
          F.paid_alias(synthetic) == "paid-synthetic")

    shipped = _chain_json(ROOT)
    rendered = (ROOT / "agents" / LANES[0] / "config.yaml").read_text(encoding="utf-8")
    check("the shipped local needles are derived from the chain and present in the rendered config",
          f"model: {F.local_model(shipped)}" in rendered
          and f"  {F.local_alias(shipped)}:" in rendered
          and f"provider: {F.local_provider(shipped)}" in rendered
          and f"base_url: {F.local_endpoint(shipped)}" in rendered
          and f"  {F.paid_alias(shipped)}:" in rendered,
          rendered[:300])


def test_a_hand_edited_lane_config_is_refused_and_names_the_lane_and_line():
    """A lane config edited by hand is the exact drift this gate exists to catch."""
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        cfg = root / "agents" / "tll-tester" / "config.yaml"
        text = cfg.read_text(encoding="utf-8")
        # Derive the shipped primary's `default:` needle instead of freezing one model id.
        primary_needle = F.default_line(_chain_json(root))
        edited_line = next(i for i, line in enumerate(text.splitlines(), start=1)
                           if primary_needle in line)
        paid_needle = "default: deepseek/deepseek-v4-flash-0731"
        cfg.write_text(text.replace(primary_needle, paid_needle), encoding="utf-8")
        res = run("--check", root=root)
        out = res.stdout + res.stderr
        check("a hand-edited lane config fails the gate", res.returncode == 1, out[-200:])
        check("the failure names the lane whose config drifted",
              "agents/tll-tester/config.yaml" in out, out[-300:])
        check("the failure names the line and both spellings",
              f"line {edited_line}:" in out and paid_needle.split("default: ")[1] in out
              and primary_needle.split("default: ")[1] in out, out[-400:])
        check("the other lane is reported as clean (only the drifted one fails)",
              "tll-reviewer" not in out, out[-300:])
        check("the refusal tells the author to re-render rather than hand-edit",
              "agent-profile-model-render" in out, out[-300:])


def test_the_chain_shape_is_the_contract_primary_fallbacks_then_last_resort():
    """Every way the chain can lose its shape is refused, by name."""
    cases = {
        "two primaries": lambda d: d["chain"][1].update({"role": "primary"}),
        "no fallback at all": lambda d: d.__setitem__("chain", [d["chain"][0], d["chain"][-1]]),
        "no last resort": lambda d: d["chain"][-1].update({"role": "fallback"}),
        "a paid model before a free one": lambda d: d["chain"].reverse(),
        "a primary that is not free": lambda d: d["chain"][0].update({"model": "anthropic/claude-opus-4.6", "context_window": 200000}),
        "the same alias twice": lambda d: d["chain"][1].update({"alias": d["chain"][0]["alias"]}),
    }
    for name, mutate in cases.items():
        with tempfile.TemporaryDirectory() as td:
            root = _scratch(Path(td))
            data = _chain_json(root)
            mutate(data)
            _write_chain(root, data)
            res = run("--check", root=root)
            out = res.stdout + res.stderr
            check(f"chain with {name} is refused", res.returncode == 1, out[-160:])
            check(f"the refusal for {name} is stated in words",
                  "[model-chain] FAIL" in out and "chain" in out, out[-160:])


def test_the_last_resort_must_be_the_model_the_makefile_pins():
    """A chain whose last step is not the pinned model/alias is a drift the gate refuses."""
    for field, needle in (("model", "HERMES_MODEL"), ("alias", "HERMES_ALIAS")):
        with tempfile.TemporaryDirectory() as td:
            root = _scratch(Path(td))
            data = _chain_json(root)
            data["chain"][-1][field] = "openai/gpt-5n" if field == "model" else "wrong-alias"
            _write_chain(root, data)
            res = run("--write", root=root)
            out1 = res.stdout + res.stderr
            res2 = run("--check", root=root)
            out2 = res2.stdout + res2.stderr
            check(f"a last resort whose {field} is not the pin fails --check", res2.returncode == 1, out2[-200:])
            check(f"the {field} refusal names the Makefile pin {needle}", needle in out2, out2[-300:])
            check(f"--write refuses to render a chain that broke its {field} pin",
                  res.returncode == 1 and "FAIL" in out1, out1[-200:])


def test_a_credential_value_or_api_key_field_is_refused_everywhere():
    """Rule 3e: a chain or a rendered config may name `key_env`, never a credential."""
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        cfg = root / "agents" / "tll-tester" / "config.yaml"
        cfg.write_text(cfg.read_text(encoding="utf-8") + "\n  api_key: not-a-credential-placeholder\n",
                       encoding="utf-8")
        res = run("--check", root=root)
        out = res.stdout + res.stderr
        check("an `api_key` field in a lane config is refused", res.returncode == 1, out[-200:])
        check("the refusal names the credential field", "api_key" in out, out[-300:])

        data = _chain_json(root)
        data["chain"][0]["api_key"] = "not-a-credential-placeholder"
        _write_chain(root, data)
        res = run("--check", root=root)
        out = res.stdout + res.stderr
        check("an `api_key` field in the chain itself is refused", res.returncode == 1, out[-200:])

    shipped = [CHAIN] + [ROOT / "agents" / lane / "config.yaml" for lane in LANES]
    texts = {str(p.relative_to(ROOT)): p.read_text(encoding="utf-8") for p in shipped}
    bad = {n: credential_field_lines(t) for n, t in texts.items() if credential_field_lines(t)}
    check("no shipped chain or lane config ASSIGNS a credential field (prose may name one)",
          not bad, str(bad))
    check("every shipped config names key_env as an environment NAME, never a value",
          all(set(key_env_names(t)) <= {"NOUS_API_KEY"} for t in texts.values()),
          str({n: key_env_names(t) for n, t in texts.items()}))
    check("the shipped `nous` configs name NO key_env at all (it re-routes to `custom`)",
          all(not key_env_names(t) for n, t in texts.items() if n.endswith("config.yaml")),
          str({n: key_env_names(t) for n, t in texts.items() if n.endswith("config.yaml")}))


def test_an_unreadable_chain_is_exit_2_never_a_silent_clean():
    """A chain that cannot be read is a loud UNDECIDABLE, not a pass."""
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        (root / "agents" / "model_chain.json").write_text('{"chain": [', encoding="utf-8")
        res = run("--check", root=root)
        check("a truncated chain JSON exits 2", res.returncode == 2, res.stdout + res.stderr)
        check("a truncated chain JSON says UNDECIDABLE", "UNDECIDABLE" in res.stderr, res.stderr[-200:])

        (root / "agents" / "model_chain.json").unlink()
        res = run("--check", root=root)
        check("a missing chain exits 2", res.returncode == 2, res.stdout + res.stderr)
        check("a missing chain names the file it wanted", "agents/model_chain.json" in res.stderr,
              res.stderr[-200:])
        res = run("--write", root=root)
        check("--write over a missing chain also exits 2", res.returncode == 2, res.stderr[-200:])


def test_a_lane_without_a_config_is_refused():
    """A new fleet lane that was never rendered is caught, not silently skipped."""
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        d = root / "agents" / "tll-newlan"
        d.mkdir(parents=True)
        (d / "SOUL.md").write_text("# new lane\n", encoding="utf-8")
        res = run("--check", root=root)
        out = res.stdout + res.stderr
        check("a lane with no config.yaml fails", res.returncode == 1, out[-200:])
        check("the refusal names the missing lane config",
              "agents/tll-newlan/config.yaml is missing" in out, out[-300:])


def test_the_make_target_renders_the_shipped_configs_from_a_fresh_tree():
    """`make agent-profile-model-render` run in a copy reproduces the configs byte-for-byte."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        shutil.copy(ROOT / "Makefile", root / "Makefile")
        (root / "scripts").mkdir()
        shutil.copy(SCRIPT, root / "scripts" / "agent_model_chain.py")
        (root / "agents").mkdir()
        shutil.copy(CHAIN, root / "agents" / "model_chain.json")
        for lane in LANES:
            d = root / "agents" / lane
            d.mkdir()
            shutil.copy(ROOT / "agents" / lane / "SOUL.md", d / "SOUL.md")
            # Issue #1618: a lane's declared extra config block is part of what the seam renders.
            append = ROOT / "agents" / lane / "config.append.yaml"
            if append.is_file():
                shutil.copy(append, d / "config.append.yaml")
        res = subprocess.run(["make", "-C", str(root), "agent-profile-model-render"],
                             cwd=str(ROOT), capture_output=True, text=True)
        check("`make agent-profile-model-render` runs in a fresh tree", res.returncode == 0,
              (res.stdout + res.stderr)[-200:])
        same = all(
            (root / "agents" / lane / "config.yaml").read_text(encoding="utf-8")
            == (ROOT / "agents" / lane / "config.yaml").read_text(encoding="utf-8")
            for lane in LANES
        )
        check("the rendered configs equal the shipped ones byte-for-byte", same)
        res = subprocess.run(["make", "-C", str(root), "agent-model-chain-check"],
                             cwd=str(ROOT), capture_output=True, text=True)
        check("`make agent-model-chain-check` passes in that fresh tree", res.returncode == 0,
              (res.stdout + res.stderr)[-200:])


def test_a_declared_lane_append_is_rendered_and_an_undeclared_one_is_refused():
    """Issue #1618: an owner-authorized lane block is rendered from the TREE, never hand-typed on a host."""
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        lane = "tll-tester"
        block = "# owner-authorized 2026-11-24 (issue #1591)\nsecurity:\n  protected_instruction_files: false\n"
        (root / "agents" / lane / "config.append.yaml").write_text(block, encoding="utf-8")
        res = run("--write", root=root)
        check("a declared append renders green", res.returncode == 0, (res.stdout + res.stderr)[-200:])
        cfg_path = root / "agents" / lane / "config.yaml"
        text = cfg_path.read_text(encoding="utf-8")
        check("the lane config carries the declared block byte-for-byte", block in text, text[-200:])
        check("the chain's owned blocks stay byte-exact before the append",
              "  - provider: nous\n    model: deepseek/deepseek-v4-flash-0731\n" in text
              and text.index("fallback_providers:") < text.index("# owner-authorized"),
              repr(text[-120:]))
        other = (root / "agents" / "tll-reviewer" / "config.yaml").read_text(encoding="utf-8")
        check("a lane with no declared append renders exactly as before",
              "protected_instruction_files" not in other, other[-120:])
        res = run("--check", root=root)
        check("the gate is green on the rendered append", res.returncode == 0,
              (res.stdout + res.stderr)[-200:])
        cfg_path.write_text(text + "terminal:\n  backend: local\n", encoding="utf-8")
        res = run("--check", root=root)
        check("an UNDECLARED extra block is refused, not laundered", res.returncode == 1,
              (res.stdout + res.stderr)[-200:])
        (root / "agents" / lane / "config.append.yaml").write_text(
            "model:\n  default: deepseek/deepseek-v4-flash-0731\n", encoding="utf-8")
        run("--write", root=root)
        res = run("--check", root=root)
        out = res.stdout + res.stderr
        check("an append may not redeclare a chain-owned block", res.returncode == 1
              and "redeclares `model:`" in out, out[-300:])


def test_the_gate_is_wired_where_it_bites():
    """Rule 6m: the check runs in `make lint` (qa-validate + the fix loop) and the suite runs it."""
    mk = (ROOT / "Makefile").read_text()
    lint_recipe = mk.split("lint: ##", 1)[1].split("\n\n", 1)[0] if "lint: ##" in mk else ""
    check("`make lint` calls agent-model-chain-check", "agent-model-chain-check" in lint_recipe,
          lint_recipe[:200])
    check("the internal recipe runs the script (no workflow reaches past the Makefile)",
          "_agent-model-chain-check:\n\tpython3 scripts/agent_model_chain.py --check" in mk, "")
    check("make lint is the FIRST check in scripts/fix_loop.sh's list",
          "CHECKS=(lint " in (ROOT / "scripts" / "fix_loop.sh").read_text(encoding="utf-8"))
    qa = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text(encoding="utf-8")
    check("qa-validate runs `make lint` (so the gate blocks auto-merge)", "run: make lint" in qa, "")
    check("no workflow reaches into scripts/agent_model_chain.py directly (rule 6m)",
          not any("agent_model_chain" in (ROOT / ".github" / "workflows" / p.name).read_text(encoding="utf-8")
                  for p in (ROOT / ".github" / "workflows").iterdir() if p.suffix == ".yml"))
    check("this suite is discovered by `make test`", wired(__file__), "")


def main() -> int:
    print(f"agent_model_chain (issue #1140): {len(LANES)} fleet lane(s) "
          f"{', '.join(LANES)}")
    test_the_shipped_chain_renders_every_lane_config_and_the_gate_is_green()
    test_every_free_step_comes_before_the_paid_last_resort()
    test_the_local_tier_is_guarded_like_every_other_tier()
    test_a_nous_step_carrying_base_url_or_key_env_is_refused()
    test_the_rendered_config_carries_the_runtime_fallback_order_and_a_credential_less_local_alias()
    test_the_rendered_goal_judge_pins_the_served_local_model()
    test_local_tier_fixtures_follow_the_chain_not_a_frozen_snapshot()
    test_a_hand_edited_lane_config_is_refused_and_names_the_lane_and_line()
    test_the_chain_shape_is_the_contract_primary_fallbacks_then_last_resort()
    test_the_last_resort_must_be_the_model_the_makefile_pins()
    test_a_credential_value_or_api_key_field_is_refused_everywhere()
    test_an_unreadable_chain_is_exit_2_never_a_silent_clean()
    test_a_lane_without_a_config_is_refused()
    test_the_make_target_renders_the_shipped_configs_from_a_fresh_tree()
    test_a_declared_lane_append_is_rendered_and_an_undeclared_one_is_refused()
    test_the_gate_is_wired_where_it_bites()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
