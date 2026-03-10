"""
Squad Data Transformation Script

This script loads squad data from the scrape directory, performs data cleaning and transformation,
and saves the processed data to the transform directory.

Main transformations:
- Convert season format from year (e.g., "2024") to season range (e.g., "24/25")
- Ensure proper data types for all columns
"""

import pandas as pd
import os
from pathlib import Path


def load_squad_data(input_path: str) -> pd.DataFrame:
    """
    Load squad data from CSV file.
    
    Args:
        input_path (str): Path to the input CSV file
        
    Returns:
        pd.DataFrame: Loaded squad data
        
    Raises:
        FileNotFoundError: If input file doesn't exist
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    print(f"Loading squad data from: {input_path}")
    df = pd.read_csv(input_path)
    print(f"Loaded {len(df)} squad records")
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


def ensure_proper_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure all columns have appropriate data types.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with proper data types
    """
    print("Ensuring proper data types...")
    
    # Convert ID columns to integers if they exist
    id_columns = ['player_id', 'club_id']
    for col in id_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
            print(f"Converted {col} to integer type")
    
    # Season is already converted to string in the previous step
    print("All data types validated")
    
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


def transform_squad_data() -> None:
    """
    Main function to orchestrate the squad data transformation process.
    """
    # Define file paths (updated for container deployment)
    input_path = "/data/scrape/squad.csv"
    output_path = "/data/transform/squad.csv"
    
    try:
        # Load data
        df = load_squad_data(input_path)
        
        print(f"\nOriginal data shape: {df.shape}")
        print(f"Original columns: {df.columns.tolist()}")
        
        # Apply transformations
        df = transform_season_format(df)
        df = ensure_proper_data_types(df)
        
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