# FSLAD-2025 Synthetic Login Activity Dataset Generator

## Overview
This repository contains the code and example files used to generate the FinnGen Synthetic Login Activity Dataset (FSLAD-2025), a privacy-preserving synthetic dataset designed for authentication anomaly detection and cybersecurity research.

The generator preserves:
- categorical distributions  
- binary feature frequencies  
- approximate numeric correlations (Gaussian copula)  
- temporal login patterns  

In addition to dataset generation, this repository includes scripts for reproducing the analytical figures presented in the associated publication.

---

## Quick Start

```bash
chmod +x setup_and_run.sh
./setup_and_run.sh data/sample_anonymized_input.csv output 42
```

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Repository Structure

| Path | Description |
|------|-------------|
| `generate_fslad2025.py` | Main dataset generation script |
| `scripts/suspicious_login_figure_dashboard.py` | Figure generation and analysis (Streamlit app) |
| `setup_and_run.sh` | One-command execution script |
| `requirements.txt` | Python dependencies |
| `data/sample_anonymized_input.csv` | Example anonymized input dataset |
| `output_example/` | Example generated outputs |
| `docs/methodology_overview.md` | Concise explanation of the generation methodology |

---

## Expected Input Schema

The input CSV should contain at minimum:

- `user_hash` (string)  
- `system_name` (string)  
- `login_timestamp` (datetime)  
- `login_success_flag` (binary)  
- `ip_address` (optional)  

Additional columns will be preserved and synthesized where possible.

---

## Outputs

Running the generator produces:

- synthetic dataset (CSV)  
- schema file  
- KS distribution comparison summary  
- auto-generated README  

---

## Figure Generation (Reproducing Paper Results)

To reproduce the figures used in the associated publication:

```bash
streamlit run scripts/suspicious_login_figure_dashboard.py
```

Then:
1. Upload the generated dataset or sample input file  
2. The script will automatically generate all figures  
3. Figures are saved to the `figures/` directory in PNG and PDF formats  

---

## Reproducibility

- All randomness is controlled via a fixed seed  
- Dataset generation and figure creation are fully reproducible  
- Outputs are deterministic given the same input and seed  

---

## Privacy and Safety

- No real user data is included  
- All identifiers are pseudonymized  
- IP addresses are synthetic and generated using private address ranges  
- Example input data are synthetic and safe for public release  
- Original anonymized source summaries are not included due to privacy and security constraints  

---

## Code Availability

https://github.com/school-of-software/fslad-2025-synthetic-dataset-generator  

A versioned release is archived via Zenodo for long-term accessibility.

---

## Citation

Dada, O. A., Wang, T., FinnGen, & Sipilä, T. P. (2026).  
FinnGen Synthetic Login Activity Dataset (FSLAD-2025)

---

## License

CC0 1.0 Universal (Public Domain Dedication)
