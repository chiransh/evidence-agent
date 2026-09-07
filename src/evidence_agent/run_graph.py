import argparse
import sys

import anthropic

from evidence_agent.graph import build_graph


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Planner -> Searcher -> Synthesizer -> Writer graph on a question."
    )
    parser.add_argument("question", nargs="?", help="Question to research. Reads stdin if omitted.")
    args = parser.parse_args()

    question = args.question or sys.stdin.read().strip()
    if not question:
        parser.error("no question provided")

    graph = build_graph()
    try:
        result = graph.invoke({"question": question})
    except (TypeError, anthropic.AuthenticationError):
        parser.error("no valid Anthropic credentials found (set ANTHROPIC_API_KEY or run `ant auth login`)")
        return

    print(result["report"])


if __name__ == "__main__":
    main()
