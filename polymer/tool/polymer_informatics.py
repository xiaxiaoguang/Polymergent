"""Polymer informatics, cheminformatics, and lightweight QM tools.

Uses RDKit (structure / descriptors / oligomers) and PySCF (HF or DFT
single points on capped repeat units). Intended for agent-side screening,
not production-quality materials DFT.

LLM-facing schemas: polymer_informatics_description.py.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from rdkit import Chem
from rdkit.Chem import (
    AllChem,
    Crippen,
    DataStructs,
    Descriptors,
    Lipinski,
    rdMolDescriptors,
)


# ---------------------------------------------------------------------------
# SMILES / graph helpers
# ---------------------------------------------------------------------------

def _mol_from_smiles(smiles: str) -> Chem.Mol:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"RDKit could not parse SMILES: {smiles!r}")
    return mol


def _dummy_atom_indices(mol: Chem.Mol) -> list[int]:
    return [atom.GetIdx() for atom in mol.GetAtoms() if atom.GetAtomicNum() == 0]


def parse_repeat_unit_smiles(smiles: str) -> dict[str, Any]:
    """Parse a repeat-unit SMILES (dummy atoms `*` or `[*:n]`) and summarize it.

    Returns dummy-atom count, heavy-atom count, formula, and canonical SMILES.
    """
    mol = _mol_from_smiles(smiles)
    dummies = _dummy_atom_indices(mol)
    heavy = mol.GetNumHeavyAtoms()
    return {
        "canonical_smiles": Chem.MolToSmiles(mol),
        "n_dummy_attachment_points": len(dummies),
        "n_heavy_atoms": heavy,
        "n_atoms_including_implicit_h": mol.GetNumAtoms(onlyExplicit=False),
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "repeat_unit_exact_mass": Descriptors.ExactMolWt(mol),
        "is_linear_aa_type": len(dummies) == 2,
        "likely_branch_or_telechelic": len(dummies) > 2,
    }


def cap_repeat_unit_with_hydrogen(smiles: str) -> str:
    """Replace dummy attachment points `*` with implicit hydrogens.

    Converts a polymer repeat-unit SMILES into a small-molecule SMILES
    suitable for descriptor or QM calculations on the capped mer.
    """
    mol = _mol_from_smiles(smiles)
    rw = Chem.RWMol(mol)
    dummies = sorted(_dummy_atom_indices(rw), reverse=True)
    for idx in dummies:
        atom = rw.GetAtomWithIdx(idx)
        neighbors = list(atom.GetNeighbors())
        if len(neighbors) != 1:
            raise ValueError(
                f"Dummy atom {idx} has {len(neighbors)} neighbors; expected 1"
            )
        rw.RemoveAtom(idx)
    capped = rw.GetMol()
    Chem.SanitizeMol(capped)
    return Chem.MolToSmiles(capped)


def build_linear_oligomer_smiles(
    repeat_unit_smiles: str,
    n_repeats: int,
    cap_with_hydrogen: bool = True,
) -> str:
    """Join n copies of a 2-dummy repeat unit into an oligomer SMILES.

    Dummy atoms must each have exactly one neighbor. Copies are connected
    head-to-tail through those neighbors; dummies are then removed and
    (optionally) the chain ends are left as implicit H.
    """
    if n_repeats < 1:
        raise ValueError("n_repeats must be >= 1")
    base = _mol_from_smiles(repeat_unit_smiles)
    dummies = _dummy_atom_indices(base)
    if len(dummies) != 2:
        raise ValueError(
            f"Linear oligomer builder requires exactly 2 dummy atoms, found {len(dummies)}"
        )

    combo = Chem.Mol(base)
    for _ in range(n_repeats - 1):
        combo = Chem.CombineMols(combo, base)

    rw = Chem.RWMol(combo)
    n_atoms_mon = base.GetNumAtoms()

    def dummy_pair(copy_i: int) -> tuple[int, int]:
        offset = copy_i * n_atoms_mon
        return dummies[0] + offset, dummies[1] + offset

    # Connect copy i dummy[1]-neighbor to copy i+1 dummy[0]-neighbor
    for i in range(n_repeats - 1):
        d_tail = dummy_pair(i)[1]
        d_head = dummy_pair(i + 1)[0]
        n_tail = [a.GetIdx() for a in rw.GetAtomWithIdx(d_tail).GetNeighbors()]
        n_head = [a.GetIdx() for a in rw.GetAtomWithIdx(d_head).GetNeighbors()]
        if len(n_tail) != 1 or len(n_head) != 1:
            raise ValueError("Each dummy must have exactly one neighbor")
        rw.AddBond(n_tail[0], n_head[0], Chem.BondType.SINGLE)

    dummies_all = sorted(_dummy_atom_indices(rw), reverse=True)
    for idx in dummies_all:
        rw.RemoveAtom(idx)

    olig = rw.GetMol()
    Chem.SanitizeMol(olig)
    if not cap_with_hydrogen:
        return Chem.MolToSmiles(olig)
    return Chem.MolToSmiles(olig)


def repeat_unit_descriptors(smiles: str, cap_dummies: bool = True) -> dict[str, float | int | str]:
    """RDKit 2D descriptors for a repeat unit (optionally H-capped).

    Useful as cheap QSPR features: MW, TPSA, Crippen logP, rotatable bonds,
    H-bond donors/acceptors, aromatic rings, fraction Csp3, Bertz complexity.
    """
    mol0 = _mol_from_smiles(smiles)
    src = cap_repeat_unit_with_hydrogen(smiles) if (cap_dummies and _dummy_atom_indices(mol0)) else smiles
    mol = _mol_from_smiles(src)
    return {
        "smiles_used": Chem.MolToSmiles(mol),
        "exact_mw": float(Descriptors.ExactMolWt(mol)),
        "heavy_atom_count": int(Lipinski.HeavyAtomCount(mol)),
        "tpsa": float(Descriptors.TPSA(mol)),
        "crippen_logp": float(Crippen.MolLogP(mol)),
        "crippen_mr": float(Crippen.MolMR(mol)),
        "hbd": int(Lipinski.NumHDonors(mol)),
        "hba": int(Lipinski.NumHAcceptors(mol)),
        "rotatable_bonds": int(Lipinski.NumRotatableBonds(mol)),
        "aromatic_rings": int(rdMolDescriptors.CalcNumAromaticRings(mol)),
        "aliphatic_rings": int(rdMolDescriptors.CalcNumAliphaticRings(mol)),
        "fraction_csp3": float(rdMolDescriptors.CalcFractionCSP3(mol)),
        "bertz_complexity": float(Descriptors.BertzCT(mol)),
        "num_valence_electrons": int(Descriptors.NumValenceElectrons(mol)),
    }


def morgan_tanimoto_similarity(
    smiles_a: str,
    smiles_b: str,
    radius: int = 2,
    n_bits: int = 2048,
) -> float:
    """Tanimoto similarity of two structures from Morgan fingerprints."""
    from rdkit.Chem import rdFingerprintGenerator

    gen = rdFingerprintGenerator.GetMorganGenerator(radius=radius, fpSize=n_bits)
    fa = gen.GetFingerprint(_mol_from_smiles(smiles_a))
    fb = gen.GetFingerprint(_mol_from_smiles(smiles_b))
    return float(DataStructs.TanimotoSimilarity(fa, fb))


def count_smarts_substructures(smiles: str, smarts_patterns: list[str]) -> dict[str, int]:
    """Count SMARTS hits on a molecule (e.g. ester, amide, vinyl, isocyanate)."""
    mol = _mol_from_smiles(smiles)
    out: dict[str, int] = {}
    for smarts in smarts_patterns:
        patt = Chem.MolFromSmarts(smarts)
        if patt is None:
            raise ValueError(f"Invalid SMARTS: {smarts!r}")
        out[smarts] = len(mol.GetSubstructMatches(patt))
    return out


COMMON_POLYMER_SMARTS: dict[str, str] = {
    "ester": "C(=O)O[C,c]",
    "carboxylic_acid": "C(=O)[OH]",
    "amide": "C(=O)N",
    "alcohol": "[CX4][OX2H]",
    "phenol": "[cX3][OX2H]",
    "primary_amine": "[NX3;H2;!$(NC=O)]",
    "isocyanate": "N=C=O",
    "epoxide": "C1OC1",
    "vinyl": "C=C",
    "acrylate": "C=CC(=O)O",
    "aromatic": "c1ccccc1",
    "urethane": "NC(=O)O",
}


def count_common_polymer_functional_groups(smiles: str) -> dict[str, int]:
    """Count common polymer-relevant functional groups via SMARTS."""
    mol = _mol_from_smiles(smiles)
    counts: dict[str, int] = {}
    for name, smarts in COMMON_POLYMER_SMARTS.items():
        patt = Chem.MolFromSmarts(smarts)
        counts[name] = len(mol.GetSubstructMatches(patt))
    return counts


# ---------------------------------------------------------------------------
# Inverse design on closed-form models
# ---------------------------------------------------------------------------

def fox_weight_fraction_for_target_tg(
    target_tg_k: float,
    tg_a_k: float,
    tg_b_k: float,
) -> dict[str, float]:
    """Solve binary Fox equation for weight fraction of A that hits target Tg.

    1/Tg = w_A/Tg_A + (1-w_A)/Tg_B
    """
    if min(target_tg_k, tg_a_k, tg_b_k) <= 0:
        raise ValueError("All Tgs must be positive Kelvin")
    if abs(tg_a_k - tg_b_k) < 1e-12:
        raise ValueError("Component Tgs are identical; composition is undefined")
    lo, hi = min(tg_a_k, tg_b_k), max(tg_a_k, tg_b_k)
    if not lo <= target_tg_k <= hi:
        raise ValueError(
            f"Target Tg {target_tg_k} K is outside the bracket [{lo}, {hi}] K"
        )
    w_a = (1.0 / target_tg_k - 1.0 / tg_b_k) / (1.0 / tg_a_k - 1.0 / tg_b_k)
    return {
        "weight_fraction_a": w_a,
        "weight_fraction_b": 1.0 - w_a,
        "target_tg_k": target_tg_k,
    }


def carothers_conversion_for_target_xn(
    target_xn: float,
    stoichiometric_ratio_r: float = 1.0,
) -> float:
    """Invert Carothers: p required to reach a target Xn (linear, r <= 1).

    p = (1 + r - (1+r)/Xn) / (2 r)
    """
    if target_xn < 1:
        raise ValueError("target_xn must be >= 1")
    if not 0.0 < stoichiometric_ratio_r <= 1.0:
        raise ValueError("stoichiometric_ratio_r must be in (0, 1]")
    r = stoichiometric_ratio_r
    p = (1.0 + r - (1.0 + r) / target_xn) / (2.0 * r)
    if not 0.0 <= p < 1.0:
        raise ValueError(f"Required conversion p={p} is not in [0, 1); check Xn and r")
    return p


# ---------------------------------------------------------------------------
# 3D embed + QM (PySCF)
# ---------------------------------------------------------------------------

def _embed_xyz_lines(smiles: str, random_seed: int = 0xF00D) -> tuple[str, int, int]:
    """Return XYZ atom block, charge, and spin multiplicity guess."""
    mol = Chem.AddHs(_mol_from_smiles(smiles))
    params = AllChem.ETKDGv3()
    params.randomSeed = random_seed
    status = AllChem.EmbedMolecule(mol, params)
    if status != 0:
        params.useRandomCoords = True
        status = AllChem.EmbedMolecule(mol, params)
    if status != 0:
        raise RuntimeError(f"3D embedding failed for {smiles!r}")
    try:
        AllChem.MMFFOptimizeMolecule(mol, maxIters=200)
    except Exception:
        AllChem.UFFOptimizeMolecule(mol, maxIters=200)

    conf = mol.GetConformer()
    lines = []
    for atom in mol.GetAtoms():
        pos = conf.GetAtomPosition(atom.GetIdx())
        lines.append(f"{atom.GetSymbol()} {pos.x:.8f} {pos.y:.8f} {pos.z:.8f}")
    charge = Chem.GetFormalCharge(mol)
    n_electrons = sum(atom.GetAtomicNum() for atom in mol.GetAtoms()) - charge
    spin = 1 if n_electrons % 2 == 0 else 2  # PySCF spin = 2S
    if n_electrons % 2 == 1:
        spin = 1  # 2S = 1 for doublet
    else:
        spin = 0
    return "; ".join(lines), charge, spin


def dft_homo_lumo_repeat_unit(
    smiles: str,
    basis: str = "sto-3g",
    xc: str = "b3lyp",
    use_hf: bool = False,
    cap_dummies: bool = True,
    max_heavy_atoms: int = 25,
) -> dict[str, Any]:
    """Geometry-embed a (capped) repeat unit and run a PySCF HF or DFT single point.

    Returns total energy (Ha), HOMO/LUMO (eV), gap (eV), dipole (Debye).
    Default is cheap B3LYP/STO-3G after MMFF embed — screening quality only.
    Hard-capped at max_heavy_atoms so the agent cannot launch huge DFT jobs.
    """
    from pyscf import dft, gto, scf

    src = smiles
    mol_rd = _mol_from_smiles(smiles)
    if cap_dummies and _dummy_atom_indices(mol_rd):
        src = cap_repeat_unit_with_hydrogen(smiles)
        mol_rd = _mol_from_smiles(src)
    n_heavy = mol_rd.GetNumHeavyAtoms()
    if n_heavy > max_heavy_atoms:
        raise ValueError(
            f"{n_heavy} heavy atoms exceeds max_heavy_atoms={max_heavy_atoms}; "
            "cap the mer, shorten the oligomer, or raise the limit deliberately"
        )

    atom_str, charge, spin = _embed_xyz_lines(src)
    mol = gto.M(atom=atom_str, basis=basis, charge=charge, spin=spin, verbose=0, unit="Angstrom")
    if use_hf or xc.lower() in {"hf", "rhf"}:
        mf = scf.UKS(mol) if spin else scf.RHF(mol)
        if spin:
            mf = scf.UHF(mol)
    else:
        mf = dft.UKS(mol) if spin else dft.RKS(mol)
        mf.xc = xc
    mf.conv_tol = 1e-7
    e_tot = float(mf.kernel())
    if not mf.converged:
        raise RuntimeError("SCF did not converge")

    mo = np.asarray(mf.mo_energy)
    if mo.ndim == 1:
        occ = np.asarray(mf.mo_occ)
        occ_idx = np.where(occ > 0.5)[0]
        virt_idx = np.where(occ <= 0.5)[0]
        if occ_idx.size == 0 or virt_idx.size == 0:
            raise RuntimeError("Could not identify HOMO/LUMO")
        homo_ha = float(mo[occ_idx].max())
        lumo_ha = float(mo[virt_idx].min())
    else:
        # unrestricted: take max occupied / min virtual across spins
        occ = np.asarray(mf.mo_occ)
        homos, lumos = [], []
        for s in range(mo.shape[0]):
            occ_idx = np.where(occ[s] > 0.5)[0]
            virt_idx = np.where(occ[s] <= 0.5)[0]
            if occ_idx.size:
                homos.append(mo[s, occ_idx].max())
            if virt_idx.size:
                lumos.append(mo[s, virt_idx].min())
        homo_ha = float(max(homos))
        lumo_ha = float(min(lumos))

    ha_to_ev = 27.211386245988
    dip = mf.dip_moment(unit="Debye", verbose=0)
    dipole = float(np.linalg.norm(dip))
    return {
        "smiles_used": src,
        "method": "HF" if use_hf or xc.lower() in {"hf", "rhf"} else f"DFT/{xc}",
        "basis": basis,
        "n_heavy_atoms": n_heavy,
        "charge": charge,
        "spin_2s": spin,
        "scf_converged": bool(mf.converged),
        "total_energy_ha": e_tot,
        "homo_ev": homo_ha * ha_to_ev,
        "lumo_ev": lumo_ha * ha_to_ev,
        "gap_ev": (lumo_ha - homo_ha) * ha_to_ev,
        "dipole_debye": dipole,
    }


def hf_sto3g_energy_smiles(
    smiles: str,
    cap_dummies: bool = True,
    max_heavy_atoms: int = 25,
) -> dict[str, Any]:
    """Convenience wrapper: RHF/STO-3G single point on a capped mer."""
    return dft_homo_lumo_repeat_unit(
        smiles,
        basis="sto-3g",
        xc="hf",
        use_hf=True,
        cap_dummies=cap_dummies,
        max_heavy_atoms=max_heavy_atoms,
    )


def estimate_oligomer_scaling_cost(
    repeat_unit_smiles: str,
    n_repeats: int,
) -> dict[str, Any]:
    """Rough DFT cost proxy: heavy atoms and O(N^4) HF scaling vs monomer.

    Helps the agent decide whether to run QM on a mer vs an oligomer.
    """
    mer = cap_repeat_unit_with_hydrogen(repeat_unit_smiles)
    n1 = _mol_from_smiles(mer).GetNumHeavyAtoms()
    olig = build_linear_oligomer_smiles(repeat_unit_smiles, n_repeats)
    nn = _mol_from_smiles(olig).GetNumHeavyAtoms()
    return {
        "monomer_heavy_atoms": n1,
        "oligomer_heavy_atoms": nn,
        "oligomer_smiles": olig,
        "hf_cost_ratio_vs_monomer_n4": (nn / max(n1, 1)) ** 4,
        "recommendation": (
            "run QM on capped monomer only"
            if nn > 25
            else "oligomer QM is still small enough for STO-3G"
        ),
    }