# Williams–Landel–Ferry equation

---

## Metadata

**Short Description**: Use when predicting how polymer viscosity or mechanical properties change with temperature, or when applying time–temperature superposition to extend material test data; covers WLF equation, shift fa...

**Authors**: Wikipedia contributors

**Version**: 1.0

**Last Updated**: 2026-09-11

**License**: CC BY-SA 4.0

**Commercial Use**: Allowed with attribution

**Source**: https://en.wikipedia.org/wiki/Williams–Landel–Ferry_equation

---

## Definition

The Williams–Landel–Ferry (WLF) equation is an empirical model for predicting temperature-dependent behavior of viscoelastic materials, particularly polymer melts. It relates a shift factor to temperature via two material constants.

## Key Equations

**Shift factor form:**
$$\log(a_T) = \frac{-C_1(T - T_r)}{C_2 + (T - T_r)}$$

**Viscosity form:**
$$\mu(T) = \mu_0 \cdot 10^{\left(\frac{-C_1(T-T_r)}{C_2+T-T_r}\right)}$$

where:
- $a_T$ = shift factor (horizontal shift on log scale)
- $T$ = temperature of interest
- $T_r$ = reference temperature (often chosen near glass transition $T_g$)
- $C_1, C_2$ = empirical constants (only three of four parameters are independent)
- $\mu_0$ = viscosity at reference temperature

## Universal Constants

When $T_r = T_g$: $C_1 \approx 17.44$, $C_2 \approx 51.6$ K

When $T_r = T_g + 43$ K: $C_1 \approx 8.86$, $C_2 \approx 101.6$ K

## Limitations

- Valid only at or above $T_g$ when constants derived from high-temperature data
- Not applicable below $T_g$ for structural predictions
- Master curves invalid if data suffered aging effects during testing
- Universal parameters are approximate; fitting to experimental data is preferable

## Applications

Extends compliance master curves beyond experimental time/frequency ranges via time–temperature superposition (TTSP), enabling property prediction across broader temperature ranges.
