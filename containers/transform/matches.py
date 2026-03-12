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
import os
from pathlib import Path


def load_matches_data(input_path: str) -> pd.DataFrame:
    """
    Load matches data from CSV file.
    
    Args:
        input_path (str): Path to the input CSV file
        
    Returns:
        pd.DataFrame: Loaded matches data
        
    Raises:
        FileNotFoundError: If input file doesn't exist
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    print(f"Loading matches data from: {input_path}")
    df = pd.read_csv(input_path)
    print(f"Loaded {len(df)} match records")
    return df


def transform_season_format(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform season from single year format (e.g., 2024) to season range format (e.g., "24/25").
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with transformed season format
    """
    print("Transforming season format from year to season range...")
    
    # Ensure season column is integer first
    df['season'] = df['season'].astype(int)
    
    # Transform to "YY/YY" format (e.g., 2024 -> "24/25")
    df['season'] = df['season'].apply(
        lambda year: f"{str(year)[-2:]}/{str(year+1)[-2:]}"
    )
    
    print(f"Converted {len(df)} season entries to range format")
    
    # Show examples of the transformation
    unique_seasons = df['season'].unique()[:3]  # Show first 3 unique seasons
    print(f"Example season formats: {unique_seasons.tolist()}")
    
    return df


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


def save_transformed_data(df: pd.DataFrame, output_path: str) -> None:
    """
    Save the transformed DataFrame to CSV file.
    
    Args:
        df (pd.DataFrame): Transformed DataFrame
        output_path (str): Path for the output CSV file
    """
    # Ensure output directory exists
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    df.to_csv(output_path, index=False)
    print(f"Transformed data saved to: {output_path}")
    print(f"Final dataset shape: {df.shape}")


def transform_matches_data() -> None:
    """
    Main function to orchestrate the matches data transformation process.
    """
    # Define file paths (updated for container deployment)
    input_path = "/data/scrape/matches.csv"
    output_path = "/data/transform/matches.csv"
    
    try:
        # Load data
        df = load_matches_data(input_path)
        
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