from pydantic import BaseModel

from evidence_agent.llm import MODEL, client, model_errors
from evidence_agent.state import ResearchState


class SubQuestions(BaseModel):
    sub_questions: list[str]


def planner_node(state: ResearchState) -> dict:
    with model_errors():
        response = client().messages.parse(
            model=MODEL,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Break the following research question into 2-4 focused sub-questions, "
                        "each narrow enough to answer with a single web search. "
                        f"Question: {state.question}"
                    ),
                }
            ],
            output_format=SubQuestions,
        )
    return {"sub_questions": response.parsed_output.sub_questions}
