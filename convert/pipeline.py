"""Register converters here when adding a new benchmark folder."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from .chembench import convert_chembench
from .common import CANARY, canonical_property, infer_task_family
from .numeric import (
    convert_opc25,
    convert_openmaterials,
    convert_openpoly,
    convert_polyagent,
    convert_polymetrix,
)
from .polyreal import convert_polyreal
from .pareto_reaction import convert_pareto_greedy_reaction

# 2. source directory map
SOURCE_DIRS = {
    "PolyReal": "polyreal",
    "ChemBench": "chembench",
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


def item_family(item: dict) -> str:
    return infer_task_family(str(item.get("category") or ""), str(item.get("source") or ""))


def item_property(item: dict) -> str:
    subfield = str(item.get("subfield") or "")
    return canonical_property(re.sub(r"^Held-out\s+", "", subfield, flags=re.I))


def write_task_views(items: list[dict], out_dir: Path) -> dict[str, str]:
    views: dict[str, str] = {}
    families = sorted({item_family(item) for item in items})
    for family in families:
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", family).lower()
        name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
        dest = out_dir / f"tasks_{name}.json"
        dest.write_text(json.dumps({"tasks": [
            item for item in items if item_family(item) == family
        ]}, ensure_ascii=False, indent=2), encoding="utf-8")
        views[family] = str(dest)
    for difficulty in range(1, 5):
        selected = [item for item in items if item.get("difficulty") == difficulty]
        if not selected:
            continue
        dest = out_dir / f"tasks_level_{difficulty}.json"
        dest.write_text(json.dumps({"tasks": selected}, ensure_ascii=False, indent=2), encoding="utf-8")
        views[f"difficulty_{difficulty}"] = str(dest)
    return views


PROPERTY_PRIORITY = {
    "glass_transition_temperature": 0,
    "electron_affinity": 1,
    "bulk_bandgap": 2,
    "chain_bandgap": 3,
    "density": 4,
    "thermal_conductivity": 5,
    "refractive_index": 6,
    "dielectric_constant": 7,
}


def balance_property_tasks(items: list[dict], per_item: int = 5) -> list[dict]:
    grouped: dict[tuple[str, str], list[tuple[int, dict]]] = {}
    for index, item in enumerate(items):
        if item_family(item) != "PropertyPrediction":
            continue
        key = (str(item.get("source") or ""), str(item.get("source_id") or ""))
        grouped.setdefault(key, []).append((index, item))
    selected: set[int] = set()
    for group in grouped.values():
        ranked = sorted(
            group,
            key=lambda pair: (
                PROPERTY_PRIORITY.get(item_property(pair[1]), 99),
                pair[0],
            ),
        )
        selected.update(index for index, _ in ranked[:per_item])
    return [
        item for index, item in enumerate(items)
        if item_family(item) != "PropertyPrediction" or index in selected
    ]


def run_convert(
    raw_dir: Path,
    out_dir: Path,
    prop_limit: int = 80,
    holdout_frac: float = 0.25,
    chembench_all: bool = False,
    include_openmaterials_nonpolymer: bool = False,
    llm_enrich: bool = False,
    llm_limit: int = 100,
    llm_model: str | None = None,
    property_tasks_per_item: int = 5,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    converters = [
        ("PolyReal", lambda: convert_polyreal(raw_dir)),
        ("ChemBench", lambda: convert_chembench(raw_dir, polymer_only=not chembench_all)),
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
    before_property_balance = len(items)
    items = balance_property_tasks(items, property_tasks_per_item)
    llm_enriched = 0
    if llm_enrich:
        from .llm_aux import enrich_tasks

        llm_enriched = enrich_tasks(items, limit=llm_limit, model=llm_model)
    views = write_task_views(items, out_dir)
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
        "n_before_property_balance": before_property_balance,
        "by_source": dict(Counter(x["source"] for x in items)),
        "by_category": dict(Counter(x["category"] for x in items)),
        "by_answer_type": dict(Counter(x["answer_type"] for x in items)),
        "by_task_family": dict(Counter(item_family(x) for x in items)),
        "by_difficulty": dict(Counter(str(x["difficulty"]) for x in items)),
        "converter_yield": status,
        "llm_enriched": llm_enriched,
        "property_tasks_per_item": property_tasks_per_item,
        "views": views,
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
    parser.add_argument("--holdout-frac", type=float, default=0.1)
    parser.add_argument("--chembench-all", action="store_true")
    parser.add_argument("--include-openmaterials-nonpolymer", action="store_true")
    parser.add_argument("--llm-enrich", action="store_true")
    parser.add_argument("--llm-limit", type=int, default=100)
    parser.add_argument("--llm-model", type=str, default=None)
    parser.add_argument("--property-tasks-per-item", type=int, default=5)
    args = parser.parse_args()
    run_convert(
        args.raw_dir,
        args.out_dir,
        args.prop_limit,
        args.holdout_frac,
        args.chembench_all,
        args.include_openmaterials_nonpolymer,
        args.llm_enrich,
        args.llm_limit,
        args.llm_model,
        args.property_tasks_per_item,
    )


if __name__ == "__main__":
    main()
