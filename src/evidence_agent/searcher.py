from evidence_agent.concurrency import map_in_order
from evidence_agent.search import SearchBackend, default_backend
from evidence_agent.state import ResearchState, SearchResultItem


def searcher_node(state: ResearchState, backend: SearchBackend | None = None) -> dict:
    """Search every sub-question at once. The calls are independent, so running
    them in sequence only added latency; results keep the planner's order."""
    backend = backend or default_backend()

    def search(sub_question: str) -> list[SearchResultItem]:
        return [
            SearchResultItem(title=r.title, url=r.url, snippet=r.snippet, backend=r.backend or None)
            for r in backend.search(sub_question, max_results=5)
        ]

    found = map_in_order(search, state.sub_questions)
    return {"search_results": dict(zip(state.sub_questions, found))}
