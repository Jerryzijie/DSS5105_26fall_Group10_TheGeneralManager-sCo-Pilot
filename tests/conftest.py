"""Shared fixtures for the PostgreSQL Phase 1 backend.

The session `db` fixture requires a live PostgreSQL baseline
(`alembic upgrade head` plus seed data). Tests that do not need a database
must not request this fixture.
"""

from __future__ import annotations

import json
import os
from uuid import uuid4

import pytest

TEST_AUTH_SECRET = "test-auth-secret-key-with-at-least-32-chars"

os.environ.setdefault("AUTH_SECRET_KEY", TEST_AUTH_SECRET)

from backend.services.database import get_db, init_db
from backend.services.auth import CurrentUser
from backend.services.pg_database import connect
from backend.services.request_context import set_current_user


@pytest.fixture(scope="session")
def db():
    init_db()
    return get_db()


def _create_active_user(role: str) -> CurrentUser:
    username = f"pytest_{role.lower()}_{uuid4().hex}"

    with connect(admin=True) as conn, conn.transaction():
        row = conn.execute(
            """
            INSERT INTO auth.users (
                username,
                password_hash,
                role,
                status
            )
            VALUES (%s, %s, %s, 'ACTIVE')
            RETURNING id
            """,
            (username, "pytest-only-not-for-login", role),
        ).fetchone()

    return CurrentUser(
        id=int(row["id"]),
        username=username,
        email=None,
        role=role,
        status="ACTIVE",
    )


def _delete_test_user(user_id: int) -> None:
    with connect(admin=True) as conn, conn.transaction():
        conn.execute(
            "DELETE FROM copilot.conversations WHERE user_id = %s",
            (user_id,),
        )
        conn.execute(
            "DELETE FROM copilot.watches WHERE user_id = %s",
            (user_id,),
        )
        conn.execute(
            "DELETE FROM copilot.order_notes WHERE user_id = %s",
            (user_id,),
        )
        conn.execute(
            "DELETE FROM copilot.reminders WHERE user_id = %s",
            (user_id,),
        )
        conn.execute(
            "DELETE FROM copilot.audit_log WHERE user_id = %s",
            (user_id,),
        )
        conn.execute(
            "UPDATE auth.users SET approved_by = NULL WHERE approved_by = %s",
            (user_id,),
        )
        conn.execute(
            "UPDATE auth.users SET deactivated_by = NULL WHERE deactivated_by = %s",
            (user_id,),
        )
        conn.execute(
            "DELETE FROM auth.users WHERE id = %s",
            (user_id,),
        )


@pytest.fixture
def clean_state(db):
    from backend.services.audit import clear_state

    clear_state()
    yield
    clear_state()
    set_current_user(None)


@pytest.fixture
def test_user(db):
    """Real temporary employee shared by service and HTTP tests."""
    user = _create_active_user("EMPLOYEE")
    set_current_user(user)

    try:
        yield user
    finally:
        set_current_user(None)
        _delete_test_user(user.id)


def _auth_headers(user_id: int, role: str) -> dict[str, str]:
    import jwt

    token = jwt.encode({"sub": str(user_id), "role": role}, TEST_AUTH_SECRET, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(db, monkeypatch):
    """Bearer headers for a real temporary administrator."""
    monkeypatch.setenv("AUTH_SECRET_KEY", TEST_AUTH_SECRET)
    user = _create_active_user("ADMIN")

    try:
        yield _auth_headers(user.id, user.role)
    finally:
        _delete_test_user(user.id)


@pytest.fixture
def employee_auth_headers(test_user, monkeypatch):
    """Bearer headers matching the real test_user identity."""
    monkeypatch.setenv("AUTH_SECRET_KEY", TEST_AUTH_SECRET)
    return _auth_headers(test_user.id, test_user.role)


def parse_tool(raw: str) -> dict:
    data = json.loads(raw)
    assert isinstance(data, dict)
    return data
