"""Translate foreign news (BBC) into Korean every 15 minutes with DeepL.

Skipped while DEEPL_API_KEY is empty. No catch-up, one active run, no task retries:
quota (456) and rate limits (429) are retried by the next scheduled run.
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

from pipelines.jobs.translate_news import TranslationSkipped, run_scheduled

with DAG(
    dag_id="news_translate_ko",
    schedule=timedelta(minutes=15),
    start_date=datetime(2026, 11, 23, tzinfo=timezone.utc),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 0},
    tags=["news", "translation"],
) as news_translate_ko:
    @task(task_id="translate_pending")
    def translate_pending():
        try:
            return run_scheduled()
        except TranslationSkipped as exc:
            raise AirflowSkipException(f"translation skipped: {exc}") from None

    translate_pending()
