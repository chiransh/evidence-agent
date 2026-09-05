from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from evidence_agent.planner import planner_node
from evidence_agent.searcher import searcher_node
from evidence_agent.state import ResearchState


def build_graph() -> CompiledStateGraph:
    graph = StateGraph(ResearchState)
    graph.add_node("planner", planner_node)
    graph.add_node("searcher", searcher_node)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "searcher")
    graph.add_edge("searcher", END)
    return graph.compile()
