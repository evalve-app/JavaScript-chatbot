"""Record one StudyBot chat turn as one Kitaru session (best effort).

Lifecycle, all through the public kitaru SDK:
    start()     create the session (in progress) and its root node "turn"
    add_node()  buffer child nodes in memory (no network)
    finish()    send the buffered nodes, mark root + session completed or failed

Best effort: Kitaru problems never raise into the app. They end up in `outcome`
(and `problem`), which the app stores and shows in Developer details:

    disabled    recording is not configured
    recorded    the whole turn was stored
    partial     the session exists but some writes failed; do not trust it as complete
    unrecorded  no session was created
"""

import asyncio
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from kitaru.api_models.v1.session import (
    SessionCreateRequest,
    SessionOrigin,
    SessionStatus,
    SessionUpdateRequest,
    TokenUsage,
)
from kitaru.api_models.v1.session_node import (
    NodeStatus,
    NodeType,
    SessionNodeBatchRequest,
    SessionNodeCreateRequest,
)

from app.recording.capture import capture, capture_error

FRAMEWORK = "pydantic-ai"
ADAPTER_VERSION = "studybot-0.1.0"
ROOT_ID = "turn"
BATCH_SIZE = 50
WRITE_TIMEOUT_SECONDS = 5.0
# After a failed write, skip recording for a while so a stopped Kitaru server
# doesn't add a timeout to every chat message.
BACKOFF_SECONDS = 60.0

_skip_until = 0.0  # monotonic time; shared by all turns in this process


class Outcome(StrEnum):
    DISABLED = "disabled"
    RECORDED = "recorded"
    PARTIAL = "partial"
    UNRECORDED = "unrecorded"


def utcnow() -> datetime:
    return datetime.now(UTC)


def reset_backoff() -> None:
    global _skip_until
    _skip_until = 0.0


def _start_backoff() -> None:
    global _skip_until
    _skip_until = time.monotonic() + BACKOFF_SECONDS


def turns_input(question: str, history: list[tuple[str, str]]) -> dict:
    """The turn as {"turns": [{"inputs", "outputs"}, ..., {"inputs": question}]}.

    Lossless for StudyBot's history: an unanswered question gets outputs=None,
    and a history that starts mid-exchange gets inputs=None.
    """
    turns: list[dict[str, Any]] = []
    for role, content in history:
        if role == "user":
            turns.append({"inputs": content, "outputs": None})
        elif turns and turns[-1]["outputs"] is None and turns[-1]["inputs"] is not None:
            turns[-1]["outputs"] = content
        else:
            turns.append({"inputs": None, "outputs": content})
    turns.append({"inputs": question})
    return {"turns": turns}


def history_from_turns(inputs: dict) -> tuple[str, list[tuple[str, str]]]:
    """Inverse of turns_input: (question, history)."""
    turns = inputs.get("turns") if isinstance(inputs, dict) else None
    if not turns or not isinstance(turns[-1].get("inputs"), str):
        raise ValueError("Recorded inputs have no question to replay")
    history: list[tuple[str, str]] = []
    for turn in turns[:-1]:
        if turn.get("inputs") is not None:
            history.append(("user", turn["inputs"]))
        if turn.get("outputs") is not None:
            history.append(("assistant", turn["outputs"]))
    return turns[-1]["inputs"], history


class TurnRecorder:
    """State for ONE turn. Create a new instance per turn; never share one."""

    def __init__(self, client_factory: Callable[[], Any] | None, secrets: list[str]):
        self._client_factory = client_factory
        self._secrets = secrets
        self._client: Any = None
        self._buffer: list[SessionNodeCreateRequest] = []
        self._started_at: datetime | None = None
        self._root_inputs: Any = None
        self.session_id: uuid.UUID | None = None
        self.outcome = Outcome.DISABLED if client_factory is None else Outcome.UNRECORDED
        self.problem: str | None = None  # first Kitaru problem, for diagnostics
        self.confirmed_nodes = 0
        # Open spans: external_id -> (buffer position, name, inputs, started_at)
        self._open_spans: dict[str, tuple[int, str, Any, datetime]] = {}

    @property
    def active(self) -> bool:
        return self.session_id is not None and self.outcome == Outcome.RECORDED

    def capture(self, value: Any) -> Any:
        return capture(value, self._secrets)

    async def _write(self, call) -> Any:
        return await asyncio.wait_for(call, WRITE_TIMEOUT_SECONDS)

    def _note_problem(self, step: str, error: BaseException) -> None:
        if self.problem is None:
            self.problem = f"{step}: {capture_error(error, self._secrets)}"
        _start_backoff()

    async def start(
        self,
        *,
        question: str,
        history: list[tuple[str, str]],
        origin: SessionOrigin = SessionOrigin.RECORDED,
        agent_id: uuid.UUID | None = None,
        agent_version_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> None:
        if self._client_factory is None:
            return
        if time.monotonic() < _skip_until:
            self.problem = "skipped: Kitaru failed recently; retrying after the backoff"
            return
        self._started_at = utcnow()
        self._root_inputs = self.capture({"question": question, "history": [list(h) for h in history]})
        inputs = self.capture(turns_input(question, history))
        try:
            self._client = self._client_factory()
            session = await self._write(
                self._client.sessions.create(
                    SessionCreateRequest(
                        agent_id=agent_id,
                        agent_version_id=agent_version_id,
                        origin=origin,
                        status=SessionStatus.IN_PROGRESS,
                        inputs=inputs,
                        outputs=None,
                        input_text_selector=f"/turns/{len(inputs['turns']) - 1}/inputs",
                        output_text_selector="/answer",
                        started_at=self._started_at,
                        framework=FRAMEWORK,
                        adapter_version=ADAPTER_VERSION,
                        metadata=self.capture(metadata or {}),
                    )
                )
            )
        except Exception as error:
            self._note_problem("create session", error)
            await self._close()
            return
        self.session_id = session.id
        self.outcome = Outcome.RECORDED
        try:
            await self._write(self._ingest([self._root(NodeStatus.IN_PROGRESS)]))
        except Exception as error:
            self._note_problem("write root", error)
            self.outcome = Outcome.PARTIAL
            await self._mark_failed("Kitaru could not store the root node")
            await self._close()

    def add_node(
        self,
        *,
        node_type: NodeType,
        name: str,
        parent: str = ROOT_ID,
        started_at: datetime | None = None,
        inputs: Any = None,
        outputs: Any = None,
        error: BaseException | None = None,
        external_id: str | None = None,
        tokens: TokenUsage | None = None,
        **fields: Any,
    ) -> str:
        """Buffer one child node and return its id (usable as a parent). No network."""
        external_id = external_id or uuid.uuid4().hex
        if not self.active:
            return external_id
        self._buffer.append(
            SessionNodeCreateRequest(
                external_id=external_id,
                parent_external_id=parent,
                node_type=node_type,
                name=name,
                status=NodeStatus.FAILED if error else NodeStatus.COMPLETED,
                error=capture_error(error, self._secrets) if error else None,
                started_at=started_at,
                ended_at=utcnow(),
                inputs=self.capture(inputs),
                outputs=self.capture(outputs),
                tokens=tokens,
                attributes=self.capture(fields.pop("attributes", {})),
                **fields,
            )
        )
        return external_id

    def begin_span(self, name: str, inputs: Any = None, parent: str = ROOT_ID) -> str:
        """Reserve a span's place in the buffer so it is sent before its children."""
        external_id = uuid.uuid4().hex
        if self.active:
            self._open_spans[external_id] = (len(self._buffer), name, inputs, utcnow())
            self._buffer.append(self._span_node(external_id, parent, name, inputs, NodeStatus.IN_PROGRESS))
        return external_id

    def end_span(self, span_id: str, outputs: Any = None, error: BaseException | None = None) -> None:
        if span_id not in self._open_spans:
            return
        position, name, inputs, started_at = self._open_spans.pop(span_id)
        parent = self._buffer[position].parent_external_id
        status = NodeStatus.FAILED if error else NodeStatus.COMPLETED
        self._buffer[position] = self._span_node(
            span_id, parent, name, inputs, status, outputs, error, started_at, utcnow()
        )

    def _span_node(self, external_id, parent, name, inputs, status, outputs=None, error=None, started_at=None, ended_at=None):
        return SessionNodeCreateRequest(
            external_id=external_id,
            parent_external_id=parent,
            node_type=NodeType.SPAN,
            name=name,
            status=status,
            error=capture_error(error, self._secrets) if error else None,
            started_at=started_at or utcnow(),
            ended_at=ended_at,
            inputs=self.capture(inputs),
            outputs=self.capture(outputs),
            attributes={},
        )

    async def finish(self, *, answer: str | None = None, error: BaseException | None = None) -> Outcome:
        """Store buffered nodes and the terminal state. Never raises."""
        if not self.active:
            return self.outcome
        for span_id in list(self._open_spans):  # a span left open means its step crashed
            self.end_span(span_id, error=error or RuntimeError("span was not closed"))
        ended_at = utcnow()
        outputs = {"answer": self.capture(answer)} if error is None else None
        error_text = capture_error(error, self._secrets) if error else None
        status = NodeStatus.FAILED if error else NodeStatus.COMPLETED
        try:
            while self._buffer:
                batch = self._buffer[:BATCH_SIZE]
                await self._write(self._ingest(batch))
                del self._buffer[: len(batch)]
                self.confirmed_nodes += len(batch)
            await self._write(self._ingest([self._root(status, outputs, error_text, ended_at)]))
            await self._write(
                self._client.sessions.update(
                    self.session_id,
                    SessionUpdateRequest(
                        status=SessionStatus.FAILED if error else SessionStatus.COMPLETED,
                        outputs=outputs,
                        error=error_text,
                        ended_at=ended_at,
                    ),
                )
            )
        except Exception as failure:
            self._note_problem("finish", failure)
            self.outcome = Outcome.PARTIAL
            await self._mark_failed(f"Kitaru recording incomplete; {self.confirmed_nodes} child nodes stored")
        finally:
            await self._close()
        return self.outcome

    # ---- internals ----

    def _ingest(self, nodes: list[SessionNodeCreateRequest]):
        return self._client.sessions.ingest_nodes(self.session_id, SessionNodeBatchRequest(nodes=nodes))

    def _root(self, status, outputs=None, error=None, ended_at=None) -> SessionNodeCreateRequest:
        return SessionNodeCreateRequest(
            external_id=ROOT_ID,
            parent_external_id=None,
            node_type=NodeType.SPAN,
            name="turn",
            status=status,
            error=error,
            started_at=self._started_at,
            ended_at=ended_at,
            inputs=self._root_inputs,
            outputs=outputs,
            input_text_selector="/question",
            output_text_selector="/answer" if outputs else None,
            attributes={},
        )

    async def _mark_failed(self, message: str) -> None:
        try:
            await self._write(
                self._client.sessions.update(
                    self.session_id,
                    SessionUpdateRequest(status=SessionStatus.FAILED, error=message, ended_at=utcnow()),
                )
            )
        except Exception:
            pass  # already PARTIAL; the first problem is kept in self.problem

    async def _close(self) -> None:
        if self._client is None:
            return
        client, self._client = self._client, None
        try:
            await client.close()
        except Exception:
            pass
