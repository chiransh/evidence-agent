"""Demo UI. Run with: streamlit run streamlit_app.py

Shows the report and, next to it, what the agent actually retrieved and what it
chose to cite. The gap between sources retrieved and sources cited is the most
useful thing to see while judging one of these, so it is on screen rather than
buried in a log.
"""

import streamlit as st

from evidence_agent.exceptions import ConfigurationError, EvidenceAgentError
from evidence_agent.graph import build_graph
from evidence_agent.ui.render import SETUP_HELP, citation_numbers, run_summary, source_rows

st.set_page_config(page_title="evidence-agent", page_icon="🔍", layout="wide")

st.title("evidence-agent")
st.caption(
    "Plans sub-questions, searches, scores each source, then writes a report where every "
    "claim carries a citation that was checked against what was actually retrieved."
)

with st.sidebar:
    st.header("Run settings")
    with_credibility = st.toggle(
        "Score source credibility",
        value=True,
        help=(
            "Adds a model call per sub-question to rate domain reputation and relevance, "
            "then reorders sources. Turning it off gives the variant the eval compares against."
        ),
    )
    st.markdown("---")
    st.markdown(
        "Sources are ranked by a blend of domain reputation and judged relevance, "
        "weighted toward relevance. See `notes/credibility.md`."
    )

question = st.text_input(
    "Research question",
    placeholder="What caused the 2008 global financial crisis?",
)

if st.button("Research", type="primary", disabled=not question.strip()):
    graph = build_graph(with_credibility=with_credibility)

    try:
        with st.spinner("Planning, searching, and writing..."):
            result = graph.invoke({"question": question})
    except ConfigurationError as exc:
        st.error(f"{exc}")
        st.info(SETUP_HELP)
        st.stop()
    except EvidenceAgentError as exc:
        st.error(f"{type(exc).__name__}: {exc}")
        st.stop()

    summary = run_summary(result)
    columns = st.columns(5)
    columns[0].metric("Sub-questions", summary["sub_questions"])
    columns[1].metric("Sources found", summary["sources_retrieved"])
    columns[2].metric("Sources cited", summary["sources_cited"])
    columns[3].metric("Claims", summary["findings"])
    columns[4].metric("Words", summary["words"])

    report_column, sources_column = st.columns([3, 2])

    with report_column:
        st.markdown(result["report"])

    with sources_column:
        st.subheader("Sources retrieved")
        numbers = citation_numbers(result.get("findings", []))

        for row in source_rows(result.get("search_results", {})):
            cited = numbers.get(row["url"])
            label = f"[{cited}] " if cited else ""
            score = row["credibility"]
            score_text = f"{score:.2f}" if score is not None else "not scored"

            with st.container(border=True):
                st.markdown(f"**{label}{row['title'] or row['url']}**")
                st.caption(row["url"])
                st.caption(
                    f"credibility {score_text}"
                    + ("" if cited else " | retrieved but not cited")
                )

        if not result.get("search_results"):
            st.info("No sources were retrieved for this question.")

    with st.expander("Sub-questions the planner chose"):
        for i, sub_question in enumerate(result.get("sub_questions", []), 1):
            found = len(result.get("search_results", {}).get(sub_question, []))
            st.markdown(f"{i}. {sub_question} ({found} results)")
