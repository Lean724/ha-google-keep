"""Tests for the Todo platform."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.components.todo import TodoItem, TodoItemStatus

from custom_components.google_keep.const import DOMAIN


async def _setup_integration(hass, mock_config_entry, mock_api):
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.google_keep.GoogleKeepAPI", return_value=mock_api
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    return mock_config_entry


async def test_checklist_becomes_todo_list(hass, mock_config_entry, mock_api):
    await _setup_integration(hass, mock_config_entry, mock_api)

    state = hass.states.get("todo.shopping_list")
    assert state is not None
    # 1 unchecked item ("Milk") out of 2 total
    assert state.state == "1"


async def test_plain_note_has_no_todo_entity(hass, mock_config_entry, mock_api):
    await _setup_integration(hass, mock_config_entry, mock_api)

    assert hass.states.get("todo.ideas") is None


async def test_create_todo_item_calls_api(hass, mock_config_entry, mock_api):
    await _setup_integration(hass, mock_config_entry, mock_api)

    await hass.services.async_call(
        "todo",
        "add_item",
        {"item": "Bread", "entity_id": "todo.shopping_list"},
        blocking=True,
    )

    mock_api.async_add_item.assert_called_once()
    assert mock_api.async_add_item.call_args.args[1] == "Bread"


async def test_complete_todo_item_calls_api(hass, mock_config_entry, mock_api):
    await _setup_integration(hass, mock_config_entry, mock_api)

    await hass.services.async_call(
        "todo",
        "update_item",
        {
            "item": "item-1",
            "entity_id": "todo.shopping_list",
            "status": "completed",
        },
        blocking=True,
    )

    mock_api.async_set_item_checked.assert_called_once_with(
        "list-1", "item-1", True
    )


async def test_remove_todo_item_calls_api(hass, mock_config_entry, mock_api):
    await _setup_integration(hass, mock_config_entry, mock_api)

    await hass.services.async_call(
        "todo",
        "remove_item",
        {"item": ["item-1"], "entity_id": "todo.shopping_list"},
        blocking=True,
    )

    mock_api.async_remove_item.assert_called_once_with("list-1", "item-1")
