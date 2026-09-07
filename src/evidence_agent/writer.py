"""Renders the final report from a fixed template. No LLM call: by the time
findings reach here they already carry a claim and a verified source_url
(evidence_agent.synthesizer drops anything that isn't), so this node's only
job is deterministic formatting, not generation."""

from evidence_agent.state import Finding, ResearchState


def _assign_citation_numbers(findings: list[Finding]) -> dict[str, int]:
    numbers: dict[str, int] = {}
    for finding in findings:
        if finding.source_url not in numbers:
            numbers[finding.source_url] = len(numbers) + 1
    return numbers


def writer_node(state: ResearchState) -> dict:
    numbers = _assign_citation_numbers(state.findings)

    lines = ["# Research Report", "", "## Question", "", state.question, "", "## Findings", ""]
    if not state.findings:
        lines.append("No findings.")
    else:
        for finding in state.findings:
            lines.append(f"- {finding.claim} [{numbers[finding.source_url]}]")

    lines += ["", "## Sources", ""]
    if not numbers:
        lines.append("No sources.")
    else:
        for url, number in numbers.items():
            lines.append(f"[{number}] {url}")

    return {"report": "\n".join(lines)}
