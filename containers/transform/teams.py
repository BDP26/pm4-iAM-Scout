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

from toolkit import (
    get_input_path,
    get_output_path,
    load_csv_data,
    remove_unnecessary_columns,
    save_transformed_data,
)


def fix_old_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Entfernt Zeilen mit alten Teamnamen, die nicht mehr benötigt werden.
    """
    print("Dropping rows for old teams: Veyvey United, Team Vaud U21")
    old_names = ["Vevey United", "Team Vaud U21"]
    before = df.shape[0]
    df = df[~df["club_name"].isin(old_names)]
    after = df.shape[0]
    print(f"Dropped {before - after} rows with old team names.")
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


def transform_teams_data() -> None:
    """
    Main function to orchestrate the teams data transformation process.
    """
    # Define file paths for container environment
    input_path = get_input_path("teams")
    output_path = get_output_path("teams")
    
    try:
        # Load data
        df = load_csv_data(input_path, "team")
        
        print(f"\nOriginal data shape: {df.shape}")
        print(f"Original columns: {df.columns.tolist()}")
        
        # Apply transformations
        df = fix_old_names(df)
        df = fix_luzern_u21_data(df)
        df = clean_plz_column(df)
        df = remove_unnecessary_columns(df, ["club_slug"])
        
        # Save transformed data
        save_transformed_data(df, output_path)
        
        print(f"\nFinal columns: {df.columns.tolist()}")
        print("Teams data transformation completed successfully!")
        
    except Exception as e:
        print(f"Error during transformation: {e}")
        raise


if __name__ == "__main__":
    transform_teams_data()