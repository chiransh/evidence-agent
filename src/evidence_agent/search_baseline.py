"""Search + summarize: one search call, one LLM call, still no planning or
multi-step orchestration. The step between the single-call baseline and the
LangGraph pipeline."""

import argparse
import sys

import anthropic

from evidence_agent.search import SearchBackend, TavilySearchBackend

MODEL = "claude-opus-5"


def search_and_summarize(question: str, backend: SearchBackend | None = None) -> str:
    backend = backend or TavilySearchBackend()
    results = backend.search(question)

    if not results:
        return "No search results found for this question."

    sources = "\n\n".join(
        f"[{i + 1}] {r.title} ({r.url})\n{r.snippet}" for i, r in enumerate(results)
    )

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=(
            "Answer the user's question using only the search results provided. "
            "Reference sources by their [n] number where relevant. If the results "
            "don't support an answer, say so instead of guessing."
        ),
        messages=[
            {
                "role": "user",
                "content": f"Question: {question}\n\nSearch results:\n{sources}",
            }
        ],
    )
    return next(block.text for block in response.content if block.type == "text")


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the web, then summarize the results.")
    parser.add_argument("question", nargs="?", help="Question to ask. Reads stdin if omitted.")
    args = parser.parse_args()

    question = args.question or sys.stdin.read().strip()
    if not question:
        parser.error("no question provided")

    try:
        print(search_and_summarize(question))
    except (TypeError, anthropic.AuthenticationError):
        parser.error("no valid Anthropic credentials found (set ANTHROPIC_API_KEY or run `ant auth login`)")


if __name__ == "__main__":
    main()
