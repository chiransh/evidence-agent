"""Pluggable search backends. Tavily is the first implementation; swapping in
Brave or SerpAPI later means adding a class here, not touching call sites."""

from dataclasses import dataclass
from typing import Protocol

from tavily import TavilyClient


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchBackend(Protocol):
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]: ...


class TavilySearchBackend:
    def __init__(self, api_key: str | None = None) -> None:
        self._client = TavilyClient(api_key=api_key)

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        response = self._client.search(query, max_results=max_results)
        return [
            SearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                snippet=result.get("content", ""),
            )
            for result in response.get("results", [])
        ]
