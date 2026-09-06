from evidence_agent.state import Finding, SearchResultItem
from evidence_agent.synthesizer import _filter_valid_findings


def test_drops_finding_with_hallucinated_url():
    sources = {
        "https://real.example.com": SearchResultItem(
            title="Real", url="https://real.example.com", snippet="..."
        )
    }
    findings = [
        Finding(claim="A true claim", source_url="https://real.example.com"),
        Finding(claim="A fabricated claim", source_url="https://made-up.example.com"),
    ]

    kept = _filter_valid_findings(findings, sources)

    assert len(kept) == 1
    assert kept[0].claim == "A true claim"


def test_keeps_all_findings_when_all_urls_are_real():
    sources = {
        "https://a.example.com": SearchResultItem(title="A", url="https://a.example.com", snippet=""),
        "https://b.example.com": SearchResultItem(title="B", url="https://b.example.com", snippet=""),
    }
    findings = [
        Finding(claim="Claim A", source_url="https://a.example.com"),
        Finding(claim="Claim B", source_url="https://b.example.com"),
    ]

    assert _filter_valid_findings(findings, sources) == findings
