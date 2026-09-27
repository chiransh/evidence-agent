"""Page text for the support judge, instead of the search snippet.

The support metric asks whether a cited source actually says what the report
claims it says. Until now the judge saw the search result snippet, which is one
or two sentences the search engine chose for its own purposes. That biases the
metric in both directions: a snippet that happens to restate the claim scores a
citation as supported without the page being read, and a page that states the
claim three paragraphs below the snippet scores as unsupported. Neither error is
visible in the output, which is what makes it worth fixing rather than noting.

So this fetches the cited page, turns it into plain text, splits it into
passages, and hands the judge the passages most likely to carry the claim.
Selection is lexical and deterministic on purpose: a model choosing the evidence
for another model to grade would let one judgment hide inside another.

Where a page cannot be fetched or yields too little text, the snippet is used and
the record says so, so a support rate can be read alongside how much of it rests
on page content.
"""

import html
import random
import re
from dataclasses import dataclass, field

import requests

USER_AGENT = "evidence-agent-eval/0.1"

# Passages shorter than this are navigation, captions and cookie notices rather
# than prose that could support a claim.
MIN_PASSAGE_CHARS = 120
MAX_PASSAGES = 4
MAX_EVIDENCE_CHARS = 4000
# Below this there is no more evidence in the page than in the snippet, so there
# is nothing gained by preferring it.
MIN_USABLE_PAGE_CHARS = 400

_SCRIPT_OR_STYLE = re.compile(r"<(script|style|noscript|template)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_BLOCK_END = re.compile(r"</(p|div|section|article|li|h[1-6]|tr|blockquote)\s*>", re.IGNORECASE)
_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")
_BLANK_LINES = re.compile(r"\n{2,}")
_SPACES = re.compile(r"[ \t\r\f\v]+")
_WORD = re.compile(r"[a-z0-9]+")

# Words too common to say anything about which passage matches a claim.
_STOPWORDS = frozenset(
    """a an and are as at be been but by for from had has have he her his how in
    into is it its of on or she that the their them there these they this to was
    were what when where which who will with would you your""".split()
)


@dataclass
class PageText:
    url: str
    status: int | None
    verdict: str  # fetched, blocked, dead, unreachable, or unparseable
    text: str = ""

    @property
    def usable(self) -> bool:
        return self.verdict == "fetched" and len(self.text) >= MIN_USABLE_PAGE_CHARS


@dataclass
class Evidence:
    """What the judge is shown for one claim, and where it came from."""

    text: str
    source: str  # page or snippet
    reason: str = ""  # why the page was not used, when it was not
    n_passages: int = 0
    page_chars: int = 0
    passage_ranks: list[int] = field(default_factory=list)


def to_text(markup: str) -> str:
    """HTML to plain text, keeping paragraph boundaries and nothing else.

    Deliberately not a parser dependency: the job is to recover readable prose
    from arbitrary pages, and block-level tags are the only structure that
    matters for that. Script and style bodies go first, because their contents
    survive tag stripping and read as text.
    """
    text = _SCRIPT_OR_STYLE.sub(" ", _COMMENT.sub(" ", markup))
    text = _BREAK.sub("\n", _BLOCK_END.sub("\n\n", text))
    text = _TAG.sub(" ", text)
    text = html.unescape(text)

    lines = [_SPACES.sub(" ", line).strip() for line in text.split("\n")]
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def fetch_page(url: str, timeout: float = 15.0, session=None, max_bytes: int = 2_000_000) -> PageText:
    """Fetch one page as text.

    Non-HTML responses are reported as unparseable rather than run through the
    text extractor: a PDF or an image would come out as noise the judge would
    then grade a claim against.
    """
    http = session or requests
    try:
        response = http.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"},
        )
    except requests.RequestException:
        return PageText(url=url, status=None, verdict="unreachable")

    status = response.status_code
    if status >= 400:
        return PageText(url=url, status=status, verdict="blocked" if status in (401, 403, 405, 406, 429) else "dead")

    content_type = response.headers.get("Content-Type", "")
    if content_type and "html" not in content_type.lower() and "text/plain" not in content_type.lower():
        return PageText(url=url, status=status, verdict="unparseable")

    return PageText(url=url, status=status, verdict="fetched", text=to_text(response.text[:max_bytes]))


def fetch_pages(urls, timeout: float = 15.0) -> dict[str, PageText]:
    """One fetch per distinct URL: several claims routinely cite the same page."""
    pages: dict[str, PageText] = {}
    with requests.Session() as session:
        for url in urls:
            if url not in pages:
                pages[url] = fetch_page(url, timeout=timeout, session=session)
    return pages


def passages(text: str, min_chars: int = MIN_PASSAGE_CHARS) -> list[str]:
    blocks = [block.strip() for block in text.split("\n")]
    return [block for block in blocks if len(block) >= min_chars]


def content_terms(text: str) -> set[str]:
    """The words in a text that carry meaning for matching, lowercased."""
    return {word for word in _WORD.findall(text.lower()) if word not in _STOPWORDS and len(word) > 2}


def score_passage(claim_terms: set[str], passage: str) -> float:
    """Share of the claim's content words the passage contains.

    Normalised by the claim rather than by the passage so that a long passage
    covering the claim is not penalised for its length, which is the case that
    matters: the evidence for a claim is often one sentence inside a long
    paragraph.
    """
    if not claim_terms:
        return 0.0
    return len(claim_terms & content_terms(passage)) / len(claim_terms)


def select_passages(
    claim: str,
    text: str,
    max_passages: int = MAX_PASSAGES,
    max_chars: int = MAX_EVIDENCE_CHARS,
) -> list[tuple[int, str]]:
    """The passages most likely to carry the claim, in the page's own order.

    Ranked by overlap with the claim, then restored to reading order: passages
    shown out of order read as a different argument from the one the page makes.
    Their ranks are kept so a record can show which part of the page was used.
    """
    candidates = passages(text)
    if not candidates:
        return []

    claim_terms = content_terms(claim)
    ranked = sorted(
        enumerate(candidates),
        key=lambda pair: (-score_passage(claim_terms, pair[1]), pair[0]),
    )

    chosen: list[tuple[int, str]] = []
    budget = max_chars
    for position, passage in ranked[:max_passages]:
        if len(passage) > budget:
            continue
        chosen.append((position, passage))
        budget -= len(passage)

    return sorted(chosen)


def random_passages(
    text: str, seed: int, target_chars: int = MAX_EVIDENCE_CHARS
) -> list[tuple[int, str]]:
    """As much page as `target_chars`, chosen without looking at the claim.

    The control for claim-targeted selection. Selected passages are several times
    the length of a search snippet, so they would contain more of a claim's words
    even if the ranking were picking at random, and only a size-matched sample
    separates the two.

    Draws until it has at least the target, so the control is never shown less
    text than the selection it is compared with. Erring the other way would flatter
    selection, which is the conclusion this is meant to test rather than support.
    """
    candidates = list(enumerate(passages(text)))
    if not candidates:
        return []

    random.Random(seed).shuffle(candidates)

    chosen: list[tuple[int, str]] = []
    total = 0
    for position, passage in candidates:
        if total >= target_chars:
            break
        chosen.append((position, passage))
        total += len(passage)

    return sorted(chosen)


def evidence_for(claim: str, snippet: str, page: PageText | None) -> Evidence:
    """What to show the judge for one claim, preferring the page over the snippet."""
    if page is None:
        return Evidence(text=snippet, source="snippet", reason="not fetched")
    if not page.usable:
        reason = page.verdict if page.verdict != "fetched" else "too little text"
        return Evidence(text=snippet, source="snippet", reason=reason, page_chars=len(page.text))

    selected = select_passages(claim, page.text)
    if not selected:
        return Evidence(
            text=snippet, source="snippet", reason="no usable passage", page_chars=len(page.text)
        )

    return Evidence(
        text="\n\n".join(passage for _, passage in selected),
        source="page",
        n_passages=len(selected),
        page_chars=len(page.text),
        passage_ranks=[position for position, _ in selected],
    )


def evidence_summary(evidence: list[Evidence]) -> dict:
    """How much of a support rate rests on page content rather than snippets.

    Reported next to the rate itself. A support number judged mostly from
    snippets is a weaker measurement than one judged from pages, and the
    difference should be visible without rerunning anything.
    """
    from_page = [e for e in evidence if e.source == "page"]
    fallbacks: dict[str, int] = {}
    for item in evidence:
        if item.source != "page":
            fallbacks[item.reason] = fallbacks.get(item.reason, 0) + 1

    return {
        "n_claims": len(evidence),
        "n_from_page": len(from_page),
        "page_rate": len(from_page) / len(evidence) if evidence else None,
        "mean_evidence_chars": (
            sum(len(e.text) for e in evidence) / len(evidence) if evidence else None
        ),
        "fallback_reasons": dict(sorted(fallbacks.items())),
    }
