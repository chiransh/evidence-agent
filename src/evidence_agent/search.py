"""Pluggable search backends. Tavily is the first implementation; swapping in
Brave or SerpAPI later means adding a class here, not touching call sites."""

from dataclasses import dataclass
from typing import Protocol

import requests
from tavily import (
    InvalidAPIKeyError,
    MissingAPIKeyError,
    TavilyClient,
    TavilyKeylessLimitError,
    UsageLimitExceededError,
)

from evidence_agent.exceptions import ConfigurationError, SearchError, TransientError


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
        try:
            response = self._client.search(query, max_results=max_results)
        except (InvalidAPIKeyError, MissingAPIKeyError) as exc:
            raise ConfigurationError(f"Tavily rejected the API key: {exc}") from exc
        except (UsageLimitExceededError, TavilyKeylessLimitError) as exc:
            # Keyless mode has a low ceiling, so this is the error a dev without
            # a TAVILY_API_KEY hits first. Retrying may clear it; it is not a
            # permanent misconfiguration.
            raise TransientError(f"Tavily rate limit reached: {exc}") from exc
        except requests.RequestException as exc:
            raise TransientError(f"Tavily request failed: {exc}") from exc
        except Exception as exc:
            raise SearchError(f"Tavily search failed: {exc}") from exc

        return [
            SearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                snippet=result.get("content", ""),
            )
            for result in response.get("results", [])
        ]
