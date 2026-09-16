"""Detect and repair chemistry writing conventions for a polymer agent.

Focus: SMILES validity, dummy-atom polymer notation, cyclic-monomer vs
opened repeat unit, and name→SMILES resolution.

Pair with polymer_informatics.py. Schema: polymer_conventions_description.py.
"""

from __future__ import annotations

import re
from typing import Any

from rdkit import Chem
from rdkit.Chem import rdMolDescriptors


# Offline fallback for names the agent already used in this project.
_NAME_TO_SMILES: dict[str, str] = {
    "gamma-butyrolactone": "O=C1CCCO1",
    "gbl": "O=C1CCCO1",
    "gamma-valerolactone": "CC1CCC(=O)O1",
    "gvl": "CC1CCC(=O)O1",
    "alpha-angelica lactone": "CC1=CCC(=O)O1",
    "delta-valerolactone": "O=C1CCCCO1",
    "delta-hexalactone": "CC1CCCC(=O)O1",
    "epsilon-caprolactone": "O=C1CCCCCO1",
    "caprolactone": "O=C1CCCCCO1",
    "4-methyl-caprolactone": "CC1CCCC(=O)OC1",
    "beta-methyl-delta-valerolactone": "CC1CCOC(=O)C1",
    "succinic anhydride": "O=C1CCC(=O)O1",
    "glutaric anhydride": "O=C1CCCC(=O)O1",
    "maleic anhydride": "O=C1C=CC(=O)O1",
    "methylsuccinic anhydride": "CC1CC(=O)OC1=O",
    "citraconic anhydride": "CC1=CC(=O)OC1=O",
    "2,2-dimethylsuccinic anhydride": "CC1(C)CC(=O)OC1=O",
    "diglycolic anhydride": "O=C1COCC(=O)O1",
    "itaconic anhydride": "C=C1CC(=O)OC1=O",
    "phthalic anhydride": "O=C1OC(=O)c2ccccc12",
    "homophthalic anhydride": "O=C1Cc2ccccc2C(=O)O1",
    "ethylene glycol": "OCCO",
    "l-lactide": "C[C@@H]1OC(=O)[C@H](C)OC1=O",
    "lactide": "CC1OC(=O)C(C)OC1=O",
    "glycolide": "O=C1COC(=O)CO1",
}


def _norm_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def validate_and_canonicalize_smiles(smiles: str) -> str:
    """Return canonical SMILES, or raise ValueError. Do not print the result."""
    raw = smiles.strip()
    mol = Chem.MolFromSmiles(raw, sanitize=False)
    if mol is None:
        raise ValueError(f"parse failed: {raw!r}")
    problems = [str(p) for p in Chem.DetectChemistryProblems(mol)]
    try:
        Chem.SanitizeMol(mol)
    except Exception as exc:
        extra = f"; {problems}" if problems else ""
        raise ValueError(f"sanitize failed: {exc}{extra}") from exc
    return Chem.MolToSmiles(mol)


def autocorrect_smiles(smiles: str) -> dict[str, Any]:
    """Apply conservative LLM-typo repairs, then validate.

    Repairs (in order): strip; drop whitespace inside the string;
    CL/BR/SE/NA/SI/SN two-letter element casing; replace terminal [X]/X
    used as dummy; convert `[*:1]` style is left intact.
    Does not invent ring closures or missing atoms.
    """
    original = smiles
    s = smiles.strip()
    notes: list[str] = []
    if s != smiles:
        notes.append("stripped leading/trailing whitespace")
    compact = re.sub(r"\s+", "", s)
    if compact != s:
        notes.append("removed internal whitespace")
        s = compact

    replacements = [
        ("CL", "Cl"),
        ("BR", "Br"),
        ("SE", "Se"),
        ("NA", "Na"),
        ("SI", "Si"),
        ("SN", "Sn"),
        ("[CL]", "[Cl]"),
        ("[BR]", "[Br]"),
    ]
    for a, b in replacements:
        if a in s:
            s = s.replace(a, b)
            notes.append(f"replaced {a} -> {b}")

    # LLM sometimes writes X or [X] for a dummy attachment.
    s2 = s.replace("[X]", "*")
    if re.fullmatch(r"X[A-Za-z0-9\(\)\[\]=#\-\+@\\\/]+X", s2):
        s2 = "*" + s2[1:-1] + "*"
    s2 = re.sub(r"(?<![A-Za-z])X(?![A-Za-z])", "*", s2)
    if s2 != s:
        notes.append("replaced X/[X] with dummy *")
        s = s2

    return validate_and_canonicalize_smiles(s)


def inspect_polymer_smiles_convention(smiles: str) -> str:
    """Return a short role tag. Bind to a variable; do not echo."""
    can = validate_and_canonicalize_smiles(smiles)
    mol = Chem.MolFromSmiles(can)
    dummies = [a.GetIdx() for a in mol.GetAtoms() if a.GetAtomicNum() == 0]
    dummy_deg = [mol.GetAtomWithIdx(i).GetDegree() for i in dummies]
    if len(dummies) == 2 and all(d == 1 for d in dummy_deg):
        return "linear_repeat_unit"
    if mol.HasSubstructMatch(Chem.MolFromSmarts("[C&R](=O)[O&R][C&R](=O)")) and not dummies:
        return "cyclic_anhydride"
    if mol.HasSubstructMatch(Chem.MolFromSmarts("[C&R](=O)[O&R]")) and not dummies:
        return "cyclic_lactone"
    if mol.HasSubstructMatch(Chem.MolFromSmarts("[C&R](=O)[N&R]")) and not dummies:
        return "cyclic_lactam"
    if not dummies:
        return "no_dummy"
    if len(dummies) == 1:
        return "one_dummy"
    return f"n_dummy={len(dummies)}"


def open_cyclic_monomer_to_repeat_unit(
    smiles: str,
    monomer_class: str = "auto",
) -> str:
    """Open a cyclic ester/lactam/anhydride; return the 2-dummy mer SMILES only.

    lactone: break the acyl–O single bond → *O-(chain)-C(=O)*
    lactam: break the acyl–N bond → *N-(chain)-C(=O)*
    anhydride: break one acyl–O bond → *OC(=O)-(chain)-C(=O)*

    monomer_class: 'auto' | 'lactone' | 'lactam' | 'anhydride'
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Cannot parse SMILES: {smiles!r}")

    cls = monomer_class.lower()
    if cls == "auto":
        if mol.HasSubstructMatch(Chem.MolFromSmarts("[C&R](=O)[O&R][C&R](=O)")):
            cls = "anhydride"
        elif mol.HasSubstructMatch(Chem.MolFromSmarts("[C&R](=O)[O&R]")):
            cls = "lactone"
        elif mol.HasSubstructMatch(Chem.MolFromSmarts("[C&R](=O)[N&R]")):
            cls = "lactam"
        else:
            raise ValueError(
                "No lactone/lactam/anhydride pattern found. "
                "Supply an opened mer with two '*' yourself."
            )

    if cls == "lactone":
        smarts = "[C&R](=O)[O&R]"
        # match: carbonyl C, carbonyl O, ring O
        matches = list(mol.GetSubstructMatches(Chem.MolFromSmarts(smarts)))
        if not matches:
            raise ValueError("No ring ester found")
        c_idx, _carbonyl_o, ring_o = matches[0]
        hetero = ring_o
    elif cls == "lactam":
        matches = list(mol.GetSubstructMatches(Chem.MolFromSmarts("[C&R](=O)[N&R]")))
        if not matches:
            raise ValueError("No ring amide found")
        c_idx, _carbonyl_o, hetero = matches[0]
    elif cls == "anhydride":
        matches = list(mol.GetSubstructMatches(Chem.MolFromSmarts("[C&R](=O)[O&R][C&R](=O)")))
        if not matches:
            raise ValueError("No cyclic anhydride found")
        # C(=O)-O-C(=O): break first C-O
        c_idx, _o1, hetero, _c2, _o2 = matches[0]
    else:
        raise ValueError("monomer_class must be auto|lactone|lactam|anhydride")

    ring_info = mol.GetRingInfo()
    if not ring_info.AreAtomsInSameRing(c_idx, hetero):
        raise ValueError("Matched ester/amide atoms are not in the same ring")

    rw = Chem.RWMol(mol)
    if rw.GetBondBetweenAtoms(c_idx, hetero) is None:
        raise ValueError("Expected a bond between acyl carbon and heteroatom")
    rw.RemoveBond(c_idx, hetero)
    d_h = rw.AddAtom(Chem.Atom(0))
    d_c = rw.AddAtom(Chem.Atom(0))
    rw.AddBond(hetero, d_h, Chem.BondType.SINGLE)
    rw.AddBond(c_idx, d_c, Chem.BondType.SINGLE)
    opened = rw.GetMol()
    Chem.SanitizeMol(opened)
    return Chem.MolToSmiles(opened)


def resolve_monomer_name_to_smiles(
    name: str,
    use_pubchem: bool = True,
) -> str:
    """Return closed-molecule SMILES for a monomer name. Raises on miss."""
    key = _norm_name(name)
    if key in _NAME_TO_SMILES:
        return Chem.MolToSmiles(Chem.MolFromSmiles(_NAME_TO_SMILES[key]))
    if use_pubchem:
        import pubchempy as pcp

        hits = pcp.get_compounds(name, "name")
        if hits and hits[0].canonical_smiles:
            mol = Chem.MolFromSmiles(hits[0].canonical_smiles)
            if mol is None:
                raise ValueError("PubChem SMILES did not parse")
            return Chem.MolToSmiles(mol)
        raise ValueError(f"no structure for {name!r}")
    raise ValueError(f"unknown name {name!r}")


def prepare_repeat_unit_from_name_or_smiles(
    name_or_smiles: str,
    n_repeats_to_test: int = 2,
) -> str:
    """Return an oligomer-ready 2-dummy mer SMILES. Prefer this one call.

    Bind the result; do not print it. Raises ValueError on failure.
    """
    from polymer.tool.polymer_informatics import build_linear_oligomer_smiles

    text = name_or_smiles.strip()
    looks_like_smiles = bool(re.search(r"[A-Za-z][0-9=#()\[\]\*]", text)) and " " not in text
    if looks_like_smiles or any(ch in text for ch in "*=#"):
        try:
            closed = autocorrect_smiles(text)
        except ValueError:
            closed = resolve_monomer_name_to_smiles(text)
    else:
        closed = resolve_monomer_name_to_smiles(text)

    role = inspect_polymer_smiles_convention(closed)
    ru = closed
    if role in {"cyclic_lactone", "cyclic_lactam", "cyclic_anhydride"}:
        ru = open_cyclic_monomer_to_repeat_unit(closed)
    elif role != "linear_repeat_unit":
        raise ValueError(f"not oligomer-ready: {role}")
    build_linear_oligomer_smiles(ru, n_repeats_to_test)
    return ru