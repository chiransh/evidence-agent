from evidence_agent.state import Finding, ResearchState
from evidence_agent.writer import writer_node


def test_shared_source_gets_one_citation_number():
    state = ResearchState(
        question="Q",
        findings=[
            Finding(claim="Claim A", source_url="https://a.example.com"),
            Finding(claim="Claim B", source_url="https://a.example.com"),
        ],
    )
    report = writer_node(state)["report"]

    assert "Claim A [1]" in report
    assert "Claim B [1]" in report
    assert report.count("https://a.example.com") == 1  # listed once in Sources


def test_distinct_sources_get_sequential_numbers_in_order_of_appearance():
    state = ResearchState(
        question="Q",
        findings=[
            Finding(claim="Claim A", source_url="https://a.example.com"),
            Finding(claim="Claim B", source_url="https://b.example.com"),
        ],
    )
    report = writer_node(state)["report"]

    assert "Claim A [1]" in report
    assert "Claim B [2]" in report
    assert "[1] https://a.example.com" in report
    assert "[2] https://b.example.com" in report


def test_empty_findings_does_not_crash():
    state = ResearchState(question="Q")
    report = writer_node(state)["report"]

    assert "No findings." in report
    assert "No sources." in report
