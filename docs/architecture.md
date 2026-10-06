# Architecture — SweaterCo General Manager's Co-Pilot

This document describes the current integrated application. Read it before
changing runtime behaviour, database ownership, authentication, or Agent state.

## System boundary

SweaterCo is a grounded, tool-using Agent rather than a general chatbot. The
manager asks an operational question, deterministic code decides whether the
stored data and registered tools can support it, LangGraph selects tools when
needed, and Python services compute business results.

```text
Authenticated manager
        |
        v
React UI
        |
        | access token + conversation UUID
        v
FastAPI
        |-- verify user and conversation ownership
        |-- answerability and deterministic routing
        |-- LangGraph ReAct Agent
        |-- conversation history persistence
        `-- explicit action confirmation
                |
                v
PostgreSQL
        |-- app.*                 factory facts
        |-- admin_meta.*          data-management metadata
        |-- auth.users            application identities
        |-- copilot.conversations visible conversation list
        |-- copilot.chat_turns    visible user/assistant turns
        |-- copilot.checkpoint_*  LangGraph state
        `-- copilot operational tables and audit log
```

The dataset clock is `FACTORY_TODAY = 2026-04-01`. Business calculations use
that value or an explicit factory `as_of` date, not `date.today()`.

## Layer responsibilities

| Layer | Main location | Owns | Must not own |
|---|---|---|---|
| UI | `frontend/` | Rendering, navigation, local interaction state | SQL, business calculations |
| API | `backend/main.py`, `backend/routers/` | HTTP contracts, authentication dependencies, status codes | Hidden judgement rules |
| Agent | `backend/agent/` | Tool selection and grounded final wording | Invented fields or business arithmetic |
| Tools | `backend/tools/` | Typed Agent-facing wrappers | Database schema management |
| Services | `backend/services/` | Runtime queries, transactions, calculations | Alembic migrations |
| Database module | `postgresql_database/` | Roles, migrations, checkpoint bootstrap, seed and DB tests | HTTP and UI behaviour |
| Semantic layer | `data/semantic_layer.yaml` | Stored-field meanings and defined terms | Formulas and mutable state |

`SQL_related_app` is a separate data-administration component. It can update the
shared operational dataset, but it does not own authentication, Manager chat
history, or LangGraph memory.

## Database ownership

The canonical structure is managed under `postgresql_database/`:

1. `sql/01_roles_and_database.sql` creates roles and the project database.
2. Alembic migrations create schemas, tables, constraints, indexes, and grants.
3. `bootstrap/setup_checkpoints.py` lets the official `PostgresSaver` create its
   version-compatible checkpoint tables in the `copilot` schema.
4. Seed, validation, and permission scripts reproduce and verify local data.

FastAPI checks that the operational baseline exists, but it does not run
migrations or create checkpoint tables during startup.

The runtime uses two database identities:

- `factory_agent` inherits read-only access to `app` for normal factory queries.
- `factory_admin` is the trusted identity for authentication, conversation
  persistence, confirmed operations, and administrative data changes.

Ordinary login roles cannot read `auth`, `admin_meta`, or `copilot` directly.
Website users access those schemas only through authenticated API routes.

## Authenticated conversation flow

```text
1. Browser sends POST /api/chat with an access token, message, and UUID.
2. FastAPI derives the current user from the token.
3. The service verifies (conversation UUID, user ID) ownership.
4. The server builds user:{user_id}:conversation:{uuid}.
5. LangGraph loads the matching PostgreSQL checkpoint.
6. The Agent answers and PostgresSaver commits graph state.
7. The API saves the visible question, answer, traces, and proposals in chat_turns.
8. The frontend refreshes the conversation list and renders the response.
```

Unknown conversations and conversations owned by another user both return 404,
so the API does not disclose whether another user's UUID exists.

### Two complementary histories

`copilot.chat_turns` and `copilot.checkpoint_*` are not duplicates:

- `chat_turns` is a stable application record used to rebuild message bubbles,
  traces, action proposals, and decisions.
- checkpoint tables are LangGraph's internal state used for Human, AI, and Tool
  context during follow-up questions.

Short-circuited answers that do not execute a full Agent invocation are also
appended to checkpoint state so later questions see a continuous conversation.

## Frontend restoration flow

After authentication, the frontend:

1. clears any previous user's in-memory messages;
2. fetches only the current user's conversation list;
3. restores the user-specific last-opened conversation ID when it still exists;
4. otherwise opens the newest conversation;
5. creates a blank conversation if no history exists;
6. fetches its history and reconstructs the message bubbles.

History requests have cancellation guards so a slow response for an older
selection cannot overwrite a newer selection. Switching and creating
conversations are disabled while a chat request is running; simultaneous
in-flight conversations are outside the current scope.

## Action confirmation flow

The Agent may propose an action but cannot silently execute it.

```text
Agent proposal
    |
    v
chat_turns.response_json.proposed_actions
    |
    +-- Confirm --> validate ownership and proposal --> execute whitelist tool
    |                                             `--> persist confirmed decision
    |
    `-- Dismiss --> validate ownership and proposal --> do not execute tool
                                                  `--> persist dismissed decision
```

The validation joins `chat_turns` to `conversations` and checks the authenticated
user. The client-only `_turn_id` is removed before comparing the submitted
action with the stored proposal.

Confirmed business effects are stored in their operational tables, such as
`watches`, `reminders`, or `order_notes`. The UI decision is separately stored
inside the originating turn's `response_json`. This is why both the operation
and its resolved button state survive a refresh.

Email remains simulated and never claims an SMTP delivery. One turn currently
resolves its proposed-action list as a single decision; independently resolving
several proposals from one assistant message is not supported.

## Agent and tools

The registered tool families are:

- retrieval: order status and risk lists;
- judgement: feasibility estimation;
- tracing: source fields and calculations;
- discovery: filtered orders and ranked factory issues;
- briefing: structured current operating facts;
- actions: drafts, simulated email, notes, reminders, and watches;
- audit: recent confirmed or declined operations.

The Agent reports only tools used after the latest user message. It must not
reuse stale tool names from an earlier turn as if they were called again.

If no LLM key is configured, deterministic endpoints and tests still work.
An in-scope `/api/chat` request that requires the LLM returns 503. Unsupported
questions can be rejected locally without making an LLM call.

## Watches and reminders

`create_reminder` stores a calendar note. Python does not parse or continuously
evaluate its free-text message.

`create_watch` stores a typed condition. The current
`ORDER_INACTIVE_BY_DATE` condition is evaluated when `GET /api/watches` runs
with an explicit or default factory date. There is no background scheduler.
Cancelling retains the row as `CANCELLED`; firing creates one `watch_events`
record and uses the local notifier implementation.

## Intentional limits

- No real SMTP, calendar, or push integration.
- No background scheduler for briefings or watches.
- No conversation rename, delete, sharing, or cross-conversation memory.
- No concurrent background requests in several conversations.
- No standalone `assess_stage_performance` tool beyond the documented baseline
  comparison reused by briefing and discovery.
- No held-out accuracy claim from `evaluation/questions.json`; it remains a
  development and few-shot wording resource.

## Adding a tool

1. Put deterministic calculations and data access in `backend/services/`.
2. Add a typed `@tool` wrapper under `backend/tools/`.
3. Return an inspectable success or failure payload with trace evidence.
4. Register the tool in `backend/tools/registry.py`.
5. Add tests that do not require an LLM call.
6. Document purpose, input, output, non-goals, and failure modes in
   `docs/tool_spec.md`.

Schema changes follow a separate path: add a reviewed Alembic revision under
`postgresql_database/migrations/versions/`, then run migration, permission, and
repository tests before application tests.
