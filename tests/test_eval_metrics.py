import json
from pathlib import Path

from evidence_agent.evaluation.harness import aggregate, evaluate_one, load_dataset, run_eval
from evidence_agent.evaluation.metrics import (
    UrlCheck,
    answer_length,
    coverage_rate,
    support_rate,
    url_validity,
)
from evidence_agent.exceptions import ConfigurationError
from evidence_agent.state import Finding, SearchResultItem


def test_blocked_urls_are_excluded_from_the_rate_not_counted_as_valid():
    checks = [
        UrlCheck("https://a", 200, "live"),
        UrlCheck("https://b", 404, "dead"),
        UrlCheck("https://c", 403, "blocked"),
    ]
    result = url_validity(checks)

    assert result["n_citations"] == 3
    assert result["n_live"] == 1 and result["n_dead"] == 1 and result["n_blocked"] == 1
    # 1 live of 2 decided, with the blocked one left out of the denominator.
    assert result["live_rate"] == 0.5


def test_all_blocked_gives_no_rate_rather_than_a_perfect_score():
    checks = [UrlCheck("https://a", 403, "blocked")]
    assert url_validity(checks)["live_rate"] is None


def test_unreachable_counts_against_validity():
    checks = [UrlCheck("https://a", 200, "live"), UrlCheck("https://b", None, "unreachable")]
    assert url_validity(checks)["live_rate"] == 0.5


def test_rates_are_none_when_there_is_nothing_to_score():
    assert support_rate([]) is None
    assert coverage_rate({}) is None


def test_answer_length_counts_words_and_characters():
    assert answer_length("one two three")["words"] == 3
    assert answer_length("abc")["characters"] == 3


def test_evaluate_one_scores_a_fake_pipeline_run():
    item = {
        "id": "q1",
        "question": "Why is the sky blue?",
        "key_points": ["Rayleigh scattering", "Shorter wavelengths scatter more"],
    }

    def pipeline(question):
        return {
            "report": "The sky is blue because of Rayleigh scattering.",
            "findings": [Finding(claim="Rayleigh scattering makes it blue", source_url="https://a")],
            "search_results": {
                "sq": [SearchResultItem(title="T", url="https://a", snippet="Rayleigh scattering")]
            },
            "sub_questions": ["sq"],
        }

    record = evaluate_one(
        item,
        pipeline,
        url_checker=lambda urls: {u: UrlCheck(u, 200, "live") for u in urls},
        support_fn=lambda pairs: [True] * len(pairs),
        coverage_fn=lambda report, points: {points[0]: True, points[1]: False},
    )

    assert record["citations"]["live_rate"] == 1.0
    assert record["support"]["support_rate"] == 1.0
    assert record["coverage"]["coverage_rate"] == 0.5
    assert record["coverage"]["missed"] == ["Shorter wavelengths scatter more"]
    assert record["length"]["words"] > 0


def test_a_failing_question_is_recorded_and_does_not_abort_the_run():
    items = [
        {"id": "boom", "question": "q", "key_points": ["p"]},
        {"id": "ok", "question": "q", "key_points": ["p"]},
    ]

    def pipeline(question):
        if not pipeline.failed:
            pipeline.failed = True
            raise ConfigurationError("no API key")
        return {"report": "fine", "findings": [], "search_results": {}, "sub_questions": []}

    pipeline.failed = False

    results = run_eval(
        items,
        pipeline,
        url_checker=lambda urls: {},
        support_fn=lambda pairs: [],
        coverage_fn=lambda report, points: {p: True for p in points},
    )

    assert results["aggregate"]["n_errors"] == 1
    assert results["aggregate"]["n_scored"] == 1
    assert "ConfigurationError" in results["per_question"][0]["error"]


def test_aggregate_ignores_missing_rates_instead_of_treating_them_as_zero():
    records = [
        {
            "citations": {"live_rate": 1.0, "n_citations": 1, "n_dead": 0, "n_blocked": 0},
            "support": {"support_rate": None},
            "coverage": {"coverage_rate": 0.5},
            "length": {"words": 10},
        },
        {
            "citations": {"live_rate": None, "n_citations": 0, "n_dead": 0, "n_blocked": 0},
            "support": {"support_rate": 1.0},
            "coverage": {"coverage_rate": 1.0},
            "length": {"words": 20},
        },
    ]
    agg = aggregate(records)

    # Only the one present value, not an average dragged down by a None read as 0.
    assert agg["mean_citation_live_rate"] == 1.0
    assert agg["mean_support_rate"] == 1.0
    assert agg["mean_coverage_rate"] == 0.75


def test_dataset_is_well_formed():
    questions = load_dataset(Path("evals/dataset.json"))

    assert len(questions) >= 15, "the plan calls for 15 to 20 questions"
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids)), "question ids must be unique"

    for q in questions:
        assert q["question"].strip()
        assert q["reference_answer"].strip()
        assert len(q["key_points"]) >= 3, f"{q['id']} needs enough key points to score coverage"
