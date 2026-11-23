"""Foreground local RSS scheduler. Restart resets its in-memory schedule."""
import argparse
import json
import math
import time

from app.db.session import get_engine
from app.features.trends.collectors.rss import FEEDS, validate_options
from pipelines.jobs.rss_history import execute_stored


def run_schedule(engine, intervals, *, cycles=1, limit=5, timeout=20,
                 clock=time.monotonic, sleep=time.sleep, execute=execute_stored,
                 emit=print):
    """Fixed delay after completion, no catch-up burst after slow jobs.

    cycles counts executions per feed; zero runs until Ctrl+C.
    """
    validate_options(limit, timeout)
    if type(cycles) is not int or cycles < 0:
        raise ValueError('cycles must be non-negative')
    if not intervals or any(feed not in FEEDS or not math.isfinite(seconds) or seconds < 300
                            for feed, seconds in intervals.items()):
        raise ValueError('Each registered feed requires an interval of at least 300 seconds')
    due = {feed: clock() for feed in intervals}
    counts = dict.fromkeys(intervals, 0)
    failed = False
    while due:
        feed = min(due, key=due.get)
        remaining = due[feed] - clock()
        if remaining > 0:
            sleep(min(remaining, 1))
            continue
        result = execute(engine, feed=feed, limit=limit, timeout=timeout)
        emit(json.dumps({'feed': feed, **result}))
        failed |= result['status'] != 'success'
        counts[feed] += 1
        if cycles and counts[feed] >= cycles:
            del due[feed]
        else:
            due[feed] = clock() + intervals[feed]
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--feed', action='append', required=True, metavar='NAME:SECONDS')
    parser.add_argument('--cycles', type=int, default=1, help='Executions per feed; 0 runs until Ctrl+C')
    parser.add_argument('--limit', type=int, default=5)
    parser.add_argument('--timeout', type=float, default=20)
    parser.add_argument('--execute', action='store_true', help='Enable network and database writes')
    args = parser.parse_args(argv)
    try:
        intervals = {}
        for value in args.feed:
            feed, seconds = value.rsplit(':', 1)
            if feed in intervals:
                raise ValueError('Duplicate feed')
            intervals[feed] = float(seconds)
        # Validate before opening the database, including dry run.
        validate_options(args.limit, args.timeout)
        if args.cycles < 0 or any(feed not in FEEDS or not math.isfinite(s) or s < 300 for feed, s in intervals.items()):
            raise ValueError('Invalid schedule')
        if not args.execute:
            print(json.dumps({'status': 'dry_run', 'intervals': intervals, 'cycles': args.cycles}))
            return 0
        return run_schedule(get_engine(), intervals, cycles=args.cycles,
                            limit=args.limit, timeout=args.timeout)
    except KeyboardInterrupt:
        print(json.dumps({'status': 'stopped'}))
        return 130
    except (ValueError, RuntimeError, OSError):
        print(json.dumps({'status': 'failed', 'error_code': 'schedule_configuration'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
