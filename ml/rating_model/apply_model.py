from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

try:
    from ml.toolkit.ml_utilities import load_model
except ImportError:
    from toolkit.ml_utilities import load_model


DEFAULT_DB_URL = "postgresql+psycopg2://postgres:postgres@host.docker.internal:5434/iamscout"
DEFAULT_PLAYER_STATS_PATH = Path("data/transform/player_stats.csv")
DEFAULT_PLAYERS_PATH = Path("data/transform/players.csv")
DEFAULT_MATCHES_PATH = Path("data/transform/matches.csv")
DEFAULT_MODEL_PATH = Path("ml/rating_model/rating_model.pkl")
RATING_COLUMN = "rating"

PLAYER_METADATA_COLUMNS = [
    "player_id",
    "player_name",
    "position",
]

MATCH_METADATA_COLUMNS = [
    "match_id",
    "home_club_id",
    "away_club_id",
    "home_goals",
    "away_goals",
]

NUMERIC_COLUMNS = [
    "goals",
    "assists",
    "minutes",
    "on_min",
    "off_min",
    "team_goals",
    "team_conceded",
]

BOOLEAN_COLUMNS = [
    "yellow",
    "yellow_red",
    "red",
    "start_eleven",
]

CATEGORICAL_COLUMNS = [
    "position",
    "result",
]

FEATURE_COLUMNS = NUMERIC_COLUMNS + BOOLEAN_COLUMNS + CATEGORICAL_COLUMNS
IDENTIFIER_COLUMNS = [
    "player_id",
    "match_id",
    "club_id",
    "home_club_id",
    "away_club_id",
]

TRUE_VALUES = {"1", "true", "yes", "y", "t"}
FALSE_VALUES = {"0", "false", "no", "n", "f", ""}


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments for the live rating prediction step."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--db-url",
        default=os.environ.get("IAMSCOUT_DB_URL", DEFAULT_DB_URL),
    )
    parser.add_argument("--player-stats-path", type=Path, default=DEFAULT_PLAYER_STATS_PATH)
    parser.add_argument("--players-path", type=Path, default=DEFAULT_PLAYERS_PATH)
    parser.add_argument("--matches-path", type=Path, default=DEFAULT_MATCHES_PATH)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    return parser.parse_args()


def resolve_project_path(project_root: Path, input_path: Path) -> Path:
    """Resolve a path relative to the project root when it is not absolute."""
    if input_path.is_absolute():
        return input_path

    return project_root / input_path


def validate_columns(dataframe: pd.DataFrame, required_columns: Iterable[str]) -> None:
    """Raise an error when required columns are missing from a dataframe."""
    missing_columns = sorted(set(required_columns) - set(dataframe.columns))

    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")


def read_csv_if_exists(input_path: Path, required_columns: Iterable[str]) -> pd.DataFrame:
    """Read a CSV file when it exists and validate required columns."""
    if not input_path.exists():
        return pd.DataFrame(columns=list(required_columns))

    dataframe = pd.read_csv(input_path)

    if dataframe.empty:
        return pd.DataFrame(columns=list(dataframe.columns))

    validate_columns(dataframe, required_columns)
    return dataframe


def normalize_identifier_columns(
    dataframe: pd.DataFrame,
    columns: Iterable[str],
) -> pd.DataFrame:
    """Normalize identifier columns to stripped strings."""
    result = dataframe.copy()

    for column in columns:
        if column in result.columns:
            result[column] = result[column].astype("string").str.strip()

    return result


def read_database_table(engine: Engine, query: str) -> pd.DataFrame:
    """Read a database query into a dataframe."""
    try:
        return pd.read_sql_query(text(query), engine)
    except Exception as error:
        raise RuntimeError(f"Could not read database query: {query}") from error


def load_database_players(engine: Engine) -> pd.DataFrame:
    """Load player metadata from the database."""
    query = """
        SELECT player_id, player_name, position
        FROM players
    """
    return read_database_table(engine, query)


def load_database_matches(engine: Engine) -> pd.DataFrame:
    """Load match metadata from the database."""
    query = """
        SELECT match_id, home_club_id, away_club_id, home_goals, away_goals
        FROM matches
    """
    return read_database_table(engine, query)


def combine_metadata(
    transformed_metadata: pd.DataFrame,
    database_metadata: pd.DataFrame,
    subset_columns: list[str],
    unique_column: str,
) -> pd.DataFrame:
    """Combine transformed and database metadata while preferring transformed rows."""
    transformed_metadata = transformed_metadata.reindex(columns=subset_columns)
    database_metadata = database_metadata.reindex(columns=subset_columns)

    metadata = pd.concat(
        [transformed_metadata, database_metadata],
        ignore_index=True,
    )
    metadata = normalize_identifier_columns(metadata, IDENTIFIER_COLUMNS)
    metadata = metadata.dropna(subset=[unique_column])
    metadata = metadata.drop_duplicates(subset=[unique_column], keep="first")

    return metadata


def load_player_metadata(
    players_path: Path,
    engine: Engine,
) -> pd.DataFrame:
    """Load player metadata from transformed players and the database."""
    transformed_players = read_csv_if_exists(players_path, PLAYER_METADATA_COLUMNS)
    database_players = load_database_players(engine)

    return combine_metadata(
        transformed_metadata=transformed_players,
        database_metadata=database_players,
        subset_columns=PLAYER_METADATA_COLUMNS,
        unique_column="player_id",
    )


def load_match_metadata(
    matches_path: Path,
    engine: Engine,
) -> pd.DataFrame:
    """Load match metadata from transformed matches and the database."""
    transformed_matches = read_csv_if_exists(matches_path, MATCH_METADATA_COLUMNS)
    database_matches = load_database_matches(engine)

    return combine_metadata(
        transformed_metadata=transformed_matches,
        database_metadata=database_matches,
        subset_columns=MATCH_METADATA_COLUMNS,
        unique_column="match_id",
    )


def merge_position_metadata(
    player_stats: pd.DataFrame,
    players: pd.DataFrame,
) -> pd.DataFrame:
    """Merge player positions into player statistics."""
    result = player_stats.merge(
        players[["player_id", "position"]],
        on="player_id",
        how="left",
        suffixes=("", "_metadata"),
    )

    if "position_metadata" in result.columns:
        if "position" in result.columns:
            result["position"] = result["position"].combine_first(result["position_metadata"])
        else:
            result["position"] = result["position_metadata"]
        result = result.drop(columns=["position_metadata"])

    return result


def merge_match_metadata(
    player_stats: pd.DataFrame,
    matches: pd.DataFrame,
) -> pd.DataFrame:
    """Merge match context into player statistics."""
    result = player_stats.merge(
        matches,
        on="match_id",
        how="left",
        suffixes=("", "_metadata"),
    )

    for column in MATCH_METADATA_COLUMNS:
        metadata_column = f"{column}_metadata"
        if metadata_column in result.columns:
            result[column] = result[column].combine_first(result[metadata_column])
            result = result.drop(columns=[metadata_column])

    return result


def add_match_result(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Add the match result from the perspective of the player's club."""
    result = normalize_identifier_columns(dataframe, IDENTIFIER_COLUMNS)

    is_home_team = result["club_id"] == result["home_club_id"]
    is_away_team = result["club_id"] == result["away_club_id"]

    result["result"] = pd.NA
    result.loc[is_home_team & (result["home_goals"] > result["away_goals"]), "result"] = "win"
    result.loc[is_home_team & (result["home_goals"] < result["away_goals"]), "result"] = "loss"
    result.loc[is_home_team & (result["home_goals"] == result["away_goals"]), "result"] = "draw"
    result.loc[is_away_team & (result["away_goals"] > result["home_goals"]), "result"] = "win"
    result.loc[is_away_team & (result["away_goals"] < result["home_goals"]), "result"] = "loss"
    result.loc[is_away_team & (result["away_goals"] == result["home_goals"]), "result"] = "draw"

    return result


def add_team_context(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Add team goals and conceded goals when they are missing."""
    result = dataframe.copy()
    is_home_team = result["club_id"] == result["home_club_id"]
    is_away_team = result["club_id"] == result["away_club_id"]

    if "team_goals" not in result.columns:
        result["team_goals"] = pd.NA

    if "team_conceded" not in result.columns:
        result["team_conceded"] = pd.NA

    result.loc[is_home_team, "team_goals"] = result.loc[is_home_team, "home_goals"]
    result.loc[is_home_team, "team_conceded"] = result.loc[is_home_team, "away_goals"]
    result.loc[is_away_team, "team_goals"] = result.loc[is_away_team, "away_goals"]
    result.loc[is_away_team, "team_conceded"] = result.loc[is_away_team, "home_goals"]

    return result


def parse_boolean_series(series: pd.Series) -> pd.Series:
    """Convert common boolean representations to boolean values."""
    normalized = series.astype("string").str.strip().str.lower()
    parsed = pd.Series(pd.NA, index=series.index, dtype="boolean")
    parsed.loc[normalized.isin(TRUE_VALUES)] = True
    parsed.loc[normalized.isin(FALSE_VALUES)] = False
    return parsed.fillna(False)


def prepare_feature_values(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Prepare model feature values with stable data types."""
    result = dataframe.copy()
    validate_columns(result, FEATURE_COLUMNS)

    for column in NUMERIC_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0)

    for column in BOOLEAN_COLUMNS:
        result[column] = parse_boolean_series(result[column])

    for column in CATEGORICAL_COLUMNS:
        result[column] = result[column].astype("string").str.strip()
        result[column] = result[column].replace({"": pd.NA, "nan": pd.NA, "<NA>": pd.NA})

    return result


def select_prediction_candidates(dataframe: pd.DataFrame) -> pd.Series:
    """Return a boolean mask for rows that have all categorical model inputs."""
    return dataframe[CATEGORICAL_COLUMNS].notna().all(axis=1)


def predict_ratings(dataframe: pd.DataFrame, model) -> pd.DataFrame:
    """Predict ratings for rows with complete model input data."""
    result = prepare_feature_values(dataframe)
    result[RATING_COLUMN] = pd.NA

    prediction_mask = select_prediction_candidates(result)
    prediction_count = int(prediction_mask.sum())
    missing_count = int((~prediction_mask).sum())

    print(f"[INFO] Rating prediction candidates: {prediction_count}")

    if missing_count:
        print(f"[WARN] Rating skipped for rows with missing position or result: {missing_count}")

    if prediction_count:
        predictions = model.predict(result.loc[prediction_mask, FEATURE_COLUMNS])
        result.loc[prediction_mask, RATING_COLUMN] = predictions.round(1)

    return result


def build_output_dataframe(
    predicted_stats: pd.DataFrame,
    original_columns: list[str],
) -> pd.DataFrame:
    """Build the final player statistics output dataframe."""
    output_columns = list(original_columns)

    if RATING_COLUMN not in output_columns:
        output_columns.append(RATING_COLUMN)

    return predicted_stats[output_columns]


def apply_rating_model(
    project_root: Path,
    player_stats_path: Path,
    players_path: Path,
    matches_path: Path,
    model_path: Path,
    db_url: str,
) -> pd.DataFrame:
    """Apply the rating model to transformed player statistics using database metadata."""
    player_stats_path = resolve_project_path(project_root, player_stats_path)
    players_path = resolve_project_path(project_root, players_path)
    matches_path = resolve_project_path(project_root, matches_path)
    model_path = resolve_project_path(project_root, model_path)

    if not player_stats_path.exists():
        print(f"[INFO] No player_stats file found, skipping ratings: {player_stats_path}")
        return pd.DataFrame()

    player_stats = pd.read_csv(player_stats_path)

    if player_stats.empty:
        print("[INFO] player_stats.csv is empty, skipping rating prediction")
        return player_stats

    validate_columns(player_stats, ["player_id", "match_id", "club_id"])
    player_stats = normalize_identifier_columns(player_stats, IDENTIFIER_COLUMNS)
    original_columns = list(player_stats.columns)

    if not model_path.exists():
        raise FileNotFoundError(f"Rating model not found: {model_path}")

    engine = create_engine(db_url)

    try:
        players = load_player_metadata(players_path, engine)
        matches = load_match_metadata(matches_path, engine)
    finally:
        engine.dispose()

    enriched_stats = merge_position_metadata(player_stats, players)
    enriched_stats = merge_match_metadata(enriched_stats, matches)
    enriched_stats = add_team_context(enriched_stats)
    enriched_stats = add_match_result(enriched_stats)

    model = load_model(model_path)
    predicted_stats = predict_ratings(enriched_stats, model)
    output_stats = build_output_dataframe(predicted_stats, original_columns)
    output_stats.to_csv(player_stats_path, index=False, encoding="utf-8-sig")

    predicted_count = int(output_stats[RATING_COLUMN].notna().sum())
    print(f"[INFO] Ratings written to: {player_stats_path}")
    print(f"[INFO] Ratings predicted: {predicted_count} of {len(output_stats)}")

    return output_stats


def main() -> None:
    """Run live rating prediction from command line arguments."""
    arguments = parse_arguments()
    project_root = arguments.project_root.resolve()

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    apply_rating_model(
        project_root=project_root,
        player_stats_path=arguments.player_stats_path,
        players_path=arguments.players_path,
        matches_path=arguments.matches_path,
        model_path=arguments.model_path,
        db_url=arguments.db_url,
    )


if __name__ == "__main__":
    main()
