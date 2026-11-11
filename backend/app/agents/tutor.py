"""Agent 2: the JavaScript tutor. One agent handles all four intents; the route adds instructions."""

from collections.abc import Iterator
from contextlib import contextmanager

from pydantic_ai import Agent, RunContext, Tool

from app.agents.deps import TutorDeps
from app.agents.prompts import TUTOR_SYSTEM_PROMPT, task_label
from app.tools.examples import get_code_example
from app.tools.progress import get_mock_progress
from app.tools.search import search_lessons

tutor_agent = Agent(
    deps_type=TutorDeps,
    output_type=str,
    instructions=TUTOR_SYSTEM_PROMPT,
    name="javascript_tutor",
    tools=[
        Tool(search_lessons, takes_ctx=True),
        Tool(get_code_example),
        Tool(get_mock_progress),
    ],
)


@tutor_agent.instructions
def route_instructions(ctx: RunContext[TutorDeps]) -> str:
    return task_label(ctx.deps.route)


@contextmanager
def tutor_prompt_override(system_prompt: str | None) -> Iterator[None]:
    """Replace the tutor's big prompt for this run (Kitaru system_prompt override).

    The one-line task label stays, so routing still reaches the tutor.
    """
    if not system_prompt:
        yield
        return
    with tutor_agent.override(instructions=[system_prompt, route_instructions]):
        yield
