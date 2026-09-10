"""Single LLM call, no tools: the floor the rest of the pipeline has to beat."""

import argparse
import sys

from evidence_agent.exceptions import EvidenceAgentError
from evidence_agent.llm import MODEL, client, model_errors


def ask(question: str) -> str:
    with model_errors():
        response = client().messages.create(
            model=MODEL,
            max_tokens=16000,
            messages=[{"role": "user", "content": question}],
        )
    return next(block.text for block in response.content if block.type == "text")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask a single question, no tools, no citations.")
    parser.add_argument("question", nargs="?", help="Question to ask. Reads stdin if omitted.")
    args = parser.parse_args()

    question = args.question or sys.stdin.read().strip()
    if not question:
        parser.error("no question provided")

    try:
        print(ask(question))
    except EvidenceAgentError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
