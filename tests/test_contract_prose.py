#!/usr/bin/env python3
"""The contract <-> prose seam's own tests (issue #1394, slice A of #691).

`data/MODEL_CONTRACT.md` summarises `data/model_contract.json` and had no owner,
so it drifted silently: 21 rows against 23 schema properties, and the `hf`/`engines`
rows said required while the schema did not require them. These tests drive the
REAL seam (`scripts/check_contract_prose.py`) over REAL files — the shipped pair
in this tree and planted fixture pairs in a temp dir. No mock replaces the
business logic (rule 6m): every failure mode below is a real drift the real
parser reports.

Covers, 1:1 with the issue's acceptance:
  * test_a_schema_property_without_a_prose_row_is_red
  * test_required_disagreement_is_red_in_both_directions
  * test_the_real_store_and_contract_are_green
  * test_the_check_is_wired_to_a_stage_and_a_target

Run:  python3 tests/test_contract_prose.py   or   make test
"""
from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_contract_prose.py"
sys.path.insert(0, str(ROOT / "scripts"))

import check_contract_prose as cp  # noqa: E402

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


def shipped_schema() -> dict:
    return json.loads((ROOT / "data" / "model_contract.json").read_text())


def shipped_markdown() -> str:
    return (ROOT / "data" / "MODEL_CONTRACT.md").read_text()


def fixture(schema: dict, markdown: str) -> tuple[Path, Path]:
    """A real contract/prose pair on disk (a temp data dir), never an in-memory fake."""
    td = Path(tempfile.mkdtemp())
    cpath = td / "model_contract.json"
    mpath = td / "MODEL_CONTRACT.md"
    cpath.write_text(json.dumps(schema))
    mpath.write_text(markdown)
    return cpath, mpath


# --------------------------------------------------------------------------- 1


def test_a_schema_property_without_a_prose_row_is_red():
    """Acceptance 1: a schema property with no MD row FAILS naming the property."""
    items = cp.model_items(shipped_schema())
    dropped = next(p for p in ("vram_tier", "last_seen") if p in items)
    schema = copy.deepcopy(shipped_schema())
    del schema["properties"]["models"]["items"]["properties"][dropped]
    cpath, mpath = fixture(schema, shipped_markdown())

    found = cp.check(cpath.parent, cpath, mpath)

    check("missing-row: the check is red", len(found) >= 1, str(found))
    line = next((l for l in found if dropped in l), "")
    check("missing-row: it names the property", bool(line), str(found))
    check("missing-row: it says the schema declares it while the prose does not",
          "NO row" in line or "does NOT declare" in line, line)

    # The reverse — a row the schema does not declare — is also a hard fail.
    md = shipped_markdown().replace("| `last_seen` | yes |",
                                    "| `last_seen` | yes |\n| `ghost_field` | no |")
    cpath, mpath = fixture(shipped_schema(), md)
    found = cp.check(cpath.parent, cpath, mpath)
    check("unknown-row: prose naming an undeclared property is red", len(found) == 1, found)
    check("unknown-row: it names the unknown row", "ghost_field" in found[0], found[0])


# --------------------------------------------------------------------------- 2


def test_required_disagreement_is_red_in_both_directions():
    """Acceptance 2: a Required cell that disagrees with the schema FAILS naming both sides."""
    schema = shipped_schema()
    required = set(schema["properties"]["models"]["items"]["required"])

    # Direction A — the schema REQUIRES a field the prose marks optional.
    optional_on_paper = next(p for p in ("weight_gb", "context_tokens", "system_ram_min")
                             if p not in required)
    grown = copy.deepcopy(schema)
    grown["properties"]["models"]["items"]["required"].append(optional_on_paper)
    cpath, mpath = fixture(grown, shipped_markdown())
    found = cp.check(cpath.parent, cpath, mpath)
    line = next((l for l in found if optional_on_paper in l), "")
    check("required A: prose says no, schema requires -> red naming both",
          len(found) == 1 and optional_on_paper in line and "REQUIRES it" in line, found)

    # Direction B — the prose marks a field required that the schema does not.
    not_required = next(p for p in ("hf", "engines", "engine_aliases") if p not in required)
    md = shipped_markdown().replace(f"| `{not_required}` | no |", f"| `{not_required}` | yes |")
    cpath, mpath = fixture(schema, md)
    found = cp.check(cpath.parent, cpath, mpath)
    line = next((l for l in found if not_required in l), "")
    check("required B: prose says yes, schema does not require -> red naming both",
          len(found) == 1 and not_required in line and "does NOT require it" in line, found)

    # A cell that is neither yes nor no is refused rather than read as drift.
    md = shipped_markdown().replace("| `last_seen` | yes |", "| `last_seen` | sometimes |")
    cpath, mpath = fixture(schema, md)
    found = cp.check(cpath.parent, cpath, mpath)
    check("vocabulary: an unreadable Required cell is red", len(found) == 1
          and "sometimes" in found[0] and "not one of" in found[0], found)


# --------------------------------------------------------------------------- 3


def test_the_real_store_and_contract_are_green():
    """Acceptance 3: the SHIPPED tree passes — the real store and the fixed prose agree."""
    cpath, mpath = fixture(shipped_schema(), shipped_markdown())
    found = cp.check(cpath.parent, cpath, mpath)
    items = cp.model_items(shipped_schema())
    rows = cp.parse_rows(shipped_markdown())

    check("real-tree: the shipped contract/prose pair is green", found == [], found)
    check("real-tree: every schema property has a row", set(items) <= set(rows),
          sorted(set(items) - set(rows)))
    check("real-tree: the two added keys now have rows",
          {"engine_aliases", "measurement_model_aliases"} <= set(rows), sorted(rows))
    check("real-tree: the corrected required cells match the schema",
          all(cp._REQUIRED[rows[p].lower()] == items[p] for p in items), "a cell still disagrees")

    # And the real CLI prints the property/row counts, exit 0 on the real tree.
    out = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, cwd=ROOT)
    check("cli: the real tree exits 0", out.returncode == 0, out.stdout + out.stderr)
    check("cli: it prints the property count", f"{len(items)} properties" in out.stdout,
          out.stdout.strip())
    check("cli: it prints the row count", f"{len(rows)} rows" in out.stdout,
          out.stdout.strip())

    # An undecidable read is a finding, never a vacuous clean.
    with tempfile.TemporaryDirectory() as td:
        empty = Path(td)
        found = cp.check(empty, empty / "model_contract.json", empty / "MODEL_CONTRACT.md")
        check("undecidable: a missing contract is a finding, not a pass",
              len(found) == 1 and "cannot read" in found[0], found)


# --------------------------------------------------------------------------- 4


def test_the_check_is_wired_to_a_stage_and_a_target():
    """Acceptance 4: `docs` is a registered stage AND selected by a Makefile `--only` list."""
    tree = ast.parse((ROOT / "scripts" / "validate.py").read_text())
    main_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
    stages: dict[str, str] = {}
    for node in ast.walk(main_fn):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "add" and len(node.args) >= 2):
            continue
        if isinstance(node.args[0], ast.Constant) and isinstance(node.args[1], ast.Constant):
            stages[str(node.args[1].value)] = stages.get(str(node.args[1].value), "") \
                + " " + ast.unparse(node.args[2])
    check("wiring: stage `docs` is registered", "docs" in stages, sorted(stages))
    check("wiring: the docs stage runs check_contract_prose",
          "check_contract_prose()" in stages.get("docs", ""), stages.get("docs"))

    # The same reader `tests/test_validate.py` uses — no second spelling (rule 6d).
    from architecture_check import stage_lists, validate_stages
    check("wiring: the validator's own stage map lists `docs`",
          "docs" in validate_stages(ROOT / "scripts" / "validate.py"),
          sorted(validate_stages(ROOT / "scripts" / "validate.py")))
    lists = stage_lists(ROOT / "Makefile")
    selects = [t for t, ss in lists if "docs" in ss]
    check("wiring: a Makefile --only list selects `docs`", selects == ["_validate-schema"], selects)
    check("wiring: the full `_validate` target runs every stage (no --only)",
          "_validate:\n\tpython3 scripts/validate.py\n" in (ROOT / "Makefile").read_text(),
          "the all-run recipe changed")

    # The call path really executes it.
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate.py"), "--only", "docs"],
                         capture_output=True, text=True, cwd=ROOT)
    check("wiring: --only docs executes the contract<->prose check",
          "contract <-> prose sync" in out.stdout, out.stdout[-300:])
    check("wiring: --only docs is green on the real tree", out.returncode == 0,
          out.stdout + out.stderr)


def main() -> int:
    print("contract-prose: direct unit tests")
    test_a_schema_property_without_a_prose_row_is_red()
    test_required_disagreement_is_red_in_both_directions()
    test_the_real_store_and_contract_are_green()
    test_the_check_is_wired_to_a_stage_and_a_target()
    print(f"\nPASSED {_PASS} | FAILED {_FAIL}")
    return 1 if _FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
