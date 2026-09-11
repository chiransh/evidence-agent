from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy

from evidence_agent.credibility import credibility_node
from evidence_agent.exceptions import TransientError
from evidence_agent.planner import planner_node
from evidence_agent.searcher import searcher_node
from evidence_agent.state import ResearchState
from evidence_agent.synthesizer import synthesizer_node
from evidence_agent.writer import writer_node

# Only TransientError is retried. A ConfigurationError (no API key) or a
# ModelError (the model returned something unusable) will fail the same way on
# every attempt, and retrying those just turns a clear failure into a slow one.
NETWORK_RETRY = RetryPolicy(
    max_attempts=3,
    initial_interval=1.0,
    backoff_factor=2.0,
    retry_on=TransientError,
)


def build_graph(
    checkpointer: BaseCheckpointSaver | None = None, with_credibility: bool = True
) -> CompiledStateGraph:
    """with_credibility=False drops the credibility node, which is what the eval
    harness scores against to see whether that node earns its cost."""
    graph = StateGraph(ResearchState)

    # Every node that touches the network gets the retry policy. Writer is pure
    # formatting, so a retry there would only repeat the same output.
    graph.add_node("planner", planner_node, retry_policy=NETWORK_RETRY)
    graph.add_node("searcher", searcher_node, retry_policy=NETWORK_RETRY)
    graph.add_node("synthesizer", synthesizer_node, retry_policy=NETWORK_RETRY)
    graph.add_node("writer", writer_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "searcher")

    if with_credibility:
        graph.add_node("credibility", credibility_node, retry_policy=NETWORK_RETRY)
        graph.add_edge("searcher", "credibility")
        graph.add_edge("credibility", "synthesizer")
    else:
        graph.add_edge("searcher", "synthesizer")

    graph.add_edge("synthesizer", "writer")
    graph.add_edge("writer", END)

    return graph.compile(checkpointer=checkpointer)
