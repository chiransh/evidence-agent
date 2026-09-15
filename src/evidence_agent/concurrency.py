"""Run independent network calls at the same time without changing what the
caller sees.

The searcher and the credibility node both make one call per sub-question, and
those calls do not depend on each other, so running them one after another only
adds latency. What must not change is everything else: results come back in the
order of the inputs, and a failure raises the same typed exception a plain loop
would, so the graph's retry policy still sees a TransientError and retries the
node.
"""

from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")

# Kept low on purpose. The upstream APIs rate-limit per key, and keyless Tavily
# limits aggressively, so more threads would mostly buy more rate-limit errors.
MAX_WORKERS = 4


def map_in_order(fn: Callable[[T], R], items: Iterable[T], max_workers: int = MAX_WORKERS) -> list[R]:
    items = list(items)
    if len(items) <= 1 or max_workers <= 1:
        return [fn(item) for item in items]

    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as pool:
        futures = [pool.submit(fn, item) for item in items]
        try:
            return [future.result() for future in futures]
        except BaseException:
            # Calls that have not started are dropped rather than sent, so one
            # failure does not spend the rest of the rate limit. Calls already in
            # flight finish before the pool closes.
            for future in futures:
                future.cancel()
            raise
