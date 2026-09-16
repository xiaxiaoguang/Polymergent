from polymer.agent import A1
# Initialize the agent with data path, Data lake will be automatically downloaded on first run (~11GB)
# agent = A1(path='/home/hcao5/workspace/datasets', llm='gpt-5.6-luna')
# claude-sonnet-5 claude-haiku-4-5-20251001
agent = A1(path='/home/hcao5/workspace/datasets', llm='claude-sonnet-5')

# agent.go("A PLA formulation is synthesized by melt blending PLA pellets with 15 wt% CaCO₃ and 1 wt% compatibilizer, followed by extrusion and injection molding. Tensile strength is 68 MPa and Young's modulus is 3.4 GPa, but elongation at break is only 2.1% and notched impact strength is poor. SEM shows particle agglomerates around 5–20 μm.\
# The goal is to increase impact toughness and elongation substantially while retaining at least 90% of the current tensile strength and modulus.\
# Diagnose the likely causes and design an experimental program. Specify which formulation/process variables you would change, the levels or ranges, controls, characterization methods, and how you would decide which modification to pursue.\
#          ")

# tool

# agent.go("Plan a RAFT comonomer screen for solvent-free, PFAS-free hydrophobic coatings: generate 32 (meth)acrylate / styrene-type pairs that maximize predicted water contact angle and keep film $T_g$ in 40–80 °C so the coating is film-forming at 120 °C. Every monomer ≤3 steps from commercial (meth)acryloyl chloride or 4-vinylbenzyl chloride.")
# agent.go("From comme·rcially catalogued 5–7-membered lactones and cyclic anhydrides, propose 16 ROP/ROCOP comonomer pairs that (i) contain only C/H/O, (ii) have an ester or anhydride in both monomers, (iii) have RDKit-estimated oligomer $T_g$ descriptors above a fixed cutoff, and (iv) are each resolvable to a PubChem CID. Return a 16-row table: A_SMILES, B_SMILES, A_CID, B_CID, reaction (ROP or ROCOP).")

# datasets

# agent.go("List the 10 most common composition strings that contain C and H and at least one of O, N, S, F, Cl in Omol25. Report counts.")
# agent.go("For hydrogen-rich organic systems typical of polymer subchains, how does the HOMO–LUMO gap change as the fragment grows from small oligomers to ~100+ atom clusters? Is the drop mostly finished by a particular size, or does it keep falling")
agent.go("The following is a polymer science question.Think step by step if needed, then give the exact short final answer.Question: The efficiency of photocatalytic [2+2] cycloaddition polymerization and the molecular weight of the resulting polymers are influenced by the monomer structure. Please refer to the experimental data in the table below and rank the following different diene monomers according to the weight-average molecular weight (Mw) of the polymers obtained after polymerization under specific conditions, from smallest to largest. a: Monomer 1c b: Monomer 1f c: Monomer 1a d: Monomer 1ePut the final answer inside <solution>...</solution>.For a number, output only the number (and unit if asked). For a ranking, output the ordered list. Do not put extra commentary inside the solution tags.")


