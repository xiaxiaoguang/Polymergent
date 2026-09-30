"""SMILES + property table converters (PolyAgent, OPC25, PolyMetriX, OpenPoly, POINT2, OpenMaterials)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .common import (
    POLYMER_RE,
    as_list,
    as_str,
    guess_id_col,
    guess_smiles_col,
    iter_files,
    make_task,
    numeric_cols,
    numeric_tasks,
    read_table,
    slug,
)

POLYAGENT_SPEC: dict[str, tuple[str, str, str]] = {
    "Egb": ("bulk_bandgap", "eV", "bulk bandgap"),
    "Eea": ("electron_affinity", "eV", "electron affinity"),
    "EPS": ("dielectric_constant", "dimensionless", "dielectric constant"),
    "Xc": ("crystallization_tendency", "percent", "crystallization tendency"),
    "Ei": ("ionization_energy", "eV", "ionization energy"),
    "Nc": ("refractive_index", "dimensionless", "refractive index"),
    "Egc": ("chain_bandgap", "eV", "chain bandgap"),
    "PE": ("ionic_conductivity", "log10 S/cm", "ionic conductivity"),
    "OPV": ("OPV_PCE", "percent", "OPV power conversion efficiency"),
}

OPC25_PROPS: dict[str, tuple[str, str, str]] = {
    "Tg": ("glass_transition_temperature", "C", "glass transition temperature"),
    "FFV": ("fractional_free_volume", "dimensionless", "fractional free volume"),
    "Tc": ("thermal_conductivity", "W/(m·K)", "thermal conductivity"),
    "Density": ("density", "g/cm^3", "density"),
    "Rg": ("radius_of_gyration", "Å", "radius of gyration"),
}

OPENPOLY_EXCLUDED = {"id", "name", "psmiles", "reference"}


def openpoly_property_meta(column: str) -> tuple[str, str, str]:
    """Return normalized property name, unit, and display label from an OpenPoly column."""
    units = (
        ("_cm2_per_s", "cm^2/s"),
        ("_kJ_per_m2", "kJ/m^2"),
        ("_W_per_mK", "W/(m·K)"),
        ("_percentage", "percent"),
        ("_Barrer", "Barrer"),
        ("_meq_per_g", "meq/g"),
        ("_eV", "eV"),
        ("_MPa", "MPa"),
        ("_K", "K"),
    )
    for suffix, unit in units:
        if column.endswith(suffix):
            base = column[: -len(suffix)]
            return slug(base), unit, base.replace("_", " ").lower()
    return slug(column), "dimensionless", column.replace("_", " ").lower()


def convert_polyagent(raw_dir: Path, limit: int, holdout_frac: float) -> list[dict]:
    folder = raw_dir / "polyagent"
    if not folder.exists():
        return []
    rows: list[dict] = []
    for path in iter_files(folder, ("*.csv", "*.parquet")):
        stem = path.stem
        spec = POLYAGENT_SPEC.get(stem)
        df = read_table(path)
        smiles = guess_smiles_col(df) or list(df.columns)[0]
        if spec:
            prop, unit, label = spec
            value_col = next(
                (c for c in df.columns if c != smiles and pd_numeric_any(df[c])),
                None,
            )
            if value_col is None:
                continue
            rows.extend(
                numeric_tasks(
                    df, smiles, value_col, prop, unit, f"PolymerAgent_{stem}",
                    limit, holdout_frac,
                    "Polymer-Agent / TransPolymer property table converted to agent exactMatch items.",
                    label=label,
                )
            )
            continue
        for col in numeric_cols(df, {smiles}):
            rows.extend(
                numeric_tasks(
                    df, smiles, col, slug(col), "unknown", f"PolymerAgent_{stem}",
                    limit, holdout_frac,
                    "Polymer-Agent property table converted to agent exactMatch items.",
                    label=str(col),
                )
            )
    return rows


def pd_numeric_any(series) -> bool:
    import pandas as pd

    return pd.to_numeric(series, errors="coerce").notna().sum() > 0


def convert_opc25(raw_dir: Path, limit: int, holdout_frac: float) -> list[dict]:
    folder = raw_dir / "opc25"
    if not folder.exists():
        return []
    rows: list[dict] = []
    for path in iter_files(folder, ("*.csv", "*.parquet")):
        split = path.stem
        df = read_table(path)
        smiles = guess_smiles_col(df)
        if smiles is None:
            continue
        id_col = guess_id_col(df)
        known = [c for c in OPC25_PROPS if c in df.columns]
        targets = [(c, *OPC25_PROPS[c]) for c in known] or [
            (c, slug(c), "unknown", str(c)) for c in numeric_cols(df, {smiles, id_col or ""})
        ]
        source = f"OPC25_{split}"
        for value_col, prop, unit, label in targets:
            rows.extend(
                numeric_tasks(
                    df, smiles, value_col, prop, unit, source,
                    limit, holdout_frac,
                    "NeurIPS Open Polymer Prediction 2025 (OPC) leaderboard table. MIT.",
                    label=label, extra_context=f"Source split: {split}.",
                )
            )
    return rows


def convert_polymetrix(raw_dir: Path, limit: int, holdout_frac: float) -> list[dict]:
    folder = raw_dir / "polymetrix"
    if not folder.exists():
        return []
    rows: list[dict] = []
    for path in iter_files(folder, ("*.parquet", "*.csv")):
        if path.name.lower() == "manifest.json":
            continue
        df = read_table(path)
        smiles = guess_smiles_col(df)
        if smiles is None:
            smiles = next((c for c in ("PSMILES", "psmiles", "SMILES", "smiles") if c in df.columns), None)
        if smiles is None:
            continue
        tg_cols = [c for c in df.columns if re.search(r"(^tg$|tg_|glass|labels\.tg|T_g)", str(c), re.I)]
        if not tg_cols:
            tg_cols = numeric_cols(df, {smiles})
        for col in tg_cols:
            unit = "K" if re.search(r"(kelvin|_k$)", str(col), re.I) else "C"
            rows.extend(
                numeric_tasks(
                    df, smiles, col, "glass_transition_temperature", unit, "PolyMetriX",
                    limit, holdout_frac,
                    "PolyMetriX curated Tg (lamalab-org/PolyMetriX). Use the official dataset license.",
                    label="glass transition temperature",
                )
            )
    return rows


def _qa_like_row(rec: dict[str, Any]) -> bool:
    return bool({str(k).lower() for k in rec.keys()} & {"question", "input", "prompt", "query"})


def convert_openmaterials(raw_dir: Path, limit: int, holdout_frac: float, polymer_only: bool) -> list[dict]:
    folder = raw_dir / "openmaterials"
    if not folder.exists():
        return []
    rows: list[dict] = []
    for path in iter_files(folder, ("*.parquet", "*.csv", "*.jsonl", "*.json")):
        split = path.stem.split("-")[0]
        source = f"OpenMaterials_{split}"
        df = read_table(path)
        records = df.to_dict(orient="records")
        impact = "high_impact" if "high" in split else "standard_impact"
        made = 0
        for i, rec in enumerate(records):
            source_id = as_str(rec.get("id") or rec.get("uuid") or i)
            material = as_str(rec.get("Material_Name"))
            formula = as_str(rec.get("Chemical_Formula"))
            material_class = as_str(rec.get("Material_Class"))
            application = as_str(rec.get("Application_Domain"))
            process = as_str(rec.get("Synthesis_Process") or rec.get("process"))
            contribution = as_str(rec.get("contribution"))
            recipe = as_str(rec.get("recipe"))
            blob = " ".join(
                [material, formula, material_class, application, process, contribution, recipe]
            )
            if not material or (polymer_only and not POLYMER_RE.search(blob)):
                continue
            context = contribution or recipe or material
            rows.append(
                make_task(
                    tid=f"openmaterials_{slug(split)}_{i:04d}_name",
                    source=source,
                    source_id=source_id,
                    category="KnowledgeQA",
                    subfield=impact,
                    question=f"Based on this materials description:\n{context}\nWhat is the material name?",
                    ideal=material,
                    keywords=["material identification", impact],
                    license_note="OpenMaterials impact split converted to agent items.",
                    extra={"formula": formula, "material_class": material_class},
                )
            )
            if process:
                rows.append(
                    make_task(
                        tid=f"openmaterials_{slug(split)}_{i:04d}_process",
                        source=source,
                        source_id=source_id,
                        category="ProtocolQA",
                        subfield=impact,
                        question=f"For {material}, what synthesis process is described?\n{recipe or contribution}",
                        ideal=process,
                        keywords=["synthesis process", impact],
                        license_note="OpenMaterials impact split converted to agent items.",
                    )
                )
            if application:
                rows.append(
                    make_task(
                        tid=f"openmaterials_{slug(split)}_{i:04d}_application",
                        source=source,
                        source_id=source_id,
                        category="KnowledgeQA",
                        subfield=impact,
                        question=f"What is the application domain of {material}?\n{contribution or recipe}",
                        ideal=application,
                        keywords=["application domain", impact],
                        license_note="OpenMaterials impact split converted to agent items.",
                    )
                )
            made += 1
            if made >= limit:
                break
    return rows


def convert_openpoly(raw_dir: Path, limit: int, holdout_frac: float) -> list[dict]:
    folder = raw_dir / "openpoly"
    if not folder.exists():
        return []
    files = iter_files(folder, ("*.csv", "*.parquet", "*.jsonl", "*.json", "*.xlsx", "*.xls"))
    rows: list[dict] = []
    for path in files:
        df = read_table(path)
        smiles = next((c for c in ("PSMILES", "pSMILES", "SMILES", "smiles") if c in df.columns), None)
        if smiles is None:
            smiles = guess_smiles_col(df)
        if smiles is None:
            continue
        excluded = {c for c in df.columns if str(c).lower() in OPENPOLY_EXCLUDED}
        value_cols = [
            c for c in df.columns
            if c not in {smiles, *excluded} and pd_numeric_any(df[c])
        ]
        for col in value_cols:
            prop, unit, label = openpoly_property_meta(str(col))
            rows.extend(
                numeric_tasks(
                    df, smiles, col, prop, unit, "OpenPoly",
                    limit, holdout_frac,
                    "OpenPoly literature-derived polymer properties converted to agent items.",
                    label=label,
                )
            )
    return rows
