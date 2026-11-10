"""Tool: get_mock_progress — fictional student progress stored in Neon."""

from pydantic import BaseModel

from app.database import new_session
from app.models import MockStudentProgress


class ProgressResult(BaseModel):
    found: bool
    student_id: str
    completed_topics: list[str] = []
    current_topic: str | None = None
    message: str | None = None


def get_mock_progress(student_id: str) -> ProgressResult:
    """Look up a fictional (mock) student's JavaScript learning progress.

    Only for StudyBot's seeded mock students, e.g. "student-001".

    Args:
        student_id: The mock student's ID, e.g. "student-001".
    """
    student_id = student_id.strip().lower()
    with new_session() as db:
        row = db.get(MockStudentProgress, student_id)
    if row is None:
        return ProgressResult(found=False, student_id=student_id, message="No mock student with that ID.")
    return ProgressResult(
        found=True,
        student_id=row.student_id,
        completed_topics=row.completed_topics,
        current_topic=row.current_topic,
    )
