# Flory–Huggins solution theory

---

## Metadata

**Short Description**: Use when modeling polymer-solvent thermodynamics, predicting phase separation, or calculating mixing free energy; covers Gibbs free energy of mixing, entropy of mixing, enthalpy of mixing, volume fra...

**Authors**: Wikipedia contributors

**Version**: 1.0

**Last Updated**: 2026-09-11

**License**: CC BY-SA 4.0

**Commercial Use**: Allowed with attribution

**Source**: https://en.wikipedia.org/wiki/Flory–Huggins_solution_theory

---

## Definition
Flory–Huggins solution theory is a lattice model for polymer solution thermodynamics that accounts for large differences in molecular size between polymer and solvent molecules. Developed independently by Paul Flory and Maurice Huggins in 1941.

## Key Equation
The Gibbs free energy change for mixing is:

**ΔG_mix = RT[n₁ ln φ₁ + n₂ ln φ₂ + n₁φ₂χ₁₂]**

Where:
- n₁, n₂ = moles of solvent and polymer
- φ₁, φ₂ = volume fractions of solvent and polymer
- χ₁₂ = dimensionless interaction parameter
- R = gas constant, T = absolute temperature

## Model Components

**Entropy of mixing:**
ΔS_mix = -k_B[N₁ ln φ₁ + N₂ ln φ₂]
Accounts for increased spatial uncertainty when molecules mix; uses volume fractions rather than mole fractions to handle size disparity.

**Enthalpy of mixing:**
ΔH_mix = k_B T N₁φ₂χ₁₂
Reflects energy cost of replacing polymer-polymer and solvent-solvent contacts with polymer-solvent contacts.

**Interaction parameter:**
χ₁₂ = zΔw/(k_B T), where z is coordination number
Can be estimated from Hildebrand solubility parameters: χ₁₂ = V_seg(δₐ - δᵦ)²/RT

## Interpretation
- Positive χ → unfavorable mixing, may cause phase separation
- Smaller χ → better miscibility
- Often temperature-dependent; typically decreases with increasing temperature
- χ includes entropic contributions beyond regular mixing entropy
