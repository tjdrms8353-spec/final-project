import importlib.util
import sys
import types
from datetime import timedelta
from pathlib import Path

import pytest

from pipelines.jobs.airflow_rss import (
    SCHEDULES, CollectionFailed, CollectionSkipped, run_feed, validate_schedules,
)


def run(result, feed='bbc-tech'):
    calls = []
    def execute(engine, **options):
        calls.append((engine, options))
        return result
    return run_feed(feed, engine_factory=lambda: 'engine', execute=execute), calls


def test_success_returns_history_result():
    result, calls = run({'status': 'success', 'inserted_count': 5})
    assert result['inserted_count'] == 5
    assert calls == [('engine', {'feed': 'bbc-tech', 'limit': 100, 'timeout': 20})]


def test_busy_is_skipped():
    with pytest.raises(CollectionSkipped):
        run({'status': 'failed', 'error_code': 'collection_busy', 'storage': 'not_started'})


@pytest.mark.parametrize('status', ['failed', 'partial'])
def test_failed_or_unstored_batch_fails_task(status):
    with pytest.raises(CollectionFailed) as error:
        run({'status': status, 'error_code': 'http_status'})
    assert error.value.result['status'] == status


def test_invalid_feed_never_opens_database():
    with pytest.raises(ValueError):
        run_feed('unknown', engine_factory=lambda: pytest.fail('DB must not open'))


@pytest.mark.parametrize('schedules', [{}, {'unknown': 30}, {'bbc-tech': 4}, {'bbc-tech': 30.0}])
def test_invalid_schedules(schedules):
    with pytest.raises(ValueError):
        validate_schedules(schedules)


def test_default_schedules_are_valid():
    validate_schedules(SCHEDULES)
    from app.features.trends.collectors.rss import SECTION_FEEDS
    from pipelines.jobs.airflow_rss import KOREAN_FEEDS
    assert SCHEDULES['bbc-tech'] == 15
    assert all(SCHEDULES[feed] == 5 for feed in KOREAN_FEEDS)
    assert all(SCHEDULES[feed] == 30 for feed in SECTION_FEEDS)
    assert len(SECTION_FEEDS) == 41 and SCHEDULES['hankyung-it'] == 30


def test_dag_file_structure(monkeypatch):
    """Airflow cannot run on Windows; check the DAG file against a minimal stub."""
    dags = []

    class DAG:
        def __init__(self, **kwargs):
            self.kwargs, self.tasks = kwargs, []
        def __enter__(self):
            dags.append(self)
            return self
        def __exit__(self, *exc):
            return False

    def task(task_id):
        def decorator(func):
            def call():
                dags[-1].tasks.append((task_id, func))
            return call
        return decorator

    class Skip(Exception):
        pass

    sdk = types.ModuleType('airflow.sdk')
    sdk.DAG, sdk.task = DAG, task
    exceptions = types.ModuleType('airflow.exceptions')
    exceptions.AirflowSkipException = Skip
    monkeypatch.setitem(sys.modules, 'airflow', types.ModuleType('airflow'))
    monkeypatch.setitem(sys.modules, 'airflow.sdk', sdk)
    monkeypatch.setitem(sys.modules, 'airflow.exceptions', exceptions)

    path = Path(__file__).resolve().parents[1] / 'dags' / 'news_rss_collection.py'
    spec = importlib.util.spec_from_file_location('news_rss_collection', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    expected = {f"news_rss_{feed.replace('-', '_')}": minutes for feed, minutes in SCHEDULES.items()}
    assert {dag.kwargs['dag_id'] for dag in dags} == set(expected)
    for dag in dags:
        assert dag.kwargs['schedule'] == timedelta(minutes=expected[dag.kwargs['dag_id']])
        assert dag.kwargs['catchup'] is False
        assert dag.kwargs['max_active_runs'] == 1
        assert dag.kwargs['default_args']['retries'] == 0
        assert [task_id for task_id, _ in dag.tasks] == ['collect_and_store']

    monkeypatch.setattr(module, 'run_feed', lambda feed: (_ for _ in ()).throw(CollectionSkipped(feed)))
    with pytest.raises(Skip):
        dags[0].tasks[0][1]()
