"""Integration tests for persisted per-user conversation history."""

from __future__ import annotations

from uuid import uuid4

import pytest

from backend.pg_config import AUTH_SCHEMA, COPILOT_SCHEMA
from backend.services.conversation_history import (
    ActionDecisionError,
    ConversationNotFoundError,
    create_conversation,
    get_owned_conversation,
    list_conversations,
    read_history_window,
    record_turn_action_decision,
    save_turn,
    validate_turn_action,
)
from backend.services.pg_database import connect


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
                f"history_test_{suffix}_first",
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
                f"history_test_{suffix}_second",
                "integration-test-not-a-real-password-hash",
            ),
        ).fetchone()

    return int(first["id"]), int(second["id"])


def delete_test_users(user_ids: list[int]) -> None:
    """Remove only conversations and users created by this test."""

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


def test_conversation_crud_pagination_and_user_isolation() -> None:
    user_ids: list[int] = []

    try:
        first_user, second_user = create_test_users()
        user_ids = [first_user, second_user]

        first_conversation = create_conversation(first_user)
        second_conversation = create_conversation(second_user)

        first_turn = save_turn(
            first_user,
            first_conversation["id"],
            question="How is ORD-120 doing?",
            answer="ORD-120 is currently in production.",
            response_json={
                "tools_used": ["get_order_status"],
            },
        )
        second_turn = save_turn(
            first_user,
            first_conversation["id"],
            question="Why is it risky?",
            answer="It has had no recent movement.",
            response_json={
                "tools_used": ["trace_order"],
            },
        )
        third_turn = save_turn(
            first_user,
            first_conversation["id"],
            question="What should I do next?",
            answer="Review the current production constraint.",
        )

        save_turn(
            second_user,
            second_conversation["id"],
            question="Which orders are at risk?",
            answer="This belongs only to the second user.",
        )

        # Each user lists only their own conversations.
        first_list = list_conversations(first_user)
        second_list = list_conversations(second_user)

        assert [row["id"] for row in first_list] == [
            first_conversation["id"]
        ]
        assert [row["id"] for row in second_list] == [
            second_conversation["id"]
        ]
        assert first_list[0]["turn_count"] == 3
        assert second_list[0]["turn_count"] == 1

        # The first question becomes the conversation title.
        owned = get_owned_conversation(
            first_user,
            first_conversation["id"],
        )
        assert owned["title"] == "How is ORD-120 doing?"

        # The newest two turns are returned in display order.
        first_page = read_history_window(
            first_user,
            first_conversation["id"],
            limit=2,
        )
        assert [
            turn["turn_number"] for turn in first_page["turns"]
        ] == [2, 3]
        assert first_page["next_before_turn_id"] == second_turn["id"]

        # The cursor retrieves the remaining older turn without duplication.
        second_page = read_history_window(
            first_user,
            first_conversation["id"],
            limit=2,
            before_turn_id=first_page["next_before_turn_id"],
        )
        assert [
            turn["turn_number"] for turn in second_page["turns"]
        ] == [1]
        assert second_page["turns"][0]["id"] == first_turn["id"]
        assert second_page["next_before_turn_id"] is None

        assert third_turn["turn_number"] == 3

        # Another user must not be able to read or write this conversation.
        with pytest.raises(ConversationNotFoundError):
            get_owned_conversation(
                second_user,
                first_conversation["id"],
            )

        with pytest.raises(ConversationNotFoundError):
            read_history_window(
                second_user,
                first_conversation["id"],
            )

        with pytest.raises(ConversationNotFoundError):
            save_turn(
                second_user,
                first_conversation["id"],
                question="Attempted cross-user write",
                answer="This must not be saved.",
            )
    finally:
        if user_ids:
            delete_test_users(user_ids)


def test_action_decision_persistence_and_user_isolation() -> None:
    user_ids: list[int] = []

    try:
        first_user, second_user = create_test_users()
        user_ids = [first_user, second_user]

        conversation = create_conversation(first_user)

        proposal = {
            "type": "create_watch",
            "order_id": "ORD-005",
            "condition_type": "NO_MOVEMENT",
            "check_date": "2026-04-02",
            "message": "Tell me if ORD-005 has not moved.",
        }

        turn = save_turn(
            first_user,
            conversation["id"],
            question="Tell me if ORD-005 hasn't moved by Thursday",
            answer="Please confirm the proposed watch.",
            response_json={
                "proposed_actions": [proposal],
            },
        )

        validated = validate_turn_action(
            first_user,
            turn["id"],
            action={**proposal, "_turn_id": turn["id"]},
        )
        assert validated == proposal

        # Another user cannot validate or execute this proposal.
        with pytest.raises(ConversationNotFoundError):
            validate_turn_action(
                second_user,
                turn["id"],
                action={**proposal, "_turn_id": turn["id"]},
            )

        # The owner cannot replace the stored proposal with another action.
        with pytest.raises(ActionDecisionError):
            validate_turn_action(
                first_user,
                turn["id"],
                action={
                    **proposal,
                    "order_id": "ORD-999",
                    "_turn_id": turn["id"],
                },
            )

        # Another user cannot update this decision.
        with pytest.raises(ConversationNotFoundError):
            record_turn_action_decision(
                second_user,
                turn["id"],
                action={**proposal, "_turn_id": turn["id"]},
                status="confirmed",
                summary="Watch saved.",
            )

        # Even the owner cannot substitute a different action.
        with pytest.raises(ActionDecisionError):
            record_turn_action_decision(
                first_user,
                turn["id"],
                action={
                    **proposal,
                    "order_id": "ORD-999",
                    "_turn_id": turn["id"],
                },
                status="confirmed",
                summary="Watch saved.",
            )

        record_turn_action_decision(
            first_user,
            turn["id"],
            action={**proposal, "_turn_id": turn["id"]},
            status="confirmed",
            summary="Watch saved.",
        )

        history = read_history_window(
            first_user,
            conversation["id"],
        )
        restored = history["turns"][0]["response_json"]

        assert restored["proposed_actions"] == []
        assert restored["decision"]["status"] == "confirmed"
        assert restored["decision"]["summary"] == "Watch saved."
        assert restored["decision"]["action"] == proposal
    finally:
        if user_ids:
            delete_test_users(user_ids)