from evidence_agent.search import SearchBackend, TavilySearchBackend
from evidence_agent.state import ResearchState


def searcher_node(state: ResearchState, backend: SearchBackend | None = None) -> dict:
    backend = backend or TavilySearchBackend()
    results: dict[str, list[dict[str, str]]] = {}
    for sub_question in state["sub_questions"]:
        found = backend.search(sub_question, max_results=5)
        results[sub_question] = [
            {"title": r.title, "url": r.url, "snippet": r.snippet} for r in found
        ]
    return {"search_results": results}
