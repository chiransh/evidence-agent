"""Single LLM call, no tools: the floor the rest of the pipeline has to beat."""

import argparse
import sys

import anthropic

MODEL = "claude-opus-5"


def ask(question: str) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
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
    except (TypeError, anthropic.AuthenticationError):
        parser.error("no valid Anthropic credentials found (set ANTHROPIC_API_KEY or run `ant auth login`)")


if __name__ == "__main__":
    main()
