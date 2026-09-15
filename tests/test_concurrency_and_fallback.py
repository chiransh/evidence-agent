"""Concurrency is asserted with a barrier rather than with timings. Every call
waits at a threading.Barrier sized to the number of calls, which only releases
once all of them are in flight at the same time. Run sequentially, the first
call waits alone and the barrier times out, so these tests cannot pass by being
fast on a quiet machine or fail by being slow on a busy one."""

import threading
import time

import pytest

from evidence_agent.concurrency import map_in_order
from evidence_agent.credibility import credibility_node
from evidence_agent.exceptions import ConfigurationError, SearchError, TransientError
from evidence_agent.search import (
    FallbackSearchBackend,
    SearchResult,
    TavilySearchBackend,
    _clean,
)
from evidence_agent.searcher import searcher_node
from evidence_agent.state import ResearchState, SearchResultItem

BARRIER_TIMEOUT = 5


# map_in_order ------------------------------------------------------------------


def test_calls_overlap_rather_than_running_one_after_another():
    barrier = threading.Barrier(3, timeout=BARRIER_TIMEOUT)

    def call(x):
        barrier.wait()  # raises BrokenBarrierError if the calls do not overlap
        return x * 2

    assert map_in_order(call, [1, 2, 3], max_workers=3) == [2, 4, 6]


def test_results_keep_input_order_even_when_completion_order_differs():
    def call(x):
        time.sleep(0.05 * (4 - x))  # the first input finishes last
        return x

    assert map_in_order(call, [1, 2, 3, 4], max_workers=4) == [1, 2, 3, 4]


def test_failure_raises_the_same_typed_exception_a_loop_would():
    """The graph's retry policy keys on TransientError, so the concurrent path
    must not wrap it in something else."""

    def call(x):
        if x == 2:
            raise TransientError("rate limited")
        return x

    with pytest.raises(TransientError, match="rate limited"):
        map_in_order(call, [1, 2, 3], max_workers=3)


def test_never_exceeds_max_workers():
    lock = threading.Lock()
    in_flight = {"now": 0, "peak": 0}

    def call(x):
        with lock:
            in_flight["now"] += 1
            in_flight["peak"] = max(in_flight["peak"], in_flight["now"])
        time.sleep(0.05)
        with lock:
            in_flight["now"] -= 1
        return x

    map_in_order(call, range(10), max_workers=3)
    assert in_flight["peak"] <= 3


def test_single_item_and_single_worker_run_inline():
    caller = threading.get_ident()
    assert map_in_order(lambda _: threading.get_ident(), [1]) == [caller]
    assert map_in_order(lambda _: threading.get_ident(), [1, 2], max_workers=1) == [caller, caller]


# searcher and credibility nodes ------------------------------------------------


class _BarrierBackend:
    def __init__(self, n):
        self.barrier = threading.Barrier(n, timeout=BARRIER_TIMEOUT)

    def search(self, query, max_results=5):
        self.barrier.wait()
        return [SearchResult(title=query, url=f"https://example.com/{query}", snippet="s", backend="fake")]


def test_searcher_runs_sub_questions_concurrently_and_keeps_planner_order():
    state = ResearchState(question="q", sub_questions=["a", "b", "c"])
    out = searcher_node(state, backend=_BarrierBackend(3))

    assert list(out["search_results"]) == ["a", "b", "c"]
    assert out["search_results"]["b"][0].url == "https://example.com/b"


def test_searcher_records_which_backend_each_result_came_from():
    state = ResearchState(question="q", sub_questions=["a"])
    out = searcher_node(state, backend=_BarrierBackend(1))
    assert out["search_results"]["a"][0].backend == "fake"


def test_credibility_judges_sub_questions_concurrently():
    barrier = threading.Barrier(3, timeout=BARRIER_TIMEOUT)

    def relevance_fn(sub_question, results):
        barrier.wait()
        return {r.url: 0.9 for r in results}

    item = lambda sq: [SearchResultItem(title="t", url=f"https://example.com/{sq}", snippet="s")]
    state = ResearchState(
        question="q",
        sub_questions=["a", "b", "c"],
        search_results={sq: item(sq) for sq in ("a", "b", "c")},
    )

    out = credibility_node(state, relevance_fn=relevance_fn)
    assert list(out["search_results"]) == ["a", "b", "c"]
    assert all(r[0].credibility_score is not None for r in out["search_results"].values())


# Fallback ----------------------------------------------------------------------


class _Scripted:
    def __init__(self, name, outcome):
        self.name, self.outcome, self.calls = name, outcome, 0

    def search(self, query, max_results=5):
        self.calls += 1
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def _result(backend):
    return [SearchResult(title="t", url="https://example.com", snippet="s", backend=backend)]


@pytest.mark.parametrize(
    "failure", [TransientError("rate limited"), SearchError("bad response")], ids=["transient", "search_error"]
)
def test_primary_failure_falls_back(failure):
    primary, fallback = _Scripted("p", failure), _Scripted("f", _result("wikipedia"))
    results = FallbackSearchBackend(primary, fallback).search("q")

    assert results[0].backend == "wikipedia"
    assert fallback.calls == 1


def test_empty_primary_result_falls_back():
    primary, fallback = _Scripted("p", []), _Scripted("f", _result("wikipedia"))
    assert FallbackSearchBackend(primary, fallback).search("q")[0].backend == "wikipedia"


def test_a_bad_key_is_surfaced_not_papered_over_with_the_fallback():
    """Quietly serving Wikipedia on every query would hide the misconfiguration
    and degrade every report without anyone noticing."""
    primary, fallback = _Scripted("p", ConfigurationError("bad key")), _Scripted("f", _result("wikipedia"))

    with pytest.raises(ConfigurationError):
        FallbackSearchBackend(primary, fallback).search("q")
    assert fallback.calls == 0


def test_healthy_primary_never_touches_the_fallback():
    primary, fallback = _Scripted("p", _result("tavily")), _Scripted("f", _result("wikipedia"))
    assert FallbackSearchBackend(primary, fallback).search("q")[0].backend == "tavily"
    assert fallback.calls == 0


def test_a_failing_fallback_raises_its_own_error():
    primary = _Scripted("p", TransientError("rate limited"))
    fallback = _Scripted("f", TransientError("wikipedia down"))

    with pytest.raises(TransientError, match="wikipedia down"):
        FallbackSearchBackend(primary, fallback).search("q")


# Tavily client per thread ------------------------------------------------------


def test_each_thread_gets_its_own_tavily_client():
    """TavilyClient holds one requests.Session, which requests does not promise
    is safe to share across threads."""
    backend = TavilySearchBackend()
    seen = {}

    def grab(key):
        seen[key] = (backend._client(), backend._client())

    threads = [threading.Thread(target=grab, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert seen[0][0] is seen[0][1], "same thread should reuse its client"
    assert seen[0][0] is not seen[1][0], "different threads must not share a client"


def test_wikipedia_text_is_cleaned_of_markup_and_entities():
    assert _clean('<span class="searchmatch">Paris</span> &amp; the  Seine\n') == "Paris & the Seine"
