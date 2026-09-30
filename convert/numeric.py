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


def convert_point2_tg(raw_dir: Path, limit: int, holdout_frac: float) -> list[dict]:
    candidates = [
        raw_dir / "point2" / "polymer_tg_dataset.csv",
        raw_dir / "point2" / "polymer_tg_dataset.parquet",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return []
    df = read_table(path)
    smiles = guess_smiles_col(df) or "SMILES"
    value = "Tg_K" if "Tg_K" in df.columns else next(
        (c for c in df.columns if str(c).lower() in {"tg", "tg_k", "tg_c"}), None
    )
    if value is None:
        return []
    unit = "K" if "k" in str(value).lower() else "C"
    return numeric_tasks(
        df, smiles, value, "glass_transition_temperature", unit, "POINT2_Tg",
        limit, holdout_frac, "POINT2 Tg table converted to agent exactMatch items.",
        label="glass transition temperature",
    )


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
        known = {c for c in df.columns if c in OPC25_PROPS}
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
        if records and _qa_like_row(records[0]):
            kept = 0
            for i, rec in enumerate(records):
                question = as_str(rec.get("question") or rec.get("input") or rec.get("prompt") or rec.get("query"))
                if not question:
                    continue
                blob = " ".join([question, as_str(rec.get("keywords")), split])
                if polymer_only and not POLYMER_RE.search(blob):
                    continue
                impact = "high_impact" if "high" in split else "standard_impact"
                rows.append(
                    make_task(
                        tid=f"openmaterials_{slug(split)}_{i:04d}",
                        source=source,
                        source_id=as_str(rec.get("id") or rec.get("uuid") or i),
                        category="KnowledgeQA",
                        subfield=impact,
                        question=question,
                        ideal=as_str(rec.get("answer") or rec.get("target") or rec.get("ideal") or rec.get("label")),
                        keywords=as_list(rec.get("keywords")) + [impact],
                        license_note="OpenMaterials impact split converted to agent items.",
                    )
                )
                kept += 1
                if kept >= max(limit * 3, limit):
                    break
            continue
        smiles = guess_smiles_col(df)
        if smiles is None:
            continue
        for col in numeric_cols(df, {smiles}):
            rows.extend(
                numeric_tasks(
                    df, smiles, col, slug(col), "unknown", source,
                    limit, holdout_frac, "OpenMaterials table converted to agent exactMatch items.",
                    label=str(col),
                )
            )
    return rows


def convert_openpoly(raw_dir: Path, limit: int, holdout_frac: float) -> list[dict]:
    folder = raw_dir / "openpoly"
    if not folder.exists():
        return []
    files = iter_files(folder, ("*.csv", "*.parquet", "*.jsonl", "*.json"))
    rows: list[dict] = []
    for path in files:
        df = read_table(path)
        smiles = guess_smiles_col(df)
        if smiles is None:
            continue
        for col in numeric_cols(df, {smiles}):
            unit = "C" if re.search(r"tg|glass", str(col), re.I) else "unknown"
            rows.extend(
                numeric_tasks(
                    df, smiles, col, slug(col), unit, "OpenPoly",
                    limit, holdout_frac,
                    "OpenPoly literature-derived polymer properties converted to agent items.",
                    label=str(col),
                )
            )
    return rows
