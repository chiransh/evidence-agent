# Snippet or page: which one actually contains the evidence

100 key points from 18 questions, searched with the keyless Wikipedia backend, each result fetched in full. For every key point, the best lexical coverage in a snippet is compared with the best in the passages selected from a page. No model is involved, so this measures whether the evidence is reachable in what the judge is shown, not whether it supports the claim.

## What the judge sees

The control column is drawn from the same pages without looking at the key point, and is given at least as many characters as the selected passages it is compared with.

| | Snippet | Page passages | Control |
|---|---|---|---|
| Mean characters shown | 645 | 2,494 | 2,806 |
| Mean key-point coverage | 28% | 80% | 36% |
| Key points locatable | 16 of 100 | 86 of 100 | 19 of 100 |

Locatable means at least 60 percent of the key point's content words appear in one passage. The mean coverage row is given so the threshold can be second-guessed. The pages themselves average 106,461 characters, so the judge is shown a small fraction of one rather than the whole thing.

The page is worth fetching. 70 of 100 key points are locatable in the page and not in the snippet, against 0 the other way round. A judge shown only snippets would have had no way to confirm those points, and the honest verdict on a claim it could not see is unsupported, so the snippet version was understating citation support by construction.

Selection, not length: a slice of the page of at least the same size, chosen without seeing the key point, reaches 36 percent mean coverage and locates 19 of 100 points, against 80 percent and 86 for the targeted passages. The ranking is doing the work rather than the character budget, which is the objection this control exists to answer.

## Fetch outcomes

| Verdict | Sources |
|---|---|
| fetched | 54 |

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
| paris-agreement | Goal of limiting warming to well below 2 degrees Celsius, pursuing 1.5 degrees | 0% | 62% |
| paris-agreement | Countries set their own nationally determined contributions | 0% | 83% |
| paris-agreement | Contributions are meant to ratchet up over time | 20% | 80% |
| mrna-vaccines | Host cell ribosomes translate the mRNA into the protein | 50% | 83% |
| mrna-vaccines | The mRNA degrades quickly and does not alter host DNA | 12% | 75% |
| crispr-cas9 | Derived from a bacterial adaptive immune system | 40% | 100% |
| crispr-cas9 | The Cas9 enzyme cuts the DNA at that site | 40% | 100% |
| crispr-cas9 | Cell repair pathways then disable a gene or insert a new sequence | 33% | 89% |
| crispr-cas9 | Applications include research knockouts, gene therapy, and crop engineering | 25% | 75% |
| gdpr-provisions | Took effect in May 2018 and applies to personal data of people in the EU | 25% | 62% |
| gdpr-provisions | Requires a lawful basis for processing such as consent | 0% | 100% |
| gdpr-provisions | Principles of data minimisation and purpose limitation | 20% | 100% |
| gdpr-provisions | Individual rights including access, erasure, rectification, and portability | 14% | 71% |
| gdpr-provisions | Breach notification within 72 hours | 25% | 75% |
| gdpr-provisions | Fines up to 4 percent of global annual turnover or 20 million euros | 0% | 71% |
| transformer-architecture | Introduced in the 2017 paper Attention Is All You Need | 0% | 100% |
| transformer-architecture | Uses self-attention instead of recurrence | 0% | 100% |
| transformer-architecture | Handles long-range dependencies well and underpins modern large language models | 30% | 70% |
| quantum-entanglement | Measurement outcomes are correlated regardless of separation | 20% | 80% |
| quantum-entanglement | Correlations exceed what classical local theories allow, confirmed by Bell tests | 11% | 67% |
| quantum-entanglement | Does not permit faster-than-light communication | 29% | 86% |
| quantum-entanglement | Relevant to quantum computing and quantum cryptography | 25% | 100% |
| soviet-collapse | Nationalist and independence movements in the constituent republics | 20% | 100% |
| soviet-collapse | The failed August 1991 coup attempt | 40% | 100% |
| tcp-vs-udp | TCP guarantees delivery through acknowledgements and retransmission | 17% | 67% |
| tcp-vs-udp | TCP preserves ordering; UDP does not | 50% | 83% |
| tcp-vs-udp | UDP has lower overhead and latency | 25% | 75% |
| tcp-vs-udp | TCP suits web and file transfer; UDP suits streaming, voice, and DNS | 22% | 78% |
| inflation-causes | Demand-pull inflation from demand exceeding supply capacity | 33% | 67% |
| inflation-causes | Cost-push inflation from higher input costs or supply shocks | 38% | 88% |
| inflation-causes | Excessive money supply growth relative to output | 33% | 100% |
| inflation-causes | Inflation expectations becoming self-reinforcing | 20% | 60% |
| solar-pv | Uses semiconductor material, typically silicon | 0% | 100% |
| solar-pv | A p-n junction creates an internal electric field | 20% | 60% |
| solar-pv | Photons excite electrons into a conducting state, the photovoltaic effect | 29% | 71% |
| solar-pv | An inverter converts DC to AC for grid use | 50% | 100% |
| jwst-purpose | Launched in December 2021 | 33% | 100% |
| jwst-purpose | Studies the earliest galaxies and highly redshifted light | 17% | 67% |
| jwst-purpose | Studies star and planet formation within dust clouds | 14% | 86% |
| jwst-purpose | Characterises exoplanet atmospheres | 0% | 67% |
| sleep-deprivation | Impaired attention, memory, and reaction time | 20% | 100% |
| sleep-deprivation | Increased risk of cardiovascular disease and high blood pressure | 0% | 100% |
| sleep-deprivation | Impaired glucose metabolism and higher type 2 diabetes risk | 0% | 100% |
| sleep-deprivation | Weight gain and appetite hormone disruption | 0% | 100% |
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
| overfitting-underfitting | Remedies include regularisation, more data, or changing model complexity | 38% | 62% |
| federal-reserve-role | Dual mandate of maximum employment and price stability | 0% | 100% |
| federal-reserve-role | Sets the federal funds rate target | 20% | 100% |
| federal-reserve-role | Uses open market operations to implement policy | 17% | 83% |
| federal-reserve-role | Supervises and regulates banks | 33% | 100% |
| federal-reserve-role | Acts as lender of last resort in a crisis | 0% | 60% |
| federal-reserve-role | Supports the payment and clearing system | 25% | 75% |

## What this does not show

- Lexical coverage is not support. A passage containing every word of a claim can still contradict it, which is exactly why the judgment itself is left to a model.
- Wikipedia is unusually well structured and unusually fetchable. A run over the paid search backend's mix of news and vendor pages would fetch less cleanly, and the fetch outcomes above are the optimistic case.
- Key points stand in for cited claims. A real report's claims are narrower and phrased in its own words, which lexical matching handles less well than it handles these.
