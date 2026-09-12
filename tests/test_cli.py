import json

import pytest

from evidence_agent import cli


def test_help_lists_every_subcommand(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--help"])

    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    for command in ("research", "ask", "search", "eval", "compare"):
        assert command in out


def test_no_subcommand_is_an_error():
    with pytest.raises(SystemExit) as exit_info:
        cli.main([])
    assert exit_info.value.code != 0


def test_forwarded_subcommand_accepts_a_leading_flag(tmp_path):
    """Regression: dispatching these through argparse.REMAINDER broke on an
    option in first position, so `eval --limit 1` was rejected as an
    unrecognised top-level flag."""
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    out = tmp_path / "cmp.md"

    run = {
        "variant": "x",
        "per_question": [
            {
                "id": "q1",
                "coverage": {"coverage_rate": 0.5},
                "support": {"support_rate": 1.0},
                "citations": {"live_rate": 1.0},
                "length": {"words": 10},
            }
        ],
        "aggregate": {
            "n_questions": 1,
            "n_scored": 1,
            "n_errors": 0,
            "mean_coverage_rate": 0.5,
            "mean_support_rate": 1.0,
            "mean_citation_live_rate": 1.0,
            "mean_words": 10.0,
            "total_citations": 1,
            "total_dead_citations": 0,
            "total_blocked_citations": 0,
        },
    }
    a.write_text(json.dumps(run))
    b.write_text(json.dumps(run))

    # --out is an option, and it follows two positionals; both orderings must work.
    cli.main(["compare", str(a), str(b), "--out", str(out)])
    assert out.exists()

    out.unlink()
    cli.main(["compare", "--out", str(out), str(a), str(b)])
    assert out.exists()


def test_typed_errors_exit_with_a_message_not_a_traceback(capsys, monkeypatch):
    from evidence_agent.exceptions import ConfigurationError

    def boom(question):
        raise ConfigurationError("no credentials here")

    monkeypatch.setattr(cli, "ask", boom)

    with pytest.raises(SystemExit) as exit_info:
        cli.main(["ask", "anything"])

    assert exit_info.value.code == 2
    assert "no credentials here" in capsys.readouterr().err


def test_unexpected_errors_are_not_swallowed(monkeypatch):
    """A bug in our own code should surface as a traceback, not be reported as
    a tidy user-facing error."""

    def boom(question):
        raise ValueError("a real bug")

    monkeypatch.setattr(cli, "ask", boom)

    with pytest.raises(ValueError, match="a real bug"):
        cli.main(["ask", "anything"])
