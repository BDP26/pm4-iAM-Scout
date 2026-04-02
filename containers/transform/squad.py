"""
Squad Data Transformation Script

This script loads squad data from the scrape directory, performs data cleaning and transformation,
and saves the processed data to the transform directory.

Main transformations:
- Convert season format from year (e.g., "2024") to season range (e.g., "24/25")
- Ensure proper data types for all columns
"""

import pandas as pd

from toolkit import (
    ensure_proper_data_types,
    get_input_path,
    get_output_path,
    load_csv_data,
    save_transformed_data,
    transform_season_format,
)


def transform_squad_data() -> None:
    """
    Main function to orchestrate the squad data transformation process.
    """
    # Define file paths (updated for container deployment)
    input_path = get_input_path("squad")
    output_path = get_output_path("squad")
    
    try:
        # Load data
        df = load_csv_data(input_path, "squad")
        
        print(f"\nOriginal data shape: {df.shape}")
        print(f"Original columns: {df.columns.tolist()}")
        
        # Apply transformations
        df = transform_season_format(df)
        df = ensure_proper_data_types(df, id_columns=["player_id", "club_id"])
        
        # Save transformed data
        save_transformed_data(df, output_path)
        
        print(f"\nFinal columns: {df.columns.tolist()}")
        print(f"Final data types:")
        print(df.dtypes.to_string())
        print("\nSquad data transformation completed successfully!")
        
    except Exception as e:
        print(f"Error during transformation: {e}")
        raise


if __name__ == "__main__":
    transform_squad_data()