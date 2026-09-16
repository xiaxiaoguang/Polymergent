description = [
    {
        "description": "Parse a polymer repeat-unit SMILES that uses dummy attachment points (* or [*:n]). Returns dummy count, formula, exact mass, and whether the mer looks like a linear A–A type (exactly two dummies).",
        "name": "parse_repeat_unit_smiles",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Repeat-unit SMILES, e.g. '*CC(*)C' or '[*]OCCOC(=O)c1ccc(C(=O)O[*])cc1'.",
                "name": "smiles",
                "type": "str",
            },
        ],
    },
    {
        "description": "Replace dummy attachment points on a repeat-unit SMILES with implicit hydrogens so the mer can be treated as a small molecule for descriptors or QM.",
        "name": "cap_repeat_unit_with_hydrogen",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Repeat-unit SMILES containing dummy atoms.",
                "name": "smiles",
                "type": "str",
            },
        ],
    },
    {
        "description": "Build a linear oligomer SMILES by joining n copies of a two-dummy repeat unit head-to-tail and capping ends with hydrogen.",
        "name": "build_linear_oligomer_smiles",
        "optional_parameters": [
            {
                "default": True,
                "description": "If true, chain ends are implicit hydrogens after dummy removal.",
                "name": "cap_with_hydrogen",
                "type": "bool",
            },
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "Repeat-unit SMILES with exactly two dummy atoms.",
                "name": "repeat_unit_smiles",
                "type": "str",
            },
            {
                "default": None,
                "description": "Number of repeat units in the oligomer (>=1).",
                "name": "n_repeats",
                "type": "int",
            },
        ],
    },
    {
        "description": "Compute RDKit 2D descriptors of a repeat unit (optionally H-capped): MW, TPSA, Crippen logP/MR, HBD/HBA, rotatable bonds, ring counts, fraction Csp3, Bertz complexity.",
        "name": "repeat_unit_descriptors",
        "optional_parameters": [
            {
                "default": True,
                "description": "Cap dummy attachment points with H before computing descriptors.",
                "name": "cap_dummies",
                "type": "bool",
            },
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "Repeat-unit or small-molecule SMILES.",
                "name": "smiles",
                "type": "str",
            },
        ],
    },
    {
        "description": "Tanimoto similarity of two SMILES strings from Morgan fingerprints (default radius 2, 2048 bits).",
        "name": "morgan_tanimoto_similarity",
        "optional_parameters": [
            {
                "default": 2,
                "description": "Morgan radius.",
                "name": "radius",
                "type": "int",
            },
            {
                "default": 2048,
                "description": "Fingerprint length in bits.",
                "name": "n_bits",
                "type": "int",
            },
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "First SMILES.",
                "name": "smiles_a",
                "type": "str",
            },
            {
                "default": None,
                "description": "Second SMILES.",
                "name": "smiles_b",
                "type": "str",
            },
        ],
    },
    {
        "description": "Count occurrences of each user-supplied SMARTS pattern on a molecule.",
        "name": "count_smarts_substructures",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Molecule SMILES.",
                "name": "smiles",
                "type": "str",
            },
            {
                "default": None,
                "description": "List of SMARTS strings to count.",
                "name": "smarts_patterns",
                "type": "list[str]",
            },
        ],
    },
    {
        "description": "Count common polymer-relevant functional groups (ester, amide, vinyl, acrylate, isocyanate, epoxide, urethane, etc.) on a SMILES.",
        "name": "count_common_polymer_functional_groups",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Monomer or repeat-unit SMILES.",
                "name": "smiles",
                "type": "str",
            },
        ],
    },
    {
        "description": "Invert the binary Fox equation to get the weight fraction of component A that yields a target mixture Tg. Target must lie between the two pure Tgs (Kelvin).",
        "name": "fox_weight_fraction_for_target_tg",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Desired mixture Tg in Kelvin.",
                "name": "target_tg_k",
                "type": "float",
            },
            {
                "default": None,
                "description": "Tg of pure A in Kelvin.",
                "name": "tg_a_k",
                "type": "float",
            },
            {
                "default": None,
                "description": "Tg of pure B in Kelvin.",
                "name": "tg_b_k",
                "type": "float",
            },
        ],
    },
    {
        "description": "Invert the linear Carothers equation to find the conversion p required to reach a target number-average degree of polymerization Xn.",
        "name": "carothers_conversion_for_target_xn",
        "optional_parameters": [
            {
                "default": 1.0,
                "description": "Stoichiometric ratio r in (0, 1].",
                "name": "stoichiometric_ratio_r",
                "type": "float",
            },
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "Target Xn (>=1).",
                "name": "target_xn",
                "type": "float",
            },
        ],
    },
    {
        "description": "Embed a (H-capped) repeat unit with RDKit MMFF, then run a PySCF HF or DFT single point. Returns total energy (Ha), HOMO/LUMO/gap (eV), and dipole (Debye). Screening-quality only; default B3LYP/STO-3G with a heavy-atom cap.",
        "name": "dft_homo_lumo_repeat_unit",
        "optional_parameters": [
            {
                "default": "sto-3g",
                "description": "PySCF basis set name (sto-3g, 3-21g, def2-svp, ...).",
                "name": "basis",
                "type": "str",
            },
            {
                "default": "b3lyp",
                "description": "DFT functional. Ignored when use_hf=True.",
                "name": "xc",
                "type": "str",
            },
            {
                "default": False,
                "description": "If true, run Hartree–Fock instead of DFT.",
                "name": "use_hf",
                "type": "bool",
            },
            {
                "default": True,
                "description": "Cap dummy atoms with H before the QM job.",
                "name": "cap_dummies",
                "type": "bool",
            },
            {
                "default": 25,
                "description": "Refuse jobs larger than this many heavy atoms.",
                "name": "max_heavy_atoms",
                "type": "int",
            },
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "Repeat-unit or small-molecule SMILES.",
                "name": "smiles",
                "type": "str",
            },
        ],
    },
    {
        "description": "Convenience RHF/STO-3G single point on a capped mer. Same return fields as dft_homo_lumo_repeat_unit.",
        "name": "hf_sto3g_energy_smiles",
        "optional_parameters": [
            {
                "default": True,
                "description": "Cap dummy atoms with H.",
                "name": "cap_dummies",
                "type": "bool",
            },
            {
                "default": 25,
                "description": "Heavy-atom safety cap.",
                "name": "max_heavy_atoms",
                "type": "int",
            },
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "Repeat-unit or small-molecule SMILES.",
                "name": "smiles",
                "type": "str",
            },
        ],
    },
    {
        "description": "Estimate how DFT/HF cost scales if the agent runs QM on an n-mer instead of the capped monomer (heavy-atom count and N^4 ratio).",
        "name": "estimate_oligomer_scaling_cost",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Two-dummy repeat-unit SMILES.",
                "name": "repeat_unit_smiles",
                "type": "str",
            },
            {
                "default": None,
                "description": "Oligomer length n.",
                "name": "n_repeats",
                "type": "int",
            },
        ],
    },
]