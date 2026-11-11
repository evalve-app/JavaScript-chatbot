"""Kitaru worker entrypoint: replay one recorded StudyBot turn.

The worker runs this for each replay task:
    uv run python -m app.kitaru_entry

It reads the task's recorded inputs and the replay (override + tool policy), answers the
question again through answer_turn(), and records the run as a session with origin "replay".
It never writes to the chat database. Exit code 0 = success; anything else = failed task.

Without a task (no KITARU_TASK_ID), it just answers and records nothing:
    uv run python -m app.kitaru_entry "Explain closures"
"""

import asyncio
import json
import os
import sys
import uuid
from typing import Any

from kitaru.api_models.v1.session import SessionOrigin
from kitaru.api_models.v1.task import AgentTaskDetails
from kitaru.client import KitaruAPIClient

from app.agents.workflow import TurnFailed, answer_turn
from app.config import get_settings
from app.recording.capture import secret_values
from app.recording.recorder import Outcome, TurnRecorder, history_from_turns
from app.recording.replay import ReplayConfigError, ReplayPlan

EXIT_OK = 0
EXIT_TURN_FAILED = 1  # the agent failed, or Kitaru could not store the replay session
EXIT_BAD_REPLAY = 2  # the task or replay asks for something StudyBot can't do; nothing ran


def task_client() -> KitaruAPIClient:
    # No arguments on purpose: use the worker's KITARU_API_URL + task-scoped KITARU_API_TOKEN,
    # never a key from the local settings file.
    return KitaruAPIClient()


def question_and_history(inputs: Any) -> tuple[str, list[tuple[str, str]]]:
    """Recorded session inputs -> (question, history). Accepts StudyBot's turns format or a plain string."""
    if isinstance(inputs, str) and inputs.strip():
        return inputs, []
    return history_from_turns(inputs)


async def load_task(client: Any, task_id: uuid.UUID) -> tuple[Any, uuid.UUID | None]:
    """(recorded inputs, replay id) from the environment or, as the worker does today, the task spec."""
    raw_inputs = os.environ.get("KITARU_TASK_INPUTS")
    replay_value = os.environ.get("KITARU_REPLAY_ID")
    if raw_inputs is not None:
        inputs = json.loads(raw_inputs)
    else:
        spec = await client.tasks.get_spec(task_id)
        if not isinstance(spec.details, AgentTaskDetails):
            raise ReplayConfigError(f"Task {task_id} is not an agent task")
        inputs = spec.details.inputs
        replay_value = replay_value or (str(spec.details.replay_id) if spec.details.replay_id else None)
    return inputs, uuid.UUID(replay_value) if replay_value else None


async def run_task(task_id: uuid.UUID, client_factory=task_client) -> int:
    secrets = secret_values(get_settings()) + [t for t in [os.environ.get("KITARU_API_TOKEN")] if t]
    client = client_factory()  # for task spec, replay, and history lookups
    try:
        # 1. Everything that can be checked before spending money.
        try:
            inputs, replay_id = await load_task(client, task_id)
            question, history = question_and_history(inputs)
            plan = None
            if replay_id is not None:
                plan = ReplayPlan.from_replay(await client.replays.get(replay_id), client)
        except (ReplayConfigError, ValueError) as error:
            print(f"Replay rejected before running: {error}", file=sys.stderr)
            return EXIT_BAD_REPLAY

        # 2. Open the replay session. Without it the replay is worthless, so stop here.
        recorder = TurnRecorder(client_factory, secrets)
        await recorder.start(
            question=question,
            history=history,
            origin=SessionOrigin.REPLAY if replay_id else SessionOrigin.RECORDED,
            metadata={
                "source": "kitaru-replay",
                "task_id": str(task_id),
                "replay_id": str(replay_id) if replay_id else None,
            },
        )
        if recorder.outcome != Outcome.RECORDED:
            print(f"Kitaru session could not be created: {recorder.problem}", file=sys.stderr)
            return EXIT_TURN_FAILED

        # 3. Answer again and record it.
        try:
            answer = await answer_turn(question, history, recorder=recorder, replay=plan)
        except TurnFailed as failed:
            error = failed.__cause__ or failed
            await recorder.finish(error=error)
            print(f"session {recorder.session_id}: turn failed: {type(error).__name__}: {error}", file=sys.stderr)
            return EXIT_TURN_FAILED

        outcome = await recorder.finish(answer=answer.response)
        print(f"session {recorder.session_id}: {outcome} (route: {answer.route})")
        if outcome != Outcome.RECORDED:
            print(f"Kitaru recording incomplete: {recorder.problem}", file=sys.stderr)
            return EXIT_TURN_FAILED
        return EXIT_OK
    finally:
        await client.close()


async def answer_locally(question: str) -> int:
    answer = await answer_turn(question, [])
    print(f"[route: {answer.route}]\n{answer.response}")
    return EXIT_OK


def main() -> None:
    task_value = os.environ.get("KITARU_TASK_ID")
    if task_value:
        sys.exit(asyncio.run(run_task(uuid.UUID(task_value))))
    if len(sys.argv) < 2:
        sys.exit('usage: python -m app.kitaru_entry "question"   (or run by a Kitaru worker task)')
    sys.exit(asyncio.run(answer_locally(" ".join(sys.argv[1:]))))


if __name__ == "__main__":
    main()
