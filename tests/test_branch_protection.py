#!/usr/bin/env python3
"""Regression guard for Rule 1's mechanical guard (issue #959).

master had ZERO branch protection and direct pushes landed on 2026-11-14
(e571aa3, 4c7c555) because "never push master" was only a convention. This
suite runs the REAL guard (scripts/check_branch_protection.py) end to end:

  1. a recorded, correctly protected master (strict, validate + live-smoke
     contexts — bare or `workflow / job` — enforce_admins) passes;
  2. a relaxed protection is refused, naming each gap (non-strict, a dropped
     context, enforce_admins false);
  3. an absent protection (GitHub's 404 body) is refused;
  4. an unreadable payload is LOUD (exit 2), never a silent clean;
  5. the guard is wired: the Makefile defines `check-branch-protection`, its
     recipe is the only path to the script, and queued-alarm.yml runs the make
     target in a job that needs the guard.

No mocks of the product (rule 6m): the pure verdict runs on real payloads, the
CLI runs as a real subprocess over recorded fixture files, and the live half is
the real `gh` client — exercised here only through the recorded-payload seam.

Run standalone: python3 tests/test_branch_protection.py   or   make test
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_branch_protection as b  # noqa: E402

_PASS = 0
_FAIL = 0


def check(name: str, cond: bool, detail: str = ""):
    global _PASS, _FAIL
    if cond:
        _PASS += 1
        print(f"  ok  {name}")
    else:
        _FAIL += 1
        print(f"  FAIL {name} {detail}")


def _run_cli(payload_text: str = "", path: str = ""):
    """Run the REAL script as a subprocess against a recorded payload file."""
    if not path:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        tmp.write(payload_text)
        tmp.close()
        path = tmp.name
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_branch_protection.py"), "--from-file", path],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


# The recorded shape (openspec/changes/master-push-guard-959/proposal.md).
CORRECT = {
    "required_status_checks": {
        "strict": True,
        "contexts": ["qa-validate / validate", "qa-validate / live-smoke"],
    },
    "enforce_admins": {"url": "x", "enabled": True},
    "required_pull_request_reviews": None,
    "restrictions": None,
}
# GitHub's live protection body nests these under their own objects; the guard
# must accept BOTH the live body and the flat PUT shape. Normalize via verdict
# inputs that mirror what `gh api …/protection` returns.
CORRECT_LIVE = {
    "required_status_checks": {"strict": True, "contexts": ["validate", "live-smoke"]},
    "enforce_admins": True,
}


def test_a_correctly_protected_master_passes():
    check("verdict: the recorded workflow-prefixed shape has no problems", b.verdict(CORRECT) == [], b.verdict(CORRECT))
    check("verdict: the bare-context shape has no problems", b.verdict(CORRECT_LIVE) == [], b.verdict(CORRECT_LIVE))
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tmp:
        json.dump(CORRECT_LIVE, tmp)
        path = tmp.name
    rc, out = _run_cli(path=path)
    check("cli: exit 0 on the protected shape", rc == 0, f"rc={rc} {out}")
    check("cli: prints the verified shape", "strict=True" in out and "enforce_admins=True" in out, out)


def test_a_relaxed_protection_is_refused():
    shapes = {
        "non-strict": {**CORRECT_LIVE, "required_status_checks": {"strict": False, "contexts": ["validate", "live-smoke"]}},
        "dropped live-smoke": {**CORRECT_LIVE, "required_status_checks": {"strict": True, "contexts": ["validate"]}},
        "admins-allowed": {**CORRECT_LIVE, "enforce_admins": False},
        "no required checks": {"required_status_checks": None, "enforce_admins": True},
    }
    for label, shape in shapes.items():
        problems = b.verdict(shape)
        check(f"verdict: {label} is a problem", bool(problems), problems)
    rc, out = _run_cli(json.dumps(shapes["dropped live-smoke"]))
    check("cli: exit 1 on a dropped required context", rc == 1, f"rc={rc}")
    check("cli: the refusal names the dropped context", "live-smoke" in out, out)
    rc, out = _run_cli(json.dumps(shapes["admins-allowed"]))
    check("cli: exit 1 when admins could still push", rc == 1 and "enforce_admins" in out, f"rc={rc} {out}")


def test_an_absent_protection_is_refused():
    rc, out = _run_cli(json.dumps({"status": "404", "message": "Branch not protected"}))
    check("cli: exit 1 when GitHub answers 404", rc == 1, f"rc={rc}")
    check("cli: says the branch is unguarded", "no branch protection" in out, out)


def test_an_unreadable_payload_is_loud():
    rc, out = _run_cli("{not json")
    check("cli: malformed payload exits 2", rc == 2, f"rc={rc}")
    check("cli: a broken read is never a pass", "UNREADABLE" in out and "OK" not in out, out)
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_branch_protection.py")],
                          capture_output=True, text=True)
    check("cli: no repo and no fixture is a usage refusal (2)", proc.returncode == 2, proc.stdout + proc.stderr)


def test_the_guard_is_wired_through_make_and_queued_alarm():
    mk = (ROOT / "Makefile").read_text()
    check("makefile: public target exists", "\ncheck-branch-protection: ##" in mk)
    check("makefile: internal recipe is the only path to the script",
          "_check-branch-protection:\n\tpython3 scripts/check_branch_protection.py" in mk)
    check("makefile: the public target delegates through make",
          "@$(MAKE) --no-print-directory _check-branch-protection" in mk)
    wf = (ROOT / ".github" / "workflows" / "queued-alarm.yml").read_text()
    check("queued-alarm: the sweep calls the target through make",
          "make check-branch-protection REPO=" in wf)
    alarm_section = wf.split("  alarm:")[1]
    check("queued-alarm: the step lives in the job that needs the guard",
          "needs: guard" in alarm_section.split("\n  ")[0] or "    needs: guard" in alarm_section[:200])
    check("queued-alarm: the protection read uses the owner PAT (the default token cannot read it)",
          "FIXBOT_DISPATCH_TOKEN" in alarm_section.split("check-branch-protection")[0][-600:])
    # Rule 6m: no workflow step may reach the script without make.
    check("queued-alarm: no step reaches scripts/check_branch_protection.py directly",
          "scripts/check_branch_protection.py" not in wf)


def main() -> int:
    test_a_correctly_protected_master_passes()
    test_a_relaxed_protection_is_refused()
    test_an_absent_protection_is_refused()
    test_an_unreadable_payload_is_loud()
    test_the_guard_is_wired_through_make_and_queued_alarm()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
