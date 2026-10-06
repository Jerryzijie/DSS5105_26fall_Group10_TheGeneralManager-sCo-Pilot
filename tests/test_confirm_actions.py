"""UI Confirm / Dismiss for proposed actions. No LLM."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.conversation_history import (
    create_conversation,
    read_history_window,
    save_turn,
)
from backend.services.watches import list_watches
from backend.tools.watches import create_watch
from tests.conftest import parse_tool


def _client(db, monkeypatch):
    monkeypatch.setattr("backend.main.init_db", lambda *args, **kwargs: db)
    return TestClient(app)


def _persist_action(test_user, action):
    conversation = create_conversation(test_user.id)

    turn = save_turn(
        test_user.id,
        conversation["id"],
        question="Test proposed action",
        answer="Please confirm or dismiss this action.",
        response_json={
            "proposed_actions": [action],
        },
    )

    persisted_action = {
        **action,
        "_turn_id": turn["id"],
    }

    return persisted_action, conversation["id"]


def test_ui_confirm_creates_watch(db, clean_state, test_user, monkeypatch, employee_auth_headers):
    proposed = parse_tool(
        create_watch.invoke(
            {
                "order_id": "ORD-005",
                "check_date": "2026-04-02",
                "confirmed": False,
            }
        )
    )
    action = proposed["data"]["proposed_action"]
    action, conversation_id = _persist_action(test_user, action,)
    with _client(db, monkeypatch) as client:
        res = client.post("/api/actions/confirm", json={"action": action}, headers=employee_auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["type"] == "create_watch"
    rows = list_watches()
    assert len(rows) == 1
    assert rows[0]["status"] == "ACTIVE"
    assert rows[0]["order_id"] == "ORD-005"
    history = read_history_window(test_user.id, conversation_id,)
    metadata = history["turns"][0]["response_json"]

    assert metadata["proposed_actions"] == []
    assert metadata["decision"]["status"] == "confirmed"


def test_ui_dismiss_does_not_create_watch(db, clean_state, test_user, monkeypatch, employee_auth_headers):
    proposed = parse_tool(
        create_watch.invoke(
            {
                "order_id": "ORD-005",
                "check_date": "2026-04-02",
                "confirmed": False,
            }
        )
    )
    action = proposed["data"]["proposed_action"]
    action, conversation_id = _persist_action(test_user, action,)
    with _client(db, monkeypatch) as client:
        res = client.post("/api/actions/decline", json={"action": action}, headers=employee_auth_headers)
    assert res.status_code == 200
    assert res.json()["declined"] is True
    assert list_watches() == []
    history = read_history_window(test_user.id, conversation_id,)
    metadata = history["turns"][0]["response_json"]

    assert metadata["proposed_actions"] == []
    assert metadata["decision"]["status"] == "dismissed"


def test_ui_confirm_rejects_unknown_type(db, clean_state, test_user, monkeypatch, employee_auth_headers):
    action, _ = _persist_action(test_user, {"type": "run_sql", "order_id": "ORD-005"},)
    with _client(db, monkeypatch) as client:
        res = client.post(
            "/api/actions/confirm",
            json={"action": action},
            headers=employee_auth_headers,
        )
    assert res.status_code == 400
    assert list_watches() == []


def test_ui_confirm_cancel_watch(db, clean_state, test_user, monkeypatch, employee_auth_headers):
    parse_tool(
        create_watch.invoke(
            {
                "order_id": "ORD-005",
                "check_date": "2026-04-02",
                "confirmed": True,
            }
        )
    )
    from backend.tools.watches import cancel_watch

    proposed = parse_tool(cancel_watch.invoke({"order_id": "ORD-005", "confirmed": False}))
    action = proposed["data"]["proposed_action"]
    action, _ = _persist_action(test_user, action,)
    with _client(db, monkeypatch) as client:
        res = client.post("/api/actions/confirm", json={"action": action}, headers=employee_auth_headers)
    assert res.status_code == 200
    assert list_watches()[0]["status"] == "CANCELLED"
