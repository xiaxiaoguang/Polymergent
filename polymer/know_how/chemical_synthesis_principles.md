# Comprehensive Principle Guide to Chemical Synthesis

---

## Metadata

**Short Description**: Use when planning chemical synthesis, computing yields or stoichiometry, distinguishing polymer mechanisms (step-growth vs chain-growth vs ring-opening), or evaluating atom economy and waste; covers...

**Authors**: Distilled for the polymer agent (Wikipedia CC BY-SA topics plus toolkit conventions)

**Version**: 1.0

**Last Updated**: 2026-09-11

**License**: CC BY-SA 4.0

**Commercial Use**: Allowed with attribution

**Source**: https://en.wikipedia.org/wiki/Chemical_synthesis

**Related Tools**: theoretical_and_percent_yield, atom_economy_percent, e_factor, moles_from_mass, dilute_solution, arrhenius_rate_constant, first_order_conversion, prepare_repeat_unit_from_name_or_smiles, open_cyclic_monomer_to_repeat_unit, build_linear_oligomer_smiles, carothers_xn_linear, flory_stockmayer_gel_point, mayo_lewis_instantaneous_composition, free_radical_steady_state_rp

---

## Moles, Yields, and Stoichiometry

n = m / M. Theoretical product moles = n_lim × (ν_product / ν_lim). Percent yield = 100 × m_isolated / m_theoretical. Atom economy = 100 × M_product / Σ(νi Mi) of all reactants. E-factor = mass_waste / mass_product. High yield with low atom economy is wasteful. C1 V1 = C2 V2 applies only to dilution, not yields. Limiting reagent identified from balanced coefficients and stoichiometric ratios, not visual inspection.

## Mechanism Classes

**Step-growth:** complementary groups react (e.g., diol + diacid). High Xn requires p → 1 and r → 1. Formula: Xn(p=1) = (1+r)/(1−r). Off-stoichiometry (r ≠ 1) caps molecular weight; fav > 2 plus high p causes gel.

**Chain-growth (free radical, ionic, coordination):** monomer adds only to active center; high polymer at low conversion possible.

**Ring-opening polymerization (ROP):** cyclic monomer opens at chain end. Lactones (GBL, caprolactone) homopolymerize to give `*O—(CH2)n—C(=O)*` mer. Cyclic anhydrides do **not** homopolymerize lactone-style; they require diol/diamine (step-growth) or epoxide (alternating polyester).

**Living/controlled chain-growth:** low termination/transfer; PDI approaches 1.

## Complementary Functional Groups

Polyester: HO—R—OH + HO2C—R'—CO2H or HO—R—CO2H (self). Polyamide: H2N—R—NH2 + HO2C—R'—CO2H. Polyurethane: OCN—R—NCO + HO—R'—OH. Two acids or two alcohols alone do not polymerize. Vinyl monomers chain-grow, not step-grow.

## Key Distinctions

Lactide is cyclic dimer of lactic acid; opening yields PLA mer. Anhydride opening gives diacid-like `*OC(=O)—R—C(=O)*`, not a self-sufficient polyester mer. Mayo–Lewis F1 is instantaneous composition; high conversion without azeotrope causes drift. Fox is a T
