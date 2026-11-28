#!/usr/bin/env python3
"""Additive DGX-Spark clarification on the two qwen3.6-35b-a3b rows (issue #1868).

Real-file guard (rule 6m): reads the REAL shipped store (data/measurements.json,
models.json, posts.json) and drives the REAL measurement_backend() from
update_trending with the store's OWN engines registry. No stand-ins, no
monkeypatch and no mocked business logic. It asserts:

  * both target rows preserve the ORIGINAL hardware string verbatim as a
    substring (rule-3b additive-only: append, never replace or shrink);
  * the appended clarification names the NVIDIA DGX Spark (GB10) and cites the
    sibling post whose rows carry the identical figures;
  * EVERY other measurement value in the whole store is byte-for-byte the
    base value (a digest with only these two hardware fields normalised), and
    neither sibling store file moved;
  * the two rows' other fields are unchanged;
  * both rows still classify CUDA (PR #1867's guard stays green).

RED on base 3c00bf44 (no clarification), GREEN on the head that appends it.

Run:  python3 tests/test_dgx_spark_hardware_clarification_1868.py   or   make test
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import update_trending as UT  # noqa: E402

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


# The exact original hardware text (must survive verbatim as a substring).
ORIGINAL = "Radeon 8060S / Strix Halo 128GB (ASUS Ascent GX10, GB10)"
MODEL = "qwen3.6-35b-a3b"
TARGETS = [("Ollama", "87.2"), ("Magnitude", "188.9")]

# The appended, evidence-bearing clarification.
NVIDIA_TOKEN = "NVIDIA DGX Spark (GB10)"
SIBLING_POST = "niklaslenz_ai/status/2111204284453044383"
SIBLING_LABEL = "NVIDIA DGX Spark (one)"

# Pinned from the untouched base 3c00bf44: a digest of the WHOLE measurements
# store with ONLY these two hardware fields normalised to a placeholder, so it
# is identical on base and on the corrected head. Any other value change moves
# it and reddens the guard.
EXPECTED_OTHERS_DIGEST = "d574b5b9e389936a121f448901f4ef9fbec345e8980ab7317f6e351a19853598"
EXPECTED_MODELS_DIGEST = "fc5abc2d224f515ac553f9ddf5384f0771ef4a529553fc6fcddec853aad5b220"
EXPECTED_POSTS_DIGEST = "d5a76e3b0bcd9d115d7fbc0c65fe22f795bdb654bda7f27e4b41cbd6aeaf9877"

# Every non-hardware field of the two rows, pinned from base.
EXPECTED_FIELDS = {
    ("Ollama", "87.2"): {
        "engine": "Ollama",
        "tps": "87.2",
        "quant": "Ollama 0.40.5 registry tag (Q4_K_M with built-in MTP), f16 KV cache; repeat-a-passage round at a 66K-token prompt, median of 3 runs, thinking off; new-story round on the same box 63.4 tok/s (Magnitude 50.4); prefill 1,834 tok/s which is prompt processing, never the decode figure",
        "weight_gb": "Q4_K_M (Ollama registry tag)",
        "context_tokens": "67584",
        "date": "2026-10-16",
        "source_post": "https://lightbrd.com/niklaslenz_ai/status/2111621869157044461",
        "engine_min_version": "Ollama 0.40.5",
    },
    ("Magnitude", "188.9"): {
        "engine": "Magnitude",
        "tps": "188.9",
        "quant": "Magnitude 0.2.9 with its DFlash drafter and quantized KV cache, unsloth UD-Q4_K_XL on the repeat-a-passage round at a 66K-token prompt (75% drafter acceptance); new-story round 50.4 tok/s at 43% acceptance; prefill 2,332 tok/s",
        "weight_gb": "UD-Q4_K_XL",
        "context_tokens": "67584",
        "system_ram_min": "128GB",
        "date": "2026-10-16",
        "source_post": "https://lightbrd.com/niklaslenz_ai/status/2111621869157044461",
    },
}


def load_measurements() -> dict:
    return json.loads((ROOT / "data" / "measurements.json").read_text())


def target_rows(d: dict) -> dict:
    """The two rows, keyed by (engine, tps), selected without reading hardware
    equality so a head that appends text is still found."""
    out = {}
    for mid, rows in d.items():
        for e in rows:
            if mid == MODEL and (e.get("engine"), e.get("tps")) in TARGETS:
                if ORIGINAL in (e.get("hardware") or ""):
                    out[(e.get("engine"), e.get("tps"))] = e
    return out


def others_digest(d: dict) -> tuple[str, int]:
    clone = json.loads(json.dumps(d))
    normalised = 0
    for mid, rows in clone.items():
        for e in rows:
            if (mid == MODEL
                    and (e.get("engine"), e.get("tps")) in TARGETS
                    and ORIGINAL in (e.get("hardware") or "")):
                e["hardware"] = "<CLARIFIED>"
                normalised += 1
    blob = json.dumps(clone, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest(), normalised


def real_store() -> dict:
    d = ROOT / "data"
    return UT.flatten_store(json.loads((d / "models.json").read_text()),
                            json.loads((d / "measurements.json").read_text()),
                            json.loads((d / "posts.json").read_text()))


def test_original_hardware_text_preserved_verbatim():
    rows = target_rows(load_measurements())
    check("both target rows found", len(rows) == 2, sorted(rows))
    for key in TARGETS:
        e = rows.get(key)
        check(f"{key}: original hardware text preserved verbatim",
              e is not None and ORIGINAL in e.get("hardware", ""),
              e and e.get("hardware"))


def test_clarification_is_additive_and_names_dgx_spark():
    rows = target_rows(load_measurements())
    for key in TARGETS:
        e = rows.get(key)
        if e is None:
            check(f"{key}: row present", False)
            continue
        hw = e.get("hardware", "")
        check(f"{key}: append-only (original is a leading substring)",
              hw.startswith(ORIGINAL), hw)
        check(f"{key}: clarification names the NVIDIA DGX Spark (GB10)",
              NVIDIA_TOKEN in hw, hw)
        check(f"{key}: cites sibling post {SIBLING_POST}", SIBLING_POST in hw, hw)
        check(f"{key}: cites sibling label '{SIBLING_LABEL}'", SIBLING_LABEL in hw, hw)


def test_no_other_measurement_value_changed_anywhere():
    digest, n = others_digest(load_measurements())
    check("exactly two hardware fields normalised", n == 2, n)
    check("every other measurement value is the base value",
          digest == EXPECTED_OTHERS_DIGEST,
          f"expected={EXPECTED_OTHERS_DIGEST} got={digest}")
    for name, expected in (("models.json", EXPECTED_MODELS_DIGEST),
                           ("posts.json", EXPECTED_POSTS_DIGEST)):
        got = hashlib.sha256((ROOT / "data" / name).read_bytes()).hexdigest()
        check(f"{name} unchanged", got == expected,
              f"expected={expected} got={got}")


def test_the_two_rows_other_fields_unchanged():
    rows = target_rows(load_measurements())
    for key, expected in EXPECTED_FIELDS.items():
        e = rows.get(key)
        check(f"{key}: non-hardware fields unchanged",
              e is not None and all(e.get(k) == v for k, v in expected.items()),
              e)


def test_rows_still_classify_cuda():
    s = real_store()
    reg = s.get("engines", {})
    rows = {(m["id"], e.get("engine"), str(e.get("tps")), e.get("hardware")): e
            for m in s["models"] for e in m.get("engines", [])}
    for eng, tps in TARGETS:
        hits = [e for (mid, ee, tt, hw), e in rows.items()
                if mid == MODEL and ee == eng and tt == tps
                and ORIGINAL in (hw or "")]
        check(f"{eng}/{tps}: real store row present", len(hits) == 1, len(hits))
        if hits:
            got = UT.measurement_backend(hits[0], reg)
            check(f"{eng}/{tps}: classifies CUDA (PR #1867 stays green)",
                  got == "CUDA", got)


def main() -> int:
    print("Additive DGX-Spark hardware clarification, two qwen3.6-35b-a3b rows (#1868)")
    test_original_hardware_text_preserved_verbatim()
    test_clarification_is_additive_and_names_dgx_spark()
    test_no_other_measurement_value_changed_anywhere()
    test_the_two_rows_other_fields_unchanged()
    test_rows_still_classify_cuda()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
