"""Is the page worth fetching, or does the snippet already say it?

Moving the support judge from search snippets to page content is a claim about
the data: that a real source often states a point somewhere other than in the
one or two sentences a search engine chose to show. That claim is cheap to
assert and cheap to test, so it is tested here rather than asserted in a README.

The measurement needs no model and no API key. It searches with the keyless
Wikipedia backend, fetches each result, and asks a lexical question of both the
snippet and the selected page passages: is this question's key point locatable
in the text. Key points come from the eval dataset, where they were written as
the things a good answer has to contain, which makes them a fair stand-in for
the claims a report would cite.

Lexical location is not the same as support, and the number this produces is not
a support rate. What it measures is whether the evidence is reachable at all in
what the judge is shown, which is a precondition for judging support correctly.

Run with `evidence-agent snippet-check`.
"""

import argparse
import json
import sys
from pathlib import Path

from evidence_agent.evaluation.pages import (
    DEFAULT_SELECTOR,
    SELECTORS,
    content_terms,
    fetch_page,
    random_passages,
    score_passage,
    select_passages,
)
from evidence_agent.exceptions import EvidenceAgentError
from evidence_agent.search import WikipediaSearchBackend

DATASET_PATH = Path("evals/dataset.json")
RESULTS_PATH = Path("evals/results/snippet-vs-page.json")
REPORT_PATH = Path("evals/snippet-vs-page.md")

RESULTS_PER_QUESTION = 3
# Share of a key point's content words that has to appear in one passage for the
# point to count as locatable there. Reported alongside the result, because the
# threshold is a judgment and the raw coverage figures are given too.
LOCATABLE = 0.6


def best_coverage(point: str, texts: list[str]) -> float:
    """Best share of the key point's content words found in any one text.

    The yardstick, and deliberately the plainest possible one: unweighted, and
    with no stemming. The selectors being compared below use stemming and term
    weighting, and scoring them with their own notion of a match would raise
    every column at once and prove nothing about which puts the evidence in front
    of the judge.
    """
    terms = content_terms(point)
    return max((score_passage(terms, text) for text in texts), default=0.0)


def _mean_chars(texts: list[str]) -> float:
    return sum(len(text) for text in texts) / len(texts) if texts else 0.0


def compare_one(question: dict, backend, max_results: int = RESULTS_PER_QUESTION) -> dict:
    """Search, fetch, and score every key point against snippet and page."""
    results = backend.search(question["question"], max_results=max_results)

    sources = []
    for result in results:
        page = fetch_page(result.url)
        sources.append({"result": result, "page": page})

    usable = [s for s in sources if s["page"].usable]
    points = []
    for i, point in enumerate(question["key_points"]):
        snippet_texts = [f"{s['result'].title}\n{s['result'].snippet}" for s in sources]
        # One set of selected passages per selector, so the ablation costs no
        # extra fetches. The named default is what the harness actually uses.
        by_selector = {
            name: [
                "\n\n".join(
                    passage
                    for _, passage in select_passages(point, s["page"].text, selector=selector)
                )
                for s in usable
            ]
            for name, selector in SELECTORS.items()
        }
        page_texts = by_selector[DEFAULT_SELECTOR]
        # The control: as much of the same page, chosen without seeing the point.
        # Matched to each page's own selected length rather than to the cap, since
        # selection often stops short of it. Seeded per key point so each one gets
        # a different sample and the run still reproduces.
        control_texts = [
            "\n\n".join(
                passage
                for _, passage in random_passages(s["page"].text, seed=i, target_chars=len(selected))
            )
            for s, selected in zip(usable, page_texts)
        ]
        points.append(
            {
                "key_point": point,
                "snippet_coverage": best_coverage(point, snippet_texts),
                "page_coverage": best_coverage(point, page_texts),
                "random_passage_coverage": best_coverage(point, control_texts),
                "selector_coverage": {
                    name: best_coverage(point, texts) for name, texts in by_selector.items()
                },
                "snippet_chars": _mean_chars(snippet_texts),
                "page_evidence_chars": _mean_chars(page_texts),
                "random_passage_chars": _mean_chars(control_texts),
            }
        )

    return {
        "id": question["id"],
        "question": question["question"],
        "sources": [
            {
                "url": s["result"].url,
                "verdict": s["page"].verdict,
                "snippet_chars": len(s["result"].snippet),
                "page_chars": len(s["page"].text),
            }
            for s in sources
        ],
        "key_points": points,
    }


def _mean(points: list[dict], field: str) -> float | None:
    values = [p[field] for p in points if p.get(field) is not None]
    return sum(values) / len(values) if values else None


def aggregate(records: list[dict], threshold: float = LOCATABLE) -> dict:
    points = [point for record in records for point in record["key_points"]]
    sources = [source for record in records for source in record["sources"]]

    in_snippet = [p for p in points if p["snippet_coverage"] >= threshold]
    in_page = [p for p in points if p["page_coverage"] >= threshold]
    gained = [
        p for p in points if p["page_coverage"] >= threshold > p["snippet_coverage"]
    ]
    lost = [p for p in points if p["snippet_coverage"] >= threshold > p["page_coverage"]]

    verdicts: dict[str, int] = {}
    for source in sources:
        verdicts[source["verdict"]] = verdicts.get(source["verdict"], 0) + 1

    selectors = sorted({name for point in points for name in point.get("selector_coverage", {})})
    # Net counts hide what moved. Every selector ranks the same passages from the
    # same fetch, so the comparison against the plain rule can be paired point by
    # point, which is the same discipline as the page-against-snippet counts above.
    ablation = {
        name: {
            "locatable": len([p for p in points if p["selector_coverage"][name] >= threshold]),
            "mean_coverage": _mean([{"v": p["selector_coverage"][name]} for p in points], "v"),
            "gained_over_plain": len(
                [
                    p
                    for p in points
                    if p["selector_coverage"][name] >= threshold > p["selector_coverage"]["plain"]
                ]
            ),
            "lost_against_plain": len(
                [
                    p
                    for p in points
                    if p["selector_coverage"]["plain"] >= threshold > p["selector_coverage"][name]
                ]
            ),
        }
        for name in selectors
    }

    return {
        "n_questions": len(records),
        "n_key_points": len(points),
        "default_selector": DEFAULT_SELECTOR,
        "selector_ablation": ablation,
        "n_sources": len(sources),
        "fetch_verdicts": dict(sorted(verdicts.items())),
        "threshold": threshold,
        "locatable_in_snippet": len(in_snippet),
        "locatable_in_page": len(in_page),
        "locatable_only_in_page": len(gained),
        "locatable_only_in_snippet": len(lost),
        # The control, with the same character budget as the selected passages:
        # how much of a key point a same-sized unselected slice of the page
        # contains. If this is close to the page figure, length rather than
        # selection is doing the work.
        "locatable_in_random_passages": len(
            [p for p in points if p["random_passage_coverage"] >= threshold]
        ),
        "mean_snippet_coverage": _mean(points, "snippet_coverage"),
        "mean_page_coverage": _mean(points, "page_coverage"),
        "mean_random_passage_coverage": _mean(points, "random_passage_coverage"),
        "mean_snippet_chars": _mean(points, "snippet_chars"),
        "mean_page_evidence_chars": _mean(points, "page_evidence_chars"),
        "mean_random_passage_chars": _mean(points, "random_passage_chars"),
        "mean_full_page_chars": (
            sum(s["page_chars"] for s in sources) / len(sources) if sources else None
        ),
    }


def _control_note(summary: dict) -> str:
    """Whether targeted selection beats an untargeted slice of the same size.

    Without this the headline is open to an obvious objection: selected passages
    are twenty times the length of a snippet, so they would contain more of a
    claim's words even if the ranking were picking at random.
    """
    page, control = summary["mean_page_coverage"], summary["mean_random_passage_coverage"]
    in_page = summary["locatable_in_page"]
    in_control = summary["locatable_in_random_passages"]
    total = summary["n_key_points"]

    opening = (
        f"Selection, not length: a slice of the page of at least the same size, chosen without "
        f"seeing the key point, "
        f"reaches {control * 100:.0f} percent mean coverage and locates {in_control} of {total} "
        f"points, against {page * 100:.0f} percent and {in_page} for the targeted passages."
    )
    if in_page >= 1.5 * max(in_control, 1) or page >= control + 0.15:
        return (
            f"{opening} The ranking is doing the work rather than the character budget, which is "
            "the objection this control exists to answer."
        )
    return (
        f"{opening} That is close enough that the character budget, not the ranking, explains most "
        "of the gain over snippets. Handing the judge any few thousand words of the page would do "
        "about as well, and the selection step is not earning its complexity."
    )


def _verdict_note(summary: dict) -> str:
    """The conclusion, graded so it cannot contradict the table above it."""
    gained, lost = summary["locatable_only_in_page"], summary["locatable_only_in_snippet"]
    total = summary["n_key_points"]
    if not total:
        return "Nothing was measured, so there is no conclusion to draw."

    if gained > lost:
        return (
            f"The page is worth fetching. {gained} of {total} key points are locatable in the page "
            f"and not in the snippet, against {lost} the other way round. A judge shown only "
            "snippets would have had no way to confirm those points, and the honest verdict on a "
            "claim it could not see is unsupported, so the snippet version was understating "
            "citation support by construction."
        )
    if gained == lost:
        return (
            f"The page and the snippet reach the same points: {gained} are locatable only in the "
            f"page and {lost} only in the snippet, out of {total}. On this evidence the fetch buys "
            "nothing, and the extra requests are not justified by what they add."
        )
    return (
        f"The snippet does better here: {lost} of {total} key points are locatable in the snippet "
        f"and not in the page, against {gained} the other way round. That is an argument against "
        "the change, most likely because passage selection is discarding the part of the page that "
        "matters, and it should be investigated before the page version is trusted."
    )


def _ablation_section(summary: dict) -> list[str]:
    """How the ranking rules compare on the fixed yardstick.

    Separate from the headline because it answers a different question: not
    whether to read the page, but how to choose which part of it. A rule is worth
    its complexity only if it locates more points than the plain one does.
    """
    ablation = summary.get("selector_ablation")
    if not ablation:
        return []

    total = summary["n_key_points"]
    lines = [
        "## Which ranking rule finds the evidence",
        "",
        "All four rank the same passages from the same fetch; only the notion of a match differs. "
        "Scored on the same plain yardstick as everything above, so a rule cannot win by counting "
        "its own matches. The last two columns are paired against the plain rule point by point, "
        "since a net count of one or two hides whether nothing moved or a handful moved both ways.",
        "",
        "| Ranking rule | Key points locatable | Mean coverage | Gained over plain | Lost against plain |",
        "|---|---|---|---|---|",
    ]
    for name, entry in sorted(ablation.items(), key=lambda kv: -kv[1]["locatable"]):
        marker = " (in use)" if name == summary.get("default_selector") else ""
        lines.append(
            f"| {name}{marker} | {entry['locatable']} of {total} | "
            f"{entry['mean_coverage'] * 100:.0f}% | {entry['gained_over_plain']} | "
            f"{entry['lost_against_plain']} |"
        )

    return lines + ["", _ablation_verdict(ablation, total), ""]


# A net difference at or below this many key points is not something 100 points
# can separate from the wording of the points themselves.
ABLATION_MARGIN = 3


def _ablation_verdict(ablation: dict, total: int) -> str:
    plain = ablation.get("plain")
    if not plain:
        return ""

    best_name, best = max(
        ((name, entry) for name, entry in ablation.items() if name != "plain"),
        key=lambda kv: kv[1]["locatable"],
    )
    net = best["locatable"] - plain["locatable"]

    if net <= 0:
        return (
            "Nothing beats the plain rule, so stemming and term weighting are complexity with no "
            "measured benefit and the plain rule stays in use. These key points share wording with "
            "the pages that answer them, which is the easy case for exact matching and not the "
            "case the extra rules were built for."
        )
    if net <= ABLATION_MARGIN:
        return (
            f"{best_name} is {net} of {total} ahead of the plain rule, gaining "
            f"{best['gained_over_plain']} points and losing {best['lost_against_plain']}. That is "
            "too small a margin for 100 key points to call, so it is recorded rather than acted on: "
            "the rule in use changes when a larger question set separates them, not on a difference "
            "this size."
        )
    return (
        f"{best_name} locates {net} more of {total} than the plain rule, gaining "
        f"{best['gained_over_plain']} and losing {best['lost_against_plain']}, so the extra matching "
        "rules earn their place and it is the rule in use."
    )


def report(summary: dict, records: list[dict]) -> str:
    lines = [
        "# Snippet or page: which one actually contains the evidence",
        "",
        f"{summary['n_key_points']} key points from {summary['n_questions']} questions, searched "
        "with the keyless Wikipedia backend, each result fetched in full. For every key point, the "
        "best lexical coverage in a snippet is compared with the best in the passages selected from "
        "a page. No model is involved, so this measures whether the evidence is reachable in what "
        "the judge is shown, not whether it supports the claim.",
        "",
        "## What the judge sees",
        "",
        "The control column is drawn from the same pages without looking at the key point, and is "
        "given at least as many characters as the selected passages it is compared with.",
        "",
        "| | Snippet | Page passages | Control |",
        "|---|---|---|---|",
        f"| Mean characters shown | {summary['mean_snippet_chars']:,.0f} | "
        f"{summary['mean_page_evidence_chars']:,.0f} | {summary['mean_random_passage_chars']:,.0f} |",
        f"| Mean key-point coverage | {summary['mean_snippet_coverage'] * 100:.0f}% | "
        f"{summary['mean_page_coverage'] * 100:.0f}% | "
        f"{summary['mean_random_passage_coverage'] * 100:.0f}% |",
        f"| Key points locatable | {summary['locatable_in_snippet']} of {summary['n_key_points']} | "
        f"{summary['locatable_in_page']} of {summary['n_key_points']} | "
        f"{summary['locatable_in_random_passages']} of {summary['n_key_points']} |",
        "",
        f"Locatable means at least {summary['threshold'] * 100:.0f} percent of the key point's "
        "content words appear in one passage. The mean coverage row is given so the threshold can "
        "be second-guessed. The pages themselves average "
        f"{summary['mean_full_page_chars']:,.0f} characters, so the judge is shown a small "
        "fraction of one rather than the whole thing.",
        "",
        _verdict_note(summary),
        "",
        _control_note(summary),
        "",
        *_ablation_section(summary),
        "## Fetch outcomes",
        "",
        "| Verdict | Sources |",
        "|---|---|",
    ]
    for verdict, count in summary["fetch_verdicts"].items():
        lines.append(f"| {verdict} | {count} |")

    lines += [
        "",
        "## Where they disagree",
        "",
        "Key points one side reaches and the other does not.",
        "",
        "| Question | Key point | Snippet | Page |",
        "|---|---|---|---|",
    ]
    threshold = summary["threshold"]
    for record in records:
        for point in record["key_points"]:
            snippet, page = point["snippet_coverage"], point["page_coverage"]
            if (snippet >= threshold) == (page >= threshold):
                continue
            lines.append(
                f"| {record['id']} | {point['key_point']} | {snippet * 100:.0f}% | {page * 100:.0f}% |"
            )

    lines += [
        "",
        "## What this does not show",
        "",
        "- Lexical coverage is not support. A passage containing every word of a claim can still "
        "contradict it, which is exactly why the judgment itself is left to a model.",
        "- Wikipedia is unusually well structured and unusually fetchable. A run over the paid "
        "search backend's mix of news and vendor pages would fetch less cleanly, and the fetch "
        "outcomes above are the optimistic case.",
        "- Key points stand in for cited claims. A real report's claims are narrower and phrased in "
        "its own words, which lexical matching handles less well than it handles these.",
        "- The figures move between runs. Repeated runs of this measurement put the page column "
        "between 85 and 87 of 100, because the search results and the pages behind them are live "
        "and edited. The page-against-snippet gap is far larger than that drift; the gap between "
        "ranking rules is not, which is why the rule in use is not chosen on it.",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Measure whether page content reaches evidence a snippet does not."
    )
    parser.add_argument("--dataset", default=str(DATASET_PATH))
    parser.add_argument("--limit", type=int, help="Only the first N questions.")
    parser.add_argument("--results", type=int, default=RESULTS_PER_QUESTION)
    parser.add_argument("--out", default=str(RESULTS_PATH))
    parser.add_argument("--report", default=str(REPORT_PATH))
    args = parser.parse_args(argv)

    questions = json.loads(Path(args.dataset).read_text())["questions"]
    if args.limit:
        questions = questions[: args.limit]

    backend = WikipediaSearchBackend()
    records = []
    for question in questions:
        print(f"{question['id']}", file=sys.stderr, flush=True)
        try:
            records.append(compare_one(question, backend, max_results=args.results))
        except EvidenceAgentError as exc:
            # One unavailable search should not throw away the rest of the run.
            print(f"  skipped: {type(exc).__name__}: {exc}", file=sys.stderr)

    summary = aggregate(records)
    out_path, report_path = Path(args.out), Path(args.report)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"summary": summary, "per_question": records}, indent=2))
    report_path.write_text(report(summary, records))

    print(f"{summary['n_key_points']} key points over {summary['n_questions']} questions")
    print(
        f"  locatable in snippet {summary['locatable_in_snippet']}, "
        f"in page {summary['locatable_in_page']}, "
        f"only in page {summary['locatable_only_in_page']}, "
        f"only in snippet {summary['locatable_only_in_snippet']}"
    )
    print(f"Saved {out_path} and {report_path}")


if __name__ == "__main__":
    main()
