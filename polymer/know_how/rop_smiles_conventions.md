# Repeat-Unit SMILES and Ring-Opening Monomers

---

## Metadata

**Short Description**: Use when converting monomers to repeat-unit SMILES for linear oligomer construction, or when working with ring-opening polymerization (lactones, lactams, anhydrides); covers repeat-unit format requir...

**Authors**: Distilled from Wikipedia (ROP, polyester, SMILES) plus toolkit conventions

**Version**: 1.0

**Last Updated**: 2026-09-11

**License**: CC BY-SA 4.0

**Commercial Use**: Allowed with attribution

**Source**: https://en.wikipedia.org/wiki/Ring-opening_polymerization

**Related Tools**: prepare_repeat_unit_from_name_or_smiles, open_cyclic_monomer_to_repeat_unit, build_linear_oligomer_smiles, autocorrect_smiles

---

## Repeat-Unit SMILES Format

Linear oligomer tools require repeat-unit SMILES with exactly two dummy atoms (`*`), each of degree 1. A cyclic monomer or ring SMILES cannot be used directly.

## Ring-Opening Polymerization (ROP) Rules

**Lactone:** Break the acyl–O single bond. Attach `*` on O and `*` on C.  
Example: `O=C1CCCCCO1` → `*OCCCCCC(*)=O`

**Lactam:** Break the acyl–N bond.  
Example: Caprolactam → `*NCCCCCC(*)=O`

**Anhydride:** Break one acyl–O bond.  
Example: Succinic anhydride → `*OC(=O)CCC(*)=O`  
Note: Anhydride mers are diacid-like units; true polyester synthesis still requires a diol partner in the chemistry.

## Workflow

1. Bind `ru = prepare_repeat_unit_from_name_or_smiles(name_or_smiles)` (do not print)
2. Then call `oligo = build_linear_oligomer_smiles(ru, n)`
3. Do not chain inspect + open + resolve on the same input; one prepare call suffices

## SMILES Autocorrect

- `CL` → `Cl` (chlorine)
- `XCCX` or `[X]CC[X]` → `*CC*`
- Fixer will not invent missing ring digits

## Descriptor Keys

Valid keys: `mw`, `tpsa`, `logp`, `bertz`, `hbd`, `hba`. Do not format missing keys with `:.1f`.

## Critical Warning

Never pass cyclic SMILES like `O=C1CCCO1` into `build_linear_oligomer_smiles`.
