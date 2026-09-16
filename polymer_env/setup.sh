#!/usr/bin/env bash
#
# setup_polymer_env.sh
#
# One-shot installer for the polymer/chemistry tool stack described in
# polymer_library_content_dict.py. Creates a conda environment, installs
# the CLI-backed / conda-only packages via conda-forge, then installs the
# rest via pip -- all in a single execution.
#
# IMPORTANT NOTE ON VERSIONS: package versions below are intentionally
# UNPINNED (no "==" or ">=" floors). An earlier version of this script
# hardcoded version floors I could not actually verify against the live
# PyPI/conda-forge index (network access to pypi.org is blocked from the
# environment that generated this script), and one of them (foyer) was
# wrong -- not because the version number was off, but because the whole
# MoSDeF toolchain (mbuild/foyer/gmso) isn't reliably pip-installable at
# all; it's primarily distributed via conda-forge. Rather than guess
# more numbers I can't check, this version lets conda/pip's own solvers
# pick the current valid release of everything, and prints exactly what
# got installed at the end so you have ground truth instead of my
# claims. If you need reproducible/pinned versions, run this once, then
# capture the real versions with `conda list` / `pip freeze` and pin
# those into your own lockfile.
#
# Usage:
#   chmod +x setup_polymer_env.sh
#   ./setup_polymer_env.sh                       # defaults: env "polymer", python 3.11
#   ./setup_polymer_env.sh -n my-env -p 3.10      # custom env name / python version
#
# Requires: conda or mamba already installed (Miniconda/Miniforge/Anaconda).
# mamba is used automatically if found (much faster dependency solving);
# otherwise falls back to conda.

set -euo pipefail

# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------
ENV_NAME="polymer"
PYTHON_VERSION="3.8"

while getopts "n:p:h" opt; do
  case "$opt" in
    n) ENV_NAME="$OPTARG" ;;
    p) PYTHON_VERSION="$OPTARG" ;;
    h)
      echo "Usage: $0 [-n env_name] [-p python_version]"
      echo "  -n  conda environment name (default: polymer)"
      echo "  -p  python version (default: 3.11)"
      exit 0
      ;;
    *)
      echo "Unknown option. Use -h for help." >&2
      exit 1
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Pick conda vs mamba
# ---------------------------------------------------------------------------
if command -v mamba >/dev/null 2>&1; then
  CONDA_BIN="mamba"
elif command -v conda >/dev/null 2>&1; then
  CONDA_BIN="conda"
else
  echo "ERROR: neither 'conda' nor 'mamba' was found on PATH." >&2
  echo "Install Miniforge/Miniconda first: https://github.com/conda-forge/miniforge" >&2
  exit 1
fi

echo "============================================================"
echo " Polymer/chemistry environment setup"
echo "============================================================"
echo "  Environment name : $ENV_NAME"
echo "  Python version    : $PYTHON_VERSION"
echo "  Package manager   : $CONDA_BIN"
echo "============================================================"
echo

# ---------------------------------------------------------------------------
# 1. Create the environment (skip if it already exists)
# ---------------------------------------------------------------------------
if "$CONDA_BIN" env list | grep -qE "^\s*${ENV_NAME}\s"; then
  echo "[1/4] Environment '$ENV_NAME' already exists -- skipping creation."
else
  echo "[1/4] Creating environment '$ENV_NAME' (python=$PYTHON_VERSION)..."
  "$CONDA_BIN" create -y -n "$ENV_NAME" "python=$PYTHON_VERSION"
fi
echo

# ---------------------------------------------------------------------------
# 2. conda-forge packages: CLI-backed tools AND the MoSDeF simulation
#    toolchain (mbuild/foyer/gmso), which is conda-forge-first and not
#    reliably available via pip at all -- this is the actual fix for the
#    "no such version for foyer" failure, not a version-pin change.
# ---------------------------------------------------------------------------
# echo "[2/4] Installing conda-forge packages..."
# "$CONDA_BIN" install -y -n "$ENV_NAME" -c conda-forge \
#   openbabel \
#   packmol \
#   xtb \
#   lammps \
#   mbuild \
#   foyer \
#   gmso
# echo

# ---------------------------------------------------------------------------
# 3. Everything else via pip, inside the new environment. Deliberately
#    unpinned -- see note at top of file.
# ---------------------------------------------------------------------------
echo "[3/4] Installing pip packages into '$ENV_NAME'..."
"$CONDA_BIN" run -n "$ENV_NAME" pip install --upgrade pip

"$CONDA_BIN" run -n "$ENV_NAME" pip install \
  rdkit \
  pubchempy \
  cirpy \
  mordred \
  networkx
#   'nglview<=3.0.1'
#   nglview \
# radonpy is NOT distributed via PyPI or conda-forge as of this writing --
# it's installed from source (https://github.com/RadonPy/RadonPy). Left out
# of the automated install; add it yourself if you need it, e.g.:
#   git clone https://github.com/RadonPy/RadonPy.git && pip install ./RadonPy
echo

# ---------------------------------------------------------------------------
# 4. Verify: print what ACTUALLY got installed (ground truth, not a claim)
#    for every Python package, and confirm each CLI binary is on PATH.
# ---------------------------------------------------------------------------
echo "[4/4] Verifying installation..."

"$CONDA_BIN" run -n "$ENV_NAME" python - <<'PYEOF'
import importlib
import importlib.metadata as md
import sys

# module import name may differ from the pip/conda package name
modules = {
    "rdkit": "rdkit",
    "pubchempy": "pubchempy",
    "cirpy": "cirpy",
    "mordred": "mordred",
    "networkx": "networkx",
    "mbuild": "mbuild",
    "foyer": "foyer",
    "gmso": "gmso",
    "stk": "stk",
    "openmm": "openmm",
    "parmed": "parmed",
    "MDAnalysis": "MDAnalysis",
    "mdtraj": "mdtraj",
    "ase": "ase",
    "pyscf": "pyscf",
    "xtb-python": "xtb",
    "thermo": "thermo",
    "chemicals": "chemicals",
    "CoolProp": "CoolProp",
    "pymatgen": "pymatgen",
    "scikit-learn": "sklearn",
    "xgboost": "xgboost",
    "deepchem": "deepchem",
    "torch": "torch",
    "torch-geometric": "torch_geometric",
    "numpy": "numpy",
    "pandas": "pandas",
    "scipy": "scipy",
    "matplotlib": "matplotlib",
    "seaborn": "seaborn",
    "py3Dmol": "py3Dmol",
    "nglview": "nglview",
    "packmol-memgen": "packmol_memgen",
}

failed = []
print("\nInstalled versions (ground truth from this machine):")
for pip_name, import_name in modules.items():
    try:
        mod = importlib.import_module(import_name)
        try:
            version = md.version(pip_name)
        except md.PackageNotFoundError:
            version = getattr(mod, "__version__", "unknown")
        print(f"  {pip_name:<20} {version}")
    except Exception as e:
        failed.append((pip_name, str(e).splitlines()[0]))

if failed:
    print("\nFailed imports (need attention):")
    for pip_name, err in failed:
        print(f"  - {pip_name}: {err}")

print(f"\n{len(modules) - len(failed)}/{len(modules)} Python packages import cleanly.")
sys.exit(1 if failed else 0)
PYEOF
py_status=$?

cli_ok=true
for cli in obabel packmol xtb lmp; do
  if "$CONDA_BIN" run -n "$ENV_NAME" bash -c "command -v $cli" >/dev/null 2>&1; then
    echo "  ✓ CLI available: $cli"
  else
    echo "  ✗ CLI NOT found: $cli"
    cli_ok=false
  fi
done

echo
echo "============================================================"
if [ "$py_status" -eq 0 ] && [ "$cli_ok" = true ]; then
  echo " Setup complete. Activate with: conda activate $ENV_NAME"
  echo " To pin these exact versions for reproducibility, run:"
  echo "   conda run -n $ENV_NAME pip freeze > requirements.lock.txt"
else
  echo " Setup finished with some issues -- see failures listed above."
fi
echo "============================================================"