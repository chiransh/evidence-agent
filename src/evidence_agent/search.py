"""Pluggable search backends.

Tavily is the primary backend. Wikipedia is the fallback, chosen because it
needs no key and is the one search API that is realistically always up, which
matters here: keyless Tavily rate-limits quickly, and a full eval run makes a
search call per sub-question across every question. `default_backend()` wires
the two together.

Every result carries the name of the backend that produced it, so a report built
partly from fallback sources says so, and the eval can separate the two.
"""

import html
import logging
import re
import threading
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

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    backend: str = ""


class SearchBackend(Protocol):
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]: ...


class TavilySearchBackend:
    name = "tavily"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key
        # TavilyClient holds a single requests.Session, and requests does not
        # promise a Session is safe to share across threads. The searcher runs
        # sub-questions concurrently, so each thread gets its own client.
        self._local = threading.local()

    def _client(self) -> TavilyClient:
        client = getattr(self._local, "client", None)
        if client is None:
            client = self._local.client = TavilyClient(api_key=self._api_key)
        return client

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        try:
            response = self._client().search(query, max_results=max_results)
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
                backend=self.name,
            )
            for result in response.get("results", [])
        ]


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
# Wikimedia asks automated clients to identify themselves and blocks generic
# user agents, so this is required rather than polite.
WIKIPEDIA_USER_AGENT = "evidence-agent/0.1 (https://github.com/chiransh/evidence-agent)"


class WikipediaSearchBackend:
    name = "wikipedia"

    def __init__(self, timeout: float = 10.0, sentences: int = 4) -> None:
        self._timeout = timeout
        self._sentences = sentences

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        params = {
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": max_results,
            # The plain-text opening of each article rather than the search
            # snippet, which is a fragment with HTML highlighting and too short to
            # judge a claim against.
            "prop": "extracts|info",
            "exintro": 1,
            "explaintext": 1,
            "exsentences": self._sentences,
            "exlimit": max_results,
            "inprop": "url",
        }
        try:
            response = requests.get(
                WIKIPEDIA_API,
                params=params,
                headers={"User-Agent": WIKIPEDIA_USER_AGENT},
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise TransientError(f"Wikipedia request failed: {exc}") from exc

        if response.status_code == 429 or response.status_code >= 500:
            raise TransientError(f"Wikipedia returned {response.status_code}")
        if response.status_code >= 400:
            raise SearchError(f"Wikipedia returned {response.status_code}")

        try:
            pages = response.json().get("query", {}).get("pages", [])
        except ValueError as exc:
            raise SearchError(f"Wikipedia returned a non-JSON response: {exc}") from exc

        # Generator results are not ordered by relevance; each page carries its
        # search rank in `index`.
        pages = sorted(pages, key=lambda page: page.get("index", 0))
        return [
            SearchResult(
                title=page.get("title", ""),
                url=page.get("fullurl", ""),
                snippet=_clean(page.get("extract", "")),
                backend=self.name,
            )
            for page in pages
            if page.get("fullurl")
        ]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", text))).strip()


class FallbackSearchBackend:
    """Try the primary backend, and use the fallback when it cannot answer.

    Falls back on a transient failure, a search error, or an empty result. It
    deliberately does not fall back on a ConfigurationError: a bad or missing key
    that got quietly replaced by Wikipedia on every query would hide the
    misconfiguration and degrade every report without anyone noticing.
    """

    def __init__(self, primary: SearchBackend, fallback: SearchBackend) -> None:
        self.primary = primary
        self.fallback = fallback

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        try:
            results = self.primary.search(query, max_results=max_results)
        except ConfigurationError:
            raise
        except (TransientError, SearchError) as exc:
            logger.warning("primary search failed for %r, using fallback: %s", query, exc)
            return self.fallback.search(query, max_results=max_results)

        if not results:
            logger.info("primary search returned nothing for %r, using fallback", query)
            return self.fallback.search(query, max_results=max_results)
        return results


def default_backend() -> SearchBackend:
    return FallbackSearchBackend(TavilySearchBackend(), WikipediaSearchBackend())
