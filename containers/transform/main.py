"""
Containerized Data Transformation Pipeline

This script serves as the main entry point for the data transformation pipeline running in Docker.
It checks for available CSV files and runs the corresponding transformation scripts.
"""

import os
import sys
from pathlib import Path
import importlib.util
from typing import Callable, Dict, Optional

from toolkit import get_expected_input_files, get_scrape_dir, get_transform_dir


def check_available_data_files() -> Dict[str, str]:
    """
    Check which CSV files are available in the container's data directory.
    
    Returns:
        Dict[str, str]: Mapping of dataset names to their file paths
    """
    scrape_dir = get_scrape_dir()
    
    if not scrape_dir.exists():
        print(f"Warning: Scrape directory {scrape_dir} does not exist")
        return {}
    
    # Define the expected dataset files
    expected_files = get_expected_input_files()
    
    available_files = {}
    
    print("Checking for available data files...")
    for dataset_name, filename in expected_files.items():
        file_path = scrape_dir / filename
        if file_path.exists():
            available_files[dataset_name] = str(file_path)
            print(f"[OK] Found: {filename}")
        else:
            print(f"[MISSING] Missing: {filename}")
    
    return available_files


def import_transformation_module(module_name: str) -> Optional[Callable[[], None]]:
    """
    Dynamically import a transformation module and return its main function.
    
    Args:
        module_name (str): Name of the module to import (without .py extension)
        
    Returns:
        Optional[Callable[[], None]]: The transformation function or None on failure
    """
    try:
        module_path = Path(f"/app/{module_name}.py")
        if not module_path.exists():
            raise FileNotFoundError(f"Transformation script {module_path} not found")
        
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed to create import spec for {module_name}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get the main transformation function
        function_name = f"transform_{module_name}_data"
        if hasattr(module, function_name):
            return getattr(module, function_name)
        else:
            raise AttributeError(f"Function {function_name} not found in {module_name}")
            
    except Exception as e:
        print(f"Error importing {module_name}: {e}")
        return None


def run_transformation(dataset_name: str, file_path: str) -> bool:
    """
    Run the transformation for a specific dataset.
    
    Args:
        dataset_name (str): Name of the dataset to transform
        file_path (str): Path to the source CSV file
        
    Returns:
        bool: True if transformation succeeded, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Starting transformation for: {dataset_name}")
    print(f"Source file: {file_path}")
    print(f"{'='*60}")
    
    try:
        # Import and run the transformation function
        transform_function = import_transformation_module(dataset_name)
        
        if transform_function is None:
            print(f"[ERROR] Failed to load transformation for {dataset_name}")
            return False
        
        # Execute the transformation
        transform_function()
        
        print(f"[SUCCESS] Successfully completed transformation for {dataset_name}")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error transforming {dataset_name}: {e}")
        return False


def create_output_directory():
    """Ensure the output directory exists."""
    output_dir = get_transform_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory ready: {output_dir}")


def main():
    """
    Main orchestrator function that coordinates the entire transformation pipeline.
    """
    print("Starting Data Transformation Pipeline")
    print("=" * 60)
    
    # Ensure output directory exists
    create_output_directory()
    
    # Check which data files are available
    available_files = check_available_data_files()
    
    if not available_files:
        print("\n[ERROR] No data files found in the scrape directory!")
        print("Please ensure the scraping process has completed and CSV files are available.")
        return False
    
    print(f"\nFound {len(available_files)} datasets to transform")
    
    # Define processing order (some datasets may depend on others)
    processing_order = [
        'teams',           # Base team data
        'player',          # Base player data  
        'team_per_season', # Team-season relationships
        'squad',           # Player-team-season relationships
        'matches',         # Match data
        'player_stats'     # Player statistics (may reference other tables)
    ]
    
    # Track transformation results
    successful_transforms = []
    failed_transforms = []
    
    # Process datasets in the defined order
    for dataset_name in processing_order:
        if dataset_name in available_files:
            file_path = available_files[dataset_name]
            
            success = run_transformation(dataset_name, file_path)
            
            if success:
                successful_transforms.append(dataset_name)
            else:
                failed_transforms.append(dataset_name)
    
    # Print final summary
    print(f"\n{'='*60}")
    print("TRANSFORMATION PIPELINE SUMMARY")
    print(f"{'='*60}")
    
    print(f"[SUCCESS] Successful transformations ({len(successful_transforms)}):")
    for dataset in successful_transforms:
        print(f"   • {dataset}")
    
    if failed_transforms:
        print(f"\n[ERROR] Failed transformations ({len(failed_transforms)}):")
        for dataset in failed_transforms:
            print(f"   • {dataset}")
    
    success_rate = len(successful_transforms) / len(available_files) * 100
    print(f"\nSuccess Rate: {success_rate:.1f}% ({len(successful_transforms)}/{len(available_files)})")
    
    if failed_transforms:
        print(f"\n[WARNING] Some transformations failed. Check the logs above for details.")
        return False
    else:
        print(f"\nAll transformations completed successfully!")
        print(f"Transformed data available in: /data/transform/")
        return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTransformation pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error in transformation pipeline: {e}")
        sys.exit(1)