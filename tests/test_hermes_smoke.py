#!/usr/bin/env python3
"""scripts/hermes_smoke.sh — routing smoke must test ROUTING, not obedience.

qa-validate on master (run 36948427364) failed because deepseek answered the
old 'Reply with exactly the word PONG' prompt with "No. I'm an AI assistant,
not a ping-pong game ..." — the key, alias and provider were all fine. The
same smoke gates every 20-minute refresh search leg, so a false negative
kills real work. A stub `hermes` plays scripted replies.

  - refusal / any real answer, exit 0      -> OK
  - HF mis-route (exit 1, 'rejected your API key ... HTTP 403') -> FAIL
  - exit 0 but a provider-error signature  -> FAIL
  - empty reply / reasoning burned budget  -> FAIL
  - first attempt fails, second answers    -> OK on attempt 2
  - hang past the timeout                  -> FAIL (timeout)
  - NOUS_API_KEY unset                     -> SKIP, exit 0
  - Makefile _hermes-smoke delegates to the script (one implementation)

Run:  python3 tests/test_hermes_smoke.py   or   make test
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SMOKE = ROOT / "scripts" / "hermes_smoke.sh"
REFUSAL = "No. I'm an AI assistant, not a ping-pong game. But let me help with whatever you actually need."
HF_403 = ("Hugging Face rejected your API key, so the model can't be reached.\n"
          "Provider said: HTTP 403: {\"error\":\"insufficient permissions\"}")

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


def run(replies, key="sk-test", timeout="5", sleep=0):
    """replies: list of (stdout, exit_code) consumed one per hermes call."""
    td = Path(tempfile.mkdtemp())
    for i, (out, rc) in enumerate(replies):
        (td / f"out{i}").write_text(out)
        (td / f"rc{i}").write_text(str(rc))
    (td / "n").write_text("0")
    stub = td / "hermes"
    stub.write_text(f"""#!/usr/bin/env bash
d="{td}"; n=$(cat "$d/n"); echo $((n+1)) > "$d/n"
sleep {sleep}
cat "$d/out$n" 2>/dev/null; exit $(cat "$d/rc$n" 2>/dev/null || echo 0)
""")
    stub.chmod(0o755)
    env = dict(os.environ, HERMES=str(stub), HERMES_SMOKE_TIMEOUT=timeout)
    env.pop("NOUS_API_KEY", None)
    if key:
        env["NOUS_API_KEY"] = key
    p = subprocess.run(["bash", str(SMOKE)], env=env, capture_output=True, text=True, timeout=60)
    calls = int((td / "n").read_text())
    shutil.rmtree(td)
    return p.returncode, p.stdout, calls


def test_refusal_is_ok():
    rc, out, calls = run([(REFUSAL, 0)])
    check("refusal text (the real CI false negative) -> OK", rc == 0 and "OK" in out, out[-200:])
    check("refusal: one call, no retry", calls == 1, calls)


def test_hf_misroute_fails():
    rc, out, calls = run([(HF_403, 1), (HF_403, 1)])
    check("HF mis-route (exit 1, 403) -> FAIL", rc == 1 and "FAIL" in out, out[-200:])
    check("HF mis-route: retried once (2 calls)", calls == 2, calls)


def test_provider_error_with_exit_zero_fails():
    rc, out, _ = run([("Provider said: HTTP 401: invalid key", 0)] * 2)
    check("exit 0 + 'Provider said: HTTP 401' -> FAIL", rc == 1 and "provider failure" in out, out[-200:])


def test_empty_and_budget_burn_fail():
    rc, out, _ = run([("", 0), ("   \n", 0)])
    check("empty reply -> FAIL", rc == 1 and "empty reply" in out, out[-200:])
    burn = "⚠️ **No visible answer was produced.** The model hit its output-token limit"
    rc, out, _ = run([(burn, 0)] * 2)
    check("reasoning burned the budget -> FAIL", rc == 1, out[-200:])


def test_retry_recovers():
    rc, out, calls = run([("Provider said: HTTP 503", 1), ("Received, thanks.", 0)])
    check("transient failure then answer -> OK on attempt 2", rc == 0 and "attempt 2" in out and calls == 2, out[-200:])


def test_timeout_fails():
    rc, out, _ = run([("late", 0), ("late", 0)], timeout="1", sleep=3)
    check("hang past timeout -> FAIL (timeout)", rc == 1 and "timeout" in out, out[-200:])


def test_skip_without_key():
    rc, out, calls = run([(REFUSAL, 0)], key="")
    check("no NOUS_API_KEY -> SKIP exit 0, hermes never called", rc == 0 and "SKIP" in out and calls == 0, out)


def test_makefile_delegates():
    mk = (ROOT / "Makefile").read_text()
    body = mk[mk.index("_hermes-smoke:\n"):].split("\n\n", 1)[0]
    check("Makefile _hermes-smoke runs scripts/hermes_smoke.sh", "scripts/hermes_smoke.sh" in body, body)
    check("Makefile _hermes-smoke no longer greps for PONG", "PONG" not in body, body)


def main() -> int:
    if not shutil.which("bash") or not shutil.which("timeout"):
        print("SKIP: bash/timeout not available")
        return 0
    print("hermes routing smoke (scripts/hermes_smoke.sh)")
    test_refusal_is_ok()
    test_hf_misroute_fails()
    test_provider_error_with_exit_zero_fails()
    test_empty_and_budget_burn_fail()
    test_retry_recovers()
    test_timeout_fails()
    test_skip_without_key()
    test_makefile_delegates()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
