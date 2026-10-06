# SweaterCo General Manager's Co-Pilot

SweaterCo is a DSS5105 Track 1 project for a small knitwear factory. It is a
tool-using LangGraph agent with a FastAPI backend, a React manager interface,
and PostgreSQL persistence. It is not a general-purpose chatbot.

The factory date represented by the supplied dataset is **2026-04-01**.
Business rules use this factory date or an explicit `as_of` date; they must not
silently use the computer clock.

[Chinese documentation / 中文说明](README_CN.md)

## Current capabilities

- Authenticated `ADMIN` and `EMPLOYEE` accounts.
- PostgreSQL-backed factory, administration, authentication, Copilot, and
  conversation data.
- Retrieval, judgement, tracing, discovery, briefing, and action tools.
- Per-user conversation lists and persisted chat turns.
- Conversation restoration after refresh, browser reopen, or backend restart.
- PostgreSQL-backed LangGraph checkpoints for multi-turn context.
- User-scoped model thread keys, so users and conversations do not share memory.
- Explicit Confirm/Dismiss handling for side-effecting actions.
- Persisted confirmation decisions, so resolved action buttons do not reappear
  after a history reload.
- Inspectable source rows and calculations through the **Why?** trace view.

## Architecture at a glance

```text
React manager UI
    |
    | Bearer token + conversation UUID
    v
FastAPI API
    |-- authentication and user ownership checks
    |-- conversation history API
    |-- deterministic routing and answerability checks
    |-- LangGraph agent and business tools
    `-- explicit action confirmation endpoints
             |
             v
PostgreSQL: factory_copilot_db
    |-- app          factory operational data
    |-- admin_meta   import and data-source metadata
    |-- auth         application users
    `-- copilot      operations, conversations, and checkpoints
```

Deterministic Python code computes dates, totals, risk flags, feasibility, and
briefing facts. The LLM selects supported tools and explains their results; it
must not invent unavailable fields or perform hidden business arithmetic.

## Persistence model

| Data | PostgreSQL location | Purpose |
|---|---|---|
| Orders, production, workshops, snapshots | `app.*` | Factory facts queried by the tools |
| Upload history and data sources | `admin_meta.*` | Data-administration state |
| Accounts and account lifecycle | `auth.users` | Login, role, approval, and deactivation |
| Notes, reminders, watches, audit events | `copilot.*` | Confirmed operational actions |
| Conversation list and visible turns | `copilot.conversations`, `copilot.chat_turns` | History shown to the manager |
| LangGraph state | `copilot.checkpoint_*` | Human, AI, and tool context used for follow-up questions |

Visible chat history and LangGraph checkpoints are intentionally separate. The
former reconstructs the UI; the latter restores the Agent's internal context.
Both survive backend restarts.

## Conversation history

Conversation endpoints require authentication:

| Endpoint | Purpose |
|---|---|
| `POST /api/conversations` | Create a conversation for the current user |
| `GET /api/conversations?limit=50` | List only the current user's conversations |
| `GET /api/conversations/{id}` | Read an owned conversation and a paginated turn window |
| `POST /api/chat` | Run the Agent in an owned conversation and persist the successful turn |

The server never trusts a client-supplied user ID. It derives the user from the
access token, verifies conversation ownership, and builds the LangGraph key as:

```text
user:{authenticated_user_id}:conversation:{conversation_uuid}
```

The first successful question becomes the conversation title. The frontend
stores the last-opened conversation ID under a user-specific browser key,
reloads its history after login, and creates an empty conversation when the
user has no history.

Current scope does not include conversation rename, delete, sharing, or several
simultaneous in-flight chats. Conversation switching is disabled while a chat
request is running to prevent an old response from being rendered in a newly
selected conversation.

## Confirmed actions

Side-effecting tools follow this lifecycle:

```text
proposal -> explicit Confirm or Dismiss -> persisted decision
```

`POST /api/actions/confirm` validates that the proposed action belongs to a
chat turn owned by the authenticated user, executes the whitelisted operation,
and stores the decision in that turn's `response_json`.
`POST /api/actions/decline` records the dismissal without executing the proposed
operation. Refreshing the page restores the resolved state instead of showing
the same buttons again.

The current action whitelist covers `create_watch`, `cancel_watch`,
`send_email`, `add_order_note`, and `create_reminder`. Email remains simulated:
the system writes an audit result but does not send SMTP mail.

## Tools

| Kind | Tool | Purpose |
|---|---|---|
| Retrieval | `get_order_status` | Retrieve one order, asking for an ID when a description is ambiguous |
| Retrieval | `get_orders_at_risk` | Find overdue, stalled, and tight-deadline orders |
| Judgement | `check_feasibility` | Estimate whether a proposed order fits available capacity |
| Tracing | `trace_order` | Return source fields, computed fields, and risk evidence |
| Discovery | `find_orders` | Apply manager-supplied filters |
| Discovery | `discover_factory_issues` | Rank defined order and production issues |
| Briefing | `get_morning_briefing` | Return structured morning operating facts |
| Action | `draft_chase_email` | Produce a local draft without sending it |
| Action | `send_email` | Propose and simulate a confirmed email action |
| Action | `add_order_note` | Propose and persist an order note after confirmation |
| Action | `create_reminder` | Propose and persist a calendar note after confirmation |
| Action | `create_watch`, `list_watches`, `cancel_watch` | Manage locally evaluated standing watches |
| Audit | `get_recent_actions` | Read recent Copilot action records |

`production_log` has factory-wide `date x stage` granularity; it is not an
order-level event log.

## Standing watches

The implemented watch condition is `ORDER_INACTIVE_BY_DATE`. A watch is
evaluated when `GET /api/watches?as_of=YYYY-MM-DD` runs. This is local,
request-driven evaluation, not a background scheduler or real-time push system.

- A fired watch produces a `watch_events` row and an audit record.
- The same watch cannot fire twice.
- Cancelling retains the row with `status=CANCELLED`; it does not delete history.
- `LocalWatchNotifier` is the current notification implementation. There is no
  email or push delivery.
- A reminder is a stored calendar note and is not evaluated like a watch.

## Repository layout

```text
backend/               FastAPI, LangGraph, tools, and runtime services
frontend/              React, Vite, and Tailwind manager UI
data/                  Source data, examples, and semantic definitions
docs/                  Architecture and tool contracts
evaluation/            Development question set and evaluation material
postgresql_database/   Database lifecycle, migrations, seed data, and DB tests
SQL_related_app/       Separate data-administration middleware
tests/                 Backend and API tests
```

`SQL_related_app` remains a separate administration component. It may update
shared factory data, but it does not own Manager conversation history.

## Prerequisites

- Python 3.12 is recommended for the project virtual environment.
- Node.js 18 or later.
- A local PostgreSQL server and `psql`.
- A Gemini or OpenAI-compatible API key only when running LLM-backed chat.

Tests that do not call the LLM can run without an LLM key. PostgreSQL integration
tests require a configured local test database.

## Local setup

### 1. Create the Python environment

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
copy .env.example .env
```

Fill the local `.env` with database credentials, an
`AUTH_SECRET_KEY` of at least 32 characters, and the selected LLM provider key.
Never commit `.env`.

### 2. Prepare PostgreSQL

Follow [postgresql_database/README.md](postgresql_database/README.md) for role,
database, migration, seed, validation, and permission-test commands. The core
sequence is:

```powershell
.\.venv\Scripts\python.exe -m alembic -c postgresql_database\alembic.ini upgrade head
.\.venv\Scripts\python.exe postgresql_database\bootstrap\setup_checkpoints.py
```

Alembic and checkpoint setup are explicit administration steps. FastAPI does
not create or migrate database tables at startup.

### 3. Start the backend

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
```

Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### 4. Start the frontend

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies `/api` to
port 8000.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest postgresql_database\tests -q
npm --prefix frontend run build
git diff --check
```

See the database README for data-validation and permission-test SQL scripts.

## Known limits

- The morning briefing and standing watches have no background scheduler.
- Email, calendar, and push integrations are local simulations only.
- `assess_stage_performance` is not a standalone tool; discovery and briefing
  use the documented production-baseline heuristic.
- `evaluation/questions.json` is a development/few-shot wording bank, not a
  held-out accuracy benchmark.
- One assistant turn currently resolves its proposed-action list as one decision;
  independent confirmation of several actions in the same turn is not supported.

## Development rules

1. Do not invent fields or business facts absent from the stored data and
   `data/semantic_layer.yaml`.
2. Keep arithmetic and business rules in deterministic Python services, not in
   prompts.
3. Require explicit confirmation before every side-effecting operation.
4. Do not claim that an external message or notification was sent.
5. Apply schema changes through reviewed Alembic migrations; do not create
   tables during normal application startup.

Read [docs/architecture.md](docs/architecture.md) and
[docs/tool_spec.md](docs/tool_spec.md) before changing system behaviour.
