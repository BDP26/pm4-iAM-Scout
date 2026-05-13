"""
Machine learning utility functions for model training and evaluation.
Extracted from rating_model and recommender_model notebooks.
"""

import pickle
from pathlib import Path
from typing import Tuple, Dict, Any

import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score


DEFAULT_TEST_SIZE = 0.2
DEFAULT_RANDOM_STATE = 42
DEFAULT_CV_FOLDS = 5


def split_data_randomly(
    features: pd.DataFrame,
    target: pd.Series,
    test_size: float = DEFAULT_TEST_SIZE,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split data randomly into train and test sets."""
    return train_test_split(
        features, target,
        test_size=test_size,
        random_state=random_state
    )


def split_data_by_group(
    dataframe: pd.DataFrame,
    features: pd.DataFrame,
    target: pd.Series,
    group_column: str,
    test_size: float = DEFAULT_TEST_SIZE,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split data by group (e.g., by player or match) into train and test sets."""
    unique_groups = dataframe[group_column].unique()

    train_groups, test_groups = train_test_split(
        unique_groups,
        test_size=test_size,
        random_state=random_state
    )

    mask_train = dataframe[group_column].isin(train_groups)
    mask_test = dataframe[group_column].isin(test_groups)

    return (
        features[mask_train],
        features[mask_test],
        target[mask_train],
        target[mask_test]
    )


def build_preprocessor(
    numeric_columns: list,
    categorical_columns: list,
    boolean_columns: list,
) -> ColumnTransformer:
    """Build a preprocessing pipeline for features."""
    return ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), numeric_columns),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical_columns),
            ("boolean", "passthrough", boolean_columns),
        ]
    )


def evaluate_model(
    y_true: pd.Series,
    y_predicted: np.ndarray,
) -> Dict[str, float]:
    """Evaluate model predictions with standard metrics."""
    return {
        "mean_absolute_error": mean_absolute_error(y_true, y_predicted),
        "root_mean_squared_error": root_mean_squared_error(y_true, y_predicted),
        "r2_score": r2_score(y_true, y_predicted),
    }


def print_evaluation(
    metrics: Dict[str, float],
    model_name: str = "Model",
) -> None:
    """Print model evaluation metrics."""
    print(f"\n{model_name} Performance:")
    print(f"  MAE:  {metrics['mean_absolute_error']:.4f}")
    print(f"  RMSE: {metrics['root_mean_squared_error']:.4f}")
    print(f"  R²:   {metrics['r2_score']:.4f}")


def save_model(model: Any, output_path: str) -> None:
    """Save a trained model to disk."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as file:
        pickle.dump(model, file)
    print(f"[INFO] Model saved to: {output_path}")


def load_model(model_path: str) -> Any:
    """Load a trained model from disk."""
    with open(model_path, "rb") as file:
        model = pickle.load(file)
    print(f"[INFO] Model loaded from: {model_path}")
    return model


def perform_grid_search(
    pipeline: Any,
    parameters: Dict[str, list],
    features_train: pd.DataFrame,
    target_train: pd.Series,
    scoring: str = "neg_root_mean_squared_error",
    cv_folds: int = DEFAULT_CV_FOLDS,
) -> Tuple[Any, Dict[str, Any]]:
    """Perform grid search for hyperparameter tuning."""
    grid_search = GridSearchCV(
        pipeline,
        parameters,
        cv=cv_folds,
        scoring=scoring,
        n_jobs=-1,
        verbose=1
    )

    grid_search.fit(features_train, target_train)

    return grid_search.best_estimator_, grid_search.best_params_


def remove_columns(
    dataframe: pd.DataFrame,
    columns_to_remove: list,
) -> pd.DataFrame:
    """Remove specified columns from dataframe, ignoring missing ones."""
    return dataframe.drop(columns=columns_to_remove, errors="ignore")


def prepare_features_and_target(
    dataframe: pd.DataFrame,
    target_column: str,
    columns_to_drop: list = None,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Prepare features and target from a dataframe."""
    if columns_to_drop:
        dataframe = remove_columns(dataframe, columns_to_drop)

    features = dataframe.drop(columns=[target_column])
    target = dataframe[target_column]

    return features, target

