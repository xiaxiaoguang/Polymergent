# Glass Transition, Fox, Flory–Fox, and WLF

---

## Metadata

**Short Description**: Use when computing or predicting glass transition temperature (Tg) in polymers, blends, copolymers, or molecular-weight-dependent systems; covers Fox equation, Gordon–Taylor, Flory–Fox, and WLF shift...

**Authors**: Distilled from Wikipedia (glass transition, Flory–Fox equation, WLF equation)

**Version**: 1.0

**Last Updated**: 2026-09-11

**License**: CC BY-SA 4.0

**Commercial Use**: Allowed with attribution

**Source**: https://en.wikipedia.org/wiki/Flory%E2%80%93Fox_equation

**Related Tools**: estimate_polymer_tg_from_fox_equation, estimate_polymer_tg_gordon_taylor, estimate_tg_flory_fox_from_mn, fox_weight_fraction_for_target_tg, wlf_shift_factor

---

## Definition
Tg is the temperature at which segmental motion unfreezes in a polymer. It is not a first-order phase transition. All equations require input in Kelvin.

## Fox Equation (Blends & Random Copolymers)
**1/Tg = Σ(wᵢ / Tgᵢ)**
- Weight fractions wᵢ must sum to ~1
- Valid only for miscible mixtures with a single Tg
- **Do not use if DSC shows two peaks** (phase-separated)
- Inverse Fox: target Tg must lie between the two pure component Tgs; solver returns wA; if target is outside bracket, change monomers, not the formula

## Gordon–Taylor Equation
**Tg = (wA TgA + k wB TgB) / (wA + k wB)**
- k = 1 gives linear mixing
- k is empirical; do not derive k from Fox equation

## Flory–Fox (Molecular Weight Dependence)
**Tg(Mn) = Tg∞ − K / Mn**
- Accounts for chain-end free volume
- **Do not mix with Fox weight fractions in a single calculation**

## WLF Shift Factor
**log₁₀(aT) = −C₁(T − Tref) / (C₂ + T − Tref)**
- Universal constants: C₁ = 17.44, C₂ = 51.6 K (only when Tref = Tg)
- aT shifts time or rate, not Tg itself

## Common Errors
- Oligomer descriptors or DFT HOMO/LUMO do not predict bulk Tg
- Must convert °C → K before all calculations
