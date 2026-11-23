"""From project root with backend on PYTHONPATH; --execute enables one RSS request."""

import argparse
import json

from app.features.trends.collectors.rss import FEEDS, collect_rss, validate_options, RssCollectionError
from app.db.session import get_engine
from pipelines.jobs.rss_history import execute_stored


def main(argv=None, *, client=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feed", choices=tuple(FEEDS), default="bbc-tech")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--store", action="store_true", help="Store a fully valid batch; requires --execute and an existing news table")
    args = parser.parse_args(argv)
    try:
        validate_options(args.limit, args.timeout)
        if args.store and not args.execute:
            raise ValueError("--store requires --execute")
        if not args.execute:
            print(json.dumps({"status": "dry_run", "source": FEEDS[args.feed][1], "limit": args.limit}))
            return 0
        if args.store:
            try:
                engine = get_engine()
            except (RuntimeError, ValueError, OSError):
                print(json.dumps({"status": "failed", "error_code": "database_configuration"}))
                return 2
            result = execute_stored(engine, feed=args.feed, limit=args.limit, timeout=args.timeout, client=client)
            print(json.dumps(result))
            return 0 if result["status"] == "success" else 1
        batch = collect_rss(limit=args.limit, timeout=args.timeout, client=client, feed=args.feed)
    except ValueError:
        print(json.dumps({"status": "failed", "error_code": "invalid_options"}))
        return 2
    except RssCollectionError as exc:
        print(json.dumps({"status": "failed", "error_code": exc.code, "http_status": exc.status_code}))
        return 1
    status = "partial" if batch.rejected else "success"
    if batch.rejected and not batch.items:
        status = "failed"
    storage = "not_requested"
    print(json.dumps({
        "status": status, "source": FEEDS[args.feed][1], "input_count": batch.input_count,
        "accepted_count": len(batch.items), "rejected_count": len(batch.rejected),
        "duplicate_count": batch.duplicate_count,
        "storage": storage,
    }))
    return 0 if status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
