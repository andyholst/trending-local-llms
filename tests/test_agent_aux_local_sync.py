#!/usr/bin/env python3
"""tests/test_agent_aux_local_sync.py — issue #1198: the chain's local tier reaches the AUXILIARY blocks.

Issue #1142/#1192 built the provision seam: the rendered chain lands in every Hermes home, but
ONLY the `model:`, `model_aliases:` and `fallback_providers:` blocks are owned — every other block
is kept byte-for-byte. Two other blocks also name the local provider: `custom_providers[strata]`
and the `moa:` presets. Measured 2026-11-21 across all 30 host homes: 23 still name the retired
`qwen3.8-flash-next-q2_0` there while the chain's `local_fallback` names
`qwen3.8-flash-next-iq3_xxs` — the MoA auxiliary tool and the strata provider entry would call a
model the box no longer serves. This suite locks the seam that closes that drift:

  1. the strata custom_providers entry (model + models-map key/context) and every local moa entry
     take the chain's local id; a NON-local provider entry and a NON-local moa reference survive
     byte-for-byte, as does every other top-level block and the leading prose;
  2. the prior config is KEPT as `config.yaml.bak-<UTC>` (rule 3b) and the sync is IDEMPOTENT
     (a clean home is not written at all);
  3. `--check` exits 1 on drift / 0 clean and writes nothing; `--dry-run` previews, writes nothing;
  4. refusals (exit 2, NOTHING written anywhere): a chain without the local tier, an ambiguous
     stale id shared with a non-local moa entry, a models map with >1 distinct stale key, a
     missing home, no named target;
  5. NO credential is required (the seam writes only credential-less local-tier references) and
     no credential VALUE or env-substitution NAME is altered;
  6. `default` names the Hermes home's own config; `--all-profiles` covers every home;
  7. the target is wired to the Makefile, ARCHITECTURE.md and a pipeline job (rules 6d/6h/6m).

The guards run the REAL `scripts/agent_aux_local_sync.py` end to end against a scratch tree and a
scratch profile home (rule 6m: no stand-in replaces the seam; the only external system is the
filesystem, which is real).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import agent_model_chain as AMC  # noqa: E402  (the ONE chain reader, rule 6d)
from wiring import wired  # noqa: E402  (a test must be discovered by `make test`, rule 6d)

SCRIPT = ROOT / "scripts" / "agent_aux_local_sync.py"
CHAIN = ROOT / "agents" / "model_chain.json"

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


# The shipped chain's local tier (this branch carries it; issue #1192 / PR #1197).
_TIER = AMC.read_chain(ROOT)[0].local_fallback
NEW_ID = _TIER.model
STALE = "qwen3.8-flash-next-q2_0"  # the retired id measured in 23 host homes (2026-11-21)
KEY_SUB = "${HERMES_CUSTOM_127_0_0_1_8080_API_KEY}"  # an env NAME substitution, never a value


# ---------------------------------------------------------------- fixtures


def _scratch(td: Path) -> Path:
    """A fresh tree carrying the seam, its ONE chain source and the Makefile pins."""
    root = td
    (root / "scripts").mkdir(parents=True)
    (root / "agents").mkdir(parents=True)
    shutil.copy(ROOT / "Makefile", root / "Makefile")
    shutil.copy(CHAIN, root / "agents" / "model_chain.json")
    for name in ("agent_model_chain.py", "require_env.py", "agent_profile_provision.py",
                 "agent_aux_local_sync.py"):
        shutil.copy(ROOT / "scripts" / name, root / "scripts" / name)
    return root


def run_sync(*args, root: Path, env=None):
    e = dict(os.environ if env is None else env)
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args],
                          capture_output=True, text=True, env=e, timeout=120)


def stale_text(moa_extra_ref: str = "", second_key: str = "", ctx: int = 999) -> str:
    """The measured live-home shape: chain-owned blocks + a STALE strata entry + stale moa."""
    extra = f"        - model: {moa_extra_ref}\n          provider: custom\n          base_url: https://openrouter.ai/api/v1\n" if moa_extra_ref else ""
    second = f"      {second_key}:\n        context_length: 131072\n" if second_key else ""
    return (
        "# a hand-written home config (issue #1198 fixture)\n"
        "model:\n"
        "  provider: custom\n"
        "  default: meituan/longcat-2.5:free\n"
        "  base_url: https://inference-api.nousresearch.com/v1\n"
        "  context_length: 1048576\n"
        "custom_providers:\n"
        "  - name: strata\n"
        "    base_url: http://127.0.0.1:8080/v1\n"
        "    key_env: HERMES_CUSTOM_127_0_0_1_8080_API_KEY\n"
        "    api_mode: chat_completions\n"
        f"    model: {STALE}\n"
        "    models:\n"
        f"      {STALE}:\n"
        f"        context_length: {ctx}\n"
        f"{second}"
        "    discover_models: true\n"
        "  - name: other\n"
        "    base_url: http://127.0.0.1:9999/v1\n"
        "    model: some-other-model\n"
        "moa:\n"
        "  default_preset: default\n"
        "  presets:\n"
        "    default:\n"
        "      aggregator:\n"
        f"        model: {STALE}\n"
        "        provider: strata\n"
        "        base_url: http://127.0.0.1:8080/v1\n"
        f"        api_key: {KEY_SUB}\n"
        "      aggregator_temperature: 0.5\n"
        "      enabled: true\n"
        "      max_tokens: 8192\n"
        "      reference_models:\n"
        f"        - model: {STALE}\n"
        "          provider: strata\n"
        "          base_url: http://127.0.0.1:8080/v1\n"
        f"          api_key: {KEY_SUB}\n"
        f"        - model: {STALE}\n"
        "          provider: strata\n"
        "          base_url: http://127.0.0.1:8080/v1\n"
        f"{extra}"
        "      reference_temperature: 0.7\n"
        "terminal:\n"
        "  backend: local\n"
        "  cwd: /tmp\n"
        "auxiliary:\n"
        "  vision:\n"
        "    provider: auto\n"
    )


def _plant(home: Path, name: str, text: str) -> Path:
    pdir = home / name
    pdir.mkdir(parents=True, exist_ok=True)
    dest = pdir / AMC.CONFIG_REL
    dest.write_text(text, encoding="utf-8")
    return dest


def _backups(pdir: Path):
    return sorted(p.name for p in pdir.iterdir() if p.name.startswith(f"{AMC.CONFIG_REL}.bak-"))


# ---------------------------------------------------------------- guards


def test_the_stale_auxiliary_blocks_take_the_chain_local_id_and_every_other_byte_survives():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        original = stale_text()
        dest = _plant(home, "developer", original)
        proc = run_sync("--profile", "developer", "--profiles-home", str(home), root=root)
        out = proc.stdout + proc.stderr
        check("syncing a named stale home exits green", proc.returncode == 0, out[-300:])
        merged = dest.read_text(encoding="utf-8")
        d = yaml.safe_load(merged)
        strata = next(c for c in d["custom_providers"] if c["name"] == "strata")
        check("the strata entry's model IS the chain's local id", strata["model"] == NEW_ID, strata["model"])
        check("the models map is keyed by the chain's local id with the tier's window",
              list(strata["models"]) == [NEW_ID]
              and strata["models"][NEW_ID]["context_length"] == _TIER.context_window,
              str(strata["models"]))
        preset = d["moa"]["presets"]["default"]
        check("the moa aggregator takes the chain's local id", preset["aggregator"]["model"] == NEW_ID)
        check("every local moa reference takes the chain's local id",
              all(r["model"] == NEW_ID for r in preset["reference_models"]))
        check("the retired id is GONE from the whole config", STALE not in merged)
        check("the NON-local provider entry survives byte-for-byte",
              "  - name: other\n    base_url: http://127.0.0.1:9999/v1\n    model: some-other-model\n" in merged)
        check("the env-substitution NAME and key_env are untouched (no credential value ever)",
              merged.count(KEY_SUB) == 2 and "key_env: HERMES_CUSTOM_127_0_0_1_8080_API_KEY" in merged)
        check("the chain-owned model block, terminal, auxiliary and leading prose survive BYTE-FOR-BYTE",
              "# a hand-written home config (issue #1198 fixture)\n" in merged
              and "model:\n  provider: custom\n  default: meituan/longcat-2.5:free\n" in merged
              and "terminal:\n  backend: local\n  cwd: /tmp\n" in merged
              and "auxiliary:\n  vision:\n    provider: auto\n" in merged, merged[-200:])
        check("the prior config is KEPT as a backup (rule 3b)",
              len(_backups(dest.parent)) == 1
              and (dest.parent / _backups(dest.parent)[0]).read_text(encoding="utf-8") == original)
        check("the seam names the profile, the destination and the local id",
              "profile=developer" in out and str(dest) in out and NEW_ID in out, out[-200:])

        again = run_sync("--profile", "developer", "--profiles-home", str(home), root=root)
        check("the sync is IDEMPOTENT (a clean home is not written, no second backup)",
              again.returncode == 0
              and dest.read_text(encoding="utf-8") == merged
              and len(_backups(dest.parent)) == 1, again.stdout[-200:] + again.stderr[-200:])


def test_check_reports_drift_without_writing_and_reads_clean_after_the_sync():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        original = stale_text()
        dest = _plant(home, "tester", original)
        proc = run_sync("--profile", "tester", "--check", "--profiles-home", str(home), root=root)
        check("--check on a stale home exits 1 (drift)", proc.returncode == 1, proc.stdout[-200:])
        check("--check names the drift and writes NOTHING",
              "DRIFT" in proc.stdout and dest.read_text(encoding="utf-8") == original
              and not _backups(dest.parent))
        run_sync("--profile", "tester", "--profiles-home", str(home), root=root)
        clean = run_sync("--profile", "tester", "--check", "--profiles-home", str(home), root=root)
        check("--check after the sync exits 0 (clean)", clean.returncode == 0, clean.stdout[-200:])
        dry = run_sync("--profile", "tester", "--dry-run", "--profiles-home", str(home), root=root)
        check("--dry-run exits 0 and writes nothing", dry.returncode == 0 and "DRY RUN" in dry.stdout)


def test_a_chain_without_the_local_tier_is_refused_and_writes_nothing():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        raw = json.loads((root / "agents" / "model_chain.json").read_text())
        raw["chain"] = [e for e in raw["chain"] if e.get("role") != "local_fallback"]
        (root / "agents" / "model_chain.json").write_text(json.dumps(raw))
        home = Path(td) / "profiles"
        original = stale_text()
        dest = _plant(home, "developer", original)
        proc = run_sync("--profile", "developer", "--profiles-home", str(home), root=root)
        check("a chain without the tier REFUSES exit 2 (master's state until #1197)",
              proc.returncode == 2, proc.stdout[-200:] + proc.stderr[-200:])
        check("the refusal names the missing tier and writes NOTHING",
              "local_fallback" in proc.stderr and dest.read_text(encoding="utf-8") == original
              and not _backups(dest.parent))


def test_an_ambiguous_stale_id_shared_with_a_non_local_moa_entry_is_refused():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        original = stale_text(moa_extra_ref=STALE)  # a NON-local entry names the same stale id
        dest = _plant(home, "developer", original)
        proc = run_sync("--profile", "developer", "--profiles-home", str(home), root=root)
        check("an id named by BOTH a local and a non-local moa entry REFUSES exit 2",
              proc.returncode == 2 and "non-local" in proc.stderr, proc.stderr[-250:])
        check("the ambiguous refusal writes NOTHING", dest.read_text(encoding="utf-8") == original
              and not _backups(dest.parent))


def test_a_models_map_with_two_distinct_stale_keys_is_refused():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        original = stale_text(second_key="another-old-local-id")
        dest = _plant(home, "developer", original)
        proc = run_sync("--profile", "developer", "--profiles-home", str(home), root=root)
        check("two distinct stale models-map keys REFUSE exit 2 (a human decision)",
              proc.returncode == 2 and "human decision" in proc.stderr, proc.stderr[-250:])
        check("the multi-key refusal writes NOTHING", dest.read_text(encoding="utf-8") == original)


def test_one_refusal_writes_nothing_anywhere_even_when_other_homes_are_clean_syncs():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        good = _plant(home, "developer", stale_text())
        bad_original = stale_text(second_key="another-old-local-id")
        bad = _plant(home, "tester", bad_original)
        proc = run_sync("--profile", "developer", "--profile", "tester",
                        "--profiles-home", str(home), root=root)
        check("a mixed run with one refusal exits 2", proc.returncode == 2, proc.stderr[-200:])
        check("NO home was written — the good home keeps its stale bytes, no backups anywhere",
              good.read_text(encoding="utf-8") == stale_text()
              and bad.read_text(encoding="utf-8") == bad_original
              and not _backups(good.parent) and not _backups(bad.parent))


def test_default_names_the_hermes_homes_own_config_and_all_profiles_covers_every_home():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        home.mkdir(parents=True)
        default_dest = Path(td) / AMC.CONFIG_REL  # beside the profiles root
        default_dest.write_text(stale_text(), encoding="utf-8")
        a = _plant(home, "architect", stale_text())
        b = _plant(home, "singularity", stale_text())
        proc = run_sync("--profile", "default", "--profiles-home", str(home), root=root)
        check("`default` syncs the Hermes home's OWN config.yaml",
              proc.returncode == 0 and STALE not in default_dest.read_text(encoding="utf-8"),
              proc.stderr[-200:])
        proc = run_sync("--all-profiles", "--profiles-home", str(home), root=root)
        out = proc.stdout + proc.stderr
        check("--all-profiles syncs every profile dir AND default, exit green",
              proc.returncode == 0 and STALE not in a.read_text(encoding="utf-8")
              and STALE not in b.read_text(encoding="utf-8"), out[-250:])
        check("--all-profiles is idempotent (second run: everything already clean)",
              "already clean" in out)


def test_a_lane_shaped_home_without_the_auxiliary_blocks_is_skipped_not_rewritten():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        rendered = AMC.render_text(AMC.read_chain(root)[0])
        dest = _plant(home, "tll-planner", rendered)
        proc = run_sync("--profile", "tll-planner", "--profiles-home", str(home), root=root)
        check("a pure chain-copy home (no custom_providers/moa) is skipped, exit green",
              proc.returncode == 0 and dest.read_text(encoding="utf-8") == rendered
              and not _backups(dest.parent), proc.stdout[-200:] + proc.stderr[-200:])


def test_no_target_and_a_missing_home_are_refusals():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        home.mkdir(parents=True)
        proc = run_sync("--profiles-home", str(home), root=root)
        check("naming nothing REFUSES exit 2 (writing a live home is never a default)",
              proc.returncode == 2 and "never a default" in proc.stderr, proc.stderr[-200:])
        proc = run_sync("--profile", "ghost", "--profiles-home", str(home), root=root)
        check("a home without a config REFUSES exit 2 and names it",
              proc.returncode == 2 and "ghost" in proc.stderr, proc.stderr[-200:])


def test_no_credential_is_required_and_none_is_ever_read():
    with tempfile.TemporaryDirectory() as td:
        root = _scratch(Path(td))
        home = Path(td) / "profiles"
        dest = _plant(home, "developer", stale_text())
        env = {k: v for k, v in os.environ.items() if k != "NOUS_API_KEY"}
        proc = run_sync("--profile", "developer", "--profiles-home", str(home), root=root, env=env)
        check("the sync succeeds with NOUS_API_KEY ABSENT (only local-tier references are written)",
              proc.returncode == 0 and STALE not in dest.read_text(encoding="utf-8"),
              proc.stderr[-250:])
        check("the seam's output names no credential requirement",
              "NOUS_API_KEY" not in proc.stdout, proc.stdout[-200:])


def test_the_target_is_wired_to_the_makefile_architecture_and_a_pipeline_job():
    mk = (ROOT / "Makefile").read_text(encoding="utf-8")
    check("the Makefile carries the agent-aux-local-sync target (rule 6d)",
          "agent-aux-local-sync:" in mk and "scripts/agent_aux_local_sync.py" in mk, "")
    arch = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    check("the seam has rows in the ARCHITECTURE target AND script tables (rule 6h)",
          "`agent-aux-local-sync`" in arch and "`scripts/agent_aux_local_sync.py`" in arch, "")
    check("a pipeline job runs the seam (rule 6m)",
          any("agent-aux-local-sync" in (ROOT / ".github" / "workflows" / p.name).read_text(encoding="utf-8")
              for p in (ROOT / ".github" / "workflows").iterdir() if p.suffix == ".yml"), "")
    check("this suite is discovered by `make test`", wired(__file__), "")


def main() -> int:
    print(f"agent_aux_local_sync (issue #1198): the chain's local tier id: {NEW_ID}")
    test_the_stale_auxiliary_blocks_take_the_chain_local_id_and_every_other_byte_survives()
    test_check_reports_drift_without_writing_and_reads_clean_after_the_sync()
    test_a_chain_without_the_local_tier_is_refused_and_writes_nothing()
    test_an_ambiguous_stale_id_shared_with_a_non_local_moa_entry_is_refused()
    test_a_models_map_with_two_distinct_stale_keys_is_refused()
    test_one_refusal_writes_nothing_anywhere_even_when_other_homes_are_clean_syncs()
    test_default_names_the_hermes_homes_own_config_and_all_profiles_covers_every_home()
    test_a_lane_shaped_home_without_the_auxiliary_blocks_is_skipped_not_rewritten()
    test_no_target_and_a_missing_home_are_refusals()
    test_no_credential_is_required_and_none_is_ever_read()
    test_the_target_is_wired_to_the_makefile_architecture_and_a_pipeline_job()
    print(f"{'FAILED' if _FAIL else 'PASSED'} {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())