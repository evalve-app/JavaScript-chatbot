"""Let ordinary app code (e.g. RAG retrieval) add steps to the current trace.

The hooks set the current (recorder, parent node) while a tool runs. Code called
from that tool can then do:

    with trace_step(NodeType.SPAN, "retrieve lessons", inputs={...}) as step:
        ...
        step.outputs = {...}

Outside a recorded turn (ingestion script, tests, recording off) it does nothing.
Context variables are per request and are copied into tool worker threads, so two
chats (or two parallel tool calls) never share a parent.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from kitaru.api_models.v1.session_node import NodeType

from app.recording.recorder import TurnRecorder

_current: ContextVar[tuple[TurnRecorder, str] | None] = ContextVar("studybot_trace", default=None)


@contextmanager
def trace_parent(recorder: TurnRecorder, parent: str) -> Iterator[None]:
    """Make `parent` the node new steps attach to, for the duration of the block."""
    token = _current.set((recorder, parent))
    try:
        yield
    finally:
        _current.reset(token)


@dataclass
class Step:
    """Filled in by the caller; recorded when the block ends."""

    outputs: Any = None
    attributes: dict = field(default_factory=dict)
    fields: dict = field(default_factory=dict)  # extra node fields: tokens, model, ...


@contextmanager
def trace_step(
    node_type: NodeType, name: str, *, inputs: Any = None, attributes: dict | None = None, **fields: Any
) -> Iterator[Step]:
    step = Step()
    current = _current.get()
    if current is None:
        yield step
        return
    recorder, parent = current
    node_id = recorder.begin_node(node_type, name, parent=parent, inputs=inputs, attributes=attributes, **fields)
    token = _current.set((recorder, node_id))  # nested steps become children of this one
    try:
        yield step
    except BaseException as error:
        _current.reset(token)
        recorder.end_node(node_id, outputs=step.outputs, error=error, attributes=step.attributes, **step.fields)
        raise
    _current.reset(token)
    recorder.end_node(node_id, outputs=step.outputs, attributes=step.attributes, **step.fields)
