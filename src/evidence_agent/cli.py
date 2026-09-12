"""Single entry point: `evidence-agent <command>`.

The three pipeline stages built along the way are all still reachable, because
the point of keeping them is being able to run the same question through each
and see what the extra machinery buys. `ask` is one model call with no tools,
`search` adds retrieval, and `research` runs the full graph.
"""

import argparse
import sys
import uuid
from contextlib import nullcontext

from langgraph.checkpoint.sqlite import SqliteSaver

from evidence_agent.baseline import ask
from evidence_agent.evaluation import compare as compare_module
from evidence_agent.evaluation import harness as harness_module
from evidence_agent.exceptions import EvidenceAgentError
from evidence_agent.graph import build_graph
from evidence_agent.search_baseline import search_and_summarize


def _question_from(args, parser: argparse.ArgumentParser) -> str:
    question = args.question or sys.stdin.read().strip()
    if not question:
        parser.error("no question provided")
    return question


def _cmd_ask(args, parser) -> None:
    print(ask(_question_from(args, parser)))


def _cmd_search(args, parser) -> None:
    print(search_and_summarize(_question_from(args, parser)))


def _cmd_research(args, parser) -> None:
    question = _question_from(args, parser)

    saver = (
        SqliteSaver.from_conn_string(args.checkpoint_db) if args.checkpoint_db else nullcontext()
    )
    with saver as checkpointer:
        graph = build_graph(checkpointer=checkpointer, with_credibility=not args.no_credibility)
        config = {"configurable": {"thread_id": args.thread_id or str(uuid.uuid4())}}
        result = graph.invoke({"question": question}, config=config)

    print(result["report"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evidence-agent",
        description="Citation-backed research agent.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    research = subparsers.add_parser(
        "research", help="Run the full graph: plan, search, score sources, synthesize, write."
    )
    research.add_argument("question", nargs="?", help="Question to research. Reads stdin if omitted.")
    research.add_argument(
        "--checkpoint-db",
        help=(
            "SQLite file to checkpoint into. With --thread-id, a run that died partway "
            "resumes from its last completed node instead of paying for the earlier ones again."
        ),
    )
    research.add_argument("--thread-id", help="Thread to write to or resume.")
    research.add_argument(
        "--no-credibility",
        action="store_true",
        help="Skip source credibility scoring, which is the variant the eval compares against.",
    )
    research.set_defaults(func=_cmd_research)

    ask_parser = subparsers.add_parser(
        "ask", help="One model call, no tools and no citations. The floor the pipeline must beat."
    )
    ask_parser.add_argument("question", nargs="?")
    ask_parser.set_defaults(func=_cmd_ask)

    search_parser = subparsers.add_parser(
        "search", help="Search then summarize, without planning or source scoring."
    )
    search_parser.add_argument("question", nargs="?")
    search_parser.set_defaults(func=_cmd_search)

    # Listed so they show up in --help. They are dispatched before argparse
    # runs (see main), because the eval tooling owns its own options and
    # argparse.REMAINDER does not capture an option in first position: it would
    # take `eval --limit 1` as an unrecognised top-level flag.
    subparsers.add_parser("eval", add_help=False, help="Score the agent against the question set.")
    subparsers.add_parser("compare", add_help=False, help="Compare two eval result files.")

    return parser


# Subcommands whose arguments belong to another parser and are forwarded whole.
FORWARDED = {
    "eval": harness_module.main,
    "compare": compare_module.main,
}


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv and argv[0] in FORWARDED:
        FORWARDED[argv[0]](argv[1:])
        return

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        args.func(args, parser)
    except EvidenceAgentError as exc:
        # Typed errors are expected conditions, so they get a clear line rather
        # than a traceback. Anything else is a bug and should surface as one.
        parser.exit(2, f"evidence-agent: error: {exc}\n")


if __name__ == "__main__":
    main()
