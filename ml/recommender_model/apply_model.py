"""Apply live recommender models to players from the current season."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

CURRENT_DIR = Path(__file__).resolve().parent
ML_ROOT = CURRENT_DIR.parent
sys.path.append(str(ML_ROOT))

from toolkit.ml_utilities import (  # noqa: E402
    POSITION_GROUPS,
    POSITION_TO_GROUP,
    align_prediction_features,
    build_recommender_season_features,
    get_recommender_feature_columns,
    load_model,
    normalize_league,
    parse_season_start_year,
)

DEFAULT_DB_URL = "postgresql+psycopg2://postgres:postgres@host.docker.internal:5434/iamscout"
CSV_ENCODING = "utf-8-sig"
CURRENT_SEASON_KEY = "season"
PLAYER_ID_COLUMN = "player_id"
POSITION_GROUP_COLUMN = "position_group"
PREDICTION_COLUMN = "prediction"
RAW_PREDICTION_COLUMN = "prediction_raw"
LEAGUE_ADJUSTMENT_COLUMN = "league_adjustment"
ADJUSTED_PREDICTION_COLUMN = "prediction_adjusted"
MIN_MATCHES_FOR_LEAGUE_DIFFERENCE = 5
LEAGUE_DIFFERENCE_FALLBACK = 0.0

PLAYER_COLUMNS = [
    "player_id",
    "player_name",
    "nationality",
    "date_of_birth",
    "height",
    "position",
    "prediction",
]

PLAYER_STATS_COLUMNS = [
    "player_id",
    "match_id",
    "club_id",
    "goals",
    "assists",
    "yellow",
    "yellow_red",
    "red",
    "start_eleven",
    "minutes",
    "on_min",
    "off_min",
    "team_goals",
    "team_conceded",
    "rating",
]

MATCH_COLUMNS = [
    "match_id",
    "season",
    "league",
    "date",
    "home_club_id",
    "away_club_id",
    "home_goals",
    "away_goals",
]

IDENTIFIER_COLUMNS = [
    "player_id",
    "match_id",
    "club_id",
    "home_club_id",
    "away_club_id",
]

MODEL_FILENAME_TEMPLATE = "recommender_model_{position_group}.pkl"


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for live recommender inference."""
    parser = argparse.ArgumentParser(description="Apply live recommender model predictions.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--db-url", type=str, default=DEFAULT_DB_URL)
    parser.add_argument("--runtime-path", type=Path, default=None)
    parser.add_argument("--player-stats-path", type=Path, default=None)
    parser.add_argument("--matches-path", type=Path, default=None)
    parser.add_argument("--players-path", type=Path, default=None)
    parser.add_argument("--model-dir", type=Path, default=None)
    return parser.parse_args()


def resolve_project_paths(arguments: argparse.Namespace) -> dict[str, Path]:
    """Resolve all project paths required for recommender inference."""
    project_root = arguments.project_root.resolve()
    transform_dir = project_root / "data" / "transform"
    model_dir = arguments.model_dir or project_root / "ml" / "recommender_model"

    return {
        "project_root": project_root,
        "runtime_path": arguments.runtime_path or project_root / "web_scraping" / "runtime" / "last_scrapes.json",
        "player_stats_path": arguments.player_stats_path or transform_dir / "player_stats.csv",
        "matches_path": arguments.matches_path or transform_dir / "matches.csv",
        "players_path": arguments.players_path or transform_dir / "players.csv",
        "model_dir": model_dir,
    }


def read_runtime_season(runtime_path: Path) -> int:
    """Read the current season start year from the runtime state file."""
    if not runtime_path.exists():
        raise FileNotFoundError(f"last_scrapes.json not found: {runtime_path}")

    with runtime_path.open("r", encoding="utf-8") as file:
        runtime_state = json.load(file)

    season = runtime_state.get(CURRENT_SEASON_KEY)
    if season is None:
        raise KeyError("Key 'season' not found in last_scrapes.json")

    return int(season)


def read_database_table(engine: Engine, query: str) -> pd.DataFrame:
    """Read a SQL query into a dataframe and attach a clear error message."""
    try:
        return pd.read_sql_query(text(query), engine)
    except Exception as error:
        raise RuntimeError(f"Could not read database query: {query}") from error


def load_database_players(engine: Engine) -> pd.DataFrame:
    """Load player metadata from the database."""
    query = """
        SELECT
            player_id,
            player_name,
            nationality,
            date_of_birth,
            height,
            position,
            prediction
        FROM players
    """
    return read_database_table(engine, query)


def load_database_matches(engine: Engine) -> pd.DataFrame:
    """Load match metadata from the database."""
    query = """
        SELECT
            match_id,
            season,
            league,
            game_date AS date,
            home_club_id,
            away_club_id,
            home_goals,
            away_goals
        FROM matches
    """
    return read_database_table(engine, query)


def load_database_player_stats(engine: Engine) -> pd.DataFrame:
    """Load player statistics from the database."""
    query = """
        SELECT
            player_id,
            match_id,
            club_id,
            goals,
            assists,
            yellow,
            yellow_red,
            red,
            start_eleven,
            minutes,
            on_min,
            off_min,
            team_goals,
            team_conceded,
            rating
        FROM player_stats
    """
    return read_database_table(engine, query)


def read_optional_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    """Read a CSV file when it exists and return an empty dataframe otherwise."""
    if not path.exists():
        return pd.DataFrame(columns=columns)

    dataframe = pd.read_csv(path)
    if dataframe.empty:
        return pd.DataFrame(columns=columns)

    return dataframe


def ensure_expected_columns(dataframe: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Ensure that a dataframe contains the expected output columns."""
    result = dataframe.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = np.nan
    return result[columns]


def normalize_identifier_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normalize identifier columns to stripped strings for stable joins."""
    result = dataframe.copy()
    for column in IDENTIFIER_COLUMNS:
        if column in result.columns:
            result[column] = result[column].dropna().astype(str).str.strip()
    return result


def combine_tables(
    database_table: pd.DataFrame,
    transform_table: pd.DataFrame,
    subset_columns: list[str],
) -> pd.DataFrame:
    """Combine database and transformed rows while keeping transformed rows last."""
    frames = [database_table, transform_table]
    non_empty_frames = [frame for frame in frames if not frame.empty]

    if not non_empty_frames:
        return pd.DataFrame()

    combined = pd.concat(non_empty_frames, ignore_index=True, sort=False)
    combined = normalize_identifier_columns(combined)
    return combined.drop_duplicates(subset=subset_columns, keep="last").reset_index(drop=True)


def load_live_tables(paths: dict[str, Path], engine: Engine) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load database and transformed tables needed for recommender inference."""
    database_players = load_database_players(engine)
    database_matches = load_database_matches(engine)
    database_player_stats = load_database_player_stats(engine)

    transform_players = read_optional_csv(paths["players_path"], PLAYER_COLUMNS)
    transform_matches = read_optional_csv(paths["matches_path"], MATCH_COLUMNS)
    transform_player_stats = read_optional_csv(paths["player_stats_path"], PLAYER_STATS_COLUMNS)

    players = combine_tables(database_players, transform_players, [PLAYER_ID_COLUMN])
    matches = combine_tables(database_matches, transform_matches, ["match_id"])
    player_stats = combine_tables(
        database_player_stats,
        transform_player_stats,
        ["player_id", "match_id", "club_id"],
    )

    return player_stats, matches, players


def build_position_group_model_path(model_dir: Path, position_group: str) -> Path:
    """Build the path to a recommender model for a position group."""
    return model_dir / MODEL_FILENAME_TEMPLATE.format(position_group=position_group)


def load_position_group_model(model_dir: Path, position_group: str) -> Any | None:
    """Load a recommender model for one position group if available."""
    model_path = build_position_group_model_path(model_dir, position_group)
    if not model_path.exists():
        print(f"[WARN] Skipped {position_group}: model file not found at {model_path}")
        return None

    return load_model(model_path)


def is_pipeline_model(model: Any) -> bool:
    """Return whether the loaded model contains its own preprocessing pipeline."""
    return hasattr(model, "named_steps")


def get_booster_feature_columns(model: Any) -> list[str]:
    """Return feature columns stored in an XGBoost booster when available."""
    if not hasattr(model, "get_booster"):
        return []

    booster_feature_names = model.get_booster().feature_names
    if not booster_feature_names:
        return []

    return list(booster_feature_names)


def get_raw_model_feature_columns(model: Any, group_dataset: pd.DataFrame) -> list[str]:
    """Return raw feature columns for models that include preprocessing internally."""
    if hasattr(model, "feature_columns_"):
        return list(model.feature_columns_)

    if hasattr(model, "feature_names_in_"):
        return list(model.feature_names_in_)

    return get_recommender_feature_columns(group_dataset)


def build_position_dummy_columns(position_group: str) -> list[str]:
    """Build expected one-hot encoded position columns for a position group."""
    return [f"position_{position}" for position in POSITION_GROUPS[position_group]]


def expand_position_feature_columns(feature_columns: list[str], position_group: str) -> list[str]:
    """Replace the raw position column by one-hot encoded position columns."""
    expanded_columns = []

    for column in feature_columns:
        if column == "position":
            expanded_columns.extend(build_position_dummy_columns(position_group))
        else:
            expanded_columns.append(column)

    return list(dict.fromkeys(expanded_columns))


def one_hot_encode_position_features(features: pd.DataFrame, position_group: str) -> pd.DataFrame:
    """One-hot encode the detailed player position for a position-group model."""
    encoded_features = pd.get_dummies(
        features,
        columns=["position"],
        prefix="position",
        dtype=int,
    )

    for dummy_column in build_position_dummy_columns(position_group):
        if dummy_column not in encoded_features.columns:
            encoded_features[dummy_column] = 0

    return encoded_features


def cast_numeric_features(features: pd.DataFrame) -> pd.DataFrame:
    """Cast model features to numeric values accepted by XGBoost."""
    result = features.copy()

    for column in result.columns:
        if pd.api.types.is_bool_dtype(result[column]):
            result[column] = result[column].astype(int)
        else:
            result[column] = pd.to_numeric(result[column], errors="coerce")

    return result


def contains_position_dummy_columns(feature_columns: list[str]) -> bool:
    """Return whether a feature list already contains one-hot encoded position columns."""
    return any(column.startswith("position_") for column in feature_columns)


def prepare_model_features(
    model: Any,
    group_dataset: pd.DataFrame,
    position_group: str,
) -> pd.DataFrame:
    """Prepare prediction features with the same position encoding used during training."""
    raw_feature_columns = get_raw_model_feature_columns(model, group_dataset)

    if is_pipeline_model(model):
        return align_prediction_features(group_dataset, raw_feature_columns)

    booster_feature_columns = get_booster_feature_columns(model)
    if booster_feature_columns:
        expected_feature_columns = booster_feature_columns
    else:
        expected_feature_columns = expand_position_feature_columns(
            raw_feature_columns,
            position_group,
        )

    needs_position_encoding = (
        "position" in raw_feature_columns
        or contains_position_dummy_columns(expected_feature_columns)
    )

    if needs_position_encoding:
        feature_source = one_hot_encode_position_features(group_dataset, position_group)
    else:
        feature_source = group_dataset.copy()

    aligned_features = align_prediction_features(feature_source, expected_feature_columns)
    return cast_numeric_features(aligned_features)


def predict_position_group(
    prediction_dataset: pd.DataFrame,
    model_dir: Path,
    position_group: str,
) -> pd.DataFrame:
    """Predict ratings for one position group with the matching saved model."""
    model = load_position_group_model(model_dir, position_group)
    if model is None:
        return pd.DataFrame(columns=[PLAYER_ID_COLUMN, RAW_PREDICTION_COLUMN])

    group_dataset = prediction_dataset[
        prediction_dataset[POSITION_GROUP_COLUMN] == position_group
    ].copy()

    if group_dataset.empty:
        return pd.DataFrame(columns=[PLAYER_ID_COLUMN, RAW_PREDICTION_COLUMN])

    features = prepare_model_features(model, group_dataset, position_group)

    predictions = group_dataset[[PLAYER_ID_COLUMN, POSITION_GROUP_COLUMN, "first_league_share"]].copy()
    predictions[RAW_PREDICTION_COLUMN] = model.predict(features)
    print(f"[INFO] Predicted {len(predictions)} players with {position_group} model")
    return predictions


def build_match_rating_dataset(
    player_stats: pd.DataFrame,
    matches: pd.DataFrame,
    players: pd.DataFrame,
) -> pd.DataFrame:
    """Create a match-level rating dataset with league and position context."""
    player_stats_prepared = normalize_identifier_columns(player_stats)
    matches_prepared = normalize_identifier_columns(matches)
    players_prepared = normalize_identifier_columns(players)

    dataset = (
        player_stats_prepared.merge(
            matches_prepared[["match_id", "season", "league"]],
            on="match_id",
            how="left",
        )
        .merge(
            players_prepared[["player_id", "player_name", "position"]],
            on="player_id",
            how="left",
        )
    )

    dataset["league_group"] = dataset["league"].map(normalize_league)
    dataset["season_start_year"] = dataset["season"].map(parse_season_start_year)
    dataset[POSITION_GROUP_COLUMN] = dataset["position"].map(POSITION_TO_GROUP)
    dataset["rating"] = pd.to_numeric(dataset["rating"], errors="coerce")
    dataset["minutes"] = pd.to_numeric(dataset["minutes"], errors="coerce")

    return dataset[
        dataset["league_group"].isin(["1. Liga", "Promotion League"])
        & dataset["rating"].notna()
        & dataset["season_start_year"].notna()
        & dataset[POSITION_GROUP_COLUMN].notna()
        & (dataset["minutes"] > 0)
    ].copy()


def aggregate_player_season_ratings(dataset: pd.DataFrame) -> pd.DataFrame:
    """Aggregate match ratings to player-season ratings."""
    player_season = (
        dataset.groupby(
            [
                "player_id",
                "player_name",
                "season",
                "season_start_year",
                "league_group",
                "position",
                POSITION_GROUP_COLUMN,
            ],
            as_index=False,
        )
        .agg(
            avg_rating=("rating", "mean"),
            matches_played=("match_id", "nunique"),
            minutes_total=("minutes", "sum"),
        )
    )

    return player_season[
        player_season["matches_played"] >= MIN_MATCHES_FOR_LEAGUE_DIFFERENCE
    ].copy()


def build_league_transition_pairs(player_season_ratings: pd.DataFrame) -> pd.DataFrame:
    """Build player-season pairs across 1. Liga and Promotion League."""
    first_league = player_season_ratings[
        player_season_ratings["league_group"] == "1. Liga"
    ].copy()
    promotion_league = player_season_ratings[
        player_season_ratings["league_group"] == "Promotion League"
    ].copy()

    first_league = first_league.rename(
        columns={
            "season": "season_first_league",
            "season_start_year": "season_year_first_league",
            "avg_rating": "avg_rating_first_league",
            "matches_played": "matches_first_league",
            "minutes_total": "minutes_first_league",
            "position": "position_first_league",
            POSITION_GROUP_COLUMN: "position_group_first_league",
        }
    )
    promotion_league = promotion_league.rename(
        columns={
            "season": "season_promotion_league",
            "season_start_year": "season_year_promotion_league",
            "avg_rating": "avg_rating_promotion_league",
            "matches_played": "matches_promotion_league",
            "minutes_total": "minutes_promotion_league",
            "position": "position_promotion_league",
            POSITION_GROUP_COLUMN: "position_group_promotion_league",
        }
    )

    pairs = first_league.merge(
        promotion_league,
        on=["player_id", "player_name"],
        how="inner",
    )
    pairs = pairs[
        (pairs["season_year_promotion_league"] - pairs["season_year_first_league"]).abs() == 1
    ].copy()
    pairs = pairs[
        pairs["position_group_first_league"] == pairs["position_group_promotion_league"]
    ].copy()

    pairs["rating_diff_promotion_minus_first_league"] = (
        pairs["avg_rating_promotion_league"] - pairs["avg_rating_first_league"]
    )

    return pairs


def calculate_league_differences(
    player_stats: pd.DataFrame,
    matches: pd.DataFrame,
    players: pd.DataFrame,
) -> dict[str, float]:
    """Calculate median league-difference adjustments by position group."""
    dataset = build_match_rating_dataset(player_stats, matches, players)
    if dataset.empty:
        return {position_group: LEAGUE_DIFFERENCE_FALLBACK for position_group in POSITION_GROUPS}

    player_season_ratings = aggregate_player_season_ratings(dataset)
    if player_season_ratings.empty:
        return {position_group: LEAGUE_DIFFERENCE_FALLBACK for position_group in POSITION_GROUPS}

    pairs = build_league_transition_pairs(player_season_ratings)
    if pairs.empty:
        return {position_group: LEAGUE_DIFFERENCE_FALLBACK for position_group in POSITION_GROUPS}

    summary = pairs.groupby("position_group_first_league")[
        "rating_diff_promotion_minus_first_league"
    ].median()

    return {
        position_group: float(summary.get(position_group, LEAGUE_DIFFERENCE_FALLBACK))
        for position_group in POSITION_GROUPS
    }


def apply_league_difference_adjustment(
    predictions: pd.DataFrame,
    league_differences: dict[str, float],
) -> pd.DataFrame:
    """Adjust raw predictions based on first-league share and position group."""
    result = predictions.copy()
    result[LEAGUE_ADJUSTMENT_COLUMN] = result[POSITION_GROUP_COLUMN].map(league_differences).fillna(0.0)
    result["first_league_share"] = pd.to_numeric(
        result["first_league_share"],
        errors="coerce",
    ).fillna(0.0)
    result[ADJUSTED_PREDICTION_COLUMN] = (
        result[RAW_PREDICTION_COLUMN]
        + result[LEAGUE_ADJUSTMENT_COLUMN] * (result["first_league_share"] / 100.0)
    )
    result[PREDICTION_COLUMN] = result[ADJUSTED_PREDICTION_COLUMN].round(2)
    return result


def build_prediction_dataset(
    player_stats: pd.DataFrame,
    matches: pd.DataFrame,
    players: pd.DataFrame,
    current_season: int,
) -> pd.DataFrame:
    """Build the current-season feature dataset used for live prediction."""
    season_features = build_recommender_season_features(player_stats, matches, players)
    prediction_dataset = season_features[
        season_features["season"] == float(current_season)
    ].copy()
    return prediction_dataset[prediction_dataset[POSITION_GROUP_COLUMN].notna()].copy()


def predict_current_season_players(
    prediction_dataset: pd.DataFrame,
    model_dir: Path,
    league_differences: dict[str, float],
) -> pd.DataFrame:
    """Predict current-season players and apply league-difference adjustments."""
    prediction_frames = [
        predict_position_group(prediction_dataset, model_dir, position_group)
        for position_group in POSITION_GROUPS
    ]
    prediction_frames = [frame for frame in prediction_frames if not frame.empty]

    if not prediction_frames:
        return pd.DataFrame(columns=[PLAYER_ID_COLUMN, PREDICTION_COLUMN])

    raw_predictions = pd.concat(prediction_frames, ignore_index=True)
    adjusted_predictions = apply_league_difference_adjustment(
        raw_predictions,
        league_differences,
    )
    adjusted_predictions = adjusted_predictions.dropna(subset=[PREDICTION_COLUMN])
    return adjusted_predictions.drop_duplicates(subset=[PLAYER_ID_COLUMN], keep="last")


def update_players_with_predictions(players: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    """Update players with live recommender predictions."""
    players_prepared = ensure_expected_columns(players, PLAYER_COLUMNS)
    players_prepared = normalize_identifier_columns(players_prepared)
    predictions_prepared = normalize_identifier_columns(
        predictions[[PLAYER_ID_COLUMN, PREDICTION_COLUMN]].copy()
    )

    result = players_prepared.drop(columns=[PREDICTION_COLUMN], errors="ignore")
    result = result.merge(predictions_prepared, on=PLAYER_ID_COLUMN, how="left")
    result[PREDICTION_COLUMN] = pd.to_numeric(result[PREDICTION_COLUMN], errors="coerce")
    return result[PLAYER_COLUMNS]


def save_players(players: pd.DataFrame, output_path: Path) -> None:
    """Save players with predictions to the transformed players file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    players.to_csv(output_path, index=False, encoding=CSV_ENCODING)
    predicted_count = int(players[PREDICTION_COLUMN].notna().sum())
    print(f"[INFO] Players with recommender predictions written to: {output_path}")
    print(f"[INFO] Recommender predictions: {predicted_count} of {len(players)}")


def print_league_differences(league_differences: dict[str, float]) -> None:
    """Print calculated league-difference adjustments."""
    print("[INFO] League-difference adjustments:")
    for position_group, adjustment in league_differences.items():
        print(f"[INFO]   {position_group}: {adjustment:.4f}")


def print_top_predictions(players: pd.DataFrame, predictions: pd.DataFrame) -> None:
    """Print the five highest live recommender predictions per position group."""
    if predictions.empty or PREDICTION_COLUMN not in predictions.columns:
        print("[INFO] No predictions available for top-player output")
        return

    player_metadata = players[
        [PLAYER_ID_COLUMN, "player_name", "position"]
    ].drop_duplicates(subset=[PLAYER_ID_COLUMN])

    top_players = predictions.merge(
        player_metadata,
        on=PLAYER_ID_COLUMN,
        how="left",
    )

    top_players["applied_league_difference"] = (
        top_players[LEAGUE_ADJUSTMENT_COLUMN]
        * (top_players["first_league_share"] / 100.0)
    ).round(4)

    display_columns = [
        PLAYER_ID_COLUMN,
        "player_name",
        "position",
        POSITION_GROUP_COLUMN,
        "first_league_share",
        RAW_PREDICTION_COLUMN,
        LEAGUE_ADJUSTMENT_COLUMN,
        "applied_league_difference",
        PREDICTION_COLUMN,
    ]

    print("[INFO] Top 5 recommender predictions per position group:")

    for position_group in POSITION_GROUPS:
        group_players = top_players[
            top_players[POSITION_GROUP_COLUMN] == position_group
        ].sort_values(PREDICTION_COLUMN, ascending=False)

        if group_players.empty:
            print(f"[INFO] No predictions for {position_group}")
            continue

        print(f"\n[INFO] {position_group.upper()}")
        print(group_players[display_columns].head(5).to_string(index=False))


def apply_recommender_model(project_root: Path, db_url: str, paths: dict[str, Path]) -> pd.DataFrame:
    """Apply live recommender models and write predictions to transformed players."""
    current_season = read_runtime_season(paths["runtime_path"])
    engine = create_engine(db_url)

    try:
        player_stats, matches, players = load_live_tables(paths, engine)
        prediction_dataset = build_prediction_dataset(
            player_stats,
            matches,
            players,
            current_season,
        )

        print(f"[INFO] Current recommender season: {current_season}")
        print(f"[INFO] Recommender prediction candidates: {len(prediction_dataset)}")

        league_differences = calculate_league_differences(player_stats, matches, players)
        print_league_differences(league_differences)

        predictions = predict_current_season_players(
            prediction_dataset,
            paths["model_dir"],
            league_differences,
        )
        updated_players = update_players_with_predictions(players, predictions)
        save_players(updated_players, paths["players_path"])
        print_top_predictions(players, predictions)
        return updated_players
    finally:
        engine.dispose()


def main() -> None:
    """Run live recommender model inference."""
    arguments = parse_arguments()
    paths = resolve_project_paths(arguments)
    apply_recommender_model(
        project_root=paths["project_root"],
        db_url=arguments.db_url,
        paths=paths,
    )


if __name__ == "__main__":
    main()
