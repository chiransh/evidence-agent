"""Live network checks for the URL half of citation validity.

This metric is the one part of the harness that can be verified against
reality without a model call, so it is worth actually doing rather than
mocking: a checker that reports every URL as live would score a hallucinated
citation as valid and nobody would notice.

Marked `network` so the suite can be run offline with
`pytest -m "not network"`.
"""

import pytest

from evidence_agent.evaluation.metrics import check_url, check_urls

pytestmark = pytest.mark.network


def test_real_page_reads_as_live():
    check = check_url("https://en.wikipedia.org/wiki/Paris")
    assert check.verdict == "live"
    assert check.status == 200


def test_missing_page_on_a_real_host_reads_as_dead():
    check = check_url("https://en.wikipedia.org/wiki/This_Page_Does_Not_Exist_Evidence_Agent_Test")
    assert check.verdict == "dead"
    assert check.status == 404


def test_unresolvable_host_reads_as_unreachable():
    check = check_url("https://this-host-does-not-exist-evidence-agent.invalid/page")
    assert check.verdict == "unreachable"
    assert check.status is None


def test_repeated_urls_are_only_fetched_once():
    urls = ["https://en.wikipedia.org/wiki/Paris"] * 3
    checked = check_urls(urls)
    assert len(checked) == 1
