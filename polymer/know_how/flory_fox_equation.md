# Flory–Fox equation

---

## Metadata

**Short Description**: Use when relating polymer molecular weight to glass transition temperature, modeling free volume effects, or understanding how chain ends affect polymer properties; covers Flory–Fox equation, glass t...

**Authors**: Wikipedia contributors

**Version**: 1.0

**Last Updated**: 2026-09-11

**License**: CC BY-SA 4.0

**Commercial Use**: Allowed with attribution

**Source**: https://en.wikipedia.org/wiki/Flory–Fox_equation

---

## Definition
The Flory–Fox equation is an empirical formula relating number-average molecular weight (Mn) to glass transition temperature (Tg) in polymers. It describes how free volume—a polymer chain's "elbow room" relative to surrounding chains—governs segmental mobility and the glass transition.

## Core Equation
$$T_g = T_{g,\infty} - \frac{K}{M_n}$$

Where:
- Tg,∞ = maximum glass transition temperature at theoretical infinite molecular weight
- K = empirical parameter related to free volume in the polymer sample
- Mn = number-average molecular weight

## Mechanism
Glass transition occurs when free volume decreases to a critical minimum, "freezing out" molecular rearrangement. Free volume depends on:
- Temperature (decreases upon cooling from rubbery state)
- Chain end density: end units have greater free volume than interior units because covalent bonds are shorter than intermolecular distances at chain ends
- Low molecular weight → more chain ends → lower Tg; high molecular weight → asymptotic approach to Tg,∞

## Molecular-Level Derivation
Zaccone and Terentjev derived Flory–Fox from temperature-dependent shear modulus G of glassy polymers. Setting G(Tg) = 0 yields:
$$T_g = \frac{1}{\alpha_T}(1-C-\phi_c^* + 2\Lambda) - \frac{2\Lambda M_0}{\alpha_T M_n}$$

Parameters include packing fraction (ϕc* ≈ 0.64 for soft spheres), thermal expansion coefficient (αT), and topological constraint parameter (Λ).

## Limitations
- Accuracy limited to narrow molecular weight distributions
- Free volume concept poorly defined at molecular level
- Recent simulations show free-volume argument fails for branched polymers despite maintained functional form
- Plasticizers and hydrogen bonding can alter expected free volume around chain ends
