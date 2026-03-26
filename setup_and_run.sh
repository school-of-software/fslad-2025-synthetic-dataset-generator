#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
INPUT_CSV="${1:-sample_anonymized_final.csv}"
OUTDIR="${2:-output}"
SEED="${3:-42}"

cd "$PROJECT_DIR"

echo "Checking Python..."
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: $PYTHON_BIN not found."
  echo "Install Python 3.7+ and python3-venv first."
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys
if sys.version_info < (3, 7):
    raise SystemExit(
        f"Error: Python 3.7+ required, found {sys.version.split()[0]}"
    )
print(f"Python version OK: {sys.version.split()[0]}")
PY

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment in $VENV_DIR ..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "Upgrading pip/setuptools/wheel..."
pip install --upgrade pip setuptools wheel

echo "Installing dependencies..."
pip install -r requirements.txt

if [ ! -f "$INPUT_CSV" ]; then
  echo "Error: input file not found: $INPUT_CSV"
  echo "Usage: ./setup_and_run.sh [input_csv] [outdir] [seed]"
  exit 1
fi

echo "Running generator..."
python generate_fslad2025.py \
  --input "$INPUT_CSV" \
  --outdir "$OUTDIR" \
  --seed "$SEED"

echo
echo "Done."
echo "Output directory: $OUTDIR"
