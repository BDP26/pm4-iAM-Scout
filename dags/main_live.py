from datetime import timedelta
import pendulum

from airflow.sdk import dag, task

from web_scraping.live.weekly import run_weekly
from web_scraping.live.yearly import run_yearly


DEFAULT_ARGS = {
    "owner": "cedric",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}


@dag(
    dag_id="live_weekly",
    start_date=pendulum.datetime(2026, 1, 1, tz="Europe/Zurich"),
    schedule="0 0 * * 1",   # jeden Montag um 00:00
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["live", "weekly"],
)
def live_weekly_dag():
    @task()
    def weekly_task():
        run_weekly()

    weekly_task()


@dag(
    dag_id="live_yearly",
    start_date=pendulum.datetime(2026, 1, 1, tz="Europe/Zurich"),
    schedule="0 0 1 8 *",   # jedes Jahr am 1. August um 00:00
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["live", "yearly"],
)
def live_yearly_dag():
    @task()
    def yearly_task():
        run_yearly()

    yearly_task()


live_weekly_dag()
live_yearly_dag()