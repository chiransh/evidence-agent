# evidence-agent: a research agent that can be checked

A plain-language summary of what this project does and how it is measured. The
[README](README.md) is the technical version.

## The problem

Language models write confident research summaries with citations that often
cannot be checked, and sometimes point at pages that do not exist or do not say
what was claimed. For anything a business will act on, the useful question is not
whether the answer reads well. It is:

- How often are the cited sources real?
- How often does a source actually support the sentence attached to it?
- How much of a good answer is missing?

A demo showing one good answer cannot tell you any of that.

## What it does

Given a research question, it splits the question into searchable parts, runs
those searches at the same time, scores each source for credibility and
relevance, writes claims tied to specific sources, and renders a report with
numbered citations.

Two design decisions matter more than the pipeline itself.

**Invented citations are deleted in code, not discouraged in a prompt.** Any
citation the model produces that was not in the retrieved search results is
discarded before the report is written. Asking a model not to invent sources is a
request; removing the invented ones is a guarantee.

**Search keeps working when the provider does not.** The primary search provider
is rate limited on its free tier, so when it refuses, the agent falls back to a
keyless source automatically and labels which source each result came from. It
deliberately does not fall back when the API key itself is wrong, because
silently degrading every answer would hide a broken configuration.

## How it is measured

A grading harness runs the agent over 18 hand-written reference questions and
records four things per answer:

1. **Do the cited URLs exist**, checked by fetching every one of them.
2. **Does each source support its claim**, judged against the cited page itself.
3. **How much of a known good answer is covered**, against reference key points.
4. **Answer length**, as a control, since coverage can otherwise be won by
   writing more rather than by answering better.

Citation accuracy is deliberately two numbers rather than one. "The agent
invented a URL" and "the URL is real but does not say this" are different
failures with different fixes, and averaging them hides which is happening. A
third state matters too: plenty of real sites refuse automated requests, and
counting those as broken citations would punish the agent for citing reputable
sources that block crawlers, so they are reported separately and left out of the
score.

Comparing two versions of the agent is done question by question with a
confidence interval, and the report says "inconclusive" when 18 questions cannot
separate them rather than quoting a difference that is really noise.

### Checking a citation against the page, not the search result

The natural shortcut is to grade a claim against the one or two sentences the
search engine shows under a result. It is also wrong in both directions: a
snippet that happens to restate the claim passes a citation nobody read, and a
page that makes the point three paragraphs lower fails a citation that was
correct.

So each cited page is fetched and the parts of it that bear on the claim are what
gets graded. That is a claim about the data, so it was measured rather than
assumed, and it needs no paid API: over 100 reference points drawn from 54 real
pages, 86 were findable in the fetched page against 16 in the search snippet, and
70 were findable in the page and in no snippet at all. None went the other way.
Grading those 70 on snippets would have marked correct citations as unsupported.

Because the obvious objection is that more text contains more words, the same
test includes a control: a comparable amount of each page picked without knowing
what was being looked for finds 19 of 100, fewer than the snippets. The targeting
is doing the work.

## Status, stated plainly

The pipeline, the grading harness and the comparison tool are built and tested.
**The scored results table is not filled in yet.** Running all 18 questions
through both versions of the agent takes roughly 200 model API calls, and that
run is pending.

There are no placeholder figures anywhere in this repository. For a project whose
argument is that others skip honest measurement, inventing the measurement would
be the one unrecoverable mistake.

## Production handling

- Failures are typed by whether retrying could possibly help, and only those are
  retried. A missing API key fails immediately with one clear line instead of
  three slow attempts.
- A run can checkpoint and resume, so an interrupted job does not pay twice for
  work it already did.
- Sub-question searches and source scoring run concurrently: four sub-questions
  went from 1.71 seconds to 0.37.

## Stack

Python, LangGraph, Claude API with structured outputs, Tavily search with a
keyless Wikipedia fallback, Pydantic, SQLite checkpointing, Streamlit demo.
107 automated tests, run on every commit.

## For engineers

- [README](README.md) covers the architecture and the engineering decisions.
- [notes/evaluation.md](notes/evaluation.md) covers what the harness measures and
  its known weaknesses, including that the judges share a model family with the
  agent.
- [notes/credibility.md](notes/credibility.md) covers how sources are scored.
- [evals/snippet-vs-page.md](evals/snippet-vs-page.md) is the page-against-snippet
  measurement, generated from the run rather than written by hand.
