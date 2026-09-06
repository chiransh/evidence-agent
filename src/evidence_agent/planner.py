import anthropic
from pydantic import BaseModel

from evidence_agent.state import ResearchState

MODEL = "claude-opus-5"


class SubQuestions(BaseModel):
    sub_questions: list[str]


def planner_node(state: ResearchState) -> dict:
    client = anthropic.Anthropic()
    response = client.messages.parse(
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
