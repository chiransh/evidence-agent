# evidence-agent

A citation-backed research agent with an evaluation harness: not just "search and summarize," but a system that scores its own citation accuracy, factual grounding, and answer completeness against a held-out question set.

## Problem

Most LLM research agents produce fluent answers with unverifiable or fabricated citations. There's rarely an honest measurement of whether the sources cited actually support the claims made, or how often the agent hallucinates, loops, or fails outright. This project builds a multi-agent research pipeline (Planner, Searcher, Synthesizer, Writer) plus the differentiator: an eval harness that measures citation validity, coverage, and grounding, plus a documented log of failure modes.

## Architecture

Flow (LangGraph orchestration):

```
Question -> Planner -> Searcher -> Credibility -> Synthesizer -> Writer -> Report
```

- **Planner**: decomposes the question into sub-questions.
- **Searcher**: runs each sub-question against a pluggable search backend.
- **Credibility**: scores each source on domain reputation and judged relevance, then reorders. See [notes/credibility.md](notes/credibility.md).
- **Synthesizer**: composes findings into claims, each traceable to a source, and drops any citation whose URL was not actually retrieved.
- **Writer**: renders the report with inline `[1][2]` citations and a sources list.

Cross-cutting: typed errors that separate retryable from not, per-node retries, and SQLite checkpointing so a run that dies partway resumes instead of re-paying for earlier model calls.

## Usage

```bash
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=...   # web search works keyless at low rate limits

evidence-agent research "What caused the 2008 global financial crisis?"
evidence-agent research "..." --no-credibility        # the variant the eval compares against
evidence-agent research "..." --checkpoint-db runs.sqlite --thread-id q1   # resumable

evidence-agent ask "..."       # one model call, no tools: the floor to beat
evidence-agent search "..."    # search then summarize, no planning
```

Demo UI:

```bash
streamlit run streamlit_app.py
```

It shows the report next to what was retrieved, with sources cited and sources merely retrieved distinguished, because the gap between those two is the most useful thing to see when judging one of these.

## Engineering decisions

Why this chunking, why this model, how it's evaluated, what would change for production.

## Evaluation

Held-out research questions with reference answers, scored on citation validity, coverage, and answer completeness. Results in `evals/results/`.

## Known failure modes

Hallucinated citations, planning loops, fabricated sources, logged as they're found.

## License

MIT, see [LICENSE](LICENSE).
