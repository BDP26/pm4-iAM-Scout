"""
Matches Data Transformation Script

This script loads matches data from the scrape directory, performs data cleaning and transformation,
and saves the processed data to the transform directory.

Main transformations:
- Convert season format from year (e.g., "2024") to season range (e.g., "24/25")
- Transform date column from string to proper datetime format
- Ensure proper data types for all columns
"""

import pandas as pd

from toolkit import (
    get_input_path,
    get_output_path,
    load_csv_data,
    save_transformed_data,
    transform_season_format,
)


def convert_date_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert date column from string to datetime format.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with converted date column
    """
    print("Converting date column to datetime format...")
    
    # Convert date from string (YYYY-MM-DD) to datetime
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    
    converted_count = df['date'].notna().sum()
    print(f"Converted {converted_count} date entries")
    
    return df


def transform_matches_data() -> None:
    """
    Main function to orchestrate the matches data transformation process.
    """
    # Define file paths (updated for container deployment)
    input_path = get_input_path("matches")
    output_path = get_output_path("matches")
    
    try:
        # Load data
        df = load_csv_data(input_path, "match")
        
        print(f"\nOriginal data shape: {df.shape}")
        print(f"Original columns: {df.columns.tolist()}")
        
        # Apply transformations
        df = transform_season_format(df)
        df = convert_date_column(df)
        
        # Save transformed data
        save_transformed_data(df, output_path)
        
        print(f"\nFinal columns: {df.columns.tolist()}")
        print(f"Final data types:")
        print(df.dtypes.to_string())
        print("\nMatches data transformation completed successfully!")
        
    except Exception as e:
        print(f"Error during transformation: {e}")
        raise


if __name__ == "__main__":
    transform_matches_data()