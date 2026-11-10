"""Agent 1: JavaScript scope + intent classifier (one LLM call, validated structured output)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent

from app.agents.prompts import CLASSIFIER_PROMPT

Scope = Literal["in_scope", "out_of_scope"]
Intent = Literal["concept", "debugging", "code_generation", "quiz"]
Language = Literal["javascript", "other", "unknown"]


class Classification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Scope
    intent: Intent
    language: Language


# The model is supplied at run time (see workflow.py) so tests can override it.
classifier_agent = Agent(
    output_type=Classification,
    instructions=CLASSIFIER_PROMPT,
    name="javascript_classifier",
    retries=2,
)


def build_classifier_input(question: str, recent_history: list[tuple[str, str]]) -> str:
    """Give the classifier the new question plus a short transcript for follow-ups."""
    if not recent_history:
        return f"New message:\n{question}"
    lines = [f"{role}: {content[:500]}" for role, content in recent_history[-6:]]
    transcript = "\n".join(lines)
    return f"Recent conversation (for context):\n{transcript}\n\nNew message to classify:\n{question}"
