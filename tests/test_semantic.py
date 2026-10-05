"""Semantic layer covers every stored column and renders into the system prompt."""

from __future__ import annotations

from backend.agent.prompts import build_system_prompt
from backend.services.semantic import load_semantic_layer, render_semantic_prompt


def test_semantic_layer_covers_runtime_columns(db):
    load_semantic_layer.cache_clear()
    layer = load_semantic_layer()
    tables = layer["data_definition"]["tables"]

    order = db.get_order_by_id("ORD-057")
    production_rows = db.production_log()
    workshop_rows = db.workshops()

    assert order is not None
    assert production_rows
    assert workshop_rows

    runtime_columns = {
        "orders": set(order),
        "production_log": set(production_rows[0]),
        "workshops": set(workshop_rows[0]),
    }

    for table_name, columns in runtime_columns.items():
        assert set(tables[table_name]["columns"]) == columns

    for table in tables.values():
        for column in (table.get("columns") or {}).values():
            assert str(column.get("description") or "").strip()


def test_semantic_prompt_includes_field_descriptions_and_terms():
    load_semantic_layer.cache_clear()
    text = render_semantic_prompt()
    assert "How many garments in this order" in text
    assert "selling_price" in text
    assert "factory_today" in text
    assert "feasibility" in text
    assert "check_feasibility" in text


def test_system_prompt_embeds_semantic_layer():
    prompt = build_system_prompt()
    assert "Semantic layer" in prompt
    assert "get_order_status" in prompt
