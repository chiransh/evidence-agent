from typing import TypedDict


class ResearchState(TypedDict):
    question: str
    sub_questions: list[str]
    search_results: dict[str, list[dict[str, str]]]
