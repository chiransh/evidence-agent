# Snippet or page: which one actually contains the evidence

143 key points from 28 questions, searched with the keyless Wikipedia backend, each result fetched in full. For every key point, the best lexical coverage in a snippet is compared with the best in the passages selected from a page. No model is involved, so this measures whether the evidence is reachable in what the judge is shown, not whether it supports the claim.

## What the judge sees

The control column is drawn from the same pages without looking at the key point, and is given at least as many characters as the selected passages it is compared with.

| | Snippet | Page passages | Control |
|---|---|---|---|
| Mean characters shown | 635 | 2,429 | 3,404 |
| Mean key-point coverage | 23% | 75% | 32% |
| Key points locatable | 16 of 143 | 110 of 143 | 20 of 143 |

Locatable means at least 60 percent of the key point's content words appear in one passage. The mean coverage row is given so the threshold can be second-guessed. The pages themselves average 107,342 characters, so the judge is shown a small fraction of one rather than the whole thing.

The page is worth fetching. 94 of 143 key points are locatable in the page and not in the snippet, against 0 the other way round. A judge shown only snippets would have had no way to confirm those points, and the honest verdict on a claim it could not see is unsupported, so the snippet version was understating citation support by construction.

Selection, not length: a slice of the page of at least the same size, chosen without seeing the key point, reaches 32 percent mean coverage and locates 20 of 143 points, against 75 percent and 110 for the targeted passages. The ranking is doing the work rather than the character budget, which is the objection this control exists to answer.

## Which ranking rule finds the evidence

All four rank the same passages from the same fetch; only the notion of a match differs. Scored on the same plain yardstick as everything above, so a rule cannot win by counting its own matches. The last two columns are paired against the plain rule point by point, since a net count of one or two hides whether nothing moved or a handful moved both ways.

| Ranking rule | Key points locatable | Mean coverage | Gained over plain | Lost against plain |
|---|---|---|---|---|
| weighted (in use) | 110 of 143 | 75% | 10 | 1 |
| plain | 101 of 143 | 72% | 0 | 0 |
| stemmed_weighted | 100 of 143 | 72% | 6 | 7 |
| stemmed | 98 of 143 | 70% | 2 | 5 |

weighted locates 9 more of 143 than the plain rule, gaining 10 and losing 1, so the extra matching rules earn their place and it is the rule in use.

## Fetch outcomes

| Verdict | Sources |
|---|---|
| fetched | 84 |

## Where they disagree

Key points one side reaches and the other does not.

| Question | Key point | Snippet | Page |
|---|---|---|---|
| supervised-vs-unsupervised | Supervised learning uses labelled input and output pairs | 57% | 86% |
| supervised-vs-unsupervised | Supervised learning predicts a target; unsupervised learning finds structure such as clusters | 33% | 78% |
| supervised-vs-unsupervised | Classification and regression are supervised; clustering and dimensionality reduction are unsupervised | 29% | 100% |
| financial-crisis-2008 | Subprime mortgage lending to borrowers who could not repay | 29% | 86% |
| financial-crisis-2008 | High leverage at banks turned losses into insolvency and a credit freeze | 38% | 62% |
| http3-vs-http2 | HTTP/3 uses QUIC over UDP; HTTP/2 uses TCP | 17% | 67% |
| paris-agreement | Adopted in 2015 under the UNFCCC | 25% | 100% |
| paris-agreement | Countries set their own nationally determined contributions | 0% | 83% |
| paris-agreement | Contributions are meant to ratchet up over time | 20% | 60% |
| mrna-vaccines | Host cell ribosomes translate the mRNA into the protein | 50% | 83% |
| mrna-vaccines | The immune system responds to that protein, creating antibodies and memory | 29% | 71% |
| mrna-vaccines | The mRNA degrades quickly and does not alter host DNA | 12% | 75% |
| crispr-cas9 | Derived from a bacterial adaptive immune system | 40% | 100% |
| crispr-cas9 | A guide RNA targets a specific DNA sequence | 50% | 100% |
| crispr-cas9 | Cell repair pathways then disable a gene or insert a new sequence | 33% | 89% |
| crispr-cas9 | Applications include research knockouts, gene therapy, and crop engineering | 25% | 75% |
| gdpr-provisions | Took effect in May 2018 and applies to personal data of people in the EU | 25% | 100% |
| gdpr-provisions | Requires a lawful basis for processing such as consent | 17% | 100% |
| gdpr-provisions | Principles of data minimisation and purpose limitation | 20% | 100% |
| gdpr-provisions | Individual rights including access, erasure, rectification, and portability | 14% | 71% |
| gdpr-provisions | Breach notification within 72 hours | 25% | 75% |
| gdpr-provisions | Fines up to 4 percent of global annual turnover or 20 million euros | 0% | 71% |
| transformer-architecture | Introduced in the 2017 paper Attention Is All You Need | 17% | 100% |
| transformer-architecture | Uses self-attention instead of recurrence | 0% | 80% |
| transformer-architecture | Parallelises training across sequence positions, unlike RNNs | 14% | 71% |
| transformer-architecture | Handles long-range dependencies well and underpins modern large language models | 0% | 70% |
| quantum-entanglement | Measurement outcomes are correlated regardless of separation | 20% | 80% |
| quantum-entanglement | Correlations exceed what classical local theories allow, confirmed by Bell tests | 11% | 67% |
| quantum-entanglement | Does not permit faster-than-light communication | 29% | 86% |
| quantum-entanglement | Relevant to quantum computing and quantum cryptography | 25% | 100% |
| soviet-collapse | Long-running economic stagnation and inefficiency of central planning | 43% | 71% |
| soviet-collapse | Heavy military spending and reliance on oil revenues that declined | 0% | 71% |
| soviet-collapse | Nationalist and independence movements in the constituent republics | 20% | 100% |
| soviet-collapse | The failed August 1991 coup attempt | 40% | 100% |
| tcp-vs-udp | TCP guarantees delivery through acknowledgements and retransmission | 17% | 83% |
| tcp-vs-udp | TCP preserves ordering; UDP does not | 50% | 83% |
| tcp-vs-udp | UDP has lower overhead and latency | 25% | 75% |
| tcp-vs-udp | TCP suits web and file transfer; UDP suits streaming, voice, and DNS | 22% | 78% |
| inflation-causes | Demand-pull inflation from demand exceeding supply capacity | 33% | 83% |
| inflation-causes | Cost-push inflation from higher input costs or supply shocks | 38% | 88% |
| inflation-causes | Excessive money supply growth relative to output | 33% | 100% |
| inflation-causes | Inflation expectations becoming self-reinforcing | 20% | 60% |
| solar-pv | Uses semiconductor material, typically silicon | 0% | 100% |
| solar-pv | A p-n junction creates an internal electric field | 20% | 80% |
| solar-pv | An inverter converts DC to AC for grid use | 50% | 100% |
| jwst-purpose | Launched in December 2021 | 33% | 100% |
| jwst-purpose | Studies the earliest galaxies and highly redshifted light | 17% | 67% |
| jwst-purpose | Studies star and planet formation within dust clouds | 14% | 86% |
| jwst-purpose | Characterises exoplanet atmospheres | 0% | 67% |
| sleep-deprivation | Impaired attention, memory, and reaction time | 20% | 100% |
| sleep-deprivation | Increased risk of cardiovascular disease and high blood pressure | 0% | 100% |
| sleep-deprivation | Impaired glucose metabolism and higher type 2 diabetes risk | 0% | 86% |
| sleep-deprivation | Weight gain and appetite hormone disruption | 0% | 80% |
| sleep-deprivation | Weakened immune function | 0% | 100% |
| sleep-deprivation | Higher risk of depression and anxiety | 0% | 100% |
| kubernetes-purpose | Schedules containers across a cluster of machines | 0% | 80% |
| kubernetes-purpose | Horizontal scaling of replicas | 33% | 67% |
| kubernetes-purpose | Service discovery and load balancing | 0% | 100% |
| kubernetes-purpose | Rolling updates and rollbacks | 0% | 67% |
| kubernetes-purpose | Declarative desired-state model reconciled by a control plane | 0% | 71% |
| overfitting-underfitting | Overfitting: good training performance, poor generalisation to unseen data | 25% | 75% |
| overfitting-underfitting | Overfitting means the model has learned noise in the training set | 57% | 71% |
| overfitting-underfitting | Underfitting: poor performance on both training and test data | 14% | 100% |
| overfitting-underfitting | Underfitting means the model is too simple for the underlying structure | 57% | 86% |
| overfitting-underfitting | Overfitting is high variance; underfitting is high bias | 20% | 100% |
| overfitting-underfitting | Remedies include regularisation, more data, or changing model complexity | 38% | 75% |
| federal-reserve-role | Dual mandate of maximum employment and price stability | 0% | 100% |
| federal-reserve-role | Sets the federal funds rate target | 20% | 100% |
| federal-reserve-role | Uses open market operations to implement policy | 17% | 100% |
| federal-reserve-role | Supervises and regulates banks | 33% | 100% |
| federal-reserve-role | Acts as lender of last resort in a crisis | 0% | 80% |
| federal-reserve-role | Supports the payment and clearing system | 25% | 75% |
| photosynthesis-basics | The captured energy is used to build simple sugars the plant lives on | 25% | 62% |
| photosynthesis-basics | Oxygen leaves the plant as a leftover of the process | 20% | 80% |
| herd-immunity | An infection that cannot find a susceptible host stops spreading | 14% | 71% |
| herd-immunity | The share of a population that must be immune rises with how easily the disease passes between people | 20% | 70% |
| herd-immunity | People who cannot be vaccinated are shielded indirectly by those around them | 29% | 71% |
| herd-immunity | Protection is a property of the group rather than of any one person | 25% | 88% |
| rates-and-inflation | Slower demand takes the pressure off prices | 0% | 67% |
| rates-and-inflation | The effect arrives long after the decision, so policy is set on forecasts | 12% | 62% |
| rates-and-inflation | Overdoing it costs output and jobs | 0% | 75% |
| browser-address-lookup | The name is first turned into a numeric address | 20% | 80% |
| browser-address-lookup | The document points at further files that are fetched before the page is drawn | 12% | 75% |
| antibiotic-resistance | Survivors of treatment are the ones that reproduce, so the survivable trait becomes common | 12% | 62% |
| antibiotic-resistance | Bacteria also hand these traits to other bacteria directly | 33% | 83% |
| antibiotic-resistance | Every course given when it was not needed adds to the pressure | 14% | 71% |
| antibiotic-resistance | Replacement drugs arrive more slowly than the problem spreads | 12% | 62% |
| saving-early | Each period's gain joins the sum that earns the next one | 0% | 62% |
| saving-early | Money put in decades earlier passes through far more periods of growth | 10% | 60% |
| greenhouse-warming | Incoming light passes through the air and heats the ground | 29% | 86% |
| greenhouse-warming | The warmed ground sends energy back out at longer wavelengths | 0% | 75% |
| greenhouse-warming | Certain gases soak up part of that outgoing energy and send some of it back down | 20% | 60% |
| greenhouse-warming | A warmer atmosphere holds more water vapour, which does the same thing and enlarges the effect | 27% | 73% |
| two-tides-a-day | The Moon pulls harder on the near side of the Earth than on the far side | 25% | 75% |

## Split by subset

The core questions' key points were written in the vocabulary the sources use. The paraphrase questions' key points state equally well documented facts in deliberately different wording. Every figure below is on the same plain yardstick.

| Subset | Key points | Locatable in snippet | Locatable in page | Only in page |
|---|---|---|---|---|
| core | 100 | 16 | 88 | 72 |
| paraphrase | 43 | 0 | 22 | 22 |

| Subset | plain | stemmed | weighted | stemmed_weighted |
|---|---|---|---|---|
| core | 85 of 100 | 83 of 100 | 88 of 100 | 85 of 100 |
| paraphrase | 16 of 43 | 15 of 43 | 22 of 43 | 15 of 43 |

Paraphrasing the key points costs 37 points of page locatability (88 percent of the core points against 51 percent of the paraphrased ones), which is the sample working as intended: these are the claims lexical matching is supposed to find hardest. On this subset the rules do separate: weighted locates 22 of 43 against the plain rule's 16, which is the case the extra matching was built for and the first evidence for adopting it.


## What this does not show

- Lexical coverage is not support. A passage containing every word of a claim can still contradict it, which is exactly why the judgment itself is left to a model.
- Wikipedia is unusually well structured and unusually fetchable. A run over the paid search backend's mix of news and vendor pages would fetch less cleanly, and the fetch outcomes above are the optimistic case.
- Key points stand in for cited claims. A real report's claims are narrower and phrased in its own words, which lexical matching handles less well than it handles these.
- The figures move between runs. Repeated runs put the core subset's page column between 85 and 87 of its 100 key points, because the search results and the pages behind them are live and edited. Differences smaller than that are not results, which is why the ranking rules were left alone until a subset separated them by more.
- The paraphrased subset was written by the same person as the ranking rules, and written after them, to create a case the plain rule should struggle with. It succeeded at that, and that is also its weakness: a subset built to expose a gap is not independent evidence that the gap matters in production. What would be independent is the same measurement over claims a real run actually cited, which needs the paid backend and a key.
