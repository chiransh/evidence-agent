import anthropic
from pydantic import BaseModel

from evidence_agent.state import Finding, ResearchState, SearchResultItem

MODEL = "claude-opus-5"


class Findings(BaseModel):
    findings: list[Finding]


def _filter_valid_findings(findings: list[Finding], sources: dict[str, SearchResultItem]) -> list[Finding]:
    """Drop any finding whose source_url wasn't actually in the search results
    the model was given, i.e. a hallucinated citation."""
    return [f for f in findings if f.source_url in sources]


def synthesizer_node(state: ResearchState) -> dict:
    sources: dict[str, SearchResultItem] = {}
    for results in state.search_results.values():
        for result in results:
            sources.setdefault(result.url, result)

    if not sources:
        return {"findings": []}

    source_list = "\n\n".join(f"{url}\n{r.title}\n{r.snippet}" for url, r in sources.items())

    client = anthropic.Anthropic()
    response = client.messages.parse(
        model=MODEL,
        max_tokens=8000,
        system=(
            "Extract the key findings that answer the research question from the search "
            "results below. Each finding is a single factual claim attributed to exactly "
            "one source_url, copied verbatim from the URLs in the search results. Never "
            "invent a URL that isn't listed."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Question: {state.question}\n\nSearch results:\n{source_list}",
            }
        ],
        output_format=Findings,
    )

    findings = _filter_valid_findings(response.parsed_output.findings, sources)
    return {"findings": findings}
