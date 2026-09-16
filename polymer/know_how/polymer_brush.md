# Polymer brush

---

## Metadata

**Short Description**: Use when modeling surface-grafted polymer layers, analyzing brush structure and density profiles, or designing applications in colloid stabilization and friction reduction; covers polymer brush defin...

**Authors**: Wikipedia contributors

**Version**: 1.0

**Last Updated**: 2026-09-11

**License**: CC BY-SA 4.0

**Commercial Use**: Allowed with attribution

**Source**: https://en.wikipedia.org/wiki/Polymer_brush

---

## Definition
A polymer brush is a surface coating of polymers tethered to a substrate (flat, curved, or nanoparticles). Can exist in solvated state (polymer + solvent) or melt state. Polyelectrolyte brushes have charged polymer chains. High graft density causes strong chain extension.

## Structure & Theory
Polymer chains stretch away from attachment surface due to steric repulsion/osmotic pressure. Within the Milner-Witten-Cates approximation:

**Single chain monomer density:** 
$$n(z,\rho) = \frac{2N}{\pi}\arcsin\left(\frac{z}{\rho}\right)$$

**Monomer density gradient:**
$$\phi(z,\rho) = \frac{\partial n}{\partial z}$$

where ρ = altitude of end monomer, N = monomers per chain, z = position.

**Overall brush density profile:** Convolution of single-chain profile with end-monomer distribution ϵ(ρ).

**Dry brush end-monomer density:**
$$\epsilon_{\rm dry}(\rho,H) = \frac{\rho/H}{Na\sqrt{1-\rho^2/H^2}}$$

where a = monomer size, H = brush height.

**Elastic free energy:**
$$\frac{F_{\rm el}}{kT} = \frac{\pi^2}{24N^2a^5}\int_0^{\infty}\left\{-z^3\frac{d\phi(z)}{dz}\right\}dz$$

## Applications
- Colloid stabilization
- Friction reduction between surfaces
- Lubrication in artificial joints
- Area-selective deposition for patterned surface alignment

## Modeling Methods
Molecular dynamics, Monte Carlo, Brownian dynamics, molecular theories.
