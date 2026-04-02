"""
Player Statistics Data Transformation Script

This script loads player statistics data from the scrape directory, performs data cleaning and 
transformation, and saves the processed data to the transform directory.

Main transformations:
- Convert card columns (yellow, yellow_red, red, start_eleven) from int64 to bool
- Convert minute columns (on_min, off_min) from float64 to int with NaN handling
- Add new rating column with default float value
- Ensure proper data types for all columns
"""

import pandas as pd

from toolkit import get_input_path, get_output_path, load_csv_data, save_transformed_data


def convert_card_columns_to_bool(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert card columns from int64 (0/1) to bool (False/True).
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with converted card columns
    """
    print("Converting card columns from int64 to bool...")
    
    # Define card columns that should be boolean
    card_columns = ['yellow', 'yellow_red', 'red', 'start_eleven']
    
    converted_columns = []
    for col in card_columns:
        if col in df.columns:
            df[col] = df[col].astype(bool)
            converted_columns.append(col)
    
    if converted_columns:
        print(f"Converted columns to bool: {converted_columns}")
    else:
        print("No card columns found to convert")
    
    return df


def convert_minute_columns_to_int(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert minute columns from float64 to int, handling NaN values.
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with converted minute columns
    """
    print("Converting minute columns from float64 to int...")
    
    # Define minute columns that should be integers
    minute_columns = ['on_min', 'off_min']
    
    converted_columns = []
    for col in minute_columns:
        if col in df.columns:
            # Count NaN values before conversion
            nan_count = df[col].isna().sum()
            if nan_count > 0:
                print(f"Found {nan_count} NaN values in {col}, filling with 0")
            
            # Fill NaN with 0 first, then convert to int
            df[col] = df[col].fillna(0).astype(int)
            converted_columns.append(col)
    
    if converted_columns:
        print(f"Converted columns to int: {converted_columns}")
    else:
        print("No minute columns found to convert")
    
    return df


def add_rating_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a new rating column with default value 0.0 (float type).
    
    Args:
        df (pd.DataFrame): Input DataFrame
        
    Returns:
        pd.DataFrame: DataFrame with added rating column
    """
    print("Adding new rating column...")
    
    if 'rating' not in df.columns:
        df['rating'] = 0.0
        print(f"Added rating column with data type: {df['rating'].dtype}")
    else:
        print("Rating column already exists, skipping addition")
    
    return df


def transform_player_stats_data() -> None:
    """
    Main function to orchestrate the player statistics data transformation process.
    """
    # Define file paths (updated for container deployment)
    input_path = get_input_path("player_stats")
    output_path = get_output_path("player_stats")
    
    try:
        # Load data
        df = load_csv_data(input_path, "player statistics")
        
        print(f"\nOriginal data shape: {df.shape}")
        print(f"Original columns: {df.columns.tolist()}")
        
        # Apply transformations
        df = convert_card_columns_to_bool(df)
        df = convert_minute_columns_to_int(df)
        df = add_rating_column(df)
        
        # Save transformed data
        save_transformed_data(df, output_path)
        
        print(f"\nFinal columns: {df.columns.tolist()}")
        print(f"Final data types:")
        print(df.dtypes.to_string())
        
        # Show summary of transformations
        print(f"\nTransformation Summary:")
        bool_cols = [col for col in df.columns if df[col].dtype == 'bool']
        int_cols = [col for col in ['on_min', 'off_min'] if col in df.columns]
        print(f"Boolean columns: {bool_cols}")
        print(f"Integer minute columns: {int_cols}")
        print(f"Rating column added: {'rating' in df.columns}")
        
        print("\nPlayer statistics data transformation completed successfully!")
        
    except Exception as e:
        print(f"Error during transformation: {e}")
        raise


if __name__ == "__main__":
    transform_player_stats_data()