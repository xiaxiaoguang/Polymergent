"""Polymer science and chemical-synthesis tool module.

Plain, importable Python. Docstrings are for humans/IDEs.
LLM-facing schemas live in polymer_science_description.py.
"""

from __future__ import annotations

import math


def estimate_polymer_tg_from_fox_equation(
    weight_fractions: list[float],
    component_tgs_k: list[float],
) -> float:
    """Estimate a copolymer/blend glass transition temperature with the Fox equation.

    1 / Tg_mix = sum(w_i / Tg_i)

    Args:
        weight_fractions: Weight fraction of each component (should sum to ~1.0).
        component_tgs_k: Glass transition temperature of each pure component, in Kelvin.

    Returns:
        float: Estimated mixture Tg in Kelvin.
    """
    if len(weight_fractions) != len(component_tgs_k):
        raise ValueError("weight_fractions and component_tgs_k must be the same length")
    if any(tg <= 0 for tg in component_tgs_k):
        raise ValueError("All component Tgs must be positive Kelvin")
    inverse_tg = sum(w / tg for w, tg in zip(weight_fractions, component_tgs_k, strict=True))
    if inverse_tg <= 0:
        raise ValueError("Computed non-positive 1/Tg; check inputs")
    return 1.0 / inverse_tg


def estimate_polymer_tg_gordon_taylor(
    weight_fraction_a: float,
    tg_a_k: float,
    tg_b_k: float,
    k: float,
) -> float:
    """Estimate binary-blend Tg with the Gordon–Taylor equation.

    Tg = (w_A * Tg_A + k * w_B * Tg_B) / (w_A + k * w_B)

    Args:
        weight_fraction_a: Weight fraction of component A (w_B = 1 - w_A).
        tg_a_k: Tg of pure A in Kelvin.
        tg_b_k: Tg of pure B in Kelvin.
        k: Gordon–Taylor k parameter (often ~ rho_A * dTgB / (rho_B * dTgA)).

    Returns:
        float: Estimated mixture Tg in Kelvin.
    """
    if not 0.0 <= weight_fraction_a <= 1.0:
        raise ValueError("weight_fraction_a must be in [0, 1]")
    if tg_a_k <= 0 or tg_b_k <= 0:
        raise ValueError("Tgs must be positive Kelvin")
    if k <= 0:
        raise ValueError("Gordon–Taylor k must be positive")
    w_a = weight_fraction_a
    w_b = 1.0 - w_a
    denom = w_a + k * w_b
    if denom <= 0:
        raise ValueError("Degenerate Gordon–Taylor denominator")
    return (w_a * tg_a_k + k * w_b * tg_b_k) / denom


def estimate_tg_flory_fox_from_mn(
    tg_infinity_k: float,
    k_flory_fox: float,
    mn_g_per_mol: float,
) -> float:
    """Estimate Tg vs number-average molar mass with the Flory–Fox equation.

    Tg(Mn) = Tg_infinity - K / Mn

    Args:
        tg_infinity_k: High-MW limiting Tg in Kelvin.
        k_flory_fox: Empirical free-volume constant K (K * g/mol).
        mn_g_per_mol: Number-average molar mass Mn (g/mol).

    Returns:
        float: Estimated Tg in Kelvin.
    """
    if mn_g_per_mol <= 0:
        raise ValueError("Mn must be positive")
    return tg_infinity_k - k_flory_fox / mn_g_per_mol


def carothers_xn_linear(
    conversion_p: float,
    stoichiometric_ratio_r: float = 1.0,
) -> float:
    """Number-average degree of polymerization from the Carothers equation.

    Equimolar A-A/B-B or A-B: Xn = 1 / (1 - p)
    With stoichiometric imbalance r <= 1: Xn = (1 + r) / (1 + r - 2 r p)

    Args:
        conversion_p: Extent of reaction p in [0, 1).
        stoichiometric_ratio_r: Mole ratio of limiting to excess bifunctional
            monomer (r <= 1). Use 1.0 for exact stoichiometry.

    Returns:
        float: Number-average degree of polymerization Xn.
    """
    if not 0.0 <= conversion_p < 1.0:
        raise ValueError("conversion_p must be in [0, 1)")
    if not 0.0 < stoichiometric_ratio_r <= 1.0:
        raise ValueError("stoichiometric_ratio_r must be in (0, 1]")
    r = stoichiometric_ratio_r
    p = conversion_p
    denom = 1.0 + r - 2.0 * r * p
    if denom <= 0:
        raise ValueError("Carothers denominator non-positive; check p and r")
    return (1.0 + r) / denom


def carothers_mw_pdi_linear(
    conversion_p: float,
    repeat_unit_mass_g_per_mol: float,
) -> dict[str, float]:
    """Mn, Mw, Xn, Xw and PDI for linear equimolar step-growth (most probable).

    Xn = 1/(1-p), Xw = (1+p)/(1-p), Mn = M0*Xn, Mw = M0*Xw, PDI = 1+p

    Args:
        conversion_p: Extent of reaction p in [0, 1).
        repeat_unit_mass_g_per_mol: Repeat-unit molar mass M0 (g/mol).

    Returns:
        dict with keys xn, xw, mn, mw, pdi.
    """
    if not 0.0 <= conversion_p < 1.0:
        raise ValueError("conversion_p must be in [0, 1)")
    if repeat_unit_mass_g_per_mol <= 0:
        raise ValueError("repeat_unit_mass_g_per_mol must be positive")
    p = conversion_p
    xn = 1.0 / (1.0 - p)
    xw = (1.0 + p) / (1.0 - p)
    mn = repeat_unit_mass_g_per_mol * xn
    mw = repeat_unit_mass_g_per_mol * xw
    return {"xn": xn, "xw": xw, "mn": mn, "mw": mw, "pdi": 1.0 + p}


def modified_carothers_xn_branching(
    conversion_p: float,
    average_functionality_fav: float,
) -> float:
    """Xn for multifunctional step-growth (modified Carothers).

    Xn = 2 / (2 - p * f_av)

    Args:
        conversion_p: Extent of reaction p.
        average_functionality_fav: Number-average functionality f_av > 0.

    Returns:
        float: Number-average degree of polymerization Xn.
    """
    if not 0.0 <= conversion_p <= 1.0:
        raise ValueError("conversion_p must be in [0, 1]")
    if average_functionality_fav <= 0:
        raise ValueError("average_functionality_fav must be positive")
    denom = 2.0 - conversion_p * average_functionality_fav
    if denom <= 0:
        raise ValueError("At or past gel point (2 - p*f_av <= 0)")
    return 2.0 / denom


def flory_stockmayer_gel_point(
    average_functionality_fav: float | None = None,
    stoichiometric_ratio_r: float = 1.0,
    branch_functionality_f: float | None = None,
) -> float:
    """Critical conversion at gelation (Flory–Stockmayer).

    If f_av is given: pc = 2 / f_av
    If branch functionality f of an RA_f + RB_2 system is given:
        pc = 1 / sqrt(r * (f - 1))

    Provide exactly one of average_functionality_fav or branch_functionality_f.

    Args:
        average_functionality_fav: Optional f_av for the simple Carothers gel criterion.
        stoichiometric_ratio_r: r = (equiv A)/(equiv B) used with branch_functionality_f.
        branch_functionality_f: Functionality of the branching monomer (f > 2).

    Returns:
        float: Critical extent of reaction pc in (0, 1].
    """
    if (average_functionality_fav is None) == (branch_functionality_f is None):
        raise ValueError("Provide exactly one of average_functionality_fav or branch_functionality_f")
    if average_functionality_fav is not None:
        if average_functionality_fav <= 2:
            raise ValueError("Gelation requires f_av > 2")
        return 2.0 / average_functionality_fav
    assert branch_functionality_f is not None
    if branch_functionality_f <= 2:
        raise ValueError("branch_functionality_f must be > 2")
    if stoichiometric_ratio_r <= 0:
        raise ValueError("stoichiometric_ratio_r must be positive")
    pc = 1.0 / math.sqrt(stoichiometric_ratio_r * (branch_functionality_f - 1.0))
    return pc


def mark_houwink_molecular_weight(
    intrinsic_viscosity_dl_per_g: float,
    k_mh: float,
    a_mh: float,
) -> float:
    """Viscosity-average molar mass from the Mark–Houwink–Sakurada equation.

    [eta] = K * M^a  =>  M = ([eta] / K)^(1/a)

    Args:
        intrinsic_viscosity_dl_per_g: Intrinsic viscosity [eta] (dL/g).
        k_mh: Mark–Houwink K in dL/g * (g/mol)^(-a).
        a_mh: Mark–Houwink exponent a (typically 0.5–0.8 in good solvent).

    Returns:
        float: Viscosity-average molar mass Mv (g/mol).
    """
    if intrinsic_viscosity_dl_per_g <= 0 or k_mh <= 0:
        raise ValueError("[eta] and K must be positive")
    if a_mh == 0:
        raise ValueError("Mark–Houwink a must be nonzero")
    return (intrinsic_viscosity_dl_per_g / k_mh) ** (1.0 / a_mh)


def mark_houwink_intrinsic_viscosity(
    molar_mass_g_per_mol: float,
    k_mh: float,
    a_mh: float,
) -> float:
    """Intrinsic viscosity from Mark–Houwink–Sakurada: [eta] = K * M^a."""
    if molar_mass_g_per_mol <= 0 or k_mh <= 0:
        raise ValueError("M and K must be positive")
    return k_mh * molar_mass_g_per_mol**a_mh


def molar_mass_averages_from_histogram(
    molar_masses: list[float],
    number_counts: list[float],
    mark_houwink_a: float | None = None,
) -> dict[str, float]:
    """Compute Mn, Mw, Mz, PDI (and optional Mv) from a discrete MWD.

    Mn = sum(Ni Mi) / sum(Ni)
    Mw = sum(Ni Mi^2) / sum(Ni Mi)
    Mz = sum(Ni Mi^3) / sum(Ni Mi^2)
    Mv = [sum(Ni Mi^{1+a}) / sum(Ni Mi)]^(1/a) if a is given.

    Args:
        molar_masses: Slice molar masses Mi.
        number_counts: Number (or mole) of chains Ni in each slice.
        mark_houwink_a: Optional MH exponent for Mv.

    Returns:
        dict with mn, mw, mz, pdi, and optionally mv.
    """
    if len(molar_masses) != len(number_counts):
        raise ValueError("molar_masses and number_counts must have the same length")
    if not molar_masses:
        raise ValueError("Empty distribution")
    if any(m <= 0 for m in molar_masses) or any(n < 0 for n in number_counts):
        raise ValueError("Masses must be > 0 and counts >= 0")
    s0 = sum(number_counts)
    s1 = sum(n * m for n, m in zip(number_counts, molar_masses, strict=True))
    s2 = sum(n * m * m for n, m in zip(number_counts, molar_masses, strict=True))
    s3 = sum(n * m * m * m for n, m in zip(number_counts, molar_masses, strict=True))
    if s0 <= 0 or s1 <= 0 or s2 <= 0:
        raise ValueError("Degenerate distribution moments")
    mn = s1 / s0
    mw = s2 / s1
    mz = s3 / s2
    out = {"mn": mn, "mw": mw, "mz": mz, "pdi": mw / mn}
    if mark_houwink_a is not None:
        if mark_houwink_a == 0:
            raise ValueError("mark_houwink_a must be nonzero")
        s_a = sum(n * (m ** (1.0 + mark_houwink_a)) for n, m in zip(number_counts, molar_masses, strict=True))
        out["mv"] = (s_a / s1) ** (1.0 / mark_houwink_a)
    return out


def mayo_lewis_instantaneous_composition(
    monomer_mole_fraction_f1: float,
    r1: float,
    r2: float,
) -> float:
    """Instantaneous copolymer composition F1 from the Mayo–Lewis equation.

    F1 = (r1 f1^2 + f1 f2) / (r1 f1^2 + 2 f1 f2 + r2 f2^2)

    Args:
        monomer_mole_fraction_f1: Instantaneous mole fraction of monomer 1 in the feed (f1).
        r1: Reactivity ratio r1 = k11/k12.
        r2: Reactivity ratio r2 = k22/k21.

    Returns:
        float: Instantaneous mole fraction F1 in the copolymer.
    """
    if not 0.0 <= monomer_mole_fraction_f1 <= 1.0:
        raise ValueError("monomer_mole_fraction_f1 must be in [0, 1]")
    if r1 < 0 or r2 < 0:
        raise ValueError("Reactivity ratios must be non-negative")
    f1 = monomer_mole_fraction_f1
    f2 = 1.0 - f1
    num = r1 * f1 * f1 + f1 * f2
    den = r1 * f1 * f1 + 2.0 * f1 * f2 + r2 * f2 * f2
    if den <= 0:
        raise ValueError("Mayo–Lewis denominator is zero; check f1, r1, r2")
    return num / den


def azeotropic_copolymer_feed(
    r1: float,
    r2: float,
) -> float | None:
    """Feed mole fraction f1 that gives azeotropic copolymerization (F1 = f1).

    f1_az = (1 - r2) / (2 - r1 - r2) when both r1, r2 < 1 or both > 1
    and the azeotrope lies in (0, 1). Returns None if no physical azeotrope.
    """
    if r1 < 0 or r2 < 0:
        raise ValueError("Reactivity ratios must be non-negative")
    denom = 2.0 - r1 - r2
    if denom == 0:
        return None
    f1 = (1.0 - r2) / denom
    if 0.0 < f1 < 1.0 and ((r1 < 1 and r2 < 1) or (r1 > 1 and r2 > 1)):
        return f1
    return None


def mayo_chain_transfer_xn(
    xn_without_transfer: float,
    transfer_constant_cs: float,
    chain_transfer_agent_conc: float,
    monomer_conc: float,
) -> float:
    """Number-average DP with chain transfer (Mayo equation, CTA term only).

    1/Xn = 1/Xn0 + Cs * [S]/[M]

    Args:
        xn_without_transfer: Xn in the absence of the added transfer agent.
        transfer_constant_cs: Cs = ktr,S / kp.
        chain_transfer_agent_conc: [S].
        monomer_conc: [M].

    Returns:
        float: Xn including transfer to S.
    """
    if xn_without_transfer <= 0:
        raise ValueError("xn_without_transfer must be positive")
    if monomer_conc <= 0:
        raise ValueError("monomer_conc must be positive")
    if chain_transfer_agent_conc < 0 or transfer_constant_cs < 0:
        raise ValueError("Cs and [S] must be non-negative")
    inv = 1.0 / xn_without_transfer + transfer_constant_cs * chain_transfer_agent_conc / monomer_conc
    return 1.0 / inv


def free_radical_steady_state_rp(
    kp: float,
    kt: float,
    f_initiator: float,
    kd: float,
    initiator_conc: float,
    monomer_conc: float,
) -> dict[str, float]:
    """Steady-state free-radical polymerization rate and kinetic chain length.

    Rp = kp [M] (f kd [I] / kt)^{1/2}
    nu  = kp [M] / (2 (f kd [I] kt)^{1/2})   (bimolecular termination)

    Rate constants must share a consistent time unit (e.g. s^-1, L mol^-1 s^-1).

    Args:
        kp: Propagation rate constant.
        kt: Termination rate constant (as written in -d[M*]/dt = 2 kt [M*]^2
            convention, use kt consistent with your definition; here Rt = 2 kt [M*]^2
            is absorbed so that [M*] = (f kd [I] / kt)^{1/2}).
        f_initiator: Initiator efficiency f in (0, 1].
        kd: Initiator decomposition rate constant.
        initiator_conc: [I].
        monomer_conc: [M].

    Returns:
        dict with rp (rate of polymerization) and kinetic_chain_length.
    """
    if min(kp, kt, kd, initiator_conc, monomer_conc) <= 0:
        raise ValueError("Rate constants and concentrations must be positive")
    if not 0.0 < f_initiator <= 1.0:
        raise ValueError("f_initiator must be in (0, 1]")
    mstar = math.sqrt(f_initiator * kd * initiator_conc / kt)
    rp = kp * monomer_conc * mstar
    nu = kp * monomer_conc / (2.0 * kt * mstar)
    return {"rp": rp, "radical_conc": mstar, "kinetic_chain_length": nu}


def wlf_shift_factor(
    temperature_k: float,
    t_ref_k: float,
    c1: float = 17.44,
    c2: float = 51.6,
) -> float:
    """Williams–Landel–Ferry time-temperature shift factor a_T.

    log10(a_T) = -C1 (T - Tref) / (C2 + T - Tref)

    Universal constants C1=17.44, C2=51.6 K apply when Tref = Tg.

    Args:
        temperature_k: Temperature T (K).
        t_ref_k: Reference temperature (K), often Tg.
        c1: WLF C1.
        c2: WLF C2 (K).

    Returns:
        float: Shift factor a_T.
    """
    denom = c2 + (temperature_k - t_ref_k)
    if denom == 0:
        raise ValueError("WLF denominator is zero")
    log_at = -c1 * (temperature_k - t_ref_k) / denom
    return 10.0**log_at


def ceiling_temperature_k(
    delta_h_j_per_mol: float,
    delta_s_j_per_mol_k: float,
    monomer_conc: float = 1.0,
    gas_constant: float = 8.314462618,
) -> float:
    """Ceiling temperature for reversible addition polymerization.

    Tc = DeltaH / (DeltaS + R ln[M])

    Use the polymerization convention: DeltaH and DeltaS of polymerization
    (usually both negative). [M] in mol/L with a 1 M standard state.

    Args:
        delta_h_j_per_mol: Enthalpy of polymerization (J/mol), typically negative.
        delta_s_j_per_mol_k: Entropy of polymerization (J/mol/K), typically negative.
        monomer_conc: Equilibrium monomer concentration [M] (mol/L).
        gas_constant: R in J/mol/K.

    Returns:
        float: Ceiling temperature Tc in Kelvin.
    """
    if monomer_conc <= 0:
        raise ValueError("monomer_conc must be positive")
    denom = delta_s_j_per_mol_k + gas_constant * math.log(monomer_conc)
    if denom == 0:
        raise ValueError("Denominator DeltaS + R ln[M] is zero")
    return delta_h_j_per_mol / denom


def flory_huggins_mixing_free_energy(
    volume_fraction_polymer: float,
    chi: float,
    degree_of_polymerization_n: float,
    temperature_k: float,
    gas_constant: float = 8.314462618,
) -> dict[str, float]:
    """Flory–Huggins mixing free energy and chemical-potential ingredients.

    DeltaG_mix / (n_total RT) per site:
        phi/N ln phi + (1-phi) ln(1-phi) + chi phi (1-phi)

    Args:
        volume_fraction_polymer: Polymer volume fraction phi.
        chi: Flory interaction parameter.
        degree_of_polymerization_n: Number of lattice sites per chain N.
        temperature_k: T in Kelvin.
        gas_constant: R.

    Returns:
        dict with dimensionless_delta_g_per_site and delta_g_per_mole_sites (J/mol).
    """
    phi = volume_fraction_polymer
    if not 0.0 < phi < 1.0:
        raise ValueError("volume_fraction_polymer must be in (0, 1)")
    if degree_of_polymerization_n <= 0 or temperature_k <= 0:
        raise ValueError("N and T must be positive")
    dimless = (
        (phi / degree_of_polymerization_n) * math.log(phi)
        + (1.0 - phi) * math.log(1.0 - phi)
        + chi * phi * (1.0 - phi)
    )
    return {
        "dimensionless_delta_g_per_site": dimless,
        "delta_g_per_mole_sites": dimless * gas_constant * temperature_k,
    }


def weight_fraction_to_mole_fraction(
    weight_fractions: list[float],
    molar_masses_g_per_mol: list[float],
) -> list[float]:
    """Convert component weight fractions to mole fractions."""
    if len(weight_fractions) != len(molar_masses_g_per_mol):
        raise ValueError("Lists must have the same length")
    moles = [w / m for w, m in zip(weight_fractions, molar_masses_g_per_mol, strict=True)]
    total = sum(moles)
    if total <= 0:
        raise ValueError("Total moles is non-positive")
    return [n / total for n in moles]


def arrhenius_rate_constant(
    pre_exponential_a: float,
    ea_j_per_mol: float,
    temperature_k: float,
    gas_constant: float = 8.314462618,
) -> float:
    """k = A exp(-Ea / RT)."""
    if temperature_k <= 0:
        raise ValueError("temperature_k must be positive")
    return pre_exponential_a * math.exp(-ea_j_per_mol / (gas_constant * temperature_k))


def first_order_conversion(
    rate_constant_k: float,
    time: float,
) -> float:
    """Irreversible first-order conversion X = 1 - exp(-k t)."""
    if time < 0:
        raise ValueError("time must be non-negative")
    return 1.0 - math.exp(-rate_constant_k * time)


def first_order_half_life(rate_constant_k: float) -> float:
    """t_1/2 = ln(2) / k for first-order kinetics."""
    if rate_constant_k <= 0:
        raise ValueError("rate_constant_k must be positive")
    return math.log(2.0) / rate_constant_k


def theoretical_and_percent_yield(
    moles_limiting_reagent: float,
    stoichiometric_product_coeff: float,
    stoichiometric_limiting_coeff: float,
    product_molar_mass_g_per_mol: float,
    isolated_product_mass_g: float,
) -> dict[str, float]:
    """Theoretical mass and percent yield from limiting reagent.

    n_product_theo = n_lim * (nu_p / nu_lim)
    m_theo = n_product_theo * M_product
    % yield = 100 * m_isolated / m_theo
    """
    if moles_limiting_reagent <= 0 or product_molar_mass_g_per_mol <= 0:
        raise ValueError("Moles and product molar mass must be positive")
    if stoichiometric_limiting_coeff <= 0 or stoichiometric_product_coeff <= 0:
        raise ValueError("Stoichiometric coefficients must be positive")
    if isolated_product_mass_g < 0:
        raise ValueError("isolated_product_mass_g must be non-negative")
    n_theo = moles_limiting_reagent * stoichiometric_product_coeff / stoichiometric_limiting_coeff
    m_theo = n_theo * product_molar_mass_g_per_mol
    return {
        "theoretical_moles_product": n_theo,
        "theoretical_mass_g": m_theo,
        "percent_yield": 100.0 * isolated_product_mass_g / m_theo,
    }


def atom_economy_percent(
    product_molar_mass_g_per_mol: float,
    reactant_molar_masses_g_per_mol: list[float],
    reactant_stoich_coeffs: list[float],
) -> float:
    """Atom economy = 100 * M_product / sum(nu_i M_i) for a balanced equation."""
    if product_molar_mass_g_per_mol <= 0:
        raise ValueError("product_molar_mass_g_per_mol must be positive")
    if len(reactant_molar_masses_g_per_mol) != len(reactant_stoich_coeffs):
        raise ValueError("Reactant mass and coefficient lists must match")
    denom = sum(nu * m for nu, m in zip(reactant_stoich_coeffs, reactant_molar_masses_g_per_mol, strict=True))
    if denom <= 0:
        raise ValueError("Denominator of atom economy is non-positive")
    return 100.0 * product_molar_mass_g_per_mol / denom


def e_factor(
    mass_waste_g: float,
    mass_product_g: float,
) -> float:
    """Sheldon E-factor = mass of waste / mass of product."""
    if mass_product_g <= 0:
        raise ValueError("mass_product_g must be positive")
    if mass_waste_g < 0:
        raise ValueError("mass_waste_g must be non-negative")
    return mass_waste_g / mass_product_g


def dilute_solution(
    c1: float,
    v1: float,
    v2: float,
) -> float:
    """C2 = C1 V1 / V2 for dilution (same concentration units)."""
    if v2 <= 0:
        raise ValueError("v2 must be positive")
    if v1 < 0 or c1 < 0:
        raise ValueError("c1 and v1 must be non-negative")
    return c1 * v1 / v2


def moles_from_mass(mass_g: float, molar_mass_g_per_mol: float) -> float:
    """n = m / M."""
    if molar_mass_g_per_mol <= 0:
        raise ValueError("molar_mass_g_per_mol must be positive")
    return mass_g / molar_mass_g_per_mol