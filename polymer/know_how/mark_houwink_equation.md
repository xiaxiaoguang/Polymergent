# Mark–Houwink equation

---

## Metadata

**Short Description**: Use when relating polymer molecular weight to intrinsic viscosity or calibrating chromatography; covers Mark–Houwink equation, polymer exponent a, solvent effects, and universal calibration for gel p...

**Authors**: Wikipedia contributors

**Version**: 1.0

**Last Updated**: 2026-09-11

**License**: CC BY-SA 4.0

**Commercial Use**: Allowed with attribution

**Source**: https://en.wikipedia.org/wiki/Mark–Houwink_equation

---

## Definition
The Mark–Houwink equation relates intrinsic viscosity [η] to molecular weight M:

[η] = KM^a

where K and a are empirical parameters dependent on the polymer-solvent system and temperature.

## Parameter Interpretation
The exponent a relates to polymer hydrodynamic volume and geometry. If radius of gyration R scales as R ~ M^ν, then a = 3ν − 1.

Specific a values indicate polymer behavior:
- a = 0: rigid sphere (e.g., bacteriophage T2 DNA)
- a = 0.5: flexible coil in theta solvent
- a = 0.76: good solvent (Flory–Huggins theory)
- a = 2.0: rigid rod (e.g., tobacco mosaic virus)
- 0.5 ≤ a ≤ 0.8: flexible polymers
- a ≥ 0.8: semi-flexible polymers

## Universal Calibration in Chromatography
In size-exclusion chromatography (SEC/GPC, which separates by hydrodynamic volume), the product [η]M is proportional to hydrodynamic radius and independent of polymer substance.

For two polymers A and B at the same retention volume:
[η]_A M_A = [η]_B M_B

Substituting the Mark–Houwink equation:
K_A M_A^(a_A+1) = K_B M_B^(a_B+1)

This allows calibration curves constructed from one polymer standard (e.g., polystyrene) to determine molecular weights of other polymers if both polymers' Mark–Houwink constants are known for the same solvent and temperature.
