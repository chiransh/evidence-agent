"""Live network checks for the page fetch, which decides both halves of citation
validity: whether the URL resolves, and what text the support judge grades a
claim against.

This is the one part of the harness that can be verified against reality without
a model call, so it is worth actually doing rather than mocking: a fetcher that
reported every URL as live would score a hallucinated citation as valid, and an
extractor that returned navigation chrome would have the judge grade claims
against a page's menu.

Marked `network` so the suite can be run offline with `pytest -m "not network"`.
"""

import pytest

from evidence_agent.evaluation.pages import (
    evidence_for,
    fetch_page,
    fetch_pages,
    passages,
    select_passages,
)

pytestmark = pytest.mark.network

PARIS = "https://en.wikipedia.org/wiki/Paris"


def _skip_if_offline(page):
    """An `unreachable` verdict here means this machine could not get out, which
    says nothing about whether the code works. Skip rather than fail, so a
    dropped connection does not look like a code defect. A wrong verdict on a
    request that did complete still fails."""
    if page.verdict == "unreachable":
        pytest.skip(f"no network access to {page.url}")


def test_real_page_reads_as_fetched():
    page = fetch_page(PARIS)
    _skip_if_offline(page)

    assert page.verdict == "fetched"
    assert page.status == 200
    assert page.usable


def test_missing_page_on_a_real_host_reads_as_dead():
    page = fetch_page("https://en.wikipedia.org/wiki/This_Page_Does_Not_Exist_Evidence_Agent_Test")
    _skip_if_offline(page)

    assert page.verdict == "dead"
    assert page.status == 404
    assert not page.usable


def test_unresolvable_host_reads_as_unreachable():
    page = fetch_page("https://this-host-does-not-exist-evidence-agent.invalid/page")

    assert page.verdict == "unreachable"
    assert page.status is None


def test_repeated_urls_are_only_fetched_once():
    assert len(fetch_pages([PARIS] * 3)) == 1


def test_extracted_text_is_prose_rather_than_markup_or_scripts():
    page = fetch_page(PARIS)
    _skip_if_offline(page)

    assert "<div" not in page.text and "</p>" not in page.text
    assert "function(" not in page.text
    assert "Paris" in page.text
    # A real article is thousands of words; a few hundred characters would mean
    # the extractor kept only the chrome.
    assert len(page.text) > 20_000


def test_passages_are_prose_paragraphs_not_navigation():
    page = fetch_page(PARIS)
    _skip_if_offline(page)

    found = passages(page.text)
    assert len(found) > 20
    assert all(len(p) >= 120 for p in found)


def test_selection_finds_the_part_of_the_page_that_carries_the_claim():
    """The point of the whole exercise: a claim whose evidence is nowhere near the
    top of the page still gets the right paragraph in front of the judge."""
    page = fetch_page(PARIS)
    _skip_if_offline(page)

    selected = select_passages("Paris is the capital and most populous city of France", page.text)
    assert selected
    text = " ".join(passage for _, passage in selected).lower()
    assert "france" in text
    assert "paris" in text


def test_page_evidence_is_longer_than_the_snippet_it_replaces():
    """If the page gave no more than the snippet there would be no reason to
    fetch it, so this is the assumption the change rests on."""
    page = fetch_page(PARIS)
    _skip_if_offline(page)

    snippet = "Paris is the capital of France."
    evidence = evidence_for("Paris is the capital of France", snippet, page)

    assert evidence.source == "page"
    assert len(evidence.text) > len(snippet) * 4
