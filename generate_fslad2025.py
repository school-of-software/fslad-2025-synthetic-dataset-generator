#!/usr/bin/env python3
"""
FSLAD-2025 Distribution-Preserving Synthetic Login Activity Generator

This script generates a synthetic authentication-event dataset from an
anonymized seed dataset while preserving key statistical properties,
including:
- categorical distributions
- binary feature frequencies
- approximate numeric correlations via Gaussian copula modeling
- temporal login patterns (hour-of-day and weekday)

Outputs:
- synthetic dataset CSV
- schema CSV
- KS comparison summary CSV
- README.md

Example:
    python generate_fslad2025.py \
        --sample_anonymized_data.csv \
        --outdir output \
        --seed 42
"""

from __future__ import annotations

import argparse
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

import numpy as np
import pandas as pd
from faker import Faker
from scipy import stats


LOGGER = logging.getLogger("fslad2025")


@dataclass(frozen=True)
class OutputPaths:
    synthetic_csv: Path
    schema_csv: Path
    ks_summary_csv: Path
    readme_md: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the FSLAD-2025 synthetic login activity dataset."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to the anonymized seed CSV file.",
    )
    parser.add_argument(
        "--outdir",
        default=Path("output"),
        type=Path,
        help="Directory where output files will be written.",
    )
    parser.add_argument(
        "--seed",
        default=42,
        type=int,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--user-col",
        default="user_hash",
        help="Column name for the user identifier.",
    )
    parser.add_argument(
        "--system-col",
        default="system_name",
        help="Column name for the system identifier.",
    )
    parser.add_argument(
        "--timestamp-col",
        default="login_timestamp",
        help="Column name for the login timestamp.",
    )
    parser.add_argument(
        "--success-col",
        default="login_success_flag",
        help="Column name for the login success binary variable.",
    )
    parser.add_argument(
        "--ip-col",
        default="ip_address",
        help="Column name for the IP address column, if present.",
    )
    parser.add_argument(
        "--synthetic-name",
        default="synthetic_login_activity_dataset.csv",
        help="Filename for the synthetic dataset output.",
    )
    parser.add_argument(
        "--schema-name",
        default="data_schema.csv",
        help="Filename for the schema output.",
    )
    parser.add_argument(
        "--ks-name",
        default="distribution_comparison_summary.csv",
        help="Filename for the KS summary output.",
    )
    parser.add_argument(
        "--readme-name",
        default="README.md",
        help="Filename for the generated README output.",
    )
    return parser.parse_args()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )


def ensure_outdir(outdir: Path) -> OutputPaths:
    outdir.mkdir(parents=True, exist_ok=True)
    return OutputPaths(
        synthetic_csv=outdir / args.synthetic_name,
        schema_csv=outdir / args.schema_name,
        ks_summary_csv=outdir / args.ks_name,
        readme_md=outdir / args.readme_name,
    )


def load_seed_data(input_path: Path, timestamp_col: str) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    df_real = pd.read_csv(input_path)
    LOGGER.info("Loaded seed dataset: %s rows x %s columns", *df_real.shape)

    # Convert numeric-like columns where possible.
    for col in df_real.columns:
        if col == timestamp_col:
            continue
        try:
            df_real[col] = pd.to_numeric(df_real[col])
        except Exception:
            pass

    if timestamp_col in df_real.columns:
        df_real[timestamp_col] = pd.to_datetime(df_real[timestamp_col], errors="coerce")

    return df_real


def hash_user_id(index: int) -> str:
    return hashlib.sha256(f"user_{index}".encode("utf-8")).hexdigest()[:16]


def empirical_sample(series: pd.Series, n: int, rng: np.random.Generator) -> np.ndarray:
    probs = series.value_counts(normalize=True, dropna=True)
    if probs.empty:
        return np.array([np.nan] * n, dtype=object)
    return rng.choice(probs.index.to_numpy(), size=n, p=probs.values)


def synthesize_user_ids(n: int) -> pd.Series:
    return pd.Series([hash_user_id(i) for i in range(n)], name="user_hash")


def synthesize_systems(
    df_real: pd.DataFrame,
    n: int,
    system_col: str,
    rng: np.random.Generator,
) -> pd.Series:
    if system_col in df_real.columns:
        return pd.Series(empirical_sample(df_real[system_col], n, rng), name=system_col)
    fallback = [f"system_{i % 5}" for i in range(n)]
    return pd.Series(fallback, name=system_col)


def synthesize_timestamps(
    df_real: pd.DataFrame,
    n: int,
    timestamp_col: str,
    rng: np.random.Generator,
) -> pd.Series:
    if timestamp_col not in df_real.columns:
        return pd.Series(pd.date_range("2025-01-01", periods=n, freq="h"), name=timestamp_col)

    valid_ts = df_real[timestamp_col].dropna()
    if valid_ts.empty:
        return pd.Series(pd.date_range("2025-01-01", periods=n, freq="h"), name=timestamp_col)

    hour_counts = valid_ts.dt.hour.value_counts(normalize=True).reindex(range(24), fill_value=0.0)
    weekday_counts = valid_ts.dt.weekday.value_counts(normalize=True).reindex(range(7), fill_value=0.0)

    hour_probs = normalize_probs(hour_counts.to_numpy(dtype=float))
    weekday_probs = normalize_probs(weekday_counts.to_numpy(dtype=float))

    date_range = pd.date_range(valid_ts.min().normalize(), valid_ts.max().normalize(), freq="D")
    timestamps: List[pd.Timestamp] = []

    for _ in range(n):
        base_date = pd.Timestamp(rng.choice(date_range))
        chosen_hour = int(rng.choice(np.arange(24), p=hour_probs))
        chosen_weekday = int(rng.choice(np.arange(7), p=weekday_probs))

        ts = base_date + pd.Timedelta(hours=chosen_hour)
        # Shift forward until the weekday matches the sampled weekday.
        while ts.weekday() != chosen_weekday:
            ts += pd.Timedelta(days=1)
        timestamps.append(ts)

    return pd.Series(timestamps, name=timestamp_col)


def synthesize_ip_addresses(n: int, faker: Faker) -> pd.Series:
    return pd.Series([faker.ipv4_private() for _ in range(n)], name="ip_address")


def normalize_probs(values: np.ndarray) -> np.ndarray:
    total = values.sum()
    if total <= 0:
        return np.repeat(1.0 / len(values), len(values))
    return values / total


def identify_binary_numeric_columns(df_real: pd.DataFrame) -> List[str]:
    binary_cols: List[str] = []
    for col in df_real.select_dtypes(include=[np.number]).columns:
        non_na = df_real[col].dropna()
        if non_na.nunique() == 2:
            binary_cols.append(col)
    return binary_cols


def identify_valid_numeric_columns(
    df_real: pd.DataFrame,
    excluded_cols: Iterable[str],
) -> List[str]:
    excluded = set(excluded_cols)
    valid_cols: List[str] = []
    for col in df_real.select_dtypes(include=[np.number]).columns:
        if col in excluded:
            continue
        non_na = df_real[col].dropna()
        if non_na.nunique() > 1 and len(non_na) > 5:
            valid_cols.append(col)
    return valid_cols


def synthesize_numeric_columns(
    df_real: pd.DataFrame,
    df_syn: pd.DataFrame,
    valid_numeric: List[str],
    n: int,
    rng: np.random.Generator,
) -> None:
    if not valid_numeric:
        return

    if len(valid_numeric) == 1:
        col = valid_numeric[0]
        source = df_real[col].dropna().to_numpy()
        uniforms = rng.random(n)
        df_syn[col] = np.quantile(source, uniforms)
        return

    x = df_real[valid_numeric].dropna()
    if len(x) < 10:
        for col in valid_numeric:
            source = df_real[col].dropna().to_numpy()
            df_syn[col] = np.quantile(source, rng.random(n))
        return

    ranked = (x.rank(method="average") - 0.5) / len(x)
    ranked = ranked.clip(1e-6, 1 - 1e-6)
    normed = stats.norm.ppf(ranked)

    cov = np.cov(normed.to_numpy().T)
    cov = np.nan_to_num(cov)
    cov += np.eye(cov.shape[0]) * 1e-6

    try:
        synthetic_norm = rng.multivariate_normal(
            mean=np.zeros(len(valid_numeric)),
            cov=cov,
            size=n,
        )
        synthetic_uniform = stats.norm.cdf(synthetic_norm)

        for i, col in enumerate(valid_numeric):
            source = df_real[col].dropna().to_numpy()
            df_syn[col] = np.quantile(source, synthetic_uniform[:, i])
    except np.linalg.LinAlgError:
        LOGGER.warning(
            "Covariance matrix was not suitable for multivariate sampling; "
            "falling back to independent quantile sampling."
        )
        for col in valid_numeric:
            source = df_real[col].dropna().to_numpy()
            df_syn[col] = np.quantile(source, rng.random(n))


def synthesize_binary_columns(
    df_real: pd.DataFrame,
    df_syn: pd.DataFrame,
    binary_cols: List[str],
    n: int,
    rng: np.random.Generator,
) -> None:
    for col in binary_cols:
        probs = df_real[col].value_counts(normalize=True, dropna=True)
        if probs.empty:
            continue
        df_syn[col] = rng.choice(probs.index.to_numpy(), size=n, p=probs.values)


def synthesize_categorical_columns(
    df_real: pd.DataFrame,
    df_syn: pd.DataFrame,
    n: int,
    excluded_cols: Iterable[str],
    rng: np.random.Generator,
) -> None:
    excluded = set(excluded_cols)
    categorical_cols = df_real.select_dtypes(include=["object", "category"]).columns.tolist()

    for col in categorical_cols:
        if col in excluded:
            continue
        sampled = empirical_sample(df_real[col], n, rng)
        df_syn[col] = sampled


def schema_validation(df_real: pd.DataFrame, df_syn: pd.DataFrame) -> None:
    if len(df_real) != len(df_syn):
        raise ValueError("Row count mismatch between seed and synthetic datasets.")
    LOGGER.info("Schema validation passed: %s rows x %s columns", *df_syn.shape)


def compute_ks_summary(
    df_real: pd.DataFrame,
    df_syn: pd.DataFrame,
    numeric_cols: List[str],
    binary_cols: List[str],
) -> pd.DataFrame:
    rows = []
    for col in list(dict.fromkeys(numeric_cols + binary_cols)):
        if col not in df_real.columns or col not in df_syn.columns:
            continue

        real_data = df_real[col].dropna()
        synth_data = df_syn[col].dropna()

        if len(real_data) < 10 or len(synth_data) < 10:
            continue

        ks_stat, p_val = stats.ks_2samp(real_data, synth_data)
        rows.append(
            {
                "Column": col,
                "KS_Statistic": float(ks_stat),
                "P_Value": float(p_val),
                "Match": "Similar" if p_val > 0.05 else "Different",
            }
        )

    return pd.DataFrame(rows)


def build_schema(df_real: pd.DataFrame, df_syn: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ColumnName": df_syn.columns,
            "RealDataType": [
                str(df_real[c].dtype) if c in df_real.columns else "N/A"
                for c in df_syn.columns
            ],
            "SyntheticDataType": [str(df_syn[c].dtype) for c in df_syn.columns],
            "NonNullCount": [int(df_syn[c].notna().sum()) for c in df_syn.columns],
        }
    )


def write_readme(
    out_path: Path,
    paths: OutputPaths,
    generated_at: datetime,
) -> None:
    text = f"""# FinnGen Synthetic Login Activity Dataset

## Overview
This package contains a synthetic authentication-event dataset derived from an anonymized seed dataset.
It preserves key statistical properties, including categorical distributions, binary feature frequencies,
approximate numeric correlations, and temporal access patterns, while ensuring privacy.

## Files
| File | Description |
|------|-------------|
| `{paths.synthetic_csv.name}` | Synthetic dataset |
| `{paths.schema_csv.name}` | Schema and data types for generated fields |
| `{paths.ks_summary_csv.name}` | KS-test comparison between seed and synthetic numeric/binary columns |
| `{paths.readme_md.name}` | Package documentation |

## Methodology
- Empirical resampling for categorical variables
- Gaussian copula-based synthesis for numeric columns
- Binary feature frequency preservation
- Timestamp synthesis using observed hour-of-day and weekday distributions
- Pseudonymized user identifiers generated with SHA-256
- Synthetic private IPv4 addresses generated with Faker

## Reproducibility
A fixed random seed can be provided at runtime. See the command-line help for available parameters.

Generated on: {generated_at.strftime('%Y-%m-%d %H:%M:%S')}
"""
    out_path.write_text(text.strip() + "\n", encoding="utf-8")


def generate_dataset(args: argparse.Namespace) -> OutputPaths:
    faker = Faker()
    Faker.seed(args.seed)
    rng = np.random.default_rng(args.seed)

    paths = OutputPaths(
        synthetic_csv=args.outdir / args.synthetic_name,
        schema_csv=args.outdir / args.schema_name,
        ks_summary_csv=args.outdir / args.ks_name,
        readme_md=args.outdir / args.readme_name,
    )
    args.outdir.mkdir(parents=True, exist_ok=True)

    df_real = load_seed_data(args.input, args.timestamp_col)
    n = len(df_real)
    df_syn = pd.DataFrame(index=range(n))

    user_col = args.user_col
    system_col = args.system_col
    timestamp_col = args.timestamp_col
    success_col = args.success_col
    ip_col = args.ip_col if args.ip_col in df_real.columns else None

    # Core identifiers and temporal structure
    df_syn[user_col] = synthesize_user_ids(n)
    df_syn[system_col] = synthesize_systems(df_real, n, system_col, rng)
    df_syn[timestamp_col] = synthesize_timestamps(df_real, n, timestamp_col, rng)
    if ip_col:
        df_syn[ip_col] = synthesize_ip_addresses(n, faker)

    binary_cols = identify_binary_numeric_columns(df_real)
    valid_numeric = identify_valid_numeric_columns(df_real, excluded_cols=[success_col] + binary_cols)

    synthesize_numeric_columns(df_real, df_syn, valid_numeric, n, rng)
    synthesize_binary_columns(df_real, df_syn, binary_cols, n, rng)
    synthesize_categorical_columns(
        df_real,
        df_syn,
        n,
        excluded_cols=[user_col, system_col, timestamp_col] + ([ip_col] if ip_col else []),
        rng=rng,
    )

    schema_validation(df_real, df_syn)

    ks_summary = compute_ks_summary(df_real, df_syn, numeric_cols=valid_numeric, binary_cols=binary_cols)
    schema = build_schema(df_real, df_syn)

    df_syn.to_csv(paths.synthetic_csv, index=False)
    schema.to_csv(paths.schema_csv, index=False)
    ks_summary.to_csv(paths.ks_summary_csv, index=False)
    write_readme(paths.readme_md, paths, datetime.now())

    LOGGER.info("Synthetic dataset saved to %s", paths.synthetic_csv.resolve())
    LOGGER.info("Schema saved to %s", paths.schema_csv.resolve())
    LOGGER.info("KS summary saved to %s", paths.ks_summary_csv.resolve())
    LOGGER.info("README saved to %s", paths.readme_md.resolve())

    return paths


def main() -> None:
    configure_logging()
    global args
    args = parse_args()
    generate_dataset(args)


if __name__ == "__main__":
    main()
