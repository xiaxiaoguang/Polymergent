# Gelation

---

## Metadata

**Short Description**: Use when predicting gel formation in polymer systems, modeling polymer network formation, or calculating gel point conditions; covers gelation definition, Carothers equation, Flory-Stockmayer theory,...

**Authors**: Wikipedia contributors

**Version**: 1.0

**Last Updated**: 2026-09-11

**License**: CC BY-SA 4.0

**Commercial Use**: Allowed with attribution

**Source**: https://en.wikipedia.org/wiki/Gelation

---

## Definition
Gelation is the formation of a gel—an "infinite" sized polymer network—from a system of branched polymers linked by chemical or physical crosslinks. At the gel point, the system loses fluidity and viscosity increases dramatically. This is an irreversible process that permanently changes system properties.

## Key Equations

**Carothers Equation:**
$$DP_n = \frac{2}{2 - p \cdot f_{av}}$$

where $p$ is extent of reaction and $f_{av}$ is average functionality.

**Critical extent of reaction (gel point):**
$$p_c = \frac{2}{f_{av}}$$

Gelation occurs when $p \geq p_c$.

**Flory-Stockmayer approach for bifunctional and multifunctional monomers:**
$$p_c = \frac{1}{\{r[1 + \rho(f-2)]\}^{1/2}}$$

where $r$ is the ratio of all A groups to all B groups, $\rho$ is the ratio of A groups in branched units to total A groups, and $f$ is functionality of multifunctional units.

## Theory
Flory and Stockmayer (1940s) developed quantitative theories assuming functional group reactivity is independent of molecular size and that no intramolecular reactions occur. Critical percolation theory was applied in the 1970s. Growth models (diffusion-limited aggregation, cluster-cluster aggregation, kinetic gelation) developed in the 1980s describe aggregation kinetics.

## Modeling Approaches
Gel networks can be analyzed as random graphs or using Erdős–Rényi/Lushnikov models to predict when a giant component arises.
