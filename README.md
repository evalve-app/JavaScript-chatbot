# StudyBot

StudyBot is a chat assistant for learning JavaScript. It explains concepts, finds bugs, writes code, and runs quizzes. Each teammate runs it on their own laptop with their own OpenAI key, and everyone's chats are saved to one shared Neon database. Each turn can be recorded to Kitaru for replay and testing.

Built with React and Vite on the front end, FastAPI and PydanticAI on the back end, OpenAI models, and Neon PostgreSQL with pgvector.

## How a message is handled

1. A classifier agent decides whether the question is about JavaScript and what kind it is: concept, debugging, code generation, or quiz.
2. Off-topic questions get a fixed, polite reply. Nothing else runs.
3. JavaScript questions go to the tutor agent. It can search the lesson library, fetch a code example, or look up a mock student's progress.
4. The question, the answer, and a log of what happened are saved to the database.

## Where to change things

| To change | Edit |
|---|---|
| Any prompt or fixed reply | `backend/app/agents/prompts.py` |
| The model | `OPENAI_MODEL` in `backend/.env` |
| The step-by-step flow | `backend/app/agents/workflow.py` |
| A tool | `backend/app/tools/` (one file each) |
| Lessons | `backend/data/lessons/`, then re-run ingestion |
| Code examples | `backend/data/examples.json` |
| Test questions | `backend/data/test_scenarios.json` |

## Set up

You need Python 3.12, [uv](https://docs.astral.sh/uv/), Node 20+, and your own OpenAI API key. Ask a teammate for the shared Neon database URL.

```bash
cd backend
uv sync
cp .env.example .env
```

In `backend/.env`, add your OpenAI key and the shared `DATABASE_URL`. If you copy the URL from Neon, change `postgresql://` to `postgresql+psycopg://`.

## Set up the shared database (one person, once)

Only one teammate needs to do this. Everyone else can skip it.

```bash
uv run python -m app.init_db     # creates the tables
uv run python -m app.seed        # adds 4 fake students
uv run python -m app.rag.ingest  # loads the lessons
```

All three are safe to run again. If you edit a lesson, run the ingest command again; it only re-embeds files that changed.

## Run it

Use two terminals:

```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 and type your display name. There's no password. Your name decides which chats you see, so pick one and keep using it. Two people who use the same name will share a chat history.

## Settings in `backend/.env`

| Setting | What it is |
|---|---|
| `OPENAI_API_KEY` | Your own key. You pay for your own usage. |
| `DATABASE_URL` | The team's shared Neon database. |
| `OPENAI_MODEL` | Which model answers. Defaults to `gpt-4o-mini`. |
| `HISTORY_LIMIT` | How many earlier messages go to OpenAI with each question. Enough for follow-ups, small enough to keep costs flat. Defaults to 10. |

Keep the database URL out of git. It contains the password, and anyone who has it can read every chat.

## Tests

The tests use a local PostgreSQL database and fake AI responses, so they cost nothing and never touch Neon.

```bash
createdb studybot_test
psql -d studybot_test -c "CREATE EXTENSION IF NOT EXISTS vector"
cd backend && uv run pytest -q
```

## Kitaru

Recording and replay are optional and off by default. Setup and what a replay can change: [docs/kitaru.md](docs/kitaru.md).

## Not built yet, on purpose

Cloud hosting, streaming replies, passwords or user accounts, database migrations, and an automatic answer checker.
