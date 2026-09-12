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
from pathlib import Path
from typing import Callable

from evidence_agent.evaluation.metrics import (
    CoverageFn,
    SupportFn,
    UrlCheckerFn,
    answer_length,
    check_urls,
    coverage_rate,
    judge_coverage,
    judge_support,
    support_rate,
    url_check_to_dict,
    url_validity,
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


def _claim_source_pairs(result: dict) -> list[tuple[str, str]]:
    """Pair each cited claim with the text of the source it cites, which is what
    the support judge needs to see."""
    snippets: dict[str, str] = {}
    for results in result.get("search_results", {}).values():
        for item in results:
            snippets.setdefault(item.url, f"{item.title}\n{item.snippet}")

    return [
        (finding.claim, snippets.get(finding.source_url, ""))
        for finding in result.get("findings", [])
    ]


def evaluate_one(
    item: dict,
    pipeline: PipelineFn,
    url_checker: UrlCheckerFn = check_urls,
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

    checks = url_checker(cited_urls)
    record["citations"] = {
        **url_validity([checks[url] for url in cited_urls if url in checks]),
        "checks": [url_check_to_dict(check) for check in checks.values()],
    }

    pairs = _claim_source_pairs(result)
    verdicts = support_fn(pairs)
    record["support"] = {
        "n_claims": len(pairs),
        "n_supported": sum(verdicts),
        "support_rate": support_rate(verdicts),
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
        "mean_coverage_rate": _mean([r["coverage"]["coverage_rate"] for r in scored]),
        "mean_words": _mean([float(r["length"]["words"]) for r in scored]),
        "total_citations": sum(r["citations"]["n_citations"] for r in scored),
        "total_dead_citations": sum(r["citations"]["n_dead"] for r in scored),
        "total_blocked_citations": sum(r["citations"]["n_blocked"] for r in scored),
    }


def run_eval(
    questions: list[dict],
    pipeline: PipelineFn,
    url_checker: UrlCheckerFn = check_urls,
    support_fn: SupportFn = judge_support,
    coverage_fn: CoverageFn = judge_coverage,
    progress: Callable[[str], None] | None = None,
) -> dict:
    records = []
    for item in questions:
        if progress:
            progress(item["id"])
        records.append(
            evaluate_one(
                item,
                pipeline,
                url_checker=url_checker,
                support_fn=support_fn,
                coverage_fn=coverage_fn,
            )
        )

    return {"per_question": records, "aggregate": aggregate(records)}


def load_dataset(path: Path = DATASET_PATH) -> list[dict]:
    return json.loads(path.read_text())["questions"]


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
    args = parser.parse_args(argv)

    questions = load_dataset(Path(args.dataset))
    if args.limit:
        questions = questions[: args.limit]

    pipeline = default_pipeline(with_credibility=args.variant == "full")

    import sys

    results = run_eval(
        questions, pipeline, progress=lambda qid: print(f"evaluating {qid}", file=sys.stderr)
    )
    results["variant"] = args.variant

    out_path = Path(args.out) if args.out else RESULTS_DIR / f"eval-{args.variant}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))

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
