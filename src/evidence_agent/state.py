from pydantic import BaseModel


class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str
    credibility_score: float | None = None


class Finding(BaseModel):
    claim: str
    source_url: str


class ResearchState(BaseModel):
    question: str
    sub_questions: list[str] = []
    search_results: dict[str, list[SearchResultItem]] = {}
    findings: list[Finding] = []
    report: str = ""
