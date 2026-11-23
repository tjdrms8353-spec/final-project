import json
import pytest
from pipelines.jobs.schedule_rss import main, run_schedule


def test_independent_intervals_and_finite_runs():
    current = [0.0]
    calls = []
    def execute(engine, **options):
        calls.append((options['feed'], current[0]))
        return {'status': 'success'}
    def sleep(seconds):
        current[0] += seconds
    assert run_schedule(None, {'bbc-tech': 300, 'sbs-latest': 600}, cycles=2,
                        clock=lambda: current[0], sleep=sleep, execute=execute, emit=lambda _: None) == 0
    assert calls == [('bbc-tech', 0), ('sbs-latest', 0), ('bbc-tech', 300), ('sbs-latest', 600)]


def test_failure_does_not_stop_other_feed():
    calls = []
    def execute(engine, **options):
        calls.append(options['feed'])
        return {'status': 'failed' if len(calls) == 1 else 'success'}
    assert run_schedule(None, {'bbc-tech': 300, 'sbs-latest': 300}, execute=execute, emit=lambda _: None) == 1
    assert len(calls) == 2


def test_no_catchup_after_slow_collection():
    current, calls = [0], []
    def execute(engine, **options):
        calls.append(current[0])
        current[0] += 700
        return {'status': 'success'}
    def sleep(seconds):
        current[0] += seconds
    run_schedule(None, {'bbc-tech': 300}, cycles=2, clock=lambda: current[0],
                 sleep=sleep, execute=execute, emit=lambda _: None)
    assert calls == [0, 1000]


@pytest.mark.parametrize('feed', ['bbc-tech:0', 'bbc-tech:nan', 'unknown:600', 'bad'])
def test_invalid_config(feed):
    assert main(['--feed', feed]) == 2


def test_dry_run_no_database(monkeypatch, capsys):
    import pipelines.jobs.schedule_rss as scheduler
    monkeypatch.setattr(scheduler, 'get_engine', lambda: pytest.fail('DB must not open'))
    assert main(['--feed', 'bbc-tech:1800']) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'dry_run'
