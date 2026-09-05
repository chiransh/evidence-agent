import argparse
import sys

import anthropic

from evidence_agent.graph import build_graph


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Planner -> Searcher graph on a question.")
    parser.add_argument("question", nargs="?", help="Question to research. Reads stdin if omitted.")
    args = parser.parse_args()

    question = args.question or sys.stdin.read().strip()
    if not question:
        parser.error("no question provided")

    graph = build_graph()
    try:
        result = graph.invoke({"question": question, "sub_questions": [], "search_results": {}})
    except (TypeError, anthropic.AuthenticationError):
        parser.error("no valid Anthropic credentials found (set ANTHROPIC_API_KEY or run `ant auth login`)")
        return

    print("Sub-questions:")
    for i, sub_question in enumerate(result["sub_questions"], 1):
        n_results = len(result["search_results"].get(sub_question, []))
        print(f"  {i}. {sub_question}  ({n_results} results)")


if __name__ == "__main__":
    main()
