"""Reusable machine learning and feature engineering utilities."""

import pickle
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler


DEFAULT_TEST_SIZE = 0.2
DEFAULT_RANDOM_STATE = 42
DEFAULT_CV_FOLDS = 5

POSITION_GROUPS = {
    "goalkeeper": [
        "Torwart",
    ],
    "defense": [
        "Linker Verteidiger",
        "Abwehr",
        "Rechter Verteidiger",
        "Innenverteidiger",
    ],
    "midfield": [
        "Defensives Mittelfeld",
        "Linkes Mittelfeld",
        "Mittelfeld",
        "Offensives Mittelfeld",
        "Zentrales Mittelfeld",
        "Rechtes Mittelfeld",
    ],
    "offense": [
        "Hängende Spitze",
        "Linksaußen",
        "Mittelstürmer",
        "Rechtsaußen",
        "Sturm",
    ],
}

POSITION_TO_GROUP = {
    position: group
    for group, positions in POSITION_GROUPS.items()
    for position in positions
}

RECOMMENDER_TARGET_COLUMN = "target_next_season_avg_rating"
RECOMMENDER_ID_COLUMNS = ["player_id", "position_group"]
RECOMMENDER_CATEGORICAL_COLUMNS = ["position"]

PLAYER_STATS_COLUMN_CANDIDATES = {
    "player_id": ["player_id"],
    "match_id": ["match_id"],
    "club_id": ["club_id"],
    "season": ["season"],
    "goals": ["goals"],
    "assists": ["assists"],
    "yellow_cards": ["yellow_cards", "yellow_card", "yellow"],
    "red_cards": ["red_cards", "red_card", "red"],
    "yellow_red_cards": ["yellow_red_cards", "yellow_red_card", "yellow_red"],
    "started": ["started", "start_eleven", "starting_eleven"],
    "minutes": ["minutes"],
    "rating": ["rating"],
    "team_goals": ["team_goals"],
    "team_conceded": ["team_conceded"],
}

MATCH_COLUMN_CANDIDATES = {
    "match_id": ["match_id"],
    "season": ["season"],
    "competition": ["competition", "league"],
    "home_club_id": ["home_club_id"],
    "away_club_id": ["away_club_id"],
    "home_goals": ["home_goals"],
    "away_goals": ["away_goals"],
    "match_date": ["match_date", "game_date", "date"],
}

PLAYER_COLUMN_CANDIDATES = {
    "player_id": ["player_id"],
    "player_name": ["player_name", "name"],
    "birth_date": ["birth_date", "date_of_birth"],
    "position": ["position"],
}


def split_data_randomly(
    features: pd.DataFrame,
    target: pd.Series,
    test_size: float = DEFAULT_TEST_SIZE,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split features and target randomly into train and test sets."""
    return train_test_split(
        features,
        target,
        test_size=test_size,
        random_state=random_state,
    )


def split_data_by_group(
    dataframe: pd.DataFrame,
    features: pd.DataFrame,
    target: pd.Series,
    group_column: str,
    test_size: float = DEFAULT_TEST_SIZE,
    random_state: int = DEFAULT_RANDOM_STATE,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split features and target by a group column to avoid data leakage."""
    unique_groups = dataframe[group_column].dropna().unique()

    train_groups, test_groups = train_test_split(
        unique_groups,
        test_size=test_size,
        random_state=random_state,
    )

    mask_train = dataframe[group_column].isin(train_groups)
    mask_test = dataframe[group_column].isin(test_groups)

    return (
        features.loc[mask_train],
        features.loc[mask_test],
        target.loc[mask_train],
        target.loc[mask_test],
    )


def build_preprocessor(
    numeric_columns: List[str],
    categorical_columns: List[str],
    boolean_columns: List[str],
) -> ColumnTransformer:
    """Build a reusable preprocessing transformer for numeric, categorical and boolean features."""
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    boolean_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
        ]
    )

    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_transformer, numeric_columns),
            ("categorical", categorical_transformer, categorical_columns),
            ("boolean", boolean_transformer, boolean_columns),
        ]
    )


def evaluate_model(
    y_true: pd.Series,
    y_predicted: np.ndarray,
) -> Dict[str, float]:
    """Calculate standard regression metrics for model predictions."""
    return {
        "mean_absolute_error": mean_absolute_error(y_true, y_predicted),
        "root_mean_squared_error": root_mean_squared_error(y_true, y_predicted),
        "r2_score": r2_score(y_true, y_predicted),
    }


def print_evaluation(
    metrics: Dict[str, float],
    model_name: str = "Model",
) -> None:
    """Print regression metrics in a compact format."""
    print(f"\n{model_name} Performance:")
    print(f"  MAE:  {metrics['mean_absolute_error']:.4f}")
    print(f"  RMSE: {metrics['root_mean_squared_error']:.4f}")
    print(f"  R²:   {metrics['r2_score']:.4f}")


def save_model(model: Any, output_path: str | Path) -> None:
    """Save a trained model to disk."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as file:
        pickle.dump(model, file)
    print(f"[INFO] Model saved to: {path}")


def load_model(model_path: str | Path) -> Any:
    """Load a trained model from disk."""
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")
    with path.open("rb") as file:
        model = pickle.load(file)
    print(f"[INFO] Model loaded from: {path}")
    return model


def perform_grid_search(
    pipeline: Any,
    parameters: Dict[str, list],
    features_train: pd.DataFrame,
    target_train: pd.Series,
    scoring: str = "neg_root_mean_squared_error",
    cv_folds: int = DEFAULT_CV_FOLDS,
) -> Tuple[Any, Dict[str, Any]]:
    """Tune a pipeline with grid search and return the best estimator and parameters."""
    grid_search = GridSearchCV(
        pipeline,
        parameters,
        cv=cv_folds,
        scoring=scoring,
        n_jobs=-1,
        verbose=1,
    )
    grid_search.fit(features_train, target_train)
    return grid_search.best_estimator_, grid_search.best_params_


def remove_columns(
    dataframe: pd.DataFrame,
    columns_to_remove: List[str],
) -> pd.DataFrame:
    """Remove columns from a dataframe while ignoring missing columns."""
    return dataframe.drop(columns=columns_to_remove, errors="ignore")


def prepare_features_and_target(
    dataframe: pd.DataFrame,
    target_column: str,
    columns_to_drop: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, pd.Series]:
    """Split a dataframe into features and target."""
    prepared_dataframe = dataframe.copy()
    if columns_to_drop:
        prepared_dataframe = remove_columns(prepared_dataframe, columns_to_drop)

    features = prepared_dataframe.drop(columns=[target_column])
    target = prepared_dataframe[target_column]

    return features, target


def standardize_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Convert dataframe column names to lowercase snake case."""
    result = dataframe.copy()
    result.columns = (
        result.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )
    return result


def pick_column(
    dataframe: pd.DataFrame,
    candidates: List[str],
    required: bool = True,
) -> Optional[str]:
    """Find the first matching column from a candidate list."""
    columns = list(dataframe.columns)

    for candidate in candidates:
        if candidate in columns:
            return candidate

    for candidate in candidates:
        for column in columns:
            if candidate in column:
                return column

    if required:
        raise KeyError(f"No matching column found for candidates: {candidates}")
    return None


def rename_detected_columns(
    dataframe: pd.DataFrame,
    column_candidates: Dict[str, List[str]],
    optional_columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Rename detected dataframe columns to canonical names."""
    optional_columns = optional_columns or []
    rename_mapping = {}

    for target_column, candidates in column_candidates.items():
        source_column = pick_column(
            dataframe,
            candidates,
            required=target_column not in optional_columns,
        )
        if source_column is not None:
            rename_mapping[source_column] = target_column

    return dataframe.rename(columns=rename_mapping)


def parse_season_start_year(value: Any) -> float:
    """Parse a season value and return the start year as a four-digit year."""
    if pd.isna(value):
        return np.nan

    season = str(value).strip()

    match = re.fullmatch(r"(\d{2})\s*[/\-]\s*(\d{2})", season)
    if match:
        return float(2000 + int(match.group(1)))

    match = re.fullmatch(r"(20\d{2})\s*[/\-]\s*(\d{2})", season)
    if match:
        return float(match.group(1))

    match = re.fullmatch(r"(20\d{2})\s*[/\-]\s*(20\d{2})", season)
    if match:
        return float(match.group(1))

    match = re.fullmatch(r"20\d{2}", season)
    if match:
        return float(season)

    return np.nan


def normalize_league(league: Any) -> Any:
    """Normalize league names to stable English-friendly league labels."""
    if pd.isna(league):
        return np.nan

    value = str(league).strip().lower()

    if value == "pl" or "promotion league" in value:
        return "Promotion League"

    if value.startswith("1_liga") or re.search(r"\b1\.?\s*liga\b", value):
        return "1. Liga"

    return np.nan


def normalize_text_series(series: pd.Series) -> pd.Series:
    """Normalize text values to lowercase strings with compact whitespace."""
    return series.fillna("").astype(str).str.strip().str.lower().str.replace(r"\s+", " ", regex=True)


def to_binary_series(series: pd.Series) -> pd.Series:
    """Convert common boolean-like values to integer indicators."""
    numeric_values = pd.to_numeric(series, errors="coerce")
    text_values = normalize_text_series(series)
    return ((numeric_values.fillna(0) > 0) | text_values.isin(["true", "yes", "y", "1"])).astype(int)


def ensure_columns(dataframe: pd.DataFrame, default_values: Dict[str, Any]) -> pd.DataFrame:
    """Ensure that a dataframe contains required columns with default values."""
    result = dataframe.copy()
    for column, default_value in default_values.items():
        if column not in result.columns:
            result[column] = default_value
    return result


def add_match_result(
    dataframe: pd.DataFrame,
    output_column: str = "result",
) -> pd.DataFrame:
    """Add the match result from the perspective of each player's club."""
    result = dataframe.copy()
    result[output_column] = None

    is_home_team = result["club_id"] == result["home_club_id"]
    is_away_team = result["club_id"] == result["away_club_id"]

    result.loc[is_home_team & (result["home_goals"] > result["away_goals"]), output_column] = "win"
    result.loc[is_home_team & (result["home_goals"] < result["away_goals"]), output_column] = "loss"
    result.loc[is_home_team & (result["home_goals"] == result["away_goals"]), output_column] = "draw"

    result.loc[is_away_team & (result["away_goals"] > result["home_goals"]), output_column] = "win"
    result.loc[is_away_team & (result["away_goals"] < result["home_goals"]), output_column] = "loss"
    result.loc[is_away_team & (result["away_goals"] == result["home_goals"]), output_column] = "draw"

    return result


def add_age_on_august_first(
    dataframe: pd.DataFrame,
    season_column: str = "season",
    birth_date_column: str = "birth_date",
    output_column: str = "age",
) -> pd.DataFrame:
    """Add player age at the first of August of the given season start year."""
    result = dataframe.copy()
    season_years = pd.to_numeric(result[season_column], errors="coerce")
    birth_dates = pd.to_datetime(result[birth_date_column], errors="coerce")
    cutoff_dates = pd.to_datetime(
        season_years.astype("Int64").astype(str) + "-08-01",
        errors="coerce",
    )

    had_birthday = (
        (cutoff_dates.dt.month > birth_dates.dt.month)
        | (
            (cutoff_dates.dt.month == birth_dates.dt.month)
            & (cutoff_dates.dt.day >= birth_dates.dt.day)
        )
    )

    result[output_column] = cutoff_dates.dt.year - birth_dates.dt.year - (~had_birthday).astype(float)
    result.loc[cutoff_dates.isna() | birth_dates.isna(), output_column] = np.nan

    return result


def add_league_indicators(
    dataframe: pd.DataFrame,
    competition_column: str = "competition",
) -> pd.DataFrame:
    """Add percentage-ready league indicator columns for 1. Liga and Promotion League."""
    result = dataframe.copy()
    normalized_competition = normalize_text_series(result[competition_column])
    result["is_first_league"] = normalized_competition.str.contains(r"\b1\.?\s*liga\b", regex=True).astype(int)
    result["is_promotion_league"] = (
        normalized_competition.str.contains("promotion league", regex=False)
        | normalized_competition.str.fullmatch("pl")
    ).astype(int)
    return result


def prepare_recommender_source_data(
    player_stats: pd.DataFrame,
    matches: pd.DataFrame,
    players: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Standardize, rename and type-cast source tables for recommender feature engineering."""
    player_stats_prepared = rename_detected_columns(
        standardize_columns(player_stats),
        PLAYER_STATS_COLUMN_CANDIDATES,
        optional_columns=[
            "season",
            "goals",
            "assists",
            "yellow_cards",
            "red_cards",
            "yellow_red_cards",
            "started",
            "minutes",
            "rating",
            "team_goals",
            "team_conceded",
        ],
    )
    matches_prepared = rename_detected_columns(
        standardize_columns(matches),
        MATCH_COLUMN_CANDIDATES,
        optional_columns=["season", "competition", "match_date"],
    )
    players_prepared = rename_detected_columns(
        standardize_columns(players),
        PLAYER_COLUMN_CANDIDATES,
        optional_columns=["player_name", "birth_date", "position"],
    )

    player_stats_prepared = ensure_columns(
        player_stats_prepared,
        {
            "goals": 0,
            "assists": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            "yellow_red_cards": 0,
            "started": 0,
            "minutes": 0,
            "rating": np.nan,
            "team_goals": 0,
            "team_conceded": 0,
        },
    )
    matches_prepared = ensure_columns(
        matches_prepared,
        {
            "home_goals": np.nan,
            "away_goals": np.nan,
            "competition": "",
        },
    )
    players_prepared = ensure_columns(
        players_prepared,
        {
            "birth_date": pd.NaT,
            "position": "unknown",
        },
    )

    numeric_player_stat_columns = [
        "goals",
        "assists",
        "yellow_cards",
        "red_cards",
        "yellow_red_cards",
        "minutes",
        "rating",
        "team_goals",
        "team_conceded",
    ]

    for column in numeric_player_stat_columns:
        player_stats_prepared[column] = pd.to_numeric(
            player_stats_prepared[column].astype(str).str.replace(",", ".", regex=False),
            errors="coerce",
        )

    matches_prepared["home_goals"] = pd.to_numeric(matches_prepared["home_goals"], errors="coerce")
    matches_prepared["away_goals"] = pd.to_numeric(matches_prepared["away_goals"], errors="coerce")
    player_stats_prepared["started"] = to_binary_series(player_stats_prepared["started"])
    players_prepared["birth_date"] = pd.to_datetime(players_prepared["birth_date"], errors="coerce")
    players_prepared["position"] = players_prepared["position"].fillna("unknown").astype(str).str.strip()

    return player_stats_prepared, matches_prepared, players_prepared


def build_recommender_match_dataset(
    player_stats: pd.DataFrame,
    matches: pd.DataFrame,
    players: pd.DataFrame,
) -> pd.DataFrame:
    """Build a match-level dataset with player, match and league context."""
    player_stats_prepared, matches_prepared, players_prepared = prepare_recommender_source_data(
        player_stats,
        matches,
        players,
    )

    match_columns = ["match_id", "home_club_id", "away_club_id", "home_goals", "away_goals", "competition"]
    optional_match_columns = ["season", "match_date"]
    match_columns.extend([column for column in optional_match_columns if column in matches_prepared.columns])

    match_frame = matches_prepared[match_columns].copy()
    if "season" in match_frame.columns:
        match_frame = match_frame.rename(columns={"season": "season_match"})

    player_frame = players_prepared[["player_id", "birth_date", "position"]].drop_duplicates("player_id")

    dataset = player_stats_prepared.merge(match_frame, on="match_id", how="left")
    dataset = dataset.merge(player_frame, on="player_id", how="left")

    if "season" not in dataset.columns:
        dataset["season"] = dataset.get("season_match")
    elif "season_match" in dataset.columns:
        dataset["season"] = dataset["season"].fillna(dataset["season_match"])

    dataset["season"] = dataset["season"].map(parse_season_start_year)
    dataset = dataset.drop_duplicates(subset=["player_id", "match_id", "club_id"]).copy()
    dataset = add_age_on_august_first(dataset)
    dataset = add_match_result(dataset)
    dataset = add_league_indicators(dataset)
    dataset["is_win"] = (dataset["result"] == "win").astype(int)
    dataset["is_draw"] = (dataset["result"] == "draw").astype(int)
    dataset["is_loss"] = (dataset["result"] == "loss").astype(int)

    return dataset


def build_recommender_season_features(
    player_stats: pd.DataFrame,
    matches: pd.DataFrame,
    players: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate match-level player data into one row per player and season."""
    match_dataset = build_recommender_match_dataset(player_stats, matches, players)

    club_season_matches = (
        match_dataset[["season", "club_id", "match_id"]]
        .drop_duplicates()
        .groupby(["season", "club_id"], as_index=False)
        .agg(team_matches_in_season=("match_id", "nunique"))
    )

    player_season_team_matches = (
        match_dataset[["player_id", "season", "club_id"]]
        .drop_duplicates()
        .merge(club_season_matches, on=["season", "club_id"], how="left")
        .groupby(["player_id", "season"], as_index=False)
        .agg(team_matches_in_season=("team_matches_in_season", "sum"))
    )

    season_features = (
        match_dataset.groupby(["player_id", "season"], as_index=False)
        .agg(
            age=("age", "first"),
            position=("position", "first"),
            matches_played=("match_id", "nunique"),
            goals_total=("goals", "sum"),
            assists_total=("assists", "sum"),
            red_cards_total=("red_cards", "sum"),
            yellow_cards_total=("yellow_cards", "sum"),
            yellow_red_cards_total=("yellow_red_cards", "sum"),
            starts_total=("started", "sum"),
            minutes_total=("minutes", "sum"),
            team_goals_total=("team_goals", "sum"),
            team_conceded_total=("team_conceded", "sum"),
            wins_total=("is_win", "sum"),
            draws_total=("is_draw", "sum"),
            losses_total=("is_loss", "sum"),
            first_league_share=("is_first_league", "mean"),
            promotion_league_share=("is_promotion_league", "mean"),
            avg_rating_current=("rating", "mean"),
        )
    )

    per_match_columns = {
        "goals_per_match": "goals_total",
        "assists_per_match": "assists_total",
        "red_cards_per_match": "red_cards_total",
        "yellow_cards_per_match": "yellow_cards_total",
        "yellow_red_cards_per_match": "yellow_red_cards_total",
        "starts_per_match": "starts_total",
        "minutes_per_match": "minutes_total",
        "team_goals_per_match": "team_goals_total",
        "team_conceded_per_match": "team_conceded_total",
        "wins_per_match": "wins_total",
        "draws_per_match": "draws_total",
        "losses_per_match": "losses_total",
    }

    for output_column, source_column in per_match_columns.items():
        season_features[output_column] = season_features[source_column] / season_features["matches_played"]

    season_features["first_league_share"] = season_features["first_league_share"] * 100
    season_features["promotion_league_share"] = season_features["promotion_league_share"] * 100

    season_features = season_features.merge(
        player_season_team_matches,
        on=["player_id", "season"],
        how="left",
    )
    season_features["appearance_ratio"] = season_features["matches_played"] / season_features["team_matches_in_season"]
    season_features["position"] = season_features["position"].fillna("unknown").astype(str).str.strip()
    season_features = add_position_group(season_features)

    return season_features.replace([np.inf, -np.inf], np.nan)


def build_recommender_training_dataset(
    season_features: pd.DataFrame,
    first_training_season: int = 2020,
    last_training_season: int = 2024,
) -> pd.DataFrame:
    """Create a supervised recommender dataset with next-season average rating as target."""
    sorted_features = season_features.sort_values(["player_id", "season"]).reset_index(drop=True)
    sorted_features["next_season"] = sorted_features.groupby("player_id")["season"].shift(-1)
    sorted_features[RECOMMENDER_TARGET_COLUMN] = sorted_features.groupby("player_id")["avg_rating_current"].shift(-1)

    model_dataset = sorted_features[
        (sorted_features["next_season"] == sorted_features["season"] + 1)
        & (sorted_features["season"] >= first_training_season)
        & (sorted_features["season"] <= last_training_season)
    ].copy()

    final_columns = [
        "player_id",
        "season",
        "age",
        "position",
        "position_group",
        "avg_rating_current",
        "appearance_ratio",
        "goals_per_match",
        "goals_total",
        "assists_per_match",
        "assists_total",
        "red_cards_per_match",
        "yellow_cards_per_match",
        "yellow_red_cards_per_match",
        "red_cards_total",
        "yellow_cards_total",
        "yellow_red_cards_total",
        "starts_per_match",
        "starts_total",
        "minutes_per_match",
        "minutes_total",
        "matches_played",
        "team_goals_per_match",
        "team_goals_total",
        "team_conceded_per_match",
        "team_conceded_total",
        "wins_per_match",
        "draws_per_match",
        "losses_per_match",
        "wins_total",
        "draws_total",
        "losses_total",
        "first_league_share",
        "promotion_league_share",
        RECOMMENDER_TARGET_COLUMN,
    ]

    return model_dataset[final_columns].dropna(subset=[RECOMMENDER_TARGET_COLUMN]).reset_index(drop=True)


def add_position_group(
    dataframe: pd.DataFrame,
    position_column: str = "position",
    output_column: str = "position_group",
) -> pd.DataFrame:
    """Add a position group based on detailed German position names."""
    result = dataframe.copy()
    result[output_column] = result[position_column].map(POSITION_TO_GROUP)
    return result


def get_recommender_feature_columns(dataframe: pd.DataFrame) -> List[str]:
    """Return usable feature columns for the recommender model."""
    excluded_columns = set(RECOMMENDER_ID_COLUMNS + [RECOMMENDER_TARGET_COLUMN])
    return [column for column in dataframe.columns if column not in excluded_columns]


def get_recommender_numeric_columns(dataframe: pd.DataFrame) -> List[str]:
    """Return numeric recommender feature columns."""
    feature_columns = get_recommender_feature_columns(dataframe)
    return [
        column
        for column in feature_columns
        if column not in RECOMMENDER_CATEGORICAL_COLUMNS
        and pd.api.types.is_numeric_dtype(dataframe[column])
    ]


def align_prediction_features(
    dataframe: pd.DataFrame,
    feature_columns: List[str],
) -> pd.DataFrame:
    """Align prediction data to the exact feature columns used for training."""
    result = dataframe.copy()
    for column in feature_columns:
        if column not in result.columns:
            result[column] = np.nan
    return result[feature_columns]
