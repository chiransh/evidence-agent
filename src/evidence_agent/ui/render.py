"""Presentation helpers for the demo UI.

These are here rather than inline in the Streamlit script so they can be tested
without starting a server. Streamlit reruns its script top to bottom on every
interaction, which makes logic embedded in the page awkward to reason about and
impossible to test directly.
"""

from evidence_agent.state import Finding, SearchResultItem

SETUP_HELP = (
    "This demo needs credentials to run. Set ANTHROPIC_API_KEY in your environment "
    "(or run `ant auth login`) and restart. Web search works without a key at low "
    "rate limits; set TAVILY_API_KEY for anything beyond a few questions."
)


def source_rows(search_results: dict[str, list[SearchResultItem]]) -> list[dict]:
    """One row per unique source, with the sub-questions it was returned for.

    A source often answers more than one sub-question, and listing it once per
    sub-question makes a handful of sources look like a dozen.
    """
    rows: dict[str, dict] = {}

    for sub_question, results in search_results.items():
        for item in results:
            row = rows.setdefault(
                item.url,
                {
                    "url": item.url,
                    "title": item.title,
                    "credibility": item.credibility_score,
                    "sub_questions": [],
                },
            )
            if sub_question not in row["sub_questions"]:
                row["sub_questions"].append(sub_question)
            # Keep the highest score seen: the same URL can be scored once per
            # sub-question, and the relevant number is its best showing.
            if item.credibility_score is not None:
                existing = row["credibility"]
                row["credibility"] = (
                    item.credibility_score
                    if existing is None
                    else max(existing, item.credibility_score)
                )

    ordered = sorted(
        rows.values(),
        key=lambda row: (row["credibility"] is not None, row["credibility"] or 0.0),
        reverse=True,
    )
    return ordered


def citation_numbers(findings: list[Finding]) -> dict[str, int]:
    """Same numbering the written report uses, so the sources panel and the
    report agree on which source is [1]."""
    numbers: dict[str, int] = {}
    for finding in findings:
        if finding.source_url not in numbers:
            numbers[finding.source_url] = len(numbers) + 1
    return numbers


def run_summary(result: dict) -> dict:
    search_results = result.get("search_results", {})
    findings = result.get("findings", [])
    unique_sources = {item.url for results in search_results.values() for item in results}

    return {
        "sub_questions": len(result.get("sub_questions", [])),
        "sources_retrieved": len(unique_sources),
        "sources_cited": len({f.source_url for f in findings}),
        "findings": len(findings),
        "words": len(result.get("report", "").split()),
    }
