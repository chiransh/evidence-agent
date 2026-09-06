from evidence_agent.search import SearchBackend, TavilySearchBackend
from evidence_agent.state import ResearchState, SearchResultItem


def searcher_node(state: ResearchState, backend: SearchBackend | None = None) -> dict:
    backend = backend or TavilySearchBackend()
    results: dict[str, list[SearchResultItem]] = {}
    for sub_question in state.sub_questions:
        found = backend.search(sub_question, max_results=5)
        results[sub_question] = [
            SearchResultItem(title=r.title, url=r.url, snippet=r.snippet) for r in found
        ]
    return {"search_results": results}
