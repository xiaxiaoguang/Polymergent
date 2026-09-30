"""Register converters here when adding a new benchmark folder."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from .chembench import convert_chembench
from .common import CANARY
from .numeric import (
    convert_opc25,
    convert_openmaterials,
    convert_openpoly,
    convert_point2_tg,
    convert_polyagent,
    convert_polymetrix,
)
from .polyreal import convert_polyreal
from .pareto_reaction import convert_pareto_greedy_reaction

# 2. source directory map
SOURCE_DIRS = {
    "PolyReal": "polyreal",
    "ChemBench": "chembench",
    "POINT2_Tg": "point2",
    "PolymerAgent": "polyagent",
    "OPC25": "opc25",
    "PolyMetriX": "polymetrix",
    "OpenPoly": "openpoly",
    "OpenMaterials": "openmaterials",
    "ParetoGreedyReaction": "pareto_greedy_reaction",
}

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "raw"
DEFAULT_OUT = ROOT / "polymer"
print(DEFAULT_RAW)
SOURCE_DIRS = {
    "PolyReal": "polyreal",
    "ChemBench": "chembench",
    "POINT2_Tg": "point2",
    "PolymerAgent": "polyagent",
    "OPC25": "opc25",
    "PolyMetriX": "polymetrix",
    "OpenPoly": "openpoly",
    "OpenMaterials": "openmaterials",
}


def dedupe(items: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    out = []
    for row in items:
        q = re.sub(r"\s+", " ", row.get("question") or "").strip().lower()
        key = (str(row.get("source") or ""), q[:300])
        if not q or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def run_convert(
    raw_dir: Path,
    out_dir: Path,
    prop_limit: int = 80,
    holdout_frac: float = 0.25,
    chembench_all: bool = False,
    include_openmaterials_nonpolymer: bool = False,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    converters = [
        ("PolyReal", lambda: convert_polyreal(raw_dir)),
        ("ChemBench", lambda: convert_chembench(raw_dir, polymer_only=not chembench_all)),
        ("POINT2_Tg", lambda: convert_point2_tg(raw_dir, prop_limit, holdout_frac)),
        ("PolymerAgent", lambda: convert_polyagent(raw_dir, prop_limit, holdout_frac)),
        ("OPC25", lambda: convert_opc25(raw_dir, prop_limit, holdout_frac)),
        ("PolyMetriX", lambda: convert_polymetrix(raw_dir, prop_limit, holdout_frac)),
        ("OpenPoly", lambda: convert_openpoly(raw_dir, prop_limit, holdout_frac)),
        (
            "OpenMaterials",
            lambda: convert_openmaterials(
                raw_dir, prop_limit, holdout_frac, polymer_only=not include_openmaterials_nonpolymer
            ),
        ),
        (
            "ParetoGreedyReaction",
            lambda: convert_pareto_greedy_reaction(raw_dir, holdout_frac=holdout_frac),
        ),
    ]

    bundles: list[list[dict]] = []
    status: dict[str, int] = {}
    for name, fn in converters:
        try:
            rows = fn()
        except Exception as exc:
            print(f"{name}: ERROR {type(exc).__name__}: {exc}")
            status[name] = 0
            continue
        status[name] = len(rows)
        present = (raw_dir / SOURCE_DIRS[name]).exists()
        if not rows and not present:
            print(f"{name}: skip (missing raw files)")
        else:
            print(f"{name}: {len(rows)}")
        if rows:
            bundles.append(rows)
    items = dedupe([row for bundle in bundles for row in bundle])
    dest = out_dir / "external_tasks.json"
    dest.write_text(
        json.dumps(
            {
                "canary": CANARY,
                "description": "Converted external polymer evaluation items.",
                "version": "0.3.0",
                "tasks": items,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    manifest = {
        "n_total": len(items),
        "n_before_dedupe": sum(len(b) for b in bundles),
        "by_source": dict(Counter(x["source"] for x in items)),
        "by_category": dict(Counter(x["category"] for x in items)),
        "by_answer_type": dict(Counter(x["answer_type"] for x in items)),
        "converter_yield": status,
        "polyreal_text_only": sum(1 for x in items if x["source"] == "PolyReal" and not x.get("mm")),
        "polyreal_multimodal": sum(1 for x in items if x["source"] == "PolyReal" and x.get("mm")),
        "prop_limit": prop_limit,
        "holdout_frac": holdout_frac,
        "output": str(dest),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert raw polymer corpora into external_tasks.json")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--prop-limit", type=int, default=80)
    parser.add_argument("--holdout-frac", type=float, default=0.25)
    parser.add_argument("--chembench-all", action="store_true")
    parser.add_argument("--include-openmaterials-nonpolymer", action="store_true")
    args = parser.parse_args()
    run_convert(
        args.raw_dir,
        args.out_dir,
        args.prop_limit,
        args.holdout_frac,
        args.chembench_all,
        args.include_openmaterials_nonpolymer,
    )


if __name__ == "__main__":
    main()
