_USAGE = (
    "PLUMBING. Call at most once per monomer. Bind the return in code "
    "(ru = f(...)); do not print, log, or paste the return into the assistant "
    "message. On success the return is a short SMILES or role string only."
)

description = [
    {
        "description": _USAGE + " Canonicalize a SMILES string. Returns canonical SMILES. Raises on parse/sanitize failure.",
        "name": "validate_and_canonicalize_smiles",
        "optional_parameters": [],
        "required_parameters": [
            {"default": None, "description": "Raw SMILES.", "name": "smiles", "type": "str"},
        ],
    },
    {
        "description": _USAGE + " Fix common SMILES typos (Cl casing, X dummy). Returns canonical SMILES. Raises if still invalid.",
        "name": "autocorrect_smiles",
        "optional_parameters": [],
        "required_parameters": [
            {"default": None, "description": "Possibly typo-ridden SMILES.", "name": "smiles", "type": "str"},
        ],
    },
    {
        "description": _USAGE + " Return one token: linear_repeat_unit | cyclic_lactone | cyclic_lactam | cyclic_anhydride | no_dummy | one_dummy. Prefer prepare_repeat_unit_from_name_or_smiles instead of this plus open_*.",
        "name": "inspect_polymer_smiles_convention",
        "optional_parameters": [],
        "required_parameters": [
            {"default": None, "description": "SMILES to classify.", "name": "smiles", "type": "str"},
        ],
    },
    {
        "description": _USAGE + " Open lactone/lactam/anhydride to a 2-dummy mer SMILES.",
        "name": "open_cyclic_monomer_to_repeat_unit",
        "optional_parameters": [
            {"default": "auto", "description": "auto|lactone|lactam|anhydride", "name": "monomer_class", "type": "str"},
        ],
        "required_parameters": [
            {"default": None, "description": "Closed cyclic SMILES.", "name": "smiles", "type": "str"},
        ],
    },
    {
        "description": _USAGE + " Name to closed SMILES. Local table then PubChem. Prefer prepare_repeat_unit_from_name_or_smiles.",
        "name": "resolve_monomer_name_to_smiles",
        "optional_parameters": [
            {"default": True, "description": "Query PubChem on local miss.", "name": "use_pubchem", "type": "bool"},
        ],
        "required_parameters": [
            {"default": None, "description": "Monomer name.", "name": "name", "type": "str"},
        ],
    },
    {
        "description": _USAGE + " PREFERRED single entry. Name or SMILES -> oligomer-ready 2-dummy mer SMILES. Do not also call inspect/open/resolve on the same input.",
        "name": "prepare_repeat_unit_from_name_or_smiles",
        "optional_parameters": [
            {"default": 2, "description": "Silent oligomer build test length.", "name": "n_repeats_to_test", "type": "int"},
        ],
        "required_parameters": [
            {"default": None, "description": "Name or SMILES.", "name": "name_or_smiles", "type": "str"},
        ],
    },
]