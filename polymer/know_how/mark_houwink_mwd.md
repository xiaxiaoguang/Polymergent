# Mark–Houwink and Molar-Mass Averages

---

## Metadata

**Short Description**: Use when computing molecular weight from viscosity data, converting between molar-mass averages (Mn, Mw, Mz, Mv), or interpreting polydispersity; covers Mark–Houwink equation, molar-mass definitions,...

**Authors**: Distilled from Wikipedia (Mark–Houwink equation, molar mass distribution, intrinsic viscosity)

**Version**: 1.0

**Last Updated**: 2026-09-11

**License**: CC BY-SA 4.0

**Commercial Use**: Allowed with attribution

**Source**: https://en.wikipedia.org/wiki/Mark%E2%80%93Houwink_equation

**Related Tools**: mark_houwink_molecular_weight, mark_houwink_intrinsic_viscosity, molar_mass_averages_from_histogram

---

## Experimental Methods Measure Different Averages

- **Viscometry** → Mv (viscosity-average)
- **Light scattering** → Mw (weight-average)
- **Osmometry** → Mn (number-average)

Do not treat these interchangeably.

## Mark–Houwink Equation

**[η] = K M^a**

Invert to find Mv: **M = ([η]/K)^(1/a)**

- K and a are solvent- and temperature-specific
- Typical flexible chains in good solvent: a ≈ 0.5–0.8
- a = 0.5 (theta conditions); a → 0 (hard sphere)
- **Unit consistency required**: [η] in dL/g requires K in matching units; do not mix mL/g K with dL/g [η]

## Molar-Mass Averages from Histograms

Given slice masses Mi and number counts Ni:

- **Mn = Σ Ni Mi / Σ Ni** (number-average)
- **Mw = Σ Ni Mi² / Σ Ni Mi** (weight-average)
- **Mz = Σ Ni Mi³ / Σ Ni Mi²** (z-average)
- **Mv** derived from Mark–Houwink with exponent a
- **PDI = Mw / Mn** (polydispersity index)

## Polymer Synthesis Reference Values

- Ideal step-growth: PDI → 2
- Ideal living chain-growth: PDI → 1

## Critical Usage Note

Mark–Houwink M is Mv-like, not Mn. Comparing MH-derived M directly to Carothers Mn is a category error.
