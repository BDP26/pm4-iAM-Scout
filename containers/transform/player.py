"""
Player Data Transformation Script

This script loads player data from the scrape directory, performs data cleaning and transformation,
and saves the processed data to the transform directory.

Main transformations:
- Convert date_of_birth from string to datetime format
- Convert height from string (e.g., "1,85 m") to float
- Remove unnecessary player_slug column
"""

import pandas as pd
import os
from pathlib import Path
from datetime import datetime


def load_player_data(input_path: str) -> pd.DataFrame:
    """
    Load player data from CSV file.
    
    Args:
        input_path (str): Path to the input CSV file
        
    Returns:
        pd.DataFrame: Loaded player data
        
    Raises:
        FileNotFoundError: If input file doesn't exist
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    print(f"Loading player data from: {input_path}")
    df = pd.read_csv(input_path)
    print(f"Loaded {len(df)} players")
    return df


def convert_date_of_birth(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert date_of_birth column from string to datetime format.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with converted date_of_birth column
    """
    print("Converting date_of_birth to datetime format...")
    
    # Convert date_of_birth from string (DD.MM.YYYY) to datetime
    df["date_of_birth"] = pd.to_datetime(df["date_of_birth"], format="%d.%m.%Y")
    
    print(f"Converted {df['date_of_birth'].notna().sum()} date_of_birth entries")
    return df


def convert_height_to_float(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert height column from string format (e.g., "1,85 m") to float.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with converted height column
    """
    print("Converting height to float format...")
    
    # Remove " m" suffix and replace comma with dot, then convert to float
    df["height"] = (df["height"]
                   .str.replace(" m", "", regex=False)
                   .str.replace(",", ".", regex=False)
                   .astype(float))
    
    print(f"Converted {df['height'].notna().sum()} height entries")
    return df


def remove_unnecessary_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove columns that are not needed for the final dataset.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with unnecessary columns removed
    """
    print("Removing unnecessary columns...")
    
    columns_to_drop = ['player_slug']
    existing_columns_to_drop = [col for col in columns_to_drop if col in df.columns]
    
    if existing_columns_to_drop:
        df = df.drop(existing_columns_to_drop, axis=1)
        print(f"Dropped columns: {existing_columns_to_drop}")
    else:
        print("No columns to drop")
    
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


def transform_player_data() -> None:
    """
    Main function to orchestrate the player data transformation process.
    """
    # Define file paths (updated for container deployment)
    input_path = "/data/scrape/player.csv"
    output_path = "/data/transform/player.csv"
    
    try:
        # Load data
        df = load_player_data(input_path)
        
        print(f"\nOriginal data shape: {df.shape}")
        print(f"Original columns: {df.columns.tolist()}")
        
        # Apply transformations
        df = convert_date_of_birth(df)
        df = convert_height_to_float(df)
        df = remove_unnecessary_columns(df)
        
        # Save transformed data
        save_transformed_data(df, output_path)
        
        print(f"\nFinal columns: {df.columns.tolist()}")
        print("Player data transformation completed successfully!")
        
    except Exception as e:
        print(f"Error during transformation: {e}")
        raise


if __name__ == "__main__":
    transform_player_data()