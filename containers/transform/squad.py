"""
Squad Data Transformation Script

This script loads squad data from the scrape directory, performs data cleaning and transformation,
and saves the processed data to the transform directory.

Main transformations:
- Convert season format from year (e.g., "2024") to season range (e.g., "24/25")
- Ensure proper data types for all columns
"""


from __future__ import annotations

import pandas as pd

from toolkit import (
    ensure_proper_data_types,
    get_input_path,
    get_output_path,
    load_csv_data,
    save_transformed_data,
)


def normalize_season(value: object) -> str | object:
    """
    Normalizes season values.

    Supported examples:
    - 2025     -> 25/26
    - "2025"   -> 25/26
    - "2025.0" -> 25/26
    - "25/26"  -> 25/26
    """
    if pd.isna(value):
        return value

    season = str(value).strip()

    if not season:
        return season

    # Already in correct format
    if "/" in season:
        return season

    try:
        year = int(float(season))
        return f"{str(year)[-2:]}/{str(year + 1)[-2:]}"
    except ValueError as exc:
        raise ValueError(f"Unsupported season format: {season}") from exc


def transform_squad_data() -> None:
    """
    Main function to orchestrate the squad data transformation process.
    """
    input_path = get_input_path("squad")
    output_path = get_output_path("squad")

    try:
        df = load_csv_data(input_path, "squad")

        print(f"\nOriginal data shape: {df.shape}")
        print(f"Original columns: {df.columns.tolist()}")

        print("Transforming season format...")
        df["season"] = df["season"].apply(normalize_season)

        df = ensure_proper_data_types(df, id_columns=["player_id", "club_id"])

        save_transformed_data(df, output_path)

        print(f"\nFinal columns: {df.columns.tolist()}")
        print("Final data types:")
        print(df.dtypes.to_string())
        print("\nSquad data transformation completed successfully!")

    except Exception as e:
        print(f"Error during transformation: {e}")
        raise


if __name__ == "__main__":
    transform_squad_data()