"""Agent 2: the JavaScript tutor. One agent handles all four intents; the route adds instructions."""

from pydantic_ai import Agent, RunContext, Tool

from app.agents.deps import TutorDeps
from app.agents.prompts import ROUTE_INSTRUCTIONS, TUTOR_SYSTEM_PROMPT
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
    return ROUTE_INSTRUCTIONS[ctx.deps.route]
