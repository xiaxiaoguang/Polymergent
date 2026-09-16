# Mayo–Lewis Copolymerization

---

## Metadata

**Short Description**: Use when predicting copolymer composition from monomer feed, analyzing reactivity ratios, finding azeotropic conditions, or estimating chain length with chain-transfer agents; covers instantaneous co...

**Authors**: Distilled from Wikipedia (Mayo–Lewis equation, copolymer)

**Version**: 1.0

**Last Updated**: 2026-09-11

**License**: CC BY-SA 4.0

**Commercial Use**: Allowed with attribution

**Source**: https://en.wikipedia.org/wiki/Mayo%E2%80%93Lewis_equation

**Related Tools**: mayo_lewis_instantaneous_composition, azeotropic_copolymer_feed, mayo_chain_transfer_xn

---

## Core Equation

**Mayo–Lewis equation** gives instantaneous copolymer composition:

F₁ = (r₁f₁² + f₁f₂) / (r₁f₁² + 2f₁f₂ + r₂f₂²)

where:
- F₁ = mole fraction of monomer 1 in copolymer (instantaneous)
- f₁ = mole fraction of monomer 1 in feed (not weight fraction)
- f₂ = 1 − f₁
- rᵢ = kᵢᵢ / kᵢⱼ (reactivity ratios)

Composition is instantaneous at t = 0, not final batch composition unless f₁ is held constant or an azeotrope exists.

## Reactivity Ratio Regimes

- r₁ ≈ r₂ ≈ 1: random copolymer
- r₁ ≈ r₂ ≈ 0: alternating copolymer
- Both rᵢ >> 1: two separate homopolymers
- One rᵢ >> 1 >> other: composition drift as preferred monomer depletes

## Azeotrope

Azeotropic point exists (0 < f₁ₐz < 1) only when both rᵢ < 1 or both rᵢ > 1:

f₁ₐz = (1 − r₂) / (2 − r₁ − r₂)

At azeotrope: F₁ = f₁ (feed and copolymer compositions match; no drift).

## Chain Transfer (Mayo DP)

1/Xₙ = 1/Xₙ₀ + Cₛ[S]/[M]

This equation caps degree of polymerization from a chain-transfer agent (CTA). Do not use reactivity ratios for chain-transfer calculations.
