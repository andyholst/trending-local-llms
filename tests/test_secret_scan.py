#!/usr/bin/env python3
"""The secret scan is wired, configured and honest (issue #122).

Hermetic: no docker inside the pipeline image, so the real scan + the planted-key
self-test run in CI's `validate` job (`make secret-scan`, `make secret-scan-self-test`)
— what is checked here is that they exist, that CI calls them, that the config only
narrows known placeholders, and that the probe file cannot itself be the leak.

Run:  python3 tests/test_secret_scan.py    or   make test
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = (ROOT / "Makefile").read_text()
CONFIG = (ROOT / ".gitleaks.toml").read_text()
PROBE = (ROOT / "scripts" / "secret_scan_self_test.py").read_text()

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


def test_targets_exist_and_are_pinned():
    """`make secret-scan` is the pre-push gate; the scanner image is pinned."""

    # Given the Makefile
    # When  the secret-scan targets are looked up
    # Then  each exists with its internal/public pair and a pinned image tag
    for target in ("_secret-scan", "secret-scan", "_secret-scan-history",
                   "secret-scan-history", "secret-scan-self-test"):
        check(f"make: {target} exists", f"\n{target}:" in MAKEFILE)
    check("make: the gitleaks image is pinned by tag",
          re.search(r"GITLEAKS_IMAGE\s*:=\s*ghcr\.io/gitleaks/gitleaks:v\d+\.\d+\.\d+", MAKEFILE) is not None,
          [l for l in MAKEFILE.splitlines() if "GITLEAKS_IMAGE" in l])
    check("make: the scan uses the repo config and redaction",
          "--config /repo/.gitleaks.toml" in MAKEFILE and "--redact" in MAKEFILE)
    check("make: a finding fails the target (exit-code 1)",
          "--exit-code 1" in MAKEFILE)
    check("make: the failure message forbids allowlisting a real value",
          "never add it to .gitleaks.toml" in MAKEFILE.lower()
          or "Never add it to .gitleaks.toml" in MAKEFILE)


def test_history_scan_refuses_a_worktree():
    """A working-tree scan cannot see history; the history target must not report
    a fake clean when it cannot read the repo at all (a git worktree)."""

    # Given the history target
    # When  it runs against a checkout where .git is a FILE (a worktree)
    # Then  it refuses loudly instead of scanning 0 commits and exiting 0
    check("history: refuses a worktree instead of a fake clean",
          "[ -f .git ]" in MAKEFILE and "needs a real clone" in MAKEFILE)


def test_ci_runs_the_scan_and_its_self_test():
    """Rule 6d: CI executes the scan — the gate is not decoration."""

    # Given the PR CI workflow
    wf = (ROOT / ".github" / "workflows" / "qa-validate.yml").read_text()

    # Then  the validate job runs both the scan and the proof that it detects
    check("ci: validate job runs `make secret-scan`", "make secret-scan\n" in wf or "run: make secret-scan" in wf)
    check("ci: validate job runs the self-test", "make secret-scan-self-test" in wf)
    check("ci: the scan runs BEFORE the data validation",
          wf.index("make secret-scan") < wf.index("make validate\n"),
          "secret scan must gate the data stages")


def test_config_only_narrows_documented_placeholders():
    """Every allowlist entry is described, commented, and narrow: an allowlist
    that suppresses whole secret CLASSES would defeat the scan."""

    # Given the gitleaks config
    # When  its allowlists are read
    # Then  the default ruleset stays on and every entry explains itself
    check("config: extends the default ruleset", "[extend]" in CONFIG and "useDefault = true" in CONFIG)
    entries = CONFIG.split("[[allowlists]]")[1:]
    check("config: has allowlist entries (the known false positives)", len(entries) >= 1, len(entries))
    for i, entry in enumerate(entries, start=1):
        check(f"config: allowlist {i} carries a description", "description =" in entry)
        check(f"config: allowlist {i} is not a catch-all",
              not re.search(r"regexes\s*=\s*\[\s*'''\.\*'''\s*\]", entry))
    # the only rule-scoped entry is the generated baseline's entropy false positive
    check("config: the generated baseline is the one rule-scoped allowlist",
          "gap_baseline" in CONFIG and "generic-api-key" in CONFIG)
    lines = CONFIG.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "[[allowlists]]":
            window = "\n".join(lines[max(0, i - 4):i])
            check(f"config: allowlist at line {i + 1} is preceded by a comment saying why",
                  "#" in window, window.replace("\n", " | ")[:120])


def test_probe_file_is_not_itself_a_leak():
    """The self-test plants credential shapes; the SCRIPT must not contain them as
    literals, or the repo scan would flag the probe and invite an allowlist."""

    # Given the self-test script source
    # When  it is scanned for literal credential shapes
    literals = re.findall(r"(?:ghp_|hf_|sk-proj-)[A-Za-z0-9]{16,}", PROBE)

    # Then  none are present (the values are assembled from parts)
    check("probe: no literal credential shape in the script", not literals, literals)
    check("probe: it builds the fake values from parts", "_PARTS" in PROBE and "join" in PROBE)
    check("probe: it FAILS when a planted credential is not detected",
          "were NOT detected" in PROBE)
    check("probe: it FAILS when the clean fixture reports findings",
          "clean fixture reported" in PROBE)
    check("probe: --redact is used so a finding never prints the value",
          "--redact" in PROBE)


def test_config_allowlists_are_justified_by_the_repo():
    """Each allowlist entry must be traceable to something real in the repo: the
    generated baseline, and documentation placeholders."""

    # Given the allowlists
    # Then  the baseline entry names the generated file it exempts
    check("config: the baseline allowlist names data/gap_baseline.json",
          "gap_baseline" in CONFIG)
    # And  the placeholder entry only matches elided/masked values
    for pattern in re.findall(r"'''(.*?)'''", CONFIG):
        if "TOKEN" in pattern or "KEY" in pattern:
            check(f"config: placeholder pattern is elided, not a value: {pattern[:40]}",
                  "<" in pattern or r"\*\*\*" in pattern, pattern)


def main() -> int:
    print("secret scan: wiring + config")
    test_targets_exist_and_are_pinned()
    test_history_scan_refuses_a_worktree()
    test_ci_runs_the_scan_and_its_self_test()
    test_config_only_narrows_documented_placeholders()
    test_probe_file_is_not_itself_a_leak()
    test_config_allowlists_are_justified_by_the_repo()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
