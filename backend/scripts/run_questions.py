"""Send the test questions in data/questions.json to the running StudyBot API.

Each question gets its own conversation; multi-turn questions send their turns in order.
Results (answer, route, tools, Kitaru status/session) are written to a JSON file.

    uv run python scripts/run_questions.py                 # all questions
    uv run python scripts/run_questions.py --ids 1 7 33    # some questions
"""

import argparse
import json
import sys
from pathlib import Path

import httpx

QUESTIONS = Path(__file__).resolve().parent.parent / "data" / "questions.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--user", default="question-runner", help="display name to log in as")
    parser.add_argument("--ids", type=int, nargs="*", help="only run these question ids")
    parser.add_argument("--out", default="question_results.json")
    args = parser.parse_args()

    questions = json.loads(QUESTIONS.read_text())
    if args.ids:
        questions = [p for p in questions if p["id"] in args.ids]

    results = []
    with httpx.Client(base_url=args.base_url, timeout=180) as client:
        client.post("/api/auth/login", json={"display_name": args.user}).raise_for_status()
        for question in questions:
            conversation_id = None
            turns = []
            for text in question["turns"]:
                body = {"message": text, "conversation_id": conversation_id}
                resp = client.post("/api/chat", json=body)
                data = resp.json()
                conversation_id = data.get("conversation_id", conversation_id)
                turns.append({"message": text, "status_code": resp.status_code, **data})
            last = turns[-1]
            print(
                f"#{question['id']:>2} {question['group']:<20} route={last.get('route')!s:<16} "
                f"kitaru={last.get('kitaru_status')} http={last['status_code']}",
                flush=True,
            )
            results.append({**question, "conversation_id": conversation_id, "results": turns})
            Path(args.out).write_text(json.dumps(results, indent=2))  # save as we go

    not_recorded = [r["id"] for r in results if r["results"][-1].get("kitaru_status") != "recorded"]
    print(f"\nSaved {len(results)} questions to {args.out}")
    if not_recorded:
        print(f"Not recorded in Kitaru: {not_recorded}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
