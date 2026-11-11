"""Per-request dependencies passed to the tutor agent and its tools."""

from dataclasses import dataclass, field


@dataclass
class TutorDeps:
    # Filled by search_lessons so the workflow can log which lessons were used.
    retrieved_sources: list[dict] = field(default_factory=list)
