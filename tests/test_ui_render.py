from evidence_agent.state import Finding, SearchResultItem
from evidence_agent.ui.render import citation_numbers, run_summary, source_rows


def _item(url: str, score: float | None = None, title: str = "T") -> SearchResultItem:
    return SearchResultItem(title=title, url=url, snippet="s", credibility_score=score)


def test_a_source_shared_by_two_sub_questions_is_listed_once():
    results = {
        "sq1": [_item("https://a", 0.8)],
        "sq2": [_item("https://a", 0.8), _item("https://b", 0.5)],
    }
    rows = source_rows(results)

    urls = [row["url"] for row in rows]
    assert urls.count("https://a") == 1
    shared = next(row for row in rows if row["url"] == "https://a")
    assert shared["sub_questions"] == ["sq1", "sq2"]


def test_rows_are_ordered_by_credibility():
    results = {"sq": [_item("https://low", 0.2), _item("https://high", 0.9)]}
    assert [row["url"] for row in source_rows(results)] == ["https://high", "https://low"]


def test_best_score_wins_when_a_url_is_scored_more_than_once():
    results = {"sq1": [_item("https://a", 0.3)], "sq2": [_item("https://a", 0.7)]}
    assert source_rows(results)[0]["credibility"] == 0.7


def test_unscored_sources_sort_after_scored_ones():
    results = {"sq": [_item("https://unscored"), _item("https://scored", 0.1)]}
    assert [row["url"] for row in source_rows(results)] == [
        "https://scored",
        "https://unscored",
    ]


def test_unscored_sources_do_not_crash_the_ordering():
    results = {"sq": [_item("https://a"), _item("https://b")]}
    rows = source_rows(results)
    assert len(rows) == 2
    assert all(row["credibility"] is None for row in rows)


def test_citation_numbers_match_first_appearance_order():
    findings = [
        Finding(claim="c1", source_url="https://b"),
        Finding(claim="c2", source_url="https://a"),
        Finding(claim="c3", source_url="https://b"),
    ]
    assert citation_numbers(findings) == {"https://b": 1, "https://a": 2}


def test_summary_separates_sources_retrieved_from_sources_cited():
    """The gap between the two is the number worth seeing: it says how much of
    what the agent read it actually used."""
    result = {
        "report": "one two three",
        "sub_questions": ["sq1", "sq2"],
        "search_results": {
            "sq1": [_item("https://a"), _item("https://b")],
            "sq2": [_item("https://c")],
        },
        "findings": [Finding(claim="c", source_url="https://a")],
    }
    summary = run_summary(result)

    assert summary["sources_retrieved"] == 3
    assert summary["sources_cited"] == 1
    assert summary["sub_questions"] == 2
    assert summary["findings"] == 1
    assert summary["words"] == 3


def test_summary_handles_an_empty_result():
    summary = run_summary({})
    assert summary == {
        "sub_questions": 0,
        "sources_retrieved": 0,
        "sources_cited": 0,
        "findings": 0,
        "words": 0,
    }
