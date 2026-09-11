# Evaluation harness

## What gets measured

18 research questions in `evals/dataset.json`, each with a hand-written
reference answer and a list of key points. For every question the harness runs
the agent and records four things.

**Citation validity, part one: does the URL exist.** Every cited URL is
fetched. A 2xx or 3xx counts as live, a 404 or similar counts as dead, and a
DNS or connection failure counts as unreachable. This is checked against the
real network, not mocked, because a checker that called everything live would
score a fabricated citation as valid and nothing would catch it.

**Citation validity, part two: does the source support the claim.** For each
finding, a model judge sees the claim next to the text of the source it cites
and decides whether that text actually supports it, as opposed to merely
being on the same topic.

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
