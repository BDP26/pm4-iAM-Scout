from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


TEAMS_UNIQUE_FILENAME = "teams_unique.csv"
TEAMS_PER_SEASON_FILENAME = "teams_per_season.csv"
TEAMS_UNIQUE_WITH_LOCATIONS_FILENAME = "teams_unique_with_locations.csv"
SQUADS_FILENAME = "squads.csv"
PLAYERS_FILENAME = "players.csv"


def _default_output_dir() -> Path:
    return Path(__file__).resolve().parent


def _write_df_to_csv(
    df: pd.DataFrame,
    filename: str,
    output_dir: Optional[str | Path] = None,
    *,
    index: bool = False,
    encoding: str = "utf-8",
) -> Path:
    if df is None:
        raise ValueError("df must not be None")

    out_dir = Path(output_dir) if output_dir is not None else _default_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / filename
    df.to_csv(out_path, index=index, encoding=encoding)
    return out_path


def write_teams_unique(
    teams_unique_df: pd.DataFrame,
    output_dir: Optional[str | Path] = None,
) -> Path:

    return _write_df_to_csv(
        teams_unique_df,
        TEAMS_UNIQUE_FILENAME,
        output_dir=output_dir,
        index=False,
    )


def write_teams_per_season(
    teams_per_season_df: pd.DataFrame,
    output_dir: Optional[str | Path] = None,
) -> Path:

    return _write_df_to_csv(
        teams_per_season_df,
        TEAMS_PER_SEASON_FILENAME,
        output_dir=output_dir,
        index=False,
    )


def write_teams_unique_with_locations(
    teams_unique_with_locations_df: pd.DataFrame,
    output_dir: Optional[str | Path] = None,
) -> Path:

    return _write_df_to_csv(
        teams_unique_with_locations_df,
        TEAMS_UNIQUE_WITH_LOCATIONS_FILENAME,
        output_dir=output_dir,
        index=False,
    )


def write_roster_memberships(df: pd.DataFrame, output_dir: str | Path | None = None) -> Path:
    return _write_df_to_csv(df, SQUADS_FILENAME, output_dir=output_dir, index=False)


def write_players(df: pd.DataFrame, output_dir: str | Path | None = None) -> Path:
    return _write_df_to_csv(df, PLAYERS_FILENAME, output_dir=output_dir, index=False)


def write_matches(df, output_dir=None):
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    path = output_dir / "matches.csv"
    df.to_csv(path, index=False)
    return path


def write_player_stats(df, output_dir=None):
    from pathlib import Path
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "player_stats.csv"
    df.to_csv(path, index=False)
    return path