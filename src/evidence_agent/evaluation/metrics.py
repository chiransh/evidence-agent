"""Metrics for the eval harness.

Citation validity is deliberately two separate measurements, because "the
report cited a URL that does not exist" and "the URL exists but does not say
what the report claims" are different failures with different fixes. The
Synthesizer already drops any citation that was not in the retrieved set, so
the first number should be near-perfect by construction; the second is where
the interesting signal is.

A third state matters for honesty: plenty of real sites answer an automated
request with 403 or 429. That says nothing about whether the citation was
genuine, so blocked URLs are reported separately and left out of the rate
rather than silently counted as either good or bad.
"""

from dataclasses import asdict, dataclass
from typing import Callable, Sequence

import requests
from pydantic import BaseModel

from evidence_agent.llm import MODEL, client, model_errors

USER_AGENT = "evidence-agent-eval/0.1"
BLOCKED_STATUSES = {401, 403, 405, 406, 429}


@dataclass
class UrlCheck:
    url: str
    status: int | None
    verdict: str  # live, dead, blocked, or unreachable


def check_url(url: str, timeout: float = 10.0, session=None) -> UrlCheck:
    http = session or requests
    headers = {"User-Agent": USER_AGENT}

    try:
        response = http.head(url, timeout=timeout, allow_redirects=True, headers=headers)
        if response.status_code >= 400:
            # Many servers refuse HEAD but serve GET perfectly well, so a 4xx
            # here is not yet evidence the page is missing.
            response = http.get(
                url, timeout=timeout, allow_redirects=True, headers=headers, stream=True
            )
            response.close()
    except requests.RequestException:
        return UrlCheck(url=url, status=None, verdict="unreachable")

    status = response.status_code
    if status < 400:
        return UrlCheck(url=url, status=status, verdict="live")
    if status in BLOCKED_STATUSES:
        return UrlCheck(url=url, status=status, verdict="blocked")
    return UrlCheck(url=url, status=status, verdict="dead")


def check_urls(urls: Sequence[str], timeout: float = 10.0) -> dict[str, UrlCheck]:
    checked: dict[str, UrlCheck] = {}
    with requests.Session() as session:
        for url in urls:
            if url not in checked:
                checked[url] = check_url(url, timeout=timeout, session=session)
    return checked


def url_validity(checks: Sequence[UrlCheck]) -> dict:
    live = sum(1 for c in checks if c.verdict == "live")
    dead = sum(1 for c in checks if c.verdict in ("dead", "unreachable"))
    blocked = sum(1 for c in checks if c.verdict == "blocked")
    decided = live + dead

    return {
        "n_citations": len(checks),
        "n_live": live,
        "n_dead": dead,
        "n_blocked": blocked,
        # None rather than 1.0 when nothing could be decided, so an eval with
        # every URL blocked does not read as a perfect score.
        "live_rate": live / decided if decided else None,
    }


class _SupportJudgment(BaseModel):
    index: int
    supported: bool


class _SupportJudgments(BaseModel):
    judgments: list[_SupportJudgment]


def judge_support(pairs: Sequence[tuple[str, str]]) -> list[bool]:
    """For each (claim, source text) pair, does the source actually support the claim."""
    if not pairs:
        return []

    listing = "\n\n".join(
        f"[{i}] CLAIM: {claim}\n    SOURCE TEXT: {source}" for i, (claim, source) in enumerate(pairs)
    )

    with model_errors():
        response = client().messages.parse(
            model=MODEL,
            max_tokens=8000,
            system=(
                "You are grading citations. For each numbered item, decide whether the source "
                "text actually supports the claim. Mark supported only if the source text states "
                "or directly implies the claim. A source that is merely on the same topic does "
                "not count. Return one judgment per item, using the given index."
            ),
            messages=[{"role": "user", "content": listing}],
            output_format=_SupportJudgments,
        )

    verdicts = {j.index: j.supported for j in response.parsed_output.judgments}
    # A missing judgment counts as unsupported: silently dropping an item the
    # judge skipped would inflate the score.
    return [verdicts.get(i, False) for i in range(len(pairs))]


class _CoveredPoint(BaseModel):
    key_point: str
    covered: bool


class _CoverageJudgment(BaseModel):
    points: list[_CoveredPoint]


def judge_coverage(report: str, key_points: Sequence[str]) -> dict[str, bool]:
    """Which of the reference answer's key points does the report actually make."""
    if not key_points:
        return {}

    listing = "\n".join(f"- {point}" for point in key_points)

    with model_errors():
        response = client().messages.parse(
            model=MODEL,
            max_tokens=4096,
            system=(
                "Decide which of the listed key points the report covers. A point is covered if "
                "the report states it in any wording, not necessarily the same wording. It is not "
                "covered if the report only alludes to the general topic. Return one judgment per "
                "key point, repeating the key point text exactly as given."
            ),
            messages=[{"role": "user", "content": f"REPORT:\n{report}\n\nKEY POINTS:\n{listing}"}],
            output_format=_CoverageJudgment,
        )

    judged = {p.key_point: p.covered for p in response.parsed_output.points}
    return {point: judged.get(point, False) for point in key_points}


def answer_length(report: str) -> dict:
    return {"words": len(report.split()), "characters": len(report)}


def support_rate(verdicts: Sequence[bool]) -> float | None:
    return sum(verdicts) / len(verdicts) if verdicts else None


def coverage_rate(covered: dict[str, bool]) -> float | None:
    return sum(covered.values()) / len(covered) if covered else None


def url_check_to_dict(check: UrlCheck) -> dict:
    return asdict(check)


UrlCheckerFn = Callable[[Sequence[str]], dict[str, UrlCheck]]
SupportFn = Callable[[Sequence[tuple[str, str]]], list[bool]]
CoverageFn = Callable[[str, Sequence[str]], dict[str, bool]]
