description = [
    {
        "description": "Estimate the glass transition temperature of a miscible copolymer or polymer blend with the Fox equation 1/Tg_mix = sum(w_i/Tg_i). Component Tgs must be in Kelvin; weight fractions should sum to ~1. Valid only for a single miscible Tg.",
        "name": "estimate_polymer_tg_from_fox_equation",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Weight fraction of each component (list of floats that should sum to ~1.0). Length must match component_tgs_k.",
                "name": "weight_fractions",
                "type": "list[float]",
            },
            {
                "default": None,
                "description": "Glass transition temperature of each pure component in Kelvin. Do not pass Celsius.",
                "name": "component_tgs_k",
                "type": "list[float]",
            },
        ],
    },
    {
        "description": "Estimate binary-blend Tg with the Gordon–Taylor equation Tg = (w_A Tg_A + k w_B Tg_B) / (w_A + k w_B). Temperatures in Kelvin. k=1 recovers a linear mixing rule.",
        "name": "estimate_polymer_tg_gordon_taylor",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Weight fraction of component A; w_B is taken as 1 - w_A.",
                "name": "weight_fraction_a",
                "type": "float",
            },
            {
                "default": None,
                "description": "Tg of pure component A in Kelvin.",
                "name": "tg_a_k",
                "type": "float",
            },
            {
                "default": None,
                "description": "Tg of pure component B in Kelvin.",
                "name": "tg_b_k",
                "type": "float",
            },
            {
                "default": None,
                "description": "Gordon–Taylor k parameter (positive).",
                "name": "k",
                "type": "float",
            },
        ],
    },
    {
        "description": "Estimate Tg versus number-average molar mass with the Flory–Fox relation Tg(Mn) = Tg_infinity - K/Mn. Returns Tg in Kelvin.",
        "name": "estimate_tg_flory_fox_from_mn",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "High-molecular-weight limiting Tg in Kelvin.",
                "name": "tg_infinity_k",
                "type": "float",
            },
            {
                "default": None,
                "description": "Empirical Flory–Fox constant K with units K * g/mol.",
                "name": "k_flory_fox",
                "type": "float",
            },
            {
                "default": None,
                "description": "Number-average molar mass Mn in g/mol.",
                "name": "mn_g_per_mol",
                "type": "float",
            },
        ],
    },
    {
        "description": "Compute the number-average degree of polymerization Xn from the Carothers equation. Equimolar case Xn = 1/(1-p); with stoichiometric imbalance r<=1, Xn = (1+r)/(1+r-2rp).",
        "name": "carothers_xn_linear",
        "optional_parameters": [
            {
                "default": 1.0,
                "description": "Stoichiometric ratio r of limiting to excess bifunctional monomer, in (0, 1]. Use 1.0 for exact stoichiometry.",
                "name": "stoichiometric_ratio_r",
                "type": "float",
            },
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "Extent of reaction p in [0, 1).",
                "name": "conversion_p",
                "type": "float",
            },
        ],
    },
    {
        "description": "For linear equimolar step-growth (most probable distribution), return Xn, Xw, Mn, Mw and PDI=1+p from conversion p and repeat-unit mass M0.",
        "name": "carothers_mw_pdi_linear",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Extent of reaction p in [0, 1).",
                "name": "conversion_p",
                "type": "float",
            },
            {
                "default": None,
                "description": "Repeat-unit molar mass M0 in g/mol.",
                "name": "repeat_unit_mass_g_per_mol",
                "type": "float",
            },
        ],
    },
    {
        "description": "Modified Carothers equation for multifunctional step-growth: Xn = 2 / (2 - p f_av). Raises if 2 - p f_av <= 0 (at or past gelation).",
        "name": "modified_carothers_xn_branching",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Extent of reaction p in [0, 1].",
                "name": "conversion_p",
                "type": "float",
            },
            {
                "default": None,
                "description": "Number-average functionality f_av.",
                "name": "average_functionality_fav",
                "type": "float",
            },
        ],
    },
    {
        "description": "Flory–Stockmayer gel-point conversion. If f_av is given, pc = 2/f_av. If branch functionality f of an RA_f + RB_2 system is given, pc = 1/sqrt(r(f-1)). Provide exactly one of the two functionality arguments.",
        "name": "flory_stockmayer_gel_point",
        "optional_parameters": [
            {
                "default": None,
                "description": "Average functionality f_av for the simple Carothers gel criterion pc=2/f_av. Mutually exclusive with branch_functionality_f.",
                "name": "average_functionality_fav",
                "type": "float",
            },
            {
                "default": 1.0,
                "description": "Stoichiometric ratio r used with branch_functionality_f.",
                "name": "stoichiometric_ratio_r",
                "type": "float",
            },
            {
                "default": None,
                "description": "Functionality f>2 of the branching monomer in an RA_f + RB_2 system. Mutually exclusive with average_functionality_fav.",
                "name": "branch_functionality_f",
                "type": "float",
            },
        ],
        "required_parameters": [],
    },
    {
        "description": "Viscosity-average molar mass from the Mark–Houwink–Sakurada equation M = ([eta]/K)^(1/a). [eta] in dL/g; K in consistent units.",
        "name": "mark_houwink_molecular_weight",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Intrinsic viscosity [eta] in dL/g.",
                "name": "intrinsic_viscosity_dl_per_g",
                "type": "float",
            },
            {
                "default": None,
                "description": "Mark–Houwink K constant.",
                "name": "k_mh",
                "type": "float",
            },
            {
                "default": None,
                "description": "Mark–Houwink exponent a (typically 0.5–0.8 in a good solvent).",
                "name": "a_mh",
                "type": "float",
            },
        ],
    },
    {
        "description": "Intrinsic viscosity from Mark–Houwink–Sakurada: [eta] = K * M^a.",
        "name": "mark_houwink_intrinsic_viscosity",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Molar mass M in g/mol.",
                "name": "molar_mass_g_per_mol",
                "type": "float",
            },
            {
                "default": None,
                "description": "Mark–Houwink K constant.",
                "name": "k_mh",
                "type": "float",
            },
            {
                "default": None,
                "description": "Mark–Houwink exponent a.",
                "name": "a_mh",
                "type": "float",
            },
        ],
    },
    {
        "description": "Compute Mn, Mw, Mz, PDI and optional Mv from a discrete molar-mass histogram of slice masses Mi and chain counts Ni.",
        "name": "molar_mass_averages_from_histogram",
        "optional_parameters": [
            {
                "default": None,
                "description": "Mark–Houwink exponent a used only if Mv is requested.",
                "name": "mark_houwink_a",
                "type": "float",
            },
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "Slice molar masses Mi in g/mol.",
                "name": "molar_masses",
                "type": "list[float]",
            },
            {
                "default": None,
                "description": "Number (or mole) of chains Ni in each slice.",
                "name": "number_counts",
                "type": "list[float]",
            },
        ],
    },
    {
        "description": "Instantaneous copolymer composition F1 from the Mayo–Lewis copolymer equation given feed mole fraction f1 and reactivity ratios r1, r2.",
        "name": "mayo_lewis_instantaneous_composition",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Instantaneous mole fraction of monomer 1 in the feed (f1) in [0, 1].",
                "name": "monomer_mole_fraction_f1",
                "type": "float",
            },
            {
                "default": None,
                "description": "Reactivity ratio r1 = k11/k12.",
                "name": "r1",
                "type": "float",
            },
            {
                "default": None,
                "description": "Reactivity ratio r2 = k22/k21.",
                "name": "r2",
                "type": "float",
            },
        ],
    },
    {
        "description": "Feed mole fraction f1 of an azeotropic copolymerization (F1=f1). Returns None if no physical azeotrope exists in (0, 1).",
        "name": "azeotropic_copolymer_feed",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Reactivity ratio r1.",
                "name": "r1",
                "type": "float",
            },
            {
                "default": None,
                "description": "Reactivity ratio r2.",
                "name": "r2",
                "type": "float",
            },
        ],
    },
    {
        "description": "Number-average DP including chain transfer to an added agent via the Mayo equation 1/Xn = 1/Xn0 + Cs [S]/[M].",
        "name": "mayo_chain_transfer_xn",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Xn in the absence of the added transfer agent.",
                "name": "xn_without_transfer",
                "type": "float",
            },
            {
                "default": None,
                "description": "Chain-transfer constant Cs = ktr,S / kp.",
                "name": "transfer_constant_cs",
                "type": "float",
            },
            {
                "default": None,
                "description": "Chain-transfer agent concentration [S].",
                "name": "chain_transfer_agent_conc",
                "type": "float",
            },
            {
                "default": None,
                "description": "Monomer concentration [M].",
                "name": "monomer_conc",
                "type": "float",
            },
        ],
    },
    {
        "description": "Steady-state free-radical polymerization rate Rp = kp [M] (f kd [I]/kt)^{1/2} and kinetic chain length. Rate constants must share a consistent time unit.",
        "name": "free_radical_steady_state_rp",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Propagation rate constant kp.",
                "name": "kp",
                "type": "float",
            },
            {
                "default": None,
                "description": "Termination rate constant kt consistent with [M*] = (f kd [I]/kt)^{1/2}.",
                "name": "kt",
                "type": "float",
            },
            {
                "default": None,
                "description": "Initiator efficiency f in (0, 1].",
                "name": "f_initiator",
                "type": "float",
            },
            {
                "default": None,
                "description": "Initiator decomposition rate constant kd.",
                "name": "kd",
                "type": "float",
            },
            {
                "default": None,
                "description": "Initiator concentration [I].",
                "name": "initiator_conc",
                "type": "float",
            },
            {
                "default": None,
                "description": "Monomer concentration [M].",
                "name": "monomer_conc",
                "type": "float",
            },
        ],
    },
    {
        "description": "Williams–Landel–Ferry time-temperature shift factor a_T. log10(a_T) = -C1 (T-Tref)/(C2+T-Tref). Universal constants C1=17.44, C2=51.6 K apply when Tref = Tg.",
        "name": "wlf_shift_factor",
        "optional_parameters": [
            {
                "default": 17.44,
                "description": "WLF C1 constant.",
                "name": "c1",
                "type": "float",
            },
            {
                "default": 51.6,
                "description": "WLF C2 constant in Kelvin.",
                "name": "c2",
                "type": "float",
            },
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "Temperature T in Kelvin.",
                "name": "temperature_k",
                "type": "float",
            },
            {
                "default": None,
                "description": "Reference temperature in Kelvin (often Tg).",
                "name": "t_ref_k",
                "type": "float",
            },
        ],
    },
    {
        "description": "Ceiling temperature of reversible addition polymerization Tc = DeltaH / (DeltaS + R ln[M]). Use polymerization DeltaH and DeltaS (typically both negative).",
        "name": "ceiling_temperature_k",
        "optional_parameters": [
            {
                "default": 1.0,
                "description": "Monomer concentration [M] in mol/L (1 M standard state).",
                "name": "monomer_conc",
                "type": "float",
            },
            {
                "default": 8.314462618,
                "description": "Gas constant R in J/mol/K.",
                "name": "gas_constant",
                "type": "float",
            },
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "Enthalpy of polymerization in J/mol (typically negative).",
                "name": "delta_h_j_per_mol",
                "type": "float",
            },
            {
                "default": None,
                "description": "Entropy of polymerization in J/mol/K (typically negative).",
                "name": "delta_s_j_per_mol_k",
                "type": "float",
            },
        ],
    },
    {
        "description": "Flory–Huggins mixing free energy per lattice site: phi/N ln phi + (1-phi) ln(1-phi) + chi phi (1-phi). Also returns the value in J per mole of sites.",
        "name": "flory_huggins_mixing_free_energy",
        "optional_parameters": [
            {
                "default": 8.314462618,
                "description": "Gas constant R in J/mol/K.",
                "name": "gas_constant",
                "type": "float",
            },
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "Polymer volume fraction phi in (0, 1).",
                "name": "volume_fraction_polymer",
                "type": "float",
            },
            {
                "default": None,
                "description": "Flory interaction parameter chi.",
                "name": "chi",
                "type": "float",
            },
            {
                "default": None,
                "description": "Number of lattice sites per chain N.",
                "name": "degree_of_polymerization_n",
                "type": "float",
            },
            {
                "default": None,
                "description": "Temperature in Kelvin.",
                "name": "temperature_k",
                "type": "float",
            },
        ],
    },
    {
        "description": "Convert component weight fractions to mole fractions given component molar masses.",
        "name": "weight_fraction_to_mole_fraction",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Weight fractions of each component.",
                "name": "weight_fractions",
                "type": "list[float]",
            },
            {
                "default": None,
                "description": "Molar mass of each component in g/mol.",
                "name": "molar_masses_g_per_mol",
                "type": "list[float]",
            },
        ],
    },
    {
        "description": "Arrhenius rate constant k = A exp(-Ea/RT).",
        "name": "arrhenius_rate_constant",
        "optional_parameters": [
            {
                "default": 8.314462618,
                "description": "Gas constant R in J/mol/K. If Ea is in cal/mol, pass R=1.987.",
                "name": "gas_constant",
                "type": "float",
            },
        ],
        "required_parameters": [
            {
                "default": None,
                "description": "Pre-exponential factor A in the same units as k.",
                "name": "pre_exponential_a",
                "type": "float",
            },
            {
                "default": None,
                "description": "Activation energy Ea in J/mol when R is 8.314.",
                "name": "ea_j_per_mol",
                "type": "float",
            },
            {
                "default": None,
                "description": "Temperature in Kelvin.",
                "name": "temperature_k",
                "type": "float",
            },
        ],
    },
    {
        "description": "Irreversible first-order conversion X = 1 - exp(-k t).",
        "name": "first_order_conversion",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "First-order rate constant k (time^-1).",
                "name": "rate_constant_k",
                "type": "float",
            },
            {
                "default": None,
                "description": "Reaction time t in the inverse units of k.",
                "name": "time",
                "type": "float",
            },
        ],
    },
    {
        "description": "First-order half-life t_1/2 = ln(2)/k.",
        "name": "first_order_half_life",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "First-order rate constant k (time^-1).",
                "name": "rate_constant_k",
                "type": "float",
            },
        ],
    },
    {
        "description": "Theoretical product moles/mass and percent yield from limiting-reagent stoichiometry.",
        "name": "theoretical_and_percent_yield",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Moles of the limiting reagent.",
                "name": "moles_limiting_reagent",
                "type": "float",
            },
            {
                "default": None,
                "description": "Stoichiometric coefficient of the product in the balanced equation.",
                "name": "stoichiometric_product_coeff",
                "type": "float",
            },
            {
                "default": None,
                "description": "Stoichiometric coefficient of the limiting reagent.",
                "name": "stoichiometric_limiting_coeff",
                "type": "float",
            },
            {
                "default": None,
                "description": "Product molar mass in g/mol.",
                "name": "product_molar_mass_g_per_mol",
                "type": "float",
            },
            {
                "default": None,
                "description": "Isolated product mass in grams.",
                "name": "isolated_product_mass_g",
                "type": "float",
            },
        ],
    },
    {
        "description": "Atom economy (%) = 100 * M_product / sum(nu_i M_i) for a balanced reaction.",
        "name": "atom_economy_percent",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Molar mass of the desired product in g/mol.",
                "name": "product_molar_mass_g_per_mol",
                "type": "float",
            },
            {
                "default": None,
                "description": "Molar masses of reactants in g/mol.",
                "name": "reactant_molar_masses_g_per_mol",
                "type": "list[float]",
            },
            {
                "default": None,
                "description": "Stoichiometric coefficients of those reactants.",
                "name": "reactant_stoich_coeffs",
                "type": "list[float]",
            },
        ],
    },
    {
        "description": "Sheldon environmental factor E = mass_waste / mass_product.",
        "name": "e_factor",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Mass of waste in grams (or any mass unit).",
                "name": "mass_waste_g",
                "type": "float",
            },
            {
                "default": None,
                "description": "Mass of isolated product in the same unit.",
                "name": "mass_product_g",
                "type": "float",
            },
        ],
    },
    {
        "description": "Dilution formula C2 = C1 V1 / V2. Concentration units must match; volume units must match.",
        "name": "dilute_solution",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Initial concentration C1.",
                "name": "c1",
                "type": "float",
            },
            {
                "default": None,
                "description": "Initial volume V1.",
                "name": "v1",
                "type": "float",
            },
            {
                "default": None,
                "description": "Final volume V2.",
                "name": "v2",
                "type": "float",
            },
        ],
    },
    {
        "description": "Convert mass to moles: n = m / M.",
        "name": "moles_from_mass",
        "optional_parameters": [],
        "required_parameters": [
            {
                "default": None,
                "description": "Mass in grams.",
                "name": "mass_g",
                "type": "float",
            },
            {
                "default": None,
                "description": "Molar mass in g/mol.",
                "name": "molar_mass_g_per_mol",
                "type": "float",
            },
        ],
    },
]