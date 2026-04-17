from __future__ import annotations

import os
import subprocess
from datetime import timedelta

import pendulum
from airflow.sdk import dag, task

from web_scraping.toolkit.live_t_l import main as run_live_tl


DEFAULT_ARGS = {
    "owner": "cedric",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}


def _run_in_scraping_env(python_code: str) -> None:
    host_project_root = os.environ.get("HOST_PROJECT_ROOT")
    if not host_project_root:
        raise RuntimeError(
            "HOST_PROJECT_ROOT is not set. Start the Airflow container with "
            "-e HOST_PROJECT_ROOT=\"$PWD\"."
        )

    cmd = [
        "docker",
        "run",
        "--rm",
        "-e",
        "PYTHONPATH=/workspace",
        "-v",
        f"{host_project_root}:/workspace",
        "-w",
        "/workspace",
        "scraping-env:latest",
        "python",
        "-c",
        python_code,
    ]

    print("[INFO] Running scraping job in scraping-env ...")
    print("[INFO] Command:", " ".join(cmd[:-1] + ["<python_code>"]))

    subprocess.run(cmd, check=True)


@dag(
    dag_id="live_weekly",
    start_date=pendulum.datetime(2026, 1, 1, tz="Europe/Zurich"),
    schedule="0 0 * * 1",
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["live", "weekly"],
)
def live_weekly_dag():
    @task()
    def weekly_task():
        _run_in_scraping_env(
            "from web_scraping.live.weekly import run_weekly; run_weekly()"
        )

    @task()
    def transform_and_load_task():
        run_live_tl()

    weekly = weekly_task()
    transform_and_load = transform_and_load_task()

    weekly >> transform_and_load


@dag(
    dag_id="live_yearly",
    start_date=pendulum.datetime(2026, 1, 1, tz="Europe/Zurich"),
    schedule="0 0 1 8 *",
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["live", "yearly"],
)
def live_yearly_dag():
    @task()
    def yearly_task():
        _run_in_scraping_env(
            "from web_scraping.live.yearly import run_yearly; run_yearly()"
        )

    @task()
    def transform_and_load_task():
        run_live_tl()

    yearly = yearly_task()
    transform_and_load = transform_and_load_task()

    yearly >> transform_and_load


live_weekly_dag()
live_yearly_dag()