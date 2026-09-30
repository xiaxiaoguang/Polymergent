"""
Data-lake catalog. Each entry: "{name} — {access type}. {content}. {use/avoid}."
Access type is always first: local table | repo bundle (read README) | hub dataset | web-only.
"""
 
data_lake_dict = {
    "opoly26": "opoly26 — local table. DFT (ωB97M-V/def2-TZVPD) on polymer clusters (≤360 atoms, 6.57M points): energies, forces, HOMO/LUMO gap, charges. Use for MLIPs/electronic structure. Not experimental Tg or MD bulk properties.",
    "polyVERSE": "polyVERSE — repo bundle (Ramprasad Group GitHub/Zenodo), read README first. Virtual CRUs (ROP/ROMP/polyimide) + gas P/D/S and recyclable-polymer CSVs. Lineage: Polymer Genome/Khazana. Not the Tg table (polymetrix_tg.parquet).",
    "polymerscholar": "polymerscholar — web-only, no local file. Literature-mined polymer names/24 properties via API: https://polymerscholar.org/search/api?list=all. Use for lookup only, not as a clean train/test set.",
    "pareto_greedy_reaction": "pareto_greedy_reaction — repo bundle (Jackson Lab OMG_PhysicalProperties/pareto_greedy), read README first. QC property labels on OMG polymers tagged by the 17 reaction IDs + Chemprop checkpoints. Computed properties/AL batches only, not recipes.",
    "lematerial_synth.parquet": "lematerial_synth. ~58k synthesis recipes from open-access papers, 16 material classes incl. polymers: steps, precursors, T/t/P, equipment. ~2.5k judged slice for eval. Procedure text only, no properties.",
    "polymetrix_tg.parquet": "polymetrix_tg.parquet — local table. Curated experimental Tg (K), ~7.3k unique PSMILES, plus class/source/reliability tags. Primary experimental Tg table. Not Tm, permeability, or MD labels.",
    "opc25.csv": "opc25.csv — local table. NeurIPS 2025 Open Polymer Challenge train (~8k P-SMILES), sparse MD labels: Tg, FFV, Tc (thermal conductivity), density, Rg. Use for multi-task MD property prediction; don't mix test IDs back in.",
    "polyomics": "polyomics — HuggingFace dataset. RadonPy MD corpus: >105k polymers, 43 properties + χ vs 19 solvents, >7M entries. Use for simulated bulk properties/Sim2Real pretrain, not experimental Tg.",
    "PI1M.csv": "PI1M.csv — local table. ~1M generative p-SMILES from an RNN trained on PolyInfo + synthetic-accessibility (SA) score. Academic use; pretraining/augmentation only, no property labels.",
    "PI1M_v2.csv": "PI1M_v2.csv — local table. 1M p-SMILES + SA scores, updated version of PI1M.csv. Pretraining/augmentation only, no property labels.",
    "PropagationQuantumChem.csv": "PropagationQuantumChem.csv — local table. CopDDB (2024-03-12): 25 DFT descriptors (barriers, reaction energies, SOMO/HOMO/LUMO, buried volume, logP, TS geometry) for radical–monomer pairs, 50 monomers. Reaction-level QC, not bulk polymer properties.",
    "bcdb_phase_behavior.parquet": "bcdb_phase_behavior.parquet — local table. BCDB melt-phase data: >5,400 literature di-/multi-block measurements (BigSMILES, morphology, DOI) + SCFT rows. Block-copolymer phase behavior only.",
    "omg_monomers.csv": "omg_monomers.csv — local table. OMG virtual monomer library (CRUs), Jackson Lab pipeline (Zenodo 7556992). Monomer-level only; see omg_polymers.csv for assembled polymers.",
    "omg_polymers.csv": "omg_polymers.csv — local table. ~12M linear homopolymer CRUs from 17 template reactions on OMG monomers. No property labels; see pareto_greedy_reaction for QC labels on a subset.",
    "OpenMaterialsGuide.parquet": "OpenMaterialsGuide.parquet — local table. OMG24/AlchemyBench: 17.7k NL synthesis recipes (text, materials, process, characterization, pdf_url). Free-text recipes only, no properties.",
    "final_polymer_properties_fromliterature.csv": "OpenPoly wide property matrix. Columns: Name, PSMILES, ~26–28 property fields with units in headers, PSMILES_2, PSMILES_4. Values are curated/aggregated literature measurements; many cells empty. Primary OpenPoly ML table.",
    "final_polymer_property_counts_fromliterature.csv": "OpenPoly two-column index: Property Name, Number. Raw literature occurrence counts before unique-polymer collapse (e.g. Tg 58,755; Tm 37,725). Use only as coverage stats, never as regression labels.",
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
    "smipoly" : "[Python] SMiPoly (Small Molecules into Polymers)” is rule-based virtual library generator for discovery of functional polymers",
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
}