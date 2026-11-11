# Recording and replaying StudyBot with Kitaru

StudyBot records each chat turn as one Kitaru session, and Kitaru can replay those turns. Recording is off until you set `KITARU_AGENT_ID`. The code lives in `backend/app/recording/` and `backend/app/kitaru_entry.py`.

## What one session holds

```
invoke_agent studybot                    span      inputs: {"turns": [..., {"inputs": question}]}
└─ invoke_agent tutor                    span      inputs: question; outputs: answer
   ├─ chat gpt-4o-mini                   llm_call
   ├─ execute_tool search_lessons        tool_call full lesson text
   │  └─ retrieve lessons                span      pgvector search: document ids + scores
   │     └─ embeddings text-embedding-3-small  llm_call  tokens, vector size (not the vector)
   └─ chat gpt-4o-mini                   llm_call
```

Names follow the OpenTelemetry GenAI conventions (`invoke_agent`, `chat`, `execute_tool`, `embeddings`), and every node carries matching `gen_ai.*` attributes. Retrieval is shaped like OpenInference (Arize Phoenix): a RETRIEVER span with its EMBEDDING call inside. Replay details use `replay.*` attributes (`replay.policy`, `replay.mocked`, `replay.override`). A tool answered from history has no retrieval children, because nothing was fetched.

Developer details in the app shows each answer's Kitaru status: `disabled`, `recorded`, `partial` (incomplete, marked failed in Kitaru), or `unrecorded` (Kitaru was unreachable; the chat still answered).

## Turn on recording

```bash
kitaru login https://YOUR-KITARU-SERVER
cd backend
kitaru agent register studybot \
  --command "uv run python -m app.kitaru_entry" \
  --working-dir "$PWD" \
  --timeout-seconds 300 \
  --description "StudyBot JavaScript tutor: one tutor agent with tools"
kitaru agent list          # copy the studybot id
```

Put the id in `backend/.env` as `KITARU_AGENT_ID`, then restart the backend. A `kitaru login` expires, so for long-running use create an API key and set `KITARU_API_URL` and `KITARU_API_KEY` instead.

## Run a worker

Replays run on a worker that has this code, your OpenAI key, and the database URL. Your laptop works:

```bash
cd backend
kitaru worker start --claim agent --concurrency 10
```

The worker runs `app/kitaru_entry.py` once per replayed session. It reads the recorded question and history, answers again, records a `replay` session, and never writes to the chat database. Exit code 0 means success, 1 means the turn or the recording failed, and 2 means the replay was rejected before anything ran.

Try the entry script without Kitaru: `uv run python -m app.kitaru_entry "Explain closures"`.

## What a replay can change

| Override | Effect |
|---|---|
| `model` | A string swaps every model call. Use a map such as `{"gpt-4o-mini": "gpt-4.1-mini"}` to target one model. OpenAI models only. |
| `model_params` | `temperature`, `top_p`, `max_tokens`, `seed` |
| `prompt` | Replaces the question for the whole turn |
| `system_prompt` | Replaces the tutor's whole prompt, including scope and task rules. |

| Tool policy | Effect |
|---|---|
| `passthrough` | Runs the real tool (the default). All three tools only read data. |
| `history` | Returns the recorded result for the same tool and arguments |
| `static` | Returns a result you define, matched `exact` or `subset` |
| `llm` | Rejected |

A miss follows `on_miss`: `fail`, `error_result`, or `passthrough`. Anything unsupported is rejected before the first model call.

## Running an experiment

An experiment replays a group of recorded turns (a cohort) with one change, scores the originals and the replays with the same evaluators, and shows what improved and what regressed. The experiment holds the change (override, tool policy, evaluators). Each experiment run picks one cohort version and one agent version, so the same experiment can be re-run on a new candidate.

### Override or new version?

Use an override for the model, `model_params`, the question, or the tutor's prompt. Anything else needs a new agent version: tools, lessons, any code.

### Make a candidate version

A version stores how to run the code (command and folder), not the code itself. Kitaru's docs put it this way: "reproducibility also requires the worker to use the intended checkout, commit, or container image." So each candidate gets its own git worktree, and only committed code ends up in it.

1. Commit everything on your main checkout first. That commit is the baseline.
2. Create a worktree and branch for the candidate, make one change, and commit it:

```bash
cd ~/projects/capstone-prototypes/lsbot-app
git worktree add ../studybot-exp/fix-sure -b exp/fix-sure
cd ../studybot-exp/fix-sure/backend
# edit one thing, for example app/agents/prompts.py
git commit -am "Classifier: 'sure' after a JavaScript offer is in scope"
uv sync
cp ~/projects/capstone-prototypes/lsbot-app/backend/.env .
```

3. Register the folder as a new version, labelled with the branch and commit:

```bash
kitaru agent version register studybot \
  --command "uv run python -m app.kitaru_entry" \
  --working-dir "$PWD" \
  --timeout-seconds 300 \
  --display-version "fix-sure-$(git rev-parse --short HEAD)" \
  --description "Classifier: treat 'sure' after a JavaScript offer as in scope" \
  --tool search_lessons --tool get_code_example --tool get_mock_progress
```

Treat a registered version as frozen. To change it, commit again and register another version. Don't edit or delete a worktree while experiments still use its version.

### Run it

Use the same evaluators for both sides (`--evaluate-baselines`) and change one thing per experiment. For lesson search, a `history` policy with `on_miss: fail` keeps lesson results out of the comparison:

```json
{"default": {"type": "passthrough"}, "tools": {"search_lessons": {"type": "history", "scope": "cohort_version", "on_miss": "fail"}}}
```

One worker serves every version, because each task runs in its own version's folder. Read the result as improved, regressed, trade-off, or inconclusive.

### Adopt the change

Merge the branch into main, register a new version for the main folder, put its id in `backend/.env` as `KITARU_AGENT_VERSION_ID`, and restart the backend. The live app's sessions are then labelled with the code that actually produced them. Remove old worktrees with `git worktree remove` once no experiment needs them.

## Not verified yet

Everything above is tested with fake models and a fake Kitaru server. Two things still need a real server: that sessions appear as expected, and that `history` lookups find the recorded tool calls (that depends on the server computing the same cache key from the recorded tool inputs).
