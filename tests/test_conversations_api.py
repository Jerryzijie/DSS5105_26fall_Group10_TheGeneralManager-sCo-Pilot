"""Authenticated conversation API and ownership-isolation tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt
from fastapi.testclient import TestClient

import backend.main as main_module
from backend.main import app
from backend.pg_config import AUTH_SCHEMA, COPILOT_SCHEMA
from backend.services.conversation_history import save_turn
from backend.services.pg_database import connect


TEST_SECRET = "conversation-api-test-secret-at-least-32-characters"


def create_test_users() -> tuple[int, int]:
    suffix = uuid4().hex

    with connect(admin=True) as connection, connection.transaction():
        first = connection.execute(
            f"""
            INSERT INTO {AUTH_SCHEMA}.users (
                username,
                password_hash,
                role,
                status
            )
            VALUES (%s, %s, 'EMPLOYEE', 'ACTIVE')
            RETURNING id
            """,
            (
                f"conversation_api_{suffix}_first",
                "integration-test-not-a-real-password-hash",
            ),
        ).fetchone()

        second = connection.execute(
            f"""
            INSERT INTO {AUTH_SCHEMA}.users (
                username,
                password_hash,
                role,
                status
            )
            VALUES (%s, %s, 'EMPLOYEE', 'ACTIVE')
            RETURNING id
            """,
            (
                f"conversation_api_{suffix}_second",
                "integration-test-not-a-real-password-hash",
            ),
        ).fetchone()

    return int(first["id"]), int(second["id"])


def auth_headers(user_id: int) -> dict[str, str]:
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(user_id),
            "role": "EMPLOYEE",
            "iat": now,
            "exp": now + timedelta(minutes=10),
        },
        TEST_SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def delete_test_users(user_ids: list[int]) -> None:
    with connect(admin=True) as connection, connection.transaction():
        connection.execute(
            f"""
            DELETE FROM {COPILOT_SCHEMA}.conversations
            WHERE user_id = ANY(%s)
            """,
            (user_ids,),
        )
        connection.execute(
            f"""
            DELETE FROM {AUTH_SCHEMA}.users
            WHERE id = ANY(%s)
            """,
            (user_ids,),
        )


def test_conversation_api_authentication_and_isolation(
    monkeypatch,
) -> None:
    user_ids: list[int] = []

    monkeypatch.setenv("AUTH_SECRET_KEY", TEST_SECRET)
    monkeypatch.setattr(
        main_module,
        "llm_is_configured",
        lambda: False,
    )

    try:
        first_user, second_user = create_test_users()
        user_ids = [first_user, second_user]

        first_headers = auth_headers(first_user)
        second_headers = auth_headers(second_user)

        with TestClient(app) as client:
            # Conversation endpoints require authentication.
            unauthorized = client.get("/api/conversations")
            assert unauthorized.status_code == 401

            created = client.post(
                "/api/conversations",
                headers=first_headers,
            )
            assert created.status_code == 201, created.text

            created_body = created.json()
            conversation_id = UUID(created_body["id"])
            assert created_body["title"] == "New conversation"
            assert created_body["turn_count"] == 0

            # Add one persisted turn without calling an external LLM.
            save_turn(
                first_user,
                conversation_id,
                question="How is ORD-120 doing?",
                answer="ORD-120 is currently in production.",
                response_json={
                    "tools_used": ["get_order_status"],
                },
            )

            first_list = client.get(
                "/api/conversations",
                headers=first_headers,
            )
            assert first_list.status_code == 200
            assert len(first_list.json()) == 1
            assert first_list.json()[0]["id"] == str(conversation_id)
            assert first_list.json()[0]["turn_count"] == 1
            assert (
                first_list.json()[0]["title"]
                == "How is ORD-120 doing?"
            )

            history = client.get(
                f"/api/conversations/{conversation_id}",
                headers=first_headers,
            )
            assert history.status_code == 200
            history_body = history.json()
            assert history_body["conversation"]["id"] == str(
                conversation_id
            )
            assert len(history_body["turns"]) == 1
            assert (
                history_body["turns"][0]["question"]
                == "How is ORD-120 doing?"
            )

            # The second user cannot discover the first user's conversation.
            second_list = client.get(
                "/api/conversations",
                headers=second_headers,
            )
            assert second_list.status_code == 200
            assert second_list.json() == []

            hidden = client.get(
                f"/api/conversations/{conversation_id}",
                headers=second_headers,
            )
            assert hidden.status_code == 404
            assert hidden.json()["detail"] == "Conversation not found"

            # Chat is authenticated and checks ownership before LLM readiness.
            unauthenticated_chat = client.post(
                "/api/chat",
                json={
                    "message": "Why?",
                    "conversation_id": str(conversation_id),
                },
            )
            assert unauthenticated_chat.status_code == 401

            cross_user_chat = client.post(
                "/api/chat",
                headers=second_headers,
                json={
                    "message": "Why?",
                    "conversation_id": str(conversation_id),
                },
            )
            assert cross_user_chat.status_code == 404

            own_chat_without_llm = client.post(
                "/api/chat",
                headers=first_headers,
                json={
                    "message": "Why?",
                    "conversation_id": str(conversation_id),
                },
            )
            assert own_chat_without_llm.status_code == 503

            observed_call = {}
            proposal = {
                "type": "create_watch",
                "order_id": "ORD-005",
                "condition_type": "NO_MOVEMENT",
                "check_date": "2026-04-02",
                "message": "Tell me if ORD-005 has not moved.",
            }

            def fake_run_agent(
                message: str,
                public_id: str,
                *,
                thread_id: str | None = None,
            ) -> dict:
                observed_call.update(
                    message=message,
                    public_id=public_id,
                    thread_id=thread_id,
                )
                return {
                    "answer": "It is still in production.",
                    "conversation_id": public_id,
                    "tools_used": [],
                    "traces": [],
                    "proposed_actions": [proposal],
                    "limitation": None,
                    "routing_intent": "PROCEED",
                }

            monkeypatch.setattr(
                main_module,
                "llm_is_configured",
                lambda: True,
            )
            monkeypatch.setattr(
                main_module,
                "run_agent",
                fake_run_agent,
            )

            continued = client.post(
                "/api/chat",
                headers=first_headers,
                json={
                    "message": "Why?",
                    "conversation_id": str(conversation_id),
                },
            )
            assert continued.status_code == 200, continued.text
            continued_json = continued.json()
            returned_action = continued_json["proposed_actions"][0]
            assert observed_call == {
                "message": "Why?",
                "public_id": str(conversation_id),
                "thread_id": (
                    f"user:{first_user}:conversation:{conversation_id}"
                ),
            }

            continued_history = client.get(
                f"/api/conversations/{conversation_id}",
                headers=first_headers,
            )
            assert continued_history.status_code == 200
            continued_body = continued_history.json()
            assert continued_body["conversation"]["turn_count"] == 2
            assert continued_body["turns"][-1]["question"] == "Why?"
            assert (
                continued_body["turns"][-1]["answer"]
                == "It is still in production."
            )

            latest_turn = continued_body["turns"][-1]

            assert returned_action == {
                **proposal,
                "_turn_id": latest_turn["id"],
            }
            assert (
                latest_turn["response_json"]["proposed_actions"]
                == [proposal]
            )
            assert (
                "_turn_id"
                not in latest_turn["response_json"]["proposed_actions"][0]
            )

            cross_user_confirm = client.post(
                "/api/actions/confirm",
                headers=second_headers,
                json={"action": returned_action},
            )
            assert cross_user_confirm.status_code == 404
            assert (
                cross_user_confirm.json()["detail"]
                == "Chat turn not found"
            )
    finally:
        if user_ids:
            delete_test_users(user_ids)
