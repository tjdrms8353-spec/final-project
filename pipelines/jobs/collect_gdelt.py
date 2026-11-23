"""GDELT collection and validation, without storage or scheduling.

Run from the project root with backend on PYTHONPATH:
    python -m pipelines.jobs.collect_gdelt --query "climate change"
Default: validate only, no network. --execute explicitly enables one request.
"""

import argparse
import json
from dataclasses import dataclass
from typing import Literal

import httpx

from app.features.trends.collectors.gdelt import (
    GdeltCollectionError, collect_news, validate_collection_options,
)
from app.features.trends.preprocessing.news import NewsBatch


@dataclass
class JobResult:
    status: Literal["dry_run", "success", "partial", "failed"]
    batch: NewsBatch | None = None
    error_code: str | None = None
    http_status: int | None = None

    def summary(self) -> dict[str, object]:
        """Counts only: omit article contents, request queries and raw errors."""
        return {
            "status": self.status,
            "input_count": self.batch.input_count if self.batch is not None else None,
            "accepted_count": len(self.batch.items) if self.batch is not None else None,
            "rejected_count": len(self.batch.rejected) if self.batch is not None else None,
            "duplicate_count": self.batch.duplicate_count if self.batch is not None else None,
            "error_code": self.error_code,
            "http_status": self.http_status,
        }


def run_job(
    query: str,
    *,
    timespan: str = "1h",
    max_records: int = 50,
    timeout: float = 15.0,
    execute: bool = False,
    client: httpx.Client | None = None,
) -> JobResult:
    """Validate before execution. All results stay in memory, with no DB writes.

    Invalid options raise ValueError; known upstream failures return failed.
    Unexpected programming errors propagate rather than being hidden.
    """
    if type(execute) is not bool:
        raise ValueError("execute must be a boolean")
    validate_collection_options(
        query, timespan=timespan, max_records=max_records, timeout=timeout,
    )
    if not execute:
        return JobResult(status="dry_run")
    try:
        batch = collect_news(
            query, timespan=timespan, max_records=max_records,
            timeout=timeout, client=client,
        )
    except GdeltCollectionError as exc:
        return JobResult(status="failed", error_code=exc.code, http_status=exc.status_code)
    if batch.rejected and not batch.items:
        return JobResult(status="failed", batch=batch, error_code="no_valid_articles")
    return JobResult(status="partial" if batch.rejected else "success", batch=batch)


def main(argv: list[str] | None = None, *, client: httpx.Client | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--timespan", default="1h")
    parser.add_argument("--max-records", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--execute", action="store_true", help="Enable one external request")
    args = parser.parse_args(argv)
    try:
        result = run_job(
            args.query, timespan=args.timespan, max_records=args.max_records,
            timeout=args.timeout, execute=args.execute, client=client,
        )
    except ValueError:
        # Do not echo invalid user-provided options.
        print(json.dumps({"status": "failed", "error_code": "invalid_options"}))
        return 2
    print(json.dumps(result.summary()))
    # Partial batches require attention rather than silently reporting success.
    return 1 if result.status in ("partial", "failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
