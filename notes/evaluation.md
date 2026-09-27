# Evaluation harness

## What gets measured

18 research questions in `evals/dataset.json`, each with a hand-written
reference answer and a list of key points. For every question the harness runs
the agent and records four things.

**Citation validity, part one: does the URL exist.** Every cited URL is
fetched. A 2xx or 3xx counts as live, a 404 or similar counts as dead, and a
DNS or connection failure counts as unreachable. This is checked against the
real network, not mocked, because a checker that called everything live would
score a fabricated citation as valid and nothing would catch it. It is the same
fetch that gives the support judge its text, since requesting every citation
twice to learn things one request already answered is waste, not rigour.

**Citation validity, part two: does the source support the claim.** For each
finding, a model judge sees the claim next to the text of the source it cites
and decides whether that text actually supports it, as opposed to merely
being on the same topic. What counts as "the text of the source" is a decision
with its own section below.

Splitting these two apart matters. The Synthesizer already drops any citation
whose URL was not in the retrieved search results, so "the agent invented a URL
from nothing" should be near zero by construction. The failure still available
to the agent is subtler: citing a real, retrieved page that does not actually
say what the report claims. Reporting one blended "citation accuracy" number
would hide which of the two is happening.

**Coverage.** A model judge decides which of the reference answer's key points
the report actually makes, in any wording. The score is the fraction covered,
and the missed points are recorded per question so a low score can be read
rather than just noted.

**Answer length.** Word and character count. Not a quality measure on its own,
but a control: coverage can be bought with verbosity, and a variant that scores
better on coverage while tripling in length has not necessarily improved.

## What the support judge is shown

The judge used to see the search result snippet, which is one or two sentences
the search engine chose for its own purposes. That biases the metric in both
directions. A snippet that happens to restate the claim scores the citation as
supported without the page ever being read. A page that states the claim three
paragraphs below the snippet scores as unsupported, and the report is penalised
for a citation that was correct.

So the cited page is fetched, converted to text, split into passages, and the
passages overlapping the claim most are what the judge sees, in the page's own
reading order rather than in score order: passages shuffled out of order read as
a different argument from the one the page makes.

Selection is lexical and deterministic, not a model call. Having a model pick
the evidence that another model then grades would nest one judgment inside
another, and a support rate would no longer say which of the two it measured.

### Measuring whether the fetch was worth it

This is a claim about the data, so `evidence-agent snippet-check` tests it
instead of asserting it, and needs no API key: it searches with the keyless
Wikipedia backend and uses the dataset's own key points in place of cited
claims. Results in `evals/snippet-vs-page.md`.

Over 100 key points from 54 fetched pages, 86 were locatable in the selected
passages against 16 in the snippet, and 70 were reachable in the page while
reachable in no snippet. None went the other way. The honest verdict on evidence
the judge cannot see is unsupported, so the snippet version was understating
support by construction.

The objection to that is length: selected passages average 2,494 characters
against a snippet's 645, so they would contain more of a claim's words even if
the ranking were picking at random. The control is a slice of the same page drawn
without seeing the key point, given at least as many characters as the selection
it is compared with. It locates 19 of 100, below even the snippets, so the
ranking is doing the work rather than the character budget.

What this does not show: lexical coverage is not support, and a passage
containing every word of a claim can still contradict it, which is why the
judgment itself stays with a model. Wikipedia is also unusually fetchable, so
the fetch outcomes here are the optimistic case.

### When the page cannot be read

Blocked, dead, non-HTML and cookie-wall pages fall back to the snippet, each
with its reason recorded, and every run reports the share of claims judged from
page content next to the support rate itself. A support rate resting mostly on
snippets is a weaker measurement than one resting on pages, and that difference
should be visible without rerunning anything.

A non-HTML response is never run through the text extractor. A PDF put through
it comes out as noise, and the judge would then grade a claim against the noise
rather than against the document.

## Three states for a URL, not two

Plenty of real sites answer an automated request with 403 or 429. That says
nothing about whether the citation was genuine, so blocked URLs are counted
separately and excluded from the denominator of the live rate rather than
scored either way. A question whose citations were all blocked reports no rate
at all instead of a perfect one. The same rule applies upward: aggregates
ignore missing rates rather than reading them as zero, so an eval where the
judge had nothing to score does not silently look like a failure.

## Errors are results

A question whose pipeline run raises is recorded with its error and the harness
carries on. Aborting the whole run on the first failure would hide how the
agent behaves on the remaining questions, and the error list is a finding in
its own right, not noise to be cleaned up before reporting.

## Known weaknesses

- **The reference answers are the weakest link.** They encode one author's view
  of what a good answer covers. Coverage scores are only as trustworthy as that
  list, and a point I did not think to include cannot be credited.
- **The judges are the same model family as the agent.** A model grading output
  from its own family may share its blind spots, and may be more generous to
  phrasing it would itself have produced. An independent judge, or a human
  spot check of a sample, would be the honest next step.
- **No inter-rater reliability.** Each judgment is a single model call with no
  second opinion and no measure of how stable it is across runs. Re-running the
  same eval will not give byte-identical scores.
- **18 questions is small.** Differences of a few percentage points between
  variants are inside the noise this sample size can resolve, and should not be
  reported as improvements.
- **Coverage rewards matching a fixed answer.** An agent that surfaces a
  correct and important point absent from the key point list gets no credit
  for it.

## Running it, and comparing two variants

The harness scores one build of the agent at a time. `--variant full` includes
the credibility node, `--variant no-credibility` drops it, which is the pair
worth comparing: the credibility node costs an extra model call per
sub-question, so it should have to show that it buys something.

```
evidence-agent eval --variant no-credibility --out evals/results/eval-no-credibility.json
evidence-agent eval --variant full           --out evals/results/eval-full.json
evidence-agent compare evals/results/eval-no-credibility.json evals/results/eval-full.json
```

The compare step writes `evals/comparison.md`.

## Why the comparison is paired, with an interval

Reporting two aggregate coverage numbers side by side invites a conclusion this
sample cannot support. Both runs answer the same 18 questions, and those
questions differ from each other far more than the two variants do, so the
comparison is done per question and the mean paired difference carries a
bootstrap 95 percent confidence interval.

When that interval includes zero the report says so and names no winner. Three
distinct outcomes are kept apart on purpose:

- **Separated**: the interval excludes zero, so the difference is larger than
  the question-to-question noise here.
- **Inconclusive**: the interval spans zero. The sample cannot separate the
  variants. This is a real finding about the experiment's resolution, not a
  gap to be filled by quoting the raw difference anyway.
- **Identical**: the two runs scored every shared question the same. A measured
  null result, which is not the same claim as inconclusive.

## Status of the measured numbers

The harness, the metrics, and the comparison are implemented and tested. The
numbers themselves have not been produced: every question in a real run needs
model calls for planning, synthesis, credibility scoring, and both judges, and
that requires an `ANTHROPIC_API_KEY` which the machine this was developed on
does not have. A run of both variants over all 18 questions is roughly 200
model calls in total.

No placeholder or illustrative figures are committed anywhere in this repo. For
a project whose argument is that portfolio agents skip honest measurement,
inventing the measurement would be the one unrecoverable mistake. `evals/`
holds the question set and the tooling; it will hold `comparison.md` and the
two result files once the runs happen.
