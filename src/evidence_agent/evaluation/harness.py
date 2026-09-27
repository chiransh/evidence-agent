"""Eval harness: run the pipeline over the question set and score it.

The pipeline is injected rather than imported directly so the same harness can
score different variants of the agent (with and without credibility scoring,
for instance) without the scoring code knowing which is which.

A question whose pipeline run raises is recorded as an error and the harness
carries on. Aborting the whole eval on one failure would hide how the agent
behaves on the rest, and the error list is itself a result worth keeping.
"""

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Callable, Sequence

from evidence_agent.evaluation.metrics import (
    CoverageFn,
    SupportFn,
    UrlCheck,
    answer_length,
    coverage_rate,
    judge_coverage,
    judge_support,
    support_rate,
    url_check_to_dict,
    url_validity,
)
from evidence_agent.evaluation.pages import (
    Evidence,
    PageText,
    evidence_for,
    evidence_summary,
    fetch_pages,
)
from evidence_agent.exceptions import EvidenceAgentError
from evidence_agent.graph import build_graph

DATASET_PATH = Path("evals/dataset.json")
RESULTS_DIR = Path("evals/results")

PipelineFn = Callable[[str], dict]


def default_pipeline(with_credibility: bool = True) -> PipelineFn:
    graph = build_graph(with_credibility=with_credibility)

    def run(question: str) -> dict:
        return graph.invoke({"question": question})

    return run


PageFetcherFn = Callable[[Sequence[str]], dict[str, PageText]]

# Page fetch verdicts mapped onto citation liveness. A page that answered but is
# not HTML still exists, so it is live for the purpose of "does this URL work",
# even though there is no text to judge a claim against.
_LIVENESS = {
    "fetched": "live",
    "unparseable": "live",
    "blocked": "blocked",
    "dead": "dead",
    "unreachable": "unreachable",
}


def _snippets(result: dict) -> dict[str, str]:
    snippets: dict[str, str] = {}
    for results in result.get("search_results", {}).values():
        for item in results:
            snippets.setdefault(item.url, f"{item.title}\n{item.snippet}")
    return snippets


def claim_evidence(result: dict, pages: dict[str, PageText]) -> list[tuple[str, Evidence]]:
    """Pair each cited claim with the text the support judge will grade it against.

    Page content where the page could be fetched, the search snippet otherwise,
    with the reason recorded either way.
    """
    snippets = _snippets(result)
    return [
        (
            finding.claim,
            evidence_for(finding.claim, snippets.get(finding.source_url, ""), pages.get(finding.source_url)),
        )
        for finding in result.get("findings", [])
    ]


def checks_from_pages(pages: dict[str, PageText]) -> dict[str, UrlCheck]:
    """Reuse the page fetch as the liveness check rather than requesting twice."""
    return {
        url: UrlCheck(url=url, status=page.status, verdict=_LIVENESS[page.verdict])
        for url, page in pages.items()
    }


def evaluate_one(
    item: dict,
    pipeline: PipelineFn,
    page_fetcher: PageFetcherFn = fetch_pages,
    support_fn: SupportFn = judge_support,
    coverage_fn: CoverageFn = judge_coverage,
) -> dict:
    record = {"id": item["id"], "question": item["question"]}

    try:
        result = pipeline(item["question"])
    except EvidenceAgentError as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
        return record

    report = result.get("report", "")
    findings = result.get("findings", [])
    cited_urls = [finding.source_url for finding in findings]

    pages = page_fetcher(cited_urls)
    checks = checks_from_pages(pages)
    record["citations"] = {
        **url_validity([checks[url] for url in cited_urls if url in checks]),
        "checks": [url_check_to_dict(check) for check in checks.values()],
    }

    evidence = claim_evidence(result, pages)
    verdicts = support_fn([(claim, item.text) for claim, item in evidence])
    record["support"] = {
        "n_claims": len(evidence),
        "n_supported": sum(verdicts),
        "support_rate": support_rate(verdicts),
        # What the judge was shown, so a support rate can be read next to how
        # much of it was decided on page content rather than snippets.
        "evidence": evidence_summary([item for _, item in evidence]),
    }

    covered = coverage_fn(report, item["key_points"])
    record["coverage"] = {
        "n_key_points": len(covered),
        "n_covered": sum(covered.values()),
        "coverage_rate": coverage_rate(covered),
        "missed": [point for point, hit in covered.items() if not hit],
    }

    record["length"] = answer_length(report)
    record["n_sub_questions"] = len(result.get("sub_questions", []))

    return record


def _mean(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return statistics.fmean(present) if present else None


def aggregate(records: list[dict]) -> dict:
    scored = [r for r in records if "error" not in r]

    return {
        "n_questions": len(records),
        "n_scored": len(scored),
        "n_errors": len(records) - len(scored),
        "mean_citation_live_rate": _mean([r["citations"]["live_rate"] for r in scored]),
        "mean_support_rate": _mean([r["support"]["support_rate"] for r in scored]),
        # A support rate judged mostly from snippets is a weaker number than one
        # judged from pages, so the run says which it is.
        "mean_page_evidence_rate": _mean(
            [r["support"]["evidence"]["page_rate"] for r in scored if "evidence" in r["support"]]
        ),
        "mean_coverage_rate": _mean([r["coverage"]["coverage_rate"] for r in scored]),
        "mean_words": _mean([float(r["length"]["words"]) for r in scored]),
        "total_citations": sum(r["citations"]["n_citations"] for r in scored),
        "total_dead_citations": sum(r["citations"]["n_dead"] for r in scored),
        "total_blocked_citations": sum(r["citations"]["n_blocked"] for r in scored),
    }


def run_eval(
    questions: list[dict],
    pipeline: PipelineFn,
    page_fetcher: PageFetcherFn = fetch_pages,
    support_fn: SupportFn = judge_support,
    coverage_fn: CoverageFn = judge_coverage,
    progress: Callable[[str], None] | None = None,
    already_scored: list[dict] | None = None,
    on_record: Callable[[list[dict]], None] | None = None,
) -> dict:
    """Score each question in turn.

    A full run is around 200 model calls and costs real money, so `already_scored`
    lets a resumed run skip questions that came back clean, and `on_record` is
    called after every question so a crash halfway through does not throw away
    what was already paid for.
    """
    records = list(already_scored or [])
    done = {record["id"] for record in records if "error" not in record}

    for item in questions:
        if item["id"] in done:
            continue
        if progress:
            progress(item["id"])
        # A question that previously errored is retried, and its old record
        # replaced rather than duplicated.
        records = [record for record in records if record["id"] != item["id"]]
        records.append(
            evaluate_one(
                item,
                pipeline,
                page_fetcher=page_fetcher,
                support_fn=support_fn,
                coverage_fn=coverage_fn,
            )
        )
        if on_record:
            on_record(records)

    order = {item["id"]: position for position, item in enumerate(questions)}
    records.sort(key=lambda record: order.get(record["id"], len(order)))
    return {"per_question": records, "aggregate": aggregate(records)}


def load_dataset(path: Path = DATASET_PATH) -> list[dict]:
    return json.loads(path.read_text())["questions"]


def load_previous(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("per_question", [])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Score the agent against the eval question set.")
    parser.add_argument("--dataset", default=str(DATASET_PATH))
    parser.add_argument("--out", help="Where to write the results JSON.")
    parser.add_argument("--limit", type=int, help="Only evaluate the first N questions.")
    parser.add_argument(
        "--variant",
        choices=["full", "no-credibility"],
        default="full",
        help="Which build of the agent to score.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Keep questions already scored in the output file and only run the rest. "
            "Questions that errored are retried."
        ),
    )
    args = parser.parse_args(argv)

    questions = load_dataset(Path(args.dataset))
    if args.limit:
        questions = questions[: args.limit]

    pipeline = default_pipeline(with_credibility=args.variant == "full")

    out_path = Path(args.out) if args.out else RESULTS_DIR / f"eval-{args.variant}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    previous = load_previous(out_path) if args.resume else []
    if previous:
        scored = len([r for r in previous if "error" not in r])
        print(f"resuming: {scored} questions already scored in {out_path}", file=sys.stderr)

    def save(records: list[dict]) -> None:
        out_path.write_text(
            json.dumps(
                {"variant": args.variant, "per_question": records, "aggregate": aggregate(records)},
                indent=2,
            )
        )

    results = run_eval(
        questions,
        pipeline,
        progress=lambda qid: print(f"evaluating {qid}", file=sys.stderr),
        already_scored=previous,
        on_record=save,
    )
    results["variant"] = args.variant
    save(results["per_question"])

    agg = results["aggregate"]
    print(f"variant: {args.variant}")
    print(f"  scored {agg['n_scored']}/{agg['n_questions']} questions, {agg['n_errors']} errors")
    for key in (
        "mean_citation_live_rate",
        "mean_support_rate",
        "mean_coverage_rate",
        "mean_words",
    ):
        value = agg[key]
        print(f"  {key}: {value:.3f}" if value is not None else f"  {key}: n/a")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
