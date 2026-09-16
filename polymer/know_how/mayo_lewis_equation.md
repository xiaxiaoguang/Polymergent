# Mayo–Lewis equation

---

## Metadata

**Short Description**: Use when predicting monomer distribution in two-component copolymers or calculating copolymer composition; covers reactivity ratios, Mayo–Lewis equation, feed vs. copolymer composition, and limiting...

**Authors**: Wikipedia contributors

**Version**: 1.0

**Last Updated**: 2026-09-11

**License**: CC BY-SA 4.0

**Commercial Use**: Allowed with attribution

**Source**: https://en.wikipedia.org/wiki/Mayo–Lewis_equation

---

## Definition & Core Equation

The Mayo–Lewis equation describes the instantaneous distribution of two monomers (M₁, M₂) in a copolymer during polymerization. It relates the rate of incorporation of each monomer to monomer concentrations and reactivity ratios.

## Key Equations

**Main copolymer equation:**
$$\frac{d[M_1]}{d[M_2]} = \frac{[M_1](r_1[M_1] + [M_2])}{[M_2]([M_1] + r_2[M_2])}$$

**Reactivity ratios:**
- $r_1 = \frac{k_{11}}{k_{12}}$ (preference of M₁*-terminated chain to add M₁ vs M₂)
- $r_2 = \frac{k_{22}}{k_{21}}$ (preference of M₂*-terminated chain to add M₂ vs M₁)

**Mole fraction form:**
$$F_1 = \frac{r_1 f_1^2 + f_1 f_2}{r_1 f_1^2 + 2f_1 f_2 + r_2 f_2^2}$$

where f₁, f₂ are feed mole fractions; F₁, F₂ are copolymer mole fractions.

## Limiting Cases

- **r₁ ≈ r₂ >> 1:** Homopolymers (monomers don't cross-react)
- **r₁ ≈ r₂ > 1:** Block copolymer
- **r₁ ≈ r₂ ≈ 1:** Random/statistical copolymer
- **r₁ ≈ r₂ ≈ 0:** Alternating copolymer (e.g., maleic anhydride–styrene with r₁=0.01, r₂=0.02)
- **r₁ >> 1 >> r₂:** Composition drift (M₁ depletes first, then M₂ dominates)
- **Both r < 1:** Azeotropic point where feed and copolymer compositions match

## Derivation Basis

Derived using steady-state approximation: formation rate of active chain ends equals destruction rate. Based on reaction kinetics involving propagating chain ends M₁* and M₂*.
