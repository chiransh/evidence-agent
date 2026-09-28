"""Page evidence tests.

Two failures matter here and neither is visible in a support score. Text
extraction that leaves script bodies or navigation in place gives the judge
something to grade that the page does not actually say. Passage selection that
misses the paragraph carrying the claim marks a genuine citation unsupported.
The rest cover the fallback to the snippet, which has to be recorded rather than
silent, because a support rate judged from snippets is a weaker number than one
judged from pages.
"""

import pytest

from evidence_agent.evaluation.pages import (
    DEFAULT_SELECTOR,
    PLAIN,
    SELECTORS,
    STEMMED,
    WEIGHTED,
    Evidence,
    PageText,
    evidence_for,
    evidence_summary,
    fetch_page,
    passages,
    random_passages,
    score_passage,
    select_passages,
    stem,
    term_weights,
    to_text,
)


def _para(text: str, filler: str = " Additional sentence to carry the paragraph past the length floor.") -> str:
    """A passage long enough to survive the navigation filter."""
    return text + filler * 2


# Text extraction ----------------------------------------------------------------


def test_script_and_style_bodies_are_removed_not_just_their_tags():
    """Tag stripping alone leaves the JavaScript behind as text, and the judge
    would then be grading a claim against it."""
    markup = """
    <html><head><style>body { color: red; }</style>
    <script>var tracking = function(x) { return x + 1; };</script></head>
    <body><p>The bridge opened in 1894.</p></body></html>
    """
    text = to_text(markup)

    assert "The bridge opened in 1894." in text
    assert "function" not in text
    assert "color: red" not in text


def test_comments_are_removed():
    assert "hidden" not in to_text("<p>shown</p><!-- hidden note -->")


def test_paragraph_boundaries_survive_and_inline_tags_do_not():
    text = to_text("<p>First para with <em>emphasis</em> inside.</p><p>Second para.</p>")

    assert text.split("\n\n") == ["First para with emphasis inside.", "Second para."]


def test_entities_are_decoded():
    assert to_text("<p>Paris &amp; Lyon, both in France</p>") == "Paris & Lyon, both in France"
    assert to_text("<p>caf&eacute; culture</p>") == "café culture"


def test_list_items_and_headings_become_separate_lines():
    text = to_text("<h2>Causes</h2><ul><li>First cause</li><li>Second cause</li></ul>")
    assert ["Causes", "First cause", "Second cause"] == [
        line for line in text.split("\n") if line
    ]


def test_line_breaks_do_not_glue_words_together():
    assert to_text("<p>one<br>two</p>") == "one\ntwo"


def test_runs_of_whitespace_collapse():
    assert to_text("<p>spaced      out\t\ttext</p>") == "spaced out text"


# Passages -----------------------------------------------------------------------


def test_short_lines_are_dropped_as_navigation():
    text = "Home\nAbout us\nContact\n" + _para("The treaty was signed in 1919.")
    found = passages(text)

    assert len(found) == 1
    assert "treaty" in found[0]


def test_a_page_of_only_navigation_yields_no_passages():
    assert passages("Home\nAbout\nPrivacy\nTerms") == []


# Selection ----------------------------------------------------------------------


def test_score_is_the_share_of_the_claims_terms_the_passage_contains():
    assert score_passage({"treaty", "signed", "1919"}, "The treaty was signed in 1919.") == 1.0
    assert score_passage({"treaty", "signed", "1919"}, "The treaty was long.") == pytest.approx(1 / 3)


def test_stopwords_do_not_count_toward_a_match():
    """Scoring on every word would rank a passage full of 'the' and 'of' as a
    match for any claim."""
    assert score_passage(set(), "anything") == 0.0
    assert score_passage({"treaty"}, "of the and with that this") == 0.0


def test_a_claim_is_matched_to_the_paragraph_that_carries_it_not_the_first_ones():
    """The whole point of fetching the page: the evidence is often well below
    whatever the search engine chose to show. Needs more paragraphs than the
    selection budget, or every one is chosen and nothing is being selected."""
    filler = [
        _para(f"An unrelated paragraph about municipal committees, number {i}.") for i in range(8)
    ]
    carrier = _para("The tram network was electrified in 1926 by the municipal company.")
    text = "\n".join(filler + [carrier])

    selected = select_passages("The tram network was electrified in 1926", text)

    assert len(selected) < len(filler) + 1, "selection should exclude most of the page"
    assert any("electrified in 1926" in passage for _, passage in selected)


def test_selected_passages_are_returned_in_the_pages_own_order():
    """Shown out of order they read as a different argument from the one the page
    makes, which is not what the judge should be grading."""
    text = "\n".join(
        [
            _para("Electrification of the tram network began early."),
            _para("An unrelated paragraph about the weather and the seasons."),
            _para("Tram network electrification finished in 1926."),
        ]
    )

    ranks = [position for position, _ in select_passages("tram network electrification", text)]
    assert ranks == sorted(ranks)


def test_selection_respects_the_character_budget():
    long_para = _para("The tram network was electrified.", filler=" filler" * 60)
    text = "\n".join([long_para] * 6)

    selected = select_passages("tram network electrified", text, max_chars=len(long_para) + 10)
    assert len(selected) == 1


def test_selection_returns_nothing_for_a_page_with_no_prose():
    assert select_passages("anything at all", "Home\nAbout\nContact") == []


# Choosing what the judge sees ---------------------------------------------------


def test_page_content_is_preferred_over_the_snippet():
    text = "\n".join(
        [_para("The canal opened in 1869 after ten years of construction work.")]
        + [_para(f"Background paragraph {i} about the surveying of the route.") for i in range(3)]
    )
    page = PageText("https://a", 200, "fetched", text)
    evidence = evidence_for("The canal opened in 1869", "canal ... 1869", page)

    assert evidence.source == "page"
    assert "after ten years" in evidence.text
    assert evidence.passage_ranks[0] == 0  # the paragraph carrying the claim


def test_a_blocked_page_falls_back_to_the_snippet_and_says_why():
    evidence = evidence_for("claim", "the snippet", PageText("https://a", 403, "blocked"))

    assert evidence.source == "snippet"
    assert evidence.text == "the snippet"
    assert evidence.reason == "blocked"


def test_a_url_that_was_never_fetched_falls_back_to_the_snippet():
    evidence = evidence_for("claim", "the snippet", None)

    assert evidence.source == "snippet"
    assert evidence.reason == "not fetched"


def test_a_page_with_less_text_than_a_snippet_is_not_preferred_to_it():
    """A cookie wall fetches with status 200 and a few words of text. Preferring
    it would replace the snippet with something worse."""
    page = PageText("https://a", 200, "fetched", "Please accept cookies to continue.")
    evidence = evidence_for("claim", "the snippet", page)

    assert evidence.source == "snippet"
    assert evidence.reason == "too little text"


def test_a_long_page_with_no_paragraph_long_enough_falls_back():
    page = PageText("https://a", 200, "fetched", "\n".join(["short line"] * 100))
    evidence = evidence_for("claim", "the snippet", page)

    assert evidence.source == "snippet"
    assert evidence.reason == "no usable passage"


def test_a_non_html_response_is_not_run_through_the_extractor():
    """A PDF put through the text extractor comes out as noise, and the judge
    would grade a claim against it."""

    class _Response:
        status_code = 200
        headers = {"Content-Type": "application/pdf"}
        text = "%PDF-1.4 binary-ish nonsense"

    class _Http:
        def get(self, url, **kwargs):
            return _Response()

    page = fetch_page("https://a/report.pdf", session=_Http())

    assert page.verdict == "unparseable"
    assert page.text == ""
    assert not page.usable


# Reporting ----------------------------------------------------------------------


def test_summary_reports_how_much_rests_on_page_content():
    evidence = [
        Evidence(text="a" * 500, source="page", n_passages=2),
        Evidence(text="b" * 100, source="snippet", reason="blocked"),
        Evidence(text="c" * 100, source="snippet", reason="blocked"),
        Evidence(text="d" * 100, source="snippet", reason="too little text"),
    ]
    summary = evidence_summary(evidence)

    assert summary["n_claims"] == 4
    assert summary["n_from_page"] == 1
    assert summary["page_rate"] == 0.25
    assert summary["fallback_reasons"] == {"blocked": 2, "too little text": 1}


def test_summary_of_nothing_is_not_reported_as_a_perfect_page_rate():
    summary = evidence_summary([])

    assert summary["page_rate"] is None
    assert summary["mean_evidence_chars"] is None


# The control ---------------------------------------------------------------------


def test_random_passages_do_not_depend_on_the_claim():
    """The point of the control: it has to be blind to what it is being compared
    against, or it is not a control."""
    text = "\n".join(_para(f"Paragraph number {i} about the tram network.") for i in range(10))

    first = random_passages(text, seed=3, target_chars=600)
    assert first == random_passages(text, seed=3, target_chars=600)
    assert random_passages(text, seed=4, target_chars=600) != first


def test_the_control_is_never_shown_less_text_than_the_selection():
    """A control given less text than the thing it controls for would flatter
    selection, which is the conclusion it exists to test."""
    text = "\n".join(_para(f"Paragraph number {i} about the tram network.") for i in range(20))

    selected = select_passages("tram network electrified", text)
    budget = sum(len(passage) for _, passage in selected)
    control = random_passages(text, seed=1, target_chars=budget)

    assert sum(len(passage) for _, passage in control) >= budget


def test_the_control_stops_at_the_target_rather_than_taking_the_page():
    text = "\n".join(_para(f"Paragraph number {i} about the tram network.") for i in range(40))
    control = random_passages(text, seed=1, target_chars=500)

    assert 0 < len(control) < 40
    assert sum(len(passage) for _, passage in control) < 1000


def test_a_page_shorter_than_the_target_is_returned_whole():
    text = "\n".join(_para(f"Paragraph number {i}.") for i in range(3))
    assert len(random_passages(text, seed=1, target_chars=100_000)) == 3


def test_random_passages_are_returned_in_page_order():
    text = "\n".join(_para(f"Paragraph number {i}.") for i in range(10))
    ranks = [position for position, _ in random_passages(text, seed=2, target_chars=600)]
    assert ranks == sorted(ranks)


def test_a_page_with_no_prose_has_no_control_passages():
    assert random_passages("Home\nAbout\nContact", seed=1, target_chars=600) == []


# Matching rules -------------------------------------------------------------------


def test_inflections_of_a_word_stem_together():
    """The failure this addresses: the report writes "shorter wavelengths scatter
    more" and the page says "light of shorter wavelength is scattered"."""
    assert stem("wavelengths") == stem("wavelength")
    assert stem("scattered") == stem("scattering") == stem("scatters")
    assert stem("predictions") == stem("prediction") == stem("predicting")


def test_short_words_are_left_alone():
    """Stripping a suffix off a short word merges words that mean nothing alike."""
    for word in ("gas", "less", "data", "ones"):
        assert stem(word) == word


def test_a_double_s_ending_is_not_stripped():
    """class and classes have to reach the same form, and stripping the s from
    class would send them to different ones."""
    assert stem("class") == "class"
    assert stem("classes") == "class"
    assert stem("less") == "less"


def test_a_doubled_consonant_left_by_a_suffix_is_collapsed():
    assert stem("labelled") == stem("labels") == "label"


def test_term_weights_favour_a_term_that_appears_in_one_passage():
    passages_ = [
        "learning learning about the topic and its history",
        "learning again, with rayleigh scattering mentioned once",
        "learning a third time with nothing else of note",
    ]
    weights = term_weights(passages_)

    assert weights["rayleigh"] > weights["learning"]


def test_weighted_scoring_prefers_the_passage_with_the_rare_term():
    """A term on every line of the page cannot say which line carries the claim."""
    candidates = [
        _para("Supervised learning is discussed throughout this article at length."),
        _para("Supervised learning here, plus the rayleigh scattering the claim is about."),
    ]
    text = "\n".join(candidates)

    plain_first = select_passages("rayleigh scattering supervised learning", text, max_passages=1)
    weighted_first = select_passages(
        "rayleigh scattering supervised learning", text, max_passages=1, selector=WEIGHTED
    )

    assert weighted_first[0][0] == 1, "the rare term should decide it"
    assert plain_first  # both rank something; the point is which one


def test_a_stemmed_selector_matches_an_inflected_claim():
    carrier = _para("Light of a shorter wavelength is scattered more by the atmosphere.")
    others = [_para(f"An unrelated paragraph about the atmosphere, number {i}.") for i in range(8)]
    text = "\n".join(others + [carrier])

    claim = "shorter wavelengths scatter more"
    plain = select_passages(claim, text, selector=PLAIN)
    stemmed = select_passages(claim, text, selector=STEMMED)

    assert any("shorter wavelength is scattered" in p for _, p in stemmed)
    assert len(plain) == len(stemmed), "both keep to the same passage budget"


def test_every_named_selector_ranks_every_candidate():
    text = "\n".join(_para(f"Paragraph number {i} about the tram network.") for i in range(6))
    candidates = passages(text)

    for name, selector in SELECTORS.items():
        order = selector.rank("tram network", candidates)
        assert sorted(order) == list(range(len(candidates))), name


def test_the_selector_in_use_is_the_one_the_default_names():
    assert DEFAULT_SELECTOR in SELECTORS
    text = "\n".join(_para(f"Paragraph number {i} about the tram network.") for i in range(6))

    assert select_passages("tram", text) == select_passages(
        "tram", text, selector=SELECTORS[DEFAULT_SELECTOR]
    )


def test_a_stem_never_depends_on_the_order_the_suffixes_are_tried():
    """Regression: classes stripped to class and then collapsed the doubled s to
    clas, a form class itself never reaches, so the two stopped matching."""
    for singular, plural in (("class", "classes"), ("guess", "guesses"), ("pass", "passes")):
        assert stem(singular) == stem(plural) == singular
