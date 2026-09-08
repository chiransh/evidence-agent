"""Credibility scoring: a domain reputation heuristic combined with an
LLM-judged relevance score. See notes/credibility.md for the design
rationale and known limitations."""

from typing import Callable
from urllib.parse import urlparse

import anthropic
from pydantic import BaseModel

from evidence_agent.state import ResearchState, SearchResultItem

MODEL = "claude-opus-5"

DOMAIN_REPUTATION: dict[str, float] = {
    "wikipedia.org": 0.75,
    "arxiv.org": 0.95,
    "nature.com": 0.95,
    "sciencedirect.com": 0.9,
    "nytimes.com": 0.85,
    "reuters.com": 0.9,
    "apnews.com": 0.85,
    "bbc.com": 0.85,
    "who.int": 0.9,
}
GOV_EDU_SCORE = 0.9
DEFAULT_DOMAIN_SCORE = 0.5

DOMAIN_WEIGHT = 0.4
RELEVANCE_WEIGHT = 0.6


def domain_score(url: str) -> float:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    for domain, score in DOMAIN_REPUTATION.items():
        if host == domain or host.endswith("." + domain):
            return score

    if host.endswith(".gov") or host.endswith(".edu"):
        return GOV_EDU_SCORE

    return DEFAULT_DOMAIN_SCORE


def combined_score(domain: float, relevance: float) -> float:
    return DOMAIN_WEIGHT * domain + RELEVANCE_WEIGHT * relevance


class RelevanceJudgment(BaseModel):
    url: str
    relevance: float


class RelevanceJudgments(BaseModel):
    judgments: list[RelevanceJudgment]


def judge_relevance(question: str, results: list[SearchResultItem]) -> dict[str, float]:
    if not results:
        return {}

    listing = "\n\n".join(f"{r.url}\n{r.title}\n{r.snippet}" for r in results)
    client = anthropic.Anthropic()
    response = client.messages.parse(
        model=MODEL,
        max_tokens=4096,
        system=(
            "Rate how directly each search result helps answer the question, from 0 "
            "(irrelevant) to 1 (directly answers it). Return exactly one judgment per "
            "result, using its url exactly as given."
        ),
        messages=[{"role": "user", "content": f"Question: {question}\n\nResults:\n{listing}"}],
        output_format=RelevanceJudgments,
    )
    return {j.url: j.relevance for j in response.parsed_output.judgments}


RelevanceFn = Callable[[str, list[SearchResultItem]], dict[str, float]]


def credibility_node(state: ResearchState, relevance_fn: RelevanceFn = judge_relevance) -> dict:
    scored_results: dict[str, list[SearchResultItem]] = {}

    for sub_question, results in state.search_results.items():
        relevance = relevance_fn(sub_question, results)
        scored = [
            result.model_copy(
                update={
                    "credibility_score": combined_score(
                        domain_score(result.url), relevance.get(result.url, DEFAULT_DOMAIN_SCORE)
                    )
                }
            )
            for result in results
        ]
        scored.sort(key=lambda r: r.credibility_score, reverse=True)
        scored_results[sub_question] = scored

    return {"search_results": scored_results}
