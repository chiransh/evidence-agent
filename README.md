# evidence-agent

A citation-backed research agent with an evaluation harness: not just "search and summarize," but a system that scores its own citation accuracy, factual grounding, and answer completeness against a held-out question set.

## Problem

Most LLM research agents produce fluent answers with unverifiable or fabricated citations. There's rarely an honest measurement of whether the sources cited actually support the claims made, or how often the agent hallucinates, loops, or fails outright. This project builds a multi-agent research pipeline (Planner, Searcher, Synthesizer, Writer) plus the differentiator: an eval harness that measures citation validity, coverage, and grounding, plus a documented log of failure modes.

## Architecture

Flow (LangGraph orchestration):

```
Question -> Planner -> Searcher -> Synthesizer -> Writer -> Report (with inline citations)
```

- **Planner**: decomposes the question into sub-questions.
- **Searcher**: runs each sub-question against a pluggable search backend.
- **Synthesizer**: composes findings into a coherent set of claims, each traceable to a source.
- **Writer**: renders a final report with inline `[1][2]` citations and a sources list.

Cross-cutting concerns: credibility scoring, checkpointing, typed errors/retries, circuit breakers.

## Engineering decisions

Why this chunking, why this model, how it's evaluated, what would change for production.

## Evaluation

Held-out research questions with reference answers, scored on citation validity, coverage, and answer completeness. Results in `evals/results/`.

## Known failure modes

Hallucinated citations, planning loops, fabricated sources, logged as they're found.

## License

MIT, see [LICENSE](LICENSE).
