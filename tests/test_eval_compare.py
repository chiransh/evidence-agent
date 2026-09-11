import pytest

from evidence_agent.evaluation.compare import (
    bootstrap_ci,
    compare,
    comparison_md,
    paired_differences,
    verdict,
)


def _run(variant: str, per_question: list[tuple[str, float, float]]) -> dict:
    """per_question entries are (id, coverage_rate, support_rate)."""
    records = [
        {
            "id": qid,
            "coverage": {"coverage_rate": coverage},
            "support": {"support_rate": support},
            "citations": {"live_rate": 1.0},
            "length": {"words": 100},
        }
        for qid, coverage, support in per_question
    ]
    return {
        "variant": variant,
        "per_question": records,
        "aggregate": {
            "n_questions": len(records),
            "n_scored": len(records),
            "n_errors": 0,
            "mean_coverage_rate": sum(c for _, c, _ in per_question) / len(per_question),
            "mean_support_rate": sum(s for _, _, s in per_question) / len(per_question),
            "mean_citation_live_rate": 1.0,
            "mean_words": 100.0,
            "total_citations": len(records),
            "total_dead_citations": 0,
            "total_blocked_citations": 0,
        },
    }


def test_pairs_only_questions_both_runs_scored():
    a = _run("a", [("q1", 0.5, 1.0), ("q2", 0.5, 1.0)])
    b = _run("b", [("q1", 0.8, 1.0), ("q3", 0.9, 1.0)])

    diffs = paired_differences(a, b, "mean_coverage_rate")
    assert diffs == pytest.approx([0.3])


def test_questions_that_errored_are_skipped():
    a = _run("a", [("q1", 0.5, 1.0)])
    a["per_question"].append({"id": "q2", "error": "ConfigurationError: boom"})
    b = _run("b", [("q1", 0.6, 1.0), ("q2", 0.9, 1.0)])

    assert len(paired_differences(a, b, "mean_coverage_rate")) == 1


def test_consistent_improvement_is_called_out():
    a = _run("a", [(f"q{i}", 0.4, 1.0) for i in range(12)])
    b = _run("b", [(f"q{i}", 0.7, 1.0) for i in range(12)])

    diffs = paired_differences(a, b, "mean_coverage_rate")
    ci = bootstrap_ci(diffs)

    assert ci[0] > 0
    assert verdict(diffs, ci) == "second run higher"


def test_noisy_wash_is_reported_as_inconclusive_not_as_a_win():
    # Mean difference is slightly positive but the per-question signs disagree,
    # which is exactly the case where a bare mean would mislead.
    a = _run("a", [(f"q{i}", 0.5, 1.0) for i in range(8)])
    b_values = [0.9, 0.1, 0.8, 0.2, 0.9, 0.1, 0.7, 0.3]
    b = _run("b", [(f"q{i}", v, 1.0) for i, v in enumerate(b_values)])

    diffs = paired_differences(a, b, "mean_coverage_rate")
    ci = bootstrap_ci(diffs)

    assert ci[0] < 0 < ci[1]
    assert "inconclusive" in verdict(diffs, ci)


def test_bootstrap_needs_more_than_one_observation():
    assert bootstrap_ci([0.5]) is None
    assert bootstrap_ci([]) is None


def test_bootstrap_is_deterministic_for_a_given_seed():
    values = [0.1, -0.2, 0.3, 0.05, -0.1, 0.2]
    assert bootstrap_ci(values, seed=7) == bootstrap_ci(values, seed=7)


def test_report_says_inconclusive_rather_than_naming_a_winner():
    a = _run("a", [(f"q{i}", 0.5, 1.0) for i in range(6)])
    b = _run("b", [(f"q{i}", v, 1.0) for i, v in enumerate([0.9, 0.1, 0.8, 0.2, 0.9, 0.1])])

    markdown = comparison_md(compare(a, b, "a", "b"), "a", "b")

    assert "does not resolve a difference" in markdown
    assert "Coverage" in markdown


def test_report_includes_both_run_summaries_and_the_length_control():
    a = _run("baseline", [("q1", 0.5, 1.0)])
    b = _run("variant", [("q1", 0.6, 1.0)])

    markdown = comparison_md(compare(a, b, "baseline", "variant"), "baseline", "variant")

    assert "baseline" in markdown and "variant" in markdown
    assert "Answer length is a control" in markdown


def test_identical_runs_are_reported_as_identical_not_inconclusive():
    """Two runs that agreed on every question have been measured as the same.
    Calling that 'inconclusive' would confuse a real null result with a
    sample too small to tell."""
    values = [(f"q{i}", 0.5, 1.0) for i in range(6)]
    a, b = _run("a", values), _run("b", values)

    diffs = paired_differences(a, b, "mean_coverage_rate")
    assert verdict(diffs, bootstrap_ci(diffs)) == "identical"


def test_identical_metrics_are_not_listed_as_unresolved_in_the_report():
    values = [(f"q{i}", 0.5, 1.0) for i in range(6)]
    markdown = comparison_md(compare(_run("a", values), _run("b", values), "a", "b"), "a", "b")

    assert "does not resolve a difference" not in markdown


def test_identical_runs_are_not_described_as_intervals_excluding_zero():
    """Regression: with every metric identical the report previously claimed
    'every interval excludes zero', which is the opposite of what happened."""
    values = [(f"q{i}", 0.5, 1.0) for i in range(6)]
    markdown = comparison_md(compare(_run("a", values), _run("b", values), "a", "b"), "a", "b")

    assert "Every interval excludes zero" not in markdown
    assert "measured null result" in markdown


def test_a_real_separation_is_described_as_exceeding_the_noise():
    a = _run("a", [(f"q{i}", 0.4, 1.0) for i in range(12)])
    b = _run("b", [(f"q{i}", 0.7, 1.0) for i in range(12)])

    markdown = comparison_md(compare(a, b, "a", "b"), "a", "b")
    assert "excludes zero" in markdown
