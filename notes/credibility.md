# Credibility scoring

## What it does

Every search result gets a credibility score between 0 and 1, computed from two signals:

1. **Domain reputation** (`domain_score`): a lookup table of known-reputable domains
   (Wikipedia, arXiv, Nature, major wire services and newspapers) plus a blanket score
   for `.gov` and `.edu` hosts. Anything not in the table gets a neutral default score
   of 0.5, not a penalty, since an unfamiliar domain is not the same thing as an
   unreliable one.
2. **LLM-judged relevance** (`judge_relevance`): a single structured-output call per
   sub-question that rates how directly each of its results actually helps answer that
   sub-question, from 0 to 1.

The two combine as a weighted average: `0.4 * domain_score + 0.6 * relevance`.
Relevance is weighted higher than domain reputation on purpose. A highly reputable
source that doesn't actually address the question is still not useful evidence, and a
mediocre-reputation source that directly answers it is more useful than a top-tier
source that doesn't. Domain reputation is a light prior, not a gate.

## Where it runs

The credibility node sits between Searcher and Synthesizer. It scores and re-sorts each
sub-question's results in place, so Synthesizer sees the most credible results first for
each sub-question without any hard filtering or dropped results. Nothing gets discarded
here. A low-scoring result is still available to Synthesizer; it is just no longer
first in line.

## Why not just an LLM score, or just a domain table

A domain table alone can't tell "reputable but off-topic" from "reputable and directly
on-topic," which matters more for a research agent than source reputation by itself.
An LLM score alone has no memory of which sources have a track record and which don't,
and it is also the more failure-prone half of the combination (see below), so leaning on
it exclusively would make the whole score only as reliable as a single model call.
Combining both means neither failure mode dominates.

## Known limitations

- The domain table is small and manually curated. It will misjudge any reputable
  source it doesn't happen to list, hence the neutral (not punitive) default.
- `judge_relevance` is a single LLM call per sub-question with no retry or
  cross-check. A bad judgment here silently reorders results rather than raising an
  error, since there's no ground truth to validate against inline. This is the sort
  of failure the eval harness is meant to catch, not something this node can catch
  on its own.
- Re-sorting by credibility is a soft signal, not a filter. If every result for a
  sub-question happens to be low credibility, Synthesizer still sees all of them; this
  node does not decide that a sub-question has no good sources.
