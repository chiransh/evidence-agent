from evidence_agent.credibility import (
    DEFAULT_DOMAIN_SCORE,
    GOV_EDU_SCORE,
    combined_score,
    credibility_node,
    domain_score,
)
from evidence_agent.state import ResearchState, SearchResultItem


def test_known_domain_gets_its_table_score():
    assert domain_score("https://arxiv.org/abs/1234") == 0.95
    assert domain_score("https://www.nature.com/articles/x") == 0.95


def test_subdomain_of_known_domain_inherits_score():
    assert domain_score("https://en.wikipedia.org/wiki/Paris") == 0.75


def test_gov_and_edu_get_the_gov_edu_score():
    assert domain_score("https://www.cdc.gov/some/page") == GOV_EDU_SCORE
    assert domain_score("https://mit.edu/some/page") == GOV_EDU_SCORE


def test_unknown_domain_gets_default_score():
    assert domain_score("https://some-random-blog.example.com/post") == DEFAULT_DOMAIN_SCORE


def test_combined_score_weights_relevance_more_than_domain():
    high_domain_low_relevance = combined_score(domain=0.95, relevance=0.1)
    low_domain_high_relevance = combined_score(domain=0.5, relevance=0.9)
    assert low_domain_high_relevance > high_domain_low_relevance


def test_credibility_node_sorts_results_by_combined_score():
    results = [
        SearchResultItem(title="Low relevance", url="https://arxiv.org/a", snippet=""),
        SearchResultItem(title="High relevance", url="https://random.example.com/b", snippet=""),
    ]
    state = ResearchState(question="Q", sub_questions=["sq"], search_results={"sq": results})

    def fake_relevance_fn(question, results):
        return {"https://arxiv.org/a": 0.1, "https://random.example.com/b": 0.95}

    out = credibility_node(state, relevance_fn=fake_relevance_fn)
    scored = out["search_results"]["sq"]

    # High relevance on a mediocre domain should outrank a top domain with low relevance,
    # since relevance is weighted higher than domain reputation.
    assert scored[0].url == "https://random.example.com/b"
    assert scored[0].credibility_score >= scored[1].credibility_score
