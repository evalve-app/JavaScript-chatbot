"""Tool: get_code_example — curated JavaScript examples from data/examples.json."""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

EXAMPLES_FILE = Path(__file__).resolve().parents[2] / "data" / "examples.json"


class CodeExample(BaseModel):
    topic: str
    code: str
    explanation: str


class CodeExampleResult(BaseModel):
    found: bool
    example: CodeExample | None = None
    available_topics: list[str]


@lru_cache
def load_examples() -> dict[str, CodeExample]:
    raw = json.loads(EXAMPLES_FILE.read_text(encoding="utf-8"))
    return {key: CodeExample(**value) for key, value in raw.items()}


def _normalize(text: str) -> str:
    return text.lower().replace("-", " ").replace("_", " ").replace("/", " ").strip()


def get_code_example(topic: str) -> CodeExampleResult:
    """Get a curated JavaScript code example.

    Args:
        topic: One of: closures, promises, array methods, recursion, async/await, objects.
    """
    examples = load_examples()
    wanted = _normalize(topic)
    for key, example in examples.items():
        names = {_normalize(key), _normalize(example.topic)}
        if any(wanted == n or wanted.rstrip("s") == n.rstrip("s") or n in wanted for n in names):
            return CodeExampleResult(found=True, example=example, available_topics=list(examples))
    return CodeExampleResult(found=False, available_topics=list(examples))
