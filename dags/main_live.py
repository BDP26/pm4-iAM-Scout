from __future__ import annotations

import os
import subprocess
from datetime import timedelta
from pathlib import Path

import pandas as pd
import pendulum
from airflow.sdk import dag, task

from web_scraping.toolkit.live_t_l import main as run_live_tl


AIRFLOW_PROJECT_ROOT = Path("/opt/airflow/project")
SCRAPE_PLAYER_STATS_PATH = AIRFLOW_PROJECT_ROOT / "data" / "scrape" / "amateur" / "player_stats.csv"
SCRAPING_IMAGE_NAME = "scraping-env:latest"
DEFAULT_ARGS = {
    "owner": "cedric",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}


def _get_host_project_root() -> str:
    """Return the host project root configured for Docker volume mounting."""
    host_project_root = os.environ.get("HOST_PROJECT_ROOT")

    if not host_project_root:
        raise RuntimeError(
            "HOST_PROJECT_ROOT is not set. Start the Airflow container with "
            "-e HOST_PROJECT_ROOT=\"$PWD\"."
        )

    return host_project_root


def _run_in_scraping_env(python_code: str) -> None:
    """Run Python code in the scraping Docker image."""
    host_project_root = _get_host_project_root()
    command = [
        "docker",
        "run",
        "--rm",
        "-e",
        "PYTHONPATH=/workspace",
        "-v",
        f"{host_project_root}:/workspace",
        "-w",
        "/workspace",
        SCRAPING_IMAGE_NAME,
        "python",
        "-c",
        python_code,
    ]

    print("[INFO] Running scraping job in scraping-env")
    print("[INFO] Command:", " ".join(command[:-1] + ["<python_code>"]))
    subprocess.run(command, check=True)


def _log_csv_overview(csv_path: Path) -> None:
    """Print a compact overview of a CSV file when it exists."""
    print(f"[CHECK] player_stats path: {csv_path}")
    print(f"[CHECK] exists: {csv_path.exists()}")

    if not csv_path.exists():
        return

    dataframe = pd.read_csv(csv_path)
    print(f"[CHECK] rows: {len(dataframe)}")
    print(f"[CHECK] cols: {list(dataframe.columns)}")

    if not dataframe.empty:
        print(dataframe.head(5).to_string())


@dag(
    dag_id="live_weekly",
    start_date=pendulum.datetime(2026, 1, 1, tz="Europe/Zurich"),
    schedule="0 0 * * 1",
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["live", "weekly"],
)
def live_weekly_dag():
    """Define the weekly live DAG for scraping, transforming, rating, and loading."""

    @task()
    def weekly_task() -> None:
        """Run the weekly scraping task."""
        _run_in_scraping_env(
            "from web_scraping.live.weekly import run_weekly; run_weekly()"
        )

    @task()
    def transform_rating_and_load_task() -> None:
        """Run transform, rating prediction, and database load."""
        _log_csv_overview(SCRAPE_PLAYER_STATS_PATH)
        run_live_tl()

    weekly = weekly_task()
    transform_rating_and_load = transform_rating_and_load_task()

    weekly >> transform_rating_and_load


@dag(
    dag_id="live_yearly",
    start_date=pendulum.datetime(2026, 1, 1, tz="Europe/Zurich"),
    schedule="0 0 1 8 *",
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["live", "yearly"],
)
def live_yearly_dag():
    """Define the yearly live DAG for scraping, transforming, rating, and loading."""

    @task()
    def yearly_task() -> None:
        """Run the yearly scraping task."""
        _run_in_scraping_env(
            "from web_scraping.live.yearly import run_yearly; run_yearly()"
        )

    @task()
    def transform_rating_and_load_task() -> None:
        """Run transform, rating prediction, and database load."""
        run_live_tl()

    yearly = yearly_task()
    transform_rating_and_load = transform_rating_and_load_task()

    yearly >> transform_rating_and_load


live_weekly_dag()
live_yearly_dag()
