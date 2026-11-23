"""One DAG per RSS feed. Requires Airflow in a separate environment (pipelines/requirements.txt).

No catch-up and one active run per feed; the collector already retries transient
errors and defers long Retry-After waits, so Airflow task retries are disabled.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "backend"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

try:
    from airflow.sdk import DAG, task
except ImportError:  # Airflow 2.x
    from airflow import DAG
    from airflow.decorators import task
from airflow.exceptions import AirflowSkipException

from pipelines.jobs.airflow_rss import SCHEDULES, CollectionSkipped, run_feed, validate_schedules

validate_schedules(SCHEDULES)


def build_dag(feed, minutes):
    with DAG(
        dag_id=f"news_rss_{feed.replace('-', '_')}",
        schedule=timedelta(minutes=minutes),
        start_date=datetime(2026, 11, 19, tzinfo=timezone.utc),
        catchup=False,
        max_active_runs=1,
        default_args={"retries": 0},
        tags=["news", "rss"],
    ) as dag:
        @task(task_id="collect_and_store")
        def collect_and_store():
            try:
                return run_feed(feed)
            except CollectionSkipped:
                raise AirflowSkipException(f"{feed} collection already running") from None

        collect_and_store()
    return dag


for _feed, _minutes in SCHEDULES.items():
    globals()[f"news_rss_{_feed.replace('-', '_')}"] = build_dag(_feed, _minutes)
