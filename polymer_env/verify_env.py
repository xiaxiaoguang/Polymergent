#!/usr/bin/env python
"""Smoke test for the `polymer` conda environment.

Usage:
    conda activate polymer
    python verify_env.py            # full report
    python verify_env.py --quick    # skip the slower functional tests

Uses only the standard library to run, so it still works when parts of the
environment are broken. Each check is isolated: one failure never stops the rest.
Exit code is 0 if nothing FAILED (SKIP/WARN do not fail), otherwise 1.
"""
import importlib
import importlib.metadata as md
import os
import shutil
import subprocess
import sys
import tempfile
import time

QUICK = "--quick" in sys.argv
results = []  # (status, name, detail)


def record(status, name, detail=""):
    results.append((status, name, detail))
    print(f"[{status:<4}] {name}" + (f"  -- {detail}" if detail else ""))


def short(exc):
    msg = f"{type(exc).__name__}: {exc}".replace("\n", " ")
    return msg[:160]


# ---------------------------------------------------------------- 1. imports
# (label, import name, distribution name for version lookup or None)
PY_PACKAGES = [
    # numeric base
    ("numpy", "numpy", "numpy"),
    ("scipy", "scipy", "scipy"),
    ("pandas", "pandas", "pandas"),
    ("matplotlib", "matplotlib", "matplotlib"),
    ("seaborn", "seaborn", "seaborn"),
    ("statsmodels", "statsmodels", "statsmodels"),
    ("scikit-learn", "sklearn", "scikit-learn"),
    ("networkx", "networkx", "networkx"),
    # chemistry / MD / QC
    ("rdkit", "rdkit", "rdkit"),
    ("openbabel", "openbabel", None),
    ("openmm", "openmm", "openmm"),
    ("parmed", "parmed", "parmed"),
    ("mdanalysis", "MDAnalysis", "MDAnalysis"),
    ("mdtraj", "mdtraj", "mdtraj"),
    ("ase", "ase", "ase"),
    ("xtb-python", "xtb", None),
    ("mbuild", "mbuild", "mbuild"),
    ("foyer", "foyer", "foyer"),
    ("gmso", "gmso", "gmso"),
    ("pymatgen", "pymatgen.core", "pymatgen"),
    ("pyscf", "pyscf", "pyscf"),
    ("nglview", "nglview", "nglview"),
    # newly added (conda)
    ("openff-toolkit", "openff.toolkit", "openff-toolkit"),
    ("openff-interchange", "openff.interchange", "openff-interchange"),
    ("openmmforcefields", "openmmforcefields", "openmmforcefields"),
    ("cclib", "cclib", "cclib"),
    ("pint", "pint", "pint"),
    # pip: chemistry
    ("pubchempy", "pubchempy", "PubChemPy"),
    ("cirpy", "cirpy", "CIRpy"),
    ("mordred", "mordred", "mordred"),
    ("stk", "stk", "stk"),
    ("thermo", "thermo", "thermo"),
    ("chemicals", "chemicals", "chemicals"),
    ("CoolProp", "CoolProp", "CoolProp"),
    ("py3Dmol", "py3Dmol", "py3Dmol"),
    # newly added (pip)
    ("polyply", "polyply", "polyply"),
    ("pysoftk", "pysoftk", "pysoftk"),
    ("psmiles", "psmiles", "psmiles"),
    ("chemprop", "chemprop", "chemprop"),
    # pip: LLM / agent
    ("langchain", "langchain", "langchain"),
    ("langgraph", "langgraph", "langgraph"),
    ("langchain-openai", "langchain_openai", "langchain-openai"),
    ("langchain-anthropic", "langchain_anthropic", "langchain-anthropic"),
    ("langchain-ollama", "langchain_ollama", "langchain-ollama"),
    ("langchain-community", "langchain_community", "langchain-community"),
    ("openai", "openai", "openai"),
    ("transformers", "transformers", "transformers"),
    ("mcp", "mcp", "mcp"),
    ("gradio", "gradio", "gradio"),
]


def dist_version(dist):
    if not dist:
        return ""
    try:
        return md.version(dist)
    except Exception:
        return ""


print("\n=== 1. Python imports ===")
for label, modname, dist in PY_PACKAGES:
    try:
        importlib.import_module(modname)
        ver = dist_version(dist)
        record("OK", label, ver)
    except Exception as e:  # ImportError, but also broken binary deps
        record("FAIL", label, short(e))

# ------------------------------------------------------------ 2. version pins
print("\n=== 2. Version pins from environment.yml ===")
for dist, prefix in [("numpy", "1.26."), ("scipy", "1.14.")]:
    v = dist_version(dist)
    if not v:
        record("FAIL", f"{dist} pin", "not installed")
    elif v.startswith(prefix):
        record("OK", f"{dist} pin", f"{v} matches {prefix}*")
    else:
        record("FAIL", f"{dist} pin", f"{v} does not match {prefix}* (pip may have replaced it)")
if sys.version_info[:2] == (3, 11):
    record("OK", "python pin", sys.version.split()[0])
else:
    record("FAIL", "python pin", f"expected 3.11, got {sys.version.split()[0]}")

# ------------------------------------------------------------------ 3. CLI
print("\n=== 3. CLI tools ===")
env_prefix = os.environ.get("CONDA_PREFIX", "")
if env_prefix:
    record("OK", "CONDA_PREFIX", env_prefix)
else:
    record("WARN", "CONDA_PREFIX", "not set; is the env activated?")

# (label, [candidate binary names], version/help args or None)
CLI_TOOLS = [
    ("obabel", ["obabel"], ["-V"]),
    ("xtb", ["xtb"], ["--version"]),
    ("packmol", ["packmol"], None),  # reads stdin; only check it exists
    ("lammps", ["lmp", "lmp_serial", "lmp_mpi", "lammps"], ["-h"]),
    ("gromacs", ["gmx", "gmx_mpi"], ["--version"]),
    ("antechamber", ["antechamber"], ["-h"]),
    ("parmchk2", ["parmchk2"], ["-h"]),
    ("tleap", ["tleap"], ["-h"]),
    ("polyply", ["polyply"], ["-h"]),
]


def run(cmd, timeout=60, stdin=None):
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, stdin=stdin
    )


cli_paths = {}
for label, candidates, args in CLI_TOOLS:
    found = next((c for c in candidates if shutil.which(c)), None)
    if not found:
        record("FAIL", label, f"none of {candidates} on PATH")
        continue
    path = shutil.which(found)
    cli_paths[label] = path
    from_env = bool(env_prefix) and os.path.realpath(path).startswith(os.path.realpath(env_prefix))
    where = "env" if from_env else "OUTSIDE ENV"
    if args is None:
        record("OK" if from_env else "WARN", label, f"{found} -> {path} [{where}]")
        continue
    try:
        r = run([found] + args, timeout=60)
        out = (r.stdout + r.stderr).strip().splitlines()
        first = out[0][:80] if out else ""
        # many tools return non-zero for -h; the point is that it launches
        status = "OK" if from_env else "WARN"
        record(status, label, f"{found} [{where}] {first}")
    except Exception as e:
        record("FAIL", label, f"{found} found but would not run: {short(e)}")

# ------------------------------------------------- 4. functional mini-tests
print("\n=== 4. Functional tests ===")


def functional(name, fn):
    t0 = time.time()
    try:
        detail = fn() or ""
        record("OK", name, f"{detail} ({time.time() - t0:.1f}s)".strip())
    except Exception as e:
        record("FAIL", name, short(e))


def t_rdkit():
    from rdkit import Chem
    from rdkit.Chem import Descriptors, AllChem

    m = Chem.AddHs(Chem.MolFromSmiles("CC(C)C(=O)OC"))  # methyl isobutyrate
    assert AllChem.EmbedMolecule(m, randomSeed=7) == 0
    return f"MW={Descriptors.MolWt(m):.2f}, 3D embed ok"


def t_openbabel():
    from openbabel import pybel

    mol = pybel.readstring("smi", "c1ccccc1")
    return f"benzene -> {mol.write('inchi').strip()}"


def t_openmm():
    import openmm

    names = [openmm.Platform.getPlatform(i).getName() for i in range(openmm.Platform.getNumPlatforms())]
    assert "Reference" in names or "CPU" in names
    return "platforms: " + ", ".join(names)


def t_openff():
    from openff.toolkit import Molecule, ForceField

    mol = Molecule.from_smiles("CCO")
    ff = ForceField("openff-2.1.0.offxml")
    return f"loaded Sage, {mol.n_atoms} atoms (charges not computed)"


def t_mordred():
    from rdkit import Chem
    from mordred import Calculator, descriptors

    calc = Calculator(descriptors, ignore_3D=True)
    res = calc(Chem.MolFromSmiles("CCO"))
    return f"{len(res)} descriptors computed"


def t_psmiles():
    from psmiles import PolymerSmiles as PS

    ps = PS("[*]CC[*]")
    return f"canonical: {ps.canonicalize}"


def t_stk():
    import stk

    bb = stk.BuildingBlock("BrCCBr", [stk.BromoFactory()])
    return f"building block with {bb.get_num_atoms()} atoms"


def t_pymatgen():
    from pymatgen.core import Lattice, Structure

    s = Structure(Lattice.cubic(4.2), ["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])
    return f"{s.composition.reduced_formula}, V={s.volume:.1f}"


def t_pyscf():
    from pyscf import gto, scf

    mol = gto.M(atom="H 0 0 0; H 0 0 0.74", basis="sto-3g", verbose=0)
    e = scf.RHF(mol).kernel()
    return f"H2 RHF energy {e:.4f} Ha (expect about -1.117)"


def t_thermo():
    from chemicals import Tc

    return f"Tc(water) = {Tc('7732-18-5')} K"


def t_coolprop():
    import CoolProp.CoolProp as CP

    return f"water density at 300 K, 1 atm = {CP.PropsSI('D', 'T', 300, 'P', 101325, 'Water'):.1f} kg/m3"


def t_mbuild():
    import mbuild as mb

    c = mb.load("CCO", smiles=True)
    return f"{c.n_particles} particles"


def t_ase():
    from ase.build import molecule

    return f"H2O with {len(molecule('H2O'))} atoms"


def t_xtb_cli():
    if "xtb" not in cli_paths:
        raise RuntimeError("xtb binary missing")
    xyz = "3\nwater\nO 0.0 0.0 0.1173\nH 0.0 0.7572 -0.4692\nH 0.0 -0.7572 -0.4692\n"
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "w.xyz"), "w") as f:
            f.write(xyz)
        r = subprocess.run(
            ["xtb", "w.xyz", "--sp"], cwd=d, capture_output=True, text=True, timeout=120
        )
        text = r.stdout + r.stderr
        assert "TOTAL ENERGY" in text, "no energy in xtb output"
        line = next(l for l in text.splitlines() if "TOTAL ENERGY" in l)
        return line.strip()


def t_xtb_python():
    from xtb.interface import Calculator, Param
    import numpy as np

    num = np.array([8, 1, 1])
    pos = np.array([[0, 0, 0.2217], [0, 1.431, -0.8868], [0, -1.431, -0.8868]])  # bohr
    calc = Calculator(Param.GFN2xTB, num, pos)
    res = calc.singlepoint()
    return f"E = {res.get_energy():.4f} Ha"


def t_polyply_cli():
    r = run(["polyply", "-h"], timeout=60)
    assert r.returncode == 0, (r.stderr or r.stdout)[:120]
    return "polyply -h exits 0"


def t_ambertools():
    r = run(["antechamber", "-h"], timeout=60)
    text = r.stdout + r.stderr
    assert "antechamber" in text.lower()
    return "antechamber launches"


def t_gmx():
    exe = "gmx" if shutil.which("gmx") else "gmx_mpi"
    r = run([exe, "--version"], timeout=60)
    text = r.stdout + r.stderr
    assert "GROMACS version" in text, text[:120]
    ver = next(l for l in text.splitlines() if "GROMACS version" in l)
    return ver.strip()


def t_lammps_python():
    import lammps  # optional: only present if built with Python module

    return f"python module present, version {lammps.__version__ if hasattr(lammps, '__version__') else '?'}"


always = [
    ("rdkit: SMILES + 3D embed", t_rdkit),
    ("openbabel: SMILES -> InChI", t_openbabel),
    ("openmm: platforms", t_openmm),
    ("openff: Molecule + Sage", t_openff),
    ("mordred: descriptors", t_mordred),
    ("psmiles: canonicalize", t_psmiles),
    ("pymatgen: Structure", t_pymatgen),
    ("pyscf: H2 RHF", t_pyscf),
    ("chemicals: Tc lookup", t_thermo),
    ("CoolProp: water density", t_coolprop),
    ("ase: build molecule", t_ase),
    ("xtb-python: GFN2 singlepoint", t_xtb_python),
    ("xtb CLI: water single point", t_xtb_cli),
    ("polyply CLI", t_polyply_cli),
    ("AmberTools: antechamber", t_ambertools),
    ("GROMACS: gmx --version", t_gmx),
]
slow = [
    ("mbuild: load from SMILES", t_mbuild),
    ("stk: BuildingBlock", t_stk),
]
for name, fn in always:
    functional(name, fn)
if not QUICK:
    for name, fn in slow:
        functional(name, fn)

# LAMMPS python module is optional (needed by pysimm/RadonPy), so SKIP not FAIL
try:
    import lammps  # noqa: F401

    functional("lammps: python module", t_lammps_python)
except ImportError:
    record("SKIP", "lammps: python module", "not installed (only needed for pysimm/RadonPy)")

# --------------------------------------------------------- 5. dependency check
print("\n=== 5. pip dependency consistency (pip check) ===")
try:
    r = run([sys.executable, "-m", "pip", "check"], timeout=180)
    out = (r.stdout + r.stderr).strip()
    if r.returncode == 0:
        record("OK", "pip check", "no broken requirements")
    else:
        lines = out.splitlines()
        record("WARN", "pip check", f"{len(lines)} issue(s); first few below")
        for line in lines[:15]:
            print("        " + line)
except Exception as e:
    record("WARN", "pip check", short(e))

# ------------------------------------------------------------------ summary
print("\n=== Summary ===")
counts = {}
for status, _, _ in results:
    counts[status] = counts.get(status, 0) + 1
print("  " + "  ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
fails = [(n, d) for s, n, d in results if s == "FAIL"]
if fails:
    print("\nFailed checks:")
    for n, d in fails:
        print(f"  - {n}: {d}")
    sys.exit(1)
print("\nNo failures.")
sys.exit(0)