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

from toolkit import (
    get_input_path,
    get_output_path,
    load_csv_data,
    remove_unnecessary_columns,
    save_transformed_data,
)


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

    height_str = df["height"].astype("string").str.strip()

    # Treat unknown height values as null before numeric conversion.
    unknown_height_mask = height_str.str.lower().isin({"k. a.", "k.a.", "k.a", "ka"})
    unknown_count = int(unknown_height_mask.sum())

    df["height"] = (
        height_str
        .where(~unknown_height_mask, pd.NA)
        .str.replace(" m", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df["height"] = pd.to_numeric(df["height"], errors="coerce")

    if unknown_count > 0:
        print(f"Set {unknown_count} unknown height values to null")
    
    print(f"Converted {df['height'].notna().sum()} height entries")
    return df


def transform_player_data() -> None:
    """
    Main function to orchestrate the player data transformation process.
    """
    # Define file paths (updated for container deployment)
    input_path = get_input_path("player")
    output_path = get_output_path("player")
    
    try:
        # Load data
        df = load_csv_data(input_path, "player")
        
        print(f"\nOriginal data shape: {df.shape}")
        print(f"Original columns: {df.columns.tolist()}")
        
        # Apply transformations
        df = convert_date_of_birth(df)
        df = convert_height_to_float(df)
        df = remove_unnecessary_columns(df, ["player_slug"])
        df.drop_duplicates(subset='player_id', keep='last', inplace=True)
        # Save transformed data
        save_transformed_data(df, output_path)
        
        print(f"\nFinal columns: {df.columns.tolist()}")
        print("Player data transformation completed successfully!")
        
    except Exception as e:
        print(f"Error during transformation: {e}")
        raise


if __name__ == "__main__":
    transform_player_data()