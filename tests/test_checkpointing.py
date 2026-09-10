"""Checkpointing has to actually let a failed run resume without redoing the
expensive work, so these tests exercise a real graph with a real saver rather
than asserting the checkpointer object was passed through."""

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy
from pydantic import BaseModel

from evidence_agent.exceptions import ConfigurationError, TransientError


class _State(BaseModel):
    calls: list[str] = []


def test_completed_nodes_are_not_rerun_after_resume(tmp_path):
    """A node that already succeeded must not be called again when the thread
    is resumed, which is the entire point of checkpointing an agent whose
    nodes cost money to run."""
    expensive_calls = []
    should_fail = True

    def expensive(state: _State) -> dict:
        expensive_calls.append("ran")
        return {"calls": state.calls + ["expensive"]}

    def flaky(state: _State) -> dict:
        if should_fail:
            raise RuntimeError("downstream blew up")
        return {"calls": state.calls + ["flaky"]}

    def build(checkpointer):
        graph = StateGraph(_State)
        graph.add_node("expensive", expensive)
        graph.add_node("flaky", flaky)
        graph.add_edge(START, "expensive")
        graph.add_edge("expensive", "flaky")
        graph.add_edge("flaky", END)
        return graph.compile(checkpointer=checkpointer)

    db = str(tmp_path / "checkpoints.sqlite")
    config = {"configurable": {"thread_id": "t1"}}

    with SqliteSaver.from_conn_string(db) as saver:
        try:
            build(saver).invoke({"calls": []}, config=config)
        except RuntimeError:
            pass

    assert expensive_calls == ["ran"]

    should_fail = False
    with SqliteSaver.from_conn_string(db) as saver:
        result = build(saver).invoke(None, config=config)

    # Resumed from the checkpoint: the expensive node was not paid for twice.
    assert expensive_calls == ["ran"]
    assert result["calls"] == ["expensive", "flaky"]


def test_retry_policy_retries_transient_then_succeeds():
    attempts = []

    def flaky(state: _State) -> dict:
        attempts.append(len(attempts))
        if len(attempts) < 3:
            raise TransientError("rate limited")
        return {"calls": ["ok"]}

    graph = StateGraph(_State)
    graph.add_node(
        "flaky",
        flaky,
        retry_policy=RetryPolicy(max_attempts=3, initial_interval=0.01, retry_on=TransientError),
    )
    graph.add_edge(START, "flaky")
    graph.add_edge("flaky", END)

    result = graph.compile().invoke({"calls": []})

    assert len(attempts) == 3
    assert result["calls"] == ["ok"]


def test_retry_policy_does_not_retry_configuration_error():
    attempts = []

    def broken(state: _State) -> dict:
        attempts.append(1)
        raise ConfigurationError("no API key")

    graph = StateGraph(_State)
    graph.add_node(
        "broken",
        broken,
        retry_policy=RetryPolicy(max_attempts=3, initial_interval=0.01, retry_on=TransientError),
    )
    graph.add_edge(START, "broken")
    graph.add_edge("broken", END)

    try:
        graph.compile().invoke({"calls": []})
    except ConfigurationError:
        pass

    assert len(attempts) == 1  # failed once, not three times
