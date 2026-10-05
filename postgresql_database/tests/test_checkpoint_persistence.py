"""Integration test for durable and isolated LangGraph checkpoints."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict
from uuid import uuid4

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from psycopg import sql

from backend.pg_config import COPILOT_SCHEMA
from backend.services.checkpoint_store import postgres_checkpointer
from backend.services.pg_database import connect


class CheckpointTestState(TypedDict):
    history: Annotated[list[str], operator.add]


def finish_step(_state: CheckpointTestState) -> dict:
    return {}


def build_test_graph(checkpointer: BaseCheckpointSaver):
    builder = StateGraph(CheckpointTestState)
    builder.add_node("finish", finish_step)
    builder.add_edge(START, "finish")
    builder.add_edge("finish", END)
    return builder.compile(checkpointer=checkpointer)


def delete_test_threads(thread_ids: list[str]) -> None:
    """Remove only checkpoint rows created by this test."""

    with connect(admin=True) as connection, connection.transaction():
        for table in (
            "checkpoint_writes",
            "checkpoint_blobs",
            "checkpoints",
        ):
            connection.execute(
                sql.SQL(
                    "DELETE FROM {}.{} WHERE thread_id = ANY(%s)"
                ).format(
                    sql.Identifier(COPILOT_SCHEMA),
                    sql.Identifier(table),
                ),
                (thread_ids,),
            )


def test_checkpoint_survives_pool_restart_and_isolates_threads() -> None:
    prefix = f"test:checkpoint:{uuid4()}"
    first_thread = f"{prefix}:first"
    second_thread = f"{prefix}:second"

    first_config = {
        "configurable": {
            "thread_id": first_thread,
        }
    }
    second_config = {
        "configurable": {
            "thread_id": second_thread,
        }
    }

    try:
        # First application lifetime: create the initial checkpoint.
        with postgres_checkpointer() as checkpointer:
            graph = build_test_graph(checkpointer)
            first_result = graph.invoke(
                {"history": ["first"]},
                config=first_config,
            )

        assert first_result["history"] == ["first"]

        # Second application lifetime: use a newly opened connection pool.
        with postgres_checkpointer() as checkpointer:
            graph = build_test_graph(checkpointer)

            restored = graph.get_state(first_config)
            assert restored.values["history"] == ["first"]

            second_result = graph.invoke(
                {"history": ["second"]},
                config=first_config,
            )
            assert second_result["history"] == ["first", "second"]

            isolated = graph.get_state(second_config)
            assert not isolated.values
    finally:
        delete_test_threads([first_thread, second_thread])