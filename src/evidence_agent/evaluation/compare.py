"""Compare two eval runs, with an honest read on whether the difference means
anything.

Two aggregate numbers side by side invite a conclusion the sample cannot
support. With 18 questions, a coverage difference of a few points is well
inside the noise, so this compares the runs question by question and puts a
bootstrap confidence interval on the mean paired difference. When that interval
spans zero, the report says the comparison is inconclusive rather than naming a
winner.

Pairing matters as much as the interval. The questions vary far more than the
two variants do, so comparing unpaired means throws away the fact that both
runs answered the same 18 questions.
"""

import argparse
import json
import random
import statistics
from pathlib import Path

DEFAULT_OUT = Path("evals/comparison.md")

# Metric key, display label, and whether higher is better. Answer length is
# reported but not scored: it is a control for coverage bought with verbosity,
# not something to maximise or minimise.
METRICS = [
    ("mean_coverage_rate", "Coverage", "higher"),
    ("mean_support_rate", "Citation support", "higher"),
    ("mean_citation_live_rate", "Citation URLs live", "higher"),
    ("mean_words", "Answer length (words)", "neutral"),
]

PER_QUESTION_PATHS = {
    "mean_coverage_rate": ("coverage", "coverage_rate"),
    "mean_support_rate": ("support", "support_rate"),
    "mean_citation_live_rate": ("citations", "live_rate"),
    "mean_words": ("length", "words"),
}


def load_run(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def _per_question(run: dict, metric: str) -> dict[str, float]:
    section, key = PER_QUESTION_PATHS[metric]
    values = {}
    for record in run["per_question"]:
        if "error" in record:
            continue
        value = record.get(section, {}).get(key)
        if value is not None:
            values[record["id"]] = float(value)
    return values


def paired_differences(run_a: dict, run_b: dict, metric: str) -> list[float]:
    """b minus a, for questions both runs actually scored."""
    a, b = _per_question(run_a, metric), _per_question(run_b, metric)
    shared = sorted(set(a) & set(b))
    return [b[qid] - a[qid] for qid in shared]


def bootstrap_ci(
    values: list[float], iterations: int = 2000, seed: int = 0, level: float = 0.95
) -> tuple[float, float] | None:
    if len(values) < 2:
        return None

    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(iterations):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(statistics.fmean(sample))

    means.sort()
    tail = (1.0 - level) / 2.0
    lower = means[int(tail * iterations)]
    upper = means[min(int((1.0 - tail) * iterations), iterations - 1)]
    return lower, upper


def verdict(diffs: list[float], ci: tuple[float, float] | None) -> str:
    if not diffs:
        return "no shared scored questions"
    if all(diff == 0 for diff in diffs):
        # Not the same thing as inconclusive: the runs agreed on every question,
        # which is a measurement, not a failure to measure.
        return "identical"
    if ci is None:
        return "too few questions to say"
    if ci[0] > 0:
        return "second run higher"
    if ci[1] < 0:
        return "second run lower"
    return "inconclusive, interval spans zero"


def compare(run_a: dict, run_b: dict, name_a: str, name_b: str) -> dict:
    rows = []
    for metric, label, direction in METRICS:
        diffs = paired_differences(run_a, run_b, metric)
        ci = bootstrap_ci(diffs)
        rows.append(
            {
                "metric": metric,
                "label": label,
                "direction": direction,
                "a": run_a["aggregate"].get(metric),
                "b": run_b["aggregate"].get(metric),
                "n_paired": len(diffs),
                "mean_diff": statistics.fmean(diffs) if diffs else None,
                "ci": ci,
                "verdict": verdict(diffs, ci),
            }
        )

    return {
        "runs": {name_a: run_a["aggregate"], name_b: run_b["aggregate"]},
        "comparison": rows,
    }


def _fmt(value: float | None, places: int = 3) -> str:
    return "n/a" if value is None else f"{value:.{places}f}"


def comparison_md(result: dict, name_a: str, name_b: str) -> str:
    aggregates = result["runs"]
    lines = [
        f"# Eval comparison: {name_a} vs {name_b}",
        "",
        "Both runs answered the same question set from `evals/dataset.json`. "
        "Differences below are paired by question and carry a bootstrap 95 percent "
        "confidence interval, because the questions differ from each other far more "
        "than the two variants do, and an unpaired comparison of means would throw "
        "that away.",
        "",
        "## Runs",
        "",
        "| Run | Scored | Errors | Total citations | Dead | Blocked |",
        "|---|---|---|---|---|---|",
    ]
    for name, agg in aggregates.items():
        lines.append(
            f"| {name} | {agg['n_scored']}/{agg['n_questions']} | {agg['n_errors']} | "
            f"{agg['total_citations']} | {agg['total_dead_citations']} | "
            f"{agg['total_blocked_citations']} |"
        )

    lines += [
        "",
        "## Metrics",
        "",
        f"| Metric | {name_a} | {name_b} | Paired diff | 95% CI | Paired n | Read |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in result["comparison"]:
        ci = row["ci"]
        ci_text = "n/a" if ci is None else f"[{ci[0]:+.3f}, {ci[1]:+.3f}]"
        diff = row["mean_diff"]
        diff_text = "n/a" if diff is None else f"{diff:+.3f}"
        places = 1 if row["metric"] == "mean_words" else 3
        lines.append(
            f"| {row['label']} | {_fmt(row['a'], places)} | {_fmt(row['b'], places)} | "
            f"{diff_text} | {ci_text} | {row['n_paired']} | {row['verdict']} |"
        )

    inconclusive = [r["label"] for r in result["comparison"] if "inconclusive" in r["verdict"]]
    identical = [r["label"] for r in result["comparison"] if r["verdict"] == "identical"]
    separated = [
        r["label"] for r in result["comparison"] if r["verdict"] in ("second run higher", "second run lower")
    ]

    lines += ["", "## How to read this", ""]
    if inconclusive:
        lines.append(
            "On "
            + ", ".join(inconclusive)
            + ", the interval includes zero, so this question set does not resolve a "
            "difference between the two variants. That is a real result, not a missing "
            "one: it says the sample is too small or the effect too small to separate "
            "them, and reporting the raw gap as an improvement would be overclaiming."
        )
    if identical:
        lines.append(
            ("" if not inconclusive else "\n")
            + "On "
            + ", ".join(identical)
            + ", the two runs scored every shared question the same. That is a measured "
            "null result rather than an unresolved one: the variants did not differ here "
            "at all, so there is no gap for a wider sample to sharpen."
        )
    if separated and not inconclusive and not identical:
        lines.append(
            "Every interval excludes zero, so the differences above are larger than the "
            "question-to-question noise in this sample."
        )
    elif separated:
        lines.append(
            "\nOn " + ", ".join(separated) + ", the interval excludes zero, so that difference "
            "is larger than the question-to-question noise in this sample."
        )

    lines += [
        "",
        "Answer length is a control rather than a score. A variant that improves "
        "coverage while also growing much longer may just be saying more, so the two "
        "columns are worth reading together.",
        "",
        "Both runs use the same model and the same judge prompts, so this compares the "
        "pipeline change and nothing else. The judges' own limitations, including that "
        "they share a model family with the agent, are covered in notes/evaluation.md "
        "and apply equally to both columns.",
    ]

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compare two eval result files.")
    parser.add_argument("run_a", help="Baseline results JSON.")
    parser.add_argument("run_b", help="Results JSON to compare against it.")
    parser.add_argument("--name-a", default=None)
    parser.add_argument("--name-b", default=None)
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    run_a, run_b = load_run(Path(args.run_a)), load_run(Path(args.run_b))
    name_a = args.name_a or run_a.get("variant", Path(args.run_a).stem)
    name_b = args.name_b or run_b.get("variant", Path(args.run_b).stem)

    result = compare(run_a, run_b, name_a, name_b)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(comparison_md(result, name_a, name_b))

    for row in result["comparison"]:
        print(f"{row['label']}: {row['verdict']} (paired n={row['n_paired']})")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
