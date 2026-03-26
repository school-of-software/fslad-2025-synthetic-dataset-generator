# FSLAD-2025 Synthetic Login Activity Dataset Generator

## Overview
This package contains the code and example files used to generate the FinnGen Synthetic Login Activity Dataset (FSLAD-2025), a privacy-preserving synthetic dataset for authentication anomaly detection research.

The generator preserves:
- categorical distributions
- binary feature frequencies
- approximate numeric correlations (Gaussian copula)
- temporal login patterns

## Quick Start

```bash
chmod +x setup_and_run.sh
./setup_and_run.sh data/sample_anonymized_input.csv output 42
```

## Installation

```bash
pip install -r requirements.txt
```

## Files

| File | Description |
|------|-------------|
| `generate_fslad2025.py` | Main dataset generation script |
| `setup_and_run.sh` | One-command execution script |
| `requirements.txt` | Python dependencies |
| `data/sample_anonymized_input.csv` | Example anonymized input dataset |
| `output_example/` | Example generated outputs |
| `docs/methodology_overview.md` | Concise explanation of the generation methodology |

## Expected Input Schema

The input CSV should contain at minimum:
- `user_hash` (string)
- `system_name` (string)
- `login_timestamp` (datetime)
- `login_success_flag` (binary)
- `ip_address` (optional)

Additional columns will be preserved and synthesized where possible.

## Outputs

Running the generator produces:
- synthetic dataset (CSV)
- schema file
- KS distribution comparison summary
- auto-generated README

## Reproducibility

All randomness is controlled via a fixed seed.

## Privacy and Safety

- No real user data is included
- All identifiers are pseudonymized
- IP addresses are synthetic and use private ranges
- Example input data are synthetic and safe for public release
- The original anonymized source summaries are not included due to privacy and security constraints

## Citation

Dada, O.A., Wang, T., FinnGen, Sipilä, T.P. (2026).
FinnGen Synthetic Login Activity Dataset (FSLAD-2025)
