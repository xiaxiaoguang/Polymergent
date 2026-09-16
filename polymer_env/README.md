conda env create -f environment.yml

conda install -c conda-forge \
  numpy scipy pandas matplotlib seaborn \
  rdkit openbabel \
  openmm parmed mdanalysis mdtraj ase \
  xtb xtb-python packmol lammps \
  mbuild foyer gmso \
  pymatgen pyscf \
  scikit-learn xgboost \
  networkx nglview ipywidgets \
  ambertools \
  -y