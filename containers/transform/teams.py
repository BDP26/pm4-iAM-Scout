"""
Teams Data Transformation Script

This script loads teams data from the scrape directory, performs data cleaning and transformation,
and saves the processed data to the transform directory.

Main transformations:
- Fix Luzern U21 team location and PLZ data
- Handle missing PLZ values by filling with 0
- Convert PLZ column from float to integer
- Remove unnecessary club_slug column
"""

import pandas as pd
import os
from pathlib import Path


def load_teams_data(input_path: str) -> pd.DataFrame:
    """
    Load teams data from CSV file.
    
    Args:
        input_path (str): Path to the input CSV file
        
    Returns:
        pd.DataFrame: Loaded teams data
        
    Raises:
        FileNotFoundError: If input file doesn't exist
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    print(f"Loading teams data from: {input_path}")
    df = pd.read_csv(input_path)
    print(f"Loaded {len(df)} teams")
    return df


def fix_luzern_u21_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fix missing location data for Luzern U21 team.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with fixed Luzern U21 data
    """
    print("Fixing Luzern U21 location data...")
    
    # Add PLZ of luzern to luzern u21 due to the u21 having no location
    luzern_mask = df['club_name'].str.contains('Luzern U21', case=False, na=False)
    df.loc[luzern_mask, 'PLZ'] = 6000
    df.loc[luzern_mask, 'location'] = 'Luzern'
    
    affected_rows = luzern_mask.sum()
    if affected_rows > 0:
        print(f"Updated {affected_rows} Luzern U21 entries")
    
    return df


def clean_plz_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize the PLZ (postal code) column.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with cleaned PLZ column
    """
    print("Cleaning PLZ column...")
    
    # Check for missing values
    nan_count = df['PLZ'].isna().sum()
    if nan_count > 0:
        print(f"Found {nan_count} missing PLZ values, filling with 0")
        
    # Fill remaining NaN values in PLZ with 0
    df['PLZ'] = df['PLZ'].fillna(0)
    
    # Transform column PLZ from float to int
    df['PLZ'] = df['PLZ'].astype(int)
    print("PLZ column converted to integer type")
    
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
    
    columns_to_drop = ['club_slug']
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


def transform_teams_data() -> None:
    """
    Main function to orchestrate the teams data transformation process.
    """
    # Define file paths for container environment
    input_path = "/data/scrape/teams.csv"
    output_path = "/data/transform/teams.csv"
    
    try:
        # Load data
        df = load_teams_data(input_path)
        
        print(f"\nOriginal data shape: {df.shape}")
        print(f"Original columns: {df.columns.tolist()}")
        
        # Apply transformations
        df = fix_luzern_u21_data(df)
        df = clean_plz_column(df)
        df = remove_unnecessary_columns(df)
        
        # Save transformed data
        save_transformed_data(df, output_path)
        
        print(f"\nFinal columns: {df.columns.tolist()}")
        print("Teams data transformation completed successfully!")
        
    except Exception as e:
        print(f"Error during transformation: {e}")
        raise


if __name__ == "__main__":
    transform_teams_data()