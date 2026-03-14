"""
Shared transformation utilities.

This module centralizes reusable helpers used across transformation scripts.
"""

from pathlib import Path
from typing import Sequence
import os

import pandas as pd


def load_csv_data(input_path: str, entity_label: str) -> pd.DataFrame:
    """Load CSV data with a consistent log and existence check."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    print(f"Loading {entity_label} data from: {input_path}")
    df = pd.read_csv(input_path)
    print(f"Loaded {len(df)} {entity_label} records")
    return df


def transform_season_format(
    df: pd.DataFrame,
    season_column: str = "season",
    preview_count: int = 3,
) -> pd.DataFrame:
    """Transform season from year format (2024) to range format (24/25)."""
    print("Transforming season format from year to season range...")

    df[season_column] = df[season_column].astype(int)
    df[season_column] = df[season_column].apply(
        lambda year: f"{str(year)[-2:]}/{str(year + 1)[-2:]}"
    )

    print(f"Converted {len(df)} season entries to range format")
    unique_seasons = df[season_column].unique()[:preview_count]
    print(f"Example season formats: {unique_seasons.tolist()}")
    return df


def ensure_proper_data_types(
    df: pd.DataFrame,
    *,
    id_columns: Sequence[str] | None = None,
    string_columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Apply common data type normalization for selected columns."""
    print("Ensuring proper data types...")

    for col in id_columns or []:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
            print(f"Converted {col} to integer type")

    for col in string_columns or []:
        if col in df.columns:
            df[col] = df[col].astype(str)
            print(f"Converted {col} to string")

    print("All data types validated")
    return df


def remove_unnecessary_columns(
    df: pd.DataFrame,
    columns_to_drop: Sequence[str],
) -> pd.DataFrame:
    """Drop optional columns if they exist in the DataFrame."""
    print("Removing unnecessary columns...")

    existing_columns_to_drop = [col for col in columns_to_drop if col in df.columns]
    if existing_columns_to_drop:
        df = df.drop(existing_columns_to_drop, axis=1)
        print(f"Dropped columns: {existing_columns_to_drop}")
    else:
        print("No columns to drop")

    return df


def save_transformed_data(df: pd.DataFrame, output_path: str) -> None:
    """Save transformed data to CSV and ensure output directory exists."""
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(output_path, index=False)
    print(f"Transformed data saved to: {output_path}")
    print(f"Final dataset shape: {df.shape}")
