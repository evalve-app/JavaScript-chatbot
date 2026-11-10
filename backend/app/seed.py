"""Seed fictional student progress records (safe to re-run).

Run from backend/:  uv run python -m app.seed
"""

from app.database import new_session
from app.models import MockStudentProgress

MOCK_STUDENTS = [
    {
        "student_id": "student-001",
        "completed_topics": ["variables and data types", "functions", "scope"],
        "current_topic": "closures",
    },
    {
        "student_id": "student-002",
        "completed_topics": ["variables and data types", "functions", "arrays", "objects", "callbacks"],
        "current_topic": "promises",
    },
    {
        "student_id": "student-003",
        "completed_topics": [],
        "current_topic": "variables and data types",
    },
    {
        "student_id": "student-004",
        "completed_topics": [
            "variables and data types", "functions", "scope", "closures", "hoisting", "arrays",
            "objects", "callbacks", "promises", "async/await",
        ],
        "current_topic": "event loop",
    },
]


def seed_students() -> int:
    with new_session() as db:
        for record in MOCK_STUDENTS:
            db.merge(MockStudentProgress(**record))
        db.commit()
    return len(MOCK_STUDENTS)


if __name__ == "__main__":
    print(f"Seeded {seed_students()} mock students.")
