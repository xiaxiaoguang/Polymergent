# Data lake dictionary with detailed descriptions

data_lake_dict = {
    "omol25_index.parquet": "Metadata index of OMol25 train_4M DFT molecules (formula, charge, spin, HOMO/LUMO) with dataset_index into the ASE-LMDB.",
    "PI1M.csv": "Original PI1M dump: ~1M generative p-SMILES polymers from an RNN trained on PolyInfo, with a synthetic-accessibility score per chain (academic use).",
    "PI1M_v2.csv": "PI1M v2 corpus: 1M p-SMILES polymers plus SA scores for pretraining/augmentation, not experimental properties.",
    "polymetrix_tg.parquet": "Curated experimental Tg (K) for ~7,362 polymers with PSMILES, polymer class, source, n_datapoints, and reliability tags (PolyMetriX).",
    "PropagationQuantumChem_2024-03-12.csv": "CopDDB raw table (2024-03-12): 25 DFT descriptors (barriers, reaction energies, SOMO/HOMO/LUMO, buried volume, logP, TS geometry) for radical–monomer pairs over 50 monomers.",
    "bcdb_phase_behavior.parquet": "BCDB melt-phase table: >5,400 literature di-/multi-block measurements (BigSMILES, morphology, characterization, DOI) plus SCFT rows, stacked by architecture.",
    "omg_monomers.csv": "OMG virtual monomer library in CRU form from the Jackson Lab generative pipeline (Zenodo 7556992).",
    "omg_polymers.csv": "OMG polymer CRU table: ~12M linear homopolymer repeat units from 17 template polymerizations on commercially available OMG reactants.",
}

"""Chemistry / polymer-science library_content_dict for env_desc.py.

Drop this dict into your polymer fork of env_desc.py (replacing or merging
with the existing `library_content_dict`), the same way Polymer's own
env_desc.py lists biology packages. The agent's system prompt renders this
verbatim ("The environment supports a list of libraries that can be
directly used...") so the model knows what's importable/callable without
having to guess or pip-install mid-task.

Format matches Polymer's convention exactly:
    "package_name": "[Python Package] / [R Package] / [CLI Tool] description"
"""

library_content_dict = {
    "rdkit": "[Python] Cheminformatics: SMILES/SMARTS, fingerprints, descriptors, "
             "substructure, 2D/3D conformers, reactions. Default for monomers and "
             "repeat units.",
    "openbabel": "[Python + CLI] Format conversion (SMILES/MOL/PDB/XYZ/CIF, 100+). "
                 "Python API plus `obabel` for batch conversion.",
    "pubchempy": "[Python] PubChem REST: name/CID/CAS → structure and computed properties.",
    "cirpy": "[Python] NCI CIR: name/CAS/SMILES/InChI identifier conversion.",
    "mordred": "[Python] 1800+ 1D/2D/3D descriptors from RDKit mols for QSPR features.",
    "networkx": "[Python] Graphs for polymer topology (branching, crosslinks) without 3D.",
    "mbuild": "[Python] MoSDeF builder: assemble repeat units into chains/systems for MD.",
    "foyer": "[Python] MoSDeF atom-typing: apply XML force fields (e.g. OPLS-AA) to mbuild structures.",
    "gmso": "[Python] MoSDeF topology container; write LAMMPS/GROMACS-style inputs from typed systems.",
    "stk": "[Python] Construct cages, rotaxanes, and some polymer topologies from building-block SMILES. "
           "Not the primary bulk-polymer MD builder.",
    "openmm": "[Python] GPU/CPU MD engine for equilibration, production, alchemical FE.",
    "parmed": "[Python] Convert topologies/parameters across AMBER, CHARMM, GROMACS, OpenMM.",
    "mdanalysis": "[Python] Trajectory analysis: RDF, H-bonds, diffusion, custom per-frame.",
    "mdtraj": "[Python] Fast traj I/O and geometry (RMSD, distances, dihedrals).",
    "ase": "[Python] Structure I/O and a common driver API for many calculators.",
    "pyscf": "[Python] HF/DFT/post-HF on monomers or small fragments.",
    "xtb-python": "[Python] GFN-xTB bindings. Maintenance is limited; prefer the `xtb` CLI for production.",
    "xtb": "[CLI] GFN-xTB binary: `xtb struct.xyz --opt`. Fast opt / single points for oligomers.",
    "packmol": "[CLI] Pack molecules/chains into a box for bulk MD initial configs. "
               "Not packmol-memgen (that is an Amber membrane tool and is not installed).",
    "lammps": "[CLI] Polymer MD engine. Locate the binary first (`lmp`, `lmp_serial`, or `lammps`).",
    "thermo": "[Python] Engineering thermophysical correlations (density, viscosity, VLE) for fluids/mixtures.",
    "chemicals": "[Python] Pure-component constants (Tc, Pc, ω, …) feeding `thermo`.",
    "CoolProp": "[Python] High-accuracy fluid Helmholtz EOS and transport properties. "
                "Not a Redlich–Kister / eutectic solver.",
    "pymatgen": "[Python] Crystal structures, phase diagrams, Materials Project. "
                "Secondary for polymer-filler/crystallinity, not melt polymers.",
    "scikit-learn": "[Python] Tabular QSPR baselines on descriptor tables.",
    "py3Dmol": "[Python] Interactive 3D molecules in notebooks.",
    "nglview": "[Python] Jupyter widget for MD structures/trajectories.",
    "numpy": "[Python] Arrays.",
    "pandas": "[Python] Tables.",
    "scipy": "[Python] Fit/optimize/integrate (e.g. excess-property or SLE models you code yourself).",
    "matplotlib" : "[Python] Plots.",
    "seaborn" : "[Python] Statistical plots.",
    # "ddgs" : "[Python]A metasearch library that aggregates results from diverse web search services.",
}