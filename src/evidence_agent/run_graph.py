import argparse
import sys
import uuid
from contextlib import nullcontext

from langgraph.checkpoint.sqlite import SqliteSaver

from evidence_agent.exceptions import EvidenceAgentError
from evidence_agent.graph import build_graph


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Planner -> Searcher -> Credibility -> Synthesizer -> Writer graph."
    )
    parser.add_argument("question", nargs="?", help="Question to research. Reads stdin if omitted.")
    parser.add_argument(
        "--checkpoint-db",
        help=(
            "SQLite file to checkpoint into. With --thread-id, a run that died partway "
            "resumes from its last completed node instead of paying for the earlier ones again."
        ),
    )
    parser.add_argument(
        "--thread-id",
        help="Conversation thread to write to or resume. Defaults to a fresh id per run.",
    )
    args = parser.parse_args()

    question = args.question or sys.stdin.read().strip()
    if not question:
        parser.error("no question provided")

    saver = SqliteSaver.from_conn_string(args.checkpoint_db) if args.checkpoint_db else nullcontext()
    with saver as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": args.thread_id or str(uuid.uuid4())}}

        try:
            result = graph.invoke({"question": question}, config=config)
        except EvidenceAgentError as exc:
            parser.error(str(exc))
            return

    print(result["report"])


if __name__ == "__main__":
    main()
